import time
import uuid
import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge_bases.service import KnowledgeBaseService
from app.modules.knowledge_bases.schemas import KBCreate
from app.core.pdf_extractor import PDFExtractor
from app.modules.knowledge_bases.services.scraper_service import ScraperService
from ..configs.eval_config import TEST_TENANT_ID, TEST_AGENT_ID, TEST_USER_ID
from ..logs.logger import eval_logger

class IngestionAuditor:
    """Audits the ingestion stage: parsing, processing time, chunking, and metadata extraction."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = KnowledgeBaseService(db, TEST_TENANT_ID)

    async def create_eval_kb(self, kb_name: str) -> str:
        """Creates a temporary knowledge base for an evaluation run."""
        kb_req = KBCreate(
            name=kb_name,
            description="Evaluation Temporary KB",
            agent_id=uuid.UUID(TEST_AGENT_ID),
            source="user_upload"
        )
        res = await self.service.create_knowledge_base(TEST_USER_ID, kb_req)
        if not res.get("success"):
            raise RuntimeError(f"Failed to create evaluation KB: {res.get('error')}")
        
        kb_id = str(res["data"]["kb"].id)
        eval_logger.info(f"Created temporary Evaluation KB with ID: {kb_id}")
        return kb_id

    async def clean_eval_kb(self, kb_id: str):
        """Cleans up the temporary evaluation knowledge base."""
        eval_logger.info(f"Tearing down temporary Evaluation KB: {kb_id}")
        await self.service.delete_kb(kb_id, TEST_USER_ID)

    async def audit_file(self, kb_id: str, file_info: dict) -> dict:
        """Ingests a file and measures metrics for parse status, time, and chunks."""
        source_type = file_info["source_type"]
        file_name = file_info["file_name"]
        file_path = file_info["file_path"]

        eval_logger.info(f"Auditing Ingestion for {file_name} [{source_type}]...")
        
        t0 = time.time()
        parse_success = False
        chunks_created = 0
        metadata_count = 0
        error_msg = None
        text = ""

        try:
            # 1. Parsing and Extraction Layer
            if source_type == "PDF":
                file_bytes = Path(file_path).read_bytes()
                text = await PDFExtractor.extract(
                    file_bytes, file_name, tenant_id=TEST_TENANT_ID, agent_id=TEST_AGENT_ID
                )
                parse_success = bool(text.strip())

            elif source_type == "URL":
                url_to_scrape = Path(file_path).read_text(encoding="utf-8").strip()
                documents = await ScraperService.extract_website_content(url=url_to_scrape)
                text = "\n\n".join(doc["content"] for doc in documents) if documents else ""
                parse_success = bool(text.strip())

            elif source_type == "DOCX":
                file_bytes = Path(file_path).read_bytes()
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx:
                    xml_content = docx.read('word/document.xml')
                    tree = ET.fromstring(xml_content)
                    text = "".join(elem.text or "" for elem in tree.iter() if elem.tag.endswith('t'))
                parse_success = bool(text.strip())

            elif source_type == "EXCEL":
                # Excel file triggers custom parser
                file_bytes = Path(file_path).read_bytes()
                res = await self.service.ingest_excel_or_csv(
                    kb_id=kb_id, file_bytes=file_bytes, filename=file_name
                )
                parse_success = res.get("success", False)
                if parse_success:
                    chunks_created = res.get("data", {}).get("chunks_created", 0)
                    metadata_count = res.get("data", {}).get("entities_extracted", 0)
                else:
                    error_msg = res.get("error", "Excel parser failed")

            else:
                # Raw Text & Markdown
                text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                parse_success = bool(text.strip())

            # 2. Ingestion and Chunking Layer (for non-Excel)
            if source_type != "EXCEL":
                if parse_success and text.strip():
                    res = await self.service.ingest_document(
                        kb_id=kb_id, document_text=text, source=file_name
                    )
                    ingest_success = res.get("success", False)
                    if ingest_success:
                        chunks_created = res.get("data", {}).get("chunks_created", 0)
                        # Metadata count is entities extracted plus triplets if any
                        metadata_count = (
                            res.get("data", {}).get("entities_extracted", 0) + 
                            res.get("data", {}).get("triplets_extracted", 0)
                        )
                    else:
                        parse_success = False
                        error_msg = res.get("error", "Ingestion/chunking failed")
                else:
                    error_msg = "Parser returned empty text"

        except Exception as e:
            eval_logger.error(f"Failed to ingest {file_name}: {e}", exc_info=True)
            parse_success = False
            error_msg = str(e)

        duration = time.time() - t0
        status = "PASS" if parse_success else "FAIL"
        
        # Calculate quality score (simple parsing and chunk validation)
        quality_score = 1.0 if status == "PASS" and chunks_created > 0 else 0.0

        eval_logger.info(
            f"Ingested {file_name}: Status={status}, Chunks={chunks_created}, "
            f"Metadata={metadata_count}, Time={duration:.2f}s, Score={quality_score*100}%"
        )

        return {
            "source_type": source_type,
            "file_name": file_name,
            "status": status,
            "chunk_count": chunks_created,
            "metadata_count": metadata_count,
            "processing_time": duration,
            "score": quality_score,
            "error_msg": error_msg
        }
