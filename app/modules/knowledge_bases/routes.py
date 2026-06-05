from typing import Optional, List, Dict, Any
"""REST routes for Knowledge Base CRUD and document ingestion"""



from fastapi import APIRouter, Request, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

import logging

import uuid



from .service import KnowledgeBaseService

from . import schemas

from ...core.database import AsyncSessionLocal

from ...utils.formatters import format_error, format_success



logger = logging.getLogger(__name__)



router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"])





# ============================================================================

# REQUEST CONTEXT HELPERS

# ============================================================================





def get_tenant_and_user(request: Request) -> tuple[str, str]:

    """

    Extract tenant_id and user_id from request context (set by middleware).



    CRITICAL: These are injected by TenantContextMiddleware.

    Never trust values from request body or query params.



    Returns:

        Tuple of (tenant_id, user_id)



    Raises:

        HTTPException if not found in request state

    """

    tenant_id = getattr(request.state, "tenant_id", None)

    user_id = getattr(request.state, "user_id", None)



    if not tenant_id or not user_id:

        logger.error("Missing tenant_id or user_id in request state")

        raise HTTPException(status_code=401, detail="Unauthorized")



    return str(tenant_id), str(user_id)





# ============================================================================

# ENDPOINTS

# ============================================================================





@router.post(

    "",

    response_model=dict,

    status_code=status.HTTP_200_OK,

    summary="Create Knowledge Base",

    description="Create a new knowledge base for an agent",

)

async def create_kb(

    request: Request,

    kb_request: schemas.KBCreate,

) -> dict:

    """

    Create a new knowledge base linked to an agent.



    Creates KB in BOTH:

    1. PostgreSQL (metadata storage)

    2. Neo4j (graph node for chunk relationships)



    TRANSACTION SAFETY:

    - If either database fails, entire operation is rolled back

    - No orphaned nodes or records



    Args:

        request: FastAPI request (contains tenant_id in state)

        kb_request: KBCreate schema with name, agent_id, description



    Returns:

        JSON response with created KB



    Raises:

        HTTPException 401: Not authenticated

        HTTPException 400: Invalid request

        HTTPException 500: Database error

    """

    try:

        tenant_id, user_id = get_tenant_and_user(request)



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)

            result = await service.create_knowledge_base(user_id, kb_request)



            if not result.get("success"):

                error_msg = result.get("error", "Unknown error")

                status_code = result.get("status_code", 400)

                raise HTTPException(status_code=status_code, detail=error_msg)



            return result



    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Create KB endpoint error: {e}")

        raise HTTPException(status_code=500, detail="Internal server error")





@router.get(

    "/{kb_id}",

    response_model=dict,

    summary="Get Knowledge Base",

    description="Get a knowledge base by ID",

)

async def get_kb(request: Request, kb_id: str) -> dict:

    """

    Get a knowledge base by ID.



    Args:

        request: FastAPI request

        kb_id: KB UUID



    Returns:

        JSON response with KB details



    Raises:

        HTTPException 401: Not authenticated

        HTTPException 404: KB not found

        HTTPException 500: Database error

    """

    try:

        tenant_id, _ = get_tenant_and_user(request)



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)

            result = await service.get_kb(kb_id)



            if not result.get("success"):

                error_msg = result.get("error", "Unknown error")

                status_code = result.get("status_code", 404)

                raise HTTPException(status_code=status_code, detail=error_msg)



            return result



    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Get KB endpoint error: {e}")

        raise HTTPException(status_code=500, detail="Internal server error")





@router.get(

    "",

    response_model=dict,

    summary="List Knowledge Bases",

    description="List all knowledge bases for the tenant",

)

