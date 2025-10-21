# Package Extraction Template

**Purpose:** Template for extracting components from waivern-community into standalone packages

---

## Template Variables

Before starting, define these variables for your specific extraction:

| Variable | Example | Description |
|----------|---------|-------------|
| `{PACKAGE_NAME}` | `waivern-source-code` | Full package name (lowercase, with hyphens) |
| `{PACKAGE_MODULE}` | `waivern_source_code` | Python module name (lowercase, underscores) |
| `{COMPONENT_TYPE}` | `analyser`, `connector` | Type of component being extracted |
| `{COMPONENT_NAME}` | `SourceCodeAnalyser` | Component class name (PascalCase) |
| `{CONFIG_NAME}` | `SourceCodeAnalyserConfig` | Config class name (if applicable) |
| `{DESCRIPTION}` | `Source code analyser for WCF` | One-line package description |
| `{SHARED_PACKAGE}` | `waivern-analysers-shared` | Shared utilities package (if needed) |
| `{DEPENDENCIES}` | `tree-sitter>=0.21.0` | External dependencies (comma-separated) |
| `{CURRENT_LOCATION}` | `connectors/source_code/` | Current path in waivern-community |
| `{TEST_COUNT}` | `~25` | Approximate number of tests |

---

## Decision: Shared Utilities Package

**Question:** Does this extraction require a shared utilities package?

### When to Create Shared Package

✅ Create shared package if:
- Multiple related components share significant utilities (>100 lines)
- You're extracting the **first** component of a type (e.g., first standalone analyser)
- Utilities are SQL/database-specific or domain-specific
- Future related packages will need the same utilities

❌ Skip shared package if:
- Component has no shared utilities
- Shared package already exists (just use it)
- Component is self-contained

### Package Naming Convention

| Component Type | Shared Package Name | Example |
|----------------|---------------------|---------|
| Database Connectors | `waivern-connectors-database` | MySQL, PostgreSQL, MSSQL |
| Analysers | `waivern-analysers-shared` | PersonalData, DataSubject, ProcessingPurpose |
| Source Code Tools | `waivern-source-code-shared` | PHP, Python, Java parsers |

**Decision for this extraction:**
- [ ] Create shared package: `{SHARED_PACKAGE}`
- [ ] Use existing shared package: `______________`
- [ ] No shared package needed

---

## Architecture Overview

### Package Dependency Graph

**With shared package:**
```
waivern-core
    ↓
{SHARED_PACKAGE}
    ↓
{PACKAGE_NAME} (standalone)
    ↓
waivern-community (re-exports for convenience)
    ↓
wct
```

**Without shared package:**
```
waivern-core
    ↓
{PACKAGE_NAME} (standalone)
    ↓
waivern-community (re-exports for convenience)
    ↓
wct
```

---

## Phase 1: Save Extraction Plan

**Status:** ⏳ Pending

Create a specific plan for this extraction:

```bash
cp docs/architecture/package-extraction-template.md \
   docs/architecture/{component-name}-extraction-plan.md
```

Fill in all template variables and customize phases as needed.

---

## Phase 2: Create Shared Package (If Needed)

**Status:** ⏳ Pending

**Skip this phase if:**
- No shared package needed
- Shared package already exists

### 2.1 Create Package Structure

```bash
mkdir -p libs/{SHARED_PACKAGE}/src/{SHARED_PACKAGE_MODULE}
mkdir -p libs/{SHARED_PACKAGE}/tests/{SHARED_PACKAGE_MODULE}
mkdir -p libs/{SHARED_PACKAGE}/scripts
```

Package structure:
```
libs/{SHARED_PACKAGE}/
├── src/{SHARED_PACKAGE_MODULE}/
│   ├── __init__.py
│   ├── base_*.py          # Base classes
│   ├── *_utils.py         # Shared utilities
│   └── [other modules]
├── tests/{SHARED_PACKAGE_MODULE}/
│   ├── test_base_*.py
│   └── test_*_utils.py
├── scripts/
│   ├── lint.sh
│   ├── format.sh
│   └── type-check.sh
├── pyproject.toml
├── README.md
└── py.typed
```

