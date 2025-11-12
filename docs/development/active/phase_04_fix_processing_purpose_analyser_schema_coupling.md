# Phase 4: Fix ProcessingPurposeAnalyser Schema Coupling

- **Status:** 📋 Planned
- **Priority:** High
- **Created:** 2025-11-12
- **Parent Task:** [Pipeline Execution and Component Decoupling](pipeline-execution-and-component-decoupling.md)

## Executive Summary

Remove direct dependency on SourceCodeAnalyser's typed Pydantic models from ProcessingPurposeAnalyser. Transform the analyser to use dictionary-based schema handling, relying on Message object validation instead of hardcoded type imports. This completes the architectural goal of eliminating all hardcoded cross-component dependencies.

## Context

This is the final phase in eliminating architectural violations where components have hardcoded dependencies on other components. Phase 3 successfully transformed SourceCodeConnector into a pure analyser. Now we need to remove the reverse dependency: ProcessingPurposeAnalyser importing SourceCodeAnalyser's schema models.

**See:** `docs/development/active/pipeline-execution-and-component-decoupling.md` for full context and architecture vision.

## Problem Statement

### Current Architectural Violation

**ProcessingPurposeAnalyser → SourceCodeAnalyser** (CRITICAL)
- **Location:** `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/`
- **Issue:** Direct imports of SourceCodeAnalyser's Pydantic models
- **Impact:** Forces mandatory dependency chain, breaks analyser independence

### Specific Coupling Points

**1. Package-level dependency:**
```toml
# libs/waivern-processing-purpose-analyser/pyproject.toml:12
dependencies = [
    "waivern-source-code-analyser",  # ← HARDCODED DEPENDENCY
]
```

**2. Direct imports in source code:**
```python
# analyser.py:18
from waivern_source_code_analyser.schemas import SourceCodeDataModel

# source_code_schema_input_handler.py:9-12
from waivern_source_code_analyser.schemas import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
)

# schema_readers/source_code_1_0_0.py:6
from waivern_source_code_analyser.schemas import SourceCodeDataModel
```

**3. Type-safe field access:**
```python
# source_code_schema_input_handler.py:50-66
def analyse_source_code_data(self, data: SourceCodeDataModel) -> list[Finding]:
    for file_data in data.data:  # ← Assumes typed model structure
        file_path = file_data.file_path
        raw_content = file_data.raw_content
        imports = file_data.imports
        functions = file_data.functions
        classes = file_data.classes
```

**4. Test coupling:**
```python
# tests/test_analyser.py:22
from waivern_source_code_analyser.schemas import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    # ... etc
)

# tests/conftest.py:4
from waivern_source_code_analyser import register_schemas
```

### Why This Is a Problem

1. **Breaks plugin architecture** - Components should communicate only through schema contracts, not typed models
2. **Creates cascading dependencies** - Changes to SourceCodeAnalyser's models break ProcessingPurposeAnalyser
3. **Prevents independent evolution** - Can't version or modify schemas without coordinating both packages
4. **Violates framework principle** - Message objects already validate against JSON schemas; typed models are redundant

### Root Cause

**Misunderstanding of schema validation responsibilities:**
- **Message object** validates data against JSON schema (wire format contract)
- **Typed models** are internal implementation details of schema producers/consumers
- **Schema readers** should transform wire format → dict, not wire format → typed model

The ProcessingPurposeAnalyser incorrectly uses SourceCodeAnalyser's **internal typed models** instead of trusting the **schema contract** that Message already validates.

## Solution Overview

Transform ProcessingPurposeAnalyser to use dictionary-based schema handling:

**Before (Current):**
```python
from waivern_source_code_analyser.schemas import SourceCodeDataModel

def analyse_source_code_data(self, data: SourceCodeDataModel) -> list[Finding]:
    for file_data in data.data:
        self._analyse_raw_content(file_data.raw_content)
```

**After (Dict-based):**
```python
# No imports from waivern-source-code-analyser

def analyse_source_code_data(self, data: dict) -> list[Finding]:
    for file_data in data["data"]:
        self._analyse_raw_content(file_data["raw_content"])
```

### Key Benefits

✅ **Eliminates hardcoded dependency** - ProcessingPurposeAnalyser depends only on waivern-core
✅ **Schema contract-driven** - Relies on JSON schema validation provided by Message
✅ **Independent evolution** - Components can evolve independently as long as schema contract maintained
✅ **True plugin architecture** - No cross-component imports except waivern-core
✅ **Cleaner architecture** - Components communicate through data contracts, not code contracts

## Implementation Plan

This phase consists of 5 atomic steps, each following TDD methodology (RED-GREEN-REFACTOR).

