# Entry Points Migration Plan

**Created:** 2025-01-07
**Status:** Ready for Execution
**Estimated Time:** ~14 hours

---

## Goal

Migrate Waivern Compliance Framework from import-time schema registration to entry points-based plugin discovery, eliminating import-time side effects and enabling a true plugin ecosystem. This will be done while completing Step 3 (waivern-source-code extraction) and then applied to all existing standalone packages.

---

## Current State

**Completed:**
- ✅ Step 1: waivern-filesystem extracted (Commit: 7eab880)
- ✅ Step 2: waivern-sqlite extracted (Commit: 1e17b9b)

**In Progress:**
- 🔄 Step 3: waivern-source-code extraction (partially complete)
  - Package structure created ✓
  - Scripts copied ✓
  - pyproject.toml created ✓
  - README.md created ✓
  - Code copied from waivern-community ✓
  - Some imports updated ✓
  - Still needs: complete import updates, schema registration, tests, integration

**Architecture Issue:**

All packages currently use import-time schema registration:

```python
# Current pattern (anti-pattern)
_SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
SchemaRegistry.register_search_path(_SCHEMA_DIR)  # ❌ Side effect at import
```

This violates Python best practices and prevents lazy imports (PEP 810).

---

## Proposed Solution: Entry Points Plugin System

Replace import-time registration with explicit entry points discovery.

**Benefits:**
- ✅ No import-time side effects
- ✅ Industry standard plugin pattern
- ✅ Compatible with PEP 810 lazy imports
- ✅ Enables third-party plugins
- ✅ Explicit control over initialisation
- ✅ Uses `importlib.resources.files()` (modern Python)

**Python Requirements:**
- ✅ Verified: Python 3.12 supports `entry_points()` and `importlib.resources.files()`

---

## Migration Strategy: 7 Phases

### Phase 0: Validation & Preparation (30 min)

**Status:** ✅ Partially Complete

**Tasks:**
1. ✅ Verify Python version supports required APIs
2. Document all packages with custom schemas
3. Create detailed implementation checklist
4. Identify all schema registration locations

**Packages with Custom Schemas (require schema entry points):**
- waivern-source-code (source_code/1.0.0) - Step 3, in progress
- waivern-personal-data-analyser (personal_data_finding/1.0.0) - standalone
- waivern-community components:
  - ProcessingPurposeAnalyser (processing_purpose_finding/1.0.0)
  - DataSubjectAnalyser (if exists)

**Packages WITHOUT Custom Schemas (only need connector entry points):**
- waivern-filesystem - uses standard_input/1.0.0
- waivern-sqlite - uses standard_input/1.0.0
- waivern-mysql - uses standard_input/1.0.0

**Success Criteria:**
- [ ] All packages documented
- [ ] Implementation plan validated
- [ ] No blockers identified

---

### Phase 1: Update Simple Standalone Packages (1 hour)

**Packages:** waivern-filesystem, waivern-sqlite, waivern-mysql

These packages only produce `standard_input/1.0.0` schema (from waivern-core), so they don't need schema registration - only connector entry points.

#### Tasks Per Package:

**1. Add connector entry point to pyproject.toml**

Example for waivern-filesystem:
```toml
[project.entry-points."waivern.connectors"]
filesystem = "waivern_filesystem:FilesystemConnectorFactory"
```

**2. Verify entry point works**
```bash
uv sync --package waivern-filesystem
python -c "
from importlib.metadata import entry_points
eps = entry_points(group='waivern.connectors')
for ep in eps:
    if ep.name == 'filesystem':
        print(f'✓ Entry point found: {ep.value}')
        factory = ep.load()
        print(f'✓ Loaded: {factory}')
"
```

**3. Run package tests**
```bash
cd libs/waivern-filesystem
uv run pytest tests/ -v
```

#### Files Changed Per Package:
- `pyproject.toml` (1 line added)

**Success Criteria:**
- [ ] waivern-filesystem entry point works
- [ ] waivern-sqlite entry point works
- [ ] waivern-mysql entry point works
- [ ] All package tests pass
- [ ] Entry points discoverable via `importlib.metadata`

---

### Phase 2: Complete waivern-source-code with Entry Points (PILOT - 2 hours)

