"""Artifact storage service for Waivern Compliance Framework."""

# Async interface (stateless, run_id per operation)
# Configuration (discriminated union pattern)
from waivern_artifact_store.configuration import (
    ArtifactStoreConfiguration,
    FilesystemStoreConfig,
    MemoryStoreConfig,
    RemoteStoreConfig,
)
from waivern_artifact_store.errors import ArtifactNotFoundError, ArtifactStoreError
from waivern_artifact_store.factory import ArtifactStoreFactory
from waivern_artifact_store.persistent.base import ArtifactStore

__all__ = [
    # Async interface
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
]
