# Artifact Store Architecture

This document explains the internal architecture of the Artifact Store package.

## Overview

The Artifact Store is a **storage abstraction** that holds artifacts (Messages) produced during runbook execution and system metadata for run management. It provides a semantic API with run-scoped isolation.

```
┌─────────────────────┐     ┌──────────────────────┐     ┌────────────────────┐
│ DAGExecutor         │────▶│ ArtifactStore        │◀────│ Downstream         │
│ (produces artifact) │     │ (semantic API)       │     │ Processor          │
└─────────────────────┘     └──────────────────────┘     └────────────────────┘
   store.save_artifact(       Artifacts + System         store.get_artifact(
     run_id, id, msg)         Metadata Storage             run_id, input_ref)
```

## Design Philosophy

### Stateless Stores with Run-Scoped Operations

The store interface is **stateless** — `run_id` is passed to each operation rather than at construction. This enables:

- **Singleton stores**: One instance shared across all runs (DI-friendly)
- **Resource sharing**: HTTP clients, connection pools held by store instance
- **Standard DI protocol**: `factory.create()` takes no parameters
- **Run isolation**: Each run's artifacts are completely isolated

### Semantic API

The interface provides **semantic methods** rather than generic key-value operations:

- **Artifact operations**: `save_artifact()`, `get_artifact()`, `list_artifacts()`, etc.
- **System metadata**: `save_execution_state()`, `load_execution_state()`, `save_run_metadata()`, `load_run_metadata()`

This separation:

1. Provides type safety at the API level
2. Hides implementation details (e.g., internal prefixes) from callers
3. Prevents accidental mixing of artifacts and system data

### All Artifacts Stored

**All artifacts are stored, regardless of the `output` flag.** The artifact store operates at the execution layer, storing every artifact that completes successfully. The `output: true` flag in runbooks controls **export filtering**, not storage.

This separation enables:

1. **Internal artifacts**: Intermediate results available to dependents but excluded from final exports
2. **Fan-in support**: Multiple downstream processors can depend on the same upstream artifact
3. **Debugging**: All execution results are available for inspection during development

## Storage vs Export Filtering

| Aspect       | Artifact Store           | Export Layer                  |
| ------------ | ------------------------ | ----------------------------- |
| **When**     | During execution         | After execution               |
| **What**     | All completed artifacts  | Only `output: true` artifacts |
| **Purpose**  | Enable downstream access | Control final results         |
| **Location** | `waivern-artifact-store` | `wct/exporters/`              |

```
Execution Flow:
                                                         ┌─────────────────┐
Artifact A ──▶ store.save_artifact(run_id, "a", msg)  ───│                 │
                                                         │  ArtifactStore  │
Artifact B ──▶ store.save_artifact(run_id, "b", msg)  ───│  (stores ALL)   │
  (output: true)                                         │                 │
                                                         │  run_id/        │
Artifact C ──▶ store.save_artifact(run_id, "c", msg)  ───│   artifacts/    │
  (uses A as input, fetches via store.get_artifact)      │   ├── a.json    │
                                                         │   ├── b.json    │
                                                         │   └── c.json    │
                                                         └────────┬────────┘
                                                                  │
                                                                  ▼
                                                         ┌─────────────────┐
                                                         │  Export Layer   │
                                                         │  (filters by    │
                                                         │   output: true) │
                                                         └────────┬────────┘
                                                                  │
                                                                  ▼
                                                           Final Results:
                                                             [Artifact B]
```

## Information Flow

```
1. DAGExecutor Starts Run
   └── Generates run_id (UUID)
   └── Gets singleton ArtifactStore from DI container
   └── Creates RunMetadata and ExecutionState
        ↓
2. Metadata Persisted
   └── await metadata.save(store)  # Uses save_run_metadata()
   └── await state.save(store)     # Uses save_execution_state()
        ↓
3. Connector/Processor Completes
   └── Produces Message with content and metadata
        ↓
4. DAGExecutor Saves Artifact
   └── await store.save_artifact(run_id, artifact_id, message)
        ↓
5. Downstream Processor Starts
   └── input_messages = [await store.get_artifact(run_id, ref) for ref in input_refs]
        ↓
6. Execution Completes
   └── await metadata.save(store)  # Final status
   └── Optionally: await store.clear_artifacts(run_id)  # Cleanup artifacts only
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ArtifactStoreFactory                         │
│  - Creates singleton store instances                            │
│  - Implements ServiceFactory protocol for DI                    │
│  - Supports environment variable fallback                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ArtifactStoreConfiguration                      │
│  - Discriminated union of backend configs                       │
│  - MemoryStoreConfig | FilesystemStoreConfig | RemoteStoreConfig│
│  - from_properties() with env var fallback                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ArtifactStore (ABC)                        │
│  - Abstract async interface for all backends                    │
│  - Stateless: run_id passed to each operation                   │
│  - Semantic methods for artifacts and system metadata           │
└─────────────────────────────────────────────────────────────────┘
                    ┌───────────┴───────────┐
                    ▼                       ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   AsyncInMemoryStore      │   │   LocalFilesystemStore    │
│   - Dict-based storage    │   │   - JSON files on disk    │
│   - For testing           │   │   - .waivern/runs/{run}/  │
│   - No persistence        │   │   - artifacts/ partition  │
│                           │   │   - _system/ partition    │
└───────────────────────────┘   └───────────────────────────┘
```