async def list_kbs(request: Request, limit: int = 50, offset: int = 0) -> dict:

    """

    List all knowledge bases for the tenant with pagination.



    Args:

        request: FastAPI request

        limit: Max results (default 50)

        offset: Pagination offset (default 0)



    Returns:

        JSON response with KBs list



    Raises:

        HTTPException 401: Not authenticated

        HTTPException 500: Database error

    """

    try:

        tenant_id, _ = get_tenant_and_user(request)



        # Validate pagination

        if limit < 1 or limit > 1000:

            limit = 50

        if offset < 0:

            offset = 0



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)

            result = await service.list_kbs(limit=limit, offset=offset)



            if not result.get("success"):

                raise HTTPException(status_code=500, detail=result.get("error"))



            return result



    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"List KBs endpoint error: {e}")

        raise HTTPException(status_code=500, detail="Internal server error")





@router.get(

    "/agents/{agent_id}",

    response_model=dict,

    summary="List Knowledge Bases for Agent",

    description="List all knowledge bases for a specific agent",

)

async def list_agent_kbs(

    request: Request,

    agent_id: str,

    limit: int = 50,

    offset: int = 0,

) -> dict:

    """

    List knowledge bases for a specific agent.



    Args:

        request: FastAPI request

        agent_id: Agent UUID

        limit: Max results (default 50)

        offset: Pagination offset (default 0)



    Returns:

        JSON response with KBs list



    Raises:

        HTTPException 401: Not authenticated

        HTTPException 500: Database error

    """

    try:

        tenant_id, _ = get_tenant_and_user(request)



        # Validate pagination

        if limit < 1 or limit > 1000:

            limit = 50

        if offset < 0:

            offset = 0



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)

            result = await service.list_kbs_by_agent(

                agent_id, limit=limit, offset=offset

            )



            if not result.get("success"):

                raise HTTPException(status_code=500, detail=result.get("error"))



            return result



    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"List agent KBs endpoint error: {e}")

        raise HTTPException(status_code=500, detail="Internal server error")





@router.post(

    "/{kb_id}/ingest",

    response_model=dict,

    summary="Ingest Document",

    description="Upload and ingest a document into a knowledge base",

)

async def ingest_document(

    request: Request,

    kb_id: str,

    body: dict,  # {"document_text": "..."}

) -> dict:

    """

    Ingest a document into a knowledge base.



    PROCESS:

    1. Validate KB exists

    2. Split text into chunks (500-1000 tokens, overlap)

    3. Generate embeddings for each chunk

    4. Store chunks in Neo4j

    5. Create ChunkChunk(NEXT) relationships



    Args:

        request: FastAPI request

        kb_id: KB UUID

        body: Request body with "document_text" field



    Returns:

        JSON response with chunks created count



    Raises:

        HTTPException 401: Not authenticated

        HTTPException 404: KB not found

        HTTPException 400: Invalid request

        HTTPException 500: Database error

    """

    try:

        tenant_id, _ = get_tenant_and_user(request)



        # Extract document text and optional source

        document_text = body.get("document_text", "").strip()

        source = body.get("source", "text").strip()

        if not document_text:

            raise HTTPException(status_code=400, detail="document_text is required")



        if len(document_text) > 1_000_000:  # 1MB limit

            raise HTTPException(status_code=400, detail="Document too large (max 1MB)")



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)

            result = await service.ingest_document(kb_id, document_text, source=source)



            if not result.get("success"):

                error_msg = result.get("error", "Unknown error")

                status_code = result.get("status_code", 400)

                raise HTTPException(status_code=status_code, detail=error_msg)



            return result



    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Ingest document endpoint error: {e}")

        raise HTTPException(status_code=500, detail="Internal server error")





from fastapi import UploadFile, File



@router.post(

    "/{kb_id}/ingest/file",

    response_model=dict,

    summary="Ingest Document File",

    description="Upload and ingest a PDF, Excel (.xlsx, .xls) or CSV (.csv) file into the knowledge base.",

)

