# Task: Update Entry Points and Package Exports

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** TODO
- **Prerequisites:** Step 9 (SourceCodeAnalyserFactory created)

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
- [ ] Analyser entry point added to pyproject.toml
- [ ] Connector entry point maintained for backward compatibility
- [ ] New classes exported in __init__.py
- [ ] __all__ list updated
- [ ] Both components discoverable by WCT

**Quality:**
- [ ] Package installs successfully
- [ ] No import errors
- [ ] Entry points resolve correctly
- [ ] Documentation updated

**Code Quality:**
- [ ] Entry point names follow conventions
- [ ] Exports are explicit (__all__)
- [ ] Module docstring updated
- [ ] Deprecation notices added for connector

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
