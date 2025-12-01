# Waivern Orchestration

Orchestration layer for Waivern Compliance Framework.

This package provides the artifact-centric runbook orchestration system, including:

- **Models**: Pydantic models for runbooks, artifacts, and execution results
- **Errors**: Typed exceptions for orchestration failures
- **Parser**: YAML runbook parsing with environment variable substitution
- **DAG**: Dependency graph building and topological sorting
- **Planner**: Upfront validation and execution planning
- **Executor**: Parallel artifact execution with asyncio

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
