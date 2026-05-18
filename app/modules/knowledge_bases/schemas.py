"""Pydantic schemas for Knowledge Base request/response validation"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class KBCreate(BaseModel):
    """
    Schema for creating a new knowledge base.

    REQUIRED:
    - name: KB name
    - agent_id: Agent this KB belongs to

    OPTIONAL:
    - description: Human description
    - source: Source type (default: "user_upload")
    """

    name: str = Field(..., min_length=1, max_length=255, description="KB name")
    description: Optional[str] = Field(
        None, max_length=1000, description="KB description"
    )
    agent_id: UUID = Field(..., description="Agent this KB belongs to")
    source: Optional[str] = Field(
        "user_upload",
        max_length=50,
        description="Source type (user_upload, api, database, etc.)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Company Documentation",
                "description": "Internal company policies and procedures",
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "source": "user_upload",
            }
        }


class KBUpdate(BaseModel):
    """
    Schema for updating an existing knowledge base.

    All fields are optional (PATCH semantics).
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated KB Name",
                "description": "Updated description...",
            }
        }


class KBResponse(BaseModel):
    """
    Schema for knowledge base response (read-only).

    Returned by GET endpoints.
    """

    id: UUID
    tenant_id: UUID
    user_id: UUID
    agent_id: UUID
    name: str
    description: Optional[str]
    source: str
    total_chunks: int
    is_active: bool
    deleted_at: Optional[datetime] = Field(
        None, description="Soft delete timestamp (null = not deleted)"
    )
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy ORM mode
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440002",
                "agent_id": "550e8400-e29b-41d4-a716-446655440003",
                "name": "Company Documentation",
                "description": "Internal company policies and procedures",
                "source": "user_upload",
                "total_chunks": 45,
                "is_active": True,
                "deleted_at": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class KBListResponse(BaseModel):
    """
    Schema for listing knowledge bases.

    Includes pagination metadata.
    """

    kbs: list[KBResponse]
    count: int = Field(..., description="Number of KBs in this page")
    total: int = Field(..., description="Total KBs in database")

    class Config:
        json_schema_extra = {
            "example": {
                "kbs": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                        "user_id": "550e8400-e29b-41d4-a716-446655440002",
                        "agent_id": "550e8400-e29b-41d4-a716-446655440003",
                        "name": "Company Documentation",
                        "description": "Internal company policies",
                        "source": "user_upload",
                        "total_chunks": 45,
                        "is_active": True,
                        "deleted_at": None,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "count": 1,
                "total": 1,
            }
        }


class KBDeleteResponse(BaseModel):
    """
    Schema for delete response.
    """

    id: UUID
    deleted_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "deleted_at": "2024-01-15T10:30:00Z",
            }
        }


class KBURLIngest(BaseModel):
    """
    Schema for URL ingestion request.
    """
    url: str = Field(..., description="Target URL to crawl")
    crawl_type: str = Field("single", pattern="^(single|all)$", description="Crawl depth: single or all (up to 10 pages)")
    proxy_mode: str = Field("basic", pattern="^(basic|stealth|enhanced)$", description="Proxy mode for scraping")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "crawl_type": "single",
                "proxy_mode": "basic"
            }
        }


class DatabaseConnectionRegister(BaseModel):
    """
    Schema to register/associate a database connection with an Agent KB.
    """
    db_type: str = Field(..., description="Database type: 'sqlite' or 'postgresql'")
    connection_params: dict = Field(..., description="JSON credentials/paths for the database connection")

    class Config:
        json_schema_extra = {
            "example": {
                "db_type": "sqlite",
                "connection_params": {
                    "filepath": "tester_zone/company.db"
                }
            }
        }


class DatabaseConnectionResponse(BaseModel):
    """
    Response schema for registered database connection details.
    """
    id: UUID
    tenant_id: UUID
    kb_id: UUID
    db_type: str
    connection_params: dict
    last_synced_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DatabaseValidationResponse(BaseModel):
    """
    Schema returning the result of connection validation or schema discovery.
    """
    success: bool
    message: str
    tables: Optional[list[str]] = None
    schema_details: Optional[dict] = None
