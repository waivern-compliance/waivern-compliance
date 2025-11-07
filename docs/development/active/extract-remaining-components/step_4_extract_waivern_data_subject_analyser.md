# Step 4: Extract waivern-data-subject-analyser

**Phase:** 3 - Independent Analyser
**Complexity:** 🟡 Medium
**Risk:** 🟢 Low
**Dependencies:** waivern-core, waivern-llm, waivern-analysers-shared, waivern-rulesets
**Needed By:** None

---

## Purpose

Extract the DataSubjectAnalyser from waivern-community into a standalone `waivern-data-subject-analyser` package. This analyser identifies data subjects (whose personal data is being processed) in content using pattern matching and LLM validation.

---

## Context

The DataSubjectAnalyser depends only on already-extracted shared packages (waivern-llm, waivern-analysers-shared, waivern-rulesets). It has no dependencies on other waivern-community components, making it suitable for extraction in Phase 3.

**Current location:** `libs/waivern-community/src/waivern_community/analysers/data_subject_analyser/`
**Size:** 743 LOC source + 716 LOC tests
**Test files:** 6 test files
**Schemas:** ✅ Yes - `data_subject_finding/1.0.0` custom schema

---

## Component Variables

```bash
PACKAGE_NAME="waivern-data-subject-analyser"
PACKAGE_MODULE="waivern_data_subject_analyser"
COMPONENT_TYPE="analyser"
COMPONENT_NAME="DataSubjectAnalyser"
CONFIG_NAME="DataSubjectAnalyserConfig"
SCHEMA_NAME="DataSubjectFindingSchema"
DESCRIPTION="Data subject analyser for WCF"
SHARED_PACKAGE="waivern-analysers-shared"
CURRENT_LOCATION="analysers/data_subject_analyser/"
TEST_COUNT="~6"
```

---

## Implementation Steps

Follow the [Component Extraction Template](../../guides/component-extraction-template.md) with these specific variables.

### 1. Create Package Structure

```bash
mkdir -p libs/waivern-data-subject-analyser/src/waivern_data_subject_analyser
mkdir -p libs/waivern-data-subject-analyser/tests/waivern_data_subject_analyser
mkdir -p libs/waivern-data-subject-analyser/scripts

# Create py.typed marker
touch libs/waivern-data-subject-analyser/src/waivern_data_subject_analyser/py.typed
```

### 2. Copy Package Scripts

```bash
cp libs/waivern-core/scripts/*.sh libs/waivern-data-subject-analyser/scripts/
chmod +x libs/waivern-data-subject-analyser/scripts/*.sh
```

### 3. Create pyproject.toml

```toml
[project]
name = "waivern-data-subject-analyser"
version = "0.1.0"
description = "Data subject analyser for WCF"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "waivern-llm",
    "waivern-analysers-shared",
    "waivern-rulesets",
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

# Include JSON schemas and py.typed
include = [
    "src/waivern_data_subject_analyser/py.typed",
    "src/waivern_data_subject_analyser/**/schemas/json_schemas/**/*.json",
]

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_data_subject_analyser"]

# Component discovery via entry points
[project.entry-points."waivern.analysers"]
data_subject = "waivern_data_subject_analyser:DataSubjectAnalyserFactory"

[project.entry-points."waivern.schemas"]
data_subject = "waivern_data_subject_analyser:register_schemas"

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
# waivern-data-subject-analyser

Data subject analyser for WCF

## Overview

The Data Subject analyser identifies data subjects (individuals or groups whose personal data is being processed) in content using pattern matching and optional LLM validation.

Key features:
- Pattern-based data subject identification using rulesets
- LLM validation for improved accuracy
- Confidence scoring
- Evidence extraction with context

## Installation

\```bash
pip install waivern-data-subject-analyser
\```

## Usage

\```python
from waivern_data_subject_analyser import (
    DataSubjectAnalyser,
    DataSubjectAnalyserConfig,
)

# Create analyser with LLM validation
config = DataSubjectAnalyserConfig(
    pattern_matching={"ruleset": "data_subjects"},
    llm_validation={"enable_llm_validation": True}
)
analyser = DataSubjectAnalyser(config)

# Process data
messages = analyser.process_data(input_message)
\```

## Development

See [CLAUDE.md](../../CLAUDE.md) for development guidelines.
```

