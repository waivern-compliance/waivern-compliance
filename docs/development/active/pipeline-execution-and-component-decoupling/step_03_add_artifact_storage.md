# Step 3: Add Artifact Storage to Executor

**Phase:** 2 - Implement Sequential Pipeline Execution
**Status:** Pending
**Prerequisites:** Steps 1-2 (pipeline fields and validation)

## Purpose

Modify the Executor's `execute_runbook` method to store intermediate Message artifacts when steps specify `save_output: true`, enabling data passing between pipeline steps.

## Decisions Made

1. **In-memory storage** - Use a dictionary to store artifacts (no disk persistence yet)
2. **Key by step ID** - Use the step's `id` field as the dictionary key
3. **Store Message objects** - Store the full Message object (not just content)
4. **Artifact passed to _execute_step** - Modify signature to accept artifacts dict

## Implementation

### Files to Modify

1. `apps/wct/src/wct/executor.py`
2. `apps/wct/src/wct/analysis.py` (add `message` field to AnalysisResult)

### Changes Required

#### 1. Update `AnalysisResult` class

**File:** `apps/wct/src/wct/analysis.py`

Add `message` field to store the full Message object:

```python
from waivern_core.message import Message

class AnalysisResult(BaseModel):
    """Results from an analysis execution."""

    analysis_name: str
    analysis_description: str
    input_schema: str
    output_schema: str
    data: dict[str, Any]
    metadata: AnalysisMetadata | None = None
    contact: str | None = None
    success: bool = True
    error_message: str | None = None

    # NEW: Store full message for artifact passing
    message: Message | None = Field(
        default=None,
        description="Full message object for pipeline artifact passing",
    )
```

#### 2. Modify `execute_runbook` method

**File:** `apps/wct/src/wct/executor.py`

```python
def execute_runbook(self, runbook_path: Path) -> list[AnalysisResult]:
    """Load and execute a runbook file with pipeline support."""
    try:
        runbook = RunbookLoader.load(runbook_path)
    except Exception as e:
        raise ExecutorError(f"Failed to load runbook {runbook_path}: {e}") from e

    # NEW: Artifact storage for passing data between steps
    artifacts: dict[str, Message] = {}

    results: list[AnalysisResult] = []
    for step in runbook.execution:
        # Pass artifacts to step execution
        result = self._execute_step(step, runbook, artifacts)
        results.append(result)

        # NEW: Save output if requested
        if step.save_output and step.id and result.message:
            logger.debug(f"Saving output artifact for step '{step.id}'")
            artifacts[step.id] = result.message

    return results
```

#### 3. Update `_execute_step` signature

**File:** `apps/wct/src/wct/executor.py`

```python
def _execute_step(
    self,
    step: ExecutionStep,
    runbook: Runbook,
    artifacts: dict[str, Message],  # NEW parameter
) -> AnalysisResult:
    """Execute a single step in either single-step or pipeline mode."""
    logger.info("Executing analysis: %s", step.name)
    # ... (rest of implementation in next steps)
```

#### 4. Update `_run_step_analysis` to include message

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
) -> AnalysisResult:
    """Execute the actual analysis step."""
    # Extract data from connector
    connector_message = connector.extract(input_schema)

    # Run the analyser with the extracted data
    result_message = analyser.process(
        input_schema, output_schema, connector_message
    )

    return AnalysisResult(
        analysis_name=step.name,
        analysis_description=step.description,
        input_schema=input_schema.name,
        output_schema=output_schema.name,
        data=result_message.content,
        metadata=analyser_config.metadata,
        contact=step.contact,
        success=True,
        message=result_message,  # NEW: Store for artifacts
    )
```

## Testing

### Unit Tests to Add

**File:** `apps/wct/tests/unit/test_executor.py`

```python
def test_executor_stores_artifacts_when_save_output_true(isolated_registry):
    """Executor stores artifacts when save_output is true."""
    # This test will be fleshed out in later steps when pipeline execution is complete
    # For now, verify artifact dict is created
    from wct.executor import Executor

    executor = Executor.create_with_built_ins()

    # Verify execute_runbook accepts artifacts (integration test needed)
    # This will be validated in Step 5 when pipeline execution is complete


def test_analysis_result_stores_message():
    """AnalysisResult can store Message object."""
    from wct.analysis import AnalysisResult
    from waivern_core.message import Message
    from waivern_core.schemas.base import Schema

    message = Message(
        id="test",
        content={"test": "data"},
        schema=Schema("standard_input", "1.0.0"),
    )

    result = AnalysisResult(
        analysis_name="Test",
        analysis_description="Test analysis",
        input_schema="standard_input",
        output_schema="personal_data_finding",
        data={"test": "data"},
        success=True,
        message=message,
    )

    assert result.message is not None
    assert result.message.id == "test"
    assert result.message.content == {"test": "data"}
```

### Integration Testing

Will be tested in Step 5 when pipeline execution is fully implemented.

### Validation

```bash
# Run unit tests
cd apps/wct
uv run pytest tests/unit/test_executor.py -v
uv run pytest tests/unit/test_analysis.py -v

# Type check
./scripts/type-check.sh

# Lint
./scripts/lint.sh
```

## Success Criteria

- [ ] `AnalysisResult` has `message` field
- [ ] `execute_runbook` creates artifacts dictionary
- [ ] `execute_runbook` saves artifacts when `save_output: true`
- [ ] `_execute_step` accepts artifacts parameter
- [ ] `_run_step_analysis` stores message in result
- [ ] Unit tests pass
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Existing functionality still works (single-step runbooks)

## Notes

- The artifacts dict is scoped to a single runbook execution
- Artifacts are stored in memory only (not persisted)
- The `message` field in AnalysisResult is optional for backward compatibility
- Artifact retrieval will be implemented in Step 5

## Next Step

Step 4: Implement execution order resolution (cycle detection)
