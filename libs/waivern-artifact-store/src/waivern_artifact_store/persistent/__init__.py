"""Persistent artifact store implementations.

This submodule provides async artifact stores with run_id scoping,
supporting multiple backends (filesystem, remote, in-memory for testing).

The strangler fig pattern is used: this new code coexists with the
legacy sync interface until migration is complete.
"""

from waivern_artifact_store.persistent.base import ArtifactStore

__all__ = ["ArtifactStore"]
