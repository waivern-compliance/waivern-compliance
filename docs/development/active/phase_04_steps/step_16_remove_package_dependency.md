# Task: Remove Package Dependency

- **Phase:** 4 - Fix ProcessingPurposeAnalyser Schema Coupling
- **Status:** TODO
- **Prerequisites:** Steps 13-15 complete (Handler, Reader, and Analyser use dict)
- **Step:** 16 of 17

## Context

This is part of removing hardcoded dependencies on SourceCodeAnalyser's typed Pydantic models. Steps 13-15 transformed all code to use dict-based data. Now we can remove the package dependency entirely.

**See:** the parent implementation plan (`docs/development/active/phase_04_fix_processing_purpose_analyser_schema_coupling.md`) for full context.

## Purpose

Remove `waivern-source-code-analyser` from ProcessingPurposeAnalyser's dependencies. Update test fixtures and configuration to work without the dependency. Verify the package is truly independent.

## Problem

Package still declares dependency on SourceCodeAnalyser:

**Location:** `libs/waivern-processing-purpose-analyser/pyproject.toml`

**Current dependency (line 12):**
```toml
dependencies = [
    "waivern-core",
    "waivern-rulesets",
    "waivern-analysers-shared",
    "waivern-llm",
    "waivern-source-code-analyser",  # ← REMOVE THIS
]
```

**Test configuration dependency:**
```python
# tests/conftest.py:4
from waivern_source_code_analyser import register_schemas
```

**Issues:**
1. Hardcoded package dependency prevents independent installation
2. Test configuration imports from SourceCodeAnalyser
3. Creates circular dependency potential
4. Violates plugin architecture principle

## Solution

Remove dependency and update test configuration:

**Changes needed:**
1. Remove `waivern-source-code-analyser` from dependencies in pyproject.toml
2. Update test conftest.py to remove schema registration import
3. Ensure source_code schema still available for tests
4. Run `uv sync` to update lock file
5. Verify all tests pass without dependency

## Implementation

### Files to Modify

**1. Package configuration:**
`libs/waivern-processing-purpose-analyser/pyproject.toml`

**2. Test configuration:**
`libs/waivern-processing-purpose-analyser/tests/conftest.py`

### Code Changes Required

#### 1. Update pyproject.toml

**Location:** Line 12 in dependencies list

**Before:**
```toml
dependencies = [
    "waivern-core",
    "waivern-rulesets",
    "waivern-analysers-shared",
    "waivern-llm",
    "waivern-source-code-analyser",
]
```

**After:**
```toml
dependencies = [
    "waivern-core",
    "waivern-rulesets",
    "waivern-analysers-shared",
    "waivern-llm",
]
```

**Rationale:**
- ProcessingPurposeAnalyser now depends only on:
  - `waivern-core` - Base abstractions (required)
  - `waivern-rulesets` - Shared rulesets (required)
  - `waivern-analysers-shared` - Shared utilities (required)
  - `waivern-llm` - LLM validation (required)
- No direct dependency on SourceCodeAnalyser
- Communication via schema contract only

#### 2. Update tests/conftest.py

**Current import (line 4):**
```python
from waivern_source_code_analyser import register_schemas
```

**Option A: Remove if schema registered elsewhere**
If source_code schema is registered by waivern-core or test setup:
```python
# Remove the import entirely
```

**Option B: Register schema manually in tests**
If tests need source_code schema:
```python
# In conftest.py or specific test files that need it
import pytest
from waivern_core import SchemaRegistry, Schema

@pytest.fixture(autouse=True)
def register_source_code_schema():
    """Register source_code schema for tests that need it."""
    # Note: This is a workaround for testing.
    # In production, schema comes from SourceCodeAnalyser package output.
    schema = Schema(name="source_code", version="1.0.0")
    SchemaRegistry.register_output_schema("source_code_analyser", schema)
    yield
    # Cleanup not needed due to isolated_registry fixture
```

**Option C: Use test data files**
Copy minimal source_code schema JSON to test fixtures:
```python
# tests/fixtures/source_code_schema.json
# Contains minimal source_code schema definition for testing
```

**Recommended approach:** Option A if possible, Option B if tests need schema registration.

**Investigation needed:**
1. Check if source_code schema is registered elsewhere
2. Determine if tests actually need schema registration
3. Verify Message validation doesn't require registry for tests
4. Consider whether tests should use real schema or mock

#### 3. Verify No Other References

**Search entire package for:**
```bash
grep -r "waivern.source.code.analyser" libs/waivern-processing-purpose-analyser/
grep -r "source_code_analyser" libs/waivern-processing-purpose-analyser/
grep -r "SourceCodeAnalyser" libs/waivern-processing-purpose-analyser/
grep -r "from waivern_source_code" libs/waivern-processing-purpose-analyser/
```

**Expected result:** No references should remain (except in comments/docs)

### Dependency Synchronization

#### 1. Update Lock File

```bash
cd libs/waivern-processing-purpose-analyser
uv sync
```

**Expected behaviour:**
- Lock file updated to remove waivern-source-code-analyser
- Dependencies resolved successfully
- No conflicts reported

#### 2. Verify Installation

```bash
# Install package in isolation
cd libs/waivern-processing-purpose-analyser
uv pip install -e .
```

