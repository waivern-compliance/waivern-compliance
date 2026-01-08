# Artifact Persistence and Run-Based Reuse

- **Status:** Design Proposal
- **Created:** 2025-01-08
- **Related:** [Architecture](./architecture.md), [Execution Persistence](../../../docs/future-plans/execution-persistence.md)

## Problem

Currently, execution artifacts exist only in memory during runbook execution. When the process exits, everything is lost. This creates two pain points:

1. **Failed runs are expensive** — If an execution fails halfway, re-running requires re-executing all successful (potentially expensive) steps.

2. **Incremental development is slow** — When developing complex runbooks, iterating on later stages requires re-running the entire pipeline from the start.

## Goals

1. **Persistent storage** — All artifacts are saved to disk, surviving process exit.

2. **Run-based reuse** — Users can reference artifacts from previous runs by run ID.

3. **Self-contained runs** — Each run contains all its artifacts (copied or freshly executed).

4. **Security** — No arbitrary file path access. Only controlled run references.

## Non-Goals

- Automatic content-addressed caching
- External file path references
- Distributed/shared storage (future extension)

---

## Design

### Storage Architecture

Single `FileSystemArtifactStore` implementation replaces `InMemoryArtifactStore`:

```
.waivern/runs/
├── run-001/
│   ├── manifest.json
│   ├── db_schema.json
│   └── findings.json
├── run-002/
│   ├── manifest.json
│   ├── db_schema.json       ← Copied from run-001
│   ├── source_code.json     ← Freshly executed
│   └── findings.json        ← Freshly executed
└── ...
```

Each run is **self-contained** — all artifacts are physically present, either:
- Freshly executed in this run
- Copied from a previous run (via `from_run`)

### Runbook Syntax

```yaml
name: "Personal Data Analysis"

artifacts:
  # Reuse expensive artifact from previous run
  db_schema:
    from_run: "run-001"

  # Normal source artifact
  source_code:
    source:
      type: filesystem
      properties:
        path: ./src

  # Processor using both artifacts
  findings:
    inputs: [db_schema, source_code]
    process:
      type: personal_data
      properties:
        ruleset: "local/personal_data/1.0.0"
    output: true
```

### Execution Flow

```
$ wct run analysis.yaml

┌─────────────────────────────────────────────────────────────────┐
│                     Create new run: run-002                     │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    For each artifact in runbook                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
        Has from_run?                    Has source/process?
                │                               │
               YES                             YES
                │                               │
                ▼                               ▼
┌───────────────────────────┐    ┌────────────────────────────────┐
│ 1. Verify run exists      │    │ 1. Execute connector/processor │
│ 2. Verify artifact exists │    │ 2. Save to run-002/            │
│ 3. Validate schema        │    └────────────────────────────────┘
│ 4. Copy to run-002/       │
│ 5. Record provenance      │
└───────────────────────────┘
```

---

## from_run Reference

### Validation

When an artifact specifies `from_run`, the system:

1. **Verifies run exists** — `runs/{run_id}/` must exist
2. **Verifies artifact exists** — `runs/{run_id}/{artifact_id}.json` must exist
3. **Validates schema compatibility** — Schema must match downstream requirements
4. **Copies artifact** — Physical copy to current run (self-contained)
5. **Records provenance** — Tracks where the artifact came from

```python
def resolve_from_run(
    run_id: str,
    artifact_id: str,
    current_run_id: str,
    store: FileSystemArtifactStore
) -> Message:
    """Copy artifact from previous run with provenance tracking."""

    # Verify source run exists
    if not store.run_exists(run_id):
        raise RunNotFoundError(f"Run '{run_id}' not found")

    # Verify artifact exists in source run
    if not store.artifact_exists(run_id, artifact_id):
        raise ArtifactNotFoundError(
            f"Artifact '{artifact_id}' not found in run '{run_id}'"
        )

    # Load artifact
    message = store.get(run_id, artifact_id)

    # Add provenance
    provenance = ArtifactProvenance(
        source_type="from_run",
        source_run=run_id,
        source_artifact=artifact_id,
        copied_at=datetime.now(UTC),
    )
    message = message.with_provenance(provenance)

    # Copy to current run (self-contained)
    store.save(current_run_id, artifact_id, message)

    return message
```

### Security

| Approach | Security |
|----------|----------|
| `external: { file: "..." }` | User can reference ANY file — S3, system files, etc. |
| `from_run: "run-001"` | Our code controls run storage, verifies existence |

Only run IDs managed by WCT can be referenced. No arbitrary file system access.

---

## Provenance Model

```python
class ArtifactProvenance(BaseModel):
    """Tracks where an artifact came from."""

    source_type: Literal["executed", "from_run"]

    # For from_run
    source_run: str | None = None
    source_artifact: str | None = None
    copied_at: datetime | None = None

    # For executed
    executed_at: datetime | None = None
    duration_seconds: float | None = None
```

### Manifest

Each run has a `manifest.json` tracking all artifacts and their provenance:

```json
{
  "run_id": "run-002",
  "created_at": "2025-01-08T10:00:00Z",
  "runbook": "analysis.yaml",
  "artifacts": {
    "db_schema": {
      "provenance": {
        "source_type": "from_run",
        "source_run": "run-001",
        "copied_at": "2025-01-08T10:00:01Z"
      },
      "schema": "standard_input/1.0.0",
      "content_hash": "sha256:abc123..."
    },
    "source_code": {
      "provenance": {
        "source_type": "executed",
        "executed_at": "2025-01-08T10:00:02Z",
        "duration_seconds": 1.2
      },
      "schema": "standard_input/1.0.0",
      "content_hash": "sha256:def456..."
    },
    "findings": {
      "provenance": {
        "source_type": "executed",
        "executed_at": "2025-01-08T10:00:05Z",
        "duration_seconds": 2.8
      },
      "schema": "personal_data_finding/1.0.0",
      "content_hash": "sha256:ghi789..."
    }
  }
}
```

