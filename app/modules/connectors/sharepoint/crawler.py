import logging
import httpx
from typing import Any, Dict, List, Optional
from collections.abc import Generator

from app.core.connectors import CheckpointedConnector, SlimDocument, HierarchyNode, ConnectorCheckpoint, StageCompletion
from .auth import SharePointAuthManager, execute_graph_request

logger = logging.getLogger(__name__)

FOLDER_MIME_TYPE = "application/vnd.microsoft.graph.folder"

class SharePointConnector(CheckpointedConnector[ConnectorCheckpoint]):
    """
    Checkpointed crawler for Microsoft SharePoint / OneDrive.
    Traverses folder structures and downloads binary files for ingestion.
    """

    def __init__(
        self,
        site_urls: Optional[List[str]] = None,
    ) -> None:
        self.auth_manager = SharePointAuthManager()
        self.site_urls = site_urls or []

    def load_credentials(self, credentials: dict) -> dict:
        """Load OAuth tokens from database connection parameters"""
        self.access_token = credentials.get("access_token")
        self.refresh_token = credentials.get("refresh_token")
        
        # ACTUALLY pass them to the auth manager!
        self.auth_manager.load_credentials(credentials)
        
        if not self.access_token:
            logger.error("Missing SharePoint OAuth access token")
            return None
            
        return credentials
    def get_headers(self) -> dict:
        """Use the delegated access token for Microsoft Graph"""
        if not hasattr(self, 'access_token') or not self.access_token:
            raise ValueError("Access token is missing. User must authenticate via OAuth.")
            
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
    def build_dummy_checkpoint(self) -> ConnectorCheckpoint:
        return ConnectorCheckpoint(
            has_more=True,
            completion_stage="start",
        )

    def validate_checkpoint_json(self, checkpoint_json: str) -> ConnectorCheckpoint:
        try:
            return ConnectorCheckpoint.model_validate_json(checkpoint_json)
        except Exception as e:
            logger.warning(f"Failed to validate checkpoint JSON: {e}, falling back to dummy")
            return self.build_dummy_checkpoint()

    async def get_site_id_from_url(self, url: str) -> Optional[str]:
        """Resolve a SharePoint URL to a Microsoft Graph Site ID."""
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return None
            
            path = parsed.path
            
            if path.startswith("/sites/"):
                site_path = "/sites/" + path.split("/")[2]
                endpoint = f"/sites/{hostname}:{site_path}"
            elif path.startswith("/teams/"):
                site_path = "/teams/" + path.split("/")[2]
                endpoint = f"/sites/{hostname}:{site_path}"
            else:
                endpoint = f"/sites/{hostname}"
                
            res = await execute_graph_request(self.auth_manager, "GET", endpoint)
            return res.get("id")
        except Exception as e:
            logger.error(f"Failed to resolve site ID for {url}: {e}")
            return None

    async def list_directory(self, parent_id: str) -> List[Dict[str, Any]]:
        """List files and folders directly within a specific SharePoint item (or drive root)."""
        # Note: parent_id in this context could be formatted as driveId:itemId to easily navigate.
        # If parent_id doesn't have a colon, we assume it's a site ID and we list the root of its default drive.
        
        try:
            if ":" in parent_id:
                drive_id, item_id = parent_id.split(":", 1)
                endpoint = f"/drives/{drive_id}/items/{item_id}/children"
            else:
                # Assume parent_id is a site_id, fetch the default drive root
                endpoint = f"/sites/{parent_id}/drive/root/children"

            res = await execute_graph_request(self.auth_manager, "GET", endpoint)
            items = res.get("value", [])
            
            # Format items similar to Google Drive for uniformity
            formatted_items = []
            for item in items:
                is_folder = "folder" in item
                mime_type = FOLDER_MIME_TYPE if is_folder else item.get("file", {}).get("mimeType", "application/octet-stream")
                drive_id = item.get("parentReference", {}).get("driveId")
                item_id = item.get("id")
                
                formatted_items.append({
                    "id": f"{drive_id}:{item_id}",
                    "name": item.get("name"),
                    "mimeType": mime_type,
                    "is_folder": is_folder,
                    "webUrl": item.get("webUrl"),
                    "parents": [parent_id]
                })
            return formatted_items
        except Exception as e:
            logger.error(f"Failed to list directory for {parent_id}: {e}")
            return []

    async def get_files_metadata(self, item_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch metadata for specific item IDs."""
        files_meta = []
        for raw_id in item_ids:
            try:
                if ":" in raw_id:
                    drive_id, item_id = raw_id.split(":", 1)
                    endpoint = f"/drives/{drive_id}/items/{item_id}"
                else:
                    # Treat as site root
                    endpoint = f"/sites/{raw_id}/drive/root"
                
                item = await execute_graph_request(self.auth_manager, "GET", endpoint)
                if item:
                    is_folder = "folder" in item
                    mime_type = FOLDER_MIME_TYPE if is_folder else item.get("file", {}).get("mimeType", "application/octet-stream")
                    drive_id = item.get("parentReference", {}).get("driveId") or item.get("id") # Fallback for root
                    parent_ref = item.get("parentReference", {}).get("id")
                    
                    parent_id = f"{drive_id}:{parent_ref}" if parent_ref else None

                    files_meta.append({
                        "id": raw_id,
                        "name": item.get("name"),
                        "mimeType": mime_type,
                        "parents": [parent_id] if parent_id else [],
                        "webViewLink": item.get("webUrl"),
                        "size": item.get("size", 0)
                    })
            except Exception as e:
                logger.error(f"Failed to get file metadata for {raw_id}: {e}")
        return files_meta

    async def download_file_bytes(self, file_id: str) -> bytes:
        """
        Download binary file content from SharePoint.
        We download binary as requested, leaving parsing to existing logic.
        """
        if ":" not in file_id:
            raise ValueError("Invalid SharePoint file ID format. Expected driveId:itemId")
            
        drive_id, item_id = file_id.split(":", 1)
        endpoint = f"/drives/{drive_id}/items/{item_id}/content"
        
        token = await self.auth_manager.get_valid_token()
        headers = {"Authorization": f"Bearer {token}"}
        base_url = "https://graph.microsoft.com/v1.0"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(f"{base_url}{endpoint}", headers=headers)
            if response.status_code >= 400:
                logger.error(f"SharePoint binary download failed: {response.text}")
                response.raise_for_status()
            
            return response.content

    async def load_from_checkpoint(
        self,
        start: float,
        end: float,
        checkpoint: ConnectorCheckpoint,
    ) -> Generator[SlimDocument | HierarchyNode, None, None]:
        # Usually implemented for full crawling, but selective sync will bypass this.
        # Since selective generator is used in the service layer, we can leave this as a no-op 
        # or implement basic full sync.
        yield HierarchyNode(raw_node_id="root", raw_parent_id=None, display_name="Root", node_type="folder")
