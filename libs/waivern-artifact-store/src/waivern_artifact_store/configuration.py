"""Artifact store configuration with DI and environment variable support.

Each backend defines its own config class with a `create_store()` method.
Pydantic's discriminated union handles deserialisation automatically.

Stores are stateless singletons - create_store() takes no parameters.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, RootModel

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.filesystem import LocalFilesystemStore
from waivern_artifact_store.in_memory import AsyncInMemoryStore


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
_ArtifactStoreConfigUnion = Annotated[
    MemoryStoreConfig | FilesystemStoreConfig | RemoteStoreConfig,
    Field(discriminator="type"),
]


class ArtifactStoreConfiguration(RootModel[_ArtifactStoreConfigUnion]):
    """Artifact store configuration with automatic type selection.

    Uses Pydantic's discriminated union to automatically deserialise to the
    correct config class (MemoryStoreConfig, FilesystemStoreConfig, or
    RemoteStoreConfig) based on the "type" field.

    Stores are stateless singletons - create_store() takes no parameters.
    This enables standard DI patterns where factory.create() takes no arguments.

    Example:
        >>> config = ArtifactStoreConfiguration.model_validate({"type": "filesystem"})
        >>> store = config.create_store()

        >>> # Access the inner config if needed
        >>> config.root.base_path
        PosixPath('.waivern')

        >>> # From environment variables
        >>> # WAIVERN_STORE_TYPE=filesystem
        >>> # WAIVERN_STORE_PATH=/data/waivern
        >>> config = ArtifactStoreConfiguration.from_properties({})

    """

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from properties with environment fallback.

        This method implements a layered configuration system:
        1. Explicit properties (highest priority)
        2. Environment variables (fallback)
        3. Defaults (lowest priority)

        Environment variables used:
        - WAIVERN_STORE_TYPE: Store type (memory, filesystem, remote). Default: memory
        - WAIVERN_STORE_PATH: Base path for filesystem store. Default: .waivern
        - WAIVERN_STORE_URL: Endpoint URL for remote store
        - WAIVERN_STORE_API_KEY: API key for remote store

        Args:
            properties: Configuration properties dictionary

        Returns:
            Validated configuration instance

        Raises:
            ValidationError: If configuration is invalid

        """
        config_data = properties.copy()

        # Type (env fallback with default)
        if "type" not in config_data:
            config_data["type"] = os.getenv("WAIVERN_STORE_TYPE", "memory")

        store_type = config_data["type"]

        # Filesystem-specific: base_path
        if store_type == "filesystem" and "base_path" not in config_data:
            base_path = os.getenv("WAIVERN_STORE_PATH")
            if base_path:
                config_data["base_path"] = base_path

        # Remote-specific: endpoint_url and api_key
        if store_type == "remote":
            if "endpoint_url" not in config_data:
                endpoint_url = os.getenv("WAIVERN_STORE_URL")
                if endpoint_url:
                    config_data["endpoint_url"] = endpoint_url

            if "api_key" not in config_data:
                api_key = os.getenv("WAIVERN_STORE_API_KEY")
                if api_key:
                    config_data["api_key"] = api_key

        return cls.model_validate(config_data)

    def create_store(self) -> ArtifactStore:
        """Create a singleton store instance.

        Delegates to the inner config's create_store method.

        Returns:
            An ArtifactStore instance.

        """
        return self.root.create_store()
