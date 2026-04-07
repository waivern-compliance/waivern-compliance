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
    # System Data Operations (generic key-value for run-scoped metadata)
    # ========================================================================

    @abstractmethod
    async def save_system_data(
        self, run_id: str, key: str, data: dict[str, JsonValue]
    ) -> None:
        """Persist system data for a run under the given key.

        Uses upsert semantics — overwrites if the key already exists.

        Well-known keys: ``"metadata"`` (run metadata), ``"state"``
        (execution state), ``"plan"`` (execution plan).

        Args:
            run_id: Unique identifier for the run.
            key: The system data key (e.g., ``"metadata"``, ``"state"``).
            data: The data to persist as a dictionary.

        """
        ...

    @abstractmethod
    async def load_system_data(self, run_id: str, key: str) -> dict[str, JsonValue]:
        """Load system data for a run by key.

        Args:
            run_id: Unique identifier for the run.
            key: The system data key to load.

        Returns:
            The stored data as a dictionary.

        Raises:
            ArtifactNotFoundError: If no data exists for this key.

        """
        ...

    @abstractmethod
    async def system_data_exists(self, run_id: str, key: str) -> bool:
        """Check if system data exists for a run under the given key.

        Args:
            run_id: Unique identifier for the run.
            key: The system data key to check.

        Returns:
            True if data exists for this key, False otherwise.

        """
        ...

    # ========================================================================
    # Batch Job Operations
    # ========================================================================

    @abstractmethod
    async def save_batch_job(
        self, run_id: str, batch_id: str, data: dict[str, JsonValue]
    ) -> None:
        """Store batch job data.

        Uses upsert semantics — overwrites if batch_id already exists.

        Args:
            run_id: Unique identifier for the run.
            batch_id: The provider's batch identifier.
            data: The batch job data as a dictionary.

        """
        ...

    @abstractmethod
    async def load_batch_job(self, run_id: str, batch_id: str) -> dict[str, JsonValue]:
        """Load batch job data.

        Args:
            run_id: Unique identifier for the run.
            batch_id: The provider's batch identifier.

        Returns:
            The batch job data as a dictionary.

        Raises:
            ArtifactNotFoundError: If batch job does not exist.

        """
        ...

    @abstractmethod
    async def list_batch_jobs(self, run_id: str) -> list[str]:
        """List all batch job IDs for a run.

        Args:
            run_id: Unique identifier for the run.

        Returns:
            List of batch IDs. Empty list if no batch jobs exist.

        """
        ...

    # ========================================================================
    # Prepared State Operations
    # ========================================================================

    @abstractmethod
    async def save_prepared(
        self, run_id: str, artifact_id: str, data: dict[str, JsonValue]
    ) -> None:
        """Persist prepared state for an artifact.

        Uses upsert semantics — overwrites if artifact_id already exists.

        Args:
            run_id: Unique identifier for the run.
            artifact_id: The artifact whose prepared state to store.
            data: The prepared state as a dictionary.

        """
        ...

    @abstractmethod
    async def load_prepared(
        self, run_id: str, artifact_id: str
    ) -> dict[str, JsonValue]:
        """Load prepared state for an artifact.

        Args:
            run_id: Unique identifier for the run.
            artifact_id: The artifact whose prepared state to load.

        Returns:
            The prepared state as a dictionary.

        Raises:
            ArtifactNotFoundError: If prepared state does not exist.

        """
        ...

    @abstractmethod
    async def delete_prepared(self, run_id: str, artifact_id: str) -> None:
        """Delete prepared state for an artifact.

        No-op if prepared state does not exist.

        Args:
            run_id: Unique identifier for the run.
            artifact_id: The artifact whose prepared state to delete.

        """
        ...

    @abstractmethod
    async def prepared_exists(self, run_id: str, artifact_id: str) -> bool:
        """Check if prepared state exists for an artifact.

        Args:
            run_id: Unique identifier for the run.
            artifact_id: The artifact to check.

        Returns:
            True if prepared state exists, False otherwise.

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
