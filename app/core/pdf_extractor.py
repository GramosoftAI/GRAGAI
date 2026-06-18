"""PDF Extraction Service  Gdocz SDK (Primary) + pdfplumber (Fallback)

ARCHITECTURE:
    Primary:  Gdocz SDK  Converts PDF to clean markdown via cloud API
    Fallback: pdfplumber + AI-OCR  Local extraction with Vision LLM for scans

STRATEGY:
    1. Try Gdocz SDK first (best quality, handles complex PDFs + scans)
    2. If Gdocz fails (API down, quota exceeded), fall back to pdfplumber
    3. Clean the raw markdown into GraphRAG-friendly plain text
    4. Return clean text ready for chunking + embedding

MARKDOWN CLEANING:
    The raw markdown from Gdocz contains formatting artifacts that are
    noise for embedding models. We clean:
    - Headers (## Title  Title)
    - Bold/Italic (**text**, *text*  text)
    - Links ([text](url)  text)
    - Images (![alt](url)  removed)
    - Tables (| col |  flattened to sentences)
    - Code blocks (```code```  code)
    - HTML tags (<tag>  removed)
    - Excessive whitespace normalized

NON-BREAKING:
    This module is imported ONLY by the agent/KB routes that handle PDF ingestion.
    No existing modules are modified. The extraction function returns plain text
    which plugs directly into the existing ingest_document() pipeline.
"""

