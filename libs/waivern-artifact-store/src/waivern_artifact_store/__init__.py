"""Artifact storage service for Waivern Compliance Framework."""

# Async interface (stateless, run_id per operation)
# Configuration (discriminated union pattern)
from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.configuration import (
    ArtifactStoreConfiguration,
    FilesystemStoreConfig,
    MemoryStoreConfig,
    RemoteStoreConfig,
)
from waivern_artifact_store.errors import ArtifactNotFoundError, ArtifactStoreError
from waivern_artifact_store.factory import ArtifactStoreFactory
from waivern_artifact_store.llm_cache import LLMCache

__all__ = [
    # Async interface
    "ArtifactStore",
    # Protocols
    "LLMCache",
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
