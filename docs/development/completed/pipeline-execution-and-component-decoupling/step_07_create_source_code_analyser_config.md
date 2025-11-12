# Task: Create SourceCodeAnalyserConfig

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** DONE
- **Prerequisites:** Phase 2 complete (pipeline execution working)
- **GitHub Issue:** #212
- **Completed:** 2025-11-12

## Context

This is part of refactoring SourceCodeConnector into a pure transformer analyser that accepts `standard_input` schema and outputs `source_code` schema.

**See:** the parent implementation plan (`docs/development/active/pipeline-execution-and-component-decoupling.md`) for full context.

## Purpose

Create configuration class for SourceCodeAnalyser that focuses on parsing configuration, removing path-related fields that are now handled by FilesystemConnector.

## Problem

Current `SourceCodeConnectorConfig` has dual responsibility:
- File discovery configuration (path, file_patterns, exclude_patterns, max_files)
- Code parsing configuration (language, max_file_size)

When SourceCodeAnalyser becomes a transformer analyser accepting `standard_input`, it only needs parsing configuration since file discovery is handled upstream by FilesystemConnector.

## Solution

Create new `SourceCodeAnalyserConfig` class that:
- Extends `BaseComponentConfiguration`
- Contains only parsing-related configuration
- Removes path, file_patterns, exclude_patterns, max_files fields
- Keeps language and max_file_size fields

## Decisions Made

1. **New config class** - Create separate config to avoid breaking changes during transition
2. **Keep max_file_size** - Analyser still needs to skip processing files that are too large
3. **Keep language** - Allows explicit language override instead of auto-detection
4. **Remove file discovery fields** - FilesystemConnector handles these now
5. **Preserve existing SourceCodeConnectorConfig** - Will be removed later when connector fully deprecated

## Implementation

### File to Create

`libs/waivern-source-code/src/waivern_source_code/analyser_config.py`

### Configuration Fields

**Keep these fields:**
```
language: str | None
  - Description: "Programming language (auto-detected if None)"
  - Default: None
  - Validation: Non-empty string if provided, lowercase

max_file_size: int
  - Description: "Skip files larger than this size in bytes"
  - Default: 10MB (10 * 1024 * 1024)
  - Validation: Must be > 0
```

**Remove these fields (handled by FilesystemConnector):**
- path
- file_patterns
- exclude_patterns
- max_files

### Implementation Approach

The config should follow the same pattern as `SourceCodeConnectorConfig`:
- Use Pydantic Field with descriptions
- Add validators for language and max_file_size
- Implement `from_properties()` classmethod
- Raise `ConnectorConfigError` on validation failures (shared error type)

## Testing

### Testing Strategy

Test through analyser's public API once analyser is created. For now, validate config creation only.

### Test Scenarios

**File:** `libs/waivern-source-code/tests/test_analyser_config.py`

#### 1. Valid config with all fields

**Setup:**
- Create config with language="php" and max_file_size=5MB

**Expected behaviour:**
- Config created successfully
- Fields accessible with correct values

#### 2. Valid config with defaults

**Setup:**
- Create config with empty dict (all defaults)

**Expected behaviour:**
- Config created successfully
- language=None (auto-detect)
- max_file_size=10MB (default)

#### 3. Invalid language (empty string)

**Setup:**
- Create config with language=""

**Expected behaviour:**
- Raises ConnectorConfigError
- Error message mentions language validation

#### 4. Invalid max_file_size (zero or negative)

**Setup:**
- Create config with max_file_size=0 or max_file_size=-1

**Expected behaviour:**
- Raises ConnectorConfigError
- Error message mentions size constraint

#### 5. from_properties() with valid data

**Setup:**
- Call from_properties({"language": "php", "max_file_size": 5242880})

**Expected behaviour:**
- Returns valid config instance
- Values correctly mapped

#### 6. from_properties() with invalid data

**Setup:**
- Call from_properties() with invalid values (e.g., negative size)

**Expected behaviour:**
- Raises ConnectorConfigError
- Clear error message

## Success Criteria

**Functional:**
- [x] SourceCodeAnalyserConfig created with language and max_file_size fields only
- [x] Validation works for language (non-empty, lowercase)
- [x] Validation works for max_file_size (positive integer)
- [x] from_properties() creates config from dict
- [x] from_properties() raises AnalyserConfigError on invalid input

**Quality:**
- [x] All tests pass (9 tests created, 910 total tests passing)
- [x] Type checking passes (strict mode)
- [x] Linting passes
- [x] Docstrings follow project standards

**Code Quality:**
- [x] Tests use from_properties() (public API)
- [x] Config follows existing patterns (PersonalDataAnalyserConfig, etc.)
- [x] No hardcoded values in validation logic
- [x] Clear error messages for validation failures

