# Task: Integrate ArtifactStore with ServiceContainer

- **Phase:** ArtifactStore Service - Dependency Injection
- **Status:** COMPLETED
- **Prerequisites:** Task 1 (Core service implementation)
- **Related Issue:** #227

## Context

ServiceContainer already supports ArtifactStore via generic `register()` and `get_service()` methods. This task adds workspace configuration and integration tests.

## Purpose

Enable components to access artifact storage through ServiceContainer using the existing DI infrastructure.

## Current State

- ✅ ServiceContainer uses generic `ServiceFactory[T]` protocol
- ✅ ArtifactStoreFactory implements `ServiceFactory[ArtifactStore]`
- ✅ Workspace configuration already includes waivern-artifact-store
- ❌ Missing integration tests demonstrating DI usage

## Expected Outcome & Usage Example

```python
from waivern_core.services import ServiceContainer
from waivern_artifact_store import ArtifactStore, ArtifactStoreFactory

# Register artifact store
container = ServiceContainer()
container.register(
    ArtifactStore,
    ArtifactStoreFactory(),
    lifetime="singleton"
)

# Get singleton instance
store = container.get_service(ArtifactStore)

# Subsequent calls return same instance
store2 = container.get_service(ArtifactStore)
assert store2 is store
```

## Implementation

### Changes Required

#### Add Integration Tests

**Location:** `libs/waivern-artifact-store/tests/waivern_artifact_store/test_integration.py`

**Test coverage:**
- Register and retrieve singleton
- Multiple containers have independent instances
- Factory configuration respected
- Explicit configuration override

## Testing

### Test Coverage

**File:** `test_integration.py` (4 tests)

1. **Singleton behavior** - `get_service()` returns same instance
2. **Multiple containers** - Each container has independent instance
3. **Configuration** - Environment variable respected
4. **Explicit config** - Explicit config overrides environment

### Validation Commands

```bash
# Run integration tests
uv run pytest libs/waivern-artifact-store/tests/waivern_artifact_store/test_integration.py -v

# Run all artifact store tests
uv run pytest libs/waivern-artifact-store/tests/ -v

# Run quality checks
./scripts/dev-checks.sh
```

## Issue Tracking

**Related Issue:** #227

**Upon completion:**
- **Do NOT close** issue #227 - this is part 2 of 3 tasks
- Issue will be closed after Task 3 (Executor integration) is complete
- Update this task status to COMPLETED
- Commit with message: `feat: add artifact store ServiceContainer integration tests`
