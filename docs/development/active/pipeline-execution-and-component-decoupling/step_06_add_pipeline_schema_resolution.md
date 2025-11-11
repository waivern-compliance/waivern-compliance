# Step 6: Add Pipeline Schema Resolution Method

**Phase:** 2 - Implement Sequential Pipeline Execution
**Status:** Pending
**Prerequisites:** Steps 1-5 (pipeline infrastructure and execution logic)

## Purpose

Implement the `_resolve_pipeline_schemas` method in the Executor to handle schema resolution for pipeline steps that use `input_from` instead of connectors. This method validates that the analyser supports the input schema from the previous step and resolves the output schema.

## Decisions Made

1. **Input schema from Message** - Use the schema from the previous step's Message object
2. **Validate analyser compatibility** - Ensure analyser supports the input schema
3. **Reuse _find_compatible_schema** - Use existing method for output schema resolution
4. **Clear error messages** - Provide helpful errors when schemas are incompatible

## Implementation

### File to Modify

`apps/wct/src/wct/executor.py`

### Method to Add

Add new private method `_resolve_pipeline_schemas`:

```python
def _resolve_pipeline_schemas(
    self,
    step: ExecutionStep,
    input_message: Message,
    analyser: Analyser,
) -> tuple[Schema, Schema]:
    """Resolve schemas for pipeline step (analyser-only).

    For pipeline steps with input_from, the input schema comes from the
    previous step's Message. We validate the analyser supports this schema
    and resolve the output schema based on the step configuration.

    Args:
        step: Execution step configuration
        input_message: Message from previous step (from artifacts)
        analyser: Analyser instance to process the message

    Returns:
        Tuple of (input_schema, output_schema)

    Raises:
        ExecutorError: If analyser doesn't support input schema or output schema invalid
    """
    # Input schema comes from previous step's message
    input_schema = input_message.schema

    logger.debug(
        f"Pipeline step '{step.name}' receiving input schema: "
        f"{input_schema.name} v{input_schema.version}"
    )

    # Validate analyser supports this input schema
    analyser_inputs = analyser.get_supported_input_schemas()

    if not any(
        s.name == input_schema.name and s.version == input_schema.version
        for s in analyser_inputs
    ):
        supported_schemas = [f"{s.name} v{s.version}" for s in analyser_inputs]
        raise ExecutorError(
            f"Schema mismatch in pipeline step '{step.name}': "
            f"Analyser '{step.analyser}' does not support input schema "
            f"'{input_schema.name}' v{input_schema.version}. "
            f"Supported schemas: {', '.join(supported_schemas)}"
        )

    # Resolve output schema
    analyser_outputs = analyser.get_supported_output_schemas()

    output_schema = self._find_compatible_schema(
        schema_name=step.output_schema,
        requested_version=step.output_schema_version,
        producer_schemas=analyser_outputs,
        consumer_schemas=[],  # No consumer schemas in pipeline mode
    )

    logger.debug(
        f"Pipeline step '{step.name}' output schema resolved: "
        f"{output_schema.name} v{output_schema.version}"
    )

    return input_schema, output_schema
```

### Integration with _execute_step

This method is called from `_execute_step` in pipeline mode (implemented in Step 5):

```python
# From Step 5 implementation
if step.connector:
    # Single-step mode: extract from connector
    input_schema, output_schema = self._resolve_step_schemas(
        step, connector, analyser
    )
    input_message = connector.extract(input_schema)
else:
    # Pipeline mode: read from previous step
    if step.input_from not in artifacts:
        raise ExecutorError(
            f"Pipeline step '{step.name}' depends on '{step.input_from}' "
            f"but no artifact found. Available artifacts: {list(artifacts.keys())}"
        )
    input_message = artifacts[step.input_from]

    # Resolve schemas (no connector, just analyser)
    input_schema, output_schema = self._resolve_pipeline_schemas(
        step, input_message, analyser
    )  # <-- NEW METHOD CALLED HERE
```

## Testing

### Unit Tests to Add

**File:** `apps/wct/tests/unit/test_executor.py`

