"""Async ArtifactStore interface (stateless, run_id per operation).

This module defines the abstract base class for persistent artifact stores.
The interface is stateless - run_id is passed to each operation, enabling:
- Singleton stores (one instance shared across all runs)
- Standard DI patterns (factory.create() takes no parameters)
- Resource sharing (HTTP clients, connection pools held by store)
- Run isolation (run_id parameter scopes each operation)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from waivern_core import JsonValue
from waivern_core.message import Message


class ArtifactStore(ABC):
    """Abstract base class for async artifact store implementations.

    Stateless interface where run_id is passed to each operation.
    This enables singleton stores compatible with standard DI patterns.

    Supports multiple backends: local filesystem, remote HTTP, in-memory (testing).

    This interface provides semantic methods for artifacts and system metadata.
    Implementations handle the internal storage structure (e.g., prefixes,
    directories) internally.
    """

    # ========================================================================
    # Artifact Operations
    # ========================================================================

    @abstractmethod
    async def save_artifact(
        self, run_id: str, artifact_id: str, message: Message
    ) -> None:
        """Store an artifact by its ID.

        Uses upsert semantics - if the artifact already exists, it is overwritten.
        The artifact is stored in an implementation-specific location
        (e.g., 'artifacts/' subdirectory for filesystem stores).

        Args:
            run_id: Unique identifier for the run.
            artifact_id: The artifact identifier (e.g., 'source_data', 'findings').
            message: The artifact data to store.

        """
        ...

    @abstractmethod
    async def get_artifact(self, run_id: str, artifact_id: str) -> Message:
        """Retrieve an artifact by its ID.

        Args:
            run_id: Unique identifier for the run.
            artifact_id: The artifact identifier to retrieve.

        Returns:
            The stored artifact message.

        Raises:
            ArtifactNotFoundError: If artifact with this ID does not exist.

        """
        ...

    @abstractmethod
    async def artifact_exists(self, run_id: str, artifact_id: str) -> bool:
        """Check if an artifact exists.

        Args:
            run_id: Unique identifier for the run.
            artifact_id: The artifact identifier to check.

        Returns:
            True if artifact exists, False otherwise.

        """
        ...

    @abstractmethod
    async def delete_artifact(self, run_id: str, artifact_id: str) -> None:
        """Delete an artifact by its ID.

        No-op if the artifact does not exist.

        Args:
            run_id: Unique identifier for the run.
            artifact_id: The artifact identifier to delete.

        """
        ...

    @abstractmethod
    async def list_artifacts(self, run_id: str) -> list[str]:
        """List all artifact IDs for a run.

        Returns artifact IDs without any internal prefix (e.g., 'source_data',
        'findings', not 'artifacts/source_data').

        Args:
            run_id: Unique identifier for the run.

        Returns:
            List of artifact IDs. Empty list if no artifacts exist.

        """
        ...

    @abstractmethod
    async def clear_artifacts(self, run_id: str) -> None:
        """Remove all artifacts for a run.

        System metadata (execution state, run metadata) is preserved.

        Args:
            run_id: Unique identifier for the run.

        """
        ...

    # ========================================================================
    # System Metadata Operations (raw dict to avoid circular imports)
    # ========================================================================

    @abstractmethod
    async def save_execution_state(
        self, run_id: str, state_data: dict[str, JsonValue]
    ) -> None:
        """Persist execution state for a run.

        Args:
            run_id: Unique identifier for the run.
            state_data: The execution state as a dictionary.

        """
        ...

    @abstractmethod
    async def load_execution_state(self, run_id: str) -> dict[str, JsonValue]:
        """Load execution state for a run.

        Args:
            run_id: Unique identifier for the run.

        Returns:
            The execution state as a dictionary.

        Raises:
            ArtifactNotFoundError: If state does not exist for this run.

        """
        ...

    @abstractmethod
    async def save_run_metadata(
        self, run_id: str, metadata: dict[str, JsonValue]
    ) -> None:
        """Persist run metadata.

        Args:
            run_id: Unique identifier for the run.
            metadata: The run metadata as a dictionary.

        """
        ...

    @abstractmethod
    async def load_run_metadata(self, run_id: str) -> dict[str, JsonValue]:
        """Load run metadata.

        Args:
            run_id: Unique identifier for the run.

        Returns:
            The run metadata as a dictionary.

        Raises:
            ArtifactNotFoundError: If metadata does not exist for this run.

        """
        ...

    # ========================================================================
    # Run Enumeration
    # ========================================================================

    @abstractmethod
    async def list_runs(self) -> list[str]:
        """List all run IDs in the store.

        Returns:
            List of run IDs. Empty list if no runs exist.

        """
        ...
