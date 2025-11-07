# Component Extraction Template

**Purpose:** Template for extracting specific components from waivern-community into standalone packages

---

## When to Use This Template

✅ **Use this template when:**
- Moving a component (analyser, connector) from waivern-community to standalone package
- Component is mature and stable enough for independent versioning
- Users need minimal dependencies (only this component, not entire community package)

---

## Prerequisites

**Does your component share code with components remaining in waivern-community?**

- ✅ **YES:** Complete `shared-package-extraction-template.md` FIRST, then use this template
- ❌ **NO:** Use this template directly (component is self-contained)

---

## Template Variables

Before starting, define these variables for your specific extraction:

| Variable | Example | Description |
|----------|---------|-------------|
| `{PACKAGE_NAME}` | `waivern-personal-data-analyser` | Full package name (lowercase, with hyphens) |
| `{PACKAGE_MODULE}` | `waivern_personal_data_analyser` | Python module name (lowercase, underscores) |
| `{COMPONENT_TYPE}` | `analyser`, `connector` | Type of component being extracted |
| `{COMPONENT_NAME}` | `PersonalDataAnalyser` | Component class name (PascalCase) |
| `{CONFIG_NAME}` | `PersonalDataAnalyserConfig` | Config class name (if applicable) |
| `{SCHEMA_NAME}` | `PersonalDataFindingSchema` | Schema class name (if applicable) |
| `{DESCRIPTION}` | `Personal data analyser for WCF` | One-line package description |
| `{SHARED_PACKAGE}` | `waivern-analysers-shared` | Shared utilities package (if applicable) |
| `{CURRENT_LOCATION}` | `analysers/personal_data_analyser/` | Current path in waivern-community |
| `{TEST_COUNT}` | `~38` | Approximate number of tests |

---

## Architecture Overview

### Before Extraction

```
[{SHARED_PACKAGE}/]                 (if applicable - already exists)
└── shared utilities

waivern-community/
└── {COMPONENT_TYPE}s/
    ├── {component}/                (~X lines - TO EXTRACT)
    ├── other_component_a/          (remains in community)
    └── other_component_b/          (remains in community)
```

### After Extraction

```
{PACKAGE_NAME}/                     (NEW - ~X lines)
├── {component}.py
├── config.py
├── schemas/                        (if applicable)
│   └── {schema}.py
└── tests/

waivern-community/
└── {COMPONENT_TYPE}s/
    ├── other_component_a/          (remains in community)
    ├── other_component_b/          (remains in community)
    └── __init__.py                 (re-exports {COMPONENT_NAME})
```

### Dependency Graph

```
waivern-core
    ↓
[{SHARED_PACKAGE}]  (if applicable)
    ↓
{PACKAGE_NAME} (NEW)
    ↓
waivern-community (re-exports for backward compatibility)
    ↓
wct
```

---

## Implementation Plan

### Phase 1: Create Component Package

#### 1.1 Create Package Structure

```bash
mkdir -p libs/{PACKAGE_NAME}/src/{PACKAGE_MODULE}
mkdir -p libs/{PACKAGE_NAME}/tests/{PACKAGE_MODULE}
mkdir -p libs/{PACKAGE_NAME}/scripts

# CRITICAL: Create py.typed marker INSIDE the package directory (not at package root!)
# Location: libs/{PACKAGE_NAME}/src/{PACKAGE_MODULE}/py.typed
touch libs/{PACKAGE_NAME}/src/{PACKAGE_MODULE}/py.typed
```

**IMPORTANT - py.typed location:**
- ✅ CORRECT: `libs/{PACKAGE_NAME}/src/{PACKAGE_MODULE}/py.typed` (inside package)
- ❌ WRONG: `libs/{PACKAGE_NAME}/py.typed` (at package root)

#### 1.2 Copy and Update Package Scripts

Copy script templates from waivern-core (uses comprehensive type checking):

```bash
cp libs/waivern-core/scripts/*.sh libs/{PACKAGE_NAME}/scripts/
chmod +x libs/{PACKAGE_NAME}/scripts/*.sh
```

**Update package-specific comments in scripts:**

Only update the comment header in `type-check.sh`:

```bash
# Change this:
# Run static type checking for waivern-core package

# To this:
# Run static type checking for {PACKAGE_NAME} package
```

