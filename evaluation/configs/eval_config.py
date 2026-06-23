import os
from pathlib import Path
from app.core.config import get_settings

settings = get_settings()

# Evaluation directory structures
EVAL_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = EVAL_DIR / "datasets"
GROUND_TRUTH_DIR = EVAL_DIR / "ground_truth"
REPORTS_DIR = EVAL_DIR / "reports"
LOGS_DIR = EVAL_DIR / "logs"

# Ensure required directories exist
for d in [DATASETS_DIR, GROUND_TRUTH_DIR, REPORTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Create subdirectories for datasets
for subdir in ["pdf", "urls", "excel", "docx", "markdown", "raw_text"]:
    (DATASETS_DIR / subdir).mkdir(parents=True, exist_ok=True)

# Create subdirectories for ground truth
for subdir in ["entities", "relationships", "retrieval", "answers"]:
    (GROUND_TRUTH_DIR / subdir).mkdir(parents=True, exist_ok=True)

# Test tenant context for evaluation database / Neo4j isolation
TEST_TENANT_ID = os.getenv("EVAL_TEST_TENANT_ID", "00000000-0000-0000-0000-000000000000")
TEST_AGENT_ID = os.getenv("EVAL_TEST_AGENT_ID", "00000000-0000-0000-0000-000000000000")
TEST_USER_ID = os.getenv("EVAL_TEST_USER_ID", "00000000-0000-0000-0000-000000000001")
EVAL_DB_URL = settings.database_url
NEO4J_URI = settings.neo4j_uri
NEO4J_USER = settings.neo4j_user
NEO4J_PASSWORD = settings.neo4j_password
