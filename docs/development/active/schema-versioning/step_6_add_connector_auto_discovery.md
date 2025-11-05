# Step 6: Add Auto-Discovery to Connector Base Class

**Phase:** 2 - Base Class Auto-Discovery
**Dependencies:** Step 5 complete (Phase 1 done)
**Estimated Scope:** Core base class enhancement

## Purpose

Add file-based schema version auto-discovery to the Connector base class. Components can then advertise version support by simply adding files to `schema_producers/` directory.

## Current State

`libs/waivern-core/src/waivern_core/base_connector.py`:
- `get_supported_output_schemas()` is abstract
- Components must manually implement and return schema lists
- No auto-discovery mechanism

## Target State

- `get_supported_output_schemas()` has default implementation with auto-discovery
- Scans `schema_producers/` directory in component's package
- Parses filenames to extract schema name and version
- Returns list of Schema objects
- Components can override if custom logic needed

## Implementation

Add this method to the `Connector` class:

```python
@classmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    """Auto-discover supported output schemas from schema_producers/ directory.

    Convention: Components declare version support through file presence.
    Files in schema_producers/ directory are discovered and parsed:
    - Filename format: {schema_name}_{major}_{minor}_{patch}.py
    - Example: standard_input_1_0_0.py → Schema("standard_input", "1.0.0")

    Components can override this method for custom discovery logic.

    Returns:
        List of Schema objects representing supported output versions
    """
    import inspect
    from pathlib import Path

    # Get the directory where the component class is defined
    component_dir = Path(inspect.getfile(cls)).parent
    schema_dir = component_dir / "schema_producers"

    schemas: list[Schema] = []

    if schema_dir.exists():
        for file in schema_dir.glob("*.py"):
            # Skip private files and __init__
            if file.name.startswith("_"):
                continue

            # Parse filename: "standard_input_1_0_0.py"
            # Use rsplit to split from right, taking last 3 parts as version
            parts = file.stem.rsplit("_", 3)

            if len(parts) == 4:
                schema_name = parts[0]
                major, minor, patch = parts[1], parts[2], parts[3]
                version = f"{major}.{minor}.{patch}"

                # Create Schema object (lightweight, no file I/O)
                schemas.append(Schema(schema_name, version))

    return schemas
```

## Testing

### Unit Tests

Create new test file: `libs/waivern-core/tests/waivern_core/test_connector_auto_discovery.py`

```python
"""Tests for Connector auto-discovery functionality."""
import tempfile
from pathlib import Path
from waivern_core.base_connector import Connector
from waivern_core.schemas.base import Schema

def test_auto_discovery_finds_schemas(tmp_path):
    """Test auto-discovery finds schema files."""
    # Create test connector with schema_producers/ directory
    # Create files: standard_input_1_0_0.py, standard_input_1_1_0.py
    # Test that get_supported_output_schemas() returns both

def test_auto_discovery_skips_private_files(tmp_path):
    """Test auto-discovery ignores __init__.py and _private.py."""

def test_auto_discovery_parses_multi_word_schema_names(tmp_path):
    """Test parsing: personal_data_finding_1_0_0.py."""

def test_auto_discovery_returns_empty_when_no_directory(tmp_path):
    """Test returns empty list when schema_producers/ doesn't exist."""

def test_component_can_override_discovery():
    """Test components can override for custom logic."""
```

### Integration Testing

Update existing connector tests to verify auto-discovery works:

```bash
cd libs/waivern-core
uv run pytest tests/waivern_core/test_connector_auto_discovery.py -v
```

## Key Decisions

**Filename parsing strategy:**
- Use `rsplit("_", 3)` to split from right
- Last 3 parts are major, minor, patch
- Everything before is schema name
- Examples:
  - `standard_input_1_0_0.py` → name: `standard_input`, version: `1.0.0`
  - `personal_data_finding_1_0_0.py` → name: `personal_data_finding`, version: `1.0.0`

**Directory convention:**
- Fixed name: `schema_producers/`
- Located in component's package directory (same dir as component class file)
- No configuration or override mechanism

**Performance:**
- Schema objects are lightweight (just name + version)
- No JSON file loading during discovery
- Fast enough to run on every call (can add caching later if needed)

## Files Modified

- `libs/waivern-core/src/waivern_core/base_connector.py` - Add auto-discovery method
- `libs/waivern-core/tests/waivern_core/test_connector_auto_discovery.py` - New test file

## Files to Update

Update the abstract method signature:
```python
# Before
@classmethod
@abc.abstractmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    """Return the output schemas supported by this connector."""

# After
@classmethod
def get_supported_output_schemas(cls) -> list[Schema]:
    """Auto-discover supported output schemas (can be overridden)."""
    # ... implementation above ...
```

Remove `@abc.abstractmethod` decorator since we now provide a default implementation.

## Notes

- This doesn't break existing components - they can still override
- Components that override won't use auto-discovery (which is fine)
- Next step will add similar auto-discovery for Analyser
- After both base classes updated, components can gradually adopt the pattern