**All three scripts:**
- **`lint.sh`**: ✅ Ready to use (may need comment update)
- **`format.sh`**: ✅ Ready to use (may need comment update)
- **`type-check.sh`**: ⚠️ Update package name in comment

#### 1.3 Create pyproject.toml

```toml
[project]
name = "{PACKAGE_NAME}"
version = "0.1.0"
description = "{DESCRIPTION}"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    # If using shared package:
    # "{SHARED_PACKAGE}",
    # Add other dependencies
    "pydantic>=2.11.5",
]

[dependency-groups]
dev = [
    "basedpyright>=1.29.2",
    "ruff>=0.11.12",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build]
dev-mode-dirs = ["src"]

# IMPORTANT: Only include non-.py files (Hatchling includes .py files by default)
# Omit this entire section if your package only contains .py files (e.g., waivern-mysql)
# Include this section ONLY if your package has non-.py files to distribute:
include = [
    "src/{PACKAGE_MODULE}/py.typed",
    # Add ONLY if your component has schemas:
    # "src/{PACKAGE_MODULE}/**/schemas/json_schemas/**/*.json",
    # Add ONLY if your component has YAML rulesets:
    # "src/{PACKAGE_MODULE}/**/rulesets/**/*.yaml",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{PACKAGE_MODULE}"]

[tool.basedpyright]
typeCheckingMode = "strict"
reportImplicitOverride = "error"

# Optional: Relax type checking for test files (recommended for packages with complex test fixtures)
# Used by: waivern-core, waivern-llm, waivern-analysers-shared, waivern-connectors-database
# Omit this section if you prefer strict type checking everywhere
[[tool.basedpyright.executionEnvironments]]
root = "tests"
reportUnknownVariableType = "none"
reportUnknownArgumentType = "none"
reportUnknownParameterType = "none"
reportUnknownMemberType = "none"
reportMissingParameterType = "none"
reportUnknownLambdaType = "none"

[tool.ruff]
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = [
    "ANN",    # flake8-annotations - enforce type annotations
    "B",      # flake8-bugbear - find likely bugs and design problems
    "D",      # pydocstyle - docstring style checking
    "F",      # pyflakes - detect various errors
    "I",      # isort - import sorting
    "PL",     # pylint - comprehensive code analysis
    "RUF100", # ruff-specific - detect unused noqa directives
    "S",      # flake8-bandit - security issue detection
    "UP",     # pyupgrade - upgrade syntax for newer Python versions
]
ignore = [
    "D203",    # one-blank-line-before-class - conflicts with D211 (no-blank-line-before-class)
    "D213",    # multi-line-summary-second-line - conflicts with D212 (multi-line-summary-first-line)
]

[tool.ruff.lint.pydocstyle]
ignore-decorators = ["typing.overload"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "ANN",     # Type annotations - not required in tests
    "B",       # flake8-bugbear - less strict in tests
    "D",       # Documentation - docstrings not required in tests
    "S101",    # Use of assert detected - assert statements are standard in pytest
    "PLC0415", # Import outside top-level - acceptable for checking optional dependencies
    "PLR2004", # Magic value comparison - magic values are acceptable in tests
]
```

#### 1.4 Create README.md

**Structure guidance:**
- **Title**: Package name
- **Brief description**: One-line description (same as pyproject.toml)
- **Overview**: 2-4 paragraphs explaining purpose, capabilities, and design
- **Installation**: Standard pip install command
- **Usage**: Concrete code example showing typical usage
- **Development**: Link to CLAUDE.md

**Example structure:**

```markdown
# {PACKAGE_NAME}

{DESCRIPTION}

## Overview

[Paragraph 1: What problem does this component solve?]
This component provides {functionality} for {use case}. It is designed to {key design principle}.

[Paragraph 2: Key capabilities]
Key features include:
- {Feature 1}
- {Feature 2}
- {Feature 3}

[Paragraph 3: Integration context (optional)]
This package integrates with the Waivern Compliance Framework and can be used {standalone/with other packages}.

## Installation

```bash
pip install {PACKAGE_NAME}
```

## Usage

```python
from {PACKAGE_MODULE} import {COMPONENT_NAME}

# Concrete example showing typical usage
{example_code}
```

```

