# Step 2: Add Validation for Pipeline Execution Mode

**Phase:** 1 - Extend Runbook Format
**Status:** ✅ Completed (2025-11-11)
**Prerequisites:** Step 1 (pipeline fields added)

## Purpose

Add Pydantic validation logic to ensure pipeline execution steps are configured correctly and that references between steps are valid.

## Decisions Made

1. **Mutual exclusivity** - A step cannot have both `connector` and `input_from`
2. **Required fields** - Either `connector` OR `input_from` must be specified
3. **ID requirement** - Steps with `save_output: true` must have an `id`
4. **Reference validation** - `input_from` must reference a valid step ID
5. **Use Pydantic validators** - Leverage Pydantic's `@model_validator` for cross-field validation

## Implementation

### File to Modify

`apps/wct/src/wct/runbook.py`

### Changes Required

1. **Add validation to `ExecutionStep` class:**

```python
class ExecutionStep(BaseModel):
    """Execution step supporting both single-step and pipeline modes."""

    # ... (fields from Step 1) ...

    @model_validator(mode="after")
    def validate_execution_mode(self) -> ExecutionStep:
        """Validate step configuration based on execution mode.

        Ensures:
        - Exactly one of connector or input_from is specified
        - Steps with save_output have an id
        """
        # Check mutual exclusivity
        if self.connector is not None and self.input_from is not None:
            raise ValueError(
                "Cannot specify both 'connector' and 'input_from'. "
                "Use 'connector' for data extraction or 'input_from' for pipeline chaining."
            )

        # Check at least one is specified
        if self.connector is None and self.input_from is None:
            raise ValueError(
                "Must specify either 'connector' (for extraction) or 'input_from' (for pipeline chaining)"
            )

        # Check id requirement for saved outputs
        if self.save_output and not self.id:
            raise ValueError(
                "Step must have 'id' field when 'save_output' is true (required for referencing)"
            )

        return self
```

2. **Add cross-reference validation to `Runbook` class:**

```python
class Runbook(BaseModel):
    """Pydantic model for complete runbook configuration."""

    # ... (existing fields) ...

    # ... (existing validators) ...

    @model_validator(mode="after")
    def validate_pipeline_references(self) -> Runbook:
        """Validate pipeline step dependencies.

        Ensures all input_from references point to valid step IDs.
        """
        # Collect all step IDs
        step_ids = {step.id for step in self.execution if step.id}

        # Validate references
        for step in self.execution:
            if step.input_from:
                if step.input_from not in step_ids:
                    raise ValueError(
                        f"Step '{step.name}' references unknown step ID '{step.input_from}'. "
                        f"Available step IDs: {sorted(step_ids)}"
                    )

        return self
```

## Testing

### Unit Tests to Add

Add to `apps/wct/tests/unit/test_runbook.py`:

