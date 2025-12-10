# Testing Patterns

**Last Updated:** 2025-12-10

This document describes testing patterns and best practices used in the Waivern Compliance Framework.

## Singleton Testing Pattern

The framework uses several singleton registries (e.g., `ComponentRegistry`, `ExporterRegistry`) that maintain global state. To ensure test isolation, we use workspace-level autouse fixtures that automatically snapshot and restore singleton state for every test.

### The Pattern

1. **Add state management methods to the singleton class**

   Each singleton that needs test isolation should implement two classmethods:
   - `snapshot_state()` - Captures the current state
   - `restore_state(snapshot)` - Restores a previously captured state

2. **Add workspace-level autouse fixture**

   Create an autouse fixture in `/Users/lwkz/Workspace/waivern-compliance/conftest.py` that automatically snapshots state before each test and restores it after.

3. **Tests get automatic isolation**

   Tests automatically get isolation without needing explicit fixtures or manual cleanup.

### Implementation Example

#### Step 1: Add State Management to Singleton

```python
class ExporterRegistry:
    """Singleton registry for compliance exporters."""

    _exporters: dict[str, Exporter] = {}

    @classmethod
    def snapshot_state(cls) -> dict[str, Exporter]:
        """Snapshot current registry state for test isolation.

        Returns:
            Deep copy of current exporters.
        """
        return cls._exporters.copy()

    @classmethod
    def restore_state(cls, snapshot: dict[str, Exporter]) -> None:
        """Restore registry to a previous state.

        Args:
            snapshot: Previously captured state from snapshot_state().
        """
        cls._exporters = snapshot.copy()

    @classmethod
    def register(cls, exporter: Exporter) -> None:
        """Register an exporter."""
        cls._exporters[exporter.name] = exporter

    @classmethod
    def get(cls, name: str) -> Exporter:
        """Get an exporter by name."""
        if name not in cls._exporters:
            raise ValueError(f"Exporter '{name}' not found")
        return cls._exporters[name]
```

#### Step 2: Add Workspace-Level Fixture

In `/Users/lwkz/Workspace/waivern-compliance/conftest.py`:

```python
import pytest
from wct.exporters.registry import ExporterRegistry

@pytest.fixture(autouse=True)
def _isolate_exporter_registry():
    """Automatically isolate ExporterRegistry for each test.

    This fixture runs automatically for every test without needing
    to be explicitly requested. It snapshots the registry state before
    the test and restores it after, ensuring tests don't interfere
    with each other.
    """
    snapshot = ExporterRegistry.snapshot_state()
    try:
        yield
    finally:
        ExporterRegistry.restore_state(snapshot)
```

#### Step 3: Tests Work Automatically

```python
def test_exporter_registration():
    """Test registering an exporter."""
    # Automatically isolated - no setup needed
    registry = ExporterRegistry()
    registry.register(MyExporter())

    assert registry.get("my_exporter") is not None
    # Cleanup happens automatically via fixture

def test_another_exporter():
    """Test runs with clean registry state."""
    # Registry is automatically reset from previous test
    registry = ExporterRegistry()
    # No exporters from previous test are present
```

### Existing Implementations

The following singletons in the codebase use this pattern:

1. **`ComponentRegistry`** (`libs/waivern-core/src/waivern_core/services/registry.py`)
   - Manages connector and processor factories
   - Fixture: `_isolate_component_registry` in workspace conftest.py

2. **`ExporterRegistry`** (`apps/wct/src/wct/exporters/registry.py`)
   - Manages compliance exporters
   - Fixture: `_isolate_exporter_registry` in workspace conftest.py

### When to Use This Pattern

Use this pattern when:

1. **Creating a new singleton registry**
   - Any class that maintains global state shared across the application
   - Registries for plugins, components, or services

2. **Singleton needs test isolation**
   - Tests should not interfere with each other
   - Each test should start with a clean state

3. **Manual cleanup is error-prone**
   - Developers might forget to clean up in teardown
   - Exception during test could skip cleanup

### When NOT to Use This Pattern

Do not use this pattern for:

1. **Non-singleton classes**
   - Regular classes that are instantiated per-use
   - Use normal test fixtures instead

2. **Stateless utilities**
   - Pure functions with no global state
   - No isolation needed

3. **External resources**
   - Database connections, file handles, network sockets
   - Use proper context managers or fixtures with explicit cleanup

## Best Practices

### Naming Conventions

- Fixture names: `_isolate_{registry_name}` (prefix with underscore for autouse)
- State methods: `snapshot_state()` and `restore_state(snapshot)`
- Keep fixtures in workspace-level `conftest.py` for global effect

### State Management

1. **Deep copies**: Always use `.copy()` or `deepcopy()` to avoid reference sharing
2. **Complete state**: Snapshot ALL mutable state, not just part of it
3. **Idempotent restore**: `restore_state()` should fully reset to snapshot, not merge

### Testing the Pattern

When adding a new singleton with this pattern, verify:

1. **Isolation works**: Run two tests that modify state - second should not see first's changes
2. **State is complete**: Snapshot captures all relevant state
3. **Cleanup on exception**: Test that state is restored even if test raises exception

## Example: Adding a New Singleton Registry

```python
# Step 1: Implement singleton with state management
class MyRegistry:
    _items: dict[str, Item] = {}

    @classmethod
    def snapshot_state(cls) -> dict[str, Item]:
        return cls._items.copy()

    @classmethod
    def restore_state(cls, snapshot: dict[str, Item]) -> None:
        cls._items = snapshot.copy()

# Step 2: Add autouse fixture in workspace conftest.py
@pytest.fixture(autouse=True)
def _isolate_my_registry():
    snapshot = MyRegistry.snapshot_state()
    try:
        yield
    finally:
        MyRegistry.restore_state(snapshot)

# Step 3: Tests automatically get isolation
def test_my_registry():
    MyRegistry.register("item1", item)
    assert MyRegistry.get("item1") is not None
```

## Related Documentation

- **[Configuration Guide](configuration.md)** - Environment configuration
- **[IDE Integration](ide-integration.md)** - Setting up IDE for development
- **[CLAUDE.md](../../CLAUDE.md)** - Development workflow and standards
