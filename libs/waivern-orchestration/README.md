# Waivern Orchestration

Orchestration layer for Waivern Compliance Framework.

This package provides the artifact-centric runbook orchestration system, including:

- **Models**: Pydantic models for runbooks, artifacts, and execution results
- **Errors**: Typed exceptions for orchestration failures
- **Parser**: YAML runbook parsing with environment variable substitution
- **DAG**: Dependency graph building and topological sorting
- **Planner**: Upfront validation, execution planning, and child runbook flattening
- **Executor**: Parallel artifact execution with asyncio
- **State Persistence**: Execution state tracking and run resumption
- **Child Runbook Composition**: Modular, reusable runbook design through plan-time flattening

## Features

### Parallel Execution

Artifacts execute in parallel using asyncio, respecting dependency ordering from the DAG.
Sync components (connectors, processors) are bridged to async via ThreadPoolExecutor.

### State Persistence & Resume

Execution state is persisted after each artifact completes, enabling:

- **Resume from failure** - Re-run failed runs, skipping completed artifacts
- **Artifact reuse** - Reference artifacts from previous runs in new runbooks
- **Run inspection** - Query run status and examine artifacts

```bash
# Resume a failed run
wct run analysis.yaml --resume <run-id>

# List recorded runs
wct runs
wct runs --status failed
```

### Artifact Reuse

Reuse artifacts from previous runs without re-executing:

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

## Installation

```bash
uv add waivern-orchestration
```

## Usage

```python
from waivern_orchestration import Runbook, ArtifactDefinition, SourceConfig

# Define a runbook programmatically
runbook = Runbook(
    name="Example Runbook",
    description="An example runbook",
    artifacts={
        "data": ArtifactDefinition(
            source=SourceConfig(type="filesystem", properties={"path": "/tmp"})
        ),
    },
)
```

## Documentation

- [Runbook Format](docs/runbook-format.md) - Artifact-centric runbook structure and syntax
- [Child Runbook Composition](docs/child-runbook-composition.md) - Guide to modular runbook design
- [Execution Persistence](../../docs/future-plans/execution-persistence.md) - State tracking and resume capability
