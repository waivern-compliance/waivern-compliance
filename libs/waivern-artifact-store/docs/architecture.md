# Artifact Store Architecture

This document explains the internal architecture of the Artifact Store package.

## Overview

The Artifact Store is a **storage abstraction** that holds artifacts (Messages) produced during runbook execution. It enables downstream components to retrieve outputs from upstream components via a simple key-value interface.

```
┌─────────────────────┐     ┌──────────────────────┐     ┌────────────────────┐
│ DAGExecutor         │────▶│ ArtifactStore        │◀────│ Downstream         │
│ (produces artifact) │     │ (save/get)           │     │ Processor          │
└─────────────────────┘     └──────────────────────┘     └────────────────────┘
   store.save(id, msg)         key-value storage          store.get(input_ref)
```

## Design Philosophy

**All artifacts are stored, regardless of the `output` flag.** The artifact store operates at the execution layer, storing every artifact that completes successfully. The `output: true` flag in runbooks controls **export filtering**, not storage.

This separation enables:

1. **Internal artifacts**: Intermediate results available to dependents but excluded from final exports
2. **Fan-in support**: Multiple downstream processors can depend on the same upstream artifact
3. **Debugging**: All execution results are available for inspection during development

## Storage vs Export Filtering

| Aspect | Artifact Store | Export Layer |
|--------|----------------|--------------|
| **When** | During execution | After execution |
| **What** | All completed artifacts | Only `output: true` artifacts |
| **Purpose** | Enable downstream access | Control final results |
| **Location** | `waivern-artifact-store` | `wct/exporters/` |

```
Execution Flow:
                                                    ┌─────────────────┐
Artifact A ──▶ store.save("a", msg) ────────────────│                 │
                                                    │  ArtifactStore  │
Artifact B ──▶ store.save("b", msg) ────────────────│  (stores ALL)   │
  (output: true)                                    │                 │
                                                    │  {"a": msg_a,   │
Artifact C ──▶ store.save("c", msg) ────────────────│   "b": msg_b,   │
  (uses A as input, fetches via store.get("a"))     │   "c": msg_c}   │
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
1. Connector/Processor Completes
   └── Produces Message with content and metadata
        ↓
2. DAGExecutor Saves
   └── store.save(artifact_id, message)
        ↓
3. Downstream Processor Starts
   └── input_messages = [store.get(ref) for ref in input_refs]
        ↓
4. Execution Completes
   └── store.clear() (cleanup)
```

### Thread Safety

The in-memory implementation uses `threading.Lock` for all operations:

```python
def save(self, step_id: str, message: Message) -> None:
    with self._lock:
        self._storage[step_id] = message

def get(self, step_id: str) -> Message:
    with self._lock:
        if step_id not in self._storage:
            raise ArtifactNotFoundError(...)
        return self._storage[step_id]
```

This enables safe concurrent access from the DAGExecutor's parallel artifact production.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ArtifactStoreFactory                         │
│  - Creates store instances with validated configuration         │
│  - Implements ServiceFactory protocol for DI                    │
│  - Supports environment variable fallback                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ArtifactStore (ABC)                        │
│  - Abstract interface for all backends                          │
│  - Defines save/get/exists/clear/list_artifacts                 │
│  - Enables future backend implementations                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  InMemoryArtifactStore                          │
│  - Default implementation using dict                            │
│  - Thread-safe via threading.Lock                               │
│  - Transient lifetime (fresh per execution)                     │
└─────────────────────────────────────────────────────────────────┘
```

## Interface Contract

```python
class ArtifactStore(ABC):
    @abstractmethod
    def save(self, step_id: str, message: Message) -> None:
        """Store artifact from completed step."""
        ...

    @abstractmethod
    def get(self, step_id: str) -> Message:
        """Retrieve artifact for downstream step.

        Raises:
            ArtifactNotFoundError: If artifact does not exist
        """
        ...

    @abstractmethod
    def exists(self, step_id: str) -> bool:
        """Check if artifact exists in storage."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all artifacts (called after execution)."""
        ...

    @abstractmethod
    def list_artifacts(self) -> list[str]:
        """Return list of all stored artifact IDs."""
        ...
```

## Dependency Injection Integration

The artifact store integrates with the `ServiceContainer` via the factory pattern:

```python
# In DAGExecutor (waivern-orchestration)
store = self._registry.container.get_service(ArtifactStore)

# Registration in WCT CLI
container.register(
    ArtifactStore,
    ArtifactStoreFactory(config),
    lifetime="transient"  # Fresh store per execution
)
```

### Lifetime Considerations

| Lifetime | Behaviour | Use Case |
|----------|-----------|----------|
| `transient` | New instance per request | Default: fresh store per runbook execution |
| `singleton` | Single shared instance | Testing, multi-runbook pipelines |

The CLI uses `transient` lifetime to ensure each runbook execution gets a clean store, preventing cross-run contamination.

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Artifact not found | `ArtifactNotFoundError` raised |
| Invalid backend config | `ValidationError` at factory creation |
| Unsupported backend | `None` returned from `factory.create()` |

When `ArtifactNotFoundError` is raised during execution, the DAGExecutor marks the dependent artifact as failed and skips its dependents.

## Configuration

```python
ArtifactStoreConfiguration(
    backend="memory"  # Currently only "memory" supported
)
```

**Environment variables:**
- `ARTIFACT_STORE_BACKEND`: Backend type (default: `"memory"`)

## Directory Structure

```
waivern-artifact-store/
├── src/waivern_artifact_store/
│   ├── __init__.py           # Package exports
│   ├── base.py               # ArtifactStore abstract base class
│   ├── in_memory.py          # InMemoryArtifactStore implementation
│   ├── factory.py            # ArtifactStoreFactory for DI
│   ├── configuration.py      # ArtifactStoreConfiguration
│   └── errors.py             # ArtifactNotFoundError
├── docs/
│   └── architecture.md       # This document
└── tests/                    # Test suite
```

## Future Extensions

The abstract interface enables future backend implementations:

| Current | Future Possibilities |
|---------|---------------------|
| In-memory (dict) | Redis (distributed execution) |
|                  | S3/GCS (large artifact persistence) |
|                  | SQLite (local persistence across runs) |

Backend selection would be controlled via the `backend` configuration field.

## Related Documentation

- [Artifact-Centric Orchestration](../../../docs/architecture/artifact-centric-orchestration.md) - How the DAGExecutor uses the artifact store
- [Execution Persistence](../../../docs/future-plans/execution-persistence.md) - Future plans for persistent storage
