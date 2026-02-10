"""Local filesystem artifact store implementation.

Maps artifact IDs and system metadata to filesystem paths under
`.waivern/runs/{run_id}/`. Uses aiofiles for async I/O operations.

Storage structure:
    {base_path}/runs/{run_id}/
        ├── _system/
        │   ├── run.json          # RunMetadata
        │   └── state.json        # ExecutionState
        ├── artifacts/
        │   ├── {artifact_id}.json
        │   └── ...
        ├── llm_cache/
        │   ├── {cache_key}.json
        │   └── ...
        └── batch_jobs/
            ├── {batch_id}.json
            └── ...
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast, override

import aiofiles
from waivern_core import JsonValue
from waivern_core.message import Message

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.errors import ArtifactNotFoundError, ArtifactStoreError


class LocalFilesystemStore(ArtifactStore):
    """Filesystem-backed artifact store with run-scoped isolation.

    Stateless singleton that stores artifacts on the local filesystem.
    Artifacts are stored in 'artifacts/' subdirectory, system metadata
    in '_system/' subdirectory.
    """

    # Internal storage prefixes
    _ARTIFACTS_PREFIX = "artifacts"
    _SYSTEM_PREFIX = "_system"
    _LLM_CACHE_PREFIX = "llm_cache"
    _BATCH_JOBS_PREFIX = "batch_jobs"

    # System file keys
    _STATE_KEY = f"{_SYSTEM_PREFIX}/state"
    _RUN_METADATA_KEY = f"{_SYSTEM_PREFIX}/run"

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

    def _artifact_key(self, artifact_id: str) -> str:
        """Convert artifact ID to internal storage key."""
        return f"{self._ARTIFACTS_PREFIX}/{artifact_id}"

    def _cache_key(self, key: str) -> str:
        """Convert cache key to internal storage key."""
        return f"{self._LLM_CACHE_PREFIX}/{key}"

    def _batch_job_key(self, batch_id: str) -> str:
        """Convert batch job ID to internal storage key."""
        return f"{self._BATCH_JOBS_PREFIX}/{batch_id}"

    # ========================================================================
    # Artifact Operations
    # ========================================================================

    @override
    async def save_artifact(
        self, run_id: str, artifact_id: str, message: Message
    ) -> None:
        """Store artifact by ID (in artifacts/ subdirectory)."""
        key = self._artifact_key(artifact_id)
        file_path = self._key_to_path(run_id, key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = message.to_dict()
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str))

    @override
    async def get_artifact(self, run_id: str, artifact_id: str) -> Message:
        """Retrieve artifact by ID (from artifacts/ subdirectory)."""
        key = self._artifact_key(artifact_id)
        file_path = self._key_to_path(run_id, key)

        if not file_path.exists():
            raise ArtifactNotFoundError(
                f"Artifact '{artifact_id}' not found in run '{run_id}'."
            )

        async with aiofiles.open(file_path) as f:
            content = await f.read()
        data = json.loads(content)
        return Message.from_dict(data)

    @override
    async def artifact_exists(self, run_id: str, artifact_id: str) -> bool:
        """Check if artifact exists."""
        key = self._artifact_key(artifact_id)
        return self._key_to_path(run_id, key).exists()

    @override
    async def delete_artifact(self, run_id: str, artifact_id: str) -> None:
        """Delete artifact by ID."""
        key = self._artifact_key(artifact_id)
        file_path = self._key_to_path(run_id, key)
        if file_path.exists():
            file_path.unlink()

    @override
    async def list_artifacts(self, run_id: str) -> list[str]:
        """List all artifact IDs for a run (without artifacts/ prefix)."""
        artifacts_dir = self._run_dir(run_id) / self._ARTIFACTS_PREFIX
        if not artifacts_dir.exists():
            return []

        artifact_ids: list[str] = []
        for file_path in artifacts_dir.rglob("*.json"):
            # Convert path to artifact ID (relative to artifacts_dir, without .json)
            relative_path = file_path.relative_to(artifacts_dir)
            artifact_id = str(relative_path.with_suffix(""))
            artifact_ids.append(artifact_id)

        return sorted(artifact_ids)

    @override
    async def clear_artifacts(self, run_id: str) -> None:
        """Remove all artifacts for a run (preserves system metadata)."""
        artifacts_dir = self._run_dir(run_id) / self._ARTIFACTS_PREFIX
        if not artifacts_dir.exists():
            return

        # Delete all artifact files
        for file_path in artifacts_dir.rglob("*.json"):
            file_path.unlink()

        # Clean up empty directories
        for dir_path in sorted(artifacts_dir.rglob("*"), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()

        # Remove artifacts directory itself if empty
        if artifacts_dir.exists() and not any(artifacts_dir.iterdir()):
            artifacts_dir.rmdir()

    # ========================================================================
    # System Metadata Operations
    # ========================================================================

    @override
    async def save_execution_state(
        self, run_id: str, state_data: dict[str, JsonValue]
    ) -> None:
        """Persist execution state to _system/state.json."""
        file_path = self._key_to_path(run_id, self._STATE_KEY)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(state_data, indent=2))

    @override
    async def load_execution_state(self, run_id: str) -> dict[str, JsonValue]:
        """Load execution state from _system/state.json."""
        file_path = self._key_to_path(run_id, self._STATE_KEY)

        if not file_path.exists():
            raise ArtifactNotFoundError(
                f"Execution state not found for run '{run_id}'."
            )

        async with aiofiles.open(file_path) as f:
            content = await f.read()
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ArtifactStoreError(
                f"Invalid execution state format for run '{run_id}': expected dict."
            )
        return cast(dict[str, JsonValue], data)

    @override
    async def save_run_metadata(
        self, run_id: str, metadata: dict[str, JsonValue]
    ) -> None:
        """Persist run metadata to _system/run.json."""
        file_path = self._key_to_path(run_id, self._RUN_METADATA_KEY)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(metadata, indent=2))

    @override
    async def load_run_metadata(self, run_id: str) -> dict[str, JsonValue]:
        """Load run metadata from _system/run.json."""
        file_path = self._key_to_path(run_id, self._RUN_METADATA_KEY)

        if not file_path.exists():
            raise ArtifactNotFoundError(f"Run metadata not found for run '{run_id}'.")

        async with aiofiles.open(file_path) as f:
            content = await f.read()
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ArtifactStoreError(
                f"Invalid run metadata format for run '{run_id}': expected dict."
            )
        return cast(dict[str, JsonValue], data)

    # ========================================================================
    # Run Enumeration
    # ========================================================================

    @override
    async def list_runs(self) -> list[str]:
        """List all run IDs in the store."""
        runs_dir = self._base_path / "runs"
        if not runs_dir.exists():
            return []

        return sorted(d.name for d in runs_dir.iterdir() if d.is_dir())

    # ========================================================================
    # Batch Job Operations
    # ========================================================================

    @override
    async def save_batch_job(
        self, run_id: str, batch_id: str, data: dict[str, JsonValue]
    ) -> None:
        """Store batch job data to batch_jobs/{batch_id}.json."""
        file_path = self._key_to_path(run_id, self._batch_job_key(batch_id))
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    @override
    async def load_batch_job(self, run_id: str, batch_id: str) -> dict[str, JsonValue]:
        """Load batch job data from batch_jobs/{batch_id}.json."""
        file_path = self._key_to_path(run_id, self._batch_job_key(batch_id))

        if not file_path.exists():
            raise ArtifactNotFoundError(
                f"Batch job '{batch_id}' not found for run '{run_id}'."
            )

        async with aiofiles.open(file_path) as f:
            content = await f.read()
        data = json.loads(content)
        return cast(dict[str, JsonValue], data)

    @override
    async def list_batch_jobs(self, run_id: str) -> list[str]:
        """List all batch job IDs for a run."""
        batch_dir = self._run_dir(run_id) / self._BATCH_JOBS_PREFIX
        if not batch_dir.exists():
            return []

        return sorted(f.stem for f in batch_dir.glob("*.json"))

    # ========================================================================
    # LLM Cache Operations
    # ========================================================================

    async def cache_get(self, run_id: str, key: str) -> dict[str, JsonValue] | None:
        """Retrieve a cache entry by key."""
        file_path = self._key_to_path(run_id, self._cache_key(key))

        if not file_path.exists():
            return None

        async with aiofiles.open(file_path) as f:
            content = await f.read()
        data = json.loads(content)
        return cast(dict[str, JsonValue], data)

    async def cache_set(
        self, run_id: str, key: str, entry: dict[str, JsonValue]
    ) -> None:
        """Store a cache entry (upsert semantics)."""
        file_path = self._key_to_path(run_id, self._cache_key(key))
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(entry, indent=2))

    async def cache_delete(self, run_id: str, key: str) -> None:
        """Delete a cache entry by key (no-op if not found)."""
        file_path = self._key_to_path(run_id, self._cache_key(key))
        if file_path.exists():
            file_path.unlink()

    async def cache_clear(self, run_id: str) -> None:
        """Delete all cache entries for a run."""
        cache_dir = self._run_dir(run_id) / self._LLM_CACHE_PREFIX
        if not cache_dir.exists():
            return

        # Delete all cache files
        for file_path in cache_dir.rglob("*.json"):
            file_path.unlink()

        # Remove cache directory if empty
        if cache_dir.exists() and not any(cache_dir.iterdir()):
            cache_dir.rmdir()
