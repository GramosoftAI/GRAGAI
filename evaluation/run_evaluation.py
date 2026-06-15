import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add root folder to python path to resolve app imports when running from command line
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import get_db_with_tenant
from evaluation.configs.eval_config import TEST_TENANT_ID, REPORTS_DIR
from evaluation.logs.logger import eval_logger
from evaluation.utils.db_setup import ensure_db_setup
from evaluation.datasets.dataset_loader import DatasetLoader
from evaluation.evaluators.ingestion_evaluator import IngestionAuditor
from evaluation.evaluators.graph_evaluator import GraphAuditor
from evaluation.reports.excel_writer import StyledExcelWriter

async def main():
    eval_logger.info("=" * 80)
    eval_logger.info("   STARTING GRAG ENTERPRISE EVALUATION SUITE (PHASES 0 - 3)   ")
    eval_logger.info("=" * 80)

    # 1. Framework Setup Metrics (Phase 0 Status)
    modules = [
        "evaluation/configs/eval_config.py",
        "evaluation/logs/logger.py",
        "evaluation/reports/excel_writer.py",
        "evaluation/datasets/dataset_loader.py",
        "evaluation/utils/db_setup.py",
        "evaluation/evaluators/ingestion_evaluator.py",
        "evaluation/evaluators/graph_evaluator.py",
        "evaluation/run_evaluation.py"
    ]
    created_count = sum(1 for m in modules if os.path.exists(m))
    components_registered = 8 # Config, Logger, ExcelWriter, DatasetLoader, DbSetup, IngestionAuditor, GraphAuditor, Runner
    readiness_score = int((created_count / len(modules)) * 100)

    setup_metrics = {
        "modules_created": created_count,
        "components_registered": components_registered,
        "readiness_score": readiness_score
    }

    eval_logger.info(f"Phase 0 Readiness: {readiness_score}% of foundational modules created.")

    # 2. Database & Fixtures Initialization
    async with get_db_with_tenant(TEST_TENANT_ID) as db:
        await ensure_db_setup(db)

    # 3. Load Datasets (Phase 1)
    datasets = DatasetLoader.scan_datasets()
    if not datasets:
        eval_logger.error("No dataset files found to evaluate. Add files to evaluation/datasets/ subfolders.")
        return

    # 4. Initialize Auditors (Phases 2 & 3)
    eval_kb_id = None
    ingestion_records = []
    graph_records = []

    async with get_db_with_tenant(TEST_TENANT_ID) as db:
        ingestion_auditor = IngestionAuditor(db)
        graph_auditor = GraphAuditor(db)

        try:
            # Create a single temporary evaluation KB
            eval_kb_id = await ingestion_auditor.create_eval_kb("EVAL_RUN_KB")

            # Audit each dataset file
            for ds in datasets:
                # Run Ingestion Audit (Phase 2)
                ingest_res = await ingestion_auditor.audit_file(eval_kb_id, ds)
                ingestion_records.append(ingest_res)

                # Run Graph Construction Audit (Phase 3)
                # Only run graph audit if ingestion succeeded and produced chunks
                if ingest_res["status"] == "PASS" and ingest_res["chunk_count"] > 0:
                    graph_res = await graph_auditor.audit_graph(eval_kb_id, ds)
                    graph_records.append(graph_res)
                else:
                    # Append a failed/empty graph record
                    graph_records.append({
                        "document": ds["file_name"],
                        "expected_entities": ds["expected_entities"],
                        "extracted_entities": 0,
                        "entity_precision": 0.0,
                        "entity_recall": 0.0,
                        "entity_f1": 0.0,
                        "expected_relations": ds["expected_relationships"],
                        "extracted_relations": 0,
                        "relation_precision": 0.0,
                        "relation_recall": 0.0,
                        "relation_f1": 0.0
                    })

        finally:
            # Clean up temporary DB and Neo4j resources
            if eval_kb_id:
                await ingestion_auditor.clean_eval_kb(eval_kb_id)

    # 5. Aggregate Scores
    avg_ingest_score = sum(r["score"] for r in ingestion_records) / len(ingestion_records) if ingestion_records else 0.0
    
    # Average Entity and Relation F1 scores
    avg_entity_f1 = sum(r["entity_f1"] for r in graph_records) / len(graph_records) if graph_records else 0.0
    avg_relation_f1 = sum(r["relation_f1"] for r in graph_records) / len(graph_records) if graph_records else 0.0
    avg_graph_score = (avg_entity_f1 + avg_relation_f1) / 2.0

    summary_scores = {
        "ingestion_score": avg_ingest_score,
        "graph_score": avg_graph_score,
        "retrieval_score": 0.0,  # Phase 4 Pending
        "context_score": 0.0,    # Phase 5 Pending
        "answer_score": 0.0,     # Phase 6 Pending
        "performance_score": 0.0  # Phase 7 Pending
    }

    # Calculate overall weighted GRAG score (using current stages, others weighted 0.0)
    # Ingestion = 15%, Graph = 20%. Other weights total 65%.
    # If we want a normalized score of completed phases:
    # (avg_ingest_score * 0.15 + avg_graph_score * 0.20) / 0.35
    completed_weighted = (avg_ingest_score * 0.15) + (avg_graph_score * 0.20)
    overall_grag_score = completed_weighted / 0.35 if avg_ingest_score or avg_graph_score else 0.0

    # 6. Generate Reports
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"evaluation_report_{timestamp}.xlsx"
    writer = StyledExcelWriter(report_filename)

    writer.add_overview_sheet(setup_metrics, summary_scores)
    writer.add_dataset_summary_sheet(datasets)
    writer.add_ingestion_audit_sheet(ingestion_records)
    writer.add_graph_audit_sheet(graph_records)

    report_path = writer.save()
    eval_logger.info(f"Excel report created successfully: {report_path}")

    # Write JSON summaries
    exec_summary = {
        "timestamp": datetime.now().isoformat(),
        "readiness_score": f"{readiness_score}%",
        "ingestion_score": f"{avg_ingest_score * 100:.1f}%",
        "graph_score": f"{avg_graph_score * 100:.1f}%",
        "overall_grag_score": f"{overall_grag_score * 100:.1f}%",
        "recommendation": "PROCEED WITH CAUTION (Phases 4-7 pending)" if overall_grag_score >= 0.8 else "REJECT (Tune ingestion/graph extraction)"
    }
    
    summary_json_path = REPORTS_DIR / f"executive_summary_{timestamp}.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(exec_summary, f, indent=4)
    eval_logger.info(f"Executive summary JSON created: {summary_json_path}")

    eval_logger.info("=" * 80)
    eval_logger.info("   EVALUATION SUITE EXECUTION COMPLETE   ")
    eval_logger.info(f"   Overall GRAG Score: {overall_grag_score * 100:.1f}%")
    eval_logger.info("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
