import logging
import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid

from app.core.database import AsyncSessionLocal
from .service import JobService
from app.modules.knowledge_bases.service import KnowledgeBaseService
from app.modules.agents.service import AgentService
from app.modules.knowledge_bases.schemas import KBCreate
from app.core.pdf_extractor import PDFExtractor
from app.core.llm.deepinfra_llm import DeepInfraLLMClient

logger = logging.getLogger(__name__)

async def run_pdf_ingestion_job(
    tenant_id: str,
    user_id: str,
    agent_id: str,
    job_id: str,
    filename: str,
    content: bytes
):
    """
    Background task for extracting and ingesting a PDF.
    Updates the ProcessingJob table with progress.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Important: set tenant context!
            await db.execute(
                text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
                {"tenant_id": str(tenant_id)}
            )
            
            job_service = JobService(db, tenant_id)
            
            # Update status to processing
            await job_service.update_job_progress(job_id, status="processing", progress=5, current_step="Starting PDF Extraction (OCR)")
            
            # Step 1: PDF Extraction (OCR)
            logger.info(f"Job {job_id}: Starting PDF extraction for {filename}")
            try:
                document_text = await PDFExtractor.extract(
                    pdf_bytes=content,
                    filename=filename,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                )
            except Exception as e:
                logger.error(f"Job {job_id}: PDF extraction failed: {e}")
                await job_service.update_job_progress(job_id, status="failed", progress=5, current_step="PDF Extraction", error_message=f"Failed to extract text from PDF: {str(e)}")
                return
                
            if not document_text.strip():
                await job_service.update_job_progress(job_id, status="failed", progress=5, current_step="PDF Extraction", error_message="PDF appears to be empty or contains no extractable text.")
                return
                
            # Classify Document Type
            await job_service.update_job_progress(job_id, status="processing", progress=15, current_step="Classifying Document Type")
            llm_client = DeepInfraLLMClient()
            prompt = f"Analyze the first 2000 characters of this document and classify its type. Valid types are: PRICE_LIST, INVOICE, QUOTATION, PURCHASE_ORDER, STOCK_REPORT, FINANCIAL_STATEMENT, GENERAL. Return ONLY the type string, nothing else.\n\nDOCUMENT START:\n{document_text[:2000]}"
            document_type = await llm_client.generate(prompt=prompt, system_prompt="You are a document classifier. Return only the exact category string.", temperature=0.0, max_tokens=15)
            document_type = document_type.strip()
            if document_type not in ["PRICE_LIST", "INVOICE", "QUOTATION", "PURCHASE_ORDER", "STOCK_REPORT", "FINANCIAL_STATEMENT", "GENERAL"]:
                document_type = "GENERAL"
            logger.info(f"Classified document as: {document_type}")
                
            await job_service.update_job_progress(job_id, status="processing", progress=25, current_step="Extracting Structured Tables")
            
            # Step 1.5: Table Extraction
            logger.info(f"Job {job_id}: Extracting structured tables")
            table_rows = await PDFExtractor.extract_tables_to_json(pdf_bytes=content)
            
            await job_service.update_job_progress(job_id, status="processing", progress=40, current_step="Creating Knowledge Base Entry")

            # Step 2: Create KB Entry
            from app.core.s3 import S3StorageService
            s3_service = S3StorageService()
            s3_url = s3_service.get_s3_url(str(tenant_id), filename)

            kb_service = KnowledgeBaseService(db, tenant_id)
            kb_request = KBCreate(
                name=f"PDF: {filename}",
                description=f"Automated PDF upload source (Gdocz extraction)",
                agent_id=uuid.UUID(agent_id),
                source="pdf_upload",
                document_type=document_type,
                s3_path=s3_url
            )
            
            kb_result = await kb_service.create_knowledge_base(user_id, kb_request)
            if not kb_result.get("success"):
                await job_service.update_job_progress(job_id, status="failed", progress=45, current_step="Creating Knowledge Base Entry", error_message="Failed to create Knowledge Base tracking row in database.")
                return
                
            kb_id = str(kb_result["data"]["kb"].id)
            
            # Step 2.5: Save Table Rows
            if table_rows:
                await kb_service.save_table_rows(kb_id, table_rows)
            
            # Store parsed content in S3
            parsed_url = None
            try:
                is_html = getattr(document_text, "is_html", False)
                raw_content = getattr(document_text, "raw_html", document_text)
                content_type = "text/html" if is_html else "text/plain"

                parsed_url = await asyncio.to_thread(
                    s3_service.store_parsed_content,
                    str(tenant_id),
                    str(kb_id),
                    raw_content,
                    content_type
                )
            except Exception as e:
                logger.error(f"Job {job_id}: Failed to store parsed content in S3: {e}")

            # Step 3: Ingest Document (Chunking + Embeddings + Neo4j)
            await job_service.update_job_progress(job_id, status="processing", progress=60, current_step="Chunking and Generating Embeddings")
            
            logger.info(f"Job {job_id}: Starting embedding and graph ingestion for {kb_id}")
            ingest_result = await kb_service.ingest_document(
                kb_id, 
                document_text, 
                source=s3_url, 
                s3_path=s3_url,
                parsed_path=parsed_url
            )


            
            if not ingest_result.get("success"):
                error_msg = ingest_result.get("error", "Unknown ingestion error")
                await job_service.update_job_progress(job_id, status="failed", progress=80, current_step="Generating Embeddings", error_message=error_msg)
                return
                
            # Success!
            await job_service.update_job_progress(job_id, status="completed", progress=100, current_step="Complete")
            logger.info(f"Job {job_id}: Successfully completed!")

    except Exception as e:
        logger.error(f"Job {job_id}: Unexpected error: {e}", exc_info=True)
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("SELECT set_config('app.current_tenant', :tenant_id, false)"),
                    {"tenant_id": str(tenant_id)}
                )
                job_service = JobService(db, tenant_id)
                await job_service.update_job_progress(job_id, status="failed", error_message=f"Internal Server Error: {str(e)}")
        except Exception as rollback_err:
            logger.error(f"Job {job_id}: Failed to update job status on error: {rollback_err}")