### 2.2 Create pyproject.toml

**IMPORTANT:** Compare with waivern-core and waivern-llm to ensure completeness.

```toml
[project]
name = "{SHARED_PACKAGE}"
version = "0.1.0"
description = "{DESCRIPTION of shared utilities}"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "pydantic>=2.11.5",
    # Add shared dependencies
]

[dependency-groups]
dev = [
    "basedpyright>=1.29.2",
    "ruff>=0.11.12",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# CRITICAL: Required for dev-mode installation
[tool.hatch.build]
dev-mode-dirs = ["src"]

[tool.hatch.build.targets.wheel]
packages = ["src/{SHARED_PACKAGE_MODULE}"]

[tool.basedpyright]
typeCheckingMode = "strict"
reportImplicitOverride = "error"

[tool.ruff]
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = [
    "ANN",    # flake8-annotations
    "B",      # flake8-bugbear
    "D",      # pydocstyle
    "F",      # pyflakes
    "I",      # isort
    "PL",     # pylint
    "RUF100", # unused-noqa-directive
    "S",      # bandit
    "UP",     # pyupgrade
]
ignore = [
    "D203",    # incorrect-blank-line-before-class (conflicts with D211)
    "D213",    # multi-line-summary-second-line (conflicts with D212)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "S101",    # Use of assert detected - standard in pytest
    "PLR2004", # Magic value used in comparison - acceptable in tests
]

# Add after analyzing linting errors
# [tool.ruff.lint.per-file-ignores]
# "tests/**/*.py" = ["S101"]
```

### 2.3 Copy Shared Code

**Copy (not move)** from waivern-community to shared package:

```bash
# Example for analysers
cp libs/waivern-community/src/waivern_community/analysers/base_*.py \
   libs/{SHARED_PACKAGE}/src/{SHARED_PACKAGE_MODULE}/

cp libs/waivern-community/src/waivern_community/analysers/*_utils.py \
   libs/{SHARED_PACKAGE}/src/{SHARED_PACKAGE_MODULE}/
```

**Note:** Keep originals temporarily until all components are updated.

### 2.4 Package Exports

Create `src/{SHARED_PACKAGE_MODULE}/__init__.py`:

```python
"""Shared utilities for {COMPONENT_TYPE}s."""

from .base_* import BaseClass
from .*_utils import UtilityClass

__all__ = [
    "BaseClass",
    "UtilityClass",
]
```

### 2.5 Copy and Update Tests

Copy tests and update imports:

```python
# Before
from waivern_community.{COMPONENT_TYPE}s.base import BaseClass

# After
from {SHARED_PACKAGE_MODULE} import BaseClass
```

### 2.6 Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    "libs/waivern-core",
    "libs/waivern-llm",
    "libs/{SHARED_PACKAGE}",     # Add this
    # ... other packages
]

[tool.uv.sources]
waivern-core = { workspace = true }
waivern-llm = { workspace = true }
{SHARED_PACKAGE} = { workspace = true }  # Add this
# ... other sources
```

### 2.7 Initial Package Installation

```bash
uv sync --package {SHARED_PACKAGE}

# Verify installation
uv run python -c "import {SHARED_PACKAGE_MODULE}; print('✓ Package installed')"
```

**Why `--package` flag?** When creating a new workspace package with no dependents yet, `uv sync` alone won't install it.

### 2.8 Run Package Tests

```bash
cd libs/{SHARED_PACKAGE}
uv run pytest tests/ -v