## Interface Contract

```python
class ArtifactStore(ABC):
    """Abstract base class for async artifact store implementations.

    Stateless interface where run_id is passed to each operation.
    This enables singleton stores compatible with standard DI patterns.

    Provides semantic methods for artifacts, system metadata, and batch jobs.
    Implementations handle internal storage structure (prefixes, directories).
    """

    # ========================================================================
    # Artifact Operations
    # ========================================================================

    @abstractmethod
    async def save_artifact(
        self, run_id: str, artifact_id: str, message: Message
    ) -> None:
        """Store an artifact by its ID (upsert semantics)."""
        ...

    @abstractmethod
    async def get_artifact(self, run_id: str, artifact_id: str) -> Message:
        """Retrieve an artifact by its ID.

        Raises:
            ArtifactNotFoundError: If artifact does not exist.
        """
        ...

    @abstractmethod
    async def artifact_exists(self, run_id: str, artifact_id: str) -> bool:
        """Check if an artifact exists."""
        ...

    @abstractmethod
    async def delete_artifact(self, run_id: str, artifact_id: str) -> None:
        """Delete an artifact by its ID (no-op if not found)."""
        ...

    @abstractmethod
    async def list_artifacts(self, run_id: str) -> list[str]:
        """List all artifact IDs for a run."""
        ...

    @abstractmethod
    async def clear_artifacts(self, run_id: str) -> None:
        """Remove all artifacts for a run (preserves system metadata)."""
        ...

    # ========================================================================
    # System Metadata Operations
    # ========================================================================

    @abstractmethod
    async def save_execution_state(
        self, run_id: str, state_data: dict[str, JsonValue]
    ) -> None:
        """Persist execution state for a run."""
        ...

    @abstractmethod
    async def load_execution_state(self, run_id: str) -> dict[str, JsonValue]:
        """Load execution state for a run.

        Raises:
            ArtifactNotFoundError: If state does not exist.
        """
        ...

    @abstractmethod
    async def save_run_metadata(
        self, run_id: str, metadata: dict[str, JsonValue]
    ) -> None:
        """Persist run metadata."""
        ...

    @abstractmethod
    async def load_run_metadata(self, run_id: str) -> dict[str, JsonValue]:
        """Load run metadata.

        Raises:
            ArtifactNotFoundError: If metadata does not exist.
        """
        ...

    # ========================================================================
    # Batch Job Operations
    # ========================================================================

    @abstractmethod
    async def save_batch_job(
        self, run_id: str, batch_id: str, data: dict[str, JsonValue]
    ) -> None:
        """Persist a batch job record."""
        ...

    @abstractmethod
    async def load_batch_job(
        self, run_id: str, batch_id: str
    ) -> dict[str, JsonValue]:
        """Load a batch job record.

        Raises:
            ArtifactNotFoundError: If batch job does not exist.
        """
        ...

    @abstractmethod
    async def list_batch_jobs(self, run_id: str) -> list[str]:
        """List all batch job IDs for a run."""
        ...

    # ========================================================================
    # Run Enumeration
    # ========================================================================

    @abstractmethod
    async def list_runs(self) -> list[str]:
        """List all run IDs in the store."""
        ...
```

## Backend Implementations

### AsyncInMemoryStore

In-memory store for testing without filesystem dependencies:

```python
store = AsyncInMemoryStore()

# Artifacts stored in nested dict: {run_id: {artifact_id: Message}}
await store.save_artifact("run-123", "findings", message)
msg = await store.get_artifact("run-123", "findings")

# System metadata stored separately
await store.save_execution_state("run-123", state_dict)
state = await store.load_execution_state("run-123")
```

- **Use case**: Unit tests, ephemeral runs
- **Persistence**: None (lost when process exits)
- **Thread safety**: Not needed (asyncio is single-threaded)

### LocalFilesystemStore

Filesystem-backed store for persistent local storage:

```python
store = LocalFilesystemStore(base_path=Path(".waivern"))

# Maps to: .waivern/runs/run-123/artifacts/findings.json
await store.save_artifact("run-123", "findings", message)

# Hierarchical artifact IDs supported:
# .waivern/runs/run-123/artifacts/namespace/analysis.json
await store.save_artifact("run-123", "namespace/analysis", message)

# System metadata stored in _system/ partition:
# .waivern/runs/run-123/_system/state.json
await store.save_execution_state("run-123", state_dict)
```

