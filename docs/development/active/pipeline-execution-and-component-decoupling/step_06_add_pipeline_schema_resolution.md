# Step 6: Add Pipeline Schema Resolution Method

**Phase:** 2 - Implement Sequential Pipeline Execution
**Status:** TODO
**Prerequisites:** Steps 1-5 (pipeline execution logic in place)

## Context

This is part of implementing pipeline execution for WCF, enabling multi-step analysis workflows where data flows between steps.

**Previous steps built:** Pipeline fields, validation, artifact storage, cycle detection, and two-mode execution (connector vs artifact).

**This step adds:** Schema validation for pipeline mode to ensure analysers can process data from previous steps.

**See:** [Pipeline Execution and Component Decoupling](../pipeline-execution-and-component-decoupling.md) for full context and roadmap.

## Purpose

Implement schema resolution for pipeline steps that read from previous steps' artifacts, validating that the analyser can process the input schema and resolving the appropriate output schema.

## Problem

Step 5 added pipeline mode execution, but schema resolution is incomplete. When a step uses `input_from`, we need to validate that:

1. The analyser can process the schema from the previous step's output
2. The analyser supports the requested output schema

**Current gap:**
```yaml
execution:
  - id: "step1"
    connector: mysql_connector
    analyser: personal_data_analyser
    output_schema: personal_data_finding  # Outputs this schema
    save_output: true

  - id: "step2"
    input_from: "step1"
    analyser: data_subject_analyser       # Can it process personal_data_finding?
    output_schema: data_subject_finding
```

**Without validation:**
- Pipeline step might fail at runtime with cryptic schema errors
- No early detection of incompatible schema chains
- Poor debugging experience for users

## Solution

Add a dedicated schema resolution method for pipeline mode that validates the analyser supports the input schema from the artifact and resolves the output schema. Use the input schema from the previous step's Message (already validated when saved) and verify analyser compatibility before execution.

## Decisions Made

