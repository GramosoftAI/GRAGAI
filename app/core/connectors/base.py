"""Abstract base classes and contracts for the connector framework"""

import abc
from collections.abc import Generator, Iterator
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel

from .models import ConnectorCheckpoint, SlimDocument, HierarchyNode

# Define generic checkpoint type variable bound to ConnectorCheckpoint
CT = TypeVar("CT", bound=ConnectorCheckpoint)


class NormalizationResult(BaseModel):
    """
    Result of a URL canonicalization attempt.
    """
    normalized_url: Optional[str] = None
    use_default: bool = False


class BaseConnector(abc.ABC, Generic[CT]):
    """
    Root interface for all data sources in the connector framework.
    """

    @abc.abstractmethod
    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        """
        Parse configuration dictionary, load client credentials, and initialize sessions.
        Returns a dictionary of updated/refreshed credential metadata, or None.
        """
        raise NotImplementedError

    def validate_connector_settings(self) -> None:
        """
        Perform validation check on connection parameters and credentials.
        Should raise an exception if invalid, otherwise do nothing (no-op by default).
        """
        pass

    @classmethod
    def normalize_url(cls, url: str) -> NormalizationResult:
        """
        Normalize a document web URL to match canonical GraphMind document identifiers.
        Allows custom URL cleaning per crawler (defaults to using the application default).
        """
        return NormalizationResult(normalized_url=None, use_default=True)


class SlimConnector(BaseConnector[CT], abc.ABC):
    """
    Interface for connectors that retrieve document identifiers and metadata only.
    Optimizes indexing times by avoiding raw download transfers where possible.
    """

    @abc.abstractmethod
    def retrieve_all_slim_docs(
        self,
        start: float | None = None,
        end: float | None = None,
    ) -> Iterator[list[SlimDocument | HierarchyNode]]:
        """
        Scan the source and yield lists of metadata slim documents and hierarchy folders.
        """
        raise NotImplementedError


class CheckpointedConnector(BaseConnector[CT], abc.ABC):
    """
    Interface for connectors that manage incremental, state-tokenized crawling.
    """

    @abc.abstractmethod
    def load_from_checkpoint(
        self,
        start: float,
        end: float,
        checkpoint: CT,
    ) -> Generator[SlimDocument | HierarchyNode, None, None]:
        """
        Sync files incrementally using the checkpoint state.
        Yields SlimDocument or HierarchyNode, and returns the next checkpoint when finished or paused.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def build_dummy_checkpoint(self) -> CT:
        """
        Generate an empty starting checkpoint instance.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def validate_checkpoint_json(self, checkpoint_json: str) -> CT:
        """
        Validate and deserialize a checkpoint JSON string back to the concrete CT checkpoint type.
        """
        raise NotImplementedError