async def ingest_file(

    request: Request,

    kb_id: str,

    file: UploadFile = File(...),

) -> dict:

    """

    Ingest a document file (PDF, Excel, or CSV) into a knowledge base.

    """

    try:

        tenant_id, _ = get_tenant_and_user(request)

        filename = file.filename.lower()



        # 1. Route based on file extension

        if filename.endswith(".pdf"):

            content = await file.read()

            if len(content) > 10 * 1024 * 1024:  # 10MB limit

                raise HTTPException(status_code=400, detail="PDF too large (max 10MB)")



            # Extract PDF using PDFExtractor (Gdocz primary + pdfplumber fallback)

            from ...core.pdf_extractor import PDFExtractor



            try:

                document_text = await PDFExtractor.extract(

                    pdf_bytes=content,

                    filename=file.filename,

                    tenant_id=tenant_id,

                )

            except ValueError as e:

                raise HTTPException(status_code=400, detail=str(e))

            except Exception as e:

                logger.error(f"PDF extraction failed: {e}")

                raise HTTPException(

                    status_code=400,

                    detail=f"Failed to extract text from PDF: {str(e)}",

                )



            if not document_text.strip():

                raise HTTPException(

                    status_code=400,

                    detail="Could not extract any text from the PDF",

                )



            # Ingest standard document text

            async with AsyncSessionLocal() as db:

                service = KnowledgeBaseService(db, tenant_id)

                result = await service.ingest_document(kb_id, document_text)



                if not result.get("success"):

                    error_msg = result.get("error", "Unknown error")

                    status_code = result.get("status_code", 400)

                    raise HTTPException(status_code=status_code, detail=error_msg)



                return result



        elif filename.endswith((".xlsx", ".xls", ".csv")):

            content = await file.read()

            if len(content) > 20 * 1024 * 1024:  # 20MB limit

                raise HTTPException(status_code=400, detail="Spreadsheet file too large (max 20MB)")



            # Ingest structured Excel or CSV

            async with AsyncSessionLocal() as db:

                service = KnowledgeBaseService(db, tenant_id)

                result = await service.ingest_excel_or_csv(

                    kb_id=kb_id,

                    file_bytes=content,

                    filename=file.filename,

                )



                if not result.get("success"):

                    error_msg = result.get("error", "Unknown error")

                    status_code = result.get("status_code", 400)

                    raise HTTPException(status_code=status_code, detail=error_msg)



                return result

        else:

            raise HTTPException(

                status_code=400,

                detail="Unsupported file format. Supported extensions: .pdf, .xlsx, .xls, .csv"

            )



    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Ingest file endpoint error: {e}")

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")





@router.post(

    "/{kb_id}/ingest/pdf",

    response_model=dict,

    summary="Ingest PDF Document (Alias/Legacy)",

    description="Unified upload endpoint wrapper supporting PDF, Excel, and CSV under the legacy path.",

)

async def ingest_pdf(

    request: Request,

    kb_id: str,

    file: UploadFile = File(...),

) -> dict:

    """

    Unified PDF legacy route wrapper to support Excel/CSV uploaded through the existing PDF interface.

    """

    return await ingest_file(request=request, kb_id=kb_id, file=file)





@router.post(

    "/{kb_id}/ingest/url",

    response_model=dict,

    summary="Ingest URL Content",

    description="Crawl a URL and ingest its content into the knowledge base. Uses Gcrawl API with BeautifulSoup fallback.",

)

