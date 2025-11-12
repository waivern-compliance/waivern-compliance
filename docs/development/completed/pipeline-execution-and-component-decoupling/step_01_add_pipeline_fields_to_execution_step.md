# Step 1: Refactor ExecutionStep to Pipeline-Only Model

**Phase:** 1 - Extend Runbook Format
**Status:** ✅ Completed (2025-11-11)
**Prerequisites:** None

## Purpose

Refactor the `ExecutionStep` Pydantic model to use a clean pipeline-only design. This is a **breaking change** that simplifies the model by making all execution steps explicit pipeline steps with clear data flow.

## Decisions Made

1. **Drop backward compatibility** - WCF is pre-1.0, breaking changes are acceptable for better design
2. **Every step has an ID** - Required `id` field for explicit step referencing
3. **Connector XOR input_from** - Steps are either connector-based OR input-based (mutually exclusive)
4. **Analyser is optional** - Connector-only steps don't require an analyser
5. **Explicit data flow** - `save_output` flag clearly marks steps that produce artifacts for chaining

### Rationale for Breaking Change

**Problems with backward compatibility approach:**
- `connector` being optional creates ambiguity
- Complex validation (single-step mode vs pipeline mode)
- Mixed mental models in the same codebase

**Benefits of clean break:**
- Simpler model: every step is a pipeline step
- Clearer data flow: explicit `input_from` references
- Better separation: connector steps vs transformer steps
- Easier to implement and maintain

**Migration cost:**
- ~5 sample runbooks need updating (low cost)
- No production deployments yet (pre-1.0)

## Implementation

### File to Modify

`apps/wct/src/wct/runbook.py`

### Changes Required

1. **Update imports** - Ensure `Field` and `model_validator` are imported from Pydantic

2. **Refactor `ExecutionStep` class:**

```python
class ExecutionStep(BaseModel):
    """Pipeline execution step with explicit data flow.

    Each step is either:
    - Connector-based: Reads from external source (connector + optional analyser)
    - Input-based: Transforms previous step output (input_from + analyser)

    Steps are mutually exclusive: connector XOR input_from.
    """

    # Step identification (REQUIRED)
    id: str = Field(
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Unique identifier for this step (required for pipeline chaining)",
    )

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

    # Data source (connector OR input_from, mutually exclusive)
    connector: str | None = Field(
        default=None,
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Name of connector instance (for connector-based steps)",
    )
    input_from: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Step ID to read input from (for input-based steps)",
    )

    # Processing (analyser optional for connector-only steps)
    analyser: str | None = Field(
        default=None,
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Name of analyser instance to use (optional for connector-only steps)",
    )

    # Schema definitions
    input_schema: str = Field(
        min_length=1,
        description="Schema name for connector output or previous step output validation"
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

    # Pipeline control
    save_output: bool = Field(
        default=False,
        description="Whether to save output for use by subsequent steps",
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional execution metadata and runtime configuration",
    )

    @model_validator(mode="after")
    def validate_connector_xor_input_from(self) -> "ExecutionStep":
        """Validate that connector and input_from are mutually exclusive."""
        if self.connector is not None and self.input_from is not None:
            msg = "Step cannot have both 'connector' and 'input_from' - choose one data source"
            raise ValueError(msg)

        if self.connector is None and self.input_from is None:
            msg = "Step must have either 'connector' or 'input_from' as data source"
            raise ValueError(msg)

        return self
```

