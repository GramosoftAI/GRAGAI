"""Ontology schemas for request/response validation"""

from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

class OntologyClassCreate(BaseModel):
    """Request to create an ontology class (Entity Type)"""
    name: str = Field(..., description="Name of the entity class (e.g., PERSON, PROJECT)")
    description: Optional[str] = Field(None, description="Detailed description of what this class represents")

class OntologyRelationCreate(BaseModel):
    """Request to create an ontology relationship (Predicate)"""
    name: str = Field(..., description="Name of the relationship type (e.g., WORKS_FOR, LOCATED_IN)")
    description: Optional[str] = Field(None, description="Detailed description of when to use this relationship")

class OntologyClassResponse(BaseModel):
    """Response for an ontology class"""
    name: str
    description: Optional[str]

class OntologyRelationResponse(BaseModel):
    """Response for an ontology relation"""
    name: str
    description: Optional[str]

class OntologyResponse(BaseModel):
    """Full ontology overview for a tenant"""
    classes: List[OntologyClassResponse]
    relations: List[OntologyRelationResponse]
