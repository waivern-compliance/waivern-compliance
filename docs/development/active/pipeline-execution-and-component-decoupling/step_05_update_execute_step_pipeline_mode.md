# Step 5: Update _execute_step to Support Pipeline Mode

**Phase:** 2 - Implement Sequential Pipeline Execution
**Status:** Pending
**Prerequisites:** Steps 1-4 (pipeline infrastructure in place)

## Purpose

Modify the `_execute_step` method to support both single-step mode (connector → analyser) and pipeline mode (previous step → analyser), retrieving input from artifacts when `input_from` is specified.

## Decisions Made

1. **Conditional input source** - Check `step.connector` vs `step.input_from` to determine mode
2. **Artifact retrieval** - Get input Message from artifacts dict using `input_from` ID
3. **Different schema resolution** - Use existing method for single-step, new method for pipeline
4. **Single-step support** - Existing single-step logic (connector XOR input_from) works as-is

## Implementation

### File to Modify

`apps/wct/src/wct/executor.py`

### Changes Required

Modify the `_execute_step` method:

```python
def _execute_step(
    self,
    step: ExecutionStep,
    runbook: Runbook,
    artifacts: dict[str, Message],
) -> AnalysisResult:
    """Execute a single step in either single-step or pipeline mode.

    Single-step mode: connector extracts data, analyser processes
    Pipeline mode: read from previous step's artifact, analyser processes

    Args:
        step: Execution step configuration
        runbook: Full runbook configuration
        artifacts: Dictionary of saved step outputs

    Returns:
        AnalysisResult with execution results

    Raises:
        ExecutorError: If step execution fails
    """
    logger.info("Executing step: %s", step.name)
    if step.description:
        logger.info("Step description: %s", step.description)

    try:
        # Get configurations
        analyser_config = self._get_analyser_config(step, runbook)
        analyser_type = self._validate_analyser_type(step, analyser_config)

        # Instantiate analyser (always needed)
        analyser = self._instantiate_analyser(analyser_type, analyser_config)

        # Determine execution mode and get input
        if step.connector:
            # SINGLE-STEP MODE: Extract from connector
            logger.debug("Single-step mode: extracting from connector '%s'", step.connector)

            connector_config = self._get_connector_config(step, runbook)
            connector_type = self._validate_connector_type(step, connector_config)
            connector = self._instantiate_connector(connector_type, connector_config)

            # Resolve schemas (connector → analyser)
            input_schema, output_schema = self._resolve_step_schemas(
                step, connector, analyser
            )

            # Extract data
            input_message = connector.extract(input_schema)

        else:
            # PIPELINE MODE: Read from previous step
            logger.debug("Pipeline mode: reading from step '%s'", step.input_from)

            # Retrieve artifact from previous step
            if step.input_from not in artifacts:
                raise ExecutorError(
                    f"Step '{step.name}' depends on step '{step.input_from}' "
                    f"but no saved artifact found. Ensure the previous step has 'save_output: true'."
                )

            input_message = artifacts[step.input_from]
            logger.debug(
                f"Retrieved artifact from '{step.input_from}': "
                f"schema={input_message.schema.name} v{input_message.schema.version}"
            )

            # Resolve schemas (previous step → analyser)
            input_schema, output_schema = self._resolve_pipeline_schemas(
                step, input_message, analyser
            )

        # Execute analyser (same for both modes)
        result_message = analyser.process(input_schema, output_schema, input_message)

        return AnalysisResult(
            analysis_name=step.name,
            analysis_description=step.description,
            input_schema=input_schema.name,
            output_schema=output_schema.name,
            data=result_message.content,
            metadata=analyser_config.metadata,
            contact=step.contact,
            success=True,
            message=result_message,  # Store for artifacts
        )

    except (ConnectorError, AnalyserError, ExecutorError, Exception) as e:
        return self._handle_step_error(step, e)
```

Add helper methods for getting configs:

