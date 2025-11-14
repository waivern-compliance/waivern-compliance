# Task: Migrate Sample Runbooks to Unified Format

- **Phase:** Unified Connector Architecture - Phase 3
- **Status:** TODO
- **Prerequisites:** Executor refactoring (Task 2)
- **Related Issue:** #226

## Context

Updates sample runbooks to use the unified connector format where every step explicitly declares its connector. This completes the migration to unified architecture and provides examples for users.

## Purpose

Migrate existing runbooks to new format and verify the unified architecture works end-to-end with real use cases.

## Problem

Current runbooks use optional connector with `input_from` field:

```yaml
execution:
  - id: "extract"
    connector: mysql_connector
    analyser: personal_data_analyser
    save_output: true

  - id: "classify"
    input_from: "extract"  # No connector declared
    analyser: data_subject_analyser
```

This format no longer supported after Executor refactoring.

## Proposed Solution

Update all sample runbooks to use ArtifactConnector for pipeline steps, making connector field explicit for every step.

## Decisions Made

1. **Scope** - Update 2 sample runbooks in `apps/wct/runbooks/samples/`
2. **Format** - Use named connector references (keep top-level connectors section)
3. **Documentation** - Update runbook README with artifact connector examples
4. **Backward compatibility** - No support for old format (breaking change)

## Expected Outcome & Usage Example

**Updated runbook format:**
```yaml
connectors:
  - name: "mysql_source"
    type: "mysql"
    properties:
      query: "SELECT * FROM users"
  - name: "artifact_from_extract"
    type: "artifact"
    properties:
      step_id: "extract"

execution:
  - id: "extract"
    connector: "mysql_source"
    analyser: personal_data_analyser
    save_output: true

  - id: "classify"
    connector: "artifact_from_extract"  # Required field, no more input_from
    analyser: data_subject_analyser
```

## Implementation

### Changes Required

#### 1. Update file_content_analysis.yaml

**Location:** `apps/wct/runbooks/samples/file_content_analysis.yaml`

**Current structure:**
- Single-step runbook (filesystem → analyser)
- No pipeline steps
- Already uses named connector format

**Changes needed:**
- Make `connector` field explicit (ensure not Optional)
- Verify `id` field present on all execution steps
- No artifact connectors needed (single-step runbook)

**Example (minimal change):**
```yaml
# Remains mostly unchanged - already has named connector
connectors:
  - name: "filesystem_reader"
    type: "filesystem"
    properties: {...}

execution:
  - id: "analyse_content"  # Ensure id present
    connector: "filesystem_reader"  # Already required
    analyser: personal_data_analyser
```

#### 2. Update LAMP_stack.yaml

**Location:** `apps/wct/runbooks/samples/LAMP_stack.yaml`

**Current structure:**
- Multi-step runbook with MySQL extraction
- Pipeline steps using `input_from`

**Changes needed:**
- Add artifact connector declarations to connectors section
- Replace `input_from` with artifact connector references
- Ensure `save_output` flags correct on source steps

**Example transformation:**
```yaml
# OLD:
connectors:
  - name: "mysql_connector"
    type: "mysql"
    properties: {...}

execution:
  - id: "extract_db"
    connector: "mysql_connector"
    save_output: true

  - id: "classify"
    input_from: "extract_db"  # Uses input_from
    analyser: data_subject_analyser

# NEW:
connectors:
  - name: "mysql_connector"
    type: "mysql"
    properties: {...}
  - name: "artifact_from_extract_db"  # NEW artifact connector
    type: "artifact"
    properties:
      step_id: "extract_db"

execution:
  - id: "extract_db"
    connector: "mysql_connector"
    save_output: true

  - id: "classify"
    connector: "artifact_from_extract_db"  # Uses artifact connector
    analyser: data_subject_analyser
```

#### 3. Update Runbook Documentation

**Location:** `apps/wct/runbooks/README.md`

**Changes:**
- Document artifact connector type
- Add examples of artifact connector declarations
- Update pipeline execution section
- Remove `input_from` documentation
- Add migration guide for existing runbooks

**Key documentation points:**
- Connector field is now required (no longer Optional)
- Pipeline steps use artifact connector with `type: "artifact"`
- Artifact connector requires `step_id` property pointing to previous step
- `save_output` still required on source steps for artifact storage
- Connectors section remains (named references preserved)

## Testing

### Testing Strategy

Run each updated runbook and verify successful execution with expected results.

### Test Scenarios

#### 1. file_content_analysis.yaml Execution

**Setup:**
- Use updated runbook
- Provide test input file

**Expected behaviour:**
- Runbook executes successfully
- Results match previous format
- No errors or warnings

#### 2. LAMP_stack.yaml Execution

**Setup:**
- Configure MySQL connection
- Run updated runbook

**Expected behaviour:**
- All steps execute in order
- Artifact passing works correctly
- Multi-step pipeline produces expected results

#### 3. Runbook Validation

**Setup:**
- Use `wct validate-runbook` command
- Validate all updated runbooks

**Expected behaviour:**
- All runbooks pass validation
- Schema validation accepts new format (artifact connector type)
- Helpful errors if misconfigured

#### 4. Error Cases

**Setup:**
- Create runbook with invalid artifact connector config
- Missing step_id, non-existent step reference, etc.

**Expected behaviour:**
- Clear error messages
- Validation catches issues early
- Execution fails gracefully with context

### Validation Commands

```bash
# Validate each runbook
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct validate-runbook apps/wct/runbooks/samples/LAMP_stack.yaml

# Execute each runbook (with appropriate config)
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v

# Run all quality checks
./scripts/dev-checks.sh
```

## Implementation Notes

**Migration checklist per runbook:**
1. ✓ Identify all execution steps with `input_from`
2. ✓ Add artifact connector declarations to connectors section
3. ✓ Replace `input_from` references with artifact connector names
4. ✓ Verify `save_output` flags on source steps
5. ✓ Ensure all execution steps have required `connector` field
6. ✓ Test execution
7. ✓ Validate schema compliance

**Breaking changes documentation:**
- Document in CHANGELOG or migration guide
- Provide examples for pipeline step migration
- Show before/after for `input_from` → artifact connector
- Update runbook schema documentation

**Connector type mapping:**
- `mysql` → MySQL connector
- `sqlite` → SQLite connector
- `filesystem` → Filesystem connector
- `artifact` → ArtifactConnector (new)

**Note:** Named connector format preserved - inline configuration is future work (DAG orchestration Epic)
