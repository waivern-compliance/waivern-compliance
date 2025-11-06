# Step 12: Update Runbook Format and Validation

**Phase:** 5 - Runbook Format Updates
**Dependencies:** Step 11 complete (Phase 4 done)
**Estimated Scope:** Runbook schema and documentation updates

## Purpose

Update runbook JSON schema to support optional version fields, update validation logic, and document version specification in runbooks.

## Files to Modify

1. **`apps/wct/src/wct/runbook.py`** - Add version format validation to ExecutionStep
2. **`apps/wct/runbook.schema.json`** - Regenerate from Pydantic models
3. **`apps/wct/runbooks/README.md`** - Document version specification
4. **`apps/wct/runbooks/samples/version_pinning_example.yaml`** - Create example runbook
5. **`apps/wct/tests/test_runbook_version_validation.py`** - Add validation tests

## Current State

**✅ Already implemented in Step 11:**
- Version fields exist in ExecutionStep (lines 97-104 in `runbook.py`):
  - `input_schema_version: str | None = None`
  - `output_schema_version: str | None = None`
- Executor version matching logic implemented
- Auto-selection of latest compatible versions working

**❌ Missing in Step 12:**
- No format validation on version fields (accepts any string)
- JSON schema outdated (missing version fields)
- Documentation not updated
- No sample runbooks demonstrating version pinning

## Implementation

### 1. Add Version Format Validation to Pydantic Model

**Note:** Pydantic models are the source of truth. JSON Schema is auto-generated from these models.

In `apps/wct/src/wct/runbook.py`, add a field validator to ExecutionStep:

```python
class ExecutionStep(BaseModel):
    """Pydantic model for execution step configuration."""

    # ... existing fields ...

    input_schema_version: str | None = Field(
        default=None,
        description="Optional specific version for input schema (auto-select latest if not specified)",
    )
    output_schema_version: str | None = Field(
        default=None,
        description="Optional specific version for output schema (auto-select latest if not specified)",
    )

    # ... existing fields ...

    @field_validator("input_schema_version", "output_schema_version")
    @classmethod
    def validate_version_format(cls, v: str | None) -> str | None:
        """Validate semantic version format for schema versions.

        Args:
            v: Version string to validate

        Returns:
            Validated version string

        Raises:
            ValueError: If version format is invalid
        """
        if v is None:
            return v

        # Semantic version pattern: major.minor.patch (e.g., "1.0.0")
        pattern = r"^\d+\.\d+\.\d+$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Version must be in format 'major.minor.patch' (e.g., '1.0.0'), got: {v}"
            )
        return v
```

**Don't forget to import re at the top of the file:**
```python
import re
```

### 2. Regenerate JSON Schema

After updating the Pydantic model, regenerate the JSON schema:

```bash
cd apps/wct
uv run wct generate-schema --output runbook.schema.json
```

This command:
1. Calls `Runbook.model_json_schema()` to generate schema from Pydantic models
2. Includes the new `@field_validator` pattern in the JSON schema
3. Saves to `apps/wct/runbook.schema.json`

**Verification:** Check that `runbook.schema.json` now includes:
- `input_schema_version` field with pattern `^\d+\.\d+\.\d+$`
- `output_schema_version` field with pattern `^\d+\.\d+\.\d+$`

### 3. Update Runbook README

Add section to `apps/wct/runbooks/README.md`:

```markdown
## Schema Version Specification

Execution steps support optional version pinning for input and output schemas.

### Auto-Selection (Recommended)

By default, WCT automatically selects the latest compatible schema version:

\```yaml
execution:
  - name: "Analyze data"
    connector: "mysql_connector"
    analyser: "personal_data_analyser"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
    # Versions auto-selected
\```

### Explicit Version Pinning

Pin specific schema versions when needed:

\```yaml
execution:
  - name: "Analyze data with specific versions"
    connector: "mysql_connector"
    analyser: "personal_data_analyser"
    input_schema: "standard_input"
    input_schema_version: "1.0.0"     # Pin input to v1.0.0
    output_schema: "personal_data_finding"
    output_schema_version: "1.0.0"    # Pin output to v1.0.0
\```

### When to Pin Versions

**Use auto-selection when:**
- You want latest features and improvements
- Components are regularly updated
- You trust component maintainers

**Pin versions when:**
- Reproducible results required (compliance audits)
- Testing specific version combinations
- Avoiding breaking changes temporarily
- Integration with external systems requiring specific format

### Version Compatibility

WCT validates version compatibility:
- Connector must support requested input schema version
- Analyser must support requested input schema version
- Analyser must support requested output schema version

If no compatible versions found, WCT provides clear error message with available versions.
\```

### 4. Create Sample Runbook with Versions

Create `apps/wct/runbooks/samples/version_pinning_example.yaml`:

```yaml
name: "Schema Version Pinning Example"
description: "Demonstrates explicit schema version specification"
contact: "engineering@example.com"

connectors:
  - name: "mysql_source"
    type: "mysql"
    properties:
      host: "${MYSQL_HOST}"
      database: "${MYSQL_DATABASE}"

