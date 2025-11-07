# Step 5: Extract waivern-processing-purpose-analyser

**Phase:** 4 - Processing Purpose Analyser
**Complexity:** 🟠 High
**Risk:** 🟡 Medium
**Dependencies:** waivern-core, waivern-llm, waivern-analysers-shared, waivern-rulesets, waivern-source-code (Step 3)
**Needed By:** None

---

## Purpose

Extract the ProcessingPurposeAnalyser from waivern-community into a standalone `waivern-processing-purpose-analyser` package. This analyser identifies processing purposes (why personal data is being processed) in content using pattern matching and LLM validation. It supports both standard_input and source_code schemas.

---

## Context

The ProcessingPurposeAnalyser depends on waivern-source-code (Step 3) for source code schema support. It's the most complex analyser extraction because it:
- Has custom schema (`processing_purpose_finding/1.0.0`)
- Supports multiple input schemas (standard_input AND source_code)
- Has a separate prompts file that needs migration
- Uses both pattern matching and LLM validation

**Current location:** `libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser/`
**Prompts location:** `libs/waivern-community/src/waivern_community/prompts/processing_purpose_validation.py` (196 LOC + 1 test file)
**Size:** 1,231 LOC source + 3,081 LOC tests
**Test files:** 14 test files (includes integration tests and source code mocks)
**Schemas:** ✅ Yes - `processing_purpose_finding/1.0.0` custom schema

---

## Component Variables

```bash
PACKAGE_NAME="waivern-processing-purpose-analyser"
PACKAGE_MODULE="waivern_processing_purpose_analyser"
COMPONENT_TYPE="analyser"
COMPONENT_NAME="ProcessingPurposeAnalyser"
CONFIG_NAME="ProcessingPurposeAnalyserConfig"
SCHEMA_NAME="ProcessingPurposeFindingSchema"
DESCRIPTION="Processing purpose analyser for WCF"
SHARED_PACKAGE="waivern-analysers-shared"
CURRENT_LOCATION="analysers/processing_purpose_analyser/"
TEST_COUNT="~12"
```

---

## Implementation Steps

Follow the [Component Extraction Template](../../guides/component-extraction-template.md) with these specific variables.

### 1. Create Package Structure

```bash
mkdir -p libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser
mkdir -p libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/prompts
mkdir -p libs/waivern-processing-purpose-analyser/tests/waivern_processing_purpose_analyser
mkdir -p libs/waivern-processing-purpose-analyser/scripts

# Create py.typed marker
touch libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/py.typed
```

### 2. Copy Package Scripts

```bash
cp libs/waivern-core/scripts/*.sh libs/waivern-processing-purpose-analyser/scripts/
chmod +x libs/waivern-processing-purpose-analyser/scripts/*.sh
```

### 3. Create pyproject.toml

```toml
[project]
name = "waivern-processing-purpose-analyser"
version = "0.1.0"
description = "Processing purpose analyser for WCF"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "waivern-core",
    "waivern-llm",
    "waivern-analysers-shared",
    "waivern-rulesets",
    "waivern-source-code",  # For source code schema support
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
    "src/waivern_processing_purpose_analyser/py.typed",
    "src/waivern_processing_purpose_analyser/**/schemas/json_schemas/**/*.json",
]

[tool.hatch.build.targets.wheel]
packages = ["src/waivern_processing_purpose_analyser"]

# Component discovery via entry points
[project.entry-points."waivern.analysers"]
processing_purpose = "waivern_processing_purpose_analyser:ProcessingPurposeAnalyserFactory"

[project.entry-points."waivern.schemas"]
processing_purpose = "waivern_processing_purpose_analyser:register_schemas"

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
# waivern-processing-purpose-analyser

Processing purpose analyser for WCF

## Overview

The Processing Purpose analyser identifies processing purposes (the reasons why personal data is being processed) in content using pattern matching and optional LLM validation. It supports both standard text input and structured source code analysis.

Key features:
- Pattern-based processing purpose identification using rulesets
- LLM validation for improved accuracy
- Source code analysis support (PHP)
- Confidence scoring
- Evidence extraction with context

## Installation

\```bash
pip install waivern-processing-purpose-analyser
\```

## Usage

\```python
from waivern_processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeAnalyserConfig,
)

# Create analyser with LLM validation
config = ProcessingPurposeAnalyserConfig(
    pattern_matching={"ruleset": "processing_purposes"},
    llm_validation={"enable_llm_validation": True}
)
analyser = ProcessingPurposeAnalyser(config)

# Process standard input
messages = analyser.process_data(input_message)

# Or process source code
source_code_messages = analyser.process_data(source_code_message)
\```

## Development

See [CLAUDE.md](../../CLAUDE.md) for development guidelines.
```

### 5. Copy Component Code

