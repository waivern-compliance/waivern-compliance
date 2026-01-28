"""Store configuration classes using hybrid Protocol + discriminated union pattern.

Each backend defines its own config class with a `create_store()` method.
Pydantic's discriminated union handles deserialisation automatically.

Stores are stateless singletons - create_store() takes no parameters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, RootModel

from waivern_artifact_store.persistent.base import ArtifactStore
from waivern_artifact_store.persistent.filesystem import LocalFilesystemStore
from waivern_artifact_store.persistent.in_memory import AsyncInMemoryStore


class StoreConfigProtocol(Protocol):
    """Protocol defining what all store configs must implement."""

    def create_store(self) -> ArtifactStore:
        """Create a singleton store instance."""
        ...


class MemoryStoreConfig(BaseModel):
    """Config for in-memory store (testing, ephemeral runs)."""

    type: Literal["memory"] = "memory"

    def create_store(self) -> ArtifactStore:
        """Create an in-memory artifact store."""
        return AsyncInMemoryStore()


class FilesystemStoreConfig(BaseModel):
    """Config for local filesystem store."""

    type: Literal["filesystem"] = "filesystem"
    base_path: Path = Path(".waivern")

    def create_store(self) -> ArtifactStore:
        """Create a filesystem-backed artifact store."""
        return LocalFilesystemStore(base_path=self.base_path)


class RemoteStoreConfig(BaseModel):
    """Config for remote HTTP store (SaaS backend)."""

    type: Literal["remote"] = "remote"
    endpoint_url: str
    api_key: str | None = None

    def create_store(self) -> ArtifactStore:
        """Create a remote HTTP artifact store.

        Raises:
            NotImplementedError: RemoteHttpArtifactStore not yet implemented (Phase 5).

        """
        raise NotImplementedError(
            "RemoteHttpArtifactStore not yet implemented. See Phase 5 of the "
            "persistent artifact store design."
        )


# Type alias for the union of all config types
_StoreConfigUnion = Annotated[
    MemoryStoreConfig | FilesystemStoreConfig | RemoteStoreConfig,
    Field(discriminator="type"),
]


class StoreConfig(RootModel[_StoreConfigUnion]):
    """Store configuration with automatic type selection based on 'type' field.

    Uses Pydantic's discriminated union to automatically deserialise to the
    correct config class (MemoryStoreConfig, FilesystemStoreConfig, or
    RemoteStoreConfig) based on the "type" field.

    Stores are stateless singletons - create_store() takes no parameters.

    Example:
        >>> config = StoreConfig.model_validate({"type": "filesystem"})
        >>> store = config.create_store()

        >>> # Access the inner config if needed
        >>> config.root.base_path
        PosixPath('.waivern')

    """

    model_config = ConfigDict(frozen=True)

    def create_store(self) -> ArtifactStore:
        """Create a singleton store instance.

        Delegates to the inner config's create_store method.

        Returns:
            An ArtifactStore instance.

        """
        return self.root.create_store()