**Status:** 🔄 In Progress

This is our pilot implementation - validates the approach before rolling out to other packages with schemas.

#### Tasks:

**1. Finish updating imports (currently incomplete)**

Files need import updates:
- ✅ `connector.py` - partially done, verify complete
- `schemas/__init__.py` - update from waivern_community imports
- `extractors/__init__.py` - update from waivern_community imports
- `extractors/base.py` - update from waivern_community imports
- `extractors/functions.py` - update from waivern_community imports
- `extractors/classes.py` - update from waivern_community imports

All `from waivern_community.connectors.source_code.*` → `from waivern_source_code.*`

**2. Create __init__.py with register_schemas() function**

```python
"""Source code connector for WCF."""

from .connector import SourceCodeConnector
from .config import SourceCodeConnectorConfig
from .factory import SourceCodeConnectorFactory
from .schemas import (
    SourceCodeClassModel,
    SourceCodeDataModel,
    SourceCodeFunctionModel,
)

def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called explicitly by WCF framework during initialisation.
    This function is referenced in pyproject.toml entry points.

    NO import-time side effects - registration is explicit.
    """
    from importlib.resources import files
    from waivern_core.schemas import SchemaRegistry

    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(schema_dir)

__all__ = [
    "SourceCodeConnector",
    "SourceCodeConnectorConfig",
    "SourceCodeConnectorFactory",
    "SourceCodeDataModel",
    "SourceCodeFunctionModel",
    "SourceCodeClassModel",
    "register_schemas",
]
```

**3. Add entry points to pyproject.toml**

```toml
[project.entry-points."waivern.connectors"]
source_code = "waivern_source_code:SourceCodeConnectorFactory"

[project.entry-points."waivern.schemas"]
source_code = "waivern_source_code:register_schemas"
```

**4. Move and update tests**

```bash
# Move tests
mv libs/waivern-community/tests/waivern_community/connectors/source_code/* \
   libs/waivern-source-code/tests/waivern_source_code/

# Update test imports
find libs/waivern-source-code/tests -name "*.py" -exec sed -i '' \
  's/from waivern_community\.connectors\.source_code/from waivern_source_code/g' {} +
```

**5. Add test fixture for schema registration**

Create `libs/waivern-source-code/tests/conftest.py`:
```python
"""Pytest configuration for waivern-source-code tests."""

import pytest


@pytest.fixture(autouse=True)
def _register_schemas():
    """Automatically register schemas for all tests.

    Since we no longer have import-time registration, tests need
    schemas to be explicitly registered.
    """
    from waivern_source_code import register_schemas

    register_schemas()
```

**6. Test entry points work**

```bash
# Verify no import-time side effects
python -c "
from waivern_core.schemas import SchemaRegistry

# Import should NOT register schemas
from waivern_source_code import SourceCodeConnector

# Schema should NOT be registered yet
try:
    schema = SchemaRegistry.get_schema('source_code', '1.0.0')
    print('❌ ERROR: Schema registered at import time!')
    exit(1)
except Exception:
    print('✓ Schema NOT registered at import (correct)')

# Now explicitly register
from waivern_source_code import register_schemas
register_schemas()

# Now it should work
schema = SchemaRegistry.get_schema('source_code', '1.0.0')
print(f'✓ Schema registered explicitly: {schema.name}/{schema.version}')
"
```

**7. Add to workspace**

Update root `pyproject.toml`:
```toml
[tool.uv.sources]
# ... existing sources ...
waivern-source-code = { workspace = true }  # ADD THIS
```

**8. Install and test package**

```bash
uv sync --package waivern-source-code --extra tree-sitter

# Run package tests
cd libs/waivern-source-code
uv run pytest tests/ -v
# Expected: ~7 tests passing

# Run quality checks
./scripts/format.sh
./scripts/lint.sh
./scripts/type-check.sh
```

#### Files Changed:
- `src/waivern_source_code/__init__.py` (rewrite with register_schemas)
- `src/waivern_source_code/schemas/__init__.py` (update imports)
- `src/waivern_source_code/extractors/*.py` (update imports)
- `pyproject.toml` (add entry points)
- `tests/conftest.py` (new file - schema fixture)
- `tests/**/*.py` (update imports)
- Root `pyproject.toml` (add workspace source)