```python
def test_resolve_pipeline_schemas_accepts_compatible_input(isolated_registry):
    """_resolve_pipeline_schemas accepts analyser-compatible input schema."""
    from wct.executor import Executor
    from waivern_core.message import Message
    from waivern_core.schemas.base import Schema
    from unittest.mock import Mock

    executor = Executor.create_with_built_ins()

    # Mock step configuration
    step = Mock()
    step.name = "test_step"
    step.analyser = "test_analyser"
    step.output_schema = "personal_data_finding"
    step.output_schema_version = None

    # Mock input message with standard_input schema
    input_message = Message(
        id="test",
        content={"test": "data"},
        schema=Schema("standard_input", "1.0.0"),
    )

    # Mock analyser that supports standard_input
    analyser = Mock()
    analyser.get_supported_input_schemas.return_value = [
        Schema("standard_input", "1.0.0")
    ]
    analyser.get_supported_output_schemas.return_value = [
        Schema("personal_data_finding", "1.0.0")
    ]

    # Should resolve successfully
    input_schema, output_schema = executor._resolve_pipeline_schemas(
        step, input_message, analyser
    )

    assert input_schema.name == "standard_input"
    assert input_schema.version == "1.0.0"
    assert output_schema.name == "personal_data_finding"
    assert output_schema.version == "1.0.0"


def test_resolve_pipeline_schemas_rejects_incompatible_input(isolated_registry):
    """_resolve_pipeline_schemas raises error when analyser doesn't support input."""
    from wct.executor import Executor, ExecutorError
    from waivern_core.message import Message
    from waivern_core.schemas.base import Schema
    from unittest.mock import Mock

    executor = Executor.create_with_built_ins()

    step = Mock()
    step.name = "test_step"
    step.analyser = "test_analyser"

    # Input message with source_code schema
    input_message = Message(
        id="test",
        content={"test": "data"},
        schema=Schema("source_code", "1.0.0"),
    )

    # Analyser that only supports standard_input (incompatible!)
    analyser = Mock()
    analyser.get_supported_input_schemas.return_value = [
        Schema("standard_input", "1.0.0")
    ]

    # Should raise ExecutorError with helpful message
    with pytest.raises(ExecutorError) as exc_info:
        executor._resolve_pipeline_schemas(step, input_message, analyser)

    assert "Schema mismatch" in str(exc_info.value)
    assert "source_code" in str(exc_info.value)
    assert "does not support" in str(exc_info.value)


def test_resolve_pipeline_schemas_validates_output_schema(isolated_registry):
    """_resolve_pipeline_schemas validates output schema exists."""
    from wct.executor import Executor, ExecutorError
    from waivern_core.message import Message
    from waivern_core.schemas.base import Schema
    from unittest.mock import Mock

    executor = Executor.create_with_built_ins()

    step = Mock()
    step.name = "test_step"
    step.analyser = "test_analyser"
    step.output_schema = "nonexistent_schema"  # Invalid!
    step.output_schema_version = None

    input_message = Message(
        id="test",
        content={"test": "data"},
        schema=Schema("standard_input", "1.0.0"),
    )

    analyser = Mock()
    analyser.get_supported_input_schemas.return_value = [
        Schema("standard_input", "1.0.0")
    ]
    analyser.get_supported_output_schemas.return_value = [
        Schema("personal_data_finding", "1.0.0")  # Doesn't match step requirement
    ]

    # Should raise ExecutorError (via _find_compatible_schema)
    with pytest.raises(ExecutorError):
        executor._resolve_pipeline_schemas(step, input_message, analyser)
```

### Integration Tests

Integration tests for full pipeline execution will be added separately, covering:
- Multi-step pipeline with schema transformations
- Error handling for missing artifacts
- Schema validation across pipeline boundaries

### Validation

```bash
# Run unit tests
cd apps/wct
uv run pytest tests/unit/test_executor.py::test_resolve_pipeline_schemas -v

# Type check
./scripts/type-check.sh

# Lint
./scripts/lint.sh
```

## Success Criteria

- [ ] `_resolve_pipeline_schemas` method implemented
- [ ] Input schema extracted from Message object
- [ ] Analyser compatibility validated
- [ ] Output schema resolved using existing method
- [ ] Clear error messages for schema mismatches
- [ ] Unit tests pass (3 new tests)
- [ ] Type checking passes (strict mode)
- [ ] Linting passes
- [ ] Method integrates with `_execute_step` from Step 5

## Notes

- This method completes the schema resolution infrastructure for pipeline mode
- It reuses `_find_compatible_schema` for consistency with single-step mode
- Error messages include step name and analyser name for debugging
- The method is called only for pipeline steps (when `step.input_from` is set)
- Input schema validation is strict (exact name and version match required)

## Next Steps

After Step 6, Phase 2 (Sequential Pipeline Execution) is complete:
- Steps 3-6 implement artifact storage, dependency resolution, execution logic, and schema resolution
- Next phase (Phase 3) will refactor SourceCodeConnector → SourceCodeAnalyser
- Integration tests for full pipeline execution can be added
- Example pipeline runbooks can be created to demonstrate the feature
