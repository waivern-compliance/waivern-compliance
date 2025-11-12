# Step 3: Add Artifact Storage to Executor

**Phase:** 2 - Implement Sequential Pipeline Execution
**Status:** ✅ Completed (2025-11-11)
**Prerequisites:** Steps 1-2 (pipeline fields and validation)

## Purpose

Modify the Executor's `execute_runbook` method to store intermediate Message artifacts when steps specify `save_output: true`, enabling data passing between pipeline steps.

## Decisions Made

1. **In-memory storage** - Use a dictionary to store artifacts (no disk persistence yet)
2. **Key by step ID** - Use the step's `id` field as the dictionary key
3. **Store Message objects** - Store the full Message object (not just content)
4. **Artifact passed to _execute_step** - Modify signature to accept artifacts dict
5. **Architecture: Option C (Tuple Return)** - `_execute_step` returns `tuple[AnalysisResult, Message]` for clean separation of concerns

### Architecture Decision: Option C - Clean Separation

After evaluating multiple approaches, implemented **Option C** for clean architecture:

- `_execute_step` returns `tuple[AnalysisResult, Message]` instead of just `AnalysisResult`
- `execute_runbook` unpacks tuple and manages artifacts separately
- **AnalysisResult remains unchanged** - No message field added (maintains clean export model)
- **Message artifacts stored separately** - Managed by Executor, not embedded in results

**Why Option C:**
- Maintains separation of concerns (export model vs internal data flow)
- Avoids circular dependency issues
- Clean architecture: AnalysisResult for JSON export, Message for pipeline flow
- Prevents pollution of user-facing export format with internal implementation details

## Implementation

### Files Modified

1. `apps/wct/src/wct/executor.py` - Artifact storage and tuple return pattern
2. `apps/wct/tests/test_executor.py` - New tests for artifact storage

**Note:** `apps/wct/src/wct/analysis.py` was **NOT** modified - AnalysisResult remains unchanged.

### Changes Implemented

#### 1. Add Message import

**File:** `apps/wct/src/wct/executor.py`

```python
from waivern_core.message import Message
```

#### 2. Update `_execute_step` signature to return tuple

**File:** `apps/wct/src/wct/executor.py`

```python
def _execute_step(
    self,
    step: ExecutionStep,
    runbook: Runbook,
    artifacts: dict[str, Message],  # NEW parameter
) -> tuple[AnalysisResult, Message]:  # NEW: Returns tuple
    """Execute a single step in the runbook.

    Args:
        step: Execution step to run
        runbook: Full runbook configuration
        artifacts: Dictionary of saved Message artifacts from previous steps

    Returns:
        Tuple of (AnalysisResult for user output, Message for pipeline artifacts)
    """
    logger.info("Executing analysis: %s", step.name)
    # ... rest of implementation
```

#### 3. Update `_run_step_analysis` to return tuple

**File:** `apps/wct/src/wct/executor.py`

```python
def _run_step_analysis(
    self,
    step: ExecutionStep,
    analyser: Analyser,
    connector: Connector,
    input_schema: Schema,
    output_schema: Schema,
    analyser_config: AnalyserConfig,
) -> tuple[AnalysisResult, Message]:  # NEW: Returns tuple
    """Execute the actual analysis step.

    Returns:
        Tuple of (AnalysisResult for user output, Message for pipeline artifacts)
    """
    # Extract data from connector
    connector_message = connector.extract(input_schema)

    # Run the analyser with the extracted data
    result_message = analyser.process(
        input_schema, output_schema, connector_message
    )

    analysis_result = AnalysisResult(
        analysis_name=step.name,
        analysis_description=step.description,
        input_schema=input_schema.name,
        output_schema=output_schema.name,
        data=result_message.content,
        metadata=analyser_config.metadata,
        contact=step.contact,
        success=True,
    )

    return analysis_result, result_message  # NEW: Return tuple
```

#### 4. Update `_handle_step_error` to return tuple

**File:** `apps/wct/src/wct/executor.py`

```python
def _handle_step_error(
    self, step: ExecutionStep, error: Exception
) -> tuple[AnalysisResult, Message]:  # NEW: Returns tuple
    """Handle execution errors and return appropriate error result.

    Returns:
        Tuple of (error AnalysisResult, error Message with empty content)
    """
    logger.error(f"Step execution failed for {step.name}: {error}")
    error_result = self._create_error_result(
        step.name,
        step.description,
        error_message=str(error),
        input_schema=step.input_schema,
        output_schema=step.output_schema,
        contact=step.contact,
    )

    # Create error Message with empty content
    error_message = Message(
        id=step.id,
        content={},
        schema=None,
    )

    return error_result, error_message  # NEW: Return tuple
```

