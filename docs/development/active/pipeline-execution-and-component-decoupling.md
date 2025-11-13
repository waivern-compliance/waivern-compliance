# Task: Pipeline Execution Model and Component Decoupling

- **Status:** Phase 5 Complete ✅
- **Priority:** High
- **Created:** 2025-11-10
- **Last Updated:** 2025-11-12

## Executive Summary

Implement CI/CD-style pipeline execution in WCF to enable multi-step analyser chaining with schema-based routing. This solves two critical architectural violations where components have hardcoded dependencies, enabling true plugin architecture with independent, composable components.

## Problem Statement

### Critical Architectural Violations

Two components violate the plugin architecture by hardcoding dependencies on other components:

1. **SourceCodeConnector → FilesystemConnector**
   - Location: `libs/waivern-source-code/src/waivern_source_code/connector.py:20,54-62`
   - Issue: Direct import and instantiation of FilesystemConnector
   - Impact: Cannot substitute file collection mechanism, breaks component independence

2. **ProcessingPurposeAnalyser → SourceCodeConnector**
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
    analyser: "source_code_parser"  # SourceCode as transformer (an analyser)!
    input_from: "read_files"
    output_schema: "source_code"
    save_output: true

  - id: "analyse_purposes"
    analyser: "purpose_analyser"
    input_from: "parse_code"
    output_schema: "processing_purpose_finding"
```

### Key Benefits

- **Eliminates hardcoded dependencies** - Components become truly independent
- **Enables reusability** - SourceCodeAnalyser can accept input from any connector as long as the connector can output `standard_output` schema
- **Future-proof** - Foundation for parallel execution and complex DAGs
- **Schema-driven** - Executor validates compatibility automatically
- **Clean architecture** - Breaking change accepted for better long-term design (WCF is pre-1.0)

## Implementation Plan

### Phase 1: Extend Runbook Format ✅ Complete

- **Status:** ✅ Completed 2025-11-11
- **PR:** #208
- **Decision:** Breaking change accepted - WCF is pre-1.0

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
- New validation tests
- All sample and test runbooks updated


---

### Phase 2: Implement Sequential Pipeline Execution ✅ Complete

- **Status:** ✅ Completed 2025-11-11
- **PR:** #211
- **Issue:** #210

#### **What was implemented:**

###### Artifact Storage
- Modified `_execute_step` to return `tuple[AnalysisResult, Message]`
- AnalysisResult for user output (JSON export)
- Message for pipeline artifacts (internal data passing)
- Artifact dictionary in `execute_runbook` storing Messages by step ID
- Clean separation between user-facing results and pipeline data

###### Execution Order Resolution
- Dependency graph validation with cycle detection
- DFS-based algorithm to detect circular dependencies
- Fails fast before execution if cycles exist
- Declaration order execution (topological sort deferred to future)

###### Two-Mode Execution
- Connector-based mode: Extract from external source
- Pipeline-based mode: Read from artifacts dict
- Mode detection via `if connector is not None` vs `else`
- Updated helper methods to handle optional connector
- `_resolve_pipeline_schemas` method for pipeline schema resolution

###### Pipeline Schema Validation
- Validate analyser supports input schema from previous step
- Exact schema matching (name + version)
- Helpful error messages listing supported schemas
- Debug logging for schema flow

**Deliverables:**
- Multi-step analysis workflows working
- Schema-validated data flow between steps

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
- Exact schema matching
- Fail-fast validation before analyser execution

---

### Phase 3: Refactor SourceCodeConnector → SourceCodeAnalyser ✅ Complete

- **Status:** ✅ Complete
- **Location:** `libs/waivern-source-code-analyser/`
- **PR:** #217
- **Issue:** #217

**What was implemented:**

- Renamed SourceCodeConnector → SourceCodeAnalyser
- Updated configuration for schema-based input
- Created SourceCodeAnalyserFactory with analyser entry point
- Updated ProcessingPurposeAnalyser to use new package
- Added end-to-end pipeline integration tests
- Renamed package to `waivern-source-code-analyser` and removed all connector code

**Migration impact:**
- Migration guide in README

---

### Phase 4: Fix ProcessingPurposeAnalyser Schema Coupling

- **Status:** ✅ Complete
- **Location:** `libs/waivern-processing-purpose-analyser/`
- **Completed:** 2025-11-12

**What was done:**
- Removed waivern-source-code-analyser dependency
- Handler uses dict-based schema handling with TypedDict
- Reader returns TypedDict with cast()

**Result:**
ProcessingPurposeAnalyser now truly independent - no package coupling, schema-driven via Message validation.

---

### Phase 5: Update Tests ✅ Complete

**Status:** ✅ Complete

**Test categories:**

1. ✅ Runbook validation tests
2. ✅ Executor pipeline tests
3. ✅  SourceCodeAnalyser tests (verify transformation from standard_input)
4. ✅ Integration tests (full pipeline execution through sample runbooks)
5. ✅ Migration validation (sample runbooks updated in Phase 1)

**Pending test work:**
- SourceCodeAnalyser unit tests (accept standard_input, produce source_code)
- ProcessingPurposeAnalyser tests with dict-based input handling
- End-to-end pipeline tests (Filesystem → SourceCode → ProcessingPurpose)
- Performance tests for artifact passing overhead

---

### Phase 6: Update Documentation and Examples ✅ Complete

**Status:** ✅ Complete

**Documentation needed:**

1. Runbook development guild and README.md
2. Updated component documentation

**Example runbooks to create:**
- Source code analysis pipeline (Filesystem → SourceCode → ProcessingPurpose)
- Schema chaining demonstrations

**Files to update:**
- runbooks/README.md (pipeline examples)
- Core concepts documentation (pipeline architecture)

---

### Phase 7: Review & Refactor ✅ Complete

**Status:** ✅ Complete

Reivew all the work described in this document so far and identify refactoring opportunities.

**Validation commands:**
```bash
./scripts/dev-checks.sh
uv run pytest -m integration
```

---

## Future Enhancements (Out of Scope)

**Explicitly deferred to future work:**
- Parallel execution (DAG-based, see #189)
- Topological sorting for execution order
- Conditional execution (if/then branching)
- Loop execution (iterate over datasets)
- Artifact persistence (save to disk)
- Advanced schema routing (automatic conversion)

These can be implemented incrementally without changing core architecture.

---

## Development Workflow

**Methodology:** Test-Driven Development (RED-GREEN-REFACTOR)

**For each phase:**
1. Break down into atomic steps (see `step_XX_*.md` files)
2. Use `work-on` skill for TDD implementation
3. Run `./scripts/dev-checks.sh` after each step
4. Use `refactor` skill for code improvements
5. Use `git-commit` skill with conventional commits
6. Create PR with `/pr-create` command when phase complete

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
