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
├── artifacts/
│   ├── source_data.json      # Artifacts (key = artifact_id)
│   ├── findings.json
│   └── validated_findings.json
│
├── llm_cache/
│   ├── {cache_key}.json      # LLM response cache entries
│   └── ...
│
└── batch_jobs/
    └── {batch_id}.json       # LLM batch job tracking metadata
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

    # Artifact operations
    async def save_artifact(self, run_id: str, artifact_id: str, message: Message) -> None: ...
    async def get_artifact(self, run_id: str, artifact_id: str) -> Message: ...
    async def artifact_exists(self, run_id: str, artifact_id: str) -> bool: ...
    async def delete_artifact(self, run_id: str, artifact_id: str) -> None: ...
    async def list_artifacts(self, run_id: str) -> list[str]: ...
    async def clear_artifacts(self, run_id: str) -> None: ...

    # System metadata
    async def save_execution_state(self, run_id: str, state_data: dict) -> None: ...
    async def load_execution_state(self, run_id: str) -> dict: ...
    async def save_run_metadata(self, run_id: str, metadata: dict) -> None: ...
    async def load_run_metadata(self, run_id: str) -> dict: ...

    # Batch job tracking
    async def save_batch_job(self, run_id: str, batch_id: str, data: dict) -> None: ...
    async def load_batch_job(self, run_id: str, batch_id: str) -> dict: ...
    async def list_batch_jobs(self, run_id: str) -> list[str]: ...

    # Run enumeration
    async def list_runs(self) -> list[str]: ...
```

**Available backends:**

- `AsyncInMemoryStore` - For testing
- `LocalFilesystemStore` - For local persistence

## Features

### Resume from Failure or Batch Interruption

Resume a failed or interrupted run, skipping already-completed artifacts:

```bash
# List recorded runs
wct runs
wct runs --status failed
wct runs --status interrupted

# Resume a specific run
wct run analysis.yaml --resume <run-id>
```

**Validation on resume:**

- Runbook hash must match (prevents resuming with modified runbook)
- Run must not be in "running" status (prevents concurrent execution)

### LLM Batch Mode Integration

When LLM batch mode is enabled (`WAIVERN_LLM_BATCH_MODE=true`), the execution flow becomes:

1. `wct run` submits prompts to the provider's Batch API and marks the run `interrupted`
2. `wct poll <run-id>` checks batch status and populates the LLM cache when complete
3. `wct run --resume <run-id>` re-attempts pending artifacts, which now hit cache

```bash
# Poll batch job status
wct poll <run-id>

# Resume once batches complete
wct run analysis.yaml --resume <run-id>
```

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
| LLM batch job storage (`batch_jobs/`)      | ✅ Implemented |
| LLM batch mode (`PendingProcessingError`)  | ✅ Implemented |
| `wct poll` command                         | ✅ Implemented |
| `interrupted` run status                   | ✅ Implemented |
| `wct inspect` command                      | ⏳ Future      |
| Run cleanup/retention policies             | ⏳ Future      |
