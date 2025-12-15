# Waivern Orchestration

Orchestration layer for Waivern Compliance Framework.

This package provides the artifact-centric runbook orchestration system, including:

- **Models**: Pydantic models for runbooks, artifacts, and execution results
- **Errors**: Typed exceptions for orchestration failures
- **Parser**: YAML runbook parsing with environment variable substitution
- **DAG**: Dependency graph building and topological sorting
- **Planner**: Upfront validation, execution planning, and child runbook flattening
- **Executor**: Parallel artifact execution with asyncio
- **Child Runbook Composition**: Modular, reusable runbook design through plan-time flattening

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
