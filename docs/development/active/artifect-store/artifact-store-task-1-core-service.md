# Task: Implement ArtifactStore Core Service

- **Phase:** ArtifactStore Service - Core Implementation
- **Status:** TODO
- **Prerequisites:** None
- **Related Issue:** #227

## Context

This implements the foundational ArtifactStore service for managing pipeline artifacts. The service follows WCF patterns (mirrors LLMService architecture) and enables the unified connector architecture. Full specification: `docs/development/active/artifact-store-service-plan.md`.

## Purpose

Create a service abstraction for artifact storage that supports multiple backends whilst maintaining simplicity for the initial in-memory implementation.

## Problem

The Executor currently uses a local dictionary for artifact storage (`artifacts = {}`), which:
- Couples storage implementation to execution logic
- Prevents future distributed execution capabilities
- Lacks proper lifecycle management and error handling

## Proposed Solution

Implement ArtifactStore as a WCF service with abstract interface, concrete in-memory implementation, and factory pattern for backend selection.

## Decisions Made

1. **Service architecture** - Abstract base class + concrete implementations (follows LLMService pattern)
2. **Initial backend** - InMemoryArtifactStore using dict-based storage
3. **Thread safety** - Use threading.Lock for concurrent access support
4. **Storage strategy** - Store Message references (assume immutability)
5. **Error hierarchy** - Custom exceptions (ArtifactNotFoundError, ArtifactStoreError)

## Expected Outcome & Usage Example

**Service usage:**
```python
# Create store via factory
store = create_artifact_store(backend="memory")

# Save artifact
store.save(step_id="extract", message=output_message)

# Retrieve artifact
message = store.get(step_id="extract")

# Check existence
if store.exists(step_id="extract"):
    # ...

# Cleanup
store.clear()
```

## Implementation

### Changes Required

#### 1. Create ArtifactStore Abstract Base

**Location:** `libs/waivern-core/src/waivern_core/services/artifact_store.py`

**Purpose:** Define service interface for all implementations

**Interface (pseudo-code):**
```python
class ArtifactStore(ABC):
    @abstractmethod
    def save(step_id: str, message: Message) -> None:
        """Store artifact from completed step"""

    @abstractmethod
    def get(step_id: str) -> Message:
        """Retrieve artifact (raises ArtifactNotFoundError if missing)"""

    @abstractmethod
    def exists(step_id: str) -> bool:
        """Check if artifact exists"""

    @abstractmethod
    def clear() -> None:
        """Remove all artifacts"""
```

#### 2. Define Exception Hierarchy

**Location:** Same file as abstract base

**Purpose:** Provide clear error messages for storage operations

**Exception design:**
- `ArtifactStoreError` - Base exception for all storage errors
- `ArtifactNotFoundError` - Specific exception for missing artifacts
- Error messages should include step_id for debugging

#### 3. Implement InMemoryArtifactStore

**Location:** `libs/waivern-core/src/waivern_core/services/in_memory_artifact_store.py`

**Purpose:** Default dict-based implementation with thread safety

**Algorithm (pseudo-code):**
```python
class InMemoryArtifactStore(ArtifactStore):
    def __init__():
        storage = dict()  # step_id -> Message
        lock = threading.Lock()

    def save(step_id, message):
        with lock:
            storage[step_id] = message  # Store reference

    def get(step_id):
        with lock:
            if step_id not in storage:
                raise ArtifactNotFoundError(...)
            return storage[step_id]
```

**Key considerations:**
- Thread-safe operations using Lock
- Store Message references (no deep copying)
- Helpful error messages with context

#### 4. Create Factory Function

**Location:** `libs/waivern-core/src/waivern_core/services/artifact_store_factory.py`

**Purpose:** Instantiate appropriate backend based on configuration

**Algorithm (pseudo-code):**
```python
def create_artifact_store(backend: str = "memory") -> ArtifactStore:
    match backend:
        case "memory":
            return InMemoryArtifactStore()
        case _:
            raise ValueError(f"Unknown backend: {backend}")
```

**Extensibility:**
- Future backends: "redis", "s3", "http"
- Load config from environment variables
- Validate backend-specific requirements

## Testing

### Testing Strategy

Unit tests for each component focusing on behaviour verification and error handling.

### Test Scenarios

#### 1. InMemoryArtifactStore - CRUD Operations

**Setup:**
- Create store instance
- Create mock Message objects

**Expected behaviour:**
- save() stores message successfully
- get() retrieves exact same reference
- exists() returns True after save, False before
- clear() removes all artifacts

#### 2. InMemoryArtifactStore - Error Cases

**Setup:**
- Create store instance
- Attempt operations on non-existent artifacts

**Expected behaviour:**
- get() on missing artifact raises ArtifactNotFoundError
- Error message includes step_id
- exists() returns False for missing artifacts

#### 3. InMemoryArtifactStore - Thread Safety

**Setup:**
- Create store instance
- Multiple threads performing concurrent saves/gets

**Expected behaviour:**
- No race conditions or corruption
- All messages retrieved match saved messages
- Lock prevents concurrent modification issues

#### 4. Factory - Backend Selection

**Setup:**
- Call factory with various backend parameters

**Expected behaviour:**
- backend="memory" returns InMemoryArtifactStore
- Invalid backend raises ValueError
- Error message lists available backends

### Validation Commands

```bash
# Run core library tests
uv run pytest libs/waivern-core/tests/services/ -v

# Run all quality checks
./scripts/dev-checks.sh
```

## Implementation Notes

**Package structure:**
```
libs/waivern-core/
├── src/waivern_core/services/
│   ├── artifact_store.py            # ABC + exceptions
│   ├── in_memory_artifact_store.py  # Default implementation
│   └── artifact_store_factory.py    # Factory function
└── tests/services/
    └── test_artifact_store.py       # Unit tests
```

**Design principles:**
- Follow LLMService architectural patterns
- Thread-safe for future parallel execution
- Message immutability assumed (no defensive copying)
- Clear separation between interface and implementation