```python
def _get_analyser_config(self, step: ExecutionStep, runbook: Runbook) -> AnalyserConfig:
    """Get analyser configuration for the step."""
    try:
        return next(p for p in runbook.analysers if p.name == step.analyser)
    except StopIteration:
        raise ExecutorError(
            f"Analyser '{step.analyser}' referenced in step '{step.name}' not found in runbook"
        )


def _get_connector_config(self, step: ExecutionStep, runbook: Runbook) -> ConnectorConfig:
    """Get connector configuration for the step."""
    if not step.connector:
        raise ExecutorError(f"Step '{step.name}' has no connector specified")

    try:
        return next(c for c in runbook.connectors if c.name == step.connector)
    except StopIteration:
        raise ExecutorError(
            f"Connector '{step.connector}' referenced in step '{step.name}' not found in runbook"
        )
```

Update `_get_step_configs` to use new helpers:

```python
def _get_step_configs(
    self, step: ExecutionStep, runbook: Runbook
) -> tuple[AnalyserConfig, ConnectorConfig | None]:
    """Get analyser and connector configurations for the step.

    Returns:
        Tuple of (analyser_config, connector_config or None)
    """
    analyser_config = self._get_analyser_config(step, runbook)
    connector_config = (
        self._get_connector_config(step, runbook) if step.connector else None
    )
    return analyser_config, connector_config
```

## Testing

### Unit Tests to Add

**File:** `apps/wct/tests/unit/test_executor.py`

```python
def test_execute_step_single_mode_uses_connector(isolated_registry):
    """Single-step mode extracts from connector."""
    # This will be an integration test - create minimal runbook and verify
    # connector is called for extraction
    pass  # Implementation depends on test fixtures


def test_execute_step_pipeline_mode_uses_artifact(isolated_registry):
    """Pipeline mode reads from artifacts dict."""
    from wct.executor import Executor, ExecutorError
    from wct.runbook import ExecutionStep, Runbook
    from waivern_core.message import Message
    from waivern_core.schemas.base import Schema

    executor = Executor.create_with_built_ins()

    # Create a step that expects artifact
    step = ExecutionStep(
        name="Pipeline step",
        description="",
        input_from="previous_step",
        analyser="personal_data_analyser",
        input_schema="standard_input",
        output_schema="personal_data_finding",
    )

    # Empty artifacts - should error
    with pytest.raises(ExecutorError) as exc_info:
        # This will error because artifact is missing
        # (Full integration test needs complete runbook)
        pass

    # Proper testing requires integration test with full runbook
    # See step_17 for integration tests


def test_execute_step_errors_on_missing_artifact(isolated_registry):
    """Pipeline mode errors if artifact not found."""
    # Verify ExecutorError is raised with helpful message
    # when input_from references non-existent artifact
    pass  # Integration test needed
```

### Integration Testing

Will be fully tested in Step 17 (integration tests).

For now, manual test with a simple pipeline runbook:

```yaml
name: "Pipeline Test"
description: "Test pipeline execution"

connectors:
  - name: "reader"
    type: "filesystem_connector"
    properties:
      path: "./test_data"
      max_files: 5

analysers:
  - name: "analyser"
    type: "personal_data_analyser"
    properties:
      pattern_matching:
        ruleset: "personal_data"

execution:
  - id: "step1"
    name: "Read files"
    connector: "reader"
    analyser: "analyser"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
    save_output: true

  - id: "step2"
    name: "Process from previous"
    input_from: "step1"
    analyser: "analyser"
    input_schema: "personal_data_finding"
    output_schema: "personal_data_finding"
```

Test (when all steps complete):
```bash
uv run wct run pipeline_test.yaml -v
```

### Validation

```bash
# Run unit tests
cd apps/wct
uv run pytest tests/unit/test_executor.py -v

# Type check
./scripts/type-check.sh

# Lint
./scripts/lint.sh
```

## Success Criteria

- [ ] `_execute_step` detects single-step vs pipeline mode
- [ ] Single-step mode uses connector for extraction (unchanged)
- [ ] Pipeline mode retrieves input from artifacts dict
- [ ] Pipeline mode validates artifact exists
- [ ] ExecutorError raised with helpful message if artifact missing
- [ ] Helper methods `_get_analyser_config` and `_get_connector_config` added
- [ ] Unit tests pass
- [ ] Type checking passes
- [ ] Linting passes

## Notes

- This step connects the pipeline infrastructure together
- Full end-to-end testing requires Step 6 (pipeline schema resolution)
- Error messages should guide users to add `save_output: true`

## Next Step

Step 6: Add pipeline schema resolution method
