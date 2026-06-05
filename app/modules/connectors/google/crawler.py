"""Google Drive Crawler and native export engine"""

import json
import logging
from collections.abc import Generator
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.core.connectors import CheckpointedConnector, SlimDocument, HierarchyNode, ConnectorCheckpoint, StageCompletion
from .auth import GoogleAuthManager, execute_google_request

logger = logging.getLogger(__name__)

# Native Google MIME types and their corresponding target export formats
NATIVE_GOOGLE_EXPORT_MAP = {
    "application/vnd.google-apps.document": {
        "mime_type": "text/plain",
        "extension": ".txt"
    },
    "application/vnd.google-apps.spreadsheet": {
        "mime_type": "text/csv",
        "extension": ".csv"
    },
    "application/vnd.google-apps.presentation": {
        "mime_type": "application/pdf",
        "extension": ".pdf"
    }
}

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class GoogleDriveConnector(CheckpointedConnector[ConnectorCheckpoint]):
    """
    Checkpointed crawler for Google Drive.
    Traverses folder structures and downloads/exports files for ingestion.
    """

    def __init__(
        self,
        folder_urls: Optional[List[str]] = None,
        include_shared_drives: bool = False,
        include_my_drive: bool = True,
        exclude_mime_types: Optional[List[str]] = None,
    ) -> None:
        self.auth_manager = GoogleAuthManager()
        self.include_shared_drives = include_shared_drives
        self.include_my_drive = include_my_drive
        self.exclude_mime_types = exclude_mime_types or []
        self.target_folder_ids = self._extract_folder_ids(folder_urls or [])

    def _extract_folder_ids(self, urls: List[str]) -> List[str]:
        """Extract folder IDs from raw Google Drive URLs"""
        ids = []
        for url in urls:
            if not url:
                continue
            parsed = urlparse(url)
            path_parts = parsed.path.rstrip("/").split("/")
            if path_parts:
                # E.g. https://drive.google.com/drive/folders/FOLDER_ID
                ids.append(path_parts[-1])
        return ids

    def load_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any] | None:
        return self.auth_manager.load_credentials(credentials)

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

    async def download_file_bytes(
        self,
        file_id: str,
        mime_type: str,
        impersonate_email: Optional[str] = None,
    ) -> bytes:
        """
        Download binary file content or export native Google formats.
        """
        async with self.auth_manager.get_client(impersonate_email) as client:
            # 1. Native Google Doc / Sheet / Slide Exporter
            if mime_type in NATIVE_GOOGLE_EXPORT_MAP:
                export_format = NATIVE_GOOGLE_EXPORT_MAP[mime_type]
                logger.info(f"Exporting native Google file {file_id} as {export_format['mime_type']}")
                url = f"/drive/v3/files/{file_id}/export"
                params = {"mimeType": export_format["mime_type"]}
                
                # Fetch raw export stream
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    raise RuntimeError(f"Google Workspace export failed: {response.text}")
                return response.content

            # 2. Standard Binary Downloader
            else:
                logger.info(f"Downloading standard binary file {file_id}")
                url = f"/drive/v3/files/{file_id}"
                params = {"alt": "media"}
                
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    raise RuntimeError(f"Google Drive binary download failed: {response.text}")
                return response.content

    def _build_search_query(self, parent_id: Optional[str] = None, start_time: Optional[float] = None) -> str:
        """Construct Google Drive file search query filters"""
        queries = ["trashed = false"]

        # Filter out folder MIME type from document lists
        queries.append(f"mimeType != '{FOLDER_MIME_TYPE}'")

        if parent_id:
            queries.append(f"'{parent_id}' in parents")

        if start_time:
            # Format UNIX timestamp to ISO 8601 YYYY-MM-DDTHH:MM:SSZ
            from datetime import datetime, timezone
            iso_time = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            queries.append(f"modifiedTime > '{iso_time}'")

        # Exclude specific MIME types
        for mime in self.exclude_mime_types:
            queries.append(f"mimeType != '{mime}'")

        return " and ".join(queries)

    async def list_directory(self, parent_id: Optional[str] = None, impersonate_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """List files and folders directly within a specific parent (or root)."""
        email = impersonate_email or self.auth_manager.primary_admin_email
        async with self.auth_manager.get_client(email) as client:
            queries = ["trashed = false"]
            if parent_id:
                queries.append(f"'{parent_id}' in parents")
            else:
                queries.append("'root' in parents")

            params = {
                "q": " and ".join(queries),
                "pageSize": 1000,
                "fields": "files(id, name, mimeType)",
                "supportsAllDrives": self.include_shared_drives,
                "includeItemsFromAllDrives": self.include_shared_drives,
            }
            try:
                res = await execute_google_request(client, "GET", "/drive/v3/files", params=params)
                return res.get("files", [])
            except Exception as e:
                logger.error(f"Failed to list directory for {email}: {e}")
                return []

    async def get_files_metadata(self, file_ids: List[str], impersonate_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch metadata for specific file IDs."""
        if not file_ids:
            return []
        email = impersonate_email or self.auth_manager.primary_admin_email
        async with self.auth_manager.get_client(email) as client:
            files_meta = []
            for fid in file_ids:
                params = {
                    "fields": "id, name, mimeType, parents, size, webViewLink, trashed",
                    "supportsAllDrives": self.include_shared_drives,
                }
                try:
                    res = await execute_google_request(client, "GET", f"/drive/v3/files/{fid}", params=params)
                    if res and not res.get("trashed"):
                        files_meta.append(res)
                except Exception as e:
                    logger.error(f"Failed to get file metadata for {fid} ({email}): {e}")
            return files_meta

    async def load_from_checkpoint(
        self,
        start: float,
        end: float,
        checkpoint: ConnectorCheckpoint,
    ) -> Generator[SlimDocument | HierarchyNode, None, None]:
        """
        Main crawling loop yielding slim documents and folder hierarchy nodes.
        Returns the subsequent checkpoint when complete or rate-limited.
        """
        # Determine emails to crawl.
        # If Service Account is active, we list and impersonate users.
        # If User OAuth is active, we crawl as the primary account.
        emails_to_crawl = [self.auth_manager.primary_admin_email]
        if self.auth_manager.is_service_account:
            if checkpoint.user_emails:
                emails_to_crawl = checkpoint.user_emails
            else:
                # Crawl as primary admin by default
                emails_to_crawl = [self.auth_manager.primary_admin_email]

        for email in emails_to_crawl:
            if email not in checkpoint.completion_map:
                checkpoint.completion_map[email] = StageCompletion(stage="crawling", completed_until=start)

            completion = checkpoint.completion_map[email]
            if completion.stage == "done":
                continue

            logger.info(f"Starting crawl stage for user: {email}")

            async with self.auth_manager.get_client(email) as client:
                # 1. FOLDER/HIERARCHY CRAWLING STAGE
                # We do a scan to map the parent folder structure if target folders are isolated.
                if self.target_folder_ids:
                    for folder_id in self.target_folder_ids:
                        try:
                            folder_meta = await execute_google_request(
                                client, "GET", f"/drive/v3/files/{folder_id}?fields=id,name,parents"
                            )
                            parent_id = folder_meta.get("parents", [None])[0]
                            yield HierarchyNode(
                                raw_node_id=folder_id,
                                raw_parent_id=parent_id,
                                display_name=folder_meta.get("name", "Target Folder"),
                                node_type="folder",
                            )
                        except Exception as e:
                            logger.warning(f"Failed to fetch metadata for target folder {folder_id}: {e}")

                # 2. FILE INDEXING STAGE
                has_more_pages = True
                page_token = completion.next_page_token

                while has_more_pages:
                    # Construct search query
                    q_query = self._build_search_query(start_time=completion.completed_until)
                    params = {
                        "q": q_query,
                        "pageSize": 50,
                        "fields": "nextPageToken, files(id, name, mimeType, parents, modifiedTime, size, webViewLink)",
                        "supportsAllDrives": self.include_shared_drives,
                        "includeItemsFromAllDrives": self.include_shared_drives,
                    }
                    if page_token:
                        params["pageToken"] = page_token

                    try:
                        logger.debug(f"Listing files with params: {params}")
                        res = await execute_google_request(client, "GET", "/drive/v3/files", params=params)
                    except Exception as e:
                        logger.error(f"Failed to list Google Drive files for {email}: {e}")
                        # Return current checkpoint to retry subsequently
                        completion.next_page_token = page_token
                        checkpoint.has_more = True
                        return

                    files = res.get("files", [])
                    for file in files:
                        file_id = file.get("id")
                        if not file_id or file_id in checkpoint.all_retrieved_file_ids:
                            continue

                        # Extract MIME type
                        mime_type = file.get("mimeType", "application/octet-stream")
                        
                        # Set up standard metadata footprint
                        meta = {
                            "file_id": file_id,
                            "filename": file.get("name", "unnamed"),
                            "mime_type": mime_type,
                            "webViewLink": file.get("webViewLink"),
                            "size_bytes": int(file.get("size", 0)),
                            "parents": file.get("parents", []),
                            "user_email": email,
                        }

                        # Check if file has a parent to yield parent hierarchy node reference
                        parents = file.get("parents", [])
                        if parents:
                            for parent_id in parents:
                                yield HierarchyNode(
                                    raw_node_id=parent_id,
                                    raw_parent_id=None,  # Resolved dynamically in higher layers
                                    display_name="Folder Reference",
                                    node_type="folder",
                                )

                        # Yield the slim metadata document
                        yield SlimDocument(
                            id=file_id,
                            source="google_drive",
                            metadata=meta,
                        )

                        checkpoint.all_retrieved_file_ids.add(file_id)

                    # Update pagination tokens
                    page_token = res.get("nextPageToken")
                    completion.next_page_token = page_token
                    has_more_pages = bool(page_token)

                # Completed crawling successfully for this email subject
                completion.stage = "done"

        # Check if all users have completed indexing
        all_done = all(comp.stage == "done" for comp in checkpoint.completion_map.values())
        checkpoint.has_more = not all_done
        return
