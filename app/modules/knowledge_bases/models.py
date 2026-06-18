"""Knowledge Base model - stored in PostgreSQL with graph nodes in Neo4j"""

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Text,
    Integer,
    JSON,
    UUID as SQLAlchemyUUID,
)
from sqlalchemy.sql import func
from datetime import datetime
import uuid

# Use the shared Base from models package
from ...models.base import Base


class KnowledgeBase(Base):
    """
    Knowledge Base model - stores documents for AI agents.

    CRITICAL:
    - Each KB belongs to one tenant
    - Each KB is owned by one agent
    - KB also represented as (:KnowledgeBase) node in Neo4j
    - Contains documents that are chunked and embedded
    - Deletion cascades to Neo4j (soft-delete via service layer)

    Properties:
    - id: Unique UUID per KB
    - tenant_id: Multi-tenancy scoping (RLS filtered)
    - user_id: User who created KB (for audit)
    - agent_id: Agent this KB belongs to
    - name: Human-readable KB name
    - description: Optional KB description
    - source: Source type (e.g., "user_upload", "api", "database")
    - total_chunks: Metadata - how many chunks in this KB
    - is_active: For soft-deletion
    - deleted_at: Soft delete timestamp
    """

    __tablename__ = "knowledge_bases"

    # ============= PRIMARY KEY =============
    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )

    # ============= MULTI-TENANCY =============
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ============= OWNERSHIP =============
    user_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ============= AGENT RELATIONSHIP =============
    agent_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ============= KB METADATA =============
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    source = Column(
        String(50),
        nullable=False,
        default="user_upload",
    )  # user_upload, api, database, etc.

    # ============= CONTENT TRACKING =============
    total_chunks = Column(
        Integer,
        nullable=False,
        default=0,
    )  # Number of chunks in this KB (metadata)

    # ============= STATUS =============
    is_active = Column(Boolean, default=True, nullable=False)

    # ============= SOFT DELETE TRACKING =============
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ============= AUDIT TRACKING =============
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ============= INDEXES =============
    __table_args__ = (
        # RLS enforcement
        Index("ix_kbs_tenant_id", "tenant_id"),
        # Find by owner
        Index("ix_kbs_user_id", "user_id"),
        # Find KBs by agent
        Index("ix_kbs_agent_id", "agent_id"),
        # Composite: tenant + agent (list KBs for specific agent)
        Index("ix_kbs_tenant_agent", "tenant_id", "agent_id"),
        # Soft-delete filtering
        Index("ix_kbs_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase id={self.id} name={self.name} agent_id={self.agent_id} chunks={self.total_chunks}>"


class DatabaseConnection(Base):
    """
    Natively represents a structured database connection source 
    associated with a parent KnowledgeBase of type 'database'.
    
    CRITICAL:
    - Enforces RLS isolation through tenant_id scope.
    - Linked 1:1 with a parent KnowledgeBase node.
    """
    __tablename__ = "kb_database_connections"

    # ============= PRIMARY KEY =============
    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )

    # ============= MULTI-TENANCY =============
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ============= KNOWLEDGE BASE RELATIONSHIP =============
    kb_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ============= DATABASE DETAILS =============
    db_type = Column(String(50), nullable=False)  # 'sqlite' or 'postgresql'
    
    # Store credentials or filepath dynamically in encrypted/raw format
    connection_params = Column(JSON, nullable=False)

    # ============= TEMPORAL TRACKING =============
    last_synced_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_db_conns_tenant_id", "tenant_id"),
        Index("ix_db_conns_kb_id", "kb_id"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return f"<DatabaseConnection id={self.id} type={self.db_type} kb_id={self.kb_id}>"


class DocumentChunk(Base):
    """
    Document Chunk model - stores text chunks and their embeddings in PostgreSQL using pgvector.
    Provides hybrid search capabilities (dense vector search in PG + relationship search in Neo4j).
    """

    __tablename__ = "document_chunks"

    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    kb_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )

    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # Store the vector. Dimension is 1024 as per EMBEDDING_DIMENSION in .env
    from pgvector.sqlalchemy import Vector
    embedding = Column(Vector(1024), nullable=True)



    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_chunks_tenant_id", "tenant_id"),
        Index("ix_chunks_kb_id", "kb_id"),
        # We can add an hnsw or ivfflat index later for performance
    )
    
    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} kb_id={self.kb_id} index={self.chunk_index}>"


