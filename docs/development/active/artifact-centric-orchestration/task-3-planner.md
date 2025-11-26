# Task 3: Implement Planner

- **Phase:** 1 - Foundation
- **Status:** TODO
- **Prerequisites:** Task 2 (parser and DAG)
- **Design:** [artifact-centric-orchestration-design.md](../artifact-centric-orchestration-design.md)

## Context

Tasks 1-2 established models, parsing, and DAG building. This task adds the Planner which orchestrates these components and performs upfront validation including schema compatibility checking.

## Purpose

Implement the Planner class that produces an immutable, validated ExecutionPlan. The Planner discovers components via entry points, validates all references and schema compatibility, and fails fast before execution begins.

## Problem

Schema validation currently happens at runtime in the executor, leading to late failures. The Planner moves all validation upfront:
- Component existence (connector/analyser types registered)
- Reference validity (all `from` references exist)
- Schema compatibility (output schemas match input schemas)

## Decisions Made

1. **Entry point discovery** - Planner discovers components directly via `importlib.metadata.entry_points()`, no external registry needed
2. **Upfront schema validation** - All schema compatibility checked at plan time
3. **Immutable ExecutionPlan** - Plan is frozen dataclass, cannot be modified after creation
4. **Optional schema overrides** - Explicit `input_schema`/`output_schema` can override inferred schemas

## Implementation

### Files to Create/Modify

```
libs/waivern-orchestration/src/waivern_orchestration/
└── planner.py     # NEW
```

### Changes Required

#### 1. Implement Planner class

**Constructor:**
```
Planner.__init__()
  - Discover connector factories from "waivern.connectors" entry points
  - Discover analyser factories from "waivern.analysers" entry points
  - Store in internal dicts for lookup
```

**Entry point loading (pseudo-code):**
```
function load_entry_points(group):
    factories = {}
    for entry_point in importlib.metadata.entry_points(group=group):
        factory_func = entry_point.load()
        factories[entry_point.name] = factory_func()
    return factories
```

**Main method:**
```
plan(runbook_path: Path) -> ExecutionPlan
  1. Parse runbook using parse_runbook()
  2. Build DAG using ExecutionDAG(runbook.artifacts)
  3. Validate DAG (cycles)
  4. Validate references (all `from` targets exist)
  5. Resolve and validate schemas
  6. Return frozen ExecutionPlan
```

**Alternative entry point:**
```
plan_from_dict(data: dict) -> ExecutionPlan
  - Same as plan() but uses parse_runbook_from_dict()
  - Useful for testing and programmatic use
```

#### 2. Implement reference validation

```
_validate_refs(runbook: Runbook) -> None
  - For each artifact with `from` field
  - Verify all referenced artifact IDs exist in runbook.artifacts
  - Raise MissingArtifactError if not found
```

**Pseudo-code:**
```
function validate_refs(runbook):
    artifact_ids = set(runbook.artifacts.keys())
    for artifact_id, definition in runbook.artifacts:
        if definition.from_artifacts:
            refs = normalise_to_set(definition.from_artifacts)
            missing = refs - artifact_ids
            if missing:
                raise MissingArtifactError(missing, artifact_id)
```

#### 3. Implement schema resolution

```
_resolve_schemas(runbook: Runbook) -> dict[str, tuple[Schema, Schema]]
  - For each artifact, determine input and output schemas
  - Use explicit overrides if specified
  - Otherwise infer from component declarations
  - Validate compatibility between connected artifacts
```

**Schema resolution logic (pseudo-code):**
```
function resolve_schemas(runbook):
    result = {}

    # Process in topological order (dependencies first)
    for artifact_id in topological_order(runbook.artifacts):
        definition = runbook.artifacts[artifact_id]

        if definition.source:
            # Source artifact - schema from connector
            connector_factory = lookup_connector(definition.source.type)
            input_schema = None  # No input for source
            output_schema = get_connector_output_schema(connector_factory)

        else:
            # Derived artifact - input from upstream
            upstream_ids = normalise_to_list(definition.from_artifacts)
            upstream_schemas = [result[uid][1] for uid in upstream_ids]

            # For fan-in, all upstream must be compatible
            input_schema = validate_compatible(upstream_schemas)

            if definition.transform:
                # Validate input compatibility
                analyser_factory = lookup_analyser(definition.transform.type)
                analyser_input = get_analyser_input_schema(analyser_factory)
                validate_compatible(input_schema, analyser_input)
                output_schema = get_analyser_output_schema(analyser_factory)
            else:
                # Pass-through (merge only)
                output_schema = input_schema

        # Apply explicit overrides if specified
        if definition.output_schema:
            output_schema = lookup_schema(definition.output_schema)

        result[artifact_id] = (input_schema, output_schema)

    return result
```

#### 4. Schema compatibility validation

```
_validate_compatible(output_schema: Schema, input_schema: Schema) -> None
  - Check if output is compatible with input
  - For now: exact match or input accepts output
  - Raise SchemaCompatibilityError if incompatible
```

**Compatibility rules:**
- Exact schema name match is compatible
- "standard_input" accepts most output schemas (flexible input)
- Future: structural compatibility checking

### Update __init__.py exports

Add:
```python
from .planner import Planner
from .models import ExecutionPlan  # If not already exported
```

## Testing

### Test Scenarios

#### 1. End-to-end planning with mock components
- Register mock connector and analyser via entry points (or mock the discovery)
- Create valid runbook
- Call plan() and verify ExecutionPlan returned
- Verify DAG, schemas, and runbook all present in plan

#### 2. Component not found - connector
- Create runbook with unknown connector type
- Verify ComponentNotFoundError raised
- Verify error includes component type name

#### 3. Component not found - analyser
- Create runbook with unknown analyser type
- Verify ComponentNotFoundError raised

#### 4. Missing artifact reference
- Create runbook where artifact references non-existent `from`
- Verify MissingArtifactError raised
- Verify error includes both artifact IDs

#### 5. Schema incompatibility
- Create runbook where upstream output doesn't match downstream input
- Verify SchemaCompatibilityError raised
- Verify error includes both schema names

#### 6. Explicit schema override
- Create runbook with `output_schema` override
- Verify override is used instead of inferred schema

#### 7. plan_from_dict
- Create dict matching runbook structure
- Call plan_from_dict()
- Verify ExecutionPlan returned

#### 8. Cycle detection propagation
- Create runbook with cycle
- Verify CycleDetectedError propagated from DAG

### Testing Strategy for Entry Points

Since entry points require installed packages, use one of:
1. **Mock `importlib.metadata.entry_points`** - Inject mock factories
2. **Create test fixtures** - Register test components in conftest.py
3. **Integration test with real components** - Use existing waivern connectors/analysers

Prefer option 1 for unit tests, option 3 for integration tests.

### Validation Commands

```bash
# Run package tests
uv run pytest libs/waivern-orchestration/tests/ -v

# Run planner tests specifically
uv run pytest libs/waivern-orchestration/tests/test_planner.py -v

# Run full dev-checks
./scripts/dev-checks.sh
```

## Implementation Notes

- Entry point group names: `waivern.connectors`, `waivern.analysers`
- ComponentFactory has `component_class` attribute for accessing static schema methods
- Schema compatibility is a policy decision - start strict, relax if needed
- Consider caching entry point discovery (expensive operation)
- ExecutionPlan should be a frozen dataclass for immutability
