import os
import logging
import urllib.parse
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.database import AsyncSessionLocal
from app.core.s3 import S3StorageService
from app.modules.knowledge_bases.service import KnowledgeBaseService
from app.modules.knowledge_bases.routes import get_tenant_and_user

logger = logging.getLogger(__name__)

# Register a router without a module prefix to support /files/{file_id}/preview
router = APIRouter(tags=["Files"])

CONTENT_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel"
}

@router.get("/files/{file_id}/preview")
@router.get("/api/v1/files/{file_id}/preview", include_in_schema=False)
async def preview_file(request: Request, file_id: str):
    """
    Securely preview or download files stored in private S3.
    Supported formats: .pdf, .csv, .xlsx, .xls
    """
    try:
        tenant_id, user_id = get_tenant_and_user(request)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncSessionLocal() as db:
        service = KnowledgeBaseService(db, tenant_id)
        result = await service.get_file_preview_metadata(file_id, user_id)
        
        if not result.get("success"):
            error_msg = result.get("error", "File not found")
            status_code = result.get("status_code", 404)
            raise HTTPException(status_code=status_code, detail=error_msg)

        data = result["data"]
        filename = data["filename"]
        s3_key = data["s3_key"]
        
        # Validation for allowed extensions
        file_ext = os.path.splitext(filename.lower())[1]
        if file_ext not in CONTENT_TYPE_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{file_ext}'. Allowed types: PDF, CSV, Excel."
            )

        content_type = CONTENT_TYPE_MAP[file_ext]
        
        # Stream file from S3
        s3_service = S3StorageService()
        try:
            stream_body = s3_service.get_file_stream(s3_key)
        except ValueError as val_err:
            logger.error(f"S3 configuration error: {val_err}")
            raise HTTPException(status_code=500, detail="S3 storage is not configured properly.")
        except Exception as s3_err:
            logger.error(f"S3 fetch failed for key {s3_key}: {s3_err}")
            raise HTTPException(status_code=500, detail="Failed to fetch file from S3 storage.")

        encoded_filename = urllib.parse.quote(filename)
        headers = {
            "Content-Disposition": f'inline; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
        }
        
        return StreamingResponse(
            stream_body,
            media_type=content_type,
            headers=headers
        )


@router.get("/files/{file_id}/content")
@router.get("/api/v1/files/{file_id}/content", include_in_schema=False)
async def get_parsed_file_content(request: Request, file_id: str):
    """
    Securely retrieve the parsed text content of a file.
    """
    try:
        tenant_id, user_id = get_tenant_and_user(request)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncSessionLocal() as db:
        service = KnowledgeBaseService(db, tenant_id)
        result = await service.get_parsed_content(file_id, user_id)
        
        if not result.get("success"):
            error_msg = result.get("error", "File not found")
            status_code = result.get("status_code", 404)
            raise HTTPException(status_code=status_code, detail=error_msg)

        return result

