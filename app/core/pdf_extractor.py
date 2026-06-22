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


class ExtractedText(str):
    def __new__(cls, clean_text: str, raw_html: str, is_html: bool = False):
        obj = super().__new__(cls, clean_text)
        obj.raw_html = raw_html
        obj.is_html = is_html
        return obj


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
    ) -> ExtractedText:
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
            ExtractedText: Subclass of str containing cleaned text, with .raw_html and .is_html properties.

        Raises:
            ValueError: If no text could be extracted from the PDF
        """
        logger.info(f" PDF Extraction starting: {filename} ({len(pdf_bytes)} bytes)")

        extracted_text = ""

        # ============= PRIMARY: GDOCZ SDK =============
        if settings.gdocz_api_key:
            try:
                raw_html = await PDFExtractor._extract_gdocz(
                    pdf_bytes, filename
                )
                if raw_html and raw_html.strip():
                    logger.info(
                        f" Gdocz extraction success: {filename} "
                        f"({len(raw_html)} chars raw HTML/markdown)"
                    )
                    # Clean page markers if present in HTML
                    raw_html_clean = re.sub(r"<---- Page \d+ ---->\r?\n?", "", raw_html)
                    # Clean markdown / HTML for RAG
                    cleaned = PDFExtractor._clean_markdown_for_rag(raw_html_clean)
                    logger.info(
                        f" Cleaned for RAG: {len(cleaned)} chars "
                        f"(from {len(raw_html_clean)} raw)"
                    )
                    return ExtractedText(cleaned, raw_html_clean, is_html=True)
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
                return ExtractedText(extracted_text, extracted_text, is_html=False)
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
        Extract PDF content using Gdocz OCR server.
        """
        def _sync_gdocz_convert(pdf_data: bytes, fname: str) -> str:
            import requests
            url = "https://gdocz.gramopro.ai/ocr/ocr/pdf"
            headers = {"X-API-Key": settings.gdocz_api_key}
            files = {"file": (fname, pdf_data, "application/pdf")}
            
            # Smart determination of document type
            doc_type = "GENERAL"
            fname_lower = fname.lower()
            if "resume" in fname_lower or "cv" in fname_lower or "profile" in fname_lower:
                doc_type = "resume"
            elif "invoice" in fname_lower or "bill" in fname_lower:
                doc_type = "INVOICE"
            elif "quote" in fname_lower or "quotation" in fname_lower:
                doc_type = "QUOTATION"
            elif "price" in fname_lower:
                doc_type = "PRICE_LIST"

            data = {
                "model": "chandra",
                "output_format": "html",
                "document_type": doc_type
            }

            logger.info(f"Calling Gdocz `/ocr/pdf` directly with document_type: {doc_type}")
            response = requests.post(url, files=files, data=data, headers=headers, timeout=600)
            
            if response.status_code != 200:
                raise ValueError(f"Gdocz API returned status code {response.status_code}: {response.text}")
                
            res_json = response.json()
            if not res_json.get("success"):
                raise ValueError(f"Gdocz API error: {res_json.get('error')}")
                
            return res_json.get("markdown", "")

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

        # ============= STEP 7: REMOVE MARKDOWN TABLES =============
        # We now extract tables separately into structured rows. We do NOT want 
        # flattened tables polluting the unstructured semantic vector space.
        # Matches typical markdown tables like | Col1 | Col2 |
        text = re.sub(r"^(?:\|[^\n]+\|\r?\n)+", "", text, flags=re.MULTILINE)

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

    @staticmethod
    async def extract_structured_entities(text: str) -> dict:
        """
        Phase 4: Universal Entity Extraction.
        LLM identifies candidate entities, system extracts exact source spans.
        """
        from .llm.deepinfra_llm import DeepInfraLLMClient
        import json
        from .entity_registry import ENTITY_TYPES, resolve_entity_type
        
        try:
            client = DeepInfraLLMClient()
            
            identifier_hints = []
            for canonical, aliases in ENTITY_TYPES.items():
                identifier_hints.append(f"{canonical} (aliases: {', '.join(aliases[:3])})")
            identifier_hint_str = "\n            ".join(identifier_hints)
            
            prompt = f"""
            Identify business identifiers and sections in the text.
            Look for these identifiers and their aliases:
            {identifier_hint_str}
            Plus standard ones like ADDRESS, EMAIL, PHONE.
            Sections include: Place of Delivery, Billing Address, Shipping Address, Customer Details.
            
            Return exactly in JSON format:
            {{
                "identifiers": [
                    {{"type": "GSTIN", "candidate_value": "33AAACS8779D1Z7", "confidence": 0.99}}
                ],
                "sections": [
                    {{"name": "Place of Delivery", "content": {{"address": "...", "gstin": "..."}}, "confidence": 0.95}}
                ]
            }}
            
            TEXT: {text}
            """
            
            response = await client.generate(
                prompt=prompt,
                system_prompt="You are an extraction system.",
                temperature=0.0,
                max_tokens=1000
            )
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {"identifiers": [], "sections": []}
                
            data = json.loads(json_match.group(0))
            
            results = {"identifiers": [], "sections": []}
            
            # System extracts exact spans for identifiers to avoid hallucination
            for ident in data.get("identifiers", []):
                cand = str(ident.get("candidate_value", ""))
                raw_type = ident.get("type", "")
                if cand and raw_type:
                    canonical_type = resolve_entity_type(raw_type)
                    # Find exact span in original text
                    idx = text.find(cand)
                    if idx != -1:
                        results["identifiers"].append({
                            "type": canonical_type,
                            "value": text[idx:idx+len(cand)],
                            "start_offset": idx,
                            "end_offset": idx+len(cand),
                            "source_text": text[max(0, idx-20):min(len(text), idx+len(cand)+20)],
                            "confidence": float(ident.get("confidence", 1.0))
                        })
            
            for sec in data.get("sections", []):
                if isinstance(sec.get("content"), dict):
                    results["sections"].append({
                        "name": sec.get("name", ""),
                        "content": sec.get("content", {})
                    })
                
            return results
        except Exception as e:
            logger.error(f"Structured extraction failed: {e}")
            return {"identifiers": [], "sections": []}
