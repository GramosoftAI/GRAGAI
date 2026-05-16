"""Ontology routes - API for managing the knowledge schema"""

from fastapi import APIRouter, Depends, Request
from typing import List
from ...core.database import get_tenant_and_user
from ...utils.formatters import format_success, format_error
from . import schemas, service

router = APIRouter(prefix="/api/v1/ontology", tags=["Ontology"])

@router.post("/classes", response_model=dict)
async def create_ontology_class(request: Request, data: schemas.OntologyClassCreate):
    """Define a valid entity type in the ontology"""
    tenant_id, _ = get_tenant_and_user(request)
    svc = service.OntologyService(str(tenant_id))
    result = await svc.create_class(data)
    return format_success(result, meta={"message": f"Class {result['name']} defined"})

@router.post("/relations", response_model=dict)
async def create_ontology_relation(request: Request, data: schemas.OntologyRelationCreate):
    """Define a valid relationship type in the ontology"""
    tenant_id, _ = get_tenant_and_user(request)
    svc = service.OntologyService(str(tenant_id))
    result = await svc.create_relation(data)
    return format_success(result, meta={"message": f"Relation {result['name']} defined"})

@router.get("", response_model=dict)
async def get_ontology(request: Request):
    """Retrieve the current ontology schema"""
    tenant_id, _ = get_tenant_and_user(request)
    svc = service.OntologyService(str(tenant_id))
    result = await svc.get_ontology()
    return format_success(result)
