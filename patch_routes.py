import sys
import re

path = 'app/modules/knowledge_bases/routes.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add the new endpoint before sync_google_drive_to_graph
new_endpoint = """
@router.get(
    "/{kb_id}/google-drive/files",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="List Google Drive Files",
    description="List files and folders from the connected Google Drive for selective ingestion."
)
async def list_google_drive_files(request: Request, kb_id: str, parent_id: Optional[str] = None) -> dict:
    try:
        tenant_id, _ = get_tenant_and_user(request)
        async with AsyncSessionLocal() as db:
            service = KnowledgeBaseService(db, tenant_id)
            return await service.list_google_drive_directory(kb_id=kb_id, parent_id=parent_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in list_google_drive_files: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

"""

target_post_sync = '@router.post(\n\n    "/{kb_id}/google-drive/sync",'
if target_post_sync not in content:
    target_post_sync = '@router.post(\n    "/{kb_id}/google-drive/sync",'
    if target_post_sync not in content:
        print("Failed to find sync POST endpoint marker")
        sys.exit(1)

content = content.replace(target_post_sync, new_endpoint + target_post_sync)

# 2. Update sync_google_drive_to_graph signature
target_def = 'async def sync_google_drive_to_graph(request: Request, kb_id: str) -> dict:'
if target_def not in content:
    target_def = 'async def sync_google_drive_to_graph(request: Request, kb_id: str) -> dict:'
    
replacement_def = 'async def sync_google_drive_to_graph(request: Request, kb_id: str, sync_req: Optional[schemas.GoogleDriveSyncRequest] = None) -> dict:'
content = content.replace(target_def, replacement_def)

# 3. Pass file_ids and folder_ids to service.sync_google_drive_source
# Need to find the exact call to sync_google_drive_source
target_call_start = 'result = await service.sync_google_drive_source('

idx = content.find(target_call_start)
if idx == -1:
    print("Failed to find sync_google_drive_source call")
    sys.exit(1)

# Find the end of the call by looking for the closing parenthesis
idx_end = content.find(')', idx)

original_call = content[idx:idx_end+1]
replacement_call = '''            file_ids = sync_req.file_ids if sync_req else None
            folder_ids = sync_req.folder_ids if sync_req else None
            result = await service.sync_google_drive_source(
                kb_id=kb_id,
                credentials_dict=credentials,
                folder_urls=folder_urls,
                file_ids=file_ids,
                folder_ids=folder_ids
            )'''

content = content.replace(original_call, replacement_call)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully patched routes.py")