**Success Criteria:**
- [ ] All imports updated from waivern_community → waivern_source_code
- [ ] No import-time schema registration
- [ ] register_schemas() function works correctly
- [ ] Entry points registered and discoverable
- [ ] All ~7 package tests pass
- [ ] Package quality checks pass (format, lint, type-check)
- [ ] Manual entry point test passes

---

### Phase 3: Add Entry Point Discovery to WCT Executor (2 hours)

**Goal:** Make WCT discover components via entry points instead of hard-coded imports.

#### Tasks:

**1. Add discovery methods to Executor**

Edit `apps/wct/src/wct/executor.py`:

```python
# Add at top
from importlib.metadata import entry_points
import logging

logger = logging.getLogger(__name__)

class Executor:
    # ... existing code ...

    def _discover_and_register_schemas(self) -> None:
        """Discover and register schemas from entry points.

        This must be called BEFORE discovering components, as components
        may reference schemas during initialisation.
        """
        schema_eps = entry_points(group="waivern.schemas")

        logger.debug(f"Discovering schemas from {len(schema_eps)} entry points")

        for ep in schema_eps:
            try:
                register_func = ep.load()
                register_func()
                logger.debug(f"✓ Registered schemas from: {ep.name}")
            except Exception as e:
                logger.warning(f"Failed to register schemas from {ep.name}: {e}")

    def _discover_connectors(self) -> None:
        """Discover connector factories from entry points."""
        connector_eps = entry_points(group="waivern.connectors")

        logger.debug(f"Discovering connectors from {len(connector_eps)} entry points")

        for ep in connector_eps:
            try:
                factory_class = ep.load()
                self.register_connector_factory(ep.name, factory_class)
                logger.debug(f"✓ Registered connector: {ep.name}")
            except Exception as e:
                logger.warning(f"Failed to load connector {ep.name}: {e}")

    def _discover_analysers(self) -> None:
        """Discover analyser classes from entry points."""
        analyser_eps = entry_points(group="waivern.analysers")

        logger.debug(f"Discovering analysers from {len(analyser_eps)} entry points")

        for ep in analyser_eps:
            try:
                analyser_class = ep.load()
                self.register_analyser(ep.name, analyser_class)
                logger.debug(f"✓ Registered analyser: {ep.name}")
            except Exception as e:
                logger.warning(f"Failed to load analyser {ep.name}: {e}")
```

**2. Update create_with_built_ins()**

```python
@staticmethod
def create_with_built_ins() -> "Executor":
    """Create executor with built-in components.

    Components are discovered via entry points - no import-time side effects.
    This enables a true plugin architecture where any installed package can
    provide connectors, analysers, or rulesets.
    """
    executor = Executor()

    # CRITICAL: Register schemas FIRST, before loading components
    executor._discover_and_register_schemas()

    # Now discover and register components
    executor._discover_connectors()
    executor._discover_analysers()

    # Rulesets (if they have entry points)
    # executor._discover_rulesets()  # Future work

    logger.info(
        f"Executor initialized with "
        f"{len(executor._connector_factories)} connectors, "
        f"{len(executor._analysers)} analysers"
    )

    return executor
```

**3. Remove hard-coded imports (if any)**

Search for and remove:
```python
# OLD - remove these
from waivern_community import (
    FilesystemConnectorFactory,
    MySQLConnectorFactory,
    # ... etc
)
```

Components are now discovered automatically via entry points.

**4. Test discovery works**

```bash
# Test entry point discovery
uv run python -c "
from wct.executor import Executor

executor = Executor.create_with_built_ins()

print('=== Discovered Connectors ===')
for name in executor._connector_factories.keys():
    print(f'  - {name}')

print('=== Discovered Analysers ===')
for name in executor._analysers.keys():
    print(f'  - {name}')
"
```

**5. Test WCT commands**

```bash
uv run wct ls-connectors
# Expected: filesystem, mysql, sqlite, source_code

uv run wct ls-analysers
# Expected: personal_data, processing_purpose, etc.

# Test with verbose logging
uv run wct ls-connectors -v
# Should show discovery debug logs
```

