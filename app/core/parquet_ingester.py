import polars as pl
import os
import logging
import time
import json
from typing import Optional, List

logger = logging.getLogger(__name__)

class ParquetIngester:
    """
    Enterprise-grade ingestion layer for 1M+ row datasets.
    Safely streams large CSVs or reads massive Excel files using memory-efficient Calamine,
    and writes them out as chunked, compressed Parquet files for DuckDB querying.
    """
    @staticmethod
    def _clean_and_sanitize_sheet(df: pl.DataFrame, sheet_name: Optional[str] = None) -> pl.DataFrame:
        if df.is_empty():
            return df
        # Cast all columns to String to prevent mixed-type schema panics on write
        df = df.cast(pl.String)
        
        # Automatic Header Offset / Multi-row Header Cleaner
        unnamed_cols = [c for c in df.columns if '__UNNAMED__' in c.upper() or c.strip() == '' or c.lower().startswith('unnamed')]
        if len(unnamed_cols) >= 2 and len(df) > 1:
            for row_idx in range(min(3, len(df))):
                row_vals = [str(df[c][row_idx] or '').strip() for c in df.columns]
                non_empty = [v for v in row_vals if v and not v.startswith('__UNNAMED__') and not v.lower().startswith('unnamed')]
                if len(non_empty) >= len(df.columns) * 0.4:
                    new_headers = []
                    seen = {}
                    for i, c in enumerate(df.columns):
                        val = str(df[c][row_idx] or '').strip()
                        if not val or val.startswith('__UNNAMED__'):
                            val = c.strip() if not c.startswith('__UNNAMED__') else f"Column_{i+1}"
                        val = val.replace('\n', ' ').strip()
                        if val in seen:
                            seen[val] += 1
                            val = f"{val}_{seen[val]}"
                        else:
                            seen[val] = 1
                        new_headers.append(val)
                    data_df = df.slice(row_idx + 1)
                    data_df.columns = new_headers
                    df = data_df
                    break

        # Sanitize column names: strip trailing dots, newlines, and excess whitespace
        sanitized_cols = []
        seen_cols = {}
        for c in df.columns:
            clean_c = str(c).replace('\n', ' ').strip().rstrip('.').strip()
            if not clean_c:
                clean_c = "Column"
            if clean_c in seen_cols:
                seen_cols[clean_c] += 1
                clean_c = f"{clean_c}_{seen_cols[clean_c]}"
            else:
                seen_cols[clean_c] = 1
            sanitized_cols.append(clean_c)
        df.columns = sanitized_cols
        
        if sheet_name:
            df = df.with_columns(pl.lit(str(sheet_name)).alias("_sheet_name"))
        return df

    @staticmethod
    def ingest_to_parquet(file_path: str, output_dir: str = "data/parquet", dataset_name: Optional[str] = None) -> tuple[Optional[str], dict]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found.")
            
        # Ensure output dir is relative to the project root, or absolute
        if not os.path.isabs(output_dir):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, output_dir)
            
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.basename(file_path)
        name_without_ext = dataset_name or os.path.splitext(base_name)[0]
        
        # PRODUCTION FIX: Parquet File Lock Contention (Versioning)
        # We append a timestamp so active queries on older files are never violently locked out.
        timestamp = int(time.time())
        versioned_filename = f"{name_without_ext}_{timestamp}.parquet"
        output_path = os.path.join(output_dir, versioned_filename)
        
        logger.info(f"Starting memory-safe versioned ingestion for {file_path}")
        
        try:
            sheet_filenames = []
            registry_sheets = {}
            
            if file_path.lower().endswith('.csv'):
                # Automatically detect separator (comma or tab) by inspecting the first line
                separator = ","
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        first_line = f.readline()
                        if "\t" in first_line and first_line.count("\t") > first_line.count(","):
                            separator = "\t"
                            logger.info(f"Detected tab delimiter for {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to auto-detect delimiter: {e}")
                    
                # PRODUCTION FIX: Schema Evolution (Dirty Data)
                # infer_schema_length=0 forces all columns to String (Utf8).
                # DuckDB will handle strict typing/casting at the semantic SQL layer.
                lf = pl.scan_csv(file_path, separator=separator, ignore_errors=True, infer_schema_length=0)
                lf.sink_parquet(output_path, row_group_size=100_000)
                sheet_filenames.append(versioned_filename)
                logger.info(f"Successfully streamed CSV to {output_path}")
                
            elif file_path.lower().endswith(('.xlsx', '.xls')):
                # Excel: Discover and process all worksheets via fastexcel / calamine
                import fastexcel
                try:
                    excel_reader = fastexcel.read_excel(file_path)
                    sheet_names = excel_reader.sheet_names
                except Exception as e:
                    logger.warning(f"fastexcel failed reading sheet names ({e}), falling back to default sheet")
                    sheet_names = [None]
                
                sheet_dfs = []
                for sname in sheet_names:
                    try:
                        raw_sheet_df = pl.read_excel(file_path, sheet_name=sname, engine="calamine") if sname is not None else pl.read_excel(file_path, engine="calamine")
                        if raw_sheet_df.is_empty():
                            continue
                        clean_sheet_df = ParquetIngester._clean_and_sanitize_sheet(raw_sheet_df, sheet_name=sname)
                        if clean_sheet_df.is_empty():
                            continue
                        sheet_dfs.append((sname, clean_sheet_df))
                    except Exception as s_err:
                        logger.warning(f"Failed reading sheet {sname!r} from {file_path}: {s_err}")
                
                if not sheet_dfs:
                    raise ValueError(f"No non-empty sheets found in Excel file {file_path}")
                
                # If only 1 sheet exists
                if len(sheet_dfs) == 1:
                    sname, df = sheet_dfs[0]
                    df.write_parquet(output_path, row_group_size=100_000)
                    sheet_filenames.append(versioned_filename)
                else:
                    # Multi-sheet Excel: Write per-sheet parquets AND a unified combined parquet
                    for sname, df in sheet_dfs:
                        clean_sname = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in str(sname)).strip("_") or "sheet"
                        s_filename = f"{name_without_ext}_{clean_sname}_{timestamp}.parquet"
                        s_path = os.path.join(output_dir, s_filename)
                        df.write_parquet(s_path, row_group_size=100_000)
                        sheet_filenames.append(s_filename)
                        registry_sheets[f"{name_without_ext} - {sname}"] = s_filename
                    
                    # Also write the diagonal concatenated combined parquet
                    all_dfs = [df for _, df in sheet_dfs]
                    combined_df = pl.concat(all_dfs, how="diagonal")
                    combined_df.write_parquet(output_path, row_group_size=100_000)
                    logger.info(f"Successfully converted multi-sheet Excel ({len(sheet_dfs)} sheets) to {output_path} and {len(sheet_filenames)} individual sheet parquets.")
                
            else:
                raise ValueError("Unsupported format. Must be CSV or XLSX.")
                
            # Update the registry to point to the newest active dataset and sheets
            registry_path = os.path.join(output_dir, "active_datasets.json")
            registry = {}
            if os.path.exists(registry_path):
                with open(registry_path, 'r') as f:
                    registry = json.load(f)
            
            registry[name_without_ext] = versioned_filename
            if sheet_filenames:
                registry[f"{name_without_ext}__sheets"] = sheet_filenames
            for k, v in registry_sheets.items():
                registry[k] = v
                
            with open(registry_path, 'w') as f:
                json.dump(registry, f, indent=4)
                
            # Extract categorical registry
            categorical_registry = {}
            try:
                df = pl.read_parquet(output_path)
                for col in df.columns:
                    if df[col].dtype == pl.String or df[col].dtype == pl.Utf8:
                        unique_vals = df[col].drop_nulls().unique().to_list()
                        if len(unique_vals) < 50:
                            categorical_registry[col] = unique_vals
            except Exception as e:
                logger.warning(f"Failed to extract categorical values: {e}")
                
            return output_path, categorical_registry
            
        except Exception as e:
            logger.error(f"Failed to ingest file to Parquet: {e}")
            raise e
            
    @staticmethod
    def _clean_dataset_name(name: str) -> str:
        if not name:
            return ""
        n = str(name).strip()
        for prefix in ["Spreadsheet: ", "spreadsheet: ", "Document: ", "document: ", "PDF: ", "pdf: "]:
            if n.startswith(prefix):
                n = n[len(prefix):].strip()
        for ext in [".xlsx", ".xls", ".csv", ".parquet"]:
            if n.lower().endswith(ext):
                n = n[:-len(ext)].strip()
        return n

    @staticmethod
    def get_active_dataset(dataset_name: str, output_dir: str = "data/parquet") -> Optional[str]:
        """Retrieves the filepath of the most recent version of a dataset."""
        if not os.path.isabs(output_dir):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, output_dir)
            
        clean_name = ParquetIngester._clean_dataset_name(dataset_name)
        registry_path = os.path.join(output_dir, "active_datasets.json")
        if os.path.exists(registry_path):
            with open(registry_path, 'r') as f:
                registry = json.load(f)
                # 1. Exact match
                if dataset_name in registry:
                    p = os.path.join(output_dir, registry[dataset_name])
                    if os.path.exists(p):
                        return p
                # 2. Cleaned name match
                if clean_name in registry:
                    p = os.path.join(output_dir, registry[clean_name])
                    if os.path.exists(p):
                        return p
                # 3. Case-insensitive / normalized search
                norm_target = clean_name.lower().replace(" ", "").replace("_", "").replace("-", "")
                for k, v in registry.items():
                    if k.endswith("__sheets"):
                        continue
                    k_norm = k.lower().replace(" ", "").replace("_", "").replace("-", "")
                    if k_norm == norm_target:
                        p = os.path.join(output_dir, v)
                        if os.path.exists(p):
                            return p

        # 4. Physical directory scan fallback
        import glob
        pattern = os.path.join(output_dir, f"{clean_name}*.parquet")
        matches = glob.glob(pattern)
        if matches:
            # Sort newest first
            matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            return matches[0]

        return None

    @staticmethod
    def get_active_datasets(dataset_name: str, output_dir: str = "data/parquet") -> List[str]:
        """Retrieves all active sheet parquet filepaths for a dataset (or the single parquet if single-sheet)."""
        if not os.path.isabs(output_dir):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, output_dir)
            
        clean_name = ParquetIngester._clean_dataset_name(dataset_name)
        registry_path = os.path.join(output_dir, "active_datasets.json")
        if os.path.exists(registry_path):
            with open(registry_path, 'r') as f:
                registry = json.load(f)
                
                # Check explicit sheets key (exact, clean, or normalized)
                for key_to_try in [f"{dataset_name}__sheets", f"{clean_name}__sheets"]:
                    if key_to_try in registry and isinstance(registry[key_to_try], list):
                        paths = [os.path.join(output_dir, fn) for fn in registry[key_to_try]]
                        valid_paths = [p for p in paths if os.path.exists(p)]
                        if valid_paths:
                            return valid_paths
                            
                norm_target = clean_name.lower().replace(" ", "").replace("_", "").replace("-", "")
                for k, v in registry.items():
                    if k.endswith("__sheets") and isinstance(v, list):
                        k_norm = k[:-8].lower().replace(" ", "").replace("_", "").replace("-", "")
                        if k_norm == norm_target:
                            paths = [os.path.join(output_dir, fn) for fn in v]
                            valid_paths = [p for p in paths if os.path.exists(p)]
                            if valid_paths:
                                return valid_paths

        # Fallback to single active dataset
        single = ParquetIngester.get_active_dataset(dataset_name, output_dir=output_dir)
        if single and os.path.exists(single):
            return [single]
            
        # Fallback to physical scan of sheet parquets
        import glob
        pattern = os.path.join(output_dir, f"{clean_name}_*.parquet")
        matches = glob.glob(pattern)
        if matches:
            return matches

        return []

    @staticmethod
    def delete_active_dataset(dataset_name: str, output_dir: str = "data/parquet") -> bool:
        """Deletes the physical Parquet file and its registry entry from active_datasets.json."""
        if not os.path.isabs(output_dir):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, output_dir)
            
        registry_path = os.path.join(output_dir, "active_datasets.json")
        if not os.path.exists(registry_path):
            return False
            
        try:
            with open(registry_path, 'r') as f:
                registry = json.load(f)
                
            if dataset_name in registry:
                filename = registry[dataset_name]
                file_path = os.path.join(output_dir, filename)
                
                # Delete physical file
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted physical Parquet file: {file_path}")
                else:
                    logger.warning(f"Physical Parquet file not found to delete: {file_path}")
                
                # Remove from registry
                del registry[dataset_name]
                with open(registry_path, 'w') as f:
                    json.dump(registry, f, indent=4)
                logger.info(f"Removed registry entry for {dataset_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete active dataset {dataset_name}: {e}")
        return False