### Step 13: Update SourceCodeSchemaInputHandler to Use Dict

**Status:** 📋 Planned
**File:** `docs/development/active/phase_04_steps/step_13_update_source_code_handler_to_dict.md`

**Objectives:**
- Change `analyse_source_code_data()` signature from `SourceCodeDataModel` to `dict`
- Replace all typed field access with dict key access
- Maintain exact same functionality and error handling
- Update all unit tests to use dict-based fixtures

**Key changes:**
1. Update method signature: `def analyse_source_code_data(self, data: dict) -> list[Finding]:`
2. Replace `data.data` with `data["data"]`
3. Replace `file_data.file_path` with `file_data["file_path"]`
4. Replace `file_data.raw_content` with `file_data["raw_content"]`
5. Replace `file_data.imports` with `file_data.get("imports", [])`
6. Replace `file_data.functions` with `file_data.get("functions", [])`
7. Replace `file_data.classes` with `file_data.get("classes", [])`

**Testing strategy:**
- Convert all test fixtures from typed models to plain dicts
- Verify pattern matching still works correctly
- Verify evidence creation unchanged
- Verify metadata structure preserved

**Quality checks:**
- All 633 lines of handler tests must pass
- Type checking must pass (dict typing)
- No functional regressions

---

### Step 14: Update Schema Reader to Return Dict

**Status:** 📋 Planned
**File:** `docs/development/active/phase_04_steps/step_14_update_schema_reader_to_dict.md`

**Objectives:**
- Change `SourceCode_1_0_0_Reader.read()` to return dict instead of typed model
- Remove import of SourceCodeDataModel
- Maintain schema validation (still return SchemaData wrapper)
- Update tests to verify dict structure

**Key changes:**
1. Change return type: `def read(self, message: Message) -> SchemaData[dict]:`
2. Remove: `from waivern_source_code_analyser.schemas import SourceCodeDataModel`
3. Return: `SchemaData(schema=..., data=message.data)` (dict, not model)
4. Remove any Pydantic model validation (Message already validates)

**Testing strategy:**
- Verify reader returns dict with correct structure
- Verify no Pydantic validation occurs in reader
- Verify reader relies on Message's schema validation
- Test with valid and invalid data (should rely on Message validation)

**Quality checks:**
- Reader tests pass
- Type checking passes
- Integration tests still work (next step verifies)

---

### Step 15: Update Main Analyser to Handle Dict

**Status:** 📋 Planned
**File:** `docs/development/active/phase_04_steps/step_15_update_analyser_to_dict.md`

**Objectives:**
- Update `_process_source_code_data()` to work with dict from reader
- Remove import of SourceCodeDataModel from analyser.py
- Verify end-to-end flow works with dict-based processing
- Update integration tests

**Key changes:**
1. Update `_process_source_code_data()` signature if needed
2. Remove: `from waivern_source_code_analyser.schemas import SourceCodeDataModel`
3. Pass dict to handler instead of typed model
4. Verify Message validation catches schema violations

**Testing strategy:**
- Test full pipeline: Message → Reader → Analyser → Handler → Findings
- Verify schema validation still works (Message level)
- Test with invalid source code schema (should fail at Message validation)
- Test with valid data (should produce identical findings)

**Quality checks:**
- All analyser integration tests pass (TestProcessingPurposeAnalyserSourceCodeProcessing)
- End-to-end functionality preserved
- Type checking passes

---

### Step 16: Remove Package Dependency

**Status:** 📋 Planned
**File:** `docs/development/active/phase_04_steps/step_16_remove_package_dependency.md`

**Objectives:**
- Remove `waivern-source-code-analyser` from dependencies in pyproject.toml
- Update test fixtures to use plain dicts
- Remove schema registration import from conftest.py
- Update imports throughout test suite

**Key changes:**
1. Edit `pyproject.toml`: Remove `"waivern-source-code-analyser"` from dependencies
2. Edit `tests/conftest.py`: Remove `from waivern_source_code_analyser import register_schemas`
3. Update all test files to remove SourceCodeAnalyser imports
4. Ensure source code schema still available (registered by waivern-core or test setup)

**Testing strategy:**
- Run `uv sync` to update dependencies
- Verify all tests still pass without the dependency
- Verify no import errors in package or tests
- Verify schema registry still finds source_code schema

**Quality checks:**
- `uv run pytest` passes for processing-purpose-analyser package
- Full workspace test suite passes (882 tests)
- No import errors
- Type checking passes

---

### Step 17: Update Documentation and Examples

**Status:** 📋 Planned
**File:** `docs/development/active/phase_04_steps/step_17_update_documentation.md`

