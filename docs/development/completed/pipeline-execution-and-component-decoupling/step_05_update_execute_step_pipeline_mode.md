# Step 5: Update _execute_step to Support Pipeline Mode

**Phase:** 2 - Implement Sequential Pipeline Execution
**Status:** DONE
**Prerequisites:** Steps 1-4 (pipeline infrastructure and validation in place)

## Context

This is part of implementing pipeline execution for WCF, enabling multi-step analysis workflows where data flows between steps.

**Previous steps built:** Pipeline fields, validation, artifact storage, and cycle detection.

**This step adds:** Support for two execution modes - connector-based (existing) and artifact-based (new pipeline mode).

**See:** [Pipeline Execution and Component Decoupling](../pipeline-execution-and-component-decoupling.md) for full context and roadmap.

## Purpose

Modify `_execute_step` to support both single-step mode (extract from connector) and pipeline mode (read from previous step's artifact), enabling data to flow through multi-step analysis workflows.

## Problem

Currently, `_execute_step` only supports single-step mode where a connector extracts data and an analyser processes it. Pipeline execution requires a second mode where steps read input from previous steps' saved artifacts instead of extracting from connectors.

**Current limitation:**
```yaml
execution:
  # This works (single-step mode)
  - id: "step1"
    connector: mysql_connector
    analyser: personal_data_analyser

  # This doesn't work yet (pipeline mode)
  - id: "step2"
    input_from: "step1"  # Need to read from step1's artifact
    analyser: data_subject_analyser
```

**Why both modes are needed:**
- **Single-step mode:** Extract data from external sources (databases, files, APIs)
- **Pipeline mode:** Transform/enrich data from previous steps without re-extraction

## Solution

Add conditional logic to `_execute_step` to detect execution mode based on `step.connector` vs `step.input_from`, retrieve input accordingly, then process with analyser. Both modes share the same analyser execution path and return the same tuple structure.

## Decisions Made

1. **Mode detection:** Check `step.connector is not None` vs `step.input_from is not None` (already mutually exclusive from Step 2)
2. **Artifact retrieval:** Use `artifacts[step.input_from]` to get previous step's Message
3. **Error handling:** Provide helpful error if artifact missing (user forgot `save_output: true`)
4. **Connector optional:** Make connector instantiation conditional (only for single-step mode)
5. **Shared execution:** Both modes use same analyser processing and return pattern
6. **Schema resolution:** Use existing method for now (Step 6 will add pipeline-specific resolution)

## Implementation

### File to Modify

`apps/wct/src/wct/executor.py`

### Changes Required

#### 1. Update `_execute_step` to support two modes

**Current structure:**
```
function _execute_step(step, runbook, artifacts) -> (AnalysisResult, Message):
    get analyser config
    get connector config  # ALWAYS required currently
    instantiate both
    resolve schemas
    extract from connector
    process with analyser
    return tuple
```

**New structure (pseudo-code):**
```
function _execute_step(step, runbook, artifacts) -> (AnalysisResult, Message):
    # Always need analyser
    analyser_config = get_analyser_config(step, runbook)
    analyser = instantiate_analyser(analyser_config)

    # Mode detection and input acquisition
    if step.connector is not None:
        # SINGLE-STEP MODE (existing)
        connector_config = get_connector_config(step, runbook)
        connector = instantiate_connector(connector_config)
        schemas = resolve_step_schemas(step, connector, analyser)
        input_message = connector.extract(schemas.input)

    else:
        # PIPELINE MODE (new)
        if step.input_from not in artifacts:
            raise ExecutorError(
                "Step '{step.name}' depends on '{step.input_from}' but artifact not found. "
                "Ensure previous step has 'save_output: true'."
            )

        input_message = artifacts[step.input_from]
        log("Pipeline mode: using artifact from '{step.input_from}'")

        # Schema resolution for pipeline mode
        # For now, use input_message.schema as-is
        # Step 6 will add proper pipeline schema resolution
        schemas = resolve_schemas_for_pipeline(step, input_message, analyser)

    # Common execution path (both modes)
    result_message = analyser.process(schemas.input, schemas.output, input_message)

    analysis_result = create_analysis_result(
        step=step,
        schemas=schemas,
        result_data=result_message.content,
        analyser_config=analyser_config
    )

    return (analysis_result, result_message)
```

**Key changes:**
- Make connector instantiation conditional (only for single-step mode)
- Add artifact retrieval logic for pipeline mode
- Validate artifact exists with helpful error message
- Use input_message.schema for pipeline mode (temporary - Step 6 improves this)
- Maintain tuple return pattern from Step 3

#### 2. Update helper methods

**Make `_get_step_configs` handle optional connector:**

Currently requires both analyser and connector. Need to support pipeline mode where connector is None.

**Option:** Split into separate methods or make connector_config optional in return type.

**Pseudo-code:**
```
function get_step_configs(step, runbook) -> (analyser_config, connector_config | None):
    analyser_config = find analyser in runbook.analysers

    if step.connector exists:
        connector_config = find connector in runbook.connectors
    else:
        connector_config = None

    return (analyser_config, connector_config)
```

#### 3. Update component instantiation

**Make `_instantiate_components` handle optional connector:**

Currently expects both. Need to handle case where connector_config is None.

**Consideration:** May need to refactor to separate methods or handle None gracefully.

## Testing

### Testing Strategy

**Critical principle:** Test through the **public API** (`execute_runbook`), not by calling private methods directly.

Create temporary runbook YAML files that exercise both execution modes and verify behavior through `execute_runbook()`.

### Test Scenarios

**File:** `apps/wct/tests/test_executor.py`

#### 1. Single-Step Mode Still Works (Regression Test)

**Setup:**
- Create runbook with single step using connector
- Step has connector + analyser, no `input_from`

**Expected behavior:**
- Execution succeeds
- Step extracts from connector as before
- Returns AnalysisResult with correct data

#### 2. Pipeline Mode Reads from Artifact

**Setup:**
- Create runbook with 2 steps:
  - Step 1: connector-based with `save_output: true`
  - Step 2: `input_from: "step1"` with different analyser

**Expected behavior:**
- Both steps execute successfully
- Step 2 reads from step 1's artifact (not from connector)
- Results contain data from both steps

#### 3. Pipeline Mode Errors on Missing Artifact

**Setup:**
- Create runbook with 2 steps:
  - Step 1: connector-based with `save_output: false` (or omitted)
  - Step 2: `input_from: "step1"`

**Expected behavior:**
- `execute_runbook()` raises `ExecutorError`
- Error message mentions "artifact not found"
- Error message suggests adding `save_output: true`
- Step 1 completes, Step 2 fails (fail at execution, not validation)

#### 4. Pipeline Mode Errors on Non-existent Step Reference

**Setup:**
- Create runbook with step that has `input_from: "nonexistent_step"`

**Expected behavior:**
- This should already be caught by Step 2 validation (cross-reference)
- Verify validation prevents this from reaching execution

### Implementation Notes

- Use `tempfile.NamedTemporaryFile` to create runbook YAML
- Use existing mock connector and analyser from test fixtures
- Test error messages are helpful and actionable
- Clean up temp files in `finally` blocks

### Validation Commands

```bash
# Run all WCT tests
uv run pytest apps/wct/tests/ -v

# Run specific executor tests
uv run pytest apps/wct/tests/test_executor.py -v

# Run dev checks
./scripts/dev-checks.sh
```

## Success Criteria

**Functional:**
- [x] Single-step mode continues to work unchanged (regression test passes)
- [x] Pipeline mode successfully retrieves input from artifacts dict
- [x] Pipeline mode executes analyser with artifact data
- [x] Helpful error when artifact missing (mentions `save_output: true`)
- [x] Both modes return proper tuple (AnalysisResult, Message)
- [x] Artifact retrieval logged for debugging

**Quality:**
- [x] All tests pass (including new pipeline mode tests)
- [x] Type checking passes (strict mode)
- [x] Linting passes
- [x] No regressions in existing single-step functionality

**Code Quality:**
- [x] Tests use public API (`execute_runbook`) only
- [x] Code follows existing Executor patterns
- [x] Error messages are actionable and user-friendly
- [x] Conditional logic is clear and maintainable

## Implementation Notes

**Current architecture (Step 3):**
- `_execute_step` returns `tuple[AnalysisResult, Message]`
- `execute_runbook` maintains `artifacts: dict[str, Message]`
- AnalysisResult has NO message field (clean separation)

**Design decisions:**
- Connector is None for pipeline mode (not instantiated)
- Schema resolution simplified for now (use input_message.schema as-is)
- Step 6 will add proper pipeline schema resolution method
- Error at execution time (not validation) because artifact missing is runtime condition

**Edge cases to consider:**
- Step references itself (`input_from: "self"`) - caught by Step 4 cycle detection
- Step references non-existent ID - caught by Step 2 cross-reference validation
- Artifact exists but has wrong schema - Step 6 will handle schema validation

**Future enhancements (not in this step):**
- Pipeline-specific schema resolution (Step 6)
- Schema compatibility validation between steps
- Better error messages showing schema mismatches

## Next Steps

- **Step 6:** Add pipeline schema resolution method to validate schema compatibility between steps
- **Phase 3:** Refactor SourceCodeConnector to SourceCodeAnalyser
- **Phase 4:** Integration tests and end-to-end validation

---

## Completion Notes

**Date Completed:** 2025-11-11

### Implementation Summary

Successfully implemented pipeline mode execution in `_execute_step` using TDD methodology (RED-GREEN-REFACTOR):

**Core Changes:**
1. Updated `_get_step_configs` to return `tuple[AnalyserConfig, ConnectorConfig | None]`
2. Updated `_validate_step_types` to handle optional connector types
3. Updated `_instantiate_components` to conditionally instantiate connectors
4. Updated `_run_step_analysis` to accept `input_message` parameter instead of connector
5. Added mode detection logic in `_execute_step` (connector-based vs pipeline-based)
6. Implemented artifact retrieval with helpful error messages

**Refactoring Improvements:**
- Extracted `_resolve_pipeline_schemas` method to match existing `_resolve_step_schemas` pattern
- Created symmetry between single-step and pipeline mode schema resolution
- Reduced `_execute_step` complexity from 54 to 43 lines
- Added inline documentation for future Strategy pattern opportunity

**Tests Added:**
1. `test_execute_runbook_pipeline_mode_reads_from_artifact` - Verifies pipeline mode reads from artifacts
2. `test_execute_runbook_pipeline_mode_errors_on_missing_artifact` - Verifies helpful error messages

**Key Design Decisions:**
- Connector is `None` for pipeline mode (not instantiated)
- Schema resolution uses dedicated helper methods for both modes
- Error messages guide users to add `save_output: true`
- Logging added for both execution modes

**Files Modified:**
- `apps/wct/src/wct/executor.py` - Core pipeline mode implementation
- `apps/wct/tests/test_executor.py` - New tests for pipeline mode

**Quality Metrics:**
- All 32 executor tests passing
- Total test suite: 897 passed, 7 skipped
- Type checking: 0 errors (strict mode)
- Linting: All checks passed
- Code coverage: Maintained

**Architecture Notes:**

The implementation uses optional type cascading (`Type | None`) through helper methods. While functional and type-safe, this approach was documented as a future refactoring opportunity. If additional input modes are needed (API, database, streaming), consider extracting to a Strategy pattern with an `InputAcquisitionStrategy` interface to:
- Eliminate optional type propagation
- Improve extensibility and Open/Closed principle compliance
- Separate input mode concerns more clearly

Inline comments added in `_execute_step` to guide future developers toward this pattern when appropriate.
