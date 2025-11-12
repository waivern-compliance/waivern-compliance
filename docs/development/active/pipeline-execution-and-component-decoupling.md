# Task: Pipeline Execution Model and Component Decoupling

**Status:** Phase 4 Complete ✅ (All steps 1-17)
**Priority:** High
**Created:** 2025-11-10
**Last Updated:** 2025-11-12

## Executive Summary

Implement CI/CD-style pipeline execution in WCF to enable multi-step analyser chaining with schema-based routing. This solves two critical architectural violations where components have hardcoded dependencies, enabling true plugin architecture with independent, composable components.

## Problem Statement

### Critical Architectural Violations

After the monorepo refactoring, two components violate the plugin architecture by hardcoding dependencies on other components:

1. **SourceCodeConnector → FilesystemConnector** (CRITICAL)
   - Location: `libs/waivern-source-code/src/waivern_source_code/connector.py:20,54-62`
   - Issue: Direct import and instantiation of FilesystemConnector
   - Impact: Cannot substitute file collection mechanism, breaks component independence

2. **ProcessingPurposeAnalyser → SourceCodeConnector** (CRITICAL)
   - Location: `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/analyser.py:18`
   - Issue: Imports SourceCodeConnector schema models directly
   - Impact: Forces mandatory dependency chain, breaks analyser independence

### Root Cause