### 5. Copy Component Code

```bash
cp -r libs/waivern-community/src/waivern_community/analysers/data_subject_analyser/* \
      libs/waivern-data-subject-analyser/src/waivern_data_subject_analyser/
```

### 6. Update Imports

Verify imports use shared packages (should already be correct):

```python
from waivern_core import Analyser, Message, Schema
from waivern_llm import BaseLLMService
from waivern_analysers_shared import (
    EvidenceExtractor,
    RulesetManager,
    PatternMatchingConfig,
)
from waivern_rulesets import DataSubjectsRuleset
```

No waivern-community internal imports to update (component is self-contained).

### 7. Package Exports with Schema Registration

**CRITICAL:** Create `src/waivern_data_subject_analyser/__init__.py` with explicit schema registration:

```python
"""Data subject analyser for WCF."""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .analyser import DataSubjectAnalyser
from .factory import DataSubjectAnalyserFactory
from .schemas import DataSubjectFindingModel
from .types import DataSubjectAnalyserConfig


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation via entry point.
    This function is referenced in pyproject.toml [project.entry-points."waivern.schemas"].

    NO import-time side effects - registration is explicit and controlled.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "DataSubjectAnalyser",
    "DataSubjectAnalyserConfig",
    "DataSubjectAnalyserFactory",
    "DataSubjectFindingModel",
    "register_schemas",
]
```

**Key Points:**
- `register_schemas()` is called by WCT Executor via entry point, NOT at import time
- Uses `importlib.resources.files()` for proper resource location in installed packages
- Entry point system allows WCT to discover and register all schemas before loading components

### 8. Move Tests

```bash
mv libs/waivern-community/tests/waivern_community/analysers/data_subject_analyser/* \
   libs/waivern-data-subject-analyser/tests/waivern_data_subject_analyser/
```

Update test imports:
```python
# Before
from waivern_community.analysers.data_subject_analyser import DataSubjectAnalyser
from waivern_community.analysers.data_subject_analyser.schemas import DataSubjectFindingModel

# After
from waivern_data_subject_analyser import DataSubjectAnalyser, DataSubjectFindingModel
```

### 9. Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.sources]
# ... existing sources ...
waivern-data-subject-analyser = { workspace = true }  # ADD THIS
```

### 10. Install and Test Package

```bash
# Install package
uv sync --package waivern-data-subject-analyser

# Verify installation
uv run python -c "import waivern_data_subject_analyser; print('✓ Package installed')"

# Verify entry point registration
uv run python -c "from importlib.metadata import entry_points; eps = entry_points(group='waivern.analysers'); assert any(ep.name == 'data_subject' for ep in eps); print('✓ Analyser entry point registered')"
uv run python -c "from importlib.metadata import entry_points; eps = entry_points(group='waivern.schemas'); assert any(ep.name == 'data_subject' for ep in eps); print('✓ Schema entry point registered')"

# Verify schema registration via entry point
uv run python -c "from waivern_data_subject_analyser import register_schemas; from waivern_core.schemas import SchemaRegistry; register_schemas(); s = SchemaRegistry.get_schema('data_subject_finding', '1.0.0'); print('✓ Schema registration works')"

# Run package tests
cd libs/waivern-data-subject-analyser
uv run pytest tests/ -v
# Expected: ~6 tests passing
```

### 11. Run Package Quality Checks

```bash
cd libs/waivern-data-subject-analyser
./scripts/format.sh
./scripts/lint.sh
./scripts/type-check.sh
```

### 12. Update waivern-community

**Update `libs/waivern-community/pyproject.toml`:**

Remove entry points (component is now standalone):
```toml
# REMOVE these entry points:
[project.entry-points."waivern.analysers"]
# data_subject = "waivern_community.analysers.data_subject_analyser:DataSubjectAnalyserFactory"  # REMOVE

