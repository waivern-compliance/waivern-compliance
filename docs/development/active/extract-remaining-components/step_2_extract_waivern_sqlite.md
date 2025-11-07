# Step 2: Extract waivern-sqlite ✅

**Status:** ✅ COMPLETED (Commit: 1e17b9b)

**Phase:** 1 - Independent Connectors
**Complexity:** 🟢 Low
**Risk:** 🟢 Low
**Dependencies:** waivern-core, waivern-connectors-database
**Needed By:** None

---

## Purpose

Extract the SQLiteConnector from waivern-community into a standalone `waivern-sqlite` package. This connector extracts database schema and data from SQLite databases and produces standard_input schema data.

---

## Context

The SQLiteConnector depends on the already-extracted `waivern-connectors-database` shared package for database utilities. It has no dependencies on other waivern-community components.

**Current location:** `libs/waivern-community/src/waivern_community/connectors/sqlite/`
**Size:** ~560 LOC across 6 files
**Tests:** ~6 test files
**Schemas:** No custom schemas (produces `standard_input/1.0.0`)

---

## Component Variables

```bash
PACKAGE_NAME="waivern-sqlite"
PACKAGE_MODULE="waivern_sqlite"
COMPONENT_TYPE="connector"
COMPONENT_NAME="SQLiteConnector"
CONFIG_NAME="SQLiteConnectorConfig"
SCHEMA_NAME="N/A"  # Uses standard_input schema from waivern-core
DESCRIPTION="SQLite connector for WCF"
SHARED_PACKAGE="waivern-connectors-database"
CURRENT_LOCATION="connectors/sqlite/"
TEST_COUNT="~6"
```

---

## Implementation Steps

Follow the [Component Extraction Template](../../guides/component-extraction-template.md) with these specific variables.

### 1. Create Package Structure

```bash
mkdir -p libs/waivern-sqlite/src/waivern_sqlite
mkdir -p libs/waivern-sqlite/tests/waivern_sqlite
mkdir -p libs/waivern-sqlite/scripts

# Create py.typed marker
touch libs/waivern-sqlite/src/waivern_sqlite/py.typed
```

### 2. Copy Package Scripts

```bash
cp libs/waivern-core/scripts/*.sh libs/waivern-sqlite/scripts/
chmod +x libs/waivern-sqlite/scripts/*.sh
```

### 3. Create pyproject.toml

```toml
[project]
name = "waivern-sqlite"
version = "0.1.0"
description = "SQLite connector for WCF"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "waivern-connectors-database",
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

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_sqlite"]

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
# waivern-sqlite

SQLite connector for WCF

## Overview

The SQLite connector extracts database schema and data from SQLite databases for compliance analysis. It uses the shared database utilities from waivern-connectors-database.

Key features:
- Extract database schema (tables, columns, types)
- Extract sample data for analysis
- Configurable data sampling
- Supports SQLite 3.x databases

## Installation

\```bash
pip install waivern-sqlite
\```

## Usage

\```python
from waivern_sqlite import SQLiteConnector, SQLiteConnectorConfig

# Extract from SQLite database
config = SQLiteConnectorConfig(
    database="/path/to/database.db",
    sample_size=100
)
connector = SQLiteConnector(config)
messages = connector.extract()
\```

```

### 5. Copy Component Code

```bash
cp -r libs/waivern-community/src/waivern_community/connectors/sqlite/* \
      libs/waivern-sqlite/src/waivern_sqlite/
```

### 6. Update Imports

Update imports from waivern-community.connectors.database to waivern-connectors-database:

```python
# Before:
from waivern_community.connectors.database import (
    DatabaseConnector,
    DatabaseExtractionUtils,
    DatabaseSchemaUtils,
)

# After:
from waivern_connectors_database import (
    DatabaseConnector,
    DatabaseExtractionUtils,
    DatabaseSchemaUtils,
)
```

**Files to update:**
- `connector.py`
- Any other files importing from `waivern_community.connectors.database`

### 7. Package Exports

Create `src/waivern_sqlite/__init__.py`:

```python
"""SQLite connector for WCF."""

from .config import SQLiteConnectorConfig
from .connector import SQLiteConnector
from .factory import SQLiteConnectorFactory

__all__ = [
    "SQLiteConnector",
    "SQLiteConnectorConfig",
    "SQLiteConnectorFactory",
]
```

### 8. Move Tests

```bash
mv libs/waivern-community/tests/waivern_community/connectors/sqlite/* \
   libs/waivern-sqlite/tests/waivern_sqlite/
```

Update test imports:
```python
# Before
from waivern_community.connectors.sqlite import SQLiteConnector

# After
from waivern_sqlite import SQLiteConnector
```

### 9. Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.sources]
# ... existing sources ...
waivern-sqlite = { workspace = true }  # ADD THIS
```

### 10. Install and Test Package

```bash
# Install package
uv sync --package waivern-sqlite

# Verify installation
uv run python -c "import waivern_sqlite; print('✓ Package installed')"

# Run package tests
cd libs/waivern-sqlite
uv run pytest tests/ -v
# Expected: ~6 tests passing
```

### 11. Run Package Quality Checks

```bash
cd libs/waivern-sqlite
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
    "waivern-sqlite",  # ADD THIS
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
from waivern_sqlite import SQLiteConnector  # ADD THIS

# Import from waivern_community
from waivern_community.connectors.source_code import SourceCodeConnector

__all__ = (
    "Connector",
    "ConnectorError",
    "FilesystemConnector",
    "MySQLConnector",
    "SourceCodeConnector",
    "SQLiteConnector",  # ADD THIS
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (
    FilesystemConnector,
    MySQLConnector,
    SourceCodeConnector,
    SQLiteConnector,  # ADD THIS
)
```

### 13. Delete Extracted Code

```bash
rm -rf libs/waivern-community/src/waivern_community/connectors/sqlite
rm -rf libs/waivern-community/tests/waivern_community/connectors/sqlite
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
cd libs/waivern-sqlite
uv run pytest tests/ -v
```

**Expected:** All ~6 tests passing

### Workspace-Level Tests

```bash
uv run pytest
./scripts/dev-checks.sh
```

**Expected:** All workspace tests passing

### Integration Tests

```bash
# Verify component is discoverable
uv run wct ls-connectors | grep sqlite

# Test with LAMP stack runbook (uses SQLite)
uv run wct validate-runbook apps/wct/runbooks/samples/LAMP_stack.yaml
```

---

## Success Criteria

- [ ] waivern-sqlite package created with correct structure
- [ ] All 6 package tests passing
- [ ] Package quality checks passing (lint, format, type-check)
- [ ] waivern-community updated to import from waivern-sqlite
- [ ] waivern-community tests passing
- [ ] All workspace tests passing
- [ ] Component discoverable via `wct ls-connectors`
- [ ] LAMP_stack.yaml runbook validates successfully
- [ ] Changes committed with message: `refactor: extract SQLiteConnector as standalone package`

---

## Decisions Made

1. **Shared database utilities:** Uses waivern-connectors-database for database operations
2. **No custom schemas:** SQLiteConnector uses `standard_input/1.0.0` from waivern-core
3. **Test environment relaxation:** Added basedpyright executionEnvironments for tests
4. **No include directive:** Package only contains .py files
5. **Import updates:** Changed waivern_community.connectors.database → waivern_connectors_database

---

## Notes

- SQLiteConnector depends on waivern-connectors-database (already extracted)
- Standard library sqlite3 is used, no external database driver needed
- After this step, both Phase 1 connectors are complete
- SQLiteConnector will be re-exported from waivern-community for backward compatibility
