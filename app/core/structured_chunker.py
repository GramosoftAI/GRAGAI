import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class StructuredRecord(BaseModel):
    document_type: str
    source_file: str
    group_name: str
    row_index: int
    columns: List[str]
    values: Dict[str, Any]

class StructuredChunk(BaseModel):
    text: str
    metadata: Dict[str, Any]

class StructuredChunker:
    """
    Chunks structured records (like spreadsheet rows or JSON array elements)
    while strictly preserving row boundaries and prepending schema metadata.
    """
    
    @staticmethod
    def chunk(records: List[StructuredRecord], chunk_size: int = 2500, overlap_rows: int = 2) -> List[StructuredChunk]:
        if not records:
            return []
            
        chunks = []
        current_chunk_records = []
        
        # Ensure records are sorted sequentially by index
        sorted_records = sorted(records, key=lambda x: x.row_index)
        
        def format_chunk(rec_list: List[StructuredRecord]) -> Optional[StructuredChunk]:
            if not rec_list:
                return None
                
            first_rec = rec_list[0]
            # Build schema context header
            header = f"Source: {first_rec.source_file} -> {first_rec.group_name}\n"
            header += f"Columns: {', '.join(first_rec.columns)}\n\n"
            
            # Build row text
            row_texts = []
            for rec in rec_list:
                row_str = f"- Row {rec.row_index}: "
                row_str += ", ".join([f"[{k}]: {v}" for k, v in rec.values.items() if str(v).strip()])
                row_texts.append(row_str)
                
            text = header + "\n".join(row_texts)
            
            metadata = {
                "document_type": first_rec.document_type,
                "source_file": first_rec.source_file,
                "sheet": first_rec.group_name,
                "start_row": rec_list[0].row_index,
                "end_row": rec_list[-1].row_index,
                "row_count": len(rec_list),
                "columns": first_rec.columns
            }
            
            return StructuredChunk(text=text, metadata=metadata)
            
        def estimate_len(rec: StructuredRecord) -> int:
            # Approximate character length of a single row string
            return len(", ".join([f"[{k}]: {v}" for k, v in rec.values.items() if str(v).strip()])) + 50
            
        current_len = 0
        header_len = 200 # Fixed buffer for the header string
        
        for rec in sorted_records:
            rec_len = estimate_len(rec)
            
            # If current chunk is getting too big, flush it
            if current_len + rec_len + header_len > chunk_size and current_chunk_records:
                chunk_obj = format_chunk(current_chunk_records)
                if chunk_obj:
                    chunks.append(chunk_obj)
                
                # Establish row-level overlap
                overlap_candidates = current_chunk_records[-overlap_rows:] if overlap_rows > 0 else []
                
                # Safety check: if overlap + new record is too massive, trim overlap
                while overlap_candidates and sum(estimate_len(r) for r in overlap_candidates) + rec_len + header_len > chunk_size:
                    overlap_candidates.pop(0)
                    
                current_chunk_records = overlap_candidates + [rec]
                current_len = sum(estimate_len(r) for r in current_chunk_records)
            else:
                current_chunk_records.append(rec)
                current_len += rec_len
                
        # Flush remainder
        if current_chunk_records:
            chunk_obj = format_chunk(current_chunk_records)
            if chunk_obj:
                chunks.append(chunk_obj)
                
        logger.info(f"StructuredChunker successfully batched {len(records)} records into {len(chunks)} row-aware chunks.")
        return chunks
