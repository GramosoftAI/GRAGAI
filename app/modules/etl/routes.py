"""REST routes for ETL database ingestion and Graph integration"""

import logging
from fastapi import APIRouter, Request, HTTPException, status

from .schemas import (
    ConnectionConfig,
    ConnectionValidationResponse,
    SchemaDiscoveryResponse,
    GraphMappingConfig,
    SyncResponse,
)
from .service import ETLService
from ...utils.formatters import format_success, format_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/etl", tags=["Database ETL Ingestion"])
etl_service = ETLService()


def get_tenant_id(request: Request) -> str:
    """Extract tenant_id from request state context (injected by middleware)"""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        logger.error("Missing tenant_id in request state")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return str(tenant_id)


@router.post(
    "/validate",
    response_model=ConnectionValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate database source connection",
    description="Validates target database credentials and lists discovered tables.",
)
async def validate_connection(
    request: Request,
    config: ConnectionConfig,
):
    # Tenant validation
    _ = get_tenant_id(request)
    
    response = await etl_service.validate_connection(config)
    if not response.success:
        raise HTTPException(
            status_code=400,
            detail=response.message
        )
    return response


@router.post(
    "/discover",
    response_model=SchemaDiscoveryResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover relational database schemas",
    description="Performs database schema reflection to discover table columns, data types, and key constraints.",
)
async def discover_schema(
    request: Request,
    config: ConnectionConfig,
):
    # Tenant validation
    _ = get_tenant_id(request)
    
    try:
        response = await etl_service.discover_schema(config)
        return response
    except Exception as e:
        logger.error(f"Failed to discover database schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Schema discovery failed: {str(e)}"
        )


@router.post(
    "/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize database into Neo4j Knowledge Graph",
    description="Performs ETL: Extracts relational rows, transforms them into graph entities, and merges them into Neo4j under active tenant namespaces.",
)
async def synchronize_graph(
    request: Request,
    config: ConnectionConfig,
    mapping: GraphMappingConfig,
):
    tenant_id = get_tenant_id(request)
    
    try:
        response = await etl_service.synchronize_graph(
            config=config,
            mapping=mapping,
            tenant_id=tenant_id
        )
        if not response.success:
            raise HTTPException(
                status_code=400,
                detail=response.message
            )
        return response
    except Exception as e:
        logger.error(f"ETL Synchronization operation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Synchronization failed: {str(e)}"
        )
