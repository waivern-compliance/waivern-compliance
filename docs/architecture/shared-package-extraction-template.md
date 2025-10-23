# Shared Package Extraction Template

**Purpose:** Template for extracting shared utilities from waivern-community into standalone shared package

---

## When to Use This Template

✅ **Use this template when:**
- Multiple components in waivern-community share significant utilities (>100 lines)
- You're extracting a component that shares code with components remaining in community
- The shared code will benefit multiple components now and in the future

❌ **Skip this template when:**
- Component has no shared utilities (use component-extraction-template.md directly)
- Shared package already exists (just add to dependencies)
- Component is completely self-contained

---

## Template Variables

Before starting, define these variables for your specific extraction:

| Variable | Example | Description |
|----------|---------|-------------|
| `{SHARED_PACKAGE}` | `waivern-analysers-shared` | Full shared package name (lowercase, with hyphens) |
| `{SHARED_MODULE}` | `waivern_analysers_shared` | Python module name (lowercase, underscores) |
| `{COMPONENT_TYPE}` | `analysers`, `connectors` | Type of components sharing utilities |
| `{SHARED_CODE_LOCATION}` | `analysers/utilities/` | Current path in waivern-community |
| `{DEPENDENT_COMPONENTS}` | `PersonalData, DataSubject, ProcessingPurpose` | Components using shared code |
| `{DESCRIPTION}` | `Shared utilities for WCF analysers` | One-line package description |
| `{TEST_COUNT}` | `~57` | Approximate number of tests for shared code |

---

## Architecture Overview

### Before Extraction

```
waivern-community/
└── {COMPONENT_TYPE}/
    ├── component_a/           (uses shared code)
    ├── component_b/           (uses shared code)
    ├── component_c/           (uses shared code)
    └── {SHARED_CODE_LOCATION} (~X lines - shared)
```

### After Extraction

```
{SHARED_PACKAGE}/              (NEW - ~X lines)
└── shared utilities

waivern-community/
└── {COMPONENT_TYPE}/
    ├── component_a/           (imports from shared package)
    ├── component_b/           (imports from shared package)
    └── component_c/           (imports from shared package)
```

### Dependency Graph

```
waivern-core
    ↓
[other dependencies]
    ↓
{SHARED_PACKAGE} (NEW)
    ↓
waivern-community (updated)
    ↓
wct
```

---

## Implementation Plan

### Phase 1: Create Shared Package

#### 1.1 Create Package Structure

```bash
mkdir -p libs/{SHARED_PACKAGE}/src/{SHARED_MODULE}
mkdir -p libs/{SHARED_PACKAGE}/tests/{SHARED_MODULE}
mkdir -p libs/{SHARED_PACKAGE}/scripts

# CRITICAL: Create py.typed marker INSIDE the package directory (not at package root!)
# Location: libs/{SHARED_PACKAGE}/src/{SHARED_MODULE}/py.typed
touch libs/{SHARED_PACKAGE}/src/{SHARED_MODULE}/py.typed
```

**IMPORTANT - py.typed location:**
- ✅ CORRECT: `libs/{SHARED_PACKAGE}/src/{SHARED_MODULE}/py.typed` (inside package)
- ❌ WRONG: `libs/{SHARED_PACKAGE}/py.typed` (at package root)

The `py.typed` file MUST be inside `src/{SHARED_MODULE}/` directory. Without it in the correct location, importing packages will show "Stub file not found" errors from type checkers.

#### 1.2 Copy and Update Package Scripts

Copy script templates from waivern-core (uses comprehensive type checking):

```bash
cp libs/waivern-core/scripts/*.sh libs/{SHARED_PACKAGE}/scripts/
chmod +x libs/{SHARED_PACKAGE}/scripts/*.sh
```

**Update package-specific comments in scripts:**

Only update the comment header in `type-check.sh`:

```bash
# Change this:
# Run static type checking for waivern-core package

# To this:
# Run static type checking for {SHARED_PACKAGE} package
```

**All three scripts:**
- **`lint.sh`**: ✅ Ready to use (may need comment update)
- **`format.sh`**: ✅ Ready to use (may need comment update)
- **`type-check.sh`**: ⚠️ Update package name in comment

#### 1.3 Create pyproject.toml

```toml
[project]
name = "{SHARED_PACKAGE}"
version = "0.1.0"
description = "{DESCRIPTION}"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    # Add other dependencies as needed
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

# CRITICAL: Include py.typed marker for type checking support
include = [
    "src/{SHARED_MODULE}/**/*.py",
    "src/{SHARED_MODULE}/py.typed",
]

[tool.hatch.build.targets.wheel]
packages = ["src/{SHARED_MODULE}"]

[tool.basedpyright]
typeCheckingMode = "strict"
reportImplicitOverride = "error"

[tool.ruff]
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = ["ANN", "B", "D", "F", "I", "PL", "RUF100", "S", "UP"]
ignore = ["D203", "D213"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "PLR2004"]
```

#### 1.4 Copy Shared Code

**Copy (not move)** from waivern-community:

```bash
cp -r libs/waivern-community/src/waivern_community/{SHARED_CODE_LOCATION}/* \
      libs/{SHARED_PACKAGE}/src/{SHARED_MODULE}/
```

**Note:** Keep originals temporarily until all components are updated.

#### 1.5 Create Package Exports

`src/{SHARED_MODULE}/__init__.py`:
```python
"""{DESCRIPTION}."""

# Import and export shared utilities
from .module_a import ClassA
from .module_b import ClassB

__all__ = [
    "ClassA",
    "ClassB",
]
```

