# Task: Test Pipeline Integration End-to-End

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** DONE
- **Prerequisites:** Step 10 (entry points and exports updated)
- **GitHub Issue:** #216

## Context

This is part of refactoring SourceCodeConnector into a pure transformer analyser. The previous steps created the analyser infrastructure and registered it.

**See:** the parent implementation plan for full context.

## Purpose

Validate that the complete pipeline works: FilesystemConnector → SourceCodeAnalyser → ProcessingPurposeAnalyser, ensuring schema-based data flow functions correctly.

## Problem

Individual unit tests verify component behaviour in isolation, but we need integration tests to verify:
- FilesystemConnector outputs standard_input schema correctly
- SourceCodeAnalyser accepts standard_input and produces source_code schema
- Pipeline execution chains components correctly
- Schema validation catches incompatibilities
- ProcessingPurposeAnalyser can consume source_code schema output

Without integration tests, we can't be confident the refactoring achieves the architectural goal of eliminating hardcoded dependencies.

## Solution

Create integration tests using temporary runbook YAML files that exercise complete pipelines through the executor's public API (`execute_runbook`).

## Decisions Made

1. **Integration test approach** - Use temporary runbooks, not unit tests
2. **Test through executor** - Public API testing only
3. **Real components** - Use actual FilesystemConnector, SourceCodeAnalyser
4. **Temporary files** - Create test PHP files in temp directory
5. **Schema validation** - Verify executor validates schema compatibility

## Implementation

### File to Create/Modify

`libs/waivern-source-code/tests/test_pipeline_integration.py` (or add to `apps/wct/tests/test_executor.py`)

### Test Scenarios

#### 1. FilesystemConnector → SourceCodeAnalyser (2-step pipeline)

**Setup:**
- Create temp directory with sample PHP file containing function
- Create runbook with 2 steps:
  - Step 1: filesystem connector reads files (output: standard_input)
  - Step 2: source_code_analyser parses code (input_from: step 1, output: source_code)
- Execute runbook via executor

**Expected behaviour:**
- Both steps execute successfully
- Step 1 produces standard_input schema with file content
- Step 2 receives standard_input, produces source_code schema
- Final output contains parsed functions and classes
- Schema validation passes at each step

#### 2. FilesystemConnector → SourceCodeAnalyser → ProcessingPurposeAnalyser (3-step pipeline)

**Setup:**
- Create temp directory with PHP file containing data collection patterns
- Create runbook with 3 steps:
  - Step 1: filesystem connector (output: standard_input)
  - Step 2: source_code_analyser (input_from: step 1, output: source_code)
  - Step 3: processing_purpose_analyser (input_from: step 2, output: processing_purpose_finding)
- Execute runbook via executor

**Expected behaviour:**
- All 3 steps execute successfully
- Data flows through pipeline: files → parsed code → findings
- ProcessingPurposeAnalyser successfully processes source_code schema
- Final output contains processing purpose findings
- No hardcoded dependencies visible

#### 3. Schema incompatibility caught (negative test)

**Setup:**
- Create runbook attempting invalid chain:
  - Step 1: filesystem connector (output: standard_input)
  - Step 2: data_subject_analyser (input_from: step 1) ← incompatible!
- data_subject_analyser expects personal_data_finding, not standard_input

**Expected behaviour:**
- Executor raises ExecutorError during schema validation
- Error message indicates schema mismatch
- Error message lists supported input schemas
- No execution occurs (fail fast)

#### 4. Missing save_output flag (negative test)

**Setup:**
- Create 2-step pipeline but forget save_output: true on step 1
- Step 2 references step 1 via input_from

**Expected behaviour:**
- Executor raises ExecutorError
- Error indicates artifact not saved
- Clear error message helps user fix runbook

#### 5. Single-file analysis (edge case)

**Setup:**
- Filesystem connector configured for single file (not directory)
- Pipeline: single file → parse

**Expected behaviour:**
- Pipeline works with single file
- standard_input schema contains 1 file entry
- SourceCodeAnalyser handles single-file input correctly

#### 6. Empty directory (edge case)

**Setup:**
- Filesystem connector points to empty directory
- Pipeline: empty dir → parse

**Expected behaviour:**
- Step 1 succeeds with empty file list
- Step 2 receives empty input, produces empty output
- No errors raised
- Graceful handling of no data

## Testing

### Testing Strategy

Use `pytest` fixtures for temp file/directory creation and cleanup.

Use `tempfile.NamedTemporaryFile` for runbook YAML files.

Mark tests with `@pytest.mark.integration` if they require multiple components.

### Implementation Approach

Each test should:
1. Create temp directory with test files
2. Generate runbook YAML as string
3. Write YAML to temp file
4. Call `executor.execute_runbook(runbook_path)`
5. Assert on results structure and content
6. Clean up temp files in finally block

### Validation Commands

```bash
# Run integration tests
uv run pytest libs/waivern-source-code/tests/test_pipeline_integration.py -v

# Run all source code tests
uv run pytest libs/waivern-source-code/tests/ -v

# Run all quality checks
./scripts/dev-checks.sh
```

## Success Criteria

**Functional:**
- [x] FilesystemConnector → SourceCodeAnalyser pipeline works
- [x] 3-step pipeline (Filesystem → SourceCode → ProcessingPurpose) works
- [x] Schema validation catches incompatible chains
- [x] Missing save_output flag detected
- [x] Single file and empty directory cases handled (covered by component tests)
- [x] No hardcoded dependencies between components

**Quality:**
- [x] All integration tests pass
- [x] Tests use public API only (execute_runbook)
- [x] Tests clean up temp files properly
- [x] Clear test names describe scenarios

**Code Quality:**
- [x] Tests are independent (no shared state)
- [x] Fixtures used for common setup
- [x] Assertions verify outcomes, not implementation
- [x] Error cases tested (negative tests)

## Implementation Notes

**Design considerations:**
- Integration tests slower than unit tests (acceptable tradeoff)
- Tests verify architectural goal achieved
- Real components used, not mocks
- Tests serve as usage examples

**Test data:**
- Create minimal PHP code samples in tests
- Focus on structure, not complex logic
- Data collection patterns for ProcessingPurpose test
- Various file sizes for edge cases

**Error validation:**
- Negative tests critical for robustness
- Verify helpful error messages
- Test fail-fast behaviour

**Future enhancements:**
- Performance benchmarks for pipeline overhead
- Large codebase stress tests
- Parallel execution tests (Phase 7+)
