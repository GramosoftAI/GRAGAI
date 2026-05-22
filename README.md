<div align="center">

# 🌐 GRAG
**Enterprise-Grade Multi-Tenant Graph RAG & Autonomous AI Platform**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)](https://neo4j.com/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

*Transforming unstructured data into strict, actionable intelligence using Active Ontologies, Vector Search, and Multi-Hop Graph Traversals.*

</div>

---

## 🚀 Welcome to GRAG

**GRAG** (formerly GraphMind) is a state-of-the-art backend system that bridges the gap between raw documents and autonomous AI reasoning. By combining the deterministic structure of **Neo4j Knowledge Graphs**, the semantic power of **Vector Embeddings (pgvector)**, and **Active Enterprise Ontologies**, GRAG allows organizations to deploy highly accurate, context-aware AI Agents isolated securely across multiple tenants.

---

## ✨ Cutting-Edge Features

### 🏢 Ironclad Multi-Tenancy
* **Row-Level Security (RLS):** Enforced natively at the PostgreSQL level for all relational data. 
* **Graph Isolation:** Mandatory `tenant_id` constraints enforced on every single Neo4j node and relationship. 
* Zero cross-tenant data leakage, guaranteed natively by the database layers.

### 🧠 Active Enterprise Ontology (AEO)
* Move beyond hallucinated LLM entities. GRAG enforces a **Strict Semantic Schema**.
* Define allowed Classes (e.g., `Application`, `Server`) and Rules (e.g., `Application -> DEPENDS_ON -> Database`).
* The extraction pipeline dynamically injects these rules directly into the LLM prompt, guaranteeing that the Knowledge Graph is built predictably and accurately.

### 🕸️ True Hybrid Graph RAG
* **Multi-Hop Reasoning:** Doesn't just find similar text—traverses relationships (`SIMILAR`, `MENTIONS`, `NEXT`) to assemble comprehensive evidence.
* **Semantic Vector Search:** Integrates `bge-large-en-v1.5` embeddings for deep contextual matching.
* **Triplet Extraction:** Uses advanced LLMs to extract factual `(Subject, Predicate, Object)` graphs from data chunks.

### 💬 Conversational Memory & Agents
* **Session Persistence:** Remembers user contexts across multi-turn conversations.
* **Persona Engine:** Configure Agents with tailored system prompts and dynamic personalities (Technical, Formal, Friendly, etc.).
* **Memory Injection:** Past chat history is dynamically embedded into the RAG context for seamless follow-up reasoning.

### 📄 Intelligent Data Ingestion
* **Multimodal Fallbacks:** Automatically utilizes Vision AI (e.g., Llama-3-Vision) to OCR scanned PDFs lacking text layers.
* **Automated Web Crawling:** Point to a URL and auto-ingest hierarchies.
* **Smart Chunking:** Sentence-aware text splitting with optimized token overlap.

### 🔌 Plug-and-Play Architecture
* **Dynamic Module Loading:** Drop a new feature into `app/modules/` and FastAPI automatically discovers and registers its routers. No monolithic boilerplate.

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Core Framework** | `FastAPI` | High-performance async REST & WebSocket APIs |
| **Relational DB** | `PostgreSQL` | Users, Tenants, Billing, Auth, RLS Security |
| **Vector Engine** | `pgvector` | Semantic similarity and embedding indexing |
| **Knowledge Graph**| `Neo4j` | Entity relationships, Triplet storage, Multi-hop RAG |
| **Inference/LLM** | `Ollama` / `DeepInfra` | Local/Remote LLM orchestration, Triplet Extraction |
| **Caching** | `Redis` | Session management and fast volatile data |
| **ORM** | `SQLAlchemy` (Async) | Database modeling and schema migrations |

---

## 🚦 Quick Start Guide

### 1. Prerequisites
Ensure you have Docker and Docker Compose installed.

### 2. Clone & Configure
```bash
git clone https://github.com/GramosoftAI/GRAGAI.git
cd GRAGAI
cp .env.example .env
# Edit .env with your specific API keys (DeepInfra, etc.) and passwords
```

### 3. Launch via Docker (Recommended)
```bash
docker-compose up -d --build
```
This will spin up Postgres, Neo4j, Redis, Ollama, and the GRAG API server. 
The API will be accessible at: `http://localhost:8000/docs`

### 4. Local Development Setup (Manual)
```bash
# Create Virtual Environment
python -m venv mind

# Windows Activation
.\\mind\\Scripts\\activate
# Linux/Mac Activation
# source mind/bin/activate

# Install Dependencies
pip install -r requirements.txt

# Start Backend
./start_backend.ps1  # Windows PowerShell
# ./start_backend.sh # Linux/Mac
```

---

## 📁 Project Architecture

```plaintext
GRAG/
├── app/
│   ├── core/              # Shared logic (Config, DB, Security, RLS, Triplet Extractor)
│   ├── modules/           # Dynamic Feature Modules
│   │   ├── agents/        # AI Agent configuration
│   │   ├── auth/          # JWT Security & Registration
│   │   ├── chats/         # Memory and conversational history
│   │   ├── etl/           # Ingestion, Chunking, OCR
│   │   ├── ontology/      # Strict Schema Rules & Relationship constraints
│   │   ├── rag/           # Hybrid retrieval pipeline & generation
│   │   └── tenants/       # Isolation management
│   ├── main.py            # Application entry point
├── config/                # Environment configurations
├── migrations/            # Alembic DB migrations
└── docker-compose.yml     # Infrastructure orchestration
```

---

## 🤝 Contributing & Extension

**Adding New Features:**
Because of the dynamic module system, creating a new feature is as simple as creating a new folder in `app/modules/`. 

```plaintext
app/modules/my_feature/
├── __init__.py
├── routes.py       # Expose APIRouter as 'router' (auto-loaded)
├── models.py       # SQLAlchemy ORM models
├── schemas.py      # Pydantic validation schemas
└── service.py      # Business logic
```

## 📜 License
This project is licensed under the **MIT License**.