**Expected behaviour:**
- Package installs successfully
- No errors about missing waivern-source-code-analyser
- Only declared dependencies installed

#### 3. Run Tests

```bash
cd libs/waivern-processing-purpose-analyser
uv run pytest
```

**Expected behaviour:**
- All tests pass
- No import errors
- No missing dependency errors

## Testing

### Testing Strategy

**Verification approach:**
1. Remove dependency from pyproject.toml
2. Run `uv sync` to update dependencies
3. Run full test suite
4. Fix any import errors or schema registration issues
5. Verify package installs independently
6. Run dev-checks to ensure quality

### Test Scenarios to Verify

#### 1. Package installs without SourceCodeAnalyser

**Setup:**
- Remove dependency from pyproject.toml
- Run `uv sync`
- Try to install package

**Expected behaviour:**
- Installation succeeds
- No dependency resolution errors
- Package functional without SourceCodeAnalyser

#### 2. Tests run without SourceCodeAnalyser

**Setup:**
- Remove dependency
- Update test configuration
- Run test suite

**Expected behaviour:**
- All tests pass
- No import errors
- Tests using source_code schema still work

#### 3. Source code schema tests work

**Setup:**
- Remove dependency
- Run tests in TestProcessingPurposeAnalyserSourceCodeProcessing

**Expected behaviour:**
- Tests create Messages with source_code schema
- Tests process dict data correctly
- Tests validate findings output

#### 4. No regression in functionality

**Setup:**
- Remove dependency
- Run full test suite

**Expected behaviour:**
- All 882+ tests pass
- No functionality lost
- All pattern matching works
- All evidence extraction works

#### 5. Workspace tests pass

**Setup:**
- Remove dependency
- Run workspace-level tests

**Expected behaviour:**
- Full workspace test suite passes
- No cross-package dependency issues
- Integration tests work (if API keys available)

### Quality Checks

**Must pass before marking step complete:**
- [ ] `waivern-source-code-analyser` removed from pyproject.toml
- [ ] `uv sync` completes successfully
- [ ] Package test suite passes (all 882+ tests)
- [ ] No import errors anywhere in package
- [ ] Type checking passes (basedpyright strict mode)
- [ ] Linting passes (ruff)
- [ ] Formatting passes (ruff format)
- [ ] `./scripts/dev-checks.sh` passes for processing-purpose-analyser
- [ ] Workspace test suite passes
- [ ] Package can be installed independently

## Success Criteria

**Functional:**
- [x] `waivern-source-code-analyser` removed from dependencies
- [x] No imports from waivern-source-code-analyser in source code
- [x] No imports from waivern-source-code-analyser in tests (except necessary fixtures)
- [x] All tests pass without the dependency
- [x] Package installs independently

**Dependencies:**
- [x] ProcessingPurposeAnalyser depends only on:
  - waivern-core (base abstractions)
  - waivern-rulesets (shared rulesets)
  - waivern-analysers-shared (shared utilities)
  - waivern-llm (LLM validation)
- [x] No circular dependencies
- [x] Dependency graph clean

**Testing:**
- [x] Full package test suite passes
- [x] Workspace test suite passes
- [x] No test failures related to missing dependency
- [x] Schema-based tests still work

**Quality:**
- [x] Type checking passes
- [x] Linting passes
- [x] Formatting passes
- [x] `./scripts/dev-checks.sh` passes
- [x] `uv sync` succeeds

## Implementation Notes

### Design Considerations

**Schema availability in tests:**
- Tests create Messages with source_code schema
- Message validates against JSON schema file
- Schema file should be available from schema registry
- May need to register schema manually for tests
- Consider copying minimal schema to test fixtures

**Dependency principle:**
- Analysers should depend only on waivern-core + shared utilities
- Communication via schema contracts (JSON files)
- No code dependencies between analysers
- True plugin architecture

### Verification Checklist

**Before considering step complete:**
1. ✅ Dependency removed from pyproject.toml
2. ✅ `uv sync` successful
3. ✅ No imports from waivern-source-code-analyser
4. ✅ All package tests pass
5. ✅ All workspace tests pass
6. ✅ Dev-checks pass
7. ✅ Package can be installed independently
8. ✅ No schema registration errors

### Potential Issues and Solutions

**Issue 1: Schema not found in tests**
- **Symptom:** Tests fail with schema not registered
- **Solution:** Register schema manually in conftest.py or test fixtures
- **Alternative:** Copy source_code schema JSON to test directory

**Issue 2: Message validation fails**
- **Symptom:** Tests fail when creating Messages with source_code schema
- **Solution:** Ensure schema JSON file available in search path
- **Alternative:** Use schema discovery from installed packages

**Issue 3: Import errors in tests**
- **Symptom:** Tests import from waivern-source-code-analyser
- **Solution:** Update test fixtures to use plain dicts (should be done in Steps 13-15)
- **Verification:** Run grep to find remaining imports

### Refactoring Opportunities

**After GREEN state:**
1. Document independent installation capability
2. Update README with dependency information
3. Add note about schema contract communication
4. Consider adding example of using source_code schema without dependency

## Next Steps

After this step is complete:
- **Step 17:** Update Documentation and Examples
- Update README.md with dict-based schema handling
- Document reliance on Message validation
- Add migration notes explaining architectural change
- Document schema contract reliance
