import sys

path = 'app/modules/knowledge_bases/service.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert list_google_drive_directory
func1 = """    async def list_google_drive_directory(self, kb_id: str, parent_id: Optional[str] = None) -> dict:
        try:
            from sqlalchemy import select
            from .models import DatabaseConnection
            import uuid
            
            query = select(DatabaseConnection).where(
                DatabaseConnection.kb_id == uuid.UUID(kb_id),
                DatabaseConnection.tenant_id == self.tenant_id,
                DatabaseConnection.db_type == "google_drive"
            )
            res = await self.db.execute(query)
            db_conn = res.scalar_one_or_none()
            if not db_conn:
                return format_error("No registered Google Drive connection found for this KB", status_code=404)

            credentials = db_conn.connection_params.get("credentials", {})
            
            from app.modules.connectors.google.crawler import GoogleDriveConnector
            connector = GoogleDriveConnector()
            connector.load_credentials(credentials)
            
            raw_items = await connector.list_directory(parent_id)
            items = []
            for item in raw_items:
                is_folder = item.get("mimeType") == "application/vnd.google-apps.folder"
                items.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "mime_type": item.get("mimeType"),
                    "is_folder": is_folder
                })
            
            return format_success({"items": items})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to list Google Drive directory: {e}", exc_info=True)
            return format_error(f"Failed to list directory: {str(e)}")

"""

idx = content.find('    async def sync_google_drive_source(')
if idx == -1:
    print("Failed to find sync_google_drive_source")
    sys.exit(1)

content = content[:idx] + func1 + content[idx:]

# 2. Update signature
idx_sig = content.find('folder_urls: Optional[List[str]] = None,', idx)
if idx_sig == -1:
    print("Failed to find folder_urls parameter")
    sys.exit(1)

# we need to be careful with double spacing
new_params = 'folder_urls: Optional[List[str]] = None,\n\n        file_ids: Optional[List[str]] = None,\n\n        folder_ids: Optional[List[str]] = None,'
content = content[:idx_sig] + new_params + content[idx_sig + len('folder_urls: Optional[List[str]] = None,'):]

# 3. Update generator assignment
# there might be empty lines
# Let's use regex
import re

target = r"generator\s*=\s*connector\.load_from_checkpoint\(0\.0,\s*0\.0,\s*checkpoint\)\s*from\s+app\.core\.connectors\s+import\s+HierarchyNode,\s*SlimDocument"

replacement = """from app.core.connectors import HierarchyNode, SlimDocument

            if file_ids or folder_ids:
                async def selective_generator():
                    all_file_ids = set(file_ids or [])
                    for fid in (folder_ids or []):
                        children = await connector.list_directory(fid)
                        for c in children:
                            if c.get("mimeType") != "application/vnd.google-apps.folder":
                                all_file_ids.add(c["id"])
                    
                    if all_file_ids:
                        meta_files = await connector.get_files_metadata(list(all_file_ids))
                        for f in meta_files:
                            yield SlimDocument(
                                id=f["id"], source="google_drive", 
                                metadata={
                                    "file_id": f["id"], 
                                    "filename": f.get("name", "unnamed"), 
                                    "mime_type": f.get("mimeType", ""), 
                                    "webViewLink": f.get("webViewLink"), 
                                    "parents": f.get("parents", [])
                                }
                            )
                generator = selective_generator()
            else:
                generator = connector.load_from_checkpoint(0.0, 0.0, checkpoint)
"""

match = re.search(target, content)
if not match:
    print("Failed to find generator loop")
    sys.exit(1)

content = content[:match.start()] + replacement + content[match.end():]

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched service.py")
