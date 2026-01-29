# Artifact Store Architecture

This document explains the internal architecture of the Artifact Store package.

## Overview

The Artifact Store is a **storage abstraction** that holds artifacts (Messages) produced during runbook execution. It enables downstream components to retrieve outputs from upstream components via a simple key-value interface with run-scoped isolation.

```
┌─────────────────────┐     ┌──────────────────────┐     ┌────────────────────┐
│ DAGExecutor         │────▶│ ArtifactStore        │◀────│ Downstream         │
│ (produces artifact) │     │ (save/get)           │     │ Processor          │
└─────────────────────┘     └──────────────────────┘     └────────────────────┘
   store.save(run_id,         key-value storage          store.get(run_id,
             key, msg)        with run isolation                   input_ref)
```

## Design Philosophy

### Stateless Stores with Run-Scoped Operations

The store interface is **stateless** — `run_id` is passed to each operation rather than at construction. This enables:

- **Singleton stores**: One instance shared across all runs (DI-friendly)
- **Resource sharing**: HTTP clients, connection pools held by store instance
- **Standard DI protocol**: `factory.create()` takes no parameters
- **Run isolation**: Each run's artifacts are completely isolated

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
Artifact A ──▶ store.save(run_id, "a", msg) ────────│                 │
                                                    │  ArtifactStore  │
Artifact B ──▶ store.save(run_id, "b", msg) ────────│  (stores ALL)   │
  (output: true)                                    │                 │
                                                    │  run_id/        │
Artifact C ──▶ store.save(run_id, "c", msg) ────────│   ├── a.json    │
  (uses A as input, fetches via store.get)          │   ├── b.json    │
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
        ↓
2. Connector/Processor Completes
   └── Produces Message with content and metadata
        ↓
3. DAGExecutor Saves
   └── await store.save(run_id, artifact_id, message)
        ↓
4. Downstream Processor Starts
   └── input_messages = [await store.get(run_id, ref) for ref in input_refs]
        ↓
5. Execution Completes
   └── await store.clear(run_id) (cleanup)
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
│  - Defines save/get/exists/delete/list_keys/clear               │
└─────────────────────────────────────────────────────────────────┘
                    ┌───────────┴───────────┐
                    ▼                       ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   AsyncInMemoryStore      │   │   LocalFilesystemStore    │
│   - Dict-based storage    │   │   - JSON files on disk    │
│   - For testing           │   │   - .waivern/runs/{run}/  │
│   - No persistence        │   │   - Supports hierarchical │
│                           │   │     keys (e.g., llm/hash) │
└───────────────────────────┘   └───────────────────────────┘
```

## Interface Contract

```python
class ArtifactStore(ABC):
    """Abstract base class for async artifact store implementations.

    Stateless interface where run_id is passed to each operation.
    This enables singleton stores compatible with standard DI patterns.
    """

    @abstractmethod
    async def save(self, run_id: str, key: str, message: Message) -> None:
        """Store artifact by key (upsert semantics)."""
        ...

    @abstractmethod
    async def get(self, run_id: str, key: str) -> Message:
        """Retrieve artifact by key.

        Raises:
            ArtifactNotFoundError: If artifact does not exist
        """
        ...

    @abstractmethod
    async def exists(self, run_id: str, key: str) -> bool:
        """Check if artifact exists in storage."""
        ...

    @abstractmethod
    async def delete(self, run_id: str, key: str) -> None:
        """Delete artifact by key (no-op if not found)."""
        ...

    @abstractmethod
    async def list_keys(self, run_id: str, prefix: str = "") -> list[str]:
        """List all keys for a run, optionally filtered by prefix."""
        ...

    @abstractmethod
    async def clear(self, run_id: str) -> None:
        """Remove all artifacts for a run."""
        ...
```

## Backend Implementations

### AsyncInMemoryStore

In-memory store for testing without filesystem dependencies:

```python
store = AsyncInMemoryStore()

# Artifacts stored in nested dict: {run_id: {key: Message}}
await store.save("run-123", "findings", message)
msg = await store.get("run-123", "findings")
```

- **Use case**: Unit tests, ephemeral runs
- **Persistence**: None (lost when process exits)
- **Thread safety**: Not needed (asyncio is single-threaded)

### LocalFilesystemStore

Filesystem-backed store for persistent local storage:

```python
store = LocalFilesystemStore(base_path=Path(".waivern"))

# Maps to: .waivern/runs/run-123/findings.json
await store.save("run-123", "findings", message)

# Hierarchical keys supported: .waivern/runs/run-123/llm_cache/abc123.json
await store.save("run-123", "llm_cache/abc123", cached_response)
```

- **Use case**: Local development, audit trails
- **Persistence**: JSON files on disk
- **Structure**: `.waivern/runs/{run_id}/{key}.json`
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
await store.save(run_id, "findings", message)
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
        ├── _system/                 # Reserved for system metadata
        │   └── state.json           # (future) execution state
        ├── artifacts/               # Pipeline artifacts
        │   ├── source_data.json
        │   └── findings.json
        └── llm_cache/               # (future) LLM response cache
            └── {hash}.json
```

**Note**: Keys starting with `_system` are excluded from `list_keys()` to separate system metadata from user artifacts.

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