SourceCodeConnector has dual responsibility:
- **File discovery/collection** (should be FilesystemConnector's job)
- **Code parsing/analysis** (transformation of standard_input → source_code schema)

This violates single responsibility principle and creates cascading dependencies:
```
ProcessingPurposeAnalyser
    ↓ (hardcoded import)
SourceCodeConnector
    ↓ (hardcoded import)
FilesystemConnector
```

## Solution Overview

Implement pipeline execution to enable schema-based component chaining, then refactor SourceCodeConnector to be a pure transformer analyser.

### Architectural Vision

**Before (Current):**
```yaml
execution:
  - name: "Analyse source code"
    connector: "source_code"  # Hardcodes FilesystemConnector internally
    analyser: "purpose_analyser"
```

**After (Pipeline):**
```yaml
execution:
  - id: "read_files"
    connector: "filesystem"
    output_schema: "standard_input"
    save_output: true

  - id: "parse_code"
    analyser: "source_code_parser"  # SourceCode as transformer!
    input_from: "read_files"
    output_schema: "source_code"
    save_output: true

  - id: "analyse_purposes"
    analyser: "purpose_analyser"
    input_from: "parse_code"
    output_schema: "processing_purpose_finding"
```

### Key Benefits

✅ **Eliminates hardcoded dependencies** - Components become truly independent
✅ **Enables reusability** - SourceCodeAnalyser can accept input from any connector
✅ **Future-proof** - Foundation for parallel execution and complex DAGs
✅ **Schema-driven** - Executor validates compatibility automatically
✅ **Clean architecture** - Breaking change accepted for better long-term design (WCF is pre-1.0)

## Implementation Plan

### Phase 1: Extend Runbook Format ✅ COMPLETED

**Status:** ✅ Completed 2025-11-11
**PR:** #208
**Decision:** Breaking change accepted - WCF is pre-1.0

**What was implemented:**
- Required `id` field for all execution steps
- `input_from` field for pipeline step references
- `save_output` boolean flag for artifact storage
- Mutual exclusivity validation (connector XOR input_from)
- Cross-reference validation ensuring step IDs exist

**Breaking changes:**
- All execution steps now require `id` field
- Old runbooks without `id` fail validation
- Migration: add unique `id` to each execution step

**Deliverables:**
- Updated ExecutionStep Pydantic model
- Enhanced Runbook validation with cross-reference checks
- 9 new validation tests
- All sample and test runbooks updated (3 samples, 29 test steps)


---

### Phase 2: Implement Sequential Pipeline Execution ✅ COMPLETED

**Status:** ✅ Completed 2025-11-11
**PR:** #211
**Issue:** #210

**What was implemented:**

#### Step 3: Artifact Storage
- Modified `_execute_step` to return `tuple[AnalysisResult, Message]`
- AnalysisResult for user output (JSON export)
- Message for pipeline artifacts (internal data passing)
- Artifact dictionary in `execute_runbook` storing Messages by step ID
- Clean separation between user-facing results and pipeline data

#### Step 4: Execution Order Resolution
- Dependency graph validation with cycle detection
- DFS-based algorithm to detect circular dependencies
- Fails fast before execution if cycles exist
- Declaration order execution (topological sort deferred to future)

#### Step 5: Two-Mode Execution
- Connector-based mode: Extract from external source
- Pipeline-based mode: Read from artifacts dict
- Mode detection via `if connector is not None` vs `else`
- Updated helper methods to handle optional connector
- `_resolve_pipeline_schemas` method for pipeline schema resolution

#### Step 6: Pipeline Schema Validation
- Validate analyser supports input schema from previous step
- Exact schema matching (name + version)
- Helpful error messages listing supported schemas
- Debug logging for schema flow

**Deliverables:**
- Multi-step analysis workflows working
- Schema-validated data flow between steps
- 36 executor tests (6 new pipeline-specific tests)
- 901 total tests passing, 0 type errors
- No regressions in existing functionality

**Example pipeline:**
```yaml
execution:
  - id: "extract"
    connector: mysql_connector
    analyser: personal_data_analyser
    save_output: true

  - id: "classify"
    input_from: "extract"
    analyser: data_subject_analyser
```

**Key design decisions:**
- Sequential execution only (parallel deferred to future)
- In-memory artifact storage (no persistence)
- Exact schema matching (no version compatibility logic yet)
- Fail-fast validation before analyser execution

---

### Phase 3: Refactor SourceCodeConnector → SourceCodeAnalyser ✅ COMPLETED

**Status:** ✅ Complete (2025-11-12)
**Location:** `libs/waivern-source-code-analyser/`
**PR:** #217
**Issue:** #217

**What was implemented:**

#### Steps 7-12: Complete refactoring from connector to pure analyser
- **Step 7**: Renamed SourceCodeConnector → SourceCodeAnalyser
- **Step 8**: Updated configuration for schema-based input
- **Step 9**: Created SourceCodeAnalyserFactory with analyser entry point
- **Step 10**: Updated ProcessingPurposeAnalyser to use new package
- **Step 11**: Added end-to-end pipeline integration tests
- **Step 12**: Renamed package to `waivern-source-code-analyser` and removed all connector code

**Key changes implemented:**
1. ✅ Created SourceCodeAnalyser class implementing Analyser interface
2. ✅ Updated configuration to remove path-related fields (handled by FilesystemConnector)
3. ✅ Created SourceCodeAnalyserFactory with analyser entry point
4. ✅ Renamed package to `waivern-source-code-analyser` (matches naming convention)
5. ✅ Removed waivern-filesystem dependency (analyser doesn't perform file I/O)
6. ✅ Deleted all connector source files (connector.py, config.py, factory.py - 532 lines)
7. ✅ Deleted all connector test files (1,247 lines)
8. ✅ Removed connector entry point entirely
9. ✅ Updated all imports throughout codebase
10. ✅ Rewrote README for analyser-only package

**Testing results:**
- 882 tests passing (41 tests removed with connector deletion)
- Integration tests verify FilesystemConnector → SourceCodeAnalyser → ProcessingPurposeAnalyser pipeline
- Unit test coverage for `last_modified` field population
- Type checking passes (strict mode)
- Linting passes

**Migration impact:**
- Breaking change: `source_code_connector` entry point removed
- Package renamed: `waivern-source-code` → `waivern-source-code-analyser`
- Users must update runbooks to use pipeline format
- Migration guide in README

---

### Phase 4: Fix ProcessingPurposeAnalyser Schema Coupling

**Status:** ✅ Complete
**Location:** `libs/waivern-processing-purpose-analyser/`
**Completed:** 2025-11-12

**What was done:**
- Removed waivern-source-code-analyser dependency
- Handler uses dict-based schema handling with TypedDict
- Reader returns TypedDict with cast()
- Deleted 5 redundant integration tests
- 877 tests pass, all quality checks pass

**Result:**
ProcessingPurposeAnalyser now truly independent - no package coupling, schema-driven via Message validation.

---

### Phase 5: Update Tests

**Status:** 📋 Planned

**Test categories:**
1. ✅ Runbook validation tests (9 tests added in Phase 1)
2. ✅ Executor pipeline tests (6 tests added in Phase 2)
3. 📋 SourceCodeAnalyser tests (verify transformation from standard_input)
4. 📋 Integration tests (full pipeline execution)
5. ✅ Migration validation (sample runbooks updated in Phase 1)

**Pending test work:**
- SourceCodeAnalyser unit tests (accept standard_input, produce source_code)
- ProcessingPurposeAnalyser tests with dict-based input handling
- End-to-end pipeline tests (Filesystem → SourceCode → ProcessingPurpose)
- Performance tests for artifact passing overhead

---

### Phase 6: Update Documentation and Examples

**Status:** 📋 Planned

**Documentation needed:**
1. Migration guide (old runbooks → pipeline format)
2. Pipeline execution examples
3. Best practices (when to use pipelines vs single-step)
4. Updated component documentation

**Example runbooks to create:**
- Source code analysis pipeline (Filesystem → SourceCode → ProcessingPurpose)
- Multi-stage data transformation examples
- Schema chaining demonstrations

**Files to update:**
- README.md (add pipeline execution section)
- runbooks/README.md (pipeline examples)
- Core concepts documentation (pipeline architecture)

---

### Phase 7: Validation and Quality Checks

**Status:** 📋 Planned

**Final checklist:**
- [ ] All tests pass (integration tests require API keys)
- [ ] Type checking passes (strict mode)
- [ ] Linting passes
- [ ] No hardcoded cross-component dependencies remain
- [ ] Example pipeline runbooks work end-to-end
- [ ] Migration guide tested with real runbooks
- [ ] Performance acceptable (artifact passing overhead)

**Validation commands:**
```bash
./scripts/dev-checks.sh
uv run pytest -m integration
```

---

## Success Criteria

### Functional Requirements

- ✅ Pipeline execution supports multi-step analyser chaining
- ✅ Schema-based routing validates compatibility automatically
- ✅ Artifact passing works between steps
- ✅ SourceCodeAnalyser accepts `standard_input` schema (Phase 3 complete)
- ✅ ProcessingPurposeAnalyser has no hardcoded imports (Phase 4)
- ✅ Breaking changes accepted for cleaner architecture

### Non-Functional Requirements

- ✅ All components independently installable
- ✅ Code quality standards maintained (877 tests passing, 0 type errors)
- ✅ No hardcoded cross-component dependencies
- ✅ Components depend only on waivern-core and shared utilities
- ✅ True plugin architecture achieved

### Architecture Validation

- ✅ FilesystemConnector is standalone (no changes needed)
- ✅ SourceCodeAnalyser depends only on waivern-core (Phase 3 complete)
- ✅ ProcessingPurposeAnalyser depends only on waivern-core + shared utilities (Phase 4 complete)
- ✅ No circular dependencies
- ✅ Sequential pipeline execution working
- ✅ Dependency graph is clean

---

## Risks and Mitigation

### Risk 1: Breaking Changes ✅ RESOLVED

**Decision:** Breaking change accepted (2025-11-11) - WCF is pre-1.0
**Impact:** Medium
**Status:** ✅ Mitigated in Phases 1-2

**Resolution:**
- All runbooks updated with required `id` field
- Migration straightforward (add `id` to execution steps)
- Clear migration guide in documentation
- Pre-1.0 status makes breaking changes acceptable

### Risk 2: Increased Complexity

**Impact:** Low
**Likelihood:** Medium

**Mitigation:**
- Single-step format still supported (no `input_from`)
- Clear examples for both patterns
- Documentation explains when to use each approach

### Risk 3: Testing Coverage Gaps

**Impact:** High
**Likelihood:** Low

**Mitigation:**
- Comprehensive test coverage in Phase 2 (901 tests passing)
- Integration tests planned for Phase 5
- Example runbooks for manual validation

### Risk 4: Performance Overhead

**Impact:** Low
**Likelihood:** Low

**Mitigation:**
- Artifacts stored only when `save_output: true`
- In-memory storage (no serialization)
- Future optimization: streaming for large datasets

---

## Future Enhancements (Out of Scope)

**Explicitly deferred to future work:**
- Parallel execution (DAG-based, see #189)
- Topological sorting for execution order
- Conditional execution (if/then branching)
- Loop execution (iterate over datasets)
- Artifact persistence (save to disk)
- Artifact visualization (UI)
- Advanced schema routing (automatic conversion)
- Schema version compatibility (semantic versioning)

These can be implemented incrementally without changing core architecture.

---

## Implementation Progress

| Phase | Status | PR | Tests | Notes |
|-------|--------|----|----|-------|
| 1. Extend Runbook Format | ✅ Complete | #208 | 890 passing | Breaking change accepted |
| 2. Pipeline Execution | ✅ Complete | #211 | 901 passing | 6 steps implemented via TDD |
| 3. SourceCode Refactor | ✅ Complete | #217 | 882 passing | 6 steps (7-12) implemented via TDD |
| 4. ProcessingPurpose Fix | ✅ Complete | #218 | 877 passing | Steps 13-17 implemented via TDD |
| 5. Update Tests | 🔄 Partial | - | - | Phase 1-4 tests complete |
| 6. Documentation | 📋 Planned | - | - | Pending Phase 5 |
| 7. Validation | 📋 Planned | - | - | Final quality checks |

**Overall Progress:** 4/7 phases complete (57%)

---

## Development Workflow

**Methodology:** Test-Driven Development (RED-GREEN-REFACTOR)

**For each phase:**
1. Break down into atomic steps (see `step_XX_*.md` files)
2. Use `work-on` skill for TDD implementation
3. Run `./scripts/dev-checks.sh` after each step
4. Use `refactor` skill for code improvements
5. Use `git-commit` skill with conventional commits
6. Create PR when phase complete

**Phases 2, 3, and 4 demonstrated this workflow successfully:**
- Phase 2: 6 atomic steps with individual step documents
- Phase 3: 6 atomic steps (steps 7-12) with individual step documents
- Phase 4: 5 atomic steps (steps 13-17) with individual step documents
- TDD methodology throughout
- All quality checks passing
- Clear git history with conventional commits

---

## References

- **WCF Core Concepts:** `docs/core-concepts/wcf-core-components.md`
- **Current Executor:** `apps/wct/src/wct/executor.py`
- **Runbook Format:** `apps/wct/src/wct/runbook.py`
- **Issue #189:** DAG-based Execution Engine (parent epic)
- **Issue #210:** Phase 2 Implementation (closed by PR #211)
- **Issue #217:** Phase 3 Implementation (closed by PR #218)

---

**Document Version:** 5.0 (Phase 4 Complete)
**Last Updated:** 2025-11-12