#### 5. Update `execute_runbook` to manage artifacts

**File:** `apps/wct/src/wct/executor.py`

```python
def execute_runbook(self, runbook_path: Path) -> list[AnalysisResult]:
    """Load and execute a runbook file."""
    try:
        runbook = RunbookLoader.load(runbook_path)
    except Exception as e:
        raise ExecutorError(f"Failed to load runbook {runbook_path}: {e}") from e

    results: list[AnalysisResult] = []
    artifacts: dict[str, Message] = {}  # NEW: Artifact storage

    for step in runbook.execution:
        # NEW: Unpack tuple
        analysis_result, message = self._execute_step(step, runbook, artifacts)
        results.append(analysis_result)

        # NEW: Store message in artifacts if step has save_output enabled
        if step.save_output:
            artifacts[step.id] = message
            logger.debug(f"Saved artifact from step '{step.id}' for pipeline use")

    return results
```

## Testing

### Unit Tests Added

**File:** `apps/wct/tests/test_executor.py`

#### Test: `test_execute_runbook_stores_message_artifacts`

Verifies that `execute_runbook` properly manages the artifacts dictionary:

```python
def test_execute_runbook_stores_message_artifacts(self) -> None:
    """Test that execute_runbook stores Message artifacts for steps with save_output."""
    from unittest.mock import patch
    from waivern_core.message import Message
    from waivern_core.schemas.base import Schema

    executor = self._create_executor_with_mocks()

    # Create runbook with two steps - first has save_output=true
    runbook_content = """
name: Pipeline Test
description: Test artifact storage
connectors:
  - name: test_connector
    type: mock_connector
    properties: {}
analysers:
  - name: test_analyser
    type: mock_analyser
    properties: {}
execution:
  - id: "step1"
    name: "First step"
    description: "Step with save_output"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
    save_output: true
  - id: "step2"
    name: "Second step"
    description: "Step without save_output"
    connector: test_connector
    analyser: test_analyser
    input_schema: standard_input
    output_schema: personal_data_finding
"""

    # ... test implementation that verifies:
    # - First call has empty artifacts dict
    # - Second call has step1's message in artifacts
```

**Test validates:**
- Artifacts dict starts empty
- Messages are stored when `save_output: true`
- Messages are accessible to subsequent steps
- Artifacts dict is passed correctly to `_execute_step`

### Validation

```bash
# Run all WCT tests
uv run pytest apps/wct/tests/ -v

# Run specific test
uv run pytest apps/wct/tests/test_executor.py::TestExecutor::test_execute_runbook_stores_message_artifacts -v

# Type check
./scripts/type-check.sh

# Lint
./scripts/lint.sh

# All checks
./scripts/dev-checks.sh
```

**Results:**
- ✅ All 891 tests pass
- ✅ Type checking passes (strict mode)
- ✅ Linting passes
- ✅ Pre-commit hooks pass

## Success Criteria

- [x] ✅ `_execute_step` returns `tuple[AnalysisResult, Message]`
- [x] ✅ `execute_runbook` creates artifacts dictionary
- [x] ✅ `execute_runbook` saves artifacts when `save_output: true`
- [x] ✅ `_execute_step` accepts artifacts parameter
- [x] ✅ `_run_step_analysis` returns tuple with Message
- [x] ✅ `_handle_step_error` returns tuple with error Message
- [x] ✅ Unit tests pass (test_execute_runbook_stores_message_artifacts)
- [x] ✅ Type checking passes (strict mode)
- [x] ✅ Linting passes
- [x] ✅ Existing functionality still works (all 891 tests pass)
- [x] ✅ Clean architecture maintained (no changes to AnalysisResult model)

## Implementation Notes

- **Architecture:** Option C (Tuple Return) chosen for clean separation of concerns
- **AnalysisResult unchanged:** Remains a clean export model without internal Message references
- **Artifacts dict:** Scoped to single runbook execution, in-memory only (not persisted)
- **Error handling:** Error steps return empty Message objects to maintain tuple contract
- **Call sites:** Only one call site (`execute_runbook`) updated to unpack tuple
- **Testing approach:** Mocked `_execute_step` to verify artifact state at each step

## Next Steps

- **Step 4:** Execution order resolution (dependency graph, cycle detection)
- **Step 5:** Update `_execute_step` for pipeline mode logic (use `input_from`)
- **Step 6:** Add pipeline schema resolution method (`_resolve_pipeline_schemas`)
