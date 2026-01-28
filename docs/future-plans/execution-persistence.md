# Execution Persistence

- **Status:** Partially Implemented
- **Last Updated:** 2026-01-28
- **Related:** [Artifact-Centric Orchestration](../architecture/artifact-centric-orchestration.md), [Persistent Artifact Store Design](../../.local/plans/persistent-artifact-store-design.md)

## Problem

Currently execution results and artifacts exist only in memory. When the process exits, everything is lost. This prevents:

- Artifact inspection after execution
- Audit trails
- SaaS deployment (users need to access their run history)

## Solution

Separate stores with run ID as correlation key:

| Store            | Purpose            | Data                                           | Status         |
| ---------------- | ------------------ | ---------------------------------------------- | -------------- |
| `ArtifactStore`  | Produced data      | `Message` objects (schema-validated artifacts) | ✅ Implemented |
| `ExecutionStore` | Execution metadata | `ExecutionResult` (status, timing, errors)     | ⏳ Future      |

## Current Implementation

The `ArtifactStore` interface is now fully implemented with async, stateless design:

```python
class ArtifactStore(ABC):
    """Stateless interface - run_id passed to each operation."""

    async def save(self, run_id: str, key: str, message: Message) -> None: ...
    async def get(self, run_id: str, key: str) -> Message: ...
    async def exists(self, run_id: str, key: str) -> bool: ...
    async def delete(self, run_id: str, key: str) -> None: ...
    async def list_keys(self, run_id: str, prefix: str = "") -> list[str]: ...
    async def clear(self, run_id: str) -> None: ...
```

**Available backends:**

- `AsyncInMemoryStore` - For testing
- `LocalFilesystemStore` - For local persistence

**Filesystem layout:**

```
.waivern/runs/{run_id}/
├── _system/                 # Reserved for system metadata
│   └── state.json           # (future) execution state
├── artifacts/
│   ├── source_data.json
│   └── findings.json
└── llm_cache/               # (future) LLM response cache
    └── {hash}.json
```

## Deployment Models

| Deployment | ArtifactStore        | ExecutionStore (future)    |
| ---------- | -------------------- | -------------------------- |
| Local/CLI  | LocalFilesystemStore | FileSystemExecutionStore   |
| SaaS       | RemoteHttpStore      | PostgreSQL (tenant-scoped) |

## Enables

- **`wct inspect`** - View artifacts without re-execution (future)
- **Exporters** - Read from stores, produce JSON/reports/API responses
- **SaaS** - Users access run history from centralised store
- **Audit** - All executions persisted with metadata

## Flow

```
Runbook → Planner → DAGExecutor → ArtifactStore
                                        ↓
                                    Exporter(s)
                                        ↓
                               JSON / Report / API
```

## Implementation Progress

| Step | Description                                           | Status    |
| ---- | ----------------------------------------------------- | --------- |
| 1    | Add `run_id` parameter to `ArtifactStore` interface   | ✅ Done   |
| 2    | Add `LocalFilesystemStore` implementation             | ✅ Done   |
| 3    | DAGExecutor generates run ID, passes to stores        | ✅ Done   |
| 4    | Add `ExecutionStore` interface                        | ⏳ Future |
| 5    | Implement `wct inspect` reading from persisted stores | ⏳ Future |
| 6    | Add exporter abstraction for output formatting        | ⏳ Future |

See [Persistent Artifact Store Design](../../.local/plans/persistent-artifact-store-design.md) for the complete implementation plan.