**Reference examples:**
- See `libs/waivern-mysql/README.md` for connector example
- See `libs/waivern-personal-data-analyser/README.md` for analyser example

#### 1.5 Copy Component Code

```bash
cp -r libs/waivern-community/src/waivern_community/{CURRENT_LOCATION}/* \
      libs/{PACKAGE_NAME}/src/{PACKAGE_MODULE}/
```

#### 1.6 Update Imports

Update all Python files to use new imports:

```python
# If using shared package:
from {SHARED_PACKAGE} import SharedUtility

# Internal imports:
from {PACKAGE_MODULE}.module import Something

# Update waivern_community internal imports to package imports:
# Before: from waivern_community.{COMPONENT_TYPE}s.{component}.module import X
# After: from {PACKAGE_MODULE}.module import X
```

**Files to verify:**
- All .py files in the component directory
- Update imports from old waivern_community paths to new package paths

#### 1.7 Package Exports

`src/{PACKAGE_MODULE}/__init__.py`:

**CRITICAL: If your component has schemas, register the schema directory FIRST (before imports):**

```python
"""{DESCRIPTION}."""

from pathlib import Path
from waivern_core.schemas import SchemaRegistry

# IMPORTANT: Register schema directory BEFORE importing component classes
# This ensures schemas are discoverable when component classes are instantiated
_SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
SchemaRegistry.register_search_path(_SCHEMA_DIR)

from .{component} import {COMPONENT_NAME}
from .config import {CONFIG_NAME}
from .schemas import {SCHEMA_NAME}Model  # If you have schema models

__all__ = [
    "{COMPONENT_NAME}",
    "{CONFIG_NAME}",
    "{SCHEMA_NAME}Model",
]
```

**If your component does NOT have schemas:**

```python
"""{DESCRIPTION}."""

from .{component} import {COMPONENT_NAME}
from .config import {CONFIG_NAME}

__all__ = [
    "{COMPONENT_NAME}",
    "{CONFIG_NAME}",
]
```

**Reference examples:**
- With schemas: `libs/waivern-personal-data-analyser/src/waivern_personal_data_analyser/__init__.py`
- Without schemas: `libs/waivern-mysql/src/waivern_mysql/__init__.py`

#### 1.8 Move Tests

```bash
mv libs/waivern-community/tests/waivern_community/{CURRENT_LOCATION}/* \
   libs/{PACKAGE_NAME}/tests/{PACKAGE_MODULE}/
```

Update test imports:
```python
# Before
from waivern_community.{COMPONENT_TYPE}s.{component} import {COMPONENT_NAME}

# After
from {PACKAGE_MODULE} import {COMPONENT_NAME}
```

#### 1.9 Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    "libs/*",    # ✅ AUTO-DISCOVERS all packages - no action needed!
    "apps/*",    # ✅ Your new package will be automatically discovered
]

