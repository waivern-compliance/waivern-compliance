# Task: Integrate ArtifactStore with ServiceContainer

- **Phase:** ArtifactStore Service - Dependency Injection
- **Status:** TODO
- **Prerequisites:** Task 1 (Core service implementation)
- **Related Issue:** #227

## Context

Integrates the ArtifactStore service into WCF's dependency injection system. This enables components to access artifact storage through the ServiceContainer, following established patterns from LLMService.

## Purpose

Make ArtifactStore available to components (Executor, ArtifactConnector) via dependency injection whilst maintaining lazy initialisation and singleton behaviour.

## Problem

Components need access to artifact storage without:
- Directly instantiating stores (tight coupling)
- Managing lifecycle manually (resource leaks)
- Duplicating configuration logic (inconsistency)

## Proposed Solution

Extend ServiceContainer with ArtifactStore support following the existing LLMService pattern: lazy initialisation, singleton per container, configuration-driven backend selection.

## Decisions Made

1. **Integration pattern** - Mirror LLMService implementation (lazy init + singleton)
2. **Configuration** - Environment variable ARTIFACT_STORE_BACKEND (defaults to "memory")
3. **Lifecycle** - Singleton per ServiceContainer instance
4. **Factory usage** - Use artifact_store_factory for instantiation

## Expected Outcome & Usage Example

**ServiceContainer usage:**
```python
# In Executor
container = ServiceContainer()
store = container.get_artifact_store()  # Returns singleton

# Subsequent calls return same instance
store2 = container.get_artifact_store()  # store2 is store == True
```

## Implementation

### Changes Required

#### 1. Update ServiceContainer Class

**Location:** `libs/waivern-core/src/waivern_core/services/service_container.py`

**Changes:**
- Add `_artifact_store: ArtifactStore | None` attribute
- Add `get_artifact_store() -> ArtifactStore` method
- Import factory function and ArtifactStore type

**Algorithm (pseudo-code):**
```python
class ServiceContainer:
    def __init__():
        self._llm_service = None
        self._artifact_store = None  # NEW

    def get_artifact_store() -> ArtifactStore:
        # Lazy initialisation
        if self._artifact_store is None:
            backend = os.getenv("ARTIFACT_STORE_BACKEND", "memory")
            self._artifact_store = create_artifact_store(backend)
        return self._artifact_store
```

**Key considerations:**
- Follow existing LLM service pattern exactly
- Lazy initialisation (only create when first requested)
- Singleton behaviour (cache instance in attribute)
- Configuration via environment variable

#### 2. Update Service Exports

**Location:** `libs/waivern-core/src/waivern_core/services/__init__.py`

**Changes:**
- Export ArtifactStore abstract class
- Export concrete implementations
- Export factory function
- Export exceptions

**Example:**
```python
from .artifact_store import ArtifactStore, ArtifactStoreError, ArtifactNotFoundError
from .in_memory_artifact_store import InMemoryArtifactStore
from .artifact_store_factory import create_artifact_store
```

## Testing

### Testing Strategy

Test ServiceContainer integration focusing on singleton behaviour and configuration.

### Test Scenarios

#### 1. Lazy Initialisation

**Setup:**
- Create ServiceContainer instance
- Call get_artifact_store()

**Expected behaviour:**
- Returns ArtifactStore instance
- Instance created on first call (lazy init)

#### 2. Singleton Behaviour

**Setup:**
- Create ServiceContainer
- Call get_artifact_store() multiple times

**Expected behaviour:**
- Same instance returned each time
- Singleton per container (not global singleton)

#### 3. Configuration Respect

**Setup:**
- Set ARTIFACT_STORE_BACKEND environment variable
- Create ServiceContainer and get store

**Expected behaviour:**
- Factory called with configured backend
- Environment variable respected

#### 4. Multiple Containers

**Setup:**
- Create two ServiceContainer instances
- Get artifact store from each

**Expected behaviour:**
- Each container has own store instance
- Stores are independent (not shared)

### Validation Commands

```bash
# Run service container tests
uv run pytest libs/waivern-core/tests/services/test_service_container.py -v

# Run all core tests
uv run pytest libs/waivern-core/tests/ -v

# Run quality checks
./scripts/dev-checks.sh
```

## Implementation Notes

**Design principles:**
- Exact pattern match with LLMService integration
- No special logic or deviation from established patterns
- Configuration follows WCF conventions
- Clear separation between container and service lifecycle
