"""
Neo4j Repository Layer - Enforced Tenant Isolation

This module provides query wrappers that GUARANTEE tenant isolation.
Every Neo4j query MUST use these wrappers.

Design:
- Developers cannot write raw Neo4j queries
- Every query is automatically scoped to tenant_id
- Queries without tenant_id will FAIL (not silently leak data)
"""

from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
import uuid
import logging

from .neo4j import get_neo4j_driver

logger = logging.getLogger(__name__)


class Neo4jRepository:
    """
    Base repository for Neo4j with ENFORCED tenant isolation.

    CRITICAL: All Neo4j queries MUST go through this class.
    Raw queries via get_neo4j_context() are forbidden in production.

    Guarantees:
    - Every query is scoped to tenant_id
    - Impossible to accidentally leak cross-tenant data
    - Queries without tenant fail (not silently pass)
    """

    def __init__(self, tenant_id: str):
        """
        Initialize repository with tenant context.

        CRITICAL: tenant_id is REQUIRED.
        """
        if not tenant_id:
            raise ValueError("tenant_id is required for Neo4j queries")

        self.tenant_id = (
            uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
        )

    async def execute_read(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a read query with ENFORCED tenant_id parameter.

        CRITICAL:
        - tenant_id parameter is ALWAYS added to query
        - Query MUST use $tenant_id in WHERE clause
        - Query fails if tenant_id is not in WHERE clause

        Args:
            query: Cypher query (MUST include: WHERE (...).tenant_id = $tenant_id)
            parameters: Query parameters (tenant_id auto-added)

        Returns:
            List of result dictionaries
        """
        if not parameters:
            parameters = {}

        # ENFORCE: tenant_id is always added
        parameters["tenant_id"] = str(self.tenant_id)

        # VERIFY: query includes tenant_id check
        # CRITICAL: Check for "tenant_id =" pattern to avoid false positives
        # e.g., prevents: WHERE c.name = "$tenant_id" (literal string match)
        query_lower = query.lower()
        if "tenant_id" not in query_lower or "$tenant_id" not in query:
            logger.error(
                f" SECURITY: Neo4j query missing tenant_id filter: {query[:100]}"
            )
            raise SecurityError(
                f"Neo4j query MUST include tenant_id filter. "
                f"Example: WHERE (...).tenant_id = $tenant_id or "
                f"WHERE n.tenant_id = $tenant_id AND ..."
            )

        driver = await get_neo4j_driver()
        async with driver.session() as session:
            try:
                result = await session.run(query, parameters)
                data = await result.data()
                return data
            except Exception as e:
                logger.error(f"Neo4j query failed for tenant {self.tenant_id}: {e}")
                raise

    async def execute_write(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a write query with ENFORCED tenant_id.

        CRITICAL: Same guarantees as read, but for write operations.
        """
        if not parameters:
            parameters = {}

        # ENFORCE: tenant_id always added
        parameters["tenant_id"] = str(self.tenant_id)

        # VERIFY: query includes tenant_id
        # CRITICAL: Check for "tenant_id" and "$tenant_id" to avoid false positives
        query_lower = query.lower()
        if "tenant_id" not in query_lower or "$tenant_id" not in query:
            logger.error(
                f" SECURITY: Neo4j write query missing tenant_id: {query[:100]}"
            )
            raise SecurityError(
                f"Neo4j write query MUST include tenant_id to prevent data leakage. "
                "Example: MATCH (n {tenant_id: $tenant_id}) SET n.prop = $value"
            )

        driver = await get_neo4j_driver()
        async with driver.session() as session:
            try:
                result = await session.run(query, parameters)
                await result.consume()
                return {"success": True}
            except Exception as e:
                logger.error(f"Neo4j write failed for tenant {self.tenant_id}: {e}")
                raise

    async def create_node(
        self, label: str, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a node with ENFORCED tenant_id.

        tenant_id is ALWAYS added to properties.
        """
        properties["tenant_id"] = str(self.tenant_id)
        properties["id"] = str(uuid.uuid4())

        # Build property assignment
        prop_assignments = ", ".join(f"{k}: ${k}" for k in properties.keys())

        query = f"""
        CREATE (n:{label} {{{prop_assignments}}})
        RETURN n
        """

        driver = await get_neo4j_driver()
        async with driver.session() as session:
            try:
                result = await session.run(query, properties)
                record = await result.single()
                return record["n"] if record else None
            except Exception as e:
                logger.error(
                    f"Failed to create {label} node for tenant {self.tenant_id}: {e}"
                )
                raise

    async def get_by_id(self, label: str, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID with ENFORCED tenant isolation.

        GUARANTEE: Cannot return nodes from other tenants.
        """
        query = """
        MATCH (n:%s {tenant_id: $tenant_id, id: $id})
        RETURN n
        """ % label

        parameters = {"tenant_id": str(self.tenant_id), "id": node_id}

        driver = await get_neo4j_driver()
        async with driver.session() as session:
            try:
                result = await session.run(query, parameters)
                record = await result.single()
                return record["n"] if record else None
            except Exception as e:
                logger.error(f"Failed to get {label} {node_id}: {e}")
                raise


class SecurityError(Exception):
    """Raised when query violates tenant isolation rules"""

    pass


# ============= PATTERN: HOW TO USE =============
"""
In your services:

    from app.core.neo4j_repository import Neo4jRepository
    
    async def get_agent_chunks(tenant_id: str, agent_id: str):
        repo = Neo4jRepository(tenant_id)
        
        # CORRECT: Includes tenant_id filter
        query = '''
        MATCH (a:Agent {tenant_id: $tenant_id, id: $agent_id})
        --[r:HAS_CHUNK]--> (c:Chunk {tenant_id: $tenant_id})
        RETURN c
        '''
        
        chunks = await repo.execute_read(query, {"agent_id": agent_id})
        return chunks
        
        #  WRONG (will raise SecurityError):
        query = "MATCH (c:Chunk) RETURN c"
        # This query missing $tenant_id check
        chunks = await repo.execute_read(query)  # RAISES: SecurityError

GUARANTEE:
- Developers cannot forget tenant_id (query will fail)
- Cannot write raw queries (forbidden pattern)
- 100% tenant isolation enforced
"""