```bash
# Copy analyser code
cp -r libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser/* \
      libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/

# Copy prompts file
cp libs/waivern-community/src/waivern_community/prompts/processing_purpose_validation.py \
   libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/prompts/
```

### 6. Update Imports

**CRITICAL:** Update imports from waivern-community to standalone packages:

```python
# Before:
from waivern_community.connectors.source_code.schemas import (
    SourceCodeDataModel,
    FunctionModel,
    ClassModel,
)

# After:
from waivern_source_code.schemas import (
    SourceCodeDataModel,
    FunctionModel,
    ClassModel,
)
```

**Files to update:**
- `analyser.py` - Main analyser file
- `source_code_schema_input_handler.py` - Source code input handler
- `schema_readers/source_code_1_0_0.py` - Source code schema reader
- Any other files importing from `waivern_community.connectors.source_code`

**Update prompt import in analyser.py:**
```python
# Before:
from waivern_community.prompts.processing_purpose_validation import PROCESSING_PURPOSE_VALIDATION_PROMPT

# After:
from waivern_processing_purpose_analyser.prompts.processing_purpose_validation import PROCESSING_PURPOSE_VALIDATION_PROMPT
```

### 7. Package Exports with Schema Registration

**CRITICAL:** Create `src/waivern_processing_purpose_analyser/__init__.py` with explicit schema registration:

```python
"""Processing purpose analyser for WCF."""

from importlib.resources import files
from pathlib import Path

from waivern_core.schemas import SchemaRegistry

from .analyser import ProcessingPurposeAnalyser
from .factory import ProcessingPurposeAnalyserFactory
from .schemas import ProcessingPurposeFindingModel
from .types import ProcessingPurposeAnalyserConfig


def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation via entry point.
    This function is referenced in pyproject.toml [project.entry-points."waivern.schemas"].

    NO import-time side effects - registration is explicit and controlled.
    """
    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(Path(str(schema_dir)))


__all__ = [
    "ProcessingPurposeAnalyser",
    "ProcessingPurposeAnalyserConfig",
    "ProcessingPurposeAnalyserFactory",
    "ProcessingPurposeFindingModel",
    "register_schemas",
]
```

**Key Points:**
- `register_schemas()` is called by WCT Executor via entry point, NOT at import time
- Uses `importlib.resources.files()` for proper resource location in installed packages
- Entry point system allows WCT to discover and register all schemas before loading components

### 8. Move Tests

```bash
mv libs/waivern-community/tests/waivern_community/analysers/processing_purpose_analyser/* \
   libs/waivern-processing-purpose-analyser/tests/waivern_processing_purpose_analyser/
```

Update test imports:
```python
# Before
from waivern_community.analysers.processing_purpose_analyser import ProcessingPurposeAnalyser
from waivern_community.analysers.processing_purpose_analyser.schemas import ProcessingPurposeFindingModel
from waivern_community.connectors.source_code.schemas import SourceCodeDataModel

# After
from waivern_processing_purpose_analyser import ProcessingPurposeAnalyser, ProcessingPurposeFindingModel
from waivern_source_code.schemas import SourceCodeDataModel
```

### 9. Add to Workspace

Update root `pyproject.toml`:

```toml
[tool.uv.sources]
# ... existing sources ...
waivern-processing-purpose-analyser = { workspace = true }  # ADD THIS
```

### 10. Install and Test Package

```bash
# Install package
uv sync --package waivern-processing-purpose-analyser

# Verify installation
uv run python -c "import waivern_processing_purpose_analyser; print('✓ Package installed')"

# Verify entry point registration
uv run python -c "from importlib.metadata import entry_points; eps = entry_points(group='waivern.analysers'); assert any(ep.name == 'processing_purpose' for ep in eps); print('✓ Analyser entry point registered')"
uv run python -c "from importlib.metadata import entry_points; eps = entry_points(group='waivern.schemas'); assert any(ep.name == 'processing_purpose' for ep in eps); print('✓ Schema entry point registered')"

# Verify schema registration via entry point
uv run python -c "from waivern_processing_purpose_analyser import register_schemas; from waivern_core.schemas import SchemaRegistry; register_schemas(); s = SchemaRegistry.get_schema('processing_purpose_finding', '1.0.0'); print('✓ Schema registration works')"

# Verify source code schema imports
uv run python -c "from waivern_processing_purpose_analyser.source_code_schema_input_handler import SourceCodeSchemaInputHandler; print('✓ Source code imports working')"

# Run package tests
cd libs/waivern-processing-purpose-analyser
uv run pytest tests/ -v
# Expected: ~14 tests passing
```

### 11. Run Package Quality Checks

```bash
cd libs/waivern-processing-purpose-analyser
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
# processing_purpose = "waivern_community.analysers.processing_purpose_analyser:ProcessingPurposeAnalyserFactory"  # REMOVE

[project.entry-points."waivern.schemas"]
# processing_purpose = "waivern_community.analysers.processing_purpose_analyser:register_schemas"  # REMOVE
```

