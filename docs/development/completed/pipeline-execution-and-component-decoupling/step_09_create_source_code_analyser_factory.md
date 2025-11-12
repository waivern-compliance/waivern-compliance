# Task: Create SourceCodeAnalyserFactory

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** DONE
- **Prerequisites:** Step 8 (SourceCodeAnalyser created)
- **GitHub Issue:** #214
- **Completed:** 2025-11-12

## Context

This is part of refactoring SourceCodeConnector into a pure transformer analyser. The previous steps created the config and analyser class.

**See:** the parent implementation plan for full context.

## Purpose

Create factory for SourceCodeAnalyser following the ComponentFactory pattern used throughout WCF, enabling automatic registration and discovery by the executor.

## Problem

WCF uses a component factory pattern for dependency injection:
- Executor discovers components via entry points
- Factories instantiate components with validated configuration
- Metaclass handles automatic registration

Without a factory, the analyser cannot be discovered or used by WCT.

## Solution

Create `SourceCodeAnalyserFactory` implementing `ComponentFactory[Analyser]`:
- Validate configuration via SourceCodeAnalyserConfig
- Instantiate SourceCodeAnalyser
- Register automatically via metaclass
- Follow existing factory patterns

## Decisions Made

1. **ComponentFactory pattern** - Use existing framework infrastructure
2. **Config validation** - Use SourceCodeAnalyserConfig.from_properties()
3. **Automatic registration** - Metaclass handles registry
4. **Type safety** - Generic type hint ComponentFactory[Analyser]
5. **Entry point** - Register in pyproject.toml under waivern.analysers

## Implementation

### File to Create

`libs/waivern-source-code/src/waivern_source_code/analyser_factory.py`

### Factory Structure

**Pattern to follow:**
```
Look at PersonalDataAnalyserFactory or DataSubjectAnalyserFactory
for reference implementation
```

**Key methods:**

#### 1. get_component_type()

Return the type name for lookup ("source_code_analyser").

#### 2. create()

Create SourceCodeAnalyser instance from properties dict.

**Algorithm (pseudo-code):**
```
function create(properties):
    # Validate configuration
    config = SourceCodeAnalyserConfig.from_properties(properties)

    # Create analyser instance
    analyser = SourceCodeAnalyser(config)

    log("Created SourceCodeAnalyser")

    return analyser
```

**Error handling:**
- Configuration errors propagate as ConnectorConfigError
- Let validation errors bubble up to executor

## Testing

### Testing Strategy

Test through **public API** via executor integration. Factory is tested indirectly through analyser usage.

Unit tests for factory focus on configuration handling only.

### Test Scenarios

**File:** `libs/waivern-source-code/tests/test_analyser_factory.py`

#### 1. Valid configuration

**Setup:**
- Call factory.create({"language": "php", "max_file_size": 5242880})

**Expected behaviour:**
- Returns SourceCodeAnalyser instance
- Config fields correctly set

#### 2. Empty configuration (all defaults)

**Setup:**
- Call factory.create({})

**Expected behaviour:**
- Returns SourceCodeAnalyser instance
- Config uses defaults (language=None, max_file_size=10MB)

#### 3. Invalid configuration

**Setup:**
- Call factory.create({"max_file_size": -1})

**Expected behaviour:**
- Raises ConnectorConfigError
- Error message mentions validation issue

#### 4. get_component_type returns correct name

**Setup:**
- Call factory.get_component_type()

**Expected behaviour:**
- Returns "source_code_analyser"

#### 5. Factory registered in component registry

**Setup:**
- Import factory module
- Query component registry

**Expected behaviour:**
- Factory discoverable by type name
- Automatic metaclass registration worked

## Success Criteria

**Functional:**
- [x] SourceCodeAnalyserFactory implements ComponentFactory[Analyser]
- [x] get_component_type() returns "source_code_analyser"
- [x] create() validates configuration via SourceCodeAnalyserConfig
- [x] create() returns SourceCodeAnalyser instance
- [x] Invalid configuration raises ValueError (via config validation)

