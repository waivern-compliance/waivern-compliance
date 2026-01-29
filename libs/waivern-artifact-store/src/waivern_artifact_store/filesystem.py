"""Local filesystem artifact store implementation.

Maps keys to filesystem paths under `.waivern/runs/{run_id}/{key}.json`.
Uses aiofiles for async I/O operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import override

import aiofiles
from waivern_core.message import Message

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.errors import ArtifactNotFoundError


class LocalFilesystemStore(ArtifactStore):
    """Filesystem-backed artifact store with run-scoped isolation.

    Stateless singleton that stores artifacts on the local filesystem.
    Storage structure:
        {base_path}/runs/{run_id}/{key}.json

    Keys support hierarchical paths (e.g., 'artifacts/findings') which
    map to nested directories on the filesystem.
    """

    # Reserved prefix for system metadata (excluded from list_keys)
    _SYSTEM_PREFIX = "_system"

    def __init__(self, base_path: Path) -> None:
        """Initialise filesystem store.

        Args:
            base_path: Root directory for storage (e.g., Path('.waivern')).

        """
        self._base_path = base_path

    @property
    def base_path(self) -> Path:
        """The base path for storage."""
        return self._base_path

    def _run_dir(self, run_id: str) -> Path:
        """Get the directory for a run's artifacts."""
        return self._base_path / "runs" / run_id

    def _validate_key(self, key: str) -> None:
        """Validate that a key is safe for filesystem use.

        Raises:
            ValueError: If key contains path traversal or is absolute.

        """
        if ".." in key:
            raise ValueError(
                f"Invalid key '{key}': path traversal sequences (..) are not allowed."
            )
        if key.startswith("/"):
            raise ValueError(f"Invalid key '{key}': absolute paths are not allowed.")

    def _key_to_path(self, run_id: str, key: str) -> Path:
        """Convert a key to its filesystem path.

        Validates the key before conversion.
        """
        self._validate_key(key)
        return self._run_dir(run_id) / f"{key}.json"

    @override
    async def save(self, run_id: str, key: str, message: Message) -> None:
        """Store artifact by key.

        Creates parent directories if they don't exist.
        Uses upsert semantics - overwrites if key already exists.
        """
        file_path = self._key_to_path(run_id, key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = message.to_dict()
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str))

    @override
    async def get(self, run_id: str, key: str) -> Message:
        """Retrieve artifact by key.

        Raises:
            ArtifactNotFoundError: If artifact with key does not exist.

        """
        file_path = self._key_to_path(run_id, key)

        if not file_path.exists():
            raise ArtifactNotFoundError(
                f"Artifact '{key}' not found in run '{run_id}'."
            )

        async with aiofiles.open(file_path) as f:
            content = await f.read()
        data = json.loads(content)
        return Message.from_dict(data)

    @override
    async def exists(self, run_id: str, key: str) -> bool:
        """Check if artifact exists."""
        return self._key_to_path(run_id, key).exists()

    @override
    async def delete(self, run_id: str, key: str) -> None:
        """Delete artifact by key.

        No-op if the key does not exist.
        """
        file_path = self._key_to_path(run_id, key)
        if file_path.exists():
            file_path.unlink()

    @override
    async def list_keys(self, run_id: str, prefix: str = "") -> list[str]:
        """List all keys for a run, optionally filtered by prefix.

        Returns keys in the format they were saved (e.g., 'artifacts/findings').
        System files under '_system/' are excluded.
        """
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return []

        keys: list[str] = []
        for file_path in run_dir.rglob("*.json"):
            # Convert path back to key (relative to run_dir, without .json)
            relative_path = file_path.relative_to(run_dir)
            key = str(relative_path.with_suffix(""))

            # Skip system files
            if key.startswith(self._SYSTEM_PREFIX):
                continue

            # Filter by prefix if provided
            if not prefix or key.startswith(prefix):
                keys.append(key)

        return keys

    @override
    async def clear(self, run_id: str) -> None:
        """Remove all artifacts for a run.

        Removes all artifact files but preserves system metadata in '_system/'.
        Also cleans up empty directories.
        """
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return

        # Delete all artifact files (excluding system files)
        for file_path in run_dir.rglob("*.json"):
            relative_path = file_path.relative_to(run_dir)
            key = str(relative_path.with_suffix(""))

            # Skip system files
            if key.startswith(self._SYSTEM_PREFIX):
                continue

            file_path.unlink()

        # Clean up empty directories (except _system and run_dir itself)
        for dir_path in sorted(run_dir.rglob("*"), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                if not str(dir_path.relative_to(run_dir)).startswith(
                    self._SYSTEM_PREFIX
                ):
                    dir_path.rmdir()