**6. Run WCT integration tests**

```bash
cd apps/wct
uv run pytest tests/integration/ -v
```

#### Files Changed:
- `apps/wct/src/wct/executor.py` (add discovery methods, update create_with_built_ins)

**Success Criteria:**
- [ ] Discovery methods implemented
- [ ] create_with_built_ins() uses entry point discovery
- [ ] No hard-coded component imports
- [ ] `wct ls-connectors` shows all components
- [ ] `wct ls-analysers` shows all components
- [ ] Integration tests pass
- [ ] Debug logging shows discovery process

---

### Phase 4: Update Remaining Standalone Packages (2 hours)

**Packages:** waivern-personal-data-analyser (and any others with custom schemas)

#### Tasks Per Package:

**1. Add entry points to pyproject.toml**

```toml
[project.entry-points."waivern.analysers"]
personal_data = "waivern_personal_data_analyser:PersonalDataAnalyser"

[project.entry-points."waivern.schemas"]
personal_data = "waivern_personal_data_analyser:register_schemas"
```

**2. Update __init__.py**

Remove import-time registration:
```python
# REMOVE THIS
from pathlib import Path
from waivern_core.schemas import SchemaRegistry
_SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
SchemaRegistry.register_search_path(_SCHEMA_DIR)  # ❌
```

Add register_schemas() function:
```python
def register_schemas() -> None:
    """Register schemas with SchemaRegistry."""
    from importlib.resources import files
    from waivern_core.schemas import SchemaRegistry

    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(schema_dir)
```

**3. Update tests**

Add `tests/conftest.py`:
```python
import pytest

@pytest.fixture(autouse=True)
def _register_schemas():
    from waivern_personal_data_analyser import register_schemas
    register_schemas()
```

**4. Test package**

```bash
cd libs/waivern-personal-data-analyser
uv run pytest tests/ -v
./scripts/dev-checks.sh
```

#### Files Changed Per Package:
- `pyproject.toml` (add entry points)
- `src/{package}/__init__.py` (remove import-time registration, add function)
- `tests/conftest.py` (add schema fixture)

**Success Criteria:**
- [ ] waivern-personal-data-analyser entry points work
- [ ] All package tests pass
- [ ] Quality checks pass

---

### Phase 5: Update waivern-community (3 hours)

**Challenge:** waivern-community has multiple components with custom schemas.

**Components to migrate:**
- ProcessingPurposeAnalyser (has processing_purpose_finding/1.0.0 schema)
- DataSubjectAnalyser (check if exists, check for schema)

#### Tasks:

**1. Add all entry points to pyproject.toml**

```toml
[project.entry-points."waivern.analysers"]
processing_purpose = "waivern_community.analysers.processing_purpose_analyser:ProcessingPurposeAnalyser"
data_subject = "waivern_community.analysers.data_subject_analyser:DataSubjectAnalyser"

[project.entry-points."waivern.schemas"]
processing_purpose = "waivern_community.analysers.processing_purpose_analyser:register_schemas"
data_subject = "waivern_community.analysers.data_subject_analyser:register_schemas"
```

**2. Remove import-time registration from main __init__.py**

Edit `libs/waivern-community/src/waivern_community/__init__.py`:

```python
# REMOVE ALL OF THIS
_PROCESSING_PURPOSE_SCHEMA_DIR = (
    Path(__file__).parent / "analysers" / "processing_purpose_analyser" / "schemas" / "json_schemas"
)
_DATA_SUBJECT_SCHEMA_DIR = (
    Path(__file__).parent / "analysers" / "data_subject_analyser" / "schemas" / "json_schemas"
)
SchemaRegistry.register_search_path(_PROCESSING_PURPOSE_SCHEMA_DIR)  # ❌
SchemaRegistry.register_search_path(_DATA_SUBJECT_SCHEMA_DIR)  # ❌
```

**3. Add register_schemas() to component sub-packages**

Create in each analyser package:

`libs/waivern-community/src/waivern_community/analysers/processing_purpose_analyser/__init__.py`:
```python
def register_schemas() -> None:
    """Register processing purpose analyser schemas."""
    from importlib.resources import files
    from waivern_core.schemas import SchemaRegistry

    schema_dir = files("waivern_community.analysers.processing_purpose_analyser") / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(schema_dir)
```