**Objectives:**
- Update README.md to reflect dict-based schema handling
- Add migration notes explaining the architectural change
- Update inline documentation and docstrings
- Document schema contract reliance

**Key changes:**
1. Update `libs/waivern-processing-purpose-analyser/README.md`:
   - Explain dict-based schema handling approach
   - Document reliance on Message validation
   - Add example showing source_code schema usage
2. Update docstrings in source_code_schema_input_handler.py
3. Update docstrings in schema_readers/source_code_1_0_0.py
4. Add architectural notes about schema contract vs typed models

**Documentation sections to add:**
- **Schema Handling:** Explain how analyser uses dict-based data
- **Schema Validation:** Clarify Message object validates against JSON schema
- **No Direct Dependencies:** Highlight independence from SourceCodeAnalyser package
- **Testing with Schemas:** Show how to create test fixtures using dicts

**Quality checks:**
- Documentation accurate and complete
- Examples reflect current implementation
- No references to old typed model approach
- Architectural principles clearly explained

---

## Testing Strategy

### Unit Tests

**Per-step testing:**
- Step 13: Handler unit tests with dict fixtures (test_source_code_schema_input_handler.py)
- Step 14: Reader unit tests with dict return type (schema_readers/test_source_code_1_0_0.py)
- Step 15: Analyser integration tests with dict flow (test_analyser.py)
- Step 16: Full test suite after dependency removal
- Step 17: Documentation examples tested

### Integration Tests

**End-to-end pipeline testing:**
- FilesystemConnector → SourceCodeAnalyser → ProcessingPurposeAnalyser
- Verify schema validation at Message boundaries
- Test with valid source code data (should succeed)
- Test with invalid source code data (should fail at schema validation)
- Compare findings output before/after refactoring (should be identical)

### Regression Testing

**Verify no functionality lost:**
- All pattern matching rules still work
- Evidence extraction unchanged
- Metadata creation preserved
- LLM validation integration unaffected
- Categorical data fields (service_category, collection_type, data_source) still populated

### Test Coverage Goals

- Maintain 100% coverage of source_code_schema_input_handler.py
- Maintain existing test count (882+ tests)
- All quality checks pass (lint, format, type check)
- Zero type errors in strict mode

## Success Criteria

### Functional Requirements

- ✅ ProcessingPurposeAnalyser processes source_code schema using dict-based data
- ✅ Schema validation relies on Message object (no Pydantic models in reader)
- ✅ All pattern matching functionality preserved
- ✅ Evidence extraction unchanged
- ✅ Metadata creation identical to before
- ✅ Integration with SourceCodeAnalyser pipeline works end-to-end

### Architectural Requirements

- ✅ No imports from waivern-source-code-analyser package
- ✅ No dependency on waivern-source-code-analyser in pyproject.toml
- ✅ ProcessingPurposeAnalyser depends only on:
  - waivern-core (base abstractions)
  - waivern-rulesets (shared rulesets)
  - waivern-analysers-shared (shared utilities)
  - waivern-llm (LLM validation)
- ✅ Components communicate only through schema contracts
- ✅ True plugin architecture achieved

### Quality Requirements

- ✅ All tests pass (882+ tests)
- ✅ Type checking passes (strict mode, 0 errors)
- ✅ Linting passes
- ✅ Formatting passes
- ✅ No regressions in functionality
- ✅ Documentation updated and accurate

### Validation Checklist

**Before starting:**
- [ ] Phase 3 complete (SourceCodeAnalyser refactoring done)
- [ ] All Phase 3 tests passing
- [ ] Understanding of dict-based schema handling approach

**After each step:**
- [ ] Step-specific tests pass
- [ ] `./scripts/dev-checks.sh` passes for processing-purpose-analyser package
- [ ] No regressions in existing functionality
- [ ] Git commit with conventional commit message

**After Phase 4 complete:**
- [ ] Full workspace test suite passes
- [ ] No hardcoded cross-component dependencies remain
- [ ] ProcessingPurposeAnalyser independently installable
- [ ] Integration tests pass (requires API keys)
- [ ] Documentation reflects architectural changes

## Risks and Mitigation

### Risk 1: Schema Structure Mismatches

**Impact:** High
**Likelihood:** Medium

**Issue:**
Dict-based access assumes schema structure. If source_code schema changes, dict keys might not exist.

**Mitigation:**
1. Use `.get()` for optional fields (imports, functions, classes)
2. Add defensive checks for required fields
3. Rely on Message validation to catch schema violations early
4. Comprehensive tests with varied source code structures
5. Integration tests verify schema compatibility

### Risk 2: Type Safety Loss

**Impact:** Medium
**Likelihood:** Low

