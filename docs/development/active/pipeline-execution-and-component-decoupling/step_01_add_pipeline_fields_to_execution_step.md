# Step 1: Add Pipeline Fields to ExecutionStep Model

**Phase:** 1 - Extend Runbook Format
**Status:** Pending
**Prerequisites:** None

## Purpose

Add new optional fields to the `ExecutionStep` Pydantic model to support pipeline execution while maintaining backward compatibility with existing single-step runbooks.

## Decisions Made

1. **Make `connector` field optional** - Pipeline steps can chain from previous steps without a connector
2. **Add three new optional fields:**
   - `id`: Unique identifier for referencing steps in pipeline
   - `input_from`: Reference to previous step's output
   - `save_output`: Flag to save output for subsequent steps
3. **Maintain backward compatibility** - Existing runbooks without these fields continue to work

## Implementation

### File to Modify

`apps/wct/src/wct/runbook.py`

### Changes Required

1. **Update imports** - Ensure `Field` and `model_validator` are imported from Pydantic

2. **Modify `ExecutionStep` class:**

```python
class ExecutionStep(BaseModel):
    """Execution step supporting both single-step and pipeline modes."""

    # Existing fields
    name: str = Field(
        min_length=1,
        description="Human-readable name for this execution step",
    )
    description: str = Field(
        description="Description of what this execution step does (can be empty)",
    )
    contact: str | None = Field(
        default=None,
        description="Optional contact information for this execution step"
    )

    # CHANGED: Make connector optional (None for pipeline steps)
    connector: str | None = Field(
        default=None,
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Name of connector instance to use (required for single-step mode)",
    )

    analyser: str = Field(
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Name of analyser instance to use",
    )
    input_schema: str = Field(
        min_length=1,
        description="Schema name for connector output validation"
    )
    output_schema: str = Field(
        min_length=1,
        description="Schema name for analyser output validation"
    )
    input_schema_version: str | None = Field(
        default=None,
        description="Optional specific version for input schema (auto-select latest if not specified)",
    )
    output_schema_version: str | None = Field(
        default=None,
        description="Optional specific version for output schema (auto-select latest if not specified)",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional execution metadata and runtime configuration",
    )

    # NEW: Pipeline execution fields
    id: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Unique identifier for this step (required for pipeline mode when save_output is true)",
    )
    input_from: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Step ID to read input from (for analyser-only pipeline steps)",
    )
    save_output: bool = Field(
        default=False,
        description="Whether to save output for use by subsequent steps",
    )
```

## Testing

### Unit Tests to Add

Create or update `apps/wct/tests/unit/test_runbook.py`:

```python
def test_execution_step_supports_pipeline_fields():
    """Pipeline fields can be specified."""
    step = ExecutionStep(
        id="parse_code",
        name="Parse source code",
        description="Extract code structure",
        input_from="read_files",
        analyser="source_code_analyser",
        input_schema="standard_input",
        output_schema="source_code",
        save_output=True,
    )

    assert step.id == "parse_code"
    assert step.input_from == "read_files"
    assert step.save_output is True
    assert step.connector is None  # No connector for pipeline steps


def test_execution_step_backward_compatible():
    """Old single-step format still works."""
    step = ExecutionStep(
        name="Analyse data",
        description="Personal data analysis",
        connector="filesystem_reader",
        analyser="personal_data_analyser",
        input_schema="standard_input",
        output_schema="personal_data_finding",
    )

    assert step.connector == "filesystem_reader"
    assert step.id is None
    assert step.input_from is None
    assert step.save_output is False
```

### Manual Testing

1. Load an existing runbook (e.g., `file_content_analysis.yaml`)
2. Verify it still validates correctly
3. Create a test runbook with new pipeline fields
4. Verify validation accepts the new fields

### Validation

```bash
# Run unit tests
cd apps/wct
uv run pytest tests/unit/test_runbook.py -v

# Run type checking
cd apps/wct
./scripts/type-check.sh

# Run linting
cd apps/wct
./scripts/lint.sh
```

## Success Criteria

- [ ] `ExecutionStep` model accepts new `id`, `input_from`, and `save_output` fields
- [ ] `connector` field is now optional
- [ ] Existing runbooks still validate correctly
- [ ] Unit tests pass
- [ ] Type checking passes
- [ ] Linting passes

## Notes

- This step does NOT add validation logic yet - that comes in Step 2
- The new fields are all optional to maintain backward compatibility
- The pattern regex ensures valid identifiers (no spaces, special chars)

## Next Step

Step 2: Add validation for pipeline execution mode