async def ingest_url(

    request: Request,

    kb_id: str,

    ingest_request: schemas.KBURLIngest,

) -> dict:

    """

    Ingest content from a URL into a knowledge base.



    STRATEGY:

    1. Scrape content using ScraperService (Gcrawl + BS4 fallback)

    2. Normalize multiple pages if crawl_type is 'all'

    3. Ingest each page's content into the KB

    """

    try:

        tenant_id, _ = get_tenant_and_user(request)



        from .services.scraper_service import ScraperService



        # 1. Scrape content

        documents = await ScraperService.extract_website_content(

            url=ingest_request.url,

            crawl_type=ingest_request.crawl_type,

            proxy_mode=ingest_request.proxy_mode

        )



        if not documents:

            raise HTTPException(

                status_code=400,

                detail="Could not extract any content from the provided URL"

            )



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)



            total_chunks = 0

            results = []



            # 2. Ingest each document

            for doc in documents:

                # Prepare document text with source header

                content = doc["content"]

                if len(documents) > 1:

                    content = f"# SOURCE: {doc['source']}\n\n{content}"



                ingest_result = await service.ingest_document(kb_id, content, source=doc["source"])



                if ingest_result.get("success"):

                    total_chunks += ingest_result["data"]["chunks_created"]

                    results.append({

                        "source": doc["source"],

                        "chunks": ingest_result["data"]["chunks_created"]

                    })



            if not results:

                raise HTTPException(status_code=500, detail="Failed to ingest any content")



            return format_success(

                {

                    "kb_id": kb_id,

                    "total_pages": len(results),

                    "total_chunks_created": total_chunks,

                    "details": results

                },

                meta={"message": f"Successfully ingested {len(results)} pages from {ingest_request.url}"}

            )



    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"URL ingestion endpoint error: {e}")

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")







@router.delete(

    "/{kb_id}",

    response_model=dict,

    summary="Delete Knowledge Base",

    description="Delete a knowledge base and all its chunks",

)

async def delete_kb(request: Request, kb_id: str) -> dict:
    """
    Delete a knowledge base.

    Deletes KB from BOTH:
    1. Neo4j (KB node + cascade chunks)
    2. PostgreSQL (soft-delete)

    Args:
        request: FastAPI request
        kb_id: KB UUID

    Returns:
        JSON response with deletion confirmation

    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: KB not found
        HTTPException 500: Database error
    """
    try:
        tenant_id, user_id = get_tenant_and_user(request)

        async with AsyncSessionLocal() as db:
            service = KnowledgeBaseService(db, tenant_id)
            result = await service.delete_kb(kb_id, user_id=user_id)



            if not result.get("success"):

                error_msg = result.get("error", "Unknown error")

                status_code = result.get("status_code", 404)

                raise HTTPException(status_code=status_code, detail=error_msg)



            return result



    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Delete KB endpoint error: {e}")

        raise HTTPException(status_code=500, detail="Internal server error")





# ============================================================================

# NATIVE DATABASE CONNECTOR ENDPOINTS

# ============================================================================



@router.post(

    "/{kb_id}/database-connection",

    response_model=dict,

    status_code=status.HTTP_200_OK,

    summary="Register Database Connection",

    description="Register and validate an external/local database connection config for this KB"

)

async def register_db_connection(

    request: Request,

    kb_id: str,

    db_request: schemas.DatabaseConnectionRegister

) -> dict:

    try:

        tenant_id, _ = get_tenant_and_user(request)



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)

            result = await service.register_database_connection(kb_id, db_request)



            if not result.get("success"):

                raise HTTPException(status_code=400, detail=result.get("error"))



            return result

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error in register_db_connection: {e}")

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")





@router.get(

    "/{kb_id}/database-schema",

    response_model=dict,

    status_code=status.HTTP_200_OK,

    summary="Discover Database Schema",

    description="Introspect the registered database tables for this KB"

)

async def discover_db_schema(request: Request, kb_id: str) -> dict:

    try:

        tenant_id, _ = get_tenant_and_user(request)



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)

            result = await service.discover_database_schema(kb_id)



            if not result.get("success"):

                raise HTTPException(status_code=400, detail=result.get("error"))



            return result

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error in discover_db_schema: {e}")

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")





@router.post(

    "/{kb_id}/sync-database",

    response_model=dict,

    status_code=status.HTTP_200_OK,

    summary="Synchronize Database to Graph",

    description="Introspect tables, transform rows into Chunk nodes, generate embeddings, and load them into Neo4j"

)

async def sync_db_to_graph(request: Request, kb_id: str) -> dict:

    try:

        tenant_id, _ = get_tenant_and_user(request)



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)

            result = await service.sync_database_source(kb_id)



            if not result.get("success"):

                raise HTTPException(status_code=400, detail=result.get("error"))



            return result

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error in sync_db_to_graph: {e}")

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.get("/{agent_id}/list_knowledge_bases")

