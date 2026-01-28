"""Persistent artifact store implementations.

This submodule provides async artifact stores with run_id scoping,
supporting multiple backends (filesystem, remote, in-memory for testing).

The strangler fig pattern is used: this new code coexists with the
legacy sync interface until migration is complete.

Configuration classes have been moved to the root module:
    from waivern_artifact_store.configuration import (
        ArtifactStoreConfiguration,
        MemoryStoreConfig,
        FilesystemStoreConfig,
        RemoteStoreConfig,
    )
"""

from waivern_artifact_store.persistent.base import ArtifactStore
from waivern_artifact_store.persistent.filesystem import LocalFilesystemStore
from waivern_artifact_store.persistent.in_memory import AsyncInMemoryStore

__all__ = [
    "ArtifactStore",
    "AsyncInMemoryStore",
    "LocalFilesystemStore",
]
