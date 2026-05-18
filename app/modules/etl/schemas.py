"""Pydantic schemas for ETL connection, schema discovery, and graph mapping"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ConnectionConfig(BaseModel):
    """Configuration for database source connection"""
    db_type: str = Field(..., description="Database type, e.g. 'sqlite', 'postgresql'")
    # SQLite-specific
    file_path: Optional[str] = Field(None, description="Absolute or relative path to SQLite file")
    # General connection settings (for PostgreSQL/MySQL later)
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

class ConnectionValidationResponse(BaseModel):
    """Status of connection validation"""
    success: bool
    message: str
    discovered_tables: List[str] = []

class ColumnMetadata(BaseModel):
    """Metadata representing a single database table column"""
    name: str
    type: str
    is_primary_key: bool
    is_foreign_key: bool
    reference_table: Optional[str] = None
    reference_column: Optional[str] = None

class TableMetadata(BaseModel):
    """Discovered schema definition of a single database table"""
    name: str
    primary_key: Optional[str] = None
    columns: List[ColumnMetadata] = []
    foreign_keys: List[Dict[str, Any]] = []

class SchemaDiscoveryResponse(BaseModel):
    """List of all discovered tables and their schema structure"""
    tables: List[TableMetadata]

class TargetNodeMapping(BaseModel):
    """Schema instruction for transforming a table into a graph Node"""
    source_table: str
    target_label: str
    properties: Dict[str, str] = Field(
        ..., 
        description="Key-value mapping of {target_property_name: source_column_name}"
    )

class TargetRelationshipMapping(BaseModel):
    """Schema instruction for transforming foreign keys or tables into a graph Edge"""
    source_table: str
    from_node: Dict[str, str] = Field(
        ..., 
        description="Scoping target node label and relational key, e.g. {'label': 'Customer', 'source_key': 'customer_id'}"
    )
    to_node: Dict[str, str] = Field(
        ..., 
        description="Scoping target node label and relational key, e.g. {'label': 'Order', 'source_key': 'id'}"
    )
    relationship_type: str
    properties: Optional[Dict[str, str]] = None

class GraphMappingConfig(BaseModel):
    """Complete instructions for relational-to-graph mapping and upserting"""
    mapping_name: str
    nodes: List[TargetNodeMapping]
    relationships: List[TargetRelationshipMapping]

class SyncResponse(BaseModel):
    """Operational summary of the loaded graph entities"""
    success: bool
    session_id: str
    nodes_created: int
    relationships_created: int
    message: str