#### 1.6 Copy and Update Tests

Copy tests from waivern-community and update imports:

```bash
cp -r libs/waivern-community/tests/waivern_community/{SHARED_CODE_LOCATION}/* \
      libs/{SHARED_PACKAGE}/tests/{SHARED_MODULE}/
```

Update imports in tests:
```python
# Before
from waivern_community.{COMPONENT_TYPE}.utilities import Utility

# After
from {SHARED_MODULE} import Utility
```

**Update patch paths in tests:**
Replace `waivern_community.{COMPONENT_TYPE}.` with `{SHARED_MODULE}.` in `@patch` decorators.

#### 1.7 Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    "libs/waivern-core",
    # ... other packages in dependency order
    "libs/{SHARED_PACKAGE}",  # ADD THIS (in correct dependency order)
    "libs/waivern-community",
    "apps/wct",
]

[tool.uv.sources]
waivern-core = { workspace = true }
# ... other sources
{SHARED_PACKAGE} = { workspace = true }  # ADD THIS
waivern-community = { workspace = true }
```

#### 1.8 Initial Package Installation

```bash
uv sync --package {SHARED_PACKAGE}
uv run python -c "import {SHARED_MODULE}; print('✓ Package installed')"
```

#### 1.9 Run Package Tests

```bash
cd libs/{SHARED_PACKAGE}
uv run pytest tests/ -v
# Expected: ~{TEST_COUNT} tests passing
```

#### 1.10 Update Root Workspace Scripts

Update `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh`:

```bash
# Add in correct dependency order
(cd libs/{SHARED_PACKAGE} && ./scripts/lint.sh "$@")
(cd libs/{SHARED_PACKAGE} && ./scripts/format.sh "$@")
(cd libs/{SHARED_PACKAGE} && ./scripts/type-check.sh)
```

#### 1.11 Update Pre-commit Wrapper Scripts

Update `scripts/pre-commit-lint.sh`, `scripts/pre-commit-format.sh`, `scripts/pre-commit-type-check.sh`:

```bash
# Add file grouping array
{shared_package}_files=()

# Add pattern matching in the loop
elif [[ "$file" == libs/{SHARED_PACKAGE}/* ]]; then
    {shared_package}_files+=("${file#libs/{SHARED_PACKAGE}/}")

# Add processing block (in dependency order)
if [ ${#{shared_package}_files[@]} -gt 0 ]; then
    (cd libs/{SHARED_PACKAGE} && ./scripts/lint.sh "${${shared_package}_files[@]}")
fi
```

#### 1.12 Run Dev-Checks and Fix Linting Errors

```bash
./scripts/dev-checks.sh 2>&1 | tee /tmp/dev-checks-shared.txt
```

Fix any linting errors following the pattern from previous extractions.

---

### Phase 2: Update waivern-community

#### 2.1 Update Dependencies

Update `libs/waivern-community/pyproject.toml`:

```toml
dependencies = [
    "waivern-core",
    # ... other dependencies
    "{SHARED_PACKAGE}",  # ADD THIS
    # ... rest
]
```

#### 2.2 Update Component Imports

Update all components to use shared utilities:

```python
# Before
from waivern_community.{COMPONENT_TYPE}.utilities import Utility

# After
from {SHARED_MODULE} import Utility
```

**Files to update:**
- List all component files that import from {SHARED_CODE_LOCATION}
- Include both source files and test files
- Update patch paths in tests

#### 2.3 Delete Extracted Code

Delete shared code (moved to shared package):

```bash
# Delete shared utilities (moved to {SHARED_PACKAGE})
rm -rf libs/waivern-community/src/waivern_community/{SHARED_CODE_LOCATION}

# Delete related tests (moved to {SHARED_PACKAGE})
rm -rf libs/waivern-community/tests/waivern_community/{SHARED_CODE_LOCATION}
```

**After this step:**
- ✅ All components using {SHARED_MODULE}
- ✅ Components ready for further extraction if needed

#### 2.4 Run Quality Checks and Fix Errors

**CRITICAL:** After deleting old files and updating imports, verify everything still works.

```bash
# Run all tests
cd libs/waivern-community
uv run pytest tests/ -v

# Run full dev-checks
cd /path/to/workspace
./scripts/dev-checks.sh 2>&1 | tee /tmp/dev-checks-phase2.txt
```

**Fix any errors:**
1. **Import errors** - Ensure all imports updated correctly
2. **Type errors** - Fix any type annotation issues
3. **Lint errors** - Fix code quality issues
4. **Test failures** - Update tests that reference old locations

**Expected results:**
- All community tests pass
- All shared package tests pass
- Type checking passes (0 errors)
- Linting passes

**Do not proceed to component extraction until all checks pass!**

---

## Success Criteria Checklist

- [ ] {SHARED_PACKAGE} package created with tests and quality checks
- [ ] All dependent components updated to use shared package
- [ ] waivern-community dependencies updated
- [ ] Pre-commit scripts updated
- [ ] Orchestration scripts updated (lint, format, type-check)
- [ ] All tests passing
- [ ] All quality checks passing (dev-checks.sh)
- [ ] py.typed marker in correct location

---

## Next Steps

After this shared package extraction is complete, you can proceed with extracting specific components using `component-extraction-template.md`.

The shared package will be a dependency for extracted components.

---

## Notes

- This template creates foundation for multiple component extractions
- Shared package benefits all components (current and future)
- Follow dependency order when updating workspace scripts
- Always run dev-checks after each major step
- Track test counts to verify completeness
