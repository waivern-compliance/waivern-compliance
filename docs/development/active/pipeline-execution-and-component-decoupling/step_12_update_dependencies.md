# Task: Rename Package and Update Dependencies

- **Phase:** 3 - Refactor SourceCodeConnector → SourceCodeAnalyser
- **Status:** DONE
- **Prerequisites:** Step 11 (pipeline integration tests passing)
- **GitHub Issue:** #217

## Context

This is the final step of Phase 3, refactoring SourceCodeConnector into a pure transformer analyser. The package must be renamed to follow the naming convention of other analyser packages, and dependencies updated to reflect that the analyser no longer needs FilesystemConnector.

**See:** the parent implementation plan for full context.

## Purpose

1. Rename package from `waivern-source-code` to `waivern-source-code-analyser` to match naming convention
2. Update all imports throughout the codebase
3. Update `pyproject.toml` dependencies to reflect that SourceCodeAnalyser is independent
4. Document waivern-filesystem dependency (only needed by deprecated connector)

## Problem

**Issue 1: Package naming inconsistency**

Current package name: `waivern-source-code`

Other analyser packages follow the pattern:
- `waivern-personal-data-analyser`
- `waivern-processing-purpose-analyser`
- `waivern-data-subject-analyser`

The `waivern-source-code` name doesn't follow this convention and creates inconsistency.

**Issue 2: Dependency structure**

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
5. **Rename package to `waivern-source-code-analyser`** - Follow naming convention of other analyser packages

**Rationale:** Breaking dependencies immediately would break existing users. Phase 3 focuses on creating the analyser; Phase 4 will handle deprecation and removal.

**Package naming rationale:** Must rename from `waivern-source-code` to `waivern-source-code-analyser` to match the established naming convention:
- `waivern-personal-data-analyser`
- `waivern-processing-purpose-analyser`
- `waivern-data-subject-analyser`

This maintains consistency across all analyser packages in the framework.

## Implementation

### Files to Modify

#### Package Rename
1. Rename directory: `libs/waivern-source-code/` → `libs/waivern-source-code-analyser/`
2. Update `libs/waivern-source-code-analyser/pyproject.toml` - package name
3. Update root `pyproject.toml` - workspace sources mapping
4. Update all imports throughout codebase
5. Update entry points references
6. Update documentation references

#### Dependency Updates
`libs/waivern-source-code-analyser/pyproject.toml`

### Changes Required

#### 1. Rename package directory

```bash
mv libs/waivern-source-code libs/waivern-source-code-analyser
```

#### 2. Update package name in pyproject.toml

```toml
[project]
name = "waivern-source-code-analyser"
description = "Source code analyser for WCF"
```

#### 3. Update root pyproject.toml workspace sources

```toml
[tool.uv.sources]
waivern-source-code-analyser = { workspace = true }
```

Remove old `waivern-source-code` entry.

#### 4. Add dependency documentation comment

Add comment explaining waivern-filesystem is only needed by connector (deprecated):

```toml
dependencies = [
    "waivern-core",
    "waivern-filesystem",  # Only needed by SourceCodeConnector (deprecated). Will be removed in Phase 4.
    "pydantic>=2.11.5",
]
```

#### 5. Update all import statements

Find and replace all imports:
- Old: `from waivern_source_code`
- New: `from waivern_source_code_analyser`

Files to update:
- All test files in `libs/waivern-source-code-analyser/tests/`
- Integration test: `libs/waivern-source-code-analyser/tests/test_pipeline_integration.py`
- WCT application files that import from this package
- Any other packages that depend on waivern-source-code

#### 6. Update entry points

In `libs/waivern-source-code-analyser/pyproject.toml`:

```toml
[project.entry-points."waivern.analysers"]
source_code_analyser = "waivern_source_code_analyser.analyser_factory:SourceCodeAnalyserFactory"

[project.entry-points."waivern.connectors"]
source_code_connector = "waivern_source_code_analyser.factory:SourceCodeConnectorFactory"
```

#### 7. Verify other dependencies

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
- [x] Package renamed to `waivern-source-code-analyser`
- [x] Package installs successfully with new name
- [x] SourceCodeAnalyser works without filesystem dependency in code
- [x] SourceCodeConnector removed (deprecated connector entry point deleted)
- [x] waivern-filesystem dependency removed from package
- [x] Package description updated
- [x] All imports updated throughout codebase

**Quality:**
- [x] All tests pass after rename and dependency changes (923 passed, 7 skipped)
- [x] Type checking passes
- [x] Linting passes
- [x] Package builds successfully
- [x] No references to old package name remain

**Code Quality:**
- [x] Dependencies cleaned up (removed waivern-filesystem)
- [x] Connector entry point removed (not exported anymore)
- [x] No unused dependencies
- [x] Naming convention matches other analyser packages

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
- Update description to "Source code analyser for WCF"
- Remove connector entry point
- Remove connector classes

**Package rename impact:**
- Directory rename: `libs/waivern-source-code/` → `libs/waivern-source-code-analyser/`
- Module imports: `waivern_source_code` → `waivern_source_code_analyser`
- Package name: `waivern-source-code` → `waivern-source-code-analyser`
- Follows established naming convention for analyser packages
- Breaking change but necessary for consistency

**Documentation updates needed:**
- README: Add "Migration Guide" section
- README: Show pipeline usage example
- README: Mark connector as deprecated
- Docstrings: Add deprecation warnings
- Update all references to package name

**Files requiring import updates:**
- All test files in the package
- WCT executor and related files
- Any integration tests
- Documentation examples
