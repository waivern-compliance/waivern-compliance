# Step 1: Extract waivern-filesystem ✅

**Status:** ✅ COMPLETED (Commit: 7eab880)

**Phase:** 1 - Independent Connectors
**Complexity:** 🟢 Low
**Risk:** 🟢 Low
**Dependencies:** None (only waivern-core)
**Needed By:** waivern-source-code (Step 3)

---

## Purpose

Extract the FilesystemConnector from waivern-community into a standalone `waivern-filesystem` package. This connector reads file contents from the filesystem and produces standard_input schema data.

---

## Context

The FilesystemConnector is self-contained with no dependencies on other waivern-community components. It only depends on waivern-core, making it an ideal first extraction candidate. The source_code connector (Step 3) depends on this package, so it must be extracted first.

**Current location:** `libs/waivern-community/src/waivern_community/connectors/filesystem/`
**Size:** ~604 LOC across 6 files
**Tests:** ~6 test files
**Schemas:** No custom schemas (produces `standard_input/1.0.0`)

---

## Component Variables

```bash
PACKAGE_NAME="waivern-filesystem"
PACKAGE_MODULE="waivern_filesystem"
COMPONENT_TYPE="connector"
COMPONENT_NAME="FilesystemConnector"
CONFIG_NAME="FilesystemConnectorConfig"
SCHEMA_NAME="N/A"  # Uses standard_input schema from waivern-core
DESCRIPTION="Filesystem connector for WCF"
SHARED_PACKAGE="N/A"
CURRENT_LOCATION="connectors/filesystem/"
TEST_COUNT="~6"
```

---

## Implementation Steps

Follow the [Component Extraction Template](../../guides/component-extraction-template.md) with these specific variables.

### 1. Create Package Structure

```bash
mkdir -p libs/waivern-filesystem/src/waivern_filesystem
mkdir -p libs/waivern-filesystem/tests/waivern_filesystem
mkdir -p libs/waivern-filesystem/scripts

# Create py.typed marker
touch libs/waivern-filesystem/src/waivern_filesystem/py.typed
```

### 2. Copy Package Scripts

```bash
cp libs/waivern-core/scripts/*.sh libs/waivern-filesystem/scripts/
chmod +x libs/waivern-filesystem/scripts/*.sh
```

### 3. Create pyproject.toml

```toml
[project]
name = "waivern-filesystem"
version = "0.1.0"
description = "Filesystem connector for WCF"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
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
packages = ["src/waivern_filesystem"]

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
# waivern-filesystem

Filesystem connector for WCF

## Overview

The Filesystem connector reads file contents from the filesystem and produces standardised data for compliance analysis. It supports single file reading and directory traversal with pattern matching.

Key features:
- Read single files or entire directories
- Glob pattern support for file filtering
- Automatic encoding detection
- Binary file handling

## Installation

\```bash
pip install waivern-filesystem
\```

## Usage

\```python
from waivern_filesystem import FilesystemConnector, FilesystemConnectorConfig

# Read a single file
config = FilesystemConnectorConfig(path="/path/to/file.txt")
connector = FilesystemConnector(config)
messages = connector.extract()

# Read directory with pattern
config = FilesystemConnectorConfig(
    path="/path/to/directory",
    pattern="*.py"
)
connector = FilesystemConnector(config)
messages = connector.extract()
\```

```

### 5. Copy Component Code

```bash
cp -r libs/waivern-community/src/waivern_community/connectors/filesystem/* \
      libs/waivern-filesystem/src/waivern_filesystem/
```

### 6. Update Imports

No waivern-community internal imports to update (component is self-contained).

Verify all imports use `waivern_core` only:
```python
from waivern_core import Connector, ConnectorConfig, Message, Schema
```

### 7. Package Exports

Create `src/waivern_filesystem/__init__.py`:

```python
"""Filesystem connector for WCF."""

from .config import FilesystemConnectorConfig
from .connector import FilesystemConnector
from .factory import FilesystemConnectorFactory

__all__ = [
    "FilesystemConnector",
    "FilesystemConnectorConfig",
    "FilesystemConnectorFactory",
]
```

### 8. Move Tests

```bash
mv libs/waivern-community/tests/waivern_community/connectors/filesystem/* \
   libs/waivern-filesystem/tests/waivern_filesystem/
```

Update test imports:
```python
# Before
from waivern_community.connectors.filesystem import FilesystemConnector

# After
from waivern_filesystem import FilesystemConnector
```

### 9. Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.sources]
# ... existing sources ...
waivern-filesystem = { workspace = true }  # ADD THIS
```

### 10. Install and Test Package

```bash
# Install package
uv sync --package waivern-filesystem

# Verify installation
uv run python -c "import waivern_filesystem; print('✓ Package installed')"

# Run package tests
cd libs/waivern-filesystem
uv run pytest tests/ -v
# Expected: ~6 tests passing
```

### 11. Run Package Quality Checks

```bash
cd libs/waivern-filesystem
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
    "waivern-filesystem",  # ADD THIS
    # ... rest
]
```

**Update `libs/waivern-community/src/waivern_community/connectors/__init__.py`:**
```python
"""WCT connectors."""

from waivern_core import Connector, ConnectorError

# Import from standalone packages
from waivern_filesystem import FilesystemConnector  # ADD THIS
from waivern_mysql import MySQLConnector

# Import from waivern_community
from waivern_community.connectors.source_code import SourceCodeConnector
from waivern_community.connectors.sqlite import SQLiteConnector

__all__ = (
    "Connector",
    "ConnectorError",
    "FilesystemConnector",  # ADD THIS
    "MySQLConnector",
    "SourceCodeConnector",
    "SQLiteConnector",
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (
    FilesystemConnector,  # ADD THIS
    MySQLConnector,
    SourceCodeConnector,
    SQLiteConnector,
)
```

### 13. Delete Extracted Code

```bash
rm -rf libs/waivern-community/src/waivern_community/connectors/filesystem
rm -rf libs/waivern-community/tests/waivern_community/connectors/filesystem
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
cd libs/waivern-filesystem
uv run pytest tests/ -v
```

**Expected:** All ~6 tests passing

### Workspace-Level Tests

```bash
uv run pytest
./scripts/dev-checks.sh
```

**Expected:** All workspace tests passing (including waivern-community re-export tests)

### Integration Tests

```bash
# Verify component is discoverable
uv run wct ls-connectors | grep filesystem

# Test with sample runbook if applicable
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v
```

---

## Success Criteria

- [ ] waivern-filesystem package created with correct structure
- [ ] All 6 package tests passing
- [ ] Package quality checks passing (lint, format, type-check)
- [ ] waivern-community updated to import from waivern-filesystem
- [ ] waivern-community tests passing
- [ ] All workspace tests passing
- [ ] Component discoverable via `wct ls-connectors`
- [ ] Sample runbooks using filesystem connector still work
- [ ] Changes committed with message: `refactor: extract FilesystemConnector as standalone package`

---

## Decisions Made

1. **No custom schemas:** FilesystemConnector uses `standard_input/1.0.0` from waivern-core, so no schema registration needed
2. **Test environment relaxation:** Added basedpyright executionEnvironments for tests (consistent with other packages)
3. **No include directive:** Package only contains .py files, so no `[tool.hatch.build] include` needed
4. **Comprehensive test ignores:** Using Pattern A for test file ignores (matches core library standards)

---

## Notes

- This is the first extraction, establishing the pattern for subsequent steps
- Component is self-contained with no internal dependencies
- After this step, waivern-source-code (Step 3) can proceed
- FilesystemConnector will be re-exported from waivern-community for backward compatibility
