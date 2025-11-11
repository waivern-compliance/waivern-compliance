# Task: Update Package Dependencies

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** TODO
- **Prerequisites:** Step 11 (pipeline integration tests passing)

## Context

This is the final step of Phase 3, refactoring SourceCodeConnector into a pure transformer analyser. The analyser no longer needs FilesystemConnector as a dependency.

**See:** the parent implementation plan for full context.

## Purpose

Update `pyproject.toml` dependencies to reflect that SourceCodeAnalyser is independent - remove waivern-filesystem from required dependencies since analyser doesn't perform file I/O.

## Problem

Current dependency structure:
```
waivern-source-code depends on:
  - waivern-core (needed)
  - waivern-filesystem (only needed by connector, NOT analyser)
  - pydantic (needed)
```

This creates unnecessary coupling:
- Users who only want SourceCodeAnalyser must install waivern-filesystem
- Breaks clean architecture (analyser shouldn't depend on connector)
- Violates dependency inversion principle

## Solution

Two options considered:

**Option A: Remove waivern-filesystem entirely**
- SourceCodeConnector becomes deprecated
- Clean break, but breaks backward compatibility immediately

**Option B: Make waivern-filesystem optional**
- Move to optional-dependencies group
- Connector requires it, analyser doesn't
- Maintains backward compatibility

## Decisions Made

1. **Keep waivern-filesystem as required dependency temporarily** - Maintain backward compatibility during transition
2. **Phase 4 will remove it** - When connector fully deprecated
3. **Document the dependency reason** - Add comment in pyproject.toml
4. **Add deprecation notice** - Update README to guide users toward analyser

**Rationale:** Breaking dependencies immediately would break existing users. Phase 3 focuses on creating the analyser; Phase 4 will handle deprecation and removal.

## Implementation

### File to Modify

`libs/waivern-source-code/pyproject.toml`

### Changes Required

#### 1. Add dependency documentation comment

Add comment explaining waivern-filesystem is only needed by connector (deprecated):

```toml
dependencies = [
    "waivern-core",
    "waivern-filesystem",  # Only needed by SourceCodeConnector (deprecated). Will be removed in Phase 4.
    "pydantic>=2.11.5",
]
```

#### 2. Update package description

Update description to mention both connector and analyser:

```toml
description = "Source code connector and analyser for WCF"
```

#### 3. Verify other dependencies

Ensure all required dependencies present:
- waivern-core: Required (base classes)
- pydantic: Required (config validation)
- tree-sitter packages: Optional (correct)

## Testing

### Testing Strategy

Verify package installation and imports work correctly.

### Test Scenarios

#### 1. Clean install in new virtual environment

**Setup:**
- Create new virtual environment
- Install waivern-source-code package
- Try importing both connector and analyser

**Expected behaviour:**
- Package installs successfully
- All dependencies resolved
- Imports work for both components

#### 2. Analyser works without using filesystem

**Setup:**
- Import and use SourceCodeAnalyser
- Don't import or use FilesystemConnector
- Create Message with standard_input manually

**Expected behaviour:**
- Analyser works correctly
- No runtime errors
- waivern-filesystem imported by connector only (not by analyser code)

#### 3. Connector still works (backward compatibility)

**Setup:**
- Import and use SourceCodeConnector
- Execute extraction

**Expected behaviour:**
- Connector works as before
- FilesystemConnector available
- No regressions

#### 4. Build and install wheel

**Setup:**
- Build package: `uv build`
- Install wheel in clean environment

**Expected behaviour:**
- Build succeeds
- Wheel installs correctly
- Dependencies installed automatically

## Success Criteria

**Functional:**
- [ ] Package installs successfully
- [ ] SourceCodeAnalyser works without filesystem dependency in code
- [ ] SourceCodeConnector still works (backward compatibility)
- [ ] Dependencies documented with comments
- [ ] Package description updated

**Quality:**
- [ ] All tests pass after dependency changes
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Package builds successfully

**Code Quality:**
- [ ] Dependencies have clear justifications
- [ ] Deprecation notices in place
- [ ] README updated with migration guidance
- [ ] No unused dependencies

## Implementation Notes

**Design considerations:**
- Backward compatibility prioritized during transition
- Clean break deferred to Phase 4
- Users given time to migrate
- Documentation guides toward new pattern

**Dependency rationale:**
- waivern-core: Base abstractions (Analyser, Message, Schema)
- waivern-filesystem: Only for SourceCodeConnector (deprecated)
- pydantic: Configuration validation (both components)
- tree-sitter: Optional, for parsing functionality

**Phase 4 changes:**
When connector deprecated:
- Remove waivern-filesystem dependency entirely
- Update description to "Source code analyser"
- Remove connector entry point
- Remove connector classes

**Documentation updates needed:**
- README: Add "Migration Guide" section
- README: Show pipeline usage example
- README: Mark connector as deprecated
- Docstrings: Add deprecation warnings

**Future considerations:**
- Could split into 2 packages: waivern-source-code-connector, waivern-source-code-analyser
- Current approach simpler for transition
- Re-evaluate in Phase 4 if split needed
