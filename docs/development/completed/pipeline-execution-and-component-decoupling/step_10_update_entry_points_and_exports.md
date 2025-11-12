# Task: Update Entry Points and Package Exports

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** DONE
- **Prerequisites:** Step 9 (SourceCodeAnalyserFactory created)
- **GitHub Issue:** #215
- **Completed:** 2025-11-12

## Context

This is part of refactoring SourceCodeConnector into a pure transformer analyser. The previous steps created the analyser infrastructure.

**See:** the parent implementation plan for full context.

## Purpose

Update package entry points and exports to register SourceCodeAnalyser while maintaining backward compatibility with existing SourceCodeConnector during transition.

## Problem

WCF discovers components through entry points in `pyproject.toml`:
- `[project.entry-points."waivern.connectors"]` for connectors
- `[project.entry-points."waivern.analysers"]` for analysers

The package currently only exports connector entry point. Need to add analyser entry point while keeping connector temporarily for backward compatibility.

## Solution

Update package configuration to expose both connector and analyser:
- Add analyser entry point in pyproject.toml
- Export new classes in `__init__.py`
- Keep existing connector exports during transition
- Update documentation strings

## Decisions Made

1. **Maintain backward compatibility** - Keep connector entry point temporarily
2. **Add analyser entry point** - New entry for source_code_analyser
3. **Export new classes** - SourceCodeAnalyser, SourceCodeAnalyserConfig, SourceCodeAnalyserFactory
4. **Keep existing exports** - Don't break imports during transition
5. **Deprecation strategy** - Add deprecation notices in docstrings

## Implementation

### Files to Modify

1. `libs/waivern-source-code/pyproject.toml`
2. `libs/waivern-source-code/src/waivern_source_code/__init__.py`

### Changes Required

#### 1. Update pyproject.toml

**Add analyser entry point:**
```
[project.entry-points."waivern.analysers"]
source_code = "waivern_source_code:SourceCodeAnalyserFactory"
```

**Keep existing connector entry point:**
```
[project.entry-points."waivern.connectors"]
source_code = "waivern_source_code:SourceCodeConnectorFactory"
```

**Note:** Both entry points can coexist during transition period.

#### 2. Update __init__.py

**Add new imports:**
```
Import SourceCodeAnalyser, SourceCodeAnalyserConfig, SourceCodeAnalyserFactory
```

**Add to __all__ list:**
```
Add new class names to __all__ for explicit exports
```

**Update docstring:**
```
Update module docstring to mention both connector and analyser
Add deprecation notice for connector
```

## Testing

### Testing Strategy

Test through **public API** - verify components discoverable by executor.

Use `wct ls-connectors` and `wct ls-analysers` commands to verify registration.

### Test Scenarios

#### 1. Analyser discoverable via entry point

**Setup:**
- Install package with updated entry points
- Run `wct ls-analysers`

**Expected behaviour:**
- "source_code" appears in analyser list
- Factory can be loaded

#### 2. Connector still discoverable (backward compatibility)

**Setup:**
- Install package with updated entry points
- Run `wct ls-connectors`

**Expected behaviour:**
- "source_code" still appears in connector list
- Existing runbooks using connector don't break

#### 3. Both components registered in registry

**Setup:**
- Import package
- Query component registry

**Expected behaviour:**
- SourceCodeConnectorFactory registered
- SourceCodeAnalyserFactory registered
- No naming conflicts

#### 4. Imports work correctly

**Setup:**
- Try importing new classes: `from waivern_source_code import SourceCodeAnalyser`

**Expected behaviour:**
- All imports succeed
- No import errors

#### 5. Schema registration still works

**Setup:**
- Call register_schemas()
- Verify source_code schema available

**Expected behaviour:**
- Schema registration unchanged
- Both connector and analyser can use schemas

## Success Criteria

**Functional:**
- [x] Analyser entry point added to pyproject.toml
- [x] Connector entry point maintained for backward compatibility
- [x] New classes exported in __init__.py
- [x] __all__ list updated
- [x] Both components discoverable by WCT

**Quality:**
- [x] Package installs successfully
- [x] No import errors
- [x] Entry points resolve correctly
- [x] Documentation updated

**Code Quality:**
- [x] Entry point names follow conventions
- [x] Exports are explicit (__all__)
- [x] Module docstring updated (analyser-focused)
- [x] No deprecation notices added (connector removed in later step)

## Implementation Notes

**Design considerations:**
- Backward compatibility critical during transition
- Both entry points coexist temporarily
- Connector will be removed in Phase 4 (separate task)
- Entry point names must be unique within namespace

**Entry point naming:**
- Connector: `source_code` (existing)
- Analyser: `source_code` (new, different namespace)
- No conflicts because different entry point groups

**Deprecation strategy:**
- Add docstring deprecation notices
- Don't remove connector yet
- Phase 4 will handle complete deprecation
- Give users time to migrate runbooks

**Future work:**
- Phase 4: Remove connector entry point
- Phase 4: Remove connector classes
- Phase 4: Update all example runbooks

## Completion Notes

### Implementation Summary

This step was **largely completed in Step 9** when creating the factory. Only minor documentation updates were required.

**What Was Already Done (Step 9):**
- ✓ Added `[project.entry-points."waivern.analysers"]` in pyproject.toml
- ✓ Kept `[project.entry-points."waivern.connectors"]` for backward compatibility
- ✓ Exported SourceCodeAnalyser, SourceCodeAnalyserConfig, SourceCodeAnalyserFactory in __init__.py
- ✓ Updated __all__ list with all new exports
- ✓ Both components registered and discoverable

**What Was Done (Step 10):**
- Updated module docstring from "Source code connector for WCF" to analyser-focused description
- Emphasized pipeline execution pattern: `FilesystemConnector → SourceCodeAnalyser → ProcessingPurposeAnalyser`
- Did NOT add deprecation notices (connector will be removed in later step)

### Files Modified

**Modified:**
- `libs/waivern-source-code/src/waivern_source_code/__init__.py` - Updated module docstring only

### Verification Results

**Entry Point Discovery:**
```bash
$ uv run wct ls-analysers | grep source_code
│ source_code_analyser  │ Factory for creating SourceCodeAnalyser instances │

$ uv run wct ls-connectors | grep source_code
│ source_code_connector │ Factory for creating SourceCodeConnector instances │
```

Both components discoverable ✓

**Test Results:**
- Total: 922 tests passed
- Skipped: 7 tests (external dependencies)
- Deselected: 14 tests (integration tests)
- Duration: 9.96s

**Quality Checks:**
- ✓ Formatting passed (ruff format)
- ✓ Linting passed (ruff check)
- ✓ Type checking passed (basedpyright strict mode, 0 errors, 0 warnings)

### Design Decisions

1. **No Deprecation Notices:** Per project direction, connector code will be removed in a later step, so no deprecation notices were added
2. **Analyser-Focused Documentation:** Updated module docstring to emphasize analyser (the future) over connector (temporary)
3. **Backward Compatibility:** Both entry points coexist until connector removal
4. **Pipeline Pattern:** Documentation emphasizes the recommended pipeline execution model

### Next Steps

**Phase 3 Continuation:**
- Step 11: Create integration tests for the pipeline (skipped if already covered)
- Step 12: Remove SourceCodeConnector code entirely