---

## CLI Integration

### Running with Reuse

```bash
# Fresh run (all artifacts executed)
$ wct run analysis.yaml
  ✓ db_schema (45.2s)
  ✓ source_code (1.1s)
  ✓ findings (2.8s)
  Run: run-001

# Later, user updates runbook to reuse db_schema
$ wct run analysis.yaml
  ✓ db_schema (from run-001, 0.1s)
  ✓ source_code (1.2s)
  ✓ findings (3.1s)
  Run: run-002
```

### Listing Runs

```bash
$ wct runs list
  run-001  2025-01-08 10:00  analysis.yaml  3 artifacts
  run-002  2025-01-08 14:30  analysis.yaml  3 artifacts

$ wct runs inspect run-001
  Run: run-001
  Created: 2025-01-08 10:00:00
  Runbook: analysis.yaml

  Artifacts:
    db_schema      standard_input/1.0.0     executed (45.2s)
    source_code    standard_input/1.0.0     executed (1.1s)
    findings       personal_data/1.0.0      executed (2.8s)
```

### Exporting Artifacts

```bash
# Export for external use (outside WCT)
$ wct runs export run-001 db_schema -o ./backup/db_schema.json
```

---

## User Workflows

### Workflow 1: Resume Failed Run

```bash
# Run fails at findings
$ wct run analysis.yaml
  ✓ db_schema (45.2s)
  ✓ source_code (1.1s)
  ✗ findings (error: LLM timeout)
  Run: run-001 (incomplete)

# User updates runbook to reuse successful artifacts
```

```yaml
artifacts:
  db_schema:
    from_run: "run-001"      # Reuse
  source_code:
    from_run: "run-001"      # Reuse
  findings:
    inputs: [db_schema, source_code]
    process: {type: personal_data}
```

```bash
# Re-run with reused artifacts
$ wct run analysis.yaml
  ✓ db_schema (from run-001, 0.1s)
  ✓ source_code (from run-001, 0.1s)
  ✓ findings (3.2s)
  Run: run-002
```

### Workflow 2: Incremental Development

```bash
# Initial run with expensive db extraction
$ wct run analysis.yaml
  ✓ db_schema (45.2s)        # Expensive
  ✓ findings (2.1s)
  Run: run-001
```

```yaml
# Iterate on findings config, keep db_schema
artifacts:
  db_schema:
    from_run: "run-001"      # Pinned

  findings:
    inputs: db_schema
    process:
      type: personal_data
      properties:
        ruleset: "local/personal_data/2.0.0"  # Iterating on this
```

```bash
# Fast iteration
$ wct run analysis.yaml
  ✓ db_schema (from run-001, 0.1s)
  ✓ findings (2.3s)
  Run: run-002

# Change ruleset again, re-run...
$ wct run analysis.yaml
  ✓ db_schema (from run-001, 0.1s)
  ✓ findings (2.5s)
  Run: run-003
```

---

## Configuration

### Storage Location

**Environment variable:**
```bash
WAIVERN_RUNS_DIRECTORY=.waivern/runs  # Default
```

**Global config (.waivern/config.yaml):**
```yaml
storage:
  runs_directory: .waivern/runs
```

**Priority:** Environment > Global config > Default

---

## Implementation Path

### Phase 1: FileSystemArtifactStore

1. Implement `FileSystemArtifactStore` with run-scoped storage
2. Add `manifest.json` generation
3. Update `DAGExecutor` to use filesystem store
4. Remove `InMemoryArtifactStore` from production code (keep for tests)

### Phase 2: from_run Support

1. Add `from_run` field to `ArtifactDefinition`
2. Implement `resolve_from_run()` with validation
3. Add `ArtifactProvenance` model
4. Update planner to validate `from_run` references

### Phase 3: CLI Tooling

1. Add `wct runs list` command
2. Add `wct runs inspect <run_id>` command
3. Add `wct runs export <run_id> <artifact_id>` command
4. Update `wct run` output to show provenance

### Phase 4: Polish

1. Run cleanup commands (`wct runs delete`, `wct runs prune`)
2. Run retention policies (TTL-based cleanup)
3. Improved error messages
4. Documentation

---

## Design Decisions

1. **No external file paths** — Security risk. Only run references allowed.

2. **Self-contained runs** — Each run has all artifacts physically present. No dangling references.

3. **Single store implementation** — `FileSystemArtifactStore` for production. `InMemoryArtifactStore` remains for unit tests only.

4. **Explicit reuse** — User explicitly specifies `from_run` in runbook. No automatic caching.

---

## Open Questions

1. **Run ID format** — Sequential (`run-001`) or timestamp-based (`run-20250108-100000`) or UUID?

2. **Large artifact handling** — Compress stored artifacts? Stream instead of loading into memory?

---

## Related Documents

- [Architecture](./architecture.md) — Artifact store architecture
- [Execution Persistence](../../../docs/future-plans/execution-persistence.md) — Original persistence proposal
- [Artifact-Centric Orchestration](../../../docs/architecture/artifact-centric-orchestration.md) — DAG execution model