**Key changes:**
- `id` is now **required** (not optional)
- `connector` and `input_from` are mutually exclusive (enforced by validator)
- `analyser` is now **optional** (connector-only steps don't need one)
- Added `model_validator` to enforce XOR constraint
- Updated docstring to reflect pipeline-only design

## Testing

### Unit Tests to Add

Add to `apps/wct/tests/test_runbook.py` - new test class:

```python
class TestPipelineExecutionStep:
    """Tests for pipeline-only ExecutionStep model."""

    def test_connector_based_step_with_analyser(self) -> None:
        """Test connector-based step with analyser."""
        step = ExecutionStep(
            id="read_and_analyse",
            name="Read and analyse files",
            description="Read files and analyse for personal data",
            connector="filesystem",
            analyser="personal_data",
            input_schema="standard_input",
            output_schema="personal_data_finding",
            save_output=True,
        )

        assert step.id == "read_and_analyse"
        assert step.connector == "filesystem"
        assert step.analyser == "personal_data"
        assert step.input_from is None
        assert step.save_output is True

    def test_connector_based_step_without_analyser(self) -> None:
        """Test connector-only step (no analyser)."""
        step = ExecutionStep(
            id="read_files",
            name="Read source files",
            description="Read files from filesystem",
            connector="filesystem",
            input_schema="standard_input",
            output_schema="standard_input",
            save_output=True,
        )

        assert step.connector == "filesystem"
        assert step.analyser is None
        assert step.input_from is None

    def test_input_based_step_with_analyser(self) -> None:
        """Test input-based transformer step."""
        step = ExecutionStep(
            id="parse_code",
            name="Parse source code",
            description="Transform files to code structure",
            input_from="read_files",
            analyser="source_code_parser",
            input_schema="standard_input",
            output_schema="source_code",
            save_output=True,
        )

        assert step.id == "parse_code"
        assert step.input_from == "read_files"
        assert step.analyser == "source_code_parser"
        assert step.connector is None
        assert step.save_output is True

    def test_id_field_required(self) -> None:
        """Test that id field is required."""
        with pytest.raises(ValidationError, match="id"):
            ExecutionStep(
                name="No ID step",
                description="Missing ID",
                connector="filesystem",
                input_schema="standard_input",
                output_schema="standard_input",
            )

    def test_connector_xor_input_from_both_fails(self) -> None:
        """Test that having both connector and input_from fails validation."""
        with pytest.raises(ValidationError, match="cannot have both"):
            ExecutionStep(
                id="invalid",
                name="Invalid step",
                description="Has both connector and input_from",
                connector="filesystem",
                input_from="previous_step",
                analyser="analyser",
                input_schema="standard_input",
                output_schema="output",
            )

    def test_connector_xor_input_from_neither_fails(self) -> None:
        """Test that having neither connector nor input_from fails validation."""
        with pytest.raises(ValidationError, match="must have either"):
            ExecutionStep(
                id="invalid",
                name="Invalid step",
                description="Has neither connector nor input_from",
                analyser="analyser",
                input_schema="standard_input",
                output_schema="output",
            )

    def test_save_output_defaults_false(self) -> None:
        """Test that save_output defaults to False."""
        step = ExecutionStep(
            id="step1",
            name="Test step",
            description="Test",
            connector="conn",
            input_schema="input",
            output_schema="output",
        )

        assert step.save_output is False
```

### Manual Testing

1. Attempt to load existing runbooks - they should FAIL validation (expected breaking change)
2. Create a test pipeline runbook with new format
3. Verify validation accepts the new format
4. Verify XOR validation works (both connector+input_from should fail)

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

- [x] `ExecutionStep` model refactored with pipeline-only design
- [x] `id` field is required
- [x] `connector` and `input_from` are mutually exclusive (XOR validation)
- [x] `analyser` field is now optional
- [x] `save_output` field added with default False
- [x] Model validator enforces connector XOR input_from constraint
- [x] Existing runbooks FAIL validation (expected breaking change - 12 tests fail as expected)
- [x] All new unit tests pass (7/7 pipeline tests passing)
- [x] Type checking passes (strict mode)
- [x] Linting passes

## Migration Notes

### Breaking Changes

**Old format (no longer valid):**
```yaml
execution:
  - name: "Analyse data"
    description: "..."
    connector: "filesystem"
    analyser: "personal_data"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
```

**New format (required):**
```yaml
execution:
  - id: "read_and_analyse"
    name: "Analyse data"
    description: "..."
    connector: "filesystem"
    analyser: "personal_data"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
```

### Runbooks to Update

After this step is complete, the following sample runbooks will need updating:
- `apps/wct/runbooks/samples/file_content_analysis.yaml`
- `apps/wct/runbooks/samples/LAMP_stack.yaml`
- Any other example runbooks in the repository

These will be updated in Step 2 after validation logic is added.

## Notes

- This step includes basic XOR validation via `model_validator`
- Advanced pipeline validation (dependency resolution, cycles) comes in Step 2
- The pattern regex ensures valid identifiers (no spaces, special chars)
- Breaking change is acceptable (WCF is pre-1.0)

## Next Step

Step 2: Implement pipeline execution engine with artifact storage and dependency resolution
