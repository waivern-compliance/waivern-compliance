# Task: Refactor Executor to Unified Connector Flow

- **Phase:** Unified Connector Architecture - Phase 2
- **Status:** TODO
- **Prerequisites:** ArtifactConnector implementation (Task 1)
- **Related Issue:** #226

## Context

Refactors Executor to eliminate dual-mode execution logic. Every step now follows the unified flow: instantiate connector → instantiate analyser → execute. This removes conditional branching and optional types. Prerequisites provide ArtifactConnector for artifact retrieval.

## Purpose

Simplify Executor by using single execution path for all steps, reducing complexity and improving maintainability.

## Problem

The Executor has two execution modes (lines 330-371):

```python
if connector is not None:
    # Mode 1: Connector-based
    input_schema, output_schema = self._resolve_step_schemas(...)
    input_message = connector.extract(input_schema)
else:
    # Mode 2: Pipeline-based
    input_message = artifacts[step.input_from]
    input_schema, output_schema = self._resolve_pipeline_schemas(...)
```

This creates:
- Dual schema resolution methods
- Optional connector types throughout helper methods
- Conditional logic in critical execution path
- Increased cognitive complexity

## Proposed Solution

Remove conditional branching by ensuring every step has a connector (either external or ArtifactConnector). Merge dual schema resolution into single method.

## Decisions Made

1. **Mandatory connectors** - Every step must have connector (enforced by runbook schema)
2. **Schema resolution** - Single unified method replaces separate methods
3. **Helper method updates** - Remove `Connector | None` optional types
4. **Backward compatibility** - Maintain during transition (temporary dual support)
5. **Migration path** - Update runbook schema, then remove old code paths

## Expected Outcome & Usage Example

**Simplified execution logic:**
```python
# AFTER refactoring (single path)
connector, analyser = self._instantiate_components(...)
input_schema, output_schema = self._resolve_schemas(connector, analyser)
input_message = connector.extract(input_schema)
result = self._run_step_analysis(...)
```

**No more branching between connector/pipeline modes.**

## Implementation

### Changes Required

#### 1. Update Runbook Schema Validation

**Location:** `apps/wct/src/wct/models/runbook.py` (or schema validation location)

**Changes:**
- Make `connector` field required in ExecutionStep
- Remove `input_from` field (replaced by ArtifactConnector config)
- Update validation to ensure connector always present

**Schema change (pseudo-code):**
```python
class ExecutionStep(BaseModel):
    id: str
    name: str
    connector: ConnectorConfig  # NOW REQUIRED (was Optional)
    analyser: str
    save_output: bool = False
    # input_from: removed
```

#### 2. Remove Dual-Mode Branching

**Location:** `apps/wct/src/wct/executor.py` - `_execute_step` method (lines 330-371)

**Changes:**
- Remove `if connector is not None` / `else` branching
- Always call `connector.extract()`
- Use single schema resolution method

**Algorithm (pseudo-code):**
```python
def _execute_step(...):
    # Get configs (no longer returns Optional connector)
    analyser_config, connector_config = self._get_step_configs(step, runbook)

    # Validate types (connector guaranteed present)
    analyser_type, connector_type = self._validate_step_types(...)

    # Instantiate (no Optional handling needed)
    analyser, connector = self._instantiate_components(...)

    # Unified schema resolution
    input_schema, output_schema = self._resolve_schemas(connector, analyser)

    # Single execution path
    input_message = connector.extract(input_schema)

    # Execute analysis
    return self._run_step_analysis(...)
```

#### 3. Simplify Helper Method Signatures

**Location:** Same file - helper methods

**Changes to `_get_step_configs`:**
```python
# OLD:
def _get_step_configs(...) -> tuple[AnalyserConfig, ConnectorConfig | None]:

# NEW:
def _get_step_configs(...) -> tuple[AnalyserConfig, ConnectorConfig]:
```

**Changes to `_validate_step_types`:**
```python
# OLD:
def _validate_step_types(..., connector_config: ConnectorConfig | None):

# NEW:
def _validate_step_types(..., connector_config: ConnectorConfig):
```

