# Task: Create SourceCodeAnalyserConfig

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** TODO
- **Prerequisites:** Phase 2 complete (pipeline execution working)

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
- [ ] SourceCodeAnalyserConfig created with language and max_file_size fields only
- [ ] Validation works for language (non-empty, lowercase)
- [ ] Validation works for max_file_size (positive integer)
- [ ] from_properties() creates config from dict
- [ ] from_properties() raises ConnectorConfigError on invalid input

**Quality:**
- [ ] All tests pass
- [ ] Type checking passes (strict mode)
- [ ] Linting passes
- [ ] Docstrings follow project standards

**Code Quality:**
- [ ] Tests use from_properties() (public API)
- [ ] Config follows existing patterns (PersonalDataAnalyserConfig, etc.)
- [ ] No hardcoded values in validation logic
- [ ] Clear error messages for validation failures

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
