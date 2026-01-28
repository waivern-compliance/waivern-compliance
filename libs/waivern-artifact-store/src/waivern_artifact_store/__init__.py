"""Artifact storage service for Waivern Compliance Framework."""

# New async interface (stateless, run_id per operation)
# Legacy sync interface (to be removed in 1.8)
from waivern_artifact_store.base import ArtifactStore as LegacyArtifactStore

# Configuration (new discriminated union pattern)
from waivern_artifact_store.configuration import (
    ArtifactStoreConfiguration,
    FilesystemStoreConfig,
    MemoryStoreConfig,
    RemoteStoreConfig,
)
from waivern_artifact_store.errors import ArtifactNotFoundError, ArtifactStoreError
from waivern_artifact_store.factory import ArtifactStoreFactory
from waivern_artifact_store.in_memory import InMemoryArtifactStore
from waivern_artifact_store.persistent.base import ArtifactStore

__all__ = [
    # New async interface (preferred)
    "ArtifactStore",
    # Configuration
    "ArtifactStoreConfiguration",
    "ArtifactStoreFactory",
    "FilesystemStoreConfig",
    "MemoryStoreConfig",
    "RemoteStoreConfig",
    # Errors
    "ArtifactStoreError",
    "ArtifactNotFoundError",
    # Legacy (to be removed in 1.8)
    "LegacyArtifactStore",
    "InMemoryArtifactStore",
]