**Changes to `_instantiate_components`:**
```python
# OLD:
def _instantiate_components(...) -> tuple[Analyser, Connector | None]:

# NEW:
def _instantiate_components(...) -> tuple[Analyser, Connector]:
```

#### 4. Merge Schema Resolution Methods

**Location:** Same file

**Changes:**
- Remove `_resolve_step_schemas()` method
- Remove `_resolve_pipeline_schemas()` method
- Create single `_resolve_schemas(connector, analyser)` method

**Algorithm (pseudo-code):**
```python
def _resolve_schemas(connector: Connector, analyser: Analyser) -> tuple[Schema, Schema]:
    """Resolve input and output schemas for step execution."""

    # Get connector's output schemas
    connector_outputs = connector.get_supported_output_schemas()

    # Get analyser's input schemas
    analyser_inputs = analyser.get_supported_input_schemas()

    # Find compatible schema (existing logic)
    input_schema = self._find_compatible_schema(connector_outputs, analyser_inputs)

    # Get output schema from analyser
    output_schema = self._select_output_schema(analyser)

    return input_schema, output_schema
```

**Key insight:** ArtifactConnector behaves like any other connector, so no special handling needed.

#### 5. Update ArtifactConnector Instantiation

**Location:** Executor connector factory registration

**Changes:**
- Register ArtifactConnectorFactory in Executor's component registry
- Pass ArtifactStore to factory during registration
- Ensure factory available for "artifact" connector type

**Pseudo-code:**
```python
def __init__(...):
    # Register standard connectors
    self._register_connectors()

    # Register artifact connector with store injection
    artifact_factory = ArtifactConnectorFactory(self.artifact_store)
    self.connector_factories["artifact"] = artifact_factory
```

#### 6. Remove Old Artifact Handling Code

**Location:** Execute runbook method

**Changes:**
- Remove artifact dict references (already using ArtifactStore)
- Remove `input_from` field handling
- Keep `save_output` handling (still needed)

## Testing

### Testing Strategy

Update existing tests to new format. Verify simplified logic works correctly.

### Test Scenarios

#### 1. Simple Connector-Based Step

**Setup:**
- Create runbook with MySQL connector → analyser
- Execute runbook

**Expected behaviour:**
- Step executes successfully
- Single code path used (no branching)
- Results identical to before

#### 2. Pipeline Step with ArtifactConnector

**Setup:**
- Create runbook with two steps
- First step saves output
- Second step uses ArtifactConnector

**Expected behaviour:**
- First step saves to artifact store
- Second step retrieves via ArtifactConnector
- Pipeline execution works correctly

#### 3. Multi-Step Pipeline

**Setup:**
- Create runbook with 3+ steps in chain
- Each step uses previous output

**Expected behaviour:**
- All steps execute in order
- Artifact passing works throughout chain
- No branching logic executed

#### 4. Schema Resolution

**Setup:**
- Various connector/analyser combinations
- Including ArtifactConnector

**Expected behaviour:**
- Single schema resolution method handles all cases
- Compatible schemas found correctly
- Error messages helpful when incompatible

#### 5. Error Handling

**Setup:**
- Missing artifact (ArtifactConnector for non-existent step)
- Schema incompatibility
- Connector extraction failure

**Expected behaviour:**
- Appropriate ConnectorError raised
- Error messages provide context
- Execution fails gracefully

### Validation Commands

```bash
# Run all executor tests
uv run pytest apps/wct/tests/test_executor.py -v

# Run pipeline tests
uv run pytest apps/wct/tests/ -k "pipeline" -v

# Run all WCT tests
uv run pytest apps/wct/tests/ -v

# Run quality checks
./scripts/dev-checks.sh
```

## Implementation Notes

**Refactoring approach:**
1. Update helper method signatures (remove Optional)
2. Merge schema resolution methods
3. Remove branching logic from _execute_step
4. Update runbook schema validation
5. Test thoroughly after each change

**Key benefits:**
- Reduced complexity (~50 LOC reduction)
- Single execution path (easier to reason about)
- No optional type handling
- Extensible to new connector types without Executor changes

**Migration considerations:**
- Breaking change to runbook format
- Update sample runbooks in same PR
- Update documentation
- Consider deprecation period if needed