# Expected: ~X tests passing
```

### 2.9 Update Root Workspace Scripts

**CRITICAL:** Must update all orchestration scripts.

Update `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh`:

```bash
# Add after waivern-llm (or appropriate location based on dependencies)
(cd libs/{SHARED_PACKAGE} && ./scripts/lint.sh "$@")
```

### 2.10 Update Pre-commit Wrapper Scripts

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

### 2.11 Analyse and Fix Linting Errors

Run dev-checks to identify quality issues:

```bash
./scripts/dev-checks.sh 2>&1 | tee /tmp/dev-checks-output.txt
```

#### 2.11.1 Group Errors by Category

Common categories:
- **ANN201**: Missing return type annotations on test methods
- **S101**: Use of assert in tests (bandit security check)
- **D205/D400/D415**: Docstring formatting issues

#### 2.11.2 Fix Strategy

**Fix these:**
1. **ANN201** - Add `-> None` return type annotations
2. **D205/D400/D415** - Improve docstring formatting

**Ignore via configuration:**
3. **S101** - Add to pyproject.toml:
   ```toml
   [tool.ruff.lint.per-file-ignores]
   "tests/**/*.py" = ["S101"]  # Allow assert statements
   ```

#### 2.11.3 Verify Fixes

```bash
./scripts/dev-checks.sh

# Expected: All checks passing
```

---

## Phase 3: Extract Main Package

**Status:** ⏳ Pending

### 3.1 Create Package Structure

```bash
mkdir -p libs/{PACKAGE_NAME}/src/{PACKAGE_MODULE}
mkdir -p libs/{PACKAGE_NAME}/tests/{PACKAGE_MODULE}
mkdir -p libs/{PACKAGE_NAME}/scripts
```

Package structure:
```
libs/{PACKAGE_NAME}/
├── src/{PACKAGE_MODULE}/
│   ├── __init__.py
│   ├── {component}.py
│   ├── config.py
│   └── schemas/                # If component has schemas
│       ├── {schema}.py
│       └── json_schemas/
│           └── {schema}/
│               └── 1.0.0/
│                   └── {schema}.json
├── tests/{PACKAGE_MODULE}/
│   ├── test_{component}.py
│   └── test_config.py
├── scripts/
│   ├── lint.sh
│   ├── format.sh
│   └── type-check.sh
├── pyproject.toml
├── README.md
└── py.typed
```

### 3.2 Create pyproject.toml

```toml
[project]
name = "{PACKAGE_NAME}"
version = "0.1.0"
description = "{DESCRIPTION}"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "{SHARED_PACKAGE}",  # If using shared package
    "{DEPENDENCIES}",    # External dependencies
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

# CRITICAL: Required for dev-mode installation
[tool.hatch.build]
dev-mode-dirs = ["src"]

[tool.hatch.build.targets.wheel]
packages = ["src/{PACKAGE_MODULE}"]

# Include JSON schemas if component has them
include = [
    "src/{PACKAGE_MODULE}/**/*.py",
    "src/{PACKAGE_MODULE}/**/schemas/json_schemas/**/*.json",
]

[tool.basedpyright]
typeCheckingMode = "strict"
reportImplicitOverride = "error"

[tool.ruff]
target-version = "py312"
src = ["src"]

[tool.ruff.lint]
select = [
    "ANN", "B", "D", "F", "I", "PL", "RUF100", "S", "UP"
]
ignore = [
    "D203",    # incorrect-blank-line-before-class
    "D213",    # multi-line-summary-second-line
]

[tool.ruff.lint.pydocstyle]
ignore-decorators = ["typing.overload"]