class DocumentTableRow(Base):
    """
    Structured Table Row model - stores extracted tabular data as JSONB in PostgreSQL.
    Provides a SQL engine target for data analytics routing (e.g. "Find products below 5000")
    instead of relying on vector semantic search.
    """

    __tablename__ = "document_table_rows"

    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    kb_id = Column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ============= KB METADATA =============
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    source = Column(
        String(50),
        nullable=False,
        default="user_upload",
    )  # user_upload, api, database, etc.
    
    document_type = Column(String(50), nullable=True) # e.g. PRICE_LIST, INVOICE, PURCHASE_ORDER, GENERAL

    # ============= CONTENT TRACKING =============
    total_chunks = Column(
        Integer,
        nullable=False,
        default=0,
    )  # Number of chunks in this KB (metadata)

    # ============= STATUS =============
    is_active = Column(Boolean, default=True, nullable=False)

    # ============= SOFT DELETE TRACKING =============
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ============= AUDIT TRACKING =============
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ============= INDEXES =============
    __table_args__ = (
        # RLS enforcement
        Index("ix_kbs_tenant_id", "tenant_id"),
        # Find by owner
        Index("ix_kbs_user_id", "user_id"),
        # Find KBs by agent
        Index("ix_kbs_agent_id", "agent_id"),
        # Composite: tenant + agent (list KBs for specific agent)
        Index("ix_kbs_tenant_agent", "tenant_id", "agent_id"),
        # Soft-delete filtering
        Index("ix_kbs_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase id={self.id} name={self.name} agent_id={self.agent_id} chunks={self.total_chunks}>"


class DatabaseConnection(Base):
    """
    Natively represents a structured database connection source 
    associated with a parent KnowledgeBase of type 'database'.
    
    CRITICAL:
    - Enforces RLS isolation through tenant_id scope.
    - Linked 1:1 with a parent KnowledgeBase node.
    """
    __tablename__ = "kb_database_connections"

    # ============= PRIMARY KEY =============
    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )

    # ============= MULTI-TENANCY =============
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ============= KNOWLEDGE BASE RELATIONSHIP =============
    kb_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # ============= DATABASE DETAILS =============
    db_type = Column(String(50), nullable=False)  # 'sqlite' or 'postgresql'
    
    # Store credentials or filepath dynamically in encrypted/raw format
    connection_params = Column(JSON, nullable=False)

    # ============= TEMPORAL TRACKING =============
    last_synced_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_db_conns_tenant_id", "tenant_id"),
        Index("ix_db_conns_kb_id", "kb_id"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return f"<DatabaseConnection id={self.id} type={self.db_type} kb_id={self.kb_id}>"


class DocumentChunk(Base):
    """
    Document Chunk model - stores text chunks and their embeddings in PostgreSQL using pgvector.
    Provides hybrid search capabilities (dense vector search in PG + relationship search in Neo4j).
    """

    __tablename__ = "document_chunks"

    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    kb_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )

    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    
    # Store the vector. Dimension is 1024 as per EMBEDDING_DIMENSION in .env
    from pgvector.sqlalchemy import Vector
    embedding = Column(Vector(1024), nullable=True)



    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_chunks_tenant_id", "tenant_id"),
        Index("ix_chunks_kb_id", "kb_id"),
        # We can add an hnsw or ivfflat index later for performance
    )
    
    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} kb_id={self.kb_id} index={self.chunk_index}>"


class DocumentTableRow(Base):
    """
    Structured Table Row model - stores extracted tabular data as JSONB in PostgreSQL.
    Provides a SQL engine target for data analytics routing (e.g. "Find products below 5000")
    instead of relying on vector semantic search.
    """

    __tablename__ = "document_table_rows"

    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    kb_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )

    page_number = Column(Integer, nullable=False, default=1)
    table_index = Column(Integer, nullable=False, default=0)
    row_index = Column(Integer, nullable=False, default=0)
    
    # Typed columns for deterministic SQL generation and indexing
    from sqlalchemy import Numeric
    part_number = Column(String(255), nullable=True, index=True)
    product_name = Column(String(1000), nullable=True, index=True)
    mrp = Column(Numeric(10, 2), nullable=True, index=True)
    gst = Column(Numeric(5, 2), nullable=True)
    hsn_code = Column(String(100), nullable=True)
    extraction_confidence = Column(Numeric(4, 3), nullable=True, default=0.99)
    
    # Store the row's key-value pairs (Header -> Value) dynamically as a fallback
    from sqlalchemy.dialects.postgresql import JSONB
    row_data = Column(JSONB, nullable=False)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_tablerows_tenant_id", "tenant_id"),
        Index("ix_tablerows_kb_id", "kb_id"),
        Index("ix_tablerows_page_idx", "page_number"),
    )
    
    def __repr__(self) -> str:
        return f"<DocumentTableRow id={self.id} kb_id={self.kb_id} table={self.table_index} row={self.row_index}>"


class AnalyticsQueryLog(Base):
    """
    Audit trail for deterministic Table Analytics queries.
    Stores the extracted intent, generated SQL, and performance metrics for transparency and debugging.
    """
    __tablename__ = "analytics_query_log"

    id = Column(
        SQLAlchemyUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        nullable=False,
    )
    
    tenant_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    kb_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )

    query_text = Column(Text, nullable=False)
    intent_json = Column(JSON, nullable=False)
    generated_sql = Column(Text, nullable=False)
    rows_returned = Column(Integer, nullable=False, default=0)
    execution_time_ms = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_analyticslog_tenant_id", "tenant_id"),
        Index("ix_analyticslog_kb_id", "kb_id"),
    )
    
    def __repr__(self) -> str:
        return f"<AnalyticsQueryLog id={self.id} kb_id={self.kb_id} rows={self.rows_returned}>"
