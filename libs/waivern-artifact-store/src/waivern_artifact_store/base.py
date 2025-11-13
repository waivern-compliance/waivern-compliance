"""Base ArtifactStore interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from waivern_core.message import Message


class ArtifactStore(ABC):
    """Abstract base class for artifact store implementations.

    This class defines the interface that all artifact store providers must implement,
    enabling support for multiple backends (in-memory, Redis, S3, etc.) with
    a unified interface for pipeline artifact management.
    """

    @abstractmethod
    def save(self, step_id: str, message: Message) -> None:
        """Store artifact from completed step.

        Args:
            step_id: Unique identifier for the step that produced this artifact
            message: The artifact data to store

        """
        pass

    @abstractmethod
    def get(self, step_id: str) -> Message:
        """Retrieve artifact for downstream step.

        Args:
            step_id: Unique identifier for the step artifact to retrieve

        Returns:
            The stored artifact

        Raises:
            ArtifactNotFoundError: If artifact with step_id does not exist

        """
        pass

    @abstractmethod
    def exists(self, step_id: str) -> bool:
        """Check if artifact exists in storage.

        Args:
            step_id: Unique identifier for the step artifact

        Returns:
            True if artifact exists, False otherwise

        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Remove all artifacts from storage.

        This is called at the end of pipeline execution to clean up resources.
        """
        pass
