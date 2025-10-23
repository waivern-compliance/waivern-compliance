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

# Include py.typed marker
# If component has schemas, include them too
include = [
    "src/{PACKAGE_MODULE}/**/*.py",
    "src/{PACKAGE_MODULE}/py.typed",
    # If schemas exist:
    # "src/{PACKAGE_MODULE}/**/schemas/json_schemas/**/*.json",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{PACKAGE_MODULE}"]

[tool.basedpyright]
typeCheckingMode = "strict"
reportImplicitOverride = "error"

[tool.ruff]
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = ["ANN", "B", "D", "F", "I", "PL", "RUF100", "S", "UP"]
ignore = ["D203", "D213"]

[tool.ruff.lint.pydocstyle]
ignore-decorators = ["typing.overload"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "PLR2004"]
```

#### 1.4 Copy Component Code

```bash
cp -r libs/waivern-community/src/waivern_community/{CURRENT_LOCATION}/* \
      libs/{PACKAGE_NAME}/src/{PACKAGE_MODULE}/
```

#### 1.5 Update Imports

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

#### 1.6 Package Exports

`src/{PACKAGE_MODULE}/__init__.py`:
```python
"""{DESCRIPTION}."""

from .{component} import {COMPONENT_NAME}
# Add other exports as needed
# from .config import {CONFIG_NAME}
# from .schemas import {SCHEMA_NAME}

__all__ = [
    "{COMPONENT_NAME}",
    # Add other exports
]
```

#### 1.7 Move Tests

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

#### 1.8 Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    # ... existing packages
    # If using shared package, add after it:
    # "libs/{SHARED_PACKAGE}",
    "libs/{PACKAGE_NAME}",  # ADD THIS
    "libs/waivern-community",
    # ...
]

[tool.uv.sources]
# ... existing sources
{PACKAGE_NAME} = { workspace = true }  # ADD THIS
```

#### 1.9 Initial Package Installation

```bash
uv sync --package {PACKAGE_NAME}
uv run python -c "import {PACKAGE_MODULE}; print('✓ Package installed')"
```

#### 1.10 Run Package Tests

```bash
cd libs/{PACKAGE_NAME}
uv run pytest tests/ -v
# Expected: ~{TEST_COUNT} tests passing
```

#### 1.11 Update Root Workspace Scripts

Update `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh`:

```bash
# Add in correct dependency order (after {SHARED_PACKAGE} if applicable)
(cd libs/{PACKAGE_NAME} && ./scripts/lint.sh "$@")
(cd libs/{PACKAGE_NAME} && ./scripts/format.sh "$@")
(cd libs/{PACKAGE_NAME} && ./scripts/type-check.sh)
```

#### 1.12 Update Pre-commit Wrapper Scripts

Update `scripts/pre-commit-lint.sh`, `scripts/pre-commit-format.sh`, `scripts/pre-commit-type-check.sh`:

```bash
# Add file grouping array
{package_name}_files=()

# Add pattern matching
elif [[ "$file" == libs/{PACKAGE_NAME}/* ]]; then
    {package_name}_files+=("${file#libs/{PACKAGE_NAME}/}")

# Add processing block (in dependency order)
if [ ${#{package_name}_files[@]} -gt 0 ]; then
    (cd libs/{PACKAGE_NAME} && ./scripts/lint.sh "${${package_name}_files[@]}")
fi
```

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

#### 2.4 Run Quality Checks

```bash
cd libs/waivern-community
uv run pytest tests/ -v

cd /path/to/workspace
./scripts/dev-checks.sh
```

---

### Phase 3: Update WCT Application

#### 3.1 Update Dependencies

Update `apps/wct/pyproject.toml`:

```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    # If using shared package:
    # "{SHARED_PACKAGE}",
    "{PACKAGE_NAME}",  # ADD THIS
    "waivern-community",
    # ... rest
]
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

## Development

See [CLAUDE.md](../../CLAUDE.md) for development guidelines.
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
