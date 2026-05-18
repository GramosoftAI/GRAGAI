"""ETL Service - Core orchestration for database schema discovery and graph transformation"""

import os
import logging
import sqlite3
from typing import List, Dict, Any, Optional
import uuid

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

from .schemas import (
    ConnectionConfig,
    ConnectionValidationResponse,
    SchemaDiscoveryResponse,
    TableMetadata,
    ColumnMetadata,
    GraphMappingConfig,
    SyncResponse,
)
from ...core.neo4j import get_neo4j_context

logger = logging.getLogger(__name__)


class ETLService:
    """
    ETL Service - coordinates extracting relational schemas and bulk upserting them to Neo4j.
    Designed for conceptual SQLite database testing before scaling to larger enterprise engines.
    """

    @staticmethod
    def _get_sqlite_absolute_path(relative_path: str) -> str:
        """Resolve database path relative to workspace or absolute"""
        # If relative, resolve against project root (two levels up from modules/etl/)
        if not os.path.isabs(relative_path):
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            return os.path.join(project_root, relative_path)
        return relative_path

    def _get_engine(self, config: ConnectionConfig) -> Engine:
        """Get SQLAlchemy Engine based on database type"""
        if config.db_type == "sqlite":
            if not config.file_path:
                raise ValueError("file_path is required for sqlite database")
            db_path = self._get_sqlite_absolute_path(config.file_path)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            connection_url = f"sqlite:///{db_path}"
            logger.info(f"Connecting to SQLite: {connection_url}")
            return create_engine(connection_url)
        else:
            # Placeholder for PostgreSQL / MySQL / SQL Server
            connection_url = (
                f"{config.db_type}://{config.username}:{config.password}@"
                f"{config.host}:{config.port}/{config.database}"
            )
            return create_engine(connection_url)

    async def validate_connection(self, config: ConnectionConfig) -> ConnectionValidationResponse:
        """
        Validate database connection parameters and return table names.
        """
        try:
            engine = self._get_engine(config)
            
            # For SQLite, check if the file exists and is readable
            if config.db_type == "sqlite" and config.file_path:
                db_path = self._get_sqlite_absolute_path(config.file_path)
                if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
                    return ConnectionValidationResponse(
                        success=False,
                        message=f"Database file not found or empty at {db_path}",
                        discovered_tables=[]
                    )

            # Test connection
            with engine.connect() as conn:
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
            return ConnectionValidationResponse(
                success=True,
                message=f"Successfully connected to {config.db_type} database.",
                discovered_tables=tables
            )
        except Exception as e:
            logger.error(f"Failed to validate connection: {e}", exc_info=True)
            return ConnectionValidationResponse(
                success=False,
                message=f"Connection failed: {str(e)}",
                discovered_tables=[]
            )

    async def discover_schema(self, config: ConnectionConfig) -> SchemaDiscoveryResponse:
        """
        Reflect database and introspect table fields, primary keys, and foreign keys.
        """
        engine = self._get_engine(config)
        discovered_tables = []

        try:
            with engine.connect() as conn:
                inspector = inspect(engine)
                table_names = inspector.get_table_names()

                for t_name in table_names:
                    columns = inspector.get_columns(t_name)
                    pk_constraint = inspector.get_pk_constraint(t_name)
                    fks = inspector.get_foreign_keys(t_name)

                    # Extract primary keys
                    pk_cols = pk_constraint.get("constrained_columns", [])
                    primary_key = pk_cols[0] if pk_cols else None

                    # Extract columns
                    cols_metadata = []
                    for col in columns:
                        c_name = col["name"]
                        c_type = str(col["type"])
                        
                        # Check if column is a foreign key
                        is_fk = False
                        ref_table = None
                        ref_col = None
                        
                        for fk in fks:
                            if c_name in fk.get("constrained_columns", []):
                                is_fk = True
                                ref_table = fk.get("referred_table")
                                referred_cols = fk.get("referred_columns", [])
                                ref_col = referred_cols[0] if referred_cols else None
                                break

                        cols_metadata.append(
                            ColumnMetadata(
                                name=c_name,
                                type=c_type,
                                is_primary_key=(c_name in pk_cols),
                                is_foreign_key=is_fk,
                                reference_table=ref_table,
                                reference_column=ref_col
                            )
                        )

                    discovered_tables.append(
                        TableMetadata(
                          name=t_name,
                          primary_key=primary_key,
                          columns=cols_metadata,
                          foreign_keys=fks
                        )
                    )

            return SchemaDiscoveryResponse(tables=discovered_tables)
        except Exception as e:
            logger.error(f"Failed to discover schema: {e}", exc_info=True)
            raise RuntimeError(f"Schema discovery failed: {str(e)}")

    async def synchronize_graph(
        self,
        config: ConnectionConfig,
        mapping: GraphMappingConfig,
        tenant_id: str
    ) -> SyncResponse:
        """
        Extract relational rows, transform them into graph nodes/edges using instructions,
        and load them into Neo4j in high-performance batches under the tenant's namespace.
        """
        engine = self._get_engine(config)
        nodes_created = 0
        relationships_created = 0
        session_uuid = str(uuid.uuid4())

        try:
            # 1. EXTRACT DATA & BUILD NODES
            # Maps: { (table_name, pk_value): target_unique_graph_id }
            node_id_registry = {}

            async with get_neo4j_context() as neo4j_sess:
                with engine.connect() as conn:
                    # 1.1 Process Nodes Mapping
                    for node_map in mapping.nodes:
                        tbl = node_map.source_table
                        label = node_map.target_label
                        prop_mapping = node_map.properties

                        # Discover table primary key for indexing
                        inspector = inspect(engine)
                        pk_info = inspector.get_pk_constraint(tbl)
                        pk_cols = pk_info.get("constrained_columns", [])
                        if not pk_cols:
                            raise ValueError(f"Table '{tbl}' must have a primary key for graph mapping.")
                        pk_name = pk_cols[0]

                        # Fetch rows
                        rows = conn.execute(f"SELECT * FROM {tbl}").mappings().all()

                        node_batch = []
                        for row in rows:
                            pk_val = str(row[pk_name])
                            # Create a globally unique composite ID for this node
                            composite_id = f"{tbl}:{pk_val}"
                            node_id_registry[(tbl, pk_val)] = composite_id

                            # Extract properties based on mapping definition
                            graph_properties = {
                                "id": composite_id,
                                "tenant_id": tenant_id,
                                "etl_source_id": pk_val,
                                "etl_source_table": tbl,
                                "sync_session_id": session_uuid
                            }

                            for target_prop, source_col in prop_mapping.items():
                                if source_col in row:
                                    graph_properties[target_prop] = row[source_col]

                            node_batch.append(graph_properties)

                        # Write nodes to Neo4j in batch
                        if node_batch:
                            # Cypher Unwind Bulk merge query
                            cypher_nodes_merge = f"""
                            UNWIND $batch AS row
                            MERGE (n:`{label}` {{id: row.id, tenant_id: $tenant_id}})
                            ON CREATE SET n += row, n.created_at = timestamp()
                            ON MATCH SET n += row, n.updated_at = timestamp()
                            """
                            await neo4j_sess.run(
                                cypher_nodes_merge,
                                batch=node_batch,
                                tenant_id=tenant_id
                            )
                            nodes_created += len(node_batch)
                            logger.info(f"Merged {len(node_batch)} nodes under label ':{label}'")

                    # 1.2 Process Relationships Mapping
                    for rel_map in mapping.relationships:
                        tbl = rel_map.source_table
                        rel_type = rel_map.relationship_type
                        
                        from_lbl = rel_map.from_node["label"]
                        from_key_col = rel_map.from_node["source_key"]
                        
                        to_lbl = rel_map.to_node["label"]
                        to_key_col = rel_map.to_node["source_key"]

                        # Discover primary key of relationships source table (to fetch unique columns)
                        rows = conn.execute(f"SELECT * FROM {tbl}").mappings().all()

                        rel_batch = []
                        for row in rows:
                            # Resolve source unique Composite IDs
                            from_pk_val = str(row[from_key_col]) if from_key_col in row else None
                            to_pk_val = str(row[to_key_col]) if to_key_col in row else None

                            if not from_pk_val or not to_pk_val:
                                continue

                            # Resolve which source table the FK links to
                            # We search the registry or fallback to standard FK resolutions
                            # For our tiny conceptual DB, we match standard composite pattern
                            from_composite_id = f"{rel_map.from_node.get('source_table', 'users')}:{from_pk_val}"
                            to_composite_id = f"{rel_map.to_node.get('source_table', 'products')}:{to_pk_val}"

                            rel_properties = {
                                "from_id": from_composite_id,
                                "to_id": to_composite_id,
                                "sync_session_id": session_uuid
                            }

                            # Map additional relationship properties (e.g. quantity, dates)
                            if rel_map.properties:
                                for target_prop, source_col in rel_map.properties.items():
                                    if source_col in row:
                                        rel_properties[target_prop] = row[source_col]

                            rel_batch.append(rel_properties)

                        # Write relationships in batch to Neo4j
                        if rel_batch:
                            cypher_relations_merge = f"""
                            UNWIND $batch AS row
                            MATCH (a {{id: row.from_id, tenant_id: $tenant_id}})
                            MATCH (b {{id: row.to_id, tenant_id: $tenant_id}})
                            MERGE (a)-[r:`{rel_type}` {{sync_session_id: row.sync_session_id}}]->(b)
                            ON CREATE SET r += row, r.created_at = timestamp()
                            ON MATCH SET r += row, r.updated_at = timestamp()
                            """
                            await neo4j_sess.run(
                                cypher_relations_merge,
                                batch=rel_batch,
                                tenant_id=tenant_id
                            )
                            relationships_created += len(rel_batch)
                            logger.info(f"Merged {len(rel_batch)} relationships of type '-[:{rel_type}]->'")

            return SyncResponse(
                success=True,
                session_id=session_uuid,
                nodes_created=nodes_created,
                relationships_created=relationships_created,
                message="Successfully synchronized database into GraphMind Knowledge Graph."
            )

        except Exception as e:
            logger.error(f"Failed to synchronize graph: {e}", exc_info=True)
            return SyncResponse(
                success=False,
                session_id=session_uuid,
                nodes_created=nodes_created,
                relationships_created=relationships_created,
                message=f"Sync failed: {str(e)}"
            )
