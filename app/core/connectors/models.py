"""Foundational Pydantic models for the connector framework"""

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

class SlimDocument(BaseModel):
    """
    Minimal representation of a document fetched from a connector source.
    Contains metadata and identifiers suitable for deduplication and sync status updates.
    """
    id: str
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HierarchyNode(BaseModel):
    """
    Represents a directory, folder, or drive node in a hierarchical source structure.
    Used to rebuild directory graphs inside Neo4j.
    """
    raw_node_id: str
    raw_parent_id: Optional[str] = None
    display_name: str
    link: Optional[str] = None
    node_type: str  # e.g., "folder", "shared_drive"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StageCompletion(BaseModel):
    """
    Tracks indexing progress for a specific sub-stage or user boundary within a connector run.
    """
    stage: str = "start"
    completed_until: float = 0.0
    current_folder_or_drive_id: Optional[str] = None
    next_page_token: Optional[str] = None
    processed_drive_ids: Set[str] = Field(default_factory=set)

    def update(
        self,
        stage: str,
        completed_until: float,
        current_folder_or_drive_id: Optional[str] = None,
        next_page_token: Optional[str] = None,
    ) -> None:
        self.stage = stage
        self.completed_until = completed_until
        if current_folder_or_drive_id is not None:
            self.current_folder_or_drive_id = current_folder_or_drive_id
        if next_page_token is not None:
            self.next_page_token = next_page_token


class ConnectorCheckpoint(BaseModel):
    """
    Checkpoint token passed between crawler cycles.
    Tracks pagination tokens, completed stages, and already retrieved files to make the crawler resumeable.
    """
    has_more: bool = True
    completion_stage: str = "start"
    completion_map: Dict[str, StageCompletion] = Field(default_factory=dict)
    user_emails: Optional[List[str]] = None
    drive_ids_to_retrieve: Optional[List[str]] = None
    folder_ids_to_retrieve: Optional[List[str]] = None
    all_retrieved_file_ids: Set[str] = Field(default_factory=set)
    failed_folder_ids_by_email: Dict[str, Set[str]] = Field(default_factory=dict)
