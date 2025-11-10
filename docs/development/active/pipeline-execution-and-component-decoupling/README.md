# Pipeline Execution and Component Decoupling - Implementation Steps

**Task Document:** `docs/tasks/pipeline-execution-and-component-decoupling.md`
**Status:** In Progress
**Created:** 2025-11-10

## Overview

This directory contains atomic implementation steps for adding CI/CD-style pipeline execution to WCF and removing hardcoded component dependencies.

## Implementation Steps

### Phase 1: Extend Runbook Format (Steps 1-2)

- [x] **Step 1:** Add pipeline fields to ExecutionStep model
- [x] **Step 2:** Add validation for pipeline execution mode

### Phase 2: Implement Sequential Pipeline Execution (Steps 3-6)

- [x] **Step 3:** Add artifact storage to Executor
- [x] **Step 4:** Implement execution order resolution (cycle detection)
- [x] **Step 5:** Update _execute_step to support pipeline mode
- [ ] **Step 6:** Add pipeline schema resolution method

### Phase 3: Refactor SourceCodeConnector → SourceCodeAnalyser (Steps 7-10)

- [ ] **Step 7:** Create SourceCodeAnalyserConfig
- [ ] **Step 8:** Create SourceCodeAnalyser class
- [ ] **Step 9:** Create SourceCodeAnalyserFactory
- [ ] **Step 10:** Update entry points and remove FilesystemConnector dependency

### Phase 4: Fix ProcessingPurposeAnalyser Schema Coupling (Steps 11-12)

- [ ] **Step 11:** Refactor source_code schema handlers to use dictionaries
- [ ] **Step 12:** Remove waivern-source-code dependency

### Phase 5: Update Tests (Steps 13-17)

- [ ] **Step 13:** Add runbook validation tests for pipeline
- [ ] **Step 14:** Add executor pipeline tests
- [ ] **Step 15:** Add SourceCodeAnalyser unit tests
- [ ] **Step 16:** Add integration tests for full pipeline
- [ ] **Step 17:** Add backward compatibility tests

### Phase 6: Update Documentation and Examples (Steps 18-20)

- [ ] **Step 18:** Create pipeline example runbook
- [ ] **Step 19:** Create migration guide
- [ ] **Step 20:** Update existing documentation

### Phase 7: Validation and Quality Checks (Steps 21-22)

- [ ] **Step 21:** Run full test suite and dev-checks
- [ ] **Step 22:** Verify no hardcoded dependencies remain

## Progress Tracking

| Phase | Steps | Completed | Status |
|-------|-------|-----------|--------|
| 1. Extend Runbook Format | 2 | 0 | Pending |
| 2. Pipeline Execution | 4 | 0 | Pending |
| 3. SourceCode Refactor | 4 | 0 | Pending |
| 4. ProcessingPurpose Fix | 2 | 0 | Pending |
| 5. Update Tests | 5 | 0 | Pending |
| 6. Documentation | 3 | 0 | Pending |
| 7. Validation | 2 | 0 | Pending |
| **Total** | **22** | **0** | **0%** |

## How to Use

1. Read each step file in order
2. Implement the changes described
3. Run the tests specified in each step
4. Mark step as complete when all success criteria are met
5. Proceed to next step

## Dependencies

Steps must be completed in order within each phase. Some phases depend on previous phases:

- Phase 2 depends on Phase 1
- Phase 3 depends on Phase 2
- Phase 4 can be done in parallel with Phase 3
- Phase 5 depends on Phases 3 and 4
- Phase 6 depends on Phases 3 and 4
- Phase 7 depends on all previous phases

## Critical Success Factors

✅ All tests pass at each step
✅ Dev-checks pass after each step
✅ Backward compatibility maintained
✅ No hardcoded dependencies remain
✅ Pipeline execution works end-to-end
