# Execution Persistence

- **Status:** Implemented
- **Last Updated:** 2026-01-30
- **Related:** [Artifact-Centric Orchestration](../architecture/artifact-centric-orchestration.md)

## Overview

Execution persistence enables artifact storage, state tracking, and run resumption. All execution data is persisted to the `ArtifactStore`, allowing runs to be inspected, resumed, and reused.

## Storage Structure

```
.waivern/runs/{run_id}/
├── _system/
│   ├── run.json              # Run metadata (runbook, timestamps, status)
│   └── state.json            # Execution state (completed, not_started, failed)
│
├── source_data.json          # Artifacts (key = artifact_id)
├── findings.json
└── validated_findings.json
```

### Run Metadata (`_system/run.json`)

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "runbook_path": "./runbooks/gdpr-analysis.yaml",
  "runbook_hash": "sha256:abc123...",
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:35:00Z",
  "status": "completed"
}
```

### Execution State (`_system/state.json`)

```json
{
  "completed": ["source_data", "findings"],
  "not_started": [],
  "failed": [],
  "skipped": [],
  "last_checkpoint": "2024-01-15T10:32:00Z"
}
```

## ArtifactStore Interface

```python
class ArtifactStore(ABC):
    """Stateless interface - run_id passed to each operation."""

    async def save(self, run_id: str, key: str, message: Message) -> None: ...
    async def get(self, run_id: str, key: str) -> Message: ...
    async def exists(self, run_id: str, key: str) -> bool: ...
    async def delete(self, run_id: str, key: str) -> None: ...
    async def list_keys(self, run_id: str, prefix: str = "") -> list[str]: ...
    async def list_runs(self) -> list[str]: ...
    async def clear(self, run_id: str) -> None: ...
    async def save_json(self, run_id: str, key: str, data: dict) -> None: ...
    async def get_json(self, run_id: str, key: str) -> dict: ...
```

**Available backends:**

- `AsyncInMemoryStore` - For testing
- `LocalFilesystemStore` - For local persistence

## Features

### Resume from Failure

Resume a failed or interrupted run, skipping already-completed artifacts:

```bash
# List recorded runs
wct runs
wct runs --status failed

# Resume a specific run
wct run analysis.yaml --resume <run-id>
```

**Validation on resume:**

- Runbook hash must match (prevents resuming with modified runbook)
- Run must not be in "running" status (prevents concurrent execution)

### Artifact Reuse

Reuse artifacts from previous runs in new runbooks:

```yaml
artifacts:
  db_schema:
    reuse:
      from_run: "550e8400-e29b-41d4-a716-446655440000"
      artifact: "db_schema"

  findings:
    inputs: db_schema
    process:
      type: personal_data
    output: true
```

## Deployment Models

| Deployment | ArtifactStore            |
| ---------- | ------------------------ |
| Local/CLI  | LocalFilesystemStore     |
| SaaS       | RemoteHttpStore (future) |

## Implementation Status

| Feature                                    | Status         |
| ------------------------------------------ | -------------- |
| `ArtifactStore` interface with run scoping | ✅ Implemented |
| `LocalFilesystemStore` implementation      | ✅ Implemented |
| `ExecutionState` model and persistence     | ✅ Implemented |
| `RunMetadata` model and persistence        | ✅ Implemented |
| Resume capability (`--resume` flag)        | ✅ Implemented |
| `wct runs` command                         | ✅ Implemented |
| Artifact reuse (`reuse` config)            | ✅ Implemented |
| `wct inspect` command                      | ⏳ Future      |
| Run cleanup/retention policies             | ⏳ Future      |