# Add after analyzing linting errors
# [tool.ruff.lint.per-file-ignores]
# "tests/**/*.py" = ["S101"]
```

### 3.3 Copy Component Code

Copy from waivern-community:

```bash
cp -r libs/waivern-community/src/waivern_community/{CURRENT_LOCATION}/* \
      libs/{PACKAGE_NAME}/src/{PACKAGE_MODULE}/
```

### 3.4 Update Imports

Update all Python files to use new imports:

```python
# Before
from waivern_community.{old_imports} import Something

# After (if using shared package)
from {SHARED_PACKAGE_MODULE} import SharedUtility

# After (internal imports)
from {PACKAGE_MODULE}.module import Component
```

### 3.5 Package Exports

Create `src/{PACKAGE_MODULE}/__init__.py`:

```python
"""{DESCRIPTION}."""

from .{component} import {COMPONENT_NAME}
from .config import {CONFIG_NAME}

__all__ = [
    "{COMPONENT_NAME}",
    "{CONFIG_NAME}",
]
```

### 3.6 Move Tests

Move tests and update imports:

```bash
mv libs/waivern-community/tests/waivern_community/{CURRENT_LOCATION}/* \
   libs/{PACKAGE_NAME}/tests/{PACKAGE_MODULE}/
```

Update test imports:

```python
# Before
from waivern_community.{old_path} import Component

# After
from {PACKAGE_MODULE} import Component
```

### 3.7 Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    # ... existing packages
    "libs/{PACKAGE_NAME}",     # Add this
    # ... rest
]

[tool.uv.sources]
# ... existing sources
{PACKAGE_NAME} = { workspace = true }  # Add this
```

### 3.8 Initial Package Installation

```bash
uv sync --package {PACKAGE_NAME}

# Verify installation
uv run python -c "import {PACKAGE_MODULE}; print('✓ Package installed')"
```

### 3.9 Run Package Tests

```bash
cd libs/{PACKAGE_NAME}
uv run pytest tests/ -v

# Expected: ~{TEST_COUNT} tests passing
```

### 3.10 Update Root Workspace Scripts

Update `scripts/lint.sh`, `scripts/format.sh`, `scripts/type-check.sh`:

```bash
# Add after {SHARED_PACKAGE} (or appropriate location)
(cd libs/{PACKAGE_NAME} && ./scripts/lint.sh "$@")
```

### 3.11 Update Pre-commit Wrapper Scripts

Update `scripts/pre-commit-lint.sh`, `scripts/pre-commit-format.sh`, `scripts/pre-commit-type-check.sh`:

```bash
# Add file grouping array
{package}_files=()

# Add pattern matching
elif [[ "$file" == libs/{PACKAGE_NAME}/* ]]; then
    {package}_files+=("${file#libs/{PACKAGE_NAME}/}")

# Add processing block (in dependency order)
if [ ${#{package}_files[@]} -gt 0 ]; then
    (cd libs/{PACKAGE_NAME} && ./scripts/lint.sh "${${package}_files[@]}")
fi
```

### 3.12 Analyse and Fix Linting Errors

Follow same process as Phase 2 (steps 2.11.1 - 2.11.3)

---

## Phase 4: Update waivern-community

**Status:** ⏳ Pending

### 4.1 Update Dependencies

Update `libs/waivern-community/pyproject.toml`:

```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    "{SHARED_PACKAGE}",    # Add if applicable
    "{PACKAGE_NAME}",      # Import from standalone
    # ... other dependencies
]

# Remove optional dependencies that moved to standalone package
[project.optional-dependencies]
# Remove: {old-optional-dep} = ["..."]
```

### 4.2 Update Component Imports

Update files that used shared utilities:

```python
# Before
from waivern_community.{COMPONENT_TYPE}s.shared import SharedUtility

# After
from {SHARED_PACKAGE_MODULE} import SharedUtility
```

### 4.3 Update Component Exports

Update `src/waivern_community/{COMPONENT_TYPE}s/__init__.py`:

```python
from {PACKAGE_MODULE} import {COMPONENT_NAME}  # Import from standalone

from waivern_community.{COMPONENT_TYPE}s.other import OtherComponent

__all__ = (
    "{COMPONENT_NAME}",  # Re-exported for convenience
    "OtherComponent",
    # ... other exports
)

BUILTIN_{COMPONENT_TYPE_UPPER}S = (
    {COMPONENT_NAME},
    OtherComponent,
    # ...
)
```

### 4.4 Delete Extracted Code

Remove from waivern-community:

```bash
rm -rf libs/waivern-community/src/waivern_community/{CURRENT_LOCATION}
rm -rf libs/waivern-community/tests/waivern_community/{CURRENT_LOCATION}
```

**Keep shared utilities** temporarily if other components still use them internally.

---

## Phase 5: Update WCT Application

**Status:** ⏳ Pending

### 5.1 Update Dependencies

Update `apps/wct/pyproject.toml`:

```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    "{SHARED_PACKAGE}",    # Add if applicable
    "{PACKAGE_NAME}",      # Add
    "waivern-community",
    # ... rest
]
```

---

## Phase 6: Verification & Testing

**Status:** ⏳ Pending

### 6.1 Workspace Sync

```bash
uv sync
```

### 6.2 Test New Packages

```bash
# Shared package (if created)
cd libs/{SHARED_PACKAGE} && uv run pytest tests/

# Main package
cd libs/{PACKAGE_NAME} && uv run pytest tests/
```

### 6.3 Full Test Suite

```bash
cd /path/to/workspace
uv run pytest

# Expected: All tests passing (track count increase)
```

### 6.4 Quality Checks

```bash
./scripts/dev-checks.sh
```

### 6.5 Verify Integration

Test that WCT can still use the component:

```bash
# For connectors
uv run wct ls-connectors | grep {COMPONENT_NAME}

# For analysers
uv run wct ls-analysers | grep {COMPONENT_NAME}

# Run sample runbook if applicable
uv run wct validate-runbook apps/wct/runbooks/samples/{related-runbook}.yaml
```

---

## Phase 7: Update Documentation

**Status:** ⏳ Pending

### 7.1 CLAUDE.md

Update package structure diagram:

```markdown
libs/
├── waivern-core/
├── waivern-llm/
├── {SHARED_PACKAGE}/    # If created
├── {PACKAGE_NAME}/      # Add this
└── waivern-community/
```

Update relevant sections:
- Package descriptions
- Dependency graph
- Development commands (if needed)

### 7.2 Migration Documentation

Update:
- `docs/architecture/monorepo-migration-plan.md` - Mark phase complete
- `docs/architecture/monorepo-migration-completed.md` - Add phase details

### 7.3 Package README

Create `libs/{PACKAGE_NAME}/README.md`:

```markdown
# {PACKAGE_NAME}

{DESCRIPTION}

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

## Phase 8: Commit Changes

**Status:** ⏳ Pending

### 8.1 Commit Message Template

```
refactor: extract {COMPONENT_NAME} as {PACKAGE_NAME} package

[If shared package created:]
Create {SHARED_PACKAGE} package with shared {COMPONENT_TYPE} utilities.

Extract {COMPONENT_NAME} as standalone package for minimal dependencies
and independent versioning.

Architecture:
[If shared package created:]
- Create libs/{SHARED_PACKAGE}/ with shared utilities
  * [List key classes/utilities]
  * ~X lines total - minimal, focused package
- Extract libs/{PACKAGE_NAME}/ package
  * {COMPONENT_NAME} and {CONFIG_NAME}
  [If using shared package:]
  * Depends on {SHARED_PACKAGE} for shared utilities
  * Dependencies: {DEPENDENCIES}
  * ~Y lines of component-specific code
- Update waivern-community
  [If using shared package:]
  * Depends on {SHARED_PACKAGE} for remaining components
  * Imports and re-exports {COMPONENT_NAME} from {PACKAGE_NAME}
  * Maintains backward compatibility via re-exports

Dependency graph:
  waivern-core
      ↓
  [If shared package:]
  {SHARED_PACKAGE}
      ↓
  {PACKAGE_NAME} (standalone)
      ↓
  waivern-community (re-exports)
      ↓
  wct

Benefits:
- Minimal dependencies: Users wanting only {COMPONENT_NAME} get ~X lines vs
  entire community package = Y% reduction
- Independent versioning and maintenance
- Enables third-party contributions
[If shared package:]
- Shared utilities enable future {COMPONENT_TYPE} extractions

Code changes:
[If shared package:]
- Create {SHARED_PACKAGE} package with {COMPONENT_TYPE} utilities
- Move {COMPONENT_NAME} from waivern-community to {PACKAGE_NAME}
[If using shared package:]
- Update remaining components to import from {SHARED_PACKAGE}
- Update waivern-community to re-export {COMPONENT_NAME}
- Update WCT to depend on {PACKAGE_NAME}
- Update pre-commit hooks and orchestration scripts

Test results:
- All X tests passing
- Type checking: 0 errors (strict mode)
- Linting: all checks passed
[If applicable:]
- {Relevant runbook} validates successfully
```

---

## Success Criteria Checklist

- [ ] Extraction plan saved to documentation
- [ ] [If needed] Shared package created with tests and quality checks
- [ ] Main package created with all tests passing
- [ ] [If applicable] Other components updated to use shared utilities
- [ ] waivern-community updated (imports from new package)
- [ ] WCT dependencies updated
- [ ] Pre-commit scripts updated (all packages)
- [ ] Orchestration scripts updated (lint, format, type-check)
- [ ] All tests passing (track count: before vs after)
- [ ] All quality checks passing (dev-checks.sh)
- [ ] [If applicable] Related runbooks verified
- [ ] Documentation updated (CLAUDE.md, migration docs, package README)
- [ ] Changes committed to git

---

## Template Checklist

Use this abbreviated checklist during execution:

### Package Creation (Shared + Main)
- [ ] Create directory structure (src, tests, scripts)
- [ ] Create complete pyproject.toml (compare with existing packages)
- [ ] Include `[tool.hatch.build]` with `dev-mode-dirs = ["src"]`
- [ ] Start with clean slate (no test ignores initially)
- [ ] Copy/move source code
- [ ] Update imports
- [ ] Create `__init__.py` with exports
- [ ] Copy script templates
- [ ] Make scripts executable

### Workspace Integration
- [ ] Add to `[tool.uv.workspace.members]`
- [ ] Add to `[tool.uv.sources]`
- [ ] Run `uv sync --package <name>`
- [ ] Verify import

### Script Updates
- [ ] Update `scripts/lint.sh`
- [ ] Update `scripts/format.sh`
- [ ] Update `scripts/type-check.sh`
- [ ] Update `scripts/pre-commit-lint.sh`
- [ ] Update `scripts/pre-commit-format.sh`
- [ ] Update `scripts/pre-commit-type-check.sh`

### Quality Checks
- [ ] Run package tests
- [ ] Run `./scripts/dev-checks.sh`
- [ ] Group errors by category
- [ ] Fix mechanical errors
- [ ] Add minimal ignores (S101)
- [ ] Verify all checks pass
- [ ] Track test count

### Documentation
- [ ] Update CLAUDE.md
- [ ] Update migration docs
- [ ] Create package README
- [ ] Update dependency docs

---

## Lessons Learned Reference

See Phase 4 MySQL extraction plan (lines 848-1015) for detailed lessons learned:

1. **pyproject.toml Configuration** - Always compare with existing packages
2. **uv Workspace Installation** - Use `uv sync --package <name>` for new packages
3. **Root Script Updates** - ALWAYS update all 6 workspace scripts
4. **Linting Error Analysis** - Run dev-checks and analyse systematically
5. **BDD-Style Docstrings** - Preserve GIVEN-WHEN-THEN with proper formatting
6. **Test Count Tracking** - Verify completeness via test count increases
7. **Package Ordering** - Process in dependency order

---

## Notes

- This template is based on the successful Phase 4 MySQL extraction
- Customise phases as needed for your specific extraction
- Not all phases may be required (e.g., shared package creation)
- Follow dependency order when updating scripts
- Always run dev-checks after each major step
- Track test counts to verify completeness
