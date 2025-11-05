# Step 7: Add Auto-Discovery to Analyser Base Class

**Phase:** 2 - Base Class Auto-Discovery
**Dependencies:** Step 6 complete
**Estimated Scope:** Core base class enhancement

## Purpose

Add file-based schema version auto-discovery to the Analyser base class. Analysers need both input and output schema discovery from `schema_readers/` and `schema_producers/` directories.

## Current State

`libs/waivern-core/src/waivern_core/base_analyser.py`:
- `get_supported_input_schemas()` is abstract
- `get_supported_output_schemas()` is abstract
- Components must manually implement and return schema lists

## Target State

- Both methods have default implementations with auto-discovery
- `get_supported_input_schemas()` scans `schema_readers/` directory
- `get_supported_output_schemas()` scans `schema_producers/` directory
- Same filename parsing as Connector
- Components can override for custom logic

## Implementation

Add these methods to the `Analyser` class:

```python
@classmethod
def get_supported_input_schemas(cls) -> list[Schema]:
    """Auto-discover supported input schemas from schema_readers/ directory.

    Convention: Analysers declare input version support through file presence.
    Files in schema_readers/ directory are discovered and parsed:
    - Filename format: {schema_name}_{major}_{minor}_{patch}.py
    - Example: standard_input_1_0_0.py → Schema("standard_input", "1.0.0")

    Components can override this method for custom discovery logic.

    Returns:
        List of Schema objects representing supported input versions
    """
    import inspect
    from pathlib import Path

    component_dir = Path(inspect.getfile(cls)).parent
    schema_dir = component_dir / "schema_readers"

    schemas: list[Schema] = []

    if schema_dir.exists():
        for file in schema_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue

            parts = file.stem.rsplit("_", 3)

            if len(parts) == 4:
                schema_name = parts[0]
                major, minor, patch = parts[1], parts[2], parts[3]
                version = f"{major}.{minor}.{patch}"
                schemas.append(Schema(schema_name, version))

    return schemas

@classmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    """Auto-discover supported output schemas from schema_producers/ directory.

    Convention: Analysers declare output version support through file presence.
    Files in schema_producers/ directory are discovered and parsed:
    - Filename format: {schema_name}_{major}_{minor}_{patch}.py
    - Example: personal_data_finding_1_0_0.py → Schema("personal_data_finding", "1.0.0")

    Components can override this method for custom discovery logic.

    Returns:
        List of Schema objects representing supported output versions
    """
    import inspect
    from pathlib import Path

    component_dir = Path(inspect.getfile(cls)).parent
    schema_dir = component_dir / "schema_producers"

    schemas: list[Schema] = []

    if schema_dir.exists():
        for file in schema_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue

            parts = file.stem.rsplit("_", 3)

            if len(parts) == 4:
                schema_name = parts[0]
                major, minor, patch = parts[1], parts[2], parts[3]
                version = f"{major}.{minor}.{patch}"
                schemas.append(Schema(schema_name, version))

    return schemas
```

## Testing

### Unit Tests

Create new test file: `libs/waivern-core/tests/waivern_core/test_analyser_auto_discovery.py`

```python
"""Tests for Analyser auto-discovery functionality."""
from pathlib import Path
from waivern_core.base_analyser import Analyser
from waivern_core.schemas.base import Schema

def test_input_schema_auto_discovery(tmp_path):
    """Test auto-discovery finds input schemas in schema_readers/."""
    # Create test analyser with schema_readers/ directory
    # Create files: standard_input_1_0_0.py, standard_input_1_1_0.py
    # Test get_supported_input_schemas() returns both

def test_output_schema_auto_discovery(tmp_path):
    """Test auto-discovery finds output schemas in schema_producers/."""
    # Create test analyser with schema_producers/ directory
    # Create files: personal_data_finding_1_0_0.py
    # Test get_supported_output_schemas() returns it

def test_both_directories_work_together(tmp_path):
    """Test analyser can have both schema_readers/ and schema_producers/."""

def test_auto_discovery_skips_private_files(tmp_path):
    """Test ignores __init__.py and _private.py in both directories."""

def test_auto_discovery_parses_complex_names(tmp_path):
    """Test parsing: processing_purpose_finding_1_0_0.py."""

def test_returns_empty_when_directories_missing(tmp_path):
    """Test returns empty lists when directories don't exist."""
```

### Integration Testing

```bash
cd libs/waivern-core
uv run pytest tests/waivern_core/test_analyser_auto_discovery.py -v
```

## Key Decisions

**Two directories for analysers:**
- `schema_readers/` - Input schemas the analyser can read
- `schema_producers/` - Output schemas the analyser can produce
- Same filename parsing for both

**Reusable logic:**
- Could extract common discovery logic to a helper function
- Both Connector and Analyser use same pattern
- Consider DRY refactoring if duplication becomes issue

**No caching yet:**
- Discovery runs on every call
- Fast enough (just directory scan + filename parsing)
- Can add `@lru_cache` decorator later if needed

## Files Modified

- `libs/waivern-core/src/waivern_core/base_analyser.py` - Add auto-discovery methods
- `libs/waivern-core/tests/waivern_core/test_analyser_auto_discovery.py` - New test file

## Files to Update

Remove `@abc.abstractmethod` decorators:
```python
# Before
@classmethod
@abc.abstractmethod
def get_supported_input_schemas(cls) -> list[Schema]:
    """Return the input schemas supported by the analyser."""

@classmethod
@abc.abstractmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    """Return the output schemas supported by this analyser."""

# After
@classmethod
def get_supported_input_schemas(cls) -> list[Schema]:
    """Auto-discover supported input schemas (can be overridden)."""
    # ... implementation above ...

@classmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    """Auto-discover supported output schemas (can be overridden)."""
    # ... implementation above ...
```

## Run All Base Class Tests

After both Connector and Analyser auto-discovery added:
```bash
cd libs/waivern-core
./scripts/dev-checks.sh
```

Expected:
- ✅ All waivern-core tests pass
- ✅ Auto-discovery tests pass
- ✅ Existing component tests still pass (they override the methods)

## Notes

- Existing components won't use auto-discovery until migrated (Phase 3+)
- This provides the foundation for components to adopt gradually
- Phase 2 complete after this step!
- Next: Proof of concept component migration (Phase 3)