- **Use case**: Local development, audit trails, resume capability
- **Persistence**: JSON files on disk
- **Structure**: `.waivern/runs/{run_id}/artifacts/{artifact_id}.json`
- **Security**: Validates keys to prevent path traversal attacks

## Dependency Injection Integration

The artifact store integrates with the `ServiceContainer` via the factory pattern:

```python
# Registration (singleton - one store shared across runs)
container.register(
    ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(config), "singleton")
)

# Usage in DAGExecutor
store = container.get_service(ArtifactStore)
await store.save_artifact(run_id, "findings", message)
```

### Lifetime: Singleton

Stores are registered as **singletons** because:

1. **Stateless design**: Run isolation via `run_id` parameter, not separate instances
2. **Resource efficiency**: Connection pools, file handles created once
3. **DI compatibility**: `factory.create()` takes no parameters

## Configuration

### Config Classes

```python
# In-memory (default for testing)
MemoryStoreConfig(type="memory")

# Local filesystem
FilesystemStoreConfig(type="filesystem", base_path=Path(".waivern"))

# Remote HTTP (future)
RemoteStoreConfig(type="remote", endpoint_url="https://...", api_key="...")
```

### Environment Variables

| Variable                | Description                                    | Default    |
| ----------------------- | ---------------------------------------------- | ---------- |
| `WAIVERN_STORE_TYPE`    | Backend type: `memory`, `filesystem`, `remote` | `memory`   |
| `WAIVERN_STORE_PATH`    | Base path for filesystem backend               | `.waivern` |
| `WAIVERN_STORE_URL`     | Endpoint URL for remote backend                | —          |
| `WAIVERN_STORE_API_KEY` | API key for remote backend                     | —          |

### Configuration Priority

1. Explicit properties (highest)
2. Environment variables
3. Defaults (lowest)

```python
# Zero-config (reads from environment)
config = ArtifactStoreConfiguration.from_properties({})

# Explicit override
config = ArtifactStoreConfiguration.from_properties({
    "type": "filesystem",
    "base_path": "/data/waivern"
})
```

## Error Handling

| Scenario               | Behaviour                                   |
| ---------------------- | ------------------------------------------- |
| Artifact not found     | `ArtifactNotFoundError` raised              |
| State/metadata missing | `ArtifactNotFoundError` raised              |
| Invalid backend config | `ValidationError` at configuration          |
| Unsupported backend    | `NotImplementedError` from `create_store()` |
| Path traversal attempt | `ValueError` from key validation            |

When `ArtifactNotFoundError` is raised during execution, the DAGExecutor marks the dependent artifact as failed and skips its dependents.

## Directory Structure

```
waivern-artifact-store/
├── src/waivern_artifact_store/
│   ├── __init__.py           # Package exports
│   ├── base.py               # ArtifactStore ABC (async interface)
│   ├── in_memory.py          # AsyncInMemoryStore implementation
│   ├── filesystem.py         # LocalFilesystemStore implementation
│   ├── factory.py            # ArtifactStoreFactory for DI
│   ├── configuration.py      # Config classes with discriminated union
│   └── errors.py             # ArtifactNotFoundError, ArtifactStoreError
├── docs/
│   └── architecture.md       # This document
└── tests/
    └── waivern_artifact_store/
        ├── test_in_memory.py
        ├── test_filesystem.py
        ├── test_configuration.py
        ├── test_factory.py
        └── test_service_composition.py
```

## Storage Structure (Filesystem Backend)

```
.waivern/
└── runs/
    └── {run-id}/                    # UUID per execution
        ├── _system/                 # System metadata partition
        │   ├── run.json             # RunMetadata (status, timestamps, hash)
        │   └── state.json           # ExecutionState (completed, failed, skipped)
        ├── artifacts/               # Pipeline artifacts partition
        │   ├── source_data.json
        │   ├── findings.json
        │   └── namespace/           # Hierarchical artifact IDs supported
        │       └── analysis.json
        ├── llm_cache/               # LLM response cache
        │   ├── {cache_key}.json     # CacheEntry (pending → completed)
        │   └── ...
        └── batch_jobs/              # LLM batch job tracking
            └── {batch_id}.json      # BatchJob metadata
```

**Note**: The `artifacts/` prefix is an internal implementation detail. API users work with artifact IDs directly (e.g., `"findings"`, `"namespace/analysis"`), not prefixed keys.

## Future Extensions

| Current              | Future Possibilities            |
| -------------------- | ------------------------------- |
| AsyncInMemoryStore   | Testing, ephemeral runs         |
| LocalFilesystemStore | Local persistence, audit trails |
| —                    | RemoteHttpStore (SaaS backend)  |
| —                    | S3Store (cloud persistence)     |

Backend selection is controlled via the `type` configuration field.

## Related Documentation

- [Persistent Artifact Store Design](../../../.local/plans/persistent-artifact-store-design.md) - Design and implementation phases
- [Artifact-Centric Orchestration](../../../docs/architecture/artifact-centric-orchestration.md) - How the DAGExecutor uses the artifact store
