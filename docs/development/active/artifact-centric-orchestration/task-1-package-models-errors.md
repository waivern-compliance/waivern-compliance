# Task 1: Create waivern-orchestration Package with Models and Errors

- **Phase:** 1 - Foundation
- **Status:** TODO
- **Prerequisites:** None
- **Design:** [artifact-centric-orchestration-design.md](../artifact-centric-orchestration-design.md)

## Context

This is the first task in implementing the artifact-centric orchestration system. It establishes the new `waivern-orchestration` package with core data models that all subsequent tasks depend on.

## Purpose

Create the foundational package structure and Pydantic models that define the artifact-centric runbook format. These models replace the current three-section runbook structure (connectors, analysers, execution) with a unified artifact-based approach.

## Problem

The current runbook format separates concerns across three sections with cross-references, making it verbose and hiding the natural data flow. The new artifact-centric format treats data (artifacts) as first-class citizens, with transformations as edges between them.

## Decisions Made

1. **New package in libs/** - `waivern-orchestration` is a library package, not part of WCT
2. **Pydantic for models** - Consistent with existing codebase patterns
3. **Field alias for `from`** - Use `from_artifacts` with `alias="from"` since `from` is a Python keyword
4. **Phase 2 models included** - `ExecuteConfig` and `execute` field added now to avoid schema changes later
5. **Mutual exclusivity validation** - `source` XOR `from` enforced at model level

## Implementation

### Package Structure

```
libs/waivern-orchestration/
├── pyproject.toml
├── scripts/
│   ├── lint.sh
│   ├── format.sh
│   └── type-check.sh
├── src/waivern_orchestration/
│   ├── __init__.py
│   ├── py.typed
│   ├── models.py
│   └── errors.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    └── test_errors.py
```

### Changes Required

#### 1. Create pyproject.toml

Follow existing package patterns (e.g., waivern-core). Key dependencies:
- `waivern-core` - For Schema, Message types
- `pyyaml` - For YAML parsing (used in later tasks)
- `pydantic` - For model definitions

Dev dependencies: `basedpyright`, `ruff`, `pytest`

#### 2. Create scripts

Copy pattern from waivern-core with package name updated.

#### 3. Implement models.py

**Configuration models:**
```
SourceConfig
  - type: str (connector type name)
  - properties: dict (connector config)

TransformConfig
  - type: str (analyser type name)
  - properties: dict (analyser config)

RunbookConfig
  - timeout: optional int (total execution timeout)
  - cost_limit: optional float (LLM budget)
  - max_concurrency: int = 10
  - max_child_depth: int = 3

ExecuteConfig (Phase 2 model, included now)
  - mode: Literal["child"]
  - timeout: optional int (child override)
  - cost_limit: optional float (child override)
```

**Core models:**
```
ArtifactDefinition
  - Metadata: name, description, contact (all optional)
  - Source: source (SourceConfig) OR from_artifacts (str | list[str])
  - Transform: transform (TransformConfig), merge strategy
  - Schema override: input_schema, output_schema (optional)
  - Behaviour: output (bool), optional (bool)
  - Phase 2: execute (ExecuteConfig)
  - Validator: source XOR from (mutually exclusive)

Runbook
  - name: str
  - description: str
  - contact: optional str
  - config: RunbookConfig (with default)
  - artifacts: dict[str, ArtifactDefinition]
```

**Execution models:**
```
ArtifactResult
  - artifact_id: str
  - success: bool
  - message: optional Message
  - error: optional str
  - duration_seconds: float

ExecutionResult
  - artifacts: dict[str, ArtifactResult]
  - skipped: set[str]
  - total_duration_seconds: float
```

**Validation logic:**
- `validate_source_xor_from`: Ensure exactly one of `source` or `from_artifacts` is set
- Handle edge case: source artifact with inline transform is valid

#### 4. Implement errors.py

```
OrchestrationError (base exception)
  - Base for all orchestration errors

RunbookParseError(OrchestrationError)
  - YAML parsing failures
  - Include file path and line number where possible

CycleDetectedError(OrchestrationError)
  - Circular dependency in artifact graph
  - Include cycle path for debugging

MissingArtifactError(OrchestrationError)
  - Reference to non-existent artifact in `from`
  - Include artifact ID and referencing artifact

SchemaCompatibilityError(OrchestrationError)
  - Output schema incompatible with input schema
  - Include both schema names

ComponentNotFoundError(OrchestrationError)
  - Connector or analyser type not found
  - Include component type and name
```

#### 5. Update root pyproject.toml

Add to `[tool.uv.sources]`:
```toml
waivern-orchestration = { workspace = true }
```

### Exports from __init__.py

```python
# Models
from .models import (
    SourceConfig,
    TransformConfig,
    RunbookConfig,
    ExecuteConfig,
    ArtifactDefinition,
    Runbook,
    ArtifactResult,
    ExecutionResult,
)

# Errors
from .errors import (
    OrchestrationError,
    RunbookParseError,
    CycleDetectedError,
    MissingArtifactError,
    SchemaCompatibilityError,
    ComponentNotFoundError,
)
```

## Testing

### Test Scenarios for Models

#### 1. Valid source artifact
- Create ArtifactDefinition with only `source` field
- Verify validation passes
- Verify `from_artifacts` is None

#### 2. Valid derived artifact
- Create ArtifactDefinition with `from` and `transform`
- Verify validation passes
- Verify `source` is None

#### 3. Valid fan-in artifact
- Create ArtifactDefinition with `from` as list of IDs
- Verify list is preserved
- Verify merge strategy defaults to "concatenate"

#### 4. Invalid: both source and from
- Attempt to create with both fields set
- Verify ValidationError raised
- Verify error message is helpful

#### 5. Invalid: neither source nor from
- Attempt to create with neither field
- Verify ValidationError raised

#### 6. Runbook round-trip
- Create Runbook with multiple artifacts
- Serialise to dict, deserialise back
- Verify equality

#### 7. Config defaults
- Create RunbookConfig with no arguments
- Verify defaults: max_concurrency=10, max_child_depth=3

### Test Scenarios for Errors

#### 1. Error inheritance
- Verify all errors inherit from OrchestrationError
- Verify OrchestrationError inherits from Exception

#### 2. Error context
- Create each error type with context
- Verify str(error) includes relevant context

### Validation Commands

```bash
# Sync dependencies
uv sync

# Run package tests
uv run pytest libs/waivern-orchestration/tests/ -v

# Run package checks
cd libs/waivern-orchestration && ./scripts/lint.sh
cd libs/waivern-orchestration && ./scripts/type-check.sh

# Run full dev-checks
./scripts/dev-checks.sh
```

## Implementation Notes

- Follow existing package patterns from waivern-core
- Use `Field(alias="from")` for the `from_artifacts` field
- Use `model_validator` decorator for cross-field validation
- Ensure py.typed marker is present for type checking support