**4. Update waivern-community to re-export from waivern-source-code**

Since source_code was extracted in Step 3:

```python
# libs/waivern-community/src/waivern_community/connectors/__init__.py

from waivern_filesystem import FilesystemConnector, FilesystemConnectorFactory
from waivern_mysql import MySQLConnector, MySQLConnectorFactory
from waivern_sqlite import SQLiteConnector, SQLiteConnectorFactory
from waivern_source_code import SourceCodeConnector, SourceCodeConnectorFactory  # NEW

__all__ = (
    "FilesystemConnector",
    "FilesystemConnectorFactory",
    "MySQLConnector",
    "MySQLConnectorFactory",
    "SourceCodeConnector",
    "SourceCodeConnectorFactory",
    "SQLiteConnector",
    "SQLiteConnectorFactory",
    "BUILTIN_CONNECTORS",
)

BUILTIN_CONNECTORS = (
    FilesystemConnector,
    MySQLConnector,
    SourceCodeConnector,
    SQLiteConnector,
)
```

**5. Add waivern-source-code dependency**

`libs/waivern-community/pyproject.toml`:
```toml
dependencies = [
    "waivern-core",
    "waivern-llm",
    "waivern-connectors-database",
    "waivern-mysql",
    "waivern-filesystem",
    "waivern-sqlite",
    "waivern-source-code",  # ADD THIS
    # ... rest
]

[project.optional-dependencies]
# Source code connector needs tree-sitter
source-code = ["waivern-source-code[tree-sitter]"]
all = ["waivern-community[source-code]"]
```

**6. Delete extracted source_code directory**

```bash
rm -rf libs/waivern-community/src/waivern_community/connectors/source_code
rm -rf libs/waivern-community/tests/waivern_community/connectors/source_code
```

**7. Update waivern-community tests**

Add schema registration to test fixtures:

`libs/waivern-community/tests/conftest.py`:
```python
import pytest
from importlib.metadata import entry_points


@pytest.fixture(autouse=True)
def _register_all_schemas():
    """Automatically register all schemas for waivern-community tests."""
    # Register schemas from all entry points
    schema_eps = entry_points(group="waivern.schemas")

    for ep in schema_eps:
        try:
            register_func = ep.load()
            register_func()
        except Exception as e:
            # Log but don't fail - some schemas might not be available
            print(f"Warning: Could not register {ep.name}: {e}")
```

**8. Test waivern-community**

```bash
cd libs/waivern-community
uv run pytest tests/ -v
./scripts/dev-checks.sh
```

#### Files Changed:
- `libs/waivern-community/pyproject.toml` (entry points, dependencies)
- `libs/waivern-community/src/waivern_community/__init__.py` (remove import-time registration)
- `libs/waivern-community/src/waivern_community/connectors/__init__.py` (import from waivern-source-code)
- `libs/waivern-community/src/waivern_community/analysers/*/` (add register_schemas functions)
- `libs/waivern-community/tests/conftest.py` (schema fixture)
- Delete: `connectors/source_code/` directory

**Success Criteria:**
- [ ] All import-time registrations removed
- [ ] Entry points added for all components
- [ ] register_schemas() functions added
- [ ] waivern-source-code dependency added
- [ ] Extracted code deleted
- [ ] All waivern-community tests pass
- [ ] Quality checks pass

---

### Phase 6: Full Workspace Testing & Validation (2 hours)

**Goal:** Verify entire system works with entry points.

#### Tasks:

**1. Clean install**

```bash
# Clean everything
rm -rf .venv
uv sync

# Verify entry points registered
python -c "
from importlib.metadata import entry_points

print('=== Connectors ===')
connector_eps = entry_points(group='waivern.connectors')
for ep in connector_eps:
    print(f'  {ep.name}: {ep.value}')
print(f'Total: {len(connector_eps)} connectors\n')

print('=== Analysers ===')
analyser_eps = entry_points(group='waivern.analysers')
for ep in analyser_eps:
    print(f'  {ep.name}: {ep.value}')
print(f'Total: {len(analyser_eps)} analysers\n')

print('=== Schemas ===')
schema_eps = entry_points(group='waivern.schemas')
for ep in schema_eps:
    print(f'  {ep.name}: {ep.value}')
print(f'Total: {len(schema_eps)} schemas')
"
```