Add dependency:
```toml
dependencies = [
    "waivern-core",
    # ... other dependencies
    "waivern-processing-purpose-analyser",  # ADD THIS
    # ... rest
]
```

**Update `libs/waivern-community/src/waivern_community/analysers/__init__.py`:**
```python
"""WCT analysers."""

from waivern_core import Analyser, AnalyserError

# Import from standalone packages
from waivern_data_subject_analyser import DataSubjectAnalyser
from waivern_personal_data_analyser import PersonalDataAnalyser
from waivern_processing_purpose_analyser import ProcessingPurposeAnalyser  # ADD THIS

__all__ = (
    "Analyser",
    "AnalyserError",
    "DataSubjectAnalyser",
    "PersonalDataAnalyser",
    "ProcessingPurposeAnalyser",  # ADD THIS
    "BUILTIN_ANALYSERS",
)

BUILTIN_ANALYSERS = (
    DataSubjectAnalyser,
    PersonalDataAnalyser,
    ProcessingPurposeAnalyser,  # ADD THIS
)
```

### 13. Delete Extracted Code

```bash
rm -rf libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser
rm -rf libs/waivern-community/tests/waivern_community/analysers/processing_purpose_analyser
rm -f libs/waivern-community/src/waivern_community/prompts/processing_purpose_validation.py
# Delete prompts directory if now empty
rmdir libs/waivern-community/src/waivern_community/prompts 2>/dev/null || true
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
cd libs/waivern-processing-purpose-analyser
uv run pytest tests/ -v
```

**Expected:** All ~12 tests passing (includes LLM validation tests and source code schema tests)

### Schema Tests

```bash
# Verify schema is discoverable
uv run python -c "
from waivern_core.schemas import SchemaRegistry
schema = SchemaRegistry.get_schema('processing_purpose_finding', '1.0.0')
print(f'✓ Schema found: {schema.name} v{schema.version}')
"

# Verify schema models work
uv run python -c "
from waivern_processing_purpose_analyser import ProcessingPurposeFindingModel
print('✓ Schema models importable')
"

# Verify source code schema integration
uv run python -c "
from waivern_source_code.schemas import SourceCodeDataModel
from waivern_processing_purpose_analyser.source_code_schema_input_handler import SourceCodeSchemaInputHandler
print('✓ Source code schema integration working')
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
uv run wct ls-analysers | grep processing-purpose

# Verify ruleset integration
uv run python -c "
from waivern_rulesets import RulesetLoader
ruleset = RulesetLoader.load_ruleset('processing_purposes')
print(f'✓ Ruleset loaded: {len(ruleset.rules)} rules')
"

# Test with LAMP stack runbook (uses processing purpose analyser with source code)
uv run wct validate-runbook apps/wct/runbooks/samples/LAMP_stack.yaml
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v
```

---

## Success Criteria

- [ ] waivern-processing-purpose-analyser package created with correct structure
- [ ] All 12 package tests passing
- [ ] Schema registration working (processing_purpose_finding/1.0.0 discoverable)
- [ ] Prompts file migrated successfully
- [ ] Source code schema imports working
- [ ] Package quality checks passing (lint, format, type-check)
- [ ] waivern-community updated to import from waivern-processing-purpose-analyser
- [ ] waivern-community tests passing
- [ ] All workspace tests passing
- [ ] Component discoverable via `wct ls-analysers`
- [ ] processing_purposes ruleset loads successfully
- [ ] LAMP_stack.yaml runbook validates and runs successfully
- [ ] Changes committed with message: `refactor: extract ProcessingPurposeAnalyser as standalone package`

---

## Decisions Made

1. **Custom schema:** processing_purpose_finding/1.0.0 schema with Pydantic models included
2. **Schema registration:** Added SchemaRegistry.register_search_path() in __init__.py
3. **Source code dependency:** Explicit dependency on waivern-source-code for schema support
4. **Prompts migration:** Moved processing_purpose_validation.py into package
5. **Include directive:** Added to distribute JSON schemas and py.typed
6. **Import updates:** Changed waivern_community.connectors.source_code → waivern_source_code
7. **Test environment relaxation:** Added basedpyright executionEnvironments for tests
8. **Multi-schema support:** Supports both standard_input and source_code input schemas

---

## Notes

- **CRITICAL:** Must complete Step 3 (waivern-source-code) before this step
- Most complex extraction due to source code schema dependency and prompts migration
- Supports both standard input and source code analysis (multi-schema)
- Uses "processing_purposes" ruleset from waivern-rulesets
- Schema registration is CRITICAL - must happen before component class imports
- Prompt file migration requires updating import in analyser.py
- After this step, all analysers are extracted
- ProcessingPurposeAnalyser will be re-exported from waivern-community for backward compatibility
- This is the last component extraction before Phase 5 (waivern-community removal)