import logging
import re
import io
import asyncio
import tempfile
import os
from typing import Optional

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PDFExtractor:
    """
    PDF content extraction with dual-layer strategy:
    1. Gdocz SDK (primary)  Cloud-based, high-quality PDF  Markdown
    2. pdfplumber (fallback)  Local extraction with AI-OCR for scans

    Usage:
        text = await PDFExtractor.extract(pdf_bytes, filename="doc.pdf")
    """

    @staticmethod
    async def extract_tables_to_json(pdf_bytes: bytes) -> list:
        """
        Extract structured tables from PDF using pdfplumber into JSONB friendly format.
        Returns a list of dicts:
        [{
            "page_number": 1,
            "table_index": 0,
            "row_index": 0,
            "row_data": {"Part Number": "123", "Price": "5000"}
        }]
        """
        import pdfplumber
        import io
        
        extracted_tables = []
        try:
            # Run blocking pdfplumber open and extraction in a thread pool
            def _extract() -> list:
                results = []
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    for page_idx, page in enumerate(pdf.pages):
                        tables = page.extract_tables()
                        for table_idx, table in enumerate(tables):
                            if not table or len(table) < 2:
                                continue
                                
                            # Extract headers
                            headers = table[0]
                            headers = [str(h).strip().replace('\n', ' ') if h else f"col_{i}" for i, h in enumerate(headers)]
                            
                            # Ensure unique headers if there are duplicates
                            unique_headers = []
                            for i, h in enumerate(headers):
                                if h in unique_headers:
                                    unique_headers.append(f"{h}_{i}")
                                else:
                                    unique_headers.append(h)
                            headers = unique_headers

                            # Extract rows
                            for row_idx, row in enumerate(table[1:]):
                                row_data = {}
                                has_data = False
                                for i, cell in enumerate(row):
                                    if i < len(headers):
                                        col_name = headers[i]
                                        cell_val = str(cell).strip().replace('\n', ' ') if cell else ""
                                        row_data[col_name] = cell_val
                                        if cell_val:
                                            has_data = True
                                
                                # Only append if the row has actual data
                                if has_data:
                                    results.append({
                                        "page_number": page_idx + 1,
                                        "table_index": table_idx,
                                        "row_index": row_idx,
                                        "row_data": row_data
                                    })
                return results

            loop = asyncio.get_event_loop()
            extracted_tables = await loop.run_in_executor(None, _extract)
            logger.info(f" Extracted {len(extracted_tables)} structured table rows from PDF")
            
        except Exception as e:
            logger.error(f" Failed to extract tables: {e}", exc_info=True)
            
        return extracted_tables

    @staticmethod
    async def extract(
        pdf_bytes: bytes,
        filename: str = "document.pdf",
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> str:
        """
        Extract text from PDF bytes using the best available method.

        FLOW:
        1. Try Gdocz SDK (cloud API, handles complex/scanned PDFs)
        2. If Gdocz fails  fall back to pdfplumber + AI-OCR
        3. Clean raw output into GraphRAG-friendly text
        4. Return cleaned text ready for chunking

        Args:
            pdf_bytes: Raw PDF file content
            filename: Original filename (for logging)
            tenant_id: For billing/tracking
            agent_id: For billing/tracking

        Returns:
            Cleaned text string ready for ingestion pipeline

        Raises:
            ValueError: If no text could be extracted from the PDF
        """
        logger.info(f" PDF Extraction starting: {filename} ({len(pdf_bytes)} bytes)")

        extracted_text = ""

        # ============= PRIMARY: GDOCZ SDK =============
        if settings.gdocz_api_key:
            try:
                extracted_text = await PDFExtractor._extract_gdocz(
                    pdf_bytes, filename
                )
                if extracted_text and extracted_text.strip():
                    logger.info(
                        f" Gdocz extraction success: {filename} "
                        f"({len(extracted_text)} chars raw markdown)"
                    )
                    # Clean markdown  GraphRAG-friendly text
                    cleaned = PDFExtractor._clean_markdown_for_rag(extracted_text)
                    logger.info(
                        f" Cleaned for RAG: {len(cleaned)} chars "
                        f"(from {len(extracted_text)} raw)"
                    )
                    return cleaned
                else:
                    logger.warning(
                        f" Gdocz returned empty result for {filename}. "
                        f"Falling back to pdfplumber."
                    )
            except Exception as e:
                logger.warning(
                    f" Gdocz extraction failed for {filename}: {e}. "
                    f"Falling back to pdfplumber."
                )
        else:
            logger.info(
                " GDOCZ_API_KEY not configured. Using pdfplumber directly."
            )

        # ============= FALLBACK: PDFPLUMBER + AI-OCR =============
        try:
            extracted_text = await PDFExtractor._extract_pdfplumber(
                pdf_bytes, filename, tenant_id, agent_id
            )
            if extracted_text and extracted_text.strip():
                logger.info(
                    f" pdfplumber extraction success: {filename} "
                    f"({len(extracted_text)} chars)"
                )
                return extracted_text
        except Exception as e:
            logger.error(f" pdfplumber also failed for {filename}: {e}")

        # ============= BOTH FAILED =============
        raise ValueError(
            f"Could not extract text from PDF: {filename}. "
            f"Both Gdocz SDK and pdfplumber failed."
        )

    # ========================================================================
    # PRIMARY: GDOCZ SDK
    # ========================================================================

    @staticmethod
    async def _extract_gdocz(pdf_bytes: bytes, filename: str) -> str:
        """
        Extract PDF content using Gdocz SDK (cloud API).

        The SDK is synchronous, so we run it in a thread pool executor
        to avoid blocking the async event loop.

        Args:
            pdf_bytes: Raw PDF bytes
            filename: Original filename

        Returns:
            Raw markdown string from Gdocz
        """
        def _sync_gdocz_convert(pdf_data: bytes, fname: str) -> str:
            """Synchronous wrapper for Gdocz SDK (runs in thread pool)."""
            from gdocz_sdk import GdoczaiClient, ConvertOptions

            client = GdoczaiClient(api_key=settings.gdocz_api_key)

            options = ConvertOptions(
                mode="chandra",  # Best quality extraction mode
            )

            # Write bytes to a temp file (SDK expects file path)
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".pdf", delete=False, prefix="graphmind_"
                ) as tmp:
                    tmp.write(pdf_data)
                    tmp_path = tmp.name

                logger.debug(f"Gdocz converting: {tmp_path}")
                result = client.convert(tmp_path, options=options)

                if isinstance(result, dict):
                    return result.get("markdown", "")
                else:
                    return getattr(result, "markdown", "") or ""
            finally:
                # Clean up temp file
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

        # Run synchronous SDK call in thread pool (non-blocking)
        loop = asyncio.get_event_loop()
        raw_markdown = await loop.run_in_executor(
            None, _sync_gdocz_convert, pdf_bytes, filename
        )

        return raw_markdown

    # ========================================================================
    # FALLBACK: PDFPLUMBER + AI-OCR
    # ========================================================================

    @staticmethod
    async def _extract_pdfplumber(
        pdf_bytes: bytes,
        filename: str,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> str:
        """
        Fallback extraction using pdfplumber with AI-OCR for scanned pages.

        Args:
            pdf_bytes: Raw PDF bytes
            filename: Original filename
            tenant_id: For AI-OCR billing
            agent_id: For AI-OCR billing

        Returns:
            Extracted text string
        """
        try:
            import pdfplumber
        except ImportError:
            raise ImportError(
                "pdfplumber is not installed. "
                "Run: pip install pdfplumber"
            )

        document_text = ""

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    document_text += text + "\n\n"
                else:
                    # OCR FALLBACK: Page is likely a scan/image
                    logger.info(
                        f" Empty page {page.page_number} in {filename}. "
                        f"Attempting AI-OCR..."
                    )
                    try:
                        from .llm.deepinfra_llm import get_llm_client

                        img = page.to_image(resolution=300).original
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format="JPEG")
                        img_bytes = img_byte_arr.getvalue()

                        llm = await get_llm_client()
                        ocr_text = await llm.vision_ocr(
                            img_bytes,
                            tenant_id=tenant_id,
                            agent_id=agent_id,
                        )

                        if ocr_text:
                            document_text += (
                                f"[OCR Page {page.page_number}]:\n"
                                f"{ocr_text}\n\n"
                            )
                            logger.info(
                                f" AI-OCR success for page {page.page_number}"
                            )
                    except Exception as ocr_err:
                        logger.error(
                            f" AI-OCR failed for page {page.page_number}: {ocr_err}"
                        )
                        # Continue  other pages may have text

        return document_text

    # ========================================================================
    # MARKDOWN CLEANING (GraphRAG-Friendly)
    # ========================================================================

    @staticmethod
    def _clean_markdown_for_rag(raw_markdown: str) -> str:
        """
        Clean raw markdown into GraphRAG-friendly plain text.

        WHAT WE KEEP:
        - All actual content text (sentences, paragraphs)
        - Header text (as plain text, preserving structure)
        - Table content (flattened to readable lines)
        - Code content (without backtick fences)
        - List items (as plain sentences)

        WHAT WE REMOVE:
        - Markdown formatting symbols (**, *, `, #)
        - Image references (![alt](url))
        - URL links (keep link text, remove URL)
        - HTML tags
        - Horizontal rules (---, ***)
        - Excessive whitespace / empty lines

        WHY: Embedding models (BAAI/bge-large) perform better on
        clean, natural language text without formatting noise.

        Args:
            raw_markdown: Raw markdown string from PDF extraction

        Returns:
            Cleaned plain text optimized for chunking + embedding
        """
        if not raw_markdown:
            return ""

        text = raw_markdown

        # ============= STEP 1: REMOVE IMAGES =============
        # ![alt text](url) or ![](url)
        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)

        # ============= STEP 2: CONVERT LINKS TO TEXT =============
        # [link text](url)  link text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # ============= STEP 3: REMOVE CODE FENCES =============
        # ```language\ncode\n```  code
        text = re.sub(r"```[\w]*\n?", "", text)

        # ============= STEP 4: REMOVE HTML TAGS =============
        text = re.sub(r"<[^>]+>", "", text)

        # ============= STEP 5: CONVERT HEADERS TO PLAIN TEXT =============
        # ## Header  Header (keep the text, remove #)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # ============= STEP 6: REMOVE FORMATTING =============
        # Bold: **text** or __text__  text
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)

        # Italic: *text* or _text_  text
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", text)

        # Strikethrough: ~~text~~  text
        text = re.sub(r"~~([^~]+)~~", r"\1", text)

        # Inline code: `text`  text
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # ============= STEP 7: CLEAN TABLE FORMATTING (SKIPPED) =============
        # We now preserve Markdown tables for Table-Aware chunking.
        # Tables will remain as | Col1 | Col2 | formats.

        # ============= STEP 8: CLEAN LIST MARKERS =============
        # - item or * item or  item  item
        text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
        # 1. item  item (Only 1-2 digit numbers to avoid stripping years like 2023.)
        text = re.sub(r"^[\s]*\d{1,2}\.\s+", "", text, flags=re.MULTILINE)

        # ============= STEP 9: REMOVE HORIZONTAL RULES =============
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        # ============= STEP 10: NORMALIZE WHITESPACE =============
        # Replace multiple blank lines with single blank line
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in text.splitlines()]

        # Remove completely empty lines at start/end
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()

        # Rejoin with clean line breaks
        text = "\n".join(lines)

        # Final trim
        text = text.strip()

        logger.debug(
            f"Markdown cleaned: {len(raw_markdown)} chars  {len(text)} chars "
            f"(removed {len(raw_markdown) - len(text)} chars of formatting)"
        )

        return text