[project.entry-points."waivern.schemas"]
# data_subject = "waivern_community.analysers.data_subject_analyser:register_schemas"  # REMOVE
```

Add dependency:
```toml
dependencies = [
    "waivern-core",
    # ... other dependencies
    "waivern-data-subject-analyser",  # ADD THIS
    # ... rest
]
```

**Update `libs/waivern-community/src/waivern_community/analysers/__init__.py`:**
```python
"""WCT analysers."""

from waivern_core import Analyser, AnalyserError

# Import from standalone packages
from waivern_data_subject_analyser import DataSubjectAnalyser  # ADD THIS
from waivern_personal_data_analyser import PersonalDataAnalyser

# Import from waivern_community
from waivern_community.analysers.processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
)

__all__ = (
    "Analyser",
    "AnalyserError",
    "DataSubjectAnalyser",  # ADD THIS
    "PersonalDataAnalyser",
    "ProcessingPurposeAnalyser",
    "BUILTIN_ANALYSERS",
)

BUILTIN_ANALYSERS = (
    DataSubjectAnalyser,  # ADD THIS
    PersonalDataAnalyser,
    ProcessingPurposeAnalyser,
)
```

### 13. Delete Extracted Code

```bash
rm -rf libs/waivern-community/src/waivern_community/analysers/data_subject_analyser
rm -rf libs/waivern-community/tests/waivern_community/analysers/data_subject_analyser
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
cd libs/waivern-data-subject-analyser
uv run pytest tests/ -v
```

**Expected:** All ~6 tests passing

### Schema Tests

```bash
# Verify schema is discoverable
uv run python -c "
from waivern_core.schemas import SchemaRegistry
schema = SchemaRegistry.get_schema('data_subject_finding', '1.0.0')
print(f'✓ Schema found: {schema.name} v{schema.version}')
"

# Verify schema models work
uv run python -c "
from waivern_data_subject_analyser import DataSubjectFindingModel
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
uv run wct ls-analysers | grep data-subject

# Verify ruleset integration
uv run python -c "
from waivern_rulesets import RulesetLoader
ruleset = RulesetLoader.load_ruleset('data_subjects')
print(f'✓ Ruleset loaded: {len(ruleset.rules)} rules')
"
```

---

## Success Criteria

- [ ] waivern-data-subject-analyser package created with correct structure
- [ ] All 6 package tests passing
- [ ] Schema registration working (data_subject_finding/1.0.0 discoverable)
- [ ] Package quality checks passing (lint, format, type-check)
- [ ] waivern-community updated to import from waivern-data-subject-analyser
- [ ] waivern-community tests passing
- [ ] All workspace tests passing
- [ ] Component discoverable via `wct ls-analysers`
- [ ] data_subjects ruleset loads successfully
- [ ] Changes committed with message: `refactor: extract DataSubjectAnalyser as standalone package`

---

## Decisions Made

1. **Custom schema:** data_subject_finding/1.0.0 schema with Pydantic models included
2. **Schema registration:** Added SchemaRegistry.register_search_path() in __init__.py
3. **Shared dependencies:** Uses waivern-analysers-shared for common utilities
4. **Ruleset integration:** Uses data_subjects ruleset from waivern-rulesets
5. **Include directive:** Added to distribute JSON schemas and py.typed
6. **Test environment relaxation:** Added basedpyright executionEnvironments for tests
7. **LLM integration:** Depends on waivern-llm for optional LLM validation

---

## Notes

- This analyser is independent - no internal waivern-community dependencies
- Can be extracted in parallel with Steps 1-3 if desired
- Uses "data_subjects" ruleset from waivern-rulesets
- Schema registration is CRITICAL - must happen before component class imports
- DataSubjectAnalyser will be re-exported from waivern-community for backward compatibility