1. **Input schema source:** Extract from `input_message.schema` (previous step's output)
2. **Strict validation:** Require exact schema name and version match for input
3. **Reuse existing logic:** Use `_find_compatible_schema` for output schema resolution
4. **Fail fast:** Validate before analyser execution (not during)
5. **Helpful errors:** Include step names, schema details, and supported alternatives

## Implementation

### File to Modify

`apps/wct/src/wct/executor.py`

### Changes Required

#### 1. Add pipeline schema resolution method

**Method:** `_resolve_pipeline_schemas(step, input_message, analyser) -> tuple[Schema, Schema]`

**Purpose:** Validate and resolve schemas for pipeline steps reading from artifacts

**Algorithm (pseudo-code):**
```
function resolve_pipeline_schemas(step, input_message, analyser):
    # Input schema comes from previous step
    input_schema = input_message.schema
    log("Pipeline step '{step.name}' receiving input: {schema}")

    # Validate analyser supports this input schema
    analyser_inputs = analyser.get_supported_input_schemas()

    if input_schema not in analyser_inputs (by name AND version):
        supported_list = format analyser_inputs for display
        raise ExecutorError(
            "Schema mismatch in pipeline step '{step.name}': "
            "Analyser '{step.analyser}' does not support '{input_schema}'. "
            "Supported: {supported_list}"
        )

    # Resolve output schema (reuse existing method)
    output_schema = find_compatible_schema(
        schema_name=step.output_schema,
        requested_version=step.output_schema_version,
        producer_schemas=analyser.get_supported_output_schemas(),
        consumer_schemas=[]  # No downstream consumer yet
    )

    log("Pipeline step '{step.name}' output resolved: {output_schema}")

    return (input_schema, output_schema)
```

**Key considerations:**
- Input schema must match exactly (name and version) - no version compatibility logic yet
- Output schema uses existing `_find_compatible_schema` for consistency
- Error messages include step name and list of supported schemas
- Logging helps debug pipeline schema flow

#### 2. Integration with _execute_step

**Step 5 left placeholder:** Step 5 implementation should call this method in pipeline mode branch.

**Expected call site (in _execute_step):**
```
if step.connector:
    # Single-step mode
    schemas = resolve_step_schemas(step, connector, analyser)
    input_message = connector.extract(schemas.input)
else:
    # Pipeline mode
    input_message = artifacts[step.input_from]
    schemas = resolve_pipeline_schemas(step, input_message, analyser)  # NEW

# Common execution
result_message = analyser.process(schemas.input, schemas.output, input_message)
```

## Testing

### Testing Strategy

**Critical principle:** Test through the **public API** (`execute_runbook`), not by calling private methods directly.

Create runbooks with schema compatibility scenarios and verify behavior through full pipeline execution.

### Test Scenarios

**File:** `apps/wct/tests/test_executor.py`

#### 1. Compatible Schema Chain Succeeds

**Setup:**
- Create runbook with 2 steps
- Step 1: Outputs `personal_data_finding` with `save_output: true`
- Step 2: `input_from: "step1"`, analyser that accepts `personal_data_finding`

**Expected behavior:**
- Both steps execute successfully
- Schema flows from step 1 to step 2
- Step 2 processes step 1's output correctly

#### 2. Incompatible Input Schema Fails

**Setup:**
- Create runbook with 2 steps
- Step 1: Outputs `personal_data_finding` with `save_output: true`
- Step 2: `input_from: "step1"`, analyser that only accepts `source_code` schema

**Expected behavior:**
- `execute_runbook()` raises `ExecutorError`
- Error message mentions "Schema mismatch"
- Error message includes:
  - Step name ("step2")
  - Received schema ("personal_data_finding")
  - List of supported schemas by analyser
  - Actionable guidance

#### 3. Invalid Output Schema Fails

**Setup:**
- Create runbook with pipeline step
- Step specifies `output_schema: "nonexistent_schema"`
- Analyser doesn't support this output schema

**Expected behavior:**
- `execute_runbook()` raises `ExecutorError`
- Error indicates output schema not supported
- Lists available output schemas from analyser

#### 4. Multi-step Pipeline with Schema Transformations

**Setup:**
- Create runbook with 3 steps chained together
- Each step transforms schema: `standard_input` → `personal_data_finding` → `data_subject_finding`
- All schema transitions are compatible

**Expected behavior:**
- All 3 steps execute successfully
- Schemas validated at each pipeline boundary
- Final result contains transformed data

### Implementation Notes

- Use `tempfile.NamedTemporaryFile` for runbook YAML
- Use real connectors/analysers (not mocks) for schema compatibility testing
- Verify error messages are actionable (mention what's wrong and what's supported)
- Test with different analyser combinations to ensure broad coverage

### Validation Commands

```bash
# Run all WCT tests
uv run pytest apps/wct/tests/ -v

# Run pipeline-specific tests
uv run pytest apps/wct/tests/test_executor.py -k "pipeline" -v

# Run dev checks
./scripts/dev-checks.sh
```

## Success Criteria

**Functional:**
- [ ] Compatible schema chains execute successfully across multiple steps
- [ ] Incompatible input schemas detected and rejected with clear error messages
- [ ] Invalid output schemas detected and rejected
- [ ] Input schema extracted correctly from previous step's Message
- [ ] Output schema resolved using existing validation logic
- [ ] Error messages include step names, schema details, and supported alternatives

**Quality:**
- [ ] All tests pass (including new pipeline schema tests)
- [ ] Type checking passes (strict mode)
- [ ] Linting passes
- [ ] No regressions in single-step or existing pipeline functionality

**Code Quality:**
- [ ] Tests use public API (`execute_runbook`) only
- [ ] Schema resolution reuses existing methods where possible
- [ ] Error messages are actionable and user-friendly
- [ ] Logging provides adequate debugging information

## Implementation Notes

**Current architecture:**
- Step 3: `_execute_step` returns tuple, artifacts stored separately
- Step 4: Cycle detection validates dependency graph
- Step 5: Two-mode execution (connector vs artifact)
- **This step:** Adds schema validation for pipeline mode

**Design decisions:**
- Strict matching: Input schema must match exactly (name + version)
- Reuse `_find_compatible_schema`: Maintains consistency with single-step mode
- Validate before execution: Fail fast with helpful errors
- No version compatibility yet: Future enhancement for semantic versioning

**Edge cases to consider:**
- Previous step's Message has no schema (shouldn't happen - Messages validated on creation)
- Analyser supports multiple versions of same schema (exact match wins)
- Output schema validation deferred to existing `_find_compatible_schema`

**Future enhancements (not in this step):**
- Schema version compatibility (e.g., analyser supports v1.0.0, receives v1.1.0)
- Schema transformation hints (e.g., "to process X, first transform to Y")
- Schema compatibility matrix validation at runbook load time (fail earlier)

## Next Steps

After Step 6, **Phase 2 is complete!** Sequential pipeline execution is fully implemented:
- ✅ Pipeline fields and validation (Steps 1-2)
- ✅ Artifact storage and passing (Step 3)
- ✅ Dependency graph validation (Step 4)
- ✅ Two-mode execution logic (Step 5)
- ✅ Schema resolution and validation (Step 6)

**Next phases:**
- **Phase 3:** Refactor SourceCodeConnector → SourceCodeAnalyser
- **Phase 4:** Integration tests, documentation, and example runbooks
- **Future:** Parallel execution, topological sort, advanced schema validation