**Expected output:**
```
=== Connectors ===
  filesystem: waivern_filesystem:FilesystemConnectorFactory
  mysql: waivern_mysql:MySQLConnectorFactory
  sqlite: waivern_sqlite:SQLiteConnectorFactory
  source_code: waivern_source_code:SourceCodeConnectorFactory
Total: 4 connectors

=== Analysers ===
  personal_data: waivern_personal_data_analyser:PersonalDataAnalyser
  processing_purpose: waivern_community.analysers.processing_purpose_analyser:ProcessingPurposeAnalyser
Total: 2 analysers

=== Schemas ===
  source_code: waivern_source_code:register_schemas
  personal_data: waivern_personal_data_analyser:register_schemas
  processing_purpose: waivern_community.analysers.processing_purpose_analyser:register_schemas
Total: 3 schemas
```

**2. Test WCT commands**

```bash
# List components
uv run wct ls-connectors
uv run wct ls-analysers

# With verbose logging
uv run wct ls-connectors -v
# Should show: "Discovering connectors from 4 entry points"
```

**3. Test sample runbooks**

```bash
# File content analysis
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v

# LAMP stack (uses source_code connector)
uv run wct validate-runbook apps/wct/runbooks/samples/LAMP_stack.yaml
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v

# LAMP stack lite
uv run wct run apps/wct/runbooks/samples/LAMP_stack_lite.yaml -v
```

**4. Run full test suite**

```bash
# All tests
uv run pytest -v

# Expected: All tests passing (including waivern-source-code tests)
```

**5. Run workspace quality checks**

```bash
./scripts/dev-checks.sh
```

**Expected results:**
- Format: All files properly formatted ✓
- Lint: No linting errors ✓
- Type check: No type errors ✓
- Tests: All 924+ tests passing ✓

**6. Test import-time behaviour (no side effects)**

```bash
python -c "
# Import packages should NOT register schemas
import waivern_source_code
import waivern_personal_data_analyser
from waivern_community.analysers.processing_purpose_analyser import ProcessingPurposeAnalyser

from waivern_core.schemas import SchemaRegistry

# These should all fail (schemas not registered yet)
try:
    SchemaRegistry.get_schema('source_code', '1.0.0')
    print('❌ ERROR: source_code schema registered at import!')
    exit(1)
except:
    print('✓ source_code schema NOT registered at import')

try:
    SchemaRegistry.get_schema('personal_data_finding', '1.0.0')
    print('❌ ERROR: personal_data_finding schema registered at import!')
    exit(1)
except:
    print('✓ personal_data_finding schema NOT registered at import')

print('✓ All imports have no side effects')
"
```

**7. Test explicit discovery**

```bash
python -c "
from importlib.metadata import entry_points
from waivern_core.schemas import SchemaRegistry

# Explicitly register schemas
schema_eps = entry_points(group='waivern.schemas')
for ep in schema_eps:
    register_func = ep.load()
    register_func()

# Now these should work
source_code = SchemaRegistry.get_schema('source_code', '1.0.0')
print(f'✓ {source_code.name}/{source_code.version} registered')

personal_data = SchemaRegistry.get_schema('personal_data_finding', '1.0.0')
print(f'✓ {personal_data.name}/{personal_data.version} registered')

processing = SchemaRegistry.get_schema('processing_purpose_finding', '1.0.0')
print(f'✓ {processing.name}/{processing.version} registered')

print('✓ Entry point discovery works correctly')
"
```

**Success Criteria:**
- [ ] All entry points discovered correctly
- [ ] All WCT commands work (ls-connectors, ls-analysers)
- [ ] All sample runbooks execute successfully
- [ ] Full test suite passes (924+ tests)
- [ ] Quality checks pass (format, lint, type-check)
- [ ] No import-time side effects verified
- [ ] Explicit discovery works correctly
- [ ] LAMP_stack.yaml works (exercises source_code connector)

---

### Phase 7: Documentation & Cleanup (1 hour)

