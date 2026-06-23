import os
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import pdfplumber
import zipfile
import xml.etree.ElementTree as ET

from ..configs.eval_config import DATASETS_DIR, GROUND_TRUTH_DIR
from ..logs.logger import eval_logger

class DatasetLoader:
    """Loads, scans, and collects metadata and ground truths for the evaluation datasets."""

    @staticmethod
    def scan_datasets() -> List[Dict[str, Any]]:
        """Scans the datasets directory and registers files with their ground truths."""
        eval_logger.info(f"Scanning datasets directory: {DATASETS_DIR}")
        dataset_list = []

        subdirs = {
            "pdf": "*.pdf",
            "urls": "*.txt",
            "excel": "*.*", # .xlsx, .xls, .csv
            "docx": "*.docx",
            "markdown": "*.*", # .md, .markdown
            "raw_text": "*.txt"
        }

        for source_type, glob_pattern in subdirs.items():
            dir_path = DATASETS_DIR / source_type
            if not dir_path.exists():
                continue

            for file_path in dir_path.iterdir():
                if file_path.is_dir() or file_path.name.startswith("."):
                    continue
                
                # Filter by extension logic
                ext = file_path.suffix.lower()
                if source_type == "excel" and ext not in [".xlsx", ".xls", ".csv"]:
                    continue
                if source_type == "markdown" and ext not in [".md", ".markdown"]:
                    continue
                if source_type == "pdf" and ext != ".pdf":
                    continue
                if source_type == "docx" and ext != ".docx":
                    continue
                if source_type in ["urls", "raw_text"] and ext != ".txt":
                    continue

                file_size = file_path.stat().st_size
                base_name = file_path.stem

                # Look for ground truth
                ent_path = GROUND_TRUTH_DIR / "entities" / f"{base_name}.json"
                rel_path = GROUND_TRUTH_DIR / "relationships" / f"{base_name}.json"

                expected_entities = 0
                expected_relationships = 0

                if ent_path.exists():
                    try:
                        with open(ent_path, "r", encoding="utf-8") as f:
                            expected_entities = len(json.load(f))
                    except Exception as e:
                        eval_logger.error(f"Failed to read entities ground truth for {base_name}: {e}")

                if rel_path.exists():
                    try:
                        with open(rel_path, "r", encoding="utf-8") as f:
                            expected_relationships = len(json.load(f))
                    except Exception as e:
                        eval_logger.error(f"Failed to read relationships ground truth for {base_name}: {e}")

                # Determine metrics (Pages/Rows)
                pages_or_rows = 0
                char_count = 0
                
                try:
                    pages_or_rows, char_count = DatasetLoader.get_file_stats(file_path, source_type)
                except Exception as e:
                    eval_logger.warning(f"Error gathering file stats for {file_path.name}: {e}")

                dataset_list.append({
                    "source_type": source_type.upper(),
                    "file_name": file_path.name,
                    "file_path": str(file_path),
                    "size": file_size,
                    "pages_or_rows": pages_or_rows,
                    "characters": char_count,
                    "expected_entities": expected_entities,
                    "expected_relationships": expected_relationships,
                    "entities_gt_path": str(ent_path) if ent_path.exists() else None,
                    "relationships_gt_path": str(rel_path) if rel_path.exists() else None
                })
        
        eval_logger.info(f"Registered {len(dataset_list)} files for evaluation.")
        return dataset_list

    @staticmethod
    def get_file_stats(file_path: Path, source_type: str) -> tuple[int, int]:
        """Calculates page/row count and character count for a file."""
        ext = file_path.suffix.lower()
        
        if source_type == "pdf" or ext == ".pdf":
            with pdfplumber.open(str(file_path)) as pdf:
                pages = len(pdf.pages)
                chars = sum(len(page.extract_text() or "") for page in pdf.pages)
            return pages, chars

        elif source_type == "docx" or ext == ".docx":
            with zipfile.ZipFile(str(file_path)) as docx:
                xml_content = docx.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                text = "".join(elem.text or "" for elem in tree.iter() if elem.tag.endswith('t'))
                return 1, len(text)

        elif source_type == "excel" or ext in [".xlsx", ".xls", ".csv"]:
            if ext == ".csv":
                df = pd.read_csv(str(file_path))
            else:
                df = pd.read_excel(str(file_path))
            rows = len(df)
            # Rough char count of everything
            chars = int(df.astype(str).map(len).sum().sum())
            return rows, chars

        else:
            # Text, Markdown, URLs text
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = len(text.splitlines())
            return lines, len(text)

    @staticmethod
    def load_content(file_path: str, source_type: str) -> str:
        """Reads and extracts full text content of a dataset file."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if source_type == "PDF" or ext == ".pdf":
            with pdfplumber.open(str(path)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)

        elif source_type == "DOCX" or ext == ".docx":
            with zipfile.ZipFile(str(path)) as docx:
                xml_content = docx.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                return "".join(elem.text or "" for elem in tree.iter() if elem.tag.endswith('t'))

        elif source_type == "EXCEL" or ext in [".xlsx", ".xls", ".csv"]:
            # Excel files are usually loaded via specialized CSV/Excel loaders, 
            # but for raw text pipeline evaluation we can dump them to CSV string
            if ext == ".csv":
                df = pd.read_csv(str(path))
            else:
                df = pd.read_excel(str(path))
            return df.to_csv(index=False)

        else:
            # TEXT, MARKDOWN, URLS
            return path.read_text(encoding="utf-8", errors="ignore")