async def list_knowledge_bases(request: Request, agent_id: str) -> dict:

    try:

        tenant_id, _ = get_tenant_and_user(request)



        async with AsyncSessionLocal() as db:

            service = KnowledgeBaseService(db, tenant_id)

            result = await service.list_knowledge_source(agent_id)

            

            if not result.get("success"):

                status_code = result.get("meta", {}).get("status_code", 400)

                raise HTTPException(status_code=status_code, detail=result.get("error"))



            return result

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error in list_knowledge_bases: {e}")

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")





# ============================================================================

# GOOGLE DRIVE CONNECTOR ENDPOINTS

# ============================================================================



@router.post(

    "/{kb_id}/google-drive/register",

    response_model=dict,

    status_code=status.HTTP_200_OK,

    summary="Register Google Drive Connection",

    description="Register Google Drive credentials and folder configurations for this KB"

)

async def register_google_drive(

    request: Request,

    kb_id: str,

    gd_request: schemas.GoogleDriveRegister

) -> dict:

    try:

        tenant_id, _ = get_tenant_and_user(request)



        async with AsyncSessionLocal() as db:

            from sqlalchemy import select

            from .models import DatabaseConnection

            import uuid

            

            # Check if a connection already exists to update it (upsert)

            query = select(DatabaseConnection).where(

                DatabaseConnection.kb_id == uuid.UUID(kb_id),

                DatabaseConnection.tenant_id == uuid.UUID(tenant_id)

            )

            db_conn_res = await db.execute(query)

            db_conn = db_conn_res.scalar_one_or_none()



            connection_params = {

                "credentials": gd_request.credentials,

                "folder_urls": gd_request.folder_urls or []

            }



            if db_conn:

                db_conn.db_type = "google_drive"

                db_conn.connection_params = connection_params

            else:

                db_conn = DatabaseConnection(

                    tenant_id=uuid.UUID(tenant_id),

                    kb_id=uuid.UUID(kb_id),

                    db_type="google_drive",

                    connection_params=connection_params

                )

                db.add(db_conn)



            await db.commit()

            return format_success(

                {"success": True},

                meta={"message": "Google Drive connection registered successfully"}

            )

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error in register_google_drive: {e}")

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")






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

@router.post(

    "/{kb_id}/google-drive/sync",

    response_model=dict,

    status_code=status.HTTP_200_OK,

    summary="Synchronize Google Drive to Graph",

    description="Crawl Google Drive, download files, generate embeddings, and load them into Neo4j graph"

)

async def sync_google_drive_to_graph(request: Request, kb_id: str, sync_req: Optional[schemas.GoogleDriveSyncRequest] = None) -> dict:

    try:

        tenant_id, _ = get_tenant_and_user(request)



        async with AsyncSessionLocal() as db:

            from sqlalchemy import select

            from .models import DatabaseConnection

            from datetime import datetime

            import uuid

            

            query = select(DatabaseConnection).where(

                DatabaseConnection.kb_id == uuid.UUID(kb_id),

                DatabaseConnection.tenant_id == uuid.UUID(tenant_id),

                DatabaseConnection.db_type == "google_drive"

            )

            res = await db.execute(query)

            db_conn = res.scalar_one_or_none()

            if not db_conn:

                raise HTTPException(status_code=404, detail="No registered Google Drive connection found for this KB")



            connection_params = db_conn.connection_params

            credentials = connection_params.get("credentials", {})

            folder_urls = connection_params.get("folder_urls", [])



            service = KnowledgeBaseService(db, tenant_id)

            file_ids = sync_req.file_ids if sync_req else None
            folder_ids = sync_req.folder_ids if sync_req else None
            result = await service.sync_google_drive_source(
                kb_id=kb_id,
                credentials_dict=credentials,
                folder_urls=folder_urls,
                file_ids=file_ids,
                folder_ids=folder_ids
            )



            if not result.get("success"):

                raise HTTPException(status_code=400, detail=result.get("error"))



            # Update sync status timestamp

            db_conn.last_synced_at = datetime.now()

            await db.commit()



            return result

    except HTTPException:

        raise

    except Exception as e:

        logger.error(f"Error in sync_google_drive_to_graph: {e}")

        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ============================================================================
