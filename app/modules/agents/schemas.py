"""Pydantic schemas for Agent request/response validation"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class AgentCreate(BaseModel):
    """
    Schema for creating a new agent.

    REQUIRED:
    - name: Agent name
    - personality: Agent tone (Friendly, Formal, Sales, Technical, Concise)

    OPTIONAL:
    - system_prompt: Optional but recommended for specific agent behavior
    """

    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    personality: Optional[str] = Field(
        "Friendly", max_length=255, description="Agent tone/personality (e.g., Friendly, Formal, Sales, Technical, Concise)"
    )
    personality_id: Optional[UUID] = Field(
        None, description="Linked personality ID from personalities table"
    )
    system_prompt: Optional[str] = Field(
        None,
        description="System prompt for specific agent behavior (e.g., 'You are a Python expert...')",
    )
    agent_type: str = Field("platform", description="'platform' or 'integrated'")
    organization_name: Optional[str] = Field(None, description="Organization Name")
    contact_phone: Optional[str] = Field(None, description="Contact Phone")
    contact_email: Optional[str] = Field(None, description="Contact Email")
    website_url: Optional[str] = Field(None, description="Website URL")
    fallback_message_enabled: bool = Field(True, description="Enable fallback message")
    brand_persona: Optional[str] = Field(None, description="Brand persona for integrated agents")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Research Agent",
                "personality": "Technical",
                "system_prompt": "You are an expert researcher. Always cite sources and provide accurate information.",
            }
        }


class AgentUpdate(BaseModel):
    """
    Schema for updating an existing agent.

    All fields are optional (PATCH semantics).
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    personality: Optional[str] = Field(None, max_length=255)
    personality_id: Optional[UUID] = Field(None)
    system_prompt: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)
    agent_type: Optional[str] = Field(None)
    organization_name: Optional[str] = Field(None)
    contact_phone: Optional[str] = Field(None)
    contact_email: Optional[str] = Field(None)
    website_url: Optional[str] = Field(None)
    fallback_message_enabled: Optional[bool] = Field(None)
    brand_persona: Optional[str] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Agent Name",
                "personality": "Sales",
                "system_prompt": "New system prompt...",
            }
        }


class AgentResponse(BaseModel):
    """
    Schema for agent response (read-only).

    Returned by GET endpoints.
    Includes deleted_at for soft-deleted agents.
    """

    id: UUID
    tenant_id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    personality: Optional[str]
    personality_id: Optional[UUID]
    system_prompt: Optional[str]
    agent_type: str
    organization_name: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    website_url: Optional[str]
    fallback_message_enabled: bool
    brand_persona: Optional[str]
    is_active: bool
    deleted_at: Optional[datetime] = Field(
        None, description="Soft delete timestamp (null = not deleted)"
    )
    created_at: datetime
    updated_at: datetime
    connected_integrations: list[str] = Field(default_factory=list, description="List of integrations connected to any KB of this agent")

    class Config:
        from_attributes = True  # SQLAlchemy ORM mode
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
                "user_id": "550e8400-e29b-41d4-a716-446655440002",
                "name": "Research Agent",
                "personality": "Technical",
                "system_prompt": "You are an expert researcher...",
                "is_active": True,
                "deleted_at": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }


class AgentListResponse(BaseModel):
    """Schema for paginated agent listing."""

    agents: list[AgentResponse]
    count: int
    total: int


class AgentEnhancedResponse(BaseModel):
    """
    EXTENDED Response including User Name, KB ID, and Tenant info.
    Required for administrative and audit dashboard views.
    """

    agent_id: UUID
    agent_name: str
    owner_id: UUID
    owner_name: str
    tenant_id: UUID
    tenant_name: str
    kb_id: Optional[UUID]
    is_active: bool
    created_at: datetime
    connected_integrations: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AgentEnhancedListResponse(BaseModel):
    """Paginated list of enhanced agents"""

    agents: list[AgentEnhancedResponse]
    count: int
    total: int


class AgentDeleteResponse(BaseModel):
    """Schema for delete response"""

    id: UUID
    deleted_at: datetime
    message: str = "Agent deleted successfully"
