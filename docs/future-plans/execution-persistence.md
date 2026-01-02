# Execution Persistence

- **Status:** Design Proposal
- **Last Updated:** 2025-12-01
- **Related:** [Artifact-Centric Orchestration](../architecture/artifact-centric-orchestration.md)

## Problem

Currently execution results and artifacts exist only in memory. When the process exits, everything is lost. This prevents:
- Artifact inspection after execution
- Audit trails
- SaaS deployment (users need to access their run history)

## Solution

Separate stores with run ID as correlation key:

| Store | Purpose | Data |
|-------|---------|------|
| `ExecutionStore` | Execution metadata | `ExecutionResult` (status, timing, errors) |
| `ArtifactStore` | Produced data | `Message` objects (schema-validated artifacts) |

## Design

```python
class ExecutionStore(Protocol):
    def save(self, run_id: str, result: ExecutionResult) -> None: ...
    def get(self, run_id: str) -> ExecutionResult: ...
    def list_runs(self) -> list[str]: ...

class ArtifactStore(Protocol):
    def save(self, run_id: str, artifact_id: str, message: Message) -> None: ...
    def get(self, run_id: str, artifact_id: str) -> Message: ...
    def list_artifacts(self, run_id: str) -> list[str]: ...
```

**Filesystem layout:**
```
.waivern/runs/{run_id}/
├── execution_result.json
└── artifacts/
    ├── source_data.json
    └── findings.json
```

## Deployment Models

| Deployment | ExecutionStore | ArtifactStore |
|------------|----------------|---------------|
| Local/CLI | Filesystem | Filesystem |
| SaaS | PostgreSQL (tenant-scoped) | S3 (tenant-prefixed) |

## Enables

- **`wct inspect`** - View artifacts without re-execution
- **Exporters** - Read from stores, produce JSON/reports/API responses
- **SaaS** - Users access run history from centralised store
- **Audit** - All executions persisted with metadata

## Flow

```
Runbook → Planner → DAGExecutor → ExecutionStore/ArtifactStore
                                            ↓
                                        Exporter(s)
                                            ↓
                                   JSON / Report / API
```

## Implementation Path

1. Add `run_id` parameter to `ArtifactStore` interface
2. Add `FileSystemArtifactStore` implementation
3. Add `ExecutionStore` interface with `FileSystemExecutionStore`
4. DAGExecutor generates run ID, passes to stores
5. Implement `wct inspect` reading from persisted stores
6. Add exporter abstraction for output formatting
