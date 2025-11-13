# ArtifactStore Service - Implementation Plan

**Date:** 2025-11-13
**Status:** Planning
**Related:** Unified Connector Architecture Plan

---

## Overview

Implement ArtifactStore as a WCF service for managing intermediate step outputs (artifacts) during pipeline execution. This provides a clean abstraction for artifact storage and retrieval, enabling future extensibility to distributed/persistent backends.

## Rationale

**Why a Service?**
- **Stateful** - maintains artifact storage during execution lifecycle
- **Multiple implementations** - InMemory (now), Redis/S3/HTTP (future)
- **Runtime configuration** - backend selection via config
- **Lifecycle management** - initialization, cleanup, resource management
- **Dependency injection** - injected into ArtifactConnector via ServiceContainer

**Consistency with WCF patterns:**
- Mirrors LLMService architecture (multiple providers, DI-based)
- Follows "Services for stateful infrastructure" principle (CLAUDE.md)
- Enables extensibility without modifying consumers (ArtifactConnector)

---

## High-Level Plan: ArtifactStore Service

### Phase 1: Design & Core Abstraction

1. **Design ArtifactStore interface** - Define core operations (save, get, exists, clear) and error handling
2. **Design service lifecycle** - Initialization, cleanup, resource management patterns
3. **Design configuration model** - Backend selection, storage options (memory limits, persistence paths)
4. **Define error hierarchy** - ArtifactNotFoundError, ArtifactStoreError, etc.

### Phase 2: Implementation

5. **Implement InMemoryArtifactStore** - Default implementation using dict-based storage
6. **Create service factory** - Factory pattern for creating store instances based on configuration
7. **Integrate with ServiceContainer** - Register ArtifactStore service in DI container
8. **Update Executor** - Inject ArtifactStore via ServiceContainer, use for artifact management

### Phase 3: Integration with ArtifactConnector

9. **Wire ArtifactConnector to store** - Pass ArtifactStore instance when creating ArtifactConnector
10. **Update connector factory** - ArtifactConnector factory receives store from Executor
11. **Test integration** - Ensure ArtifactConnector correctly retrieves from store

### Phase 4: Testing & Documentation

12. **Add unit tests** - Test InMemoryArtifactStore operations, error handling
13. **Add integration tests** - Test full pipeline with artifact storage
14. **Document service** - Architecture docs, usage examples
15. **Run full quality checks** - `./scripts/dev-checks.sh` to ensure everything passes

---

## Service Architecture

```
ServiceContainer
├── LLMService (existing)
│   ├── AnthropicService
│   ├── OpenAIService
│   └── GoogleService
└── ArtifactStore (new)
    ├── InMemoryArtifactStore (default)
    └── Future: RedisArtifactStore, S3ArtifactStore, HttpArtifactStore
```

---

## Interface Design (Conceptual)

**Core Operations:**
- `save(step_id: str, message: Message) -> None` - Store artifact from completed step
- `get(step_id: str) -> Message` - Retrieve artifact for downstream step
- `exists(step_id: str) -> bool` - Check if artifact exists
- `clear() -> None` - Cleanup all artifacts (end of execution)

**Error Handling:**
- Raise `ArtifactNotFoundError` if step_id doesn't exist
- Raise `ArtifactStoreError` for storage failures

---

## Configuration (Conceptual)

**Environment variables / Config:**
```python
ARTIFACT_STORE_BACKEND=memory  # memory, redis, s3, http
ARTIFACT_STORE_MEMORY_LIMIT=100  # Max artifacts in memory
```

**Future backends:**
- Redis: `ARTIFACT_STORE_REDIS_URL`, connection pooling
- S3: `ARTIFACT_STORE_S3_BUCKET`, serialization strategy
- HTTP: `ARTIFACT_STORE_HTTP_ENDPOINT`, authentication

---

## Integration with Unified Connector Architecture

**Dependency:** This service is required for the ArtifactConnector implementation.

**Execution flow:**
1. Executor receives ServiceContainer with ArtifactStore
2. Step 1 completes → Executor calls `store.save(step_id, message)`
3. Step 2 needs artifact → Executor creates ArtifactConnector with store
4. ArtifactConnector calls `store.get(step_id)` → returns Message
5. End of execution → Executor calls `store.clear()`

---

## Implementation Notes

- **Thread safety:** InMemoryArtifactStore must be thread-safe for future parallel execution
- **Message immutability:** Store references, not deep copies (Messages should be immutable)
- **Schema preservation:** Stored Messages retain schema metadata
- **Lifecycle:** Store is singleton per execution (tied to Executor lifecycle)

---

## Future Extensibility Examples

**Redis-backed storage** (distributed execution):
```python
class RedisArtifactStore(ArtifactStore):
    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url)

    def save(self, step_id: str, message: Message) -> None:
        serialized = pickle.dumps(message)
        self.client.set(f"artifact:{step_id}", serialized)
```

**S3-backed storage** (large datasets):
```python
class S3ArtifactStore(ArtifactStore):
    def __init__(self, bucket: str):
        self.s3 = boto3.client('s3')
        self.bucket = bucket

    def save(self, step_id: str, message: Message) -> None:
        serialized = pickle.dumps(message)
        self.s3.put_object(Bucket=self.bucket, Key=step_id, Body=serialized)
```

**HTTP-backed storage** (remote service):
```python
class HttpArtifactStore(ArtifactStore):
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def save(self, step_id: str, message: Message) -> None:
        self.session.post(f"{self.endpoint}/artifacts/{step_id}", json=message.to_dict())
```

---

**Estimated Scope:** ~200-250 LOC (service + tests)
**Breaking Changes:** None (internal implementation)
