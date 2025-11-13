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

1. **Scope** - Update 3 sample runbooks in `apps/wct/runbooks/samples/`
2. **Format** - Use inline connector config (type + properties)
3. **Documentation** - Update runbook README with new format
4. **Backward compatibility** - No support for old format (breaking change)

## Expected Outcome & Usage Example

**Updated runbook format:**
```yaml
execution:
  - id: "extract"
    connector:
      type: "mysql"
      properties:
        query: "SELECT * FROM users"
    analyser: personal_data_analyser
    save_output: true

  - id: "classify"
    connector:
      type: "artifact"
      properties:
        step_id: "extract"
    analyser: data_subject_analyser
```

## Implementation

### Changes Required

#### 1. Update file_content_analysis.yaml

**Location:** `apps/wct/runbooks/samples/file_content_analysis.yaml`

**Current structure:**
- Single-step runbook (filesystem → analyser)
- No pipeline steps

**Changes needed:**
- Update connector config to inline format
- Verify format consistency

**Example transformation:**
```yaml
# OLD:
connectors:
  - name: "filesystem_reader"
    type: "filesystem"
    properties: {...}
execution:
  - connector: "filesystem_reader"

# NEW:
execution:
  - id: "analyse_content"
    connector:
      type: "filesystem"
      properties: {...}
```

#### 2. Update LAMP_stack.yaml

**Location:** `apps/wct/runbooks/samples/LAMP_stack.yaml`

**Current structure:**
- Multi-step runbook with MySQL extraction
- Pipeline steps using `input_from`

**Changes needed:**
- Convert all connectors to inline format
- Replace `input_from` with ArtifactConnector
- Ensure `save_output` flags correct

**Example transformation:**
```yaml
# OLD:
execution:
  - id: "extract_db"
    connector: "mysql_connector"
    save_output: true

  - id: "classify"
    input_from: "extract_db"

# NEW:
execution:
  - id: "extract_db"
    connector:
      type: "mysql"
      properties: {...}
    save_output: true

  - id: "classify"
    connector:
      type: "artifact"
      properties:
        step_id: "extract_db"
```

#### 3. Update Third Sample Runbook

**Location:** Third runbook in `apps/wct/runbooks/samples/`

**Changes:**
- Apply same transformation pattern
- Inline connector configs
- Use ArtifactConnector for pipeline steps

#### 4. Remove Old Connector Declarations

**Location:** All updated runbooks

**Changes:**
- Remove top-level `connectors:` section
- Move all configs inline to execution steps
- Ensure no references to named connectors

**Rationale:**
- Simplifies runbook structure
- Eliminates indirection (connector name → config lookup)
- Makes step dependencies explicit

#### 5. Update Runbook Documentation

**Location:** `apps/wct/runbooks/README.md`

**Changes:**
- Document new connector format
- Add ArtifactConnector examples
- Update pipeline execution section
- Remove `input_from` documentation
- Add migration guide for existing runbooks

**Key documentation points:**
- Connector field is now required
- Pipeline steps use `type: "artifact"`
- Artifact connector requires `step_id` property
- `save_output` still required for artifact source steps

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

#### 3. Third Runbook Execution

**Setup:**
- Configure necessary connections
- Execute runbook

**Expected behaviour:**
- Successful execution
- Results validate correctly

#### 4. Runbook Validation

**Setup:**
- Use `wct validate-runbook` command
- Validate all updated runbooks

**Expected behaviour:**
- All runbooks pass validation
- Schema validation accepts new format
- Helpful errors if misconfigured

#### 5. Error Cases

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
1. ✓ Identify all execution steps
2. ✓ Convert external connectors to inline format
3. ✓ Replace `input_from` with ArtifactConnector
4. ✓ Verify `save_output` flags
5. ✓ Remove top-level connectors section
6. ✓ Test execution
7. ✓ Validate schema compliance

**Breaking changes documentation:**
- Document in CHANGELOG
- Update migration guide
- Provide examples for common patterns
- Consider version bump strategy

**Connector type mapping:**
- `mysql` → MySQL connector
- `sqlite` → SQLite connector
- `filesystem` → Filesystem connector
- `artifact` → ArtifactConnector (new)