## Implementation Notes

**Design considerations:**
- Config is simple - only 2 optional fields
- No complex validation logic needed
- Pattern matches other analyser configs in framework
- Error handling consistent with connector config

**Future enhancements:**
- Could add parsing options (e.g., depth limits)
- Could add language-specific parsing flags
- Could add performance tuning options

## Completion Notes

### What Was Implemented

**Core Implementation:**
- Created `SourceCodeAnalyserConfig` in `libs/waivern-source-code/src/waivern_source_code/analyser_config.py`
- Two fields only: `language` (optional) and `max_file_size` (default 10MB)
- Follows Pydantic validation pattern with Field descriptions
- Uses `from_properties()` classmethod for runbook property loading

**Test Coverage:**
- Created `libs/waivern-source-code/tests/test_analyser_config.py` with 9 comprehensive tests
- All tests passing (100% coverage of config behaviour)
- Tests cover valid configs, defaults, validation errors, and edge cases

### Framework Enhancement

**Added AnalyserConfigError Exception:**
- Added `AnalyserConfigError` to `libs/waivern-core/src/waivern_core/errors.py`
- Exported in `waivern_core.__init__.py`
- Creates symmetry with `ConnectorConfigError` in exception hierarchy
- Proper separation: config errors vs. input/processing errors

**Exception Hierarchy:**
```
WaivernError
├── AnalyserError
│   ├── AnalyserConfigError    ← NEW (configuration validation)
│   ├── AnalyserInputError      (invalid input data)
│   └── AnalyserProcessingError (processing failures)
└── ConnectorError
    ├── ConnectorConfigError    (configuration validation)
    └── ConnectorExtractionError (extraction failures)
```

### Refactoring Applied

**Extracted Shared Validation Utility:**
- Created `libs/waivern-source-code/src/waivern_source_code/validators.py`
- Moved language validation logic to `validate_and_normalise_language()` function
- Updated both `analyser_config.py` and `config.py` to use shared validator
- Eliminated code duplication (DRY principle)
- Consistent validation across connector and analyser configs

### Test Results

**Package Tests:**
- 9 new tests in `test_analyser_config.py` - all passing
- Existing source code package tests - all passing

**Full Test Suite:**
- Total: 910 tests passed
- Skipped: 7 tests (expected - require external dependencies)
- Deselected: 14 tests (expected - integration tests)
- Duration: 7.67s

**Quality Checks:**
- ✓ Formatting passed (ruff format)
- ✓ Linting passed (ruff check)
- ✓ Type checking passed (basedpyright strict mode, 0 errors, 0 warnings)

### Technical Debt Created

**Framework Enhancement Opportunity:**
- Created `docs/technical-debt/standardise-config-error-handling.md`
- Documents template method pattern for eliminating boilerplate error handling
- Currently, every config class duplicates error handling in `from_properties()`
- Proposed solution: Add `_get_config_error_class()` abstract method to `BaseComponentConfiguration`
- Priority: LOW (nice to have, not blocking)
- Impact: Reduces ~10 lines to ~2 lines per config class

### Files Modified

**New Files:**
1. `libs/waivern-source-code/src/waivern_source_code/analyser_config.py` - Config class
2. `libs/waivern-source-code/src/waivern_source_code/validators.py` - Shared validation
3. `libs/waivern-source-code/tests/test_analyser_config.py` - Test suite
4. `docs/technical-debt/standardise-config-error-handling.md` - Tech debt document

**Modified Files:**
1. `libs/waivern-core/src/waivern_core/errors.py` - Added AnalyserConfigError
2. `libs/waivern-core/src/waivern_core/__init__.py` - Exported new exception
3. `libs/waivern-source-code/src/waivern_source_code/config.py` - Use shared validator

### Methodology Followed

**TDD (RED-GREEN-REFACTOR):**
1. Created 9 empty test stubs (all with `pass`)
2. Implemented tests one at a time
3. Each test passed immediately (GREEN state)
4. Ran refactor skill after all tests passed
5. Applied refactoring fixes identified

**SOLID Principles:**
- Liskov Substitution: Fixed by using correct error type (AnalyserConfigError)
- DRY Principle: Eliminated duplication through shared validator
- Single Responsibility: Config class focused solely on configuration

### Next Steps

This task is complete. The next step in Phase 3 is:

**Step 8:** Create SourceCodeAnalyser class
- Implement analyser accepting `standard_input` schema
- Transform to `source_code` schema output
- Use new `SourceCodeAnalyserConfig`
- Maintain existing parsing logic from connector