**Quality:**
- [x] All tests pass (922 passed, 7 skipped)
- [x] Type checking passes (strict mode, 0 errors)
- [x] Linting passes
- [x] Factory follows existing patterns

**Code Quality:**
- [x] Tests verify factory behaviour using ComponentFactoryContractTests
- [x] Error handling consistent with other factories
- [x] No explicit logging needed (simple glue code)
- [x] Minimal code (103 lines including docstrings)

## Implementation Notes

**Design considerations:**
- Factory is simple glue code
- Configuration validation handled by config class
- Component creation is straightforward
- Registry handles discovery automatically

**Pattern consistency:**
- Match PersonalDataAnalyserFactory structure
- Same error handling approach
- Same logging approach
- Same type annotations

**Integration points:**
- Entry point in pyproject.toml: `[project.entry-points."waivern.analysers"]`
- Registry via metaclass (automatic)
- Executor discovery via entry points

## Completion Notes

### What Was Implemented

**Core Implementation:**
- Created `SourceCodeAnalyserFactory` in `libs/waivern-source-code/src/waivern_source_code/analyser_factory.py`
- Implements `ComponentFactory[SourceCodeAnalyser]` with all required methods
- Follows established factory pattern from PersonalDataAnalyserFactory and FilesystemConnectorFactory
- No service dependencies (simpler than analysers with LLM dependencies)

**Test Coverage:**
- Created `libs/waivern-source-code/tests/test_analyser_factory.py` with 6 contract tests
- Inherits from `ComponentFactoryContractTests` for automatic interface compliance testing
- Tests cover: component creation, schema queries, configuration validation, service dependencies
- All tests passing (100% coverage of factory interface)

### Files Modified

1. **Created:**
   - `libs/waivern-source-code/src/waivern_source_code/analyser_factory.py` - Factory implementation (103 lines)
   - `libs/waivern-source-code/tests/test_analyser_factory.py` - Factory tests (57 lines)

2. **Modified:**
   - `libs/waivern-source-code/pyproject.toml` - Added entry point for `waivern.analysers`
   - `libs/waivern-source-code/src/waivern_source_code/__init__.py` - Exported factory, analyser, and config

### Implementation Approach

**Methodology:**
- Followed TDD (RED-GREEN-REFACTOR) strictly
- Created test fixtures first (factory and valid_config)
- Implemented minimal factory to pass contract tests
- No refactoring needed (simple glue code following established pattern)

**Design Decisions:**
1. **No Service Dependencies:** SourceCodeAnalyser has no external dependencies (unlike LLM-based analysers)
2. **Contract Testing:** Used ComponentFactoryContractTests for automatic interface compliance
3. **Configuration Validation:** Delegated to SourceCodeAnalyserConfig.from_properties()
4. **Error Handling:** ValueError propagates from config validation (consistent with framework)

### Test Results

**Package Tests:**
- 6 new factory tests - all passing
- Contract tests verify: create(), can_create(), get_component_name(), get_input_schemas(), get_output_schemas(), get_service_dependencies()

**Full Test Suite:**
- Total: 922 tests passed (6 more than previous step)
- Skipped: 7 tests (external dependencies)
- Deselected: 14 tests (integration tests)
- Duration: 5.59s

**Quality Checks:**
- ✓ Formatting passed (ruff format)
- ✓ Linting passed (ruff check)
- ✓ Type checking passed (basedpyright strict mode, 0 errors, 0 warnings)

### Integration

**Entry Point Registration:**
```toml
[project.entry-points."waivern.analysers"]
source_code = "waivern_source_code:SourceCodeAnalyserFactory"
```

**Package Exports:**
- SourceCodeAnalyser
- SourceCodeAnalyserConfig
- SourceCodeAnalyserFactory

All exported from `waivern_source_code.__init__` for easy import.

### Next Steps

**Phase 3 Continuation:**
- Step 10: Create integration tests for FilesystemConnector → SourceCodeAnalyser pipeline
- Step 11: Update documentation and runbook examples
- Step 12: Deprecate/remove old SourceCodeConnector