```python
import pytest
from pydantic import ValidationError
from wct.runbook import ExecutionStep, Runbook


def test_pipeline_step_cannot_have_both_connector_and_input_from():
    """Step cannot specify both connector and input_from."""
    with pytest.raises(ValidationError) as exc_info:
        ExecutionStep(
            name="Invalid step",
            description="",
            connector="filesystem",
            input_from="previous_step",  # Conflict!
            analyser="personal_data",
            input_schema="standard_input",
            output_schema="personal_data_finding",
        )

    assert "Cannot specify both 'connector' and 'input_from'" in str(exc_info.value)


def test_pipeline_step_must_have_connector_or_input_from():
    """Step must have either connector or input_from."""
    with pytest.raises(ValidationError) as exc_info:
        ExecutionStep(
            name="Invalid step",
            description="",
            # Missing both connector and input_from
            analyser="personal_data",
            input_schema="standard_input",
            output_schema="personal_data_finding",
        )

    assert "Must specify either 'connector'" in str(exc_info.value)


def test_pipeline_step_requires_id_when_save_output():
    """Step must have id when save_output is true."""
    with pytest.raises(ValidationError) as exc_info:
        ExecutionStep(
            name="Parse code",
            description="",
            input_from="read_files",
            analyser="source_code",
            input_schema="standard_input",
            output_schema="source_code",
            save_output=True,  # Requires id
            # Missing: id field
        )

    assert "must have 'id' field when 'save_output' is true" in str(exc_info.value)


def test_runbook_validates_pipeline_step_references():
    """Runbook validation catches invalid input_from references."""
    with pytest.raises(ValidationError) as exc_info:
        Runbook(
            name="Test Runbook",
            description="Test",
            connectors=[
                {"name": "reader", "type": "filesystem_connector", "properties": {}}
            ],
            analysers=[
                {"name": "analyser", "type": "personal_data_analyser", "properties": {}}
            ],
            execution=[
                {
                    "name": "Step 1",
                    "description": "",
                    "input_from": "non_existent_step",  # Invalid reference!
                    "analyser": "analyser",
                    "input_schema": "standard_input",
                    "output_schema": "personal_data_finding",
                }
            ],
        )

    assert "references unknown step ID 'non_existent_step'" in str(exc_info.value)


def test_runbook_accepts_valid_pipeline():
    """Valid pipeline configuration is accepted."""
    runbook = Runbook(
        name="Pipeline Test",
        description="Valid pipeline",
        connectors=[
            {"name": "reader", "type": "filesystem_connector", "properties": {"path": "."}}
        ],
        analysers=[
            {"name": "parser", "type": "source_code_analyser", "properties": {}},
            {"name": "analyser", "type": "personal_data_analyser", "properties": {}},
        ],
        execution=[
            {
                "id": "read",
                "name": "Read files",
                "description": "",
                "connector": "reader",
                "analyser": "parser",
                "input_schema": "standard_input",
                "output_schema": "source_code",
                "save_output": True,
            },
            {
                "id": "analyse",
                "name": "Analyse",
                "description": "",
                "input_from": "read",  # Valid reference
                "analyser": "analyser",
                "input_schema": "source_code",
                "output_schema": "personal_data_finding",
            },
        ],
    )

    assert len(runbook.execution) == 2
    assert runbook.execution[0].id == "read"
    assert runbook.execution[1].input_from == "read"
```

### Manual Testing

Create a test YAML file `test_invalid_pipeline.yaml`:

```yaml
name: "Invalid Pipeline"
description: "Test validation"

connectors:
  - name: "reader"
    type: "filesystem_connector"
    properties:
      path: "."

analysers:
  - name: "analyser"
    type: "personal_data_analyser"

execution:
  - name: "Bad step"
    connector: "reader"
    input_from: "other"  # Both specified - should fail!
    analyser: "analyser"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
```

Test:
```bash
uv run wct validate-runbook test_invalid_pipeline.yaml
# Should show validation error
```

### Validation

```bash
# Run unit tests
cd apps/wct
uv run pytest tests/unit/test_runbook.py::test_pipeline -v

# Run all wct tests
cd apps/wct
uv run pytest tests/ -v

# Type check
./scripts/type-check.sh

# Lint
./scripts/lint.sh
```

## Success Criteria

- [x] Validation prevents both `connector` and `input_from` being specified (Step 1)
- [x] Validation requires either `connector` OR `input_from` (Step 1)
- [x] Required `id` field for all steps (Step 1 - cleaner than conditional requirement)
- [x] Runbook validation catches invalid `input_from` references
- [x] Valid pipeline configurations are accepted
- [x] All unit tests pass (30/30 passing)
- [x] Type checking passes
- [x] Linting passes

**Note:** Most validation was implemented in Step 1 via ExecutionStep model validators. Step 2 added cross-reference validation in Runbook.validate_cross_references().

## Notes

- Validation happens automatically during runbook loading via Pydantic
- Error messages are user-friendly and indicate the problem clearly
- The `@model_validator(mode="after")` runs after field validation

## Next Step

Step 3: Add artifact storage to Executor