# SHAREPOINT CONNECTOR ENDPOINTS
# ============================================================================

@router.post(
    "/{kb_id}/sharepoint/register",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Register SharePoint Connection",
    description="Register SharePoint credentials for this KB"
)
async def register_sharepoint(
    request: Request,
    kb_id: str,
    sp_request: schemas.SharePointRegister
) -> dict:
    try:
        tenant_id, _ = get_tenant_and_user(request)
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from .models import DatabaseConnection
            import uuid
            
            query = select(DatabaseConnection).where(
                DatabaseConnection.kb_id == uuid.UUID(kb_id),
                DatabaseConnection.tenant_id == uuid.UUID(tenant_id)
            )
            db_conn_res = await db.execute(query)
            db_conn = db_conn_res.scalar_one_or_none()

            connection_params = {
                "credentials": sp_request.credentials,
                "site_urls": sp_request.site_urls or []
            }

            if db_conn:
                db_conn.db_type = "sharepoint"
                db_conn.connection_params = connection_params
            else:
                db_conn = DatabaseConnection(
                    tenant_id=uuid.UUID(tenant_id),
                    kb_id=uuid.UUID(kb_id),
                    db_type="sharepoint",
                    connection_params=connection_params
                )
                db.add(db_conn)

            await db.commit()
            return format_success(
                {"success": True},
                meta={"message": "SharePoint connection registered successfully"}
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in register_sharepoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get(
    "/{kb_id}/sharepoint/files",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="List SharePoint Files",
    description="List files and folders from the connected SharePoint for selective ingestion."
)
async def list_sharepoint_files(request: Request, kb_id: str, parent_id: Optional[str] = None) -> dict:
    try:
        tenant_id, _ = get_tenant_and_user(request)
        async with AsyncSessionLocal() as db:
            service = KnowledgeBaseService(db, tenant_id)
            return await service.list_sharepoint_directory(kb_id=kb_id, parent_id=parent_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in list_sharepoint_files: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post(
    "/{kb_id}/sharepoint/sync",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Synchronize SharePoint to Graph",
    description="Crawl SharePoint, download files, generate embeddings, and load them into Neo4j graph"
)
async def sync_sharepoint_to_graph(request: Request, kb_id: str, sync_req: Optional[schemas.SharePointSyncRequest] = None) -> dict:
    try:
        tenant_id, _ = get_tenant_and_user(request)

        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from .models import DatabaseConnection
            from datetime import datetime
            import uuid
            
            query = select(DatabaseConnection).where(
                DatabaseConnection.kb_id == uuid.UUID(kb_id),
                DatabaseConnection.tenant_id == uuid.UUID(tenant_id),
                DatabaseConnection.db_type == "sharepoint"
            )
            res = await db.execute(query)
            db_conn = res.scalar_one_or_none()
            if not db_conn:
                raise HTTPException(status_code=404, detail="No registered SharePoint connection found for this KB")

            connection_params = db_conn.connection_params
            credentials = connection_params.get("credentials", {})
            site_urls = connection_params.get("site_urls", [])

            service = KnowledgeBaseService(db, tenant_id)
            file_ids = sync_req.file_ids if sync_req else None
            folder_ids = sync_req.folder_ids if sync_req else None
            result = await service.sync_sharepoint_source(
                kb_id=kb_id,
                credentials_dict=credentials,
                site_urls=site_urls,
                file_ids=file_ids,
                folder_ids=folder_ids
            )

            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error"))

            # Update sync status timestamp
            db_conn.last_synced_at = datetime.now()
            await db.commit()

            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sync_sharepoint_to_graph: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
