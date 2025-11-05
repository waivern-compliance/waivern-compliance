# Step 12: Update Runbook Format and Validation

**Phase:** 5 - Runbook Format Updates
**Dependencies:** Step 11 complete (Phase 4 done)
**Estimated Scope:** Runbook schema and documentation updates

## Purpose

Update runbook JSON schema to support optional version fields, update validation logic, and document version specification in runbooks.

## Files to Modify

1. **Runbook JSON Schema** - Add version fields
2. **`apps/wct/runbooks/README.md`** - Document version specification
3. **Validation logic** - Ensure version fields validated correctly
4. **Sample runbooks** - Add examples with version specification

## Implementation

### 1. Update Runbook JSON Schema

Locate the runbook JSON schema file and add optional version fields to execution steps:

```json
{
  "execution": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "connector": {"type": "string"},
        "analyser": {"type": "string"},
        "input_schema": {"type": "string"},
        "output_schema": {"type": "string"},
        "input_schema_version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+\\.\\d+$",
          "description": "Optional specific version for input schema (e.g., '1.0.0')"
        },
        "output_schema_version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+\\.\\d+$",
          "description": "Optional specific version for output schema (e.g., '1.0.0')"
        }
      },
      "required": ["name", "connector", "analyser", "input_schema", "output_schema"]
    }
  }
}
```

### 2. Update Runbook README

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

### 3. Create Sample Runbook with Versions

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

### 4. Update Runbook Validation

If `wct validate-runbook` exists, update it to:
- Parse optional version fields
- Validate version format (semantic versioning)
- Check version compatibility before execution
- Provide helpful error messages

Example validation logic in CLI:

```python
def validate_runbook(runbook_path: Path):
    """Validate runbook including schema version compatibility."""
    runbook = load_runbook(runbook_path)

    for step in runbook.execution:
        # Validate version format if specified
        if step.input_schema_version:
            if not is_valid_version(step.input_schema_version):
                raise ValidationError(
                    f"Invalid input_schema_version '{step.input_schema_version}' "
                    f"in step '{step.name}'. Must be semantic version (e.g., '1.0.0')"
                )

        if step.output_schema_version:
            if not is_valid_version(step.output_schema_version):
                raise ValidationError(
                    f"Invalid output_schema_version '{step.output_schema_version}' "
                    f"in step '{step.name}'. Must be semantic version (e.g., '1.0.0')"
                )

        # Note: Actual compatibility checking happens at execution time
        # when components are instantiated and schemas discovered
```

## Testing

### Validation Tests

Create `apps/wct/tests/test_runbook_version_validation.py`:

```python
def test_valid_runbook_with_versions():
    """Test runbook with valid version specifications passes validation."""

def test_runbook_with_invalid_version_format():
    """Test runbook with invalid version format fails validation."""

def test_runbook_without_versions_still_valid():
    """Test backward compatibility - runbooks without versions still valid."""
```

### Integration Tests

```python
def test_version_pinning_in_execution():
    """Test execution with explicitly pinned versions works."""

def test_auto_version_selection_in_execution():
    """Test execution without versions auto-selects latest."""
```

### Run Tests

```bash
cd apps/wct
./scripts/dev-checks.sh
```

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

- Runbook JSON schema file
- `apps/wct/runbooks/README.md`
- `apps/wct/runbooks/samples/version_pinning_example.yaml` (new)
- `apps/wct/src/wct/cli.py` (if validation updates needed)
- `apps/wct/tests/test_runbook_version_validation.py` (new)

## Notes

- Phase 5 complete after this step!
- System now fully supports multi-version schemas
- Next: Migrate remaining components to use pattern (Phase 6)