analysers:
  - name: "personal_data_detector"
    type: "personal_data_analyser"
    properties:
      pattern_matching:
        ruleset: "personal_data"
      llm_validation:
        enable_llm_validation: true

execution:
  # Example 1: Auto-select latest versions
  - name: "Auto-select versions (recommended)"
    connector: "mysql_source"
    analyser: "personal_data_detector"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"

  # Example 2: Pin input schema version only
  - name: "Pin input version"
    connector: "mysql_source"
    analyser: "personal_data_detector"
    input_schema: "standard_input"
    input_schema_version: "1.0.0"
    output_schema: "personal_data_finding"

  # Example 3: Pin both input and output versions
  - name: "Pin both versions (reproducible)"
    connector: "mysql_source"
    analyser: "personal_data_detector"
    input_schema: "standard_input"
    input_schema_version: "1.0.0"
    output_schema: "personal_data_finding"
    output_schema_version: "1.0.0"
```

### 5. Validation Logic (Automatic via Pydantic)

**No manual validation code needed!** The `@field_validator` in ExecutionStep automatically:
- Validates version format when runbook is loaded
- Provides clear error messages if format is invalid
- Works with existing `wct validate-runbook` command (uses RunbookLoader)

Example error when invalid version is provided:

```
Runbook validation failed:
  execution -> 0 -> input_schema_version: Version must be in format 'major.minor.patch' (e.g., '1.0.0'), got: invalid
```

**Note:**
- Format validation happens at runbook load time (immediate feedback)
- Compatibility validation happens at execution time (when components are instantiated)
- This provides early error detection while maintaining flexibility

## Testing

### Unit Tests for Version Format Validation

Create `apps/wct/tests/test_runbook_version_validation.py`:

**Test 1: Valid semantic versions**
```python
def test_valid_version_formats():
    """Test that valid semantic versions pass validation."""
    # Test with valid versions: "1.0.0", "2.10.5", "0.0.1"
    # Load runbook via RunbookLoader.load()
    # Assert no validation errors raised
```

**Test 2: Invalid version formats**
```python
def test_invalid_version_formats():
    """Test that invalid version formats raise ValidationError."""
    # Test with invalid: "1.0", "v1.0.0", "1.0.0-beta", "invalid"
    # Attempt to load runbook
    # Assert RunbookValidationError raised with helpful message
```

**Test 3: Backward compatibility**
```python
def test_missing_versions_still_valid():
    """Test that runbooks without version fields are still valid."""
    # Load runbook without input_schema_version/output_schema_version
    # Assert loads successfully (fields are optional)
```

**Test 4: None values accepted**
```python
def test_explicit_null_versions():
    """Test that explicit null/None values are valid."""
    # YAML with `input_schema_version: null`
    # Assert loads successfully
```

### Integration Tests (Already exist)

Version matching integration tests already exist in `test_executor_version_matching.py`:
- ✅ Auto-selection of latest version
- ✅ Explicit version pinning
- ✅ Version compatibility checking
- ✅ Error handling for mismatches

### Run Tests

```bash
cd apps/wct
./scripts/dev-checks.sh
```

All tests should pass including:
- New validation tests
- Existing executor version matching tests
- Backward compatibility with existing runbooks

## Key Decisions

**Backward compatibility:**
- Version fields are optional
- Existing runbooks work without modification
- Default behavior: auto-select latest

**Validation scope:**
- Format validation at runbook load time
- Compatibility validation at execution time
- Clear error messages guide users

**Documentation:**
- Clear guidance on when to pin versions
- Examples of both auto-selection and pinning
- Best practices documented

## Files Modified

1. **`apps/wct/src/wct/runbook.py`** - Add `@field_validator` for version format validation (import `re`)
2. **`apps/wct/runbook.schema.json`** - Regenerated from Pydantic models (auto-includes validation pattern)
3. **`apps/wct/runbooks/README.md`** - Add "Schema Version Specification" section with examples
4. **`apps/wct/runbooks/samples/version_pinning_example.yaml`** - New sample demonstrating version pinning
5. **`apps/wct/tests/test_runbook_version_validation.py`** - New tests for version format validation

**Note:** No changes needed to:
- `cli.py` - Existing `validate-runbook` command already uses RunbookLoader (Pydantic validation)
- `executor.py` - Version matching logic already implemented in Step 11

## Summary

**What Step 12 adds:**
- ✅ Early validation of version format (fail fast at load time)
- ✅ Auto-generated JSON schema includes version validation
- ✅ Comprehensive documentation for users
- ✅ Sample runbooks demonstrating best practices
- ✅ Test coverage for validation edge cases

**Workflow:**
1. User writes runbook YAML with optional version fields
2. RunbookLoader validates format via Pydantic `@field_validator` (immediate feedback)
3. Executor validates compatibility and selects versions at execution time
4. Clear error messages guide users at each step

## Notes

- ✅ **Phase 5 (Runbook Format) complete after this step!**
- ✅ System now fully supports multi-version schemas end-to-end
- ✅ Backward compatible - existing runbooks work without modification
- 📋 **Next:** End-to-end testing and production deployment