**Goal:** Document the new architecture and provide migration guidance.

#### Tasks:

**1. Update CLAUDE.md**

Add section on component development:

```markdown
## Component Development

### Schema Registration (Entry Points)

Components with custom schemas must use explicit registration via entry points.

**DO NOT** register schemas at import time:
```python
# ❌ WRONG - import-time side effect
from pathlib import Path
from waivern_core.schemas import SchemaRegistry

_SCHEMA_DIR = Path(__file__).parent / "schemas" / "json_schemas"
SchemaRegistry.register_search_path(_SCHEMA_DIR)  # Anti-pattern!
```

**DO** use explicit registration via entry points:

1. Define a registration function in your package:

```python
# ✓ CORRECT - explicit registration
def register_schemas() -> None:
    """Register schemas with SchemaRegistry.

    Called by WCF framework during initialisation.
    """
    from importlib.resources import files
    from waivern_core.schemas import SchemaRegistry

    schema_dir = files(__name__) / "schemas" / "json_schemas"
    SchemaRegistry.register_search_path(schema_dir)
```

2. Declare the entry point in `pyproject.toml`:

```toml
[project.entry-points."waivern.schemas"]
my_component = "my_package:register_schemas"

[project.entry-points."waivern.connectors"]
my_connector = "my_package:MyConnectorFactory"
```

3. WCF will automatically discover and call your registration function.

**Benefits:**
- No import-time side effects
- Compatible with lazy imports (PEP 810)
- True plugin architecture
- Industry standard pattern

### Testing Components

Tests need explicit schema registration. Add a pytest fixture:

```python
# tests/conftest.py
import pytest

@pytest.fixture(autouse=True)
def _register_schemas():
    """Register schemas for tests."""
    from my_package import register_schemas
    register_schemas()
```
```

**2. Update component extraction template**

Edit `docs/guides/component-extraction-template.md`:

Add section on entry points:
- How to add entry points to pyproject.toml
- How to create register_schemas() function
- How to test entry points work
- Test fixture pattern

**3. Create migration guide for third-party developers**

Create `docs/guides/entry-points-migration.md`:
- Why we migrated
- Before/after examples
- Step-by-step migration guide
- Common issues and solutions

**4. Update Step 3 documentation**

Edit `docs/development/active/extract-remaining-components/step_3_extract_waivern_source_code.md`:

Mark as complete:
```markdown
# Step 3: Extract waivern-source-code ✅

**Status:** ✅ COMPLETED (Commit: TBD)
```

**5. Document architecture decision**

Create `docs/architecture/entry-points-plugin-system.md`:
- Current architecture overview
- Entry points groups (waivern.connectors, waivern.schemas, waivern.analysers)
- Discovery mechanism
- Benefits and trade-offs
- Future extension points

#### Files Changed:
- `CLAUDE.md` (add component development section)
- `docs/guides/component-extraction-template.md` (add entry points)
- `docs/guides/entry-points-migration.md` (new file)
- `docs/development/active/extract-remaining-components/step_3_extract_waivern_source_code.md` (mark complete)
- `docs/architecture/entry-points-plugin-system.md` (new file)

**Success Criteria:**
- [ ] CLAUDE.md updated with entry points guidance
- [ ] Component extraction template updated
- [ ] Migration guide created
- [ ] Step 3 marked as complete
- [ ] Architecture decision documented

---

## Risk Assessment

### High Risk Areas:

1. **Schema Registration Timing**
   - Risk: Schemas not registered before component initialisation
   - Mitigation: Always call _discover_and_register_schemas() FIRST in executor
   - Test: Verify schema availability before using components

2. **Test Fixtures**
   - Risk: Tests fail due to missing schema registration
   - Mitigation: Use autouse fixtures in conftest.py
   - Test: Run full test suite in each phase

3. **waivern-community Complexity**
   - Risk: Multiple components, complex dependencies
   - Mitigation: Do waivern-community last, after validating approach
   - Test: Extensive testing in Phase 5

### Medium Risk Areas:

1. **Entry Point Discovery**
   - Risk: Entry points not found after package installation
   - Mitigation: Always run `uv sync` after adding entry points
   - Test: Verify with `entry_points()` queries