[tool.uv.sources]
# ❌ NOT AUTO-DISCOVERED - you MUST manually add this line:
{PACKAGE_NAME} = { workspace = true }  # ADD THIS - REQUIRED!
```

**CRITICAL DISTINCTION:**

| Configuration | Auto-Discovery | Action Required |
|--------------|----------------|-----------------|
| `[tool.uv.workspace]` members | ✅ Yes (via `libs/*` glob) | ❌ No update needed |
| `[tool.uv.sources]` | ❌ No (mapping structure) | ✅ **MUST manually add entry** |

**Why manual update is required:**
- Workspace members use glob patterns (`libs/*`) for auto-discovery
- Workspace sources use a mapping structure that cannot use globs
- If you forget this step, other packages won't be able to import your package
- This is only required if your package will be used as a dependency by other packages

**After adding the source entry, verify it appears in workspace sources:**
```bash
uv sync
# Your package should now be available to other workspace members
```

#### 1.10 Initial Package Installation

```bash
uv sync --package {PACKAGE_NAME}
uv run python -c "import {PACKAGE_MODULE}; print('✓ Package installed')"
```

#### 1.11 Run Package Tests

```bash
cd libs/{PACKAGE_NAME}
uv run pytest tests/ -v
# Expected: ~{TEST_COUNT} tests passing
```

#### 1.12 Workspace Scripts Auto-Discovery ✅

**No action needed!** Workspace scripts now auto-discover packages:

- `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh` automatically find all packages in `libs/*` and `apps/*`
- Scripts run package checks in parallel for improved performance
- Pre-commit scripts (`scripts/pre-commit-*.sh`) dynamically group files by package

Your new package will be automatically discovered as long as:
1. It has a `pyproject.toml` file
2. It has the standard scripts: `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh`

No manual script updates required!

#### 1.13 Run Dev-Checks and Fix Linting Errors

```bash
./scripts/dev-checks.sh 2>&1 | tee /tmp/dev-checks-component.txt
```

---

### Phase 2: Update waivern-community

#### 2.1 Update Dependencies

Update `libs/waivern-community/pyproject.toml`:

```toml
dependencies = [
    "waivern-core",
    # ... other dependencies
    # If using shared package (already added):
    # "{SHARED_PACKAGE}",
    "{PACKAGE_NAME}",  # ADD THIS
    # ... rest
]
```

#### 2.2 Update Component Exports

Update `src/waivern_community/{COMPONENT_TYPE}s/__init__.py`:

```python
"""WCT {COMPONENT_TYPE}s."""

# Import from waivern_core
from waivern_core import {ComponentType}, {ComponentType}Error

# Import from standalone packages
from {PACKAGE_MODULE} import {COMPONENT_NAME}

# Import from waivern_community
from waivern_community.{COMPONENT_TYPE}s.other_component import OtherComponent

__all__ = (
    "{ComponentType}",
    "{ComponentType}Error",
    "{COMPONENT_NAME}",  # Re-exported from standalone package
    "OtherComponent",
    "BUILTIN_{COMPONENT_TYPE}S",
)

BUILTIN_{COMPONENT_TYPE}S = (
    {COMPONENT_NAME},
    OtherComponent,
)
```

#### 2.3 Delete Extracted Code

Remove component from waivern-community:

```bash
# Delete component (now in standalone package)
rm -rf libs/waivern-community/src/waivern_community/{CURRENT_LOCATION}
rm -rf libs/waivern-community/tests/waivern_community/{CURRENT_LOCATION}
```

#### 2.4 Run Quality Checks and Fix All Errors

**CRITICAL:** Run dev-checks and fix ALL errors immediately, including downstream errors in WCT or other packages. Do not leave broken tests for later phases.

```bash
# Run full workspace dev-checks
./scripts/dev-checks.sh 2>&1 | tee /tmp/dev-checks-phase2.txt
```

**Fix errors as they appear:**

1. **waivern-community errors:**
   - Update any remaining imports in `src/waivern_community/__init__.py`
   - Fix any references to old package paths

2. **WCT errors (if dev-checks reveals them):**
   - Update `apps/wct/src/wct/schemas/__init__.py` to import from standalone package
   - Update any WCT test files that import from old paths
   - Fix any patch paths in tests (replace old module paths with new package paths)

3. **Re-run dev-checks until all pass:**
   ```bash
   ./scripts/dev-checks.sh
   # Expected: All tests passing, 0 type errors, all lint checks passed
   ```

**Expected results:**
- ✅ All waivern-community tests pass
- ✅ All WCT tests pass
- ✅ Type checking passes (0 errors)
- ✅ Linting passes

**Do not proceed to Phase 3 if any errors remain!**

---

### Phase 3: Update WCT Application

**Note:** If you followed Phase 2.4 correctly, WCT imports and tests were already fixed during quality checks. This phase is primarily for adding dependencies if not already done.

#### 3.1 Update Dependencies (if needed)

Check if `apps/wct/pyproject.toml` needs updating:

```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    # If using shared package (may already be present):
    # "{SHARED_PACKAGE}",
    "{PACKAGE_NAME}",  # ADD if not present
    "waivern-community",
    # ... rest
]
```

**Note:** waivern-community already depends on {PACKAGE_NAME}, so WCT gets it transitively. Only add explicit dependency if needed for direct imports.

#### 3.2 Verify WCT Still Works

```bash
# Verify component is registered
uv run wct ls-{COMPONENT_TYPE}s | grep {component}

# Expected output shows component is available
```

---

### Phase 4: Verification & Testing

#### 4.1 Workspace Sync

```bash
uv sync
```

#### 4.2 Test New Package

```bash
cd libs/{PACKAGE_NAME}
uv run pytest tests/ -v
# Expected: ~{TEST_COUNT} tests passing
```

#### 4.3 Full Test Suite

```bash
cd /path/to/workspace
uv run pytest
# Expected: All tests passing (same count, different package locations)
```

#### 4.4 Quality Checks

```bash
./scripts/dev-checks.sh
# Expected: All checks passing
```

#### 4.5 Verify Integration

```bash
# For connectors
uv run wct ls-connectors | grep {component}

# For analysers
uv run wct ls-analysers | grep {component}

# Validate related runbook if applicable
uv run wct validate-runbook apps/wct/runbooks/samples/{runbook}.yaml

# Run sample analysis if applicable
uv run wct run apps/wct/runbooks/samples/{runbook}.yaml -v
```

---

### Phase 5: Update Documentation

#### 5.1 Update CLAUDE.md

Update package structure:

```markdown
libs/
├── waivern-core/
├── waivern-llm/
├── [{SHARED_PACKAGE}/]    # If applicable
├── {PACKAGE_NAME}/        # NEW
└── waivern-community/
```

Update package descriptions:

```markdown
**Framework Libraries:**
- **waivern-core**: Base abstractions
- **{PACKAGE_NAME}**: {DESCRIPTION} (standalone)
- **waivern-community**: Built-in components (re-exports standalone packages)
```

#### 5.2 Update Migration Documentation

Update:
- `docs/architecture/monorepo-migration-plan.md` - Mark phase complete
- `docs/architecture/monorepo-migration-completed.md` - Add phase details

#### 5.3 Create Package README

**`libs/{PACKAGE_NAME}/README.md`:**
```markdown
# {PACKAGE_NAME}

{DESCRIPTION}

## Overview

[Describe what the component does]

## Installation

```bash
pip install {PACKAGE_NAME}
```

## Usage

```python
from {PACKAGE_MODULE} import {COMPONENT_NAME}

# Usage example
```

```

---

### Phase 6: Commit Changes

#### 6.1 Commit Message

```
refactor: extract {COMPONENT_NAME} as standalone package

Extract {COMPONENT_NAME} from waivern-community into standalone
{PACKAGE_NAME} package for minimal dependencies and independent versioning.

Architecture:
- Create libs/{PACKAGE_NAME}/ package
  * {COMPONENT_NAME} and {CONFIG_NAME}
  [If using shared package:]
  * Depends on {SHARED_PACKAGE} for shared utilities
  * ~X lines of component-specific code
  * {TEST_COUNT} tests
- Update waivern-community
  * Imports and re-exports {COMPONENT_NAME} from standalone package
  * Maintains backward compatibility via re-exports
- Update WCT
  * Add {PACKAGE_NAME} dependency

Dependency graph:
  waivern-core
      ↓
  [{SHARED_PACKAGE}]  (if applicable)
      ↓
  {PACKAGE_NAME} (NEW)
      ↓
  waivern-community (re-exports)
      ↓
  wct

Benefits:
- Minimal dependencies: Users wanting only {COMPONENT_NAME} get ~X lines
  vs entire community package
- Independent versioning and maintenance
- Enables third-party contributions

Test results:
- All X tests passing
- Type checking: 0 errors (strict mode)
- Linting: all checks passed
[If applicable:]
- {runbook}.yaml validates successfully
```

---

## Troubleshooting

Common issues and solutions during component extraction:

### Issue 1: Package Not Found / Import Errors

**Symptoms:**
```
ModuleNotFoundError: No module named '{PACKAGE_MODULE}'
```

**Cause:** Forgot to add package to `[tool.uv.sources]` in root `pyproject.toml`

**Solution:**
1. Add entry to root `pyproject.toml`:
   ```toml
   [tool.uv.sources]
   {PACKAGE_NAME} = { workspace = true }
   ```
2. Run `uv sync` to register the package
3. Verify with: `uv run python -c "import {PACKAGE_MODULE}; print('✓ Package installed')"`

### Issue 2: Schemas Not Found

**Symptoms:**
```
SchemaNotFoundError: Schema '{schema_name}' version '{version}' not found
```

**Cause:** Schema directory not registered in package `__init__.py`

**Solution:**
1. Add schema registration to `src/{PACKAGE_MODULE}/__init__.py` (BEFORE imports):
   ```python
   from pathlib import Path
   from waivern_core.schemas import SchemaRegistry

   _SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
   SchemaRegistry.register_search_path(_SCHEMA_DIR)
   ```
2. Verify schemas are included in build (check `pyproject.toml` include directive)
3. Run tests to verify: `cd libs/{PACKAGE_NAME} && uv run pytest tests/ -v`

### Issue 3: Type Checking Errors in Tests

**Symptoms:**
```
error: Argument type is partially unknown [reportUnknownArgumentType]
```

**Cause:** Strict type checking applied to test files

**Solution:**
Add test environment relaxation to `pyproject.toml`:
```toml
[[tool.basedpyright.executionEnvironments]]
root = "tests"
reportUnknownVariableType = "none"
reportUnknownArgumentType = "none"
reportUnknownParameterType = "none"
reportUnknownMemberType = "none"
reportMissingParameterType = "none"
reportUnknownLambdaType = "none"
```

### Issue 4: Workspace Scripts Don't Find Package

**Symptoms:**
- Running `./scripts/lint.sh` doesn't check your new package

**Cause:** Package missing required scripts or `pyproject.toml`

**Solution:**
1. Verify package has all required scripts:
   ```bash
   ls libs/{PACKAGE_NAME}/scripts/
   # Should show: format.sh, lint.sh, type-check.sh
   ```
2. Ensure scripts are executable:
   ```bash
   chmod +x libs/{PACKAGE_NAME}/scripts/*.sh
   ```
3. Verify `pyproject.toml` exists in package root

### Issue 5: waivern-community Tests Fail After Extraction

**Symptoms:**
- Tests in waivern-community fail with import errors or missing components

**Cause:** Forgot to update imports in waivern-community `__init__.py` or missing dependency

**Solution:**
1. Update `libs/waivern-community/pyproject.toml` dependencies:
   ```toml
   dependencies = [
       "{PACKAGE_NAME}",
       # ... other deps
   ]
   ```
2. Update `libs/waivern-community/src/waivern_community/{COMPONENT_TYPE}s/__init__.py`:
   ```python
   from {PACKAGE_MODULE} import {COMPONENT_NAME}

   __all__ = (
       "{COMPONENT_NAME}",
       # ... other exports
   )
   ```
3. Run: `uv sync && ./scripts/dev-checks.sh`

### Issue 6: WCT Can't Find Component

**Symptoms:**
- `uv run wct ls-{COMPONENT_TYPE}s` doesn't show your component

**Cause:** Component not registered or WCT dependencies not updated

**Solution:**
1. Verify component is exported from waivern-community (see Issue 5)
2. Update WCT dependencies if needed (usually inherited from waivern-community)
3. Rebuild: `uv sync`
4. Verify: `uv run wct ls-{COMPONENT_TYPE}s | grep {component}`

### Verification Steps

Run these commands to verify extraction is complete:

```bash
# 1. Verify package installation
uv run python -c "import {PACKAGE_MODULE}; print('✓ Package installed')"

# 2. Run package tests
cd libs/{PACKAGE_NAME} && uv run pytest tests/ -v

# 3. Run full workspace checks
./scripts/dev-checks.sh

# 4. Verify component registration
uv run wct ls-{COMPONENT_TYPE}s | grep {component}

# 5. Validate related runbook (if applicable)
uv run wct validate-runbook apps/wct/runbooks/samples/{runbook}.yaml
```

---

## Success Criteria Checklist

- [ ] {PACKAGE_NAME} package created with all tests passing ({TEST_COUNT} tests)
- [ ] waivern-community updated (imports from new package)
- [ ] WCT dependencies updated
- [ ] Pre-commit scripts updated
- [ ] Orchestration scripts updated (lint, format, type-check)
- [ ] All tests passing
- [ ] All quality checks passing (dev-checks.sh)
- [ ] Related runbooks verified (if applicable)
- [ ] Documentation updated (CLAUDE.md, migration docs, package README)
- [ ] Changes committed to git

---

## Notes

- If using shared package, ensure it's completed first (see `shared-package-extraction-template.md`)
- Component imports should already be correct if shared package was extracted first
- Test count should remain same (tests move from community to new package)
- Maintains backward compatibility via waivern-community re-exports
- Follow dependency order when updating workspace scripts
