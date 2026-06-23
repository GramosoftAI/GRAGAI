"""REST routes for Personality CRUD operations"""

from fastapi import APIRouter, Request, HTTPException, status
from .service import PersonalityService
from . import schemas
from ...core.database import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/personalities", tags=["personalities"])

def get_tenant_and_user(request: Request) -> tuple[str, str]:
    """Extract tenant_id and user_id from request context"""
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)

    if not tenant_id or not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return str(tenant_id), str(user_id)

@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Create Personality",
    description="Create a new custom personality for the current tenant"
)
async def create_personality(
    request: Request,
    personality_request: schemas.PersonalityCreate
) -> dict:
    try:
        tenant_id, user_id = get_tenant_and_user(request)
        async with AsyncSessionLocal() as db:
            service = PersonalityService(db, tenant_id, user_id)
            result = await service.create_personality(personality_request)
            if not result.get("success"):
                raise HTTPException(status_code=result.get("status_code", 400), detail=result.get("error"))
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating personality: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "",
    response_model=dict,
    summary="List Personalities",
    description="List all available personalities (system + tenant specific)"
)
async def list_personalities(request: Request) -> dict:
    try:
        tenant_id, user_id = get_tenant_and_user(request)
        async with AsyncSessionLocal() as db:
            service = PersonalityService(db, tenant_id, user_id)
            return await service.list_personalities()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing personalities: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get(
    "/{id}",
    response_model=dict,
    summary="Get Personality",
    description="Retrieve a specific personality by ID"
)
async def get_personality(request: Request, id: str) -> dict:
    try:
        tenant_id, user_id = get_tenant_and_user(request)
        async with AsyncSessionLocal() as db:
            service = PersonalityService(db, tenant_id, user_id)
            result = await service.get_personality(id)
            if not result.get("success"):
                raise HTTPException(status_code=result.get("status_code", 404), detail=result.get("error"))
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting personality: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put(
    "/{id}",
    response_model=dict,
    summary="Update Personality",
    description="Update a custom personality"
)
async def update_personality(
    request: Request,
    id: str,
    personality_request: schemas.PersonalityUpdate
) -> dict:
    try:
        tenant_id, user_id = get_tenant_and_user(request)
        async with AsyncSessionLocal() as db:
            service = PersonalityService(db, tenant_id, user_id)
            result = await service.update_personality(id, personality_request)
            if not result.get("success"):
                raise HTTPException(status_code=result.get("status_code", 400), detail=result.get("error"))
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating personality: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete(
    "/{id}",
    response_model=dict,
    summary="Delete Personality",
    description="Delete a custom personality"
)
async def delete_personality(request: Request, id: str) -> dict:
    try:
        tenant_id, user_id = get_tenant_and_user(request)
        async with AsyncSessionLocal() as db:
            service = PersonalityService(db, tenant_id, user_id)
            result = await service.delete_personality(id)
            if not result.get("success"):
                raise HTTPException(status_code=result.get("status_code", 400), detail=result.get("error"))
            return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting personality: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