**Issue:**
Replacing typed models with dicts loses compile-time type checking.

**Mitigation:**
1. Use TypedDict annotations for dict structures
2. Comprehensive runtime tests for all code paths
3. Schema validation at Message boundary catches invalid data
4. Type hints on dict parameters: `data: dict[str, Any]`
5. Extensive test coverage compensates for type safety loss

**Trade-off accepted:** Runtime schema validation + tests > compile-time type checking with hardcoded dependencies

### Risk 3: Test Coverage Gaps

**Impact:** High
**Likelihood:** Low

**Issue:**
Converting typed model tests to dict tests might miss edge cases.

**Mitigation:**
1. Convert existing tests one-to-one (same assertions, different fixtures)
2. Add new tests for dict key access patterns
3. Test with missing optional fields
4. Test with invalid data types (should fail at Message validation)
5. Compare findings output before/after (should be identical)

### Risk 4: Performance Degradation

**Impact:** Low
**Likelihood:** Very Low

**Issue:**
Dict access might be slower than attribute access on typed models.

**Mitigation:**
1. Negligible performance difference for dict vs model access
2. Most time spent in pattern matching, not data access
3. Performance tests if needed (not expected to be an issue)

## Implementation Workflow

### Development Process

**For each step (13-17):**

1. **Create step document** with detailed task breakdown
2. **Use work-on skill** for TDD implementation (RED-GREEN-REFACTOR)
3. **Run dev-checks** after each test passes: `./scripts/dev-checks.sh`
4. **Use refactor skill** if code smells detected
5. **Git commit** with conventional commit message
6. **Update step document** with completion notes

### Quality Gates

**After each step:**
- ✅ All step-specific tests pass
- ✅ Package dev-checks pass
- ✅ No type errors (strict mode)
- ✅ No linting errors
- ✅ No functional regressions

**After Phase 4 complete:**
- ✅ Full workspace test suite passes (882+ tests)
- ✅ Integration tests pass (requires API keys)
- ✅ Documentation updated
- ✅ Ready for PR and merge

### Git Workflow

**Branch strategy:**
```bash
git checkout -b refactor/phase-4-remove-processing-purpose-schema-coupling
```

**Commit strategy:**
- One commit per atomic step
- Conventional commit messages
- Clear commit descriptions

**Example commits:**
```
refactor(processing-purpose): update handler to dict-based schema handling

- Change analyse_source_code_data to accept dict instead of typed model
- Replace typed field access with dict key access
- Update all handler tests to use dict fixtures
- Maintain identical functionality and error handling

Refs: #<issue_number>
```

## Dependencies

### Prerequisites

- ✅ Phase 3 complete (SourceCodeAnalyser is pure analyser)
- ✅ Pipeline execution working (Phases 1-2)
- ✅ SourceCodeAnalyser produces source_code schema v1.0.0
- ✅ ProcessingPurposeAnalyser accepts source_code schema v1.0.0

### No External Dependencies

This phase is self-contained:
- No new packages required
- No API changes needed
- No schema changes needed
- Only internal refactoring

## Future Enhancements (Out of Scope)

**Explicitly deferred:**
- TypedDict annotations for better type hints (nice to have, not blocking)
- Schema version compatibility logic (semantic versioning)
- Automatic schema conversion utilities
- Schema evolution testing framework
- Performance optimization for dict access patterns

These can be added incrementally without changing core architecture.

## References

### Parent Documentation

- **Main Task:** `docs/development/active/pipeline-execution-and-component-decoupling.md`
- **WCF Core Concepts:** `docs/core-concepts/wcf-core-components.md`
- **Phase 3 Step Documents:** `docs/development/completed/pipeline-execution-and-component-decoupling/step_07-12_*.md`

### Code Locations

**Source code:**
- `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/analyser.py`
- `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/source_code_schema_input_handler.py`
- `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/schema_readers/source_code_1_0_0.py`

**Tests:**
- `libs/waivern-processing-purpose-analyser/tests/test_source_code_schema_input_handler.py` (633 lines)
- `libs/waivern-processing-purpose-analyser/tests/test_analyser.py` (1121 lines)
- `libs/waivern-processing-purpose-analyser/tests/schema_readers/test_source_code_1_0_0.py` (54 lines)

**Configuration:**
- `libs/waivern-processing-purpose-analyser/pyproject.toml` (dependencies)

### Related Issues

- Parent epic: #189 (DAG-based Execution Engine)
- Phase 2: #210 (Pipeline Execution - closed by PR #211)
- Phase 3: #217 (SourceCode Refactor - closed by PR #218)
- Phase 4: TBD (this phase)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-12
**Status:** Ready for implementation