2. **Import Cycles**
   - Risk: register_schemas() creates import cycles
   - Mitigation: Use local imports inside register_schemas()
   - Test: Import packages in isolation

### Low Risk Areas:

1. **Simple Packages** (filesystem, sqlite, mysql)
   - Risk: Minimal changes, no schemas
   - Mitigation: These are straightforward
   - Test: Package tests + entry point verification

---

## Rollback Strategy

### Granular Rollback by Phase:

- **Phase 1-2**: Revert individual package commits
- **Phase 3**: Revert executor changes (doesn't break packages)
- **Phase 4-5**: Revert individual package commits
- **Phase 6-7**: Documentation only, no rollback needed

### Full Rollback:

If critical issues arise:
```bash
git revert <first-commit>..<last-commit>
uv sync
./scripts/dev-checks.sh
```

All changes are in feature branch, so can abandon branch and restart from main if needed.

---

## Time Estimate

| Phase | Estimated Time | Status |
|-------|----------------|--------|
| Phase 0: Validation & Prep | 30 min | Pending |
| Phase 1: Simple Packages | 1 hour | Pending |
| Phase 2: waivern-source-code (PILOT) | 2 hours | In Progress |
| Phase 3: WCT Executor Discovery | 2 hours | Pending |
| Phase 4: Other Packages with Schemas | 2 hours | Pending |
| Phase 5: waivern-community | 3 hours | Pending |
| Phase 6: Testing & Validation | 2 hours | Pending |
| Phase 7: Documentation | 1 hour | Pending |
| **Total** | **~14 hours** | In Progress |

---

## Success Metrics

**Technical:**
- [ ] 0 import-time side effects
- [ ] All entry points discoverable
- [ ] All 924+ tests passing
- [ ] All quality checks passing
- [ ] All sample runbooks execute

**Architectural:**
- [ ] True plugin system implemented
- [ ] PEP 810 compatible
- [ ] Industry standard patterns used
- [ ] Third-party plugins supported

**Code Quality:**
- [ ] Uses importlib.resources.files()
- [ ] Explicit registration functions
- [ ] Proper error handling
- [ ] Comprehensive logging

---

## Next Actions

**Immediate (Phase 2 - waivern-source-code):**
1. Finish updating imports in all source_code files
2. Update __init__.py with register_schemas()
3. Add entry points to pyproject.toml
4. Move and update tests with schema fixture
5. Validate entry points work
6. Run package quality checks

**After Phase 2 Validation:**
- Proceed to Phase 1 (simple packages)
- Then Phase 3 (executor discovery)
- Continue through remaining phases

**Decision Point:**
After Phase 2 pilot completion, assess:
- Did entry points work as expected?
- Any unforeseen issues?
- Adjust plan if needed before proceeding

---

## Appendix: Entry Points Reference

### Entry Point Groups

**waivern.connectors** - Connector factory classes
```toml
[project.entry-points."waivern.connectors"]
name = "package:FactoryClass"
```

**waivern.analysers** - Analyser classes
```toml
[project.entry-points."waivern.analysers"]
name = "package:AnalyserClass"
```

**waivern.schemas** - Schema registration functions
```toml
[project.entry-points."waivern.schemas"]
name = "package:register_schemas"
```

**Future groups** (not in this plan):
- waivern.rulesets - Ruleset classes
- waivern.prompts - Prompt templates
- waivern.reporters - Output formatters

### Discovery Pattern

```python
from importlib.metadata import entry_points

# Discover group
eps = entry_points(group="waivern.connectors")

# Load each entry point
for ep in eps:
    obj = ep.load()  # Returns the object (class or function)
    # Use obj...
```

### Testing Entry Points

```bash
# List all entry points for a group
python -c "
from importlib.metadata import entry_points
for ep in entry_points(group='waivern.connectors'):
    print(f'{ep.name}: {ep.value}')
"

# Test loading
python -c "
from importlib.metadata import entry_points
ep = next(entry_points(group='waivern.connectors', name='filesystem'))
factory = ep.load()
print(f'Loaded: {factory}')
"
```

---

**Plan Status:** Ready for execution
**Created:** 2025-01-07
**Last Updated:** 2025-01-07
