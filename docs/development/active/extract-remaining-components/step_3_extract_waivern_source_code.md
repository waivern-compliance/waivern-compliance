# Step 3: Extract waivern-source-code ✅

**Status:** ✅ COMPLETED (Commit: df14915)

**Phase:** 2 - Source Code Connector
**Complexity:** 🟡 Medium
**Risk:** 🟡 Medium
**Dependencies:** waivern-core, waivern-filesystem (Step 1)
**Needed By:** waivern-processing-purpose-analyser (Step 5)

---

## Purpose

Extract the SourceCodeConnector from waivern-community into a standalone `waivern-source-code` package. This connector parses source code files (PHP) using tree-sitter and produces structured source code data.

---

## Context

The SourceCodeConnector depends on FilesystemConnector (extracted in Step 1) for file collection. It has a custom schema (`source_code/1.0.0`) and optional tree-sitter dependencies for PHP parsing. The ProcessingPurposeAnalyser (Step 5) depends on this package's schemas.

**Current location:** `libs/waivern-community/src/waivern_community/connectors/source_code/`
**Size:** ~1,658 LOC across 13 files
**Tests:** ~7 test files
**Schemas:** ✅ Yes - `source_code/1.0.0` custom schema

---

## Component Variables

```bash
PACKAGE_NAME="waivern-source-code"
PACKAGE_MODULE="waivern_source_code"
COMPONENT_TYPE="connector"
COMPONENT_NAME="SourceCodeConnector"
CONFIG_NAME="SourceCodeConnectorConfig"
SCHEMA_NAME="SourceCodeSchema"
DESCRIPTION="Source code connector for WCF"
SHARED_PACKAGE="N/A"
CURRENT_LOCATION="connectors/source_code/"
TEST_COUNT="~7"
```

---

## Implementation Steps

Follow the [Component Extraction Template](../../guides/component-extraction-template.md) with these specific variables.

### 1. Create Package Structure

```bash
mkdir -p libs/waivern-source-code/src/waivern_source_code
mkdir -p libs/waivern-source-code/tests/waivern_source_code
mkdir -p libs/waivern-source-code/scripts

# Create py.typed marker
touch libs/waivern-source-code/src/waivern_source_code/py.typed
```

### 2. Copy Package Scripts

```bash
cp libs/waivern-core/scripts/*.sh libs/waivern-source-code/scripts/
chmod +x libs/waivern-source-code/scripts/*.sh
```

### 3. Create pyproject.toml

```toml
[project]
name = "waivern-source-code"
version = "0.1.0"
description = "Source code connector for WCF"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "waivern-filesystem",
    "pydantic>=2.11.5",
]

[project.optional-dependencies]
tree-sitter = [
    "tree-sitter>=0.21.0",
    "tree-sitter-php>=0.22.0",
]
all = ["waivern-source-code[tree-sitter]"]

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

# Include JSON schemas and py.typed
include = [
    "src/waivern_source_code/py.typed",
    "src/waivern_source_code/**/schemas/json_schemas/**/*.json",
]

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_source_code"]

[tool.basedpyright]
typeCheckingMode = "strict"
reportImplicitOverride = "error"

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
    "D203",    # one-blank-line-before-class
    "D213",    # multi-line-summary-second-line
]

[tool.ruff.lint.pydocstyle]
ignore-decorators = ["typing.overload"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "ANN",     # Type annotations - not required in tests
    "B",       # flake8-bugbear - less strict in tests
    "D",       # Documentation - docstrings not required in tests
    "S101",    # Use of assert detected
    "PLC0415", # Import outside top-level
    "PLR2004", # Magic value comparison
]
```

### 4. Create README.md

```markdown
# waivern-source-code

Source code connector for WCF

## Overview

The Source Code connector parses source code files (currently PHP) using tree-sitter and extracts structured information about functions, classes, and code patterns for compliance analysis.

Key features:
- PHP source code parsing via tree-sitter
- Function and class extraction
- Code structure analysis
- Integrates with filesystem connector for file collection

## Installation

Basic installation:
\```bash
pip install waivern-source-code
\```

With tree-sitter support for PHP parsing:
\```bash
pip install waivern-source-code[tree-sitter]
\```

## Usage

\```python
from waivern_source_code import SourceCodeConnector, SourceCodeConnectorConfig

# Parse PHP files in a directory
config = SourceCodeConnectorConfig(
    path="/path/to/source",
    language="php",
    pattern="*.php"
)
connector = SourceCodeConnector(config)
messages = connector.extract()
\```

```

### 5. Copy Component Code

```bash
cp -r libs/waivern-community/src/waivern_community/connectors/source_code/* \
      libs/waivern-source-code/src/waivern_source_code/
```

### 6. Update Imports

**CRITICAL:** Update imports from waivern-community to waivern-filesystem:

```python
# Before:
from waivern_community.connectors.filesystem import (
    FilesystemConnector,
    FilesystemConnectorConfig,
)

# After:
from waivern_filesystem import (
    FilesystemConnector,
    FilesystemConnectorConfig,
)
```

**Files to update:**
- `connector.py` (main usage of FilesystemConnector)
- Any other files importing from `waivern_community.connectors.filesystem`

### 7. Package Exports with Schema Registration

**CRITICAL:** Create `src/waivern_source_code/__init__.py` with schema registration:

```python
"""Source code connector for WCF."""

from pathlib import Path

from waivern_core.schemas import SchemaRegistry

# IMPORTANT: Register schema directory BEFORE importing component classes
_SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
SchemaRegistry.register_search_path(_SCHEMA_DIR)

from .config import SourceCodeConnectorConfig
from .connector import SourceCodeConnector
from .factory import SourceCodeConnectorFactory
from .schemas import SourceCodeDataModel, FunctionModel, ClassModel

__all__ = [
    "SourceCodeConnector",
    "SourceCodeConnectorConfig",
    "SourceCodeConnectorFactory",
    "SourceCodeDataModel",
    "FunctionModel",
    "ClassModel",
]
```

### 8. Move Tests

```bash
mv libs/waivern-community/tests/waivern_community/connectors/source_code/* \
   libs/waivern-source-code/tests/waivern_source_code/
```

Update test imports:
```python
# Before
from waivern_community.connectors.source_code import SourceCodeConnector
from waivern_community.connectors.source_code.schemas import SourceCodeDataModel

# After
from waivern_source_code import SourceCodeConnector, SourceCodeDataModel
```

### 9. Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.sources]
# ... existing sources ...
waivern-source-code = { workspace = true }  # ADD THIS
```

### 10. Install and Test Package

```bash
# Install package with optional tree-sitter dependencies
uv sync --package waivern-source-code --extra tree-sitter

# Verify installation
uv run python -c "import waivern_source_code; print('✓ Package installed')"

# Verify schema registration
uv run python -c "from waivern_core.schemas import SchemaRegistry; s = SchemaRegistry.get_schema('source_code', '1.0.0'); print('✓ Schema registered')"

# Run package tests
cd libs/waivern-source-code
uv run pytest tests/ -v
# Expected: ~7 tests passing
```

### 11. Run Package Quality Checks

```bash
cd libs/waivern-source-code
./scripts/format.sh
./scripts/lint.sh
./scripts/type-check.sh
```

### 12. Update waivern-community

**Update `libs/waivern-community/pyproject.toml`:**
```toml
dependencies = [
    "waivern-core",
    # ... other dependencies
    "waivern-source-code",  # ADD THIS (with optional dependencies)
    # ... rest
]
```

**Update `libs/waivern-community/src/waivern_community/connectors/__init__.py`:**
```python
"""WCT connectors."""

from waivern_core import Connector, ConnectorError

# Import from standalone packages
from waivern_filesystem import FilesystemConnector
from waivern_mysql import MySQLConnector
from waivern_source_code import SourceCodeConnector  # ADD THIS
from waivern_sqlite import SQLiteConnector

__all__ = (
    "Connector",
    "ConnectorError",
    "FilesystemConnector",
    "MySQLConnector",
    "SourceCodeConnector",  # ADD THIS
    "SQLiteConnector",
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (
    FilesystemConnector,
    MySQLConnector,
    SourceCodeConnector,  # ADD THIS
    SQLiteConnector,
)
```

### 13. Delete Extracted Code

```bash
rm -rf libs/waivern-community/src/waivern_community/connectors/source_code
rm -rf libs/waivern-community/tests/waivern_community/connectors/source_code
```

### 14. Run Full Workspace Checks

```bash
uv sync
./scripts/dev-checks.sh
```

---

## Testing

### Package-Level Tests

```bash
cd libs/waivern-source-code
uv run pytest tests/ -v
```

**Expected:** All ~7 tests passing

### Schema Tests

```bash
# Verify schema is discoverable
uv run python -c "
from waivern_core.schemas import SchemaRegistry
schema = SchemaRegistry.get_schema('source_code', '1.0.0')
print(f'✓ Schema found: {schema.name} v{schema.version}')
"

# Verify schema models work
uv run python -c "
from waivern_source_code import SourceCodeDataModel, FunctionModel
print('✓ Schema models importable')
"
```

### Workspace-Level Tests

```bash
uv run pytest
./scripts/dev-checks.sh
```

**Expected:** All workspace tests passing

### Integration Tests

```bash
# Verify component is discoverable
uv run wct ls-connectors | grep source

# Test with LAMP stack runbook (uses source code connector)
uv run wct validate-runbook apps/wct/runbooks/samples/LAMP_stack.yaml
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v
```

---

## Success Criteria

- [ ] waivern-source-code package created with correct structure
- [ ] All 7 package tests passing
- [ ] Schema registration working (source_code/1.0.0 discoverable)
- [ ] Package quality checks passing (lint, format, type-check)
- [ ] waivern-community updated to import from waivern-source-code
- [ ] waivern-community tests passing
- [ ] All workspace tests passing
- [ ] Component discoverable via `wct ls-connectors`
- [ ] LAMP_stack.yaml runbook validates and runs successfully
- [ ] Changes committed with message: `refactor: extract SourceCodeConnector as standalone package`

---

## Decisions Made

1. **Custom schema:** source_code/1.0.0 schema with Pydantic models included
2. **Schema registration:** Added SchemaRegistry.register_search_path() in __init__.py
3. **Optional dependencies:** tree-sitter and tree-sitter-php are optional extras
4. **Include directive:** Added to distribute JSON schemas and py.typed
5. **Import updates:** Changed waivern_community.connectors.filesystem → waivern_filesystem
6. **Test environment relaxation:** Added basedpyright executionEnvironments for tests
7. **Export schema models:** SourceCodeDataModel, FunctionModel, ClassModel exported for use by analysers

---

## Notes

- This connector depends on waivern-filesystem (Step 1) - ensure Step 1 is complete first
- Optional tree-sitter dependencies allow parsing but aren't required for basic operation
- The source_code schema is used by ProcessingPurposeAnalyser (Step 5)
- Schema registration is CRITICAL - must happen before component class imports
- After this step, ProcessingPurposeAnalyser (Step 5) can proceed
- SourceCodeConnector will be re-exported from waivern-community for backward compatibility
