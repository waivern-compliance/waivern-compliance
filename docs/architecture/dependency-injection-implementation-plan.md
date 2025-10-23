# Dependency Injection System Implementation Plan

**Status:** Approved
**Created:** 2025-10-23
**Related ADR:** [ADR-0002](../adr/0002-dependency-injection-for-service-management.md)

## Executive Summary

This document outlines the implementation plan for introducing a **Dependency Injection (DI) system** into the Waivern Compliance Framework. The DI system will replace the current `LLMServiceManager` with a generic, extensible service management solution that can handle LLM services, databases, caches, and any future services.

**Key Principle:** `waivern-llm` stays clean as a pure service library with NO DI knowledge. The DI layer lives in `waivern-core` as foundational infrastructure available to all components (connectors, analysers, tools).

---

## Phase 0: Architecture Decision Record

### Create ADR-0002
- [ ] Write `docs/adr/0002-dependency-injection-for-service-management.md`
- [ ] Document context, alternatives, decision, and consequences
- [ ] Get team review and approval
- [ ] Update `docs/adr/README.md` index
- [ ] Link from `CLAUDE.md`
- [ ] Save detailed implementation plan to `docs/architecture/di-implementation-plan.md`

**Deliverable:** ADR approved and documented before any code changes

---

## Phase 1: Core DI Infrastructure

### 1.1 Create Package Structure
- [ ] Create `libs/waivern-core/src/waivern_core/services/` directory
- [ ] Create `__init__.py` with public API exports
- [ ] Create `libs/waivern-core/src/waivern_core/services/llm/` directory

### 1.2 Implement Service Protocols
- [ ] Create `services/protocols.py`
- [ ] Define `ServiceFactory[T]` protocol with `create()` and `can_create()`
- [ ] Define `ServiceProvider` protocol with `get_service()` and `is_available()`
- [ ] Add comprehensive docstrings
- [ ] Write unit tests for protocol compliance

### 1.3 Implement Service Lifecycle
- [ ] Create `services/lifecycle.py`
- [ ] Implement `ServiceDescriptor[T]` dataclass
- [ ] Add lifetime management (singleton, transient)
- [ ] Add health check configuration
- [ ] Write unit tests (10+ test cases)

### 1.4 Implement Service Container
- [ ] Create `services/container.py`
- [ ] Implement `ServiceContainer` class with:
  - `register()` method for service registration
  - `get_service()` method for lazy creation and caching
  - `is_healthy()` method for health checking
  - Singleton instance management
  - Transient instance creation
  - Failed service tracking (no infinite retries)
  - `clear()` method for testing
- [ ] Write comprehensive unit tests (20+ test cases):
  - Singleton caching behaviour
  - Transient instance creation
  - Failed service handling
  - Health checking logic
  - Concurrent access (if needed)

**Deliverable:** Generic DI container that works for any service type

---

## Phase 2: LLM Service Integration

### 2.1 Implement LLM Service Factory
- [ ] Create `services/llm/factory.py`
- [ ] Implement `LLMServiceFactory(ServiceFactory[BaseLLMService])`
- [ ] Wrap `waivern_llm.LLMServiceFactory.create_service()`
- [ ] Add `can_create()` validation logic
- [ ] Handle provider, model, api_key configuration
- [ ] Add detailed logging
- [ ] Write unit tests (8+ test cases)

### 2.2 Implement LLM Service Provider
- [ ] Create `services/llm/provider.py`
- [ ] Implement `LLMServiceProvider(ServiceProvider)`
- [ ] Provide `get_llm_service()` convenience method
- [ ] Add `is_available` property
- [ ] Implement generic `get_service()` and `is_available()` from protocol
- [ ] Write unit tests (6+ test cases)

### 2.3 Implement LLM Configuration
- [ ] Create `services/llm/configuration.py`
- [ ] Implement `LLMServiceConfiguration` dataclass
- [ ] Add `from_dict()` factory method with validation
- [ ] Support health_check_enabled and health_check_interval
- [ ] Write unit tests (5+ test cases)

### 2.4 Integration Tests
- [ ] Write integration tests for full LLM service flow
- [ ] Test container + factory + provider working together
- [ ] Test with mock BaseLLMService
- [ ] Test graceful degradation when service unavailable
- [ ] Test singleton caching across multiple provider instances

**Deliverable:** Working LLM service integration via DI system

---

## Phase 3: Analyser Migration

### 3.1 Update PersonalDataAnalyser
- [ ] Update `from_properties()` to create `ServiceContainer`
- [ ] Register `BaseLLMService` with `LLMServiceFactory`
- [ ] Create `LLMServiceProvider` instance
- [ ] Update constructor to accept `LLMServiceProvider` instead of `LLMServiceManager`
- [ ] Update `_validate_with_llm()` to use `provider.get_llm_service()`
- [ ] Update all tests to use new approach
- [ ] Verify 752 tests still pass

### 3.2 Update ProcessingPurposeAnalyser
- [ ] Same steps as PersonalDataAnalyser
- [ ] Update constructor and `from_properties()`
- [ ] Update LLM usage sites
- [ ] Update tests
- [ ] Verify tests pass

### 3.3 Update DataSubjectAnalyser
- [ ] Same steps as PersonalDataAnalyser
- [ ] Update constructor and `from_properties()`
- [ ] Update LLM usage sites
- [ ] Update tests
- [ ] Verify tests pass

### 3.4 Verify All Analysers
- [ ] Run full test suite (752+ tests)
- [ ] Run sample runbooks to verify end-to-end
- [ ] Check type checking passes (basedpyright strict)
- [ ] Check linting passes (ruff)

**Deliverable:** All analysers using new DI system

---

## Phase 4: Testing & Documentation

### 4.1 Comprehensive Test Suite
- [ ] Ensure 90%+ test coverage for new DI code
- [ ] Unit tests for all protocols (5+ tests)
- [ ] Unit tests for ServiceDescriptor (5+ tests)
- [ ] Unit tests for ServiceContainer (20+ tests)
- [ ] Unit tests for LLMServiceFactory (8+ tests)
- [ ] Unit tests for LLMServiceProvider (6+ tests)
- [ ] Unit tests for LLMServiceConfiguration (5+ tests)
- [ ] Integration tests (10+ tests)
- [ ] **Target: 60+ new tests for DI system**

### 4.2 Update Package Documentation
- [ ] Update `waivern-core/README.md`:
  - Add Services section
  - Document DI system overview
  - Provide usage examples
  - Document that services are available to all components
- [ ] Update inline documentation:
  - Comprehensive docstrings for all classes
  - Type hints with explanations
  - Usage examples in docstrings

### 4.3 Update Framework Documentation
- [ ] Update `CLAUDE.md`:
  - Add DI system overview
  - Document service management pattern
  - Link to ADR-0002
  - Add examples for future services
- [ ] Update `docs/wcf_core_concepts.md`:
  - Add Service Management section
  - Explain DI container role
  - Document service lifecycle

**Deliverable:** Complete documentation suite

---

## Phase 5: Cleanup & Finalisation

### 5.1 Code Review
- [ ] Self-review all new code
- [ ] Check for consistent naming conventions
- [ ] Verify all type hints are correct
- [ ] Ensure all docstrings are comprehensive
- [ ] Review error handling and logging

### 5.2 Performance Verification
- [ ] Benchmark service creation overhead
- [ ] Verify singleton caching works efficiently
- [ ] Check no memory leaks in long-running scenarios
- [ ] Profile analyser initialisation time

### 5.3 Final Testing
- [ ] Run full test suite (752+ new tests)
- [ ] Run all sample runbooks
- [ ] Test with all three LLM providers (Anthropic, OpenAI, Google)
- [ ] Test service unavailable scenarios
- [ ] Verify graceful degradation

### 5.4 Release Preparation
- [ ] Create feature branch `feature/dependency-injection-system`
- [ ] Commit all changes with conventional commits
- [ ] Create comprehensive PR description
- [ ] Link to ADR-0002
- [ ] Request code review

**Deliverable:** Production-ready DI system

---

## Success Criteria

### Functionality ✅
- [ ] All existing tests pass (752+ tests)
- [ ] All new tests pass (60+ new DI tests)
- [ ] Sample runbooks execute successfully
- [ ] LLM services created and cached correctly
- [ ] Graceful degradation when services unavailable

### Code Quality ✅
- [ ] Basedpyright type checking passes (strict mode)
- [ ] Ruff linting passes (no errors)
- [ ] Test coverage > 90% for new DI code
- [ ] All docstrings comprehensive and accurate
- [ ] Conventional commit messages throughout

### Documentation ✅
- [ ] ADR-0002 approved and published
- [ ] Package README updated
- [ ] CLAUDE.md updated
- [ ] Implementation plan saved
- [ ] Inline documentation complete

### Extensibility ✅
- [ ] Easy to add new service types
- [ ] Clear patterns for future services
- [ ] No changes needed to waivern-llm
- [ ] Third-party services can be added

---

## Architecture Overview

### Package Responsibilities

```
waivern-llm                          # Infrastructure Layer (UNCHANGED)
├── BaseLLMService                   # Abstract interface
├── AnthropicLLMService             # Concrete implementations
├── LLMServiceFactory               # Simple provider selection
└── Errors (LLMServiceError, etc)   # Error types

waivern-core                         # Core Framework (NEW DI SYSTEM)
├── abstractions/                    # Existing: Connector, Analyser
├── schemas/                         # Existing: Schema, Message
└── services/                        # NEW: Generic DI framework
    ├── protocols.py                 # Service abstractions
    ├── container.py                 # ServiceContainer (DI core)
    ├── lifecycle.py                 # ServiceDescriptor, lifecycle management
    ├── llm/                         # LLM-specific adapters
    │   ├── factory.py               # LLMServiceFactory (DI adapter)
    │   ├── provider.py              # LLMServiceProvider (high-level API)
    │   └── configuration.py         # LLMServiceConfiguration
    └── __init__.py                  # Public API exports

waivern-analysers-shared             # Analyser utilities
└── utilities/
    └── llm_service_manager.py       # Current location (will be replaced)
```

**Why `waivern-core`?**
- Service management is foundational infrastructure, like schemas/messages
- Available to all components: connectors, analysers, future tools
- Connectors may need services (database pools, caches, HTTP clients)
- Clean dependency: all components already depend on `waivern-core`

### Layered Interaction

```
┌─────────────────────────────────────────┐
│ Analyser (e.g., PersonalDataAnalyser)  │
│  - Uses: LLMServiceProvider             │
└──────────────┬──────────────────────────┘
               │ get_llm_service()
               ↓
┌──────────────────────────────────────────┐
│ LLMServiceProvider (DI Layer)           │
│  - Manages: lifecycle, health, config   │
│  - Uses: ServiceContainer                │
└──────────────┬───────────────────────────┘
               │ get_service(BaseLLMService)
               ↓
┌──────────────────────────────────────────┐
│ ServiceContainer (DI Core)              │
│  - Manages: singleton instances          │
│  - Uses: LLMServiceFactory               │
└──────────────┬───────────────────────────┘
               │ factory.create()
               ↓
┌──────────────────────────────────────────┐
│ LLMServiceFactory (DI Adapter)          │
│  - Wraps: waivern-llm factory            │
│  - Adds: retry, config, validation       │
└──────────────┬───────────────────────────┘
               │ WaivernLLMFactory.create_service()
               ↓
┌──────────────────────────────────────────┐
│ waivern-llm (Infrastructure)            │
│  - Creates: AnthropicLLMService          │
│  - NO DI KNOWLEDGE                       │
└──────────────────────────────────────────┘
```

---

## Risk Mitigation

### Risk: Performance regression
**Mitigation:** Benchmark before/after, singleton caching minimizes overhead

### Risk: Test coverage gaps
**Mitigation:** Target 90%+ coverage, integration tests, comprehensive unit tests

---

## Future Enhancements (Post-Initial Release)

### Phase 7: Additional Services (Future)
- [ ] Database connection pool service
- [ ] Cache service (Redis, Memcached)
- [ ] HTTP client service
- [ ] Metrics/telemetry service
- [ ] Message queue service

### Phase 8: Advanced Features (Future)
- [ ] Scoped services (per-request lifetime)
- [ ] Service discovery (dynamic registration)
- [ ] Circuit breaker pattern for failed services
- [ ] Retry logic with exponential backoff
- [ ] Connection pooling support


---

## Code Examples

### Registration (New DI System)
```python
from waivern_llm import BaseLLMService
from waivern_core.services import ServiceContainer
from waivern_core.services.llm import LLMServiceFactory, LLMServiceProvider

# Create container
container = ServiceContainer()

# Register LLM service with DI-aware factory
container.register(
    BaseLLMService,                           # Service type (from waivern-llm)
    LLMServiceFactory(                        # DI adapter factory
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
    ),
    lifetime="singleton"
)

# Create provider
provider = LLMServiceProvider(container)
```

### Consumption (Analyser Usage)
```python
class PersonalDataAnalyser(Analyser):
    def __init__(
        self,
        config: PersonalDataAnalyserConfig,
        llm_provider: LLMServiceProvider,  # High-level provider
    ):
        self._config = config
        self._llm_provider = llm_provider

    def _validate_with_llm(self, findings):
        # Get service through provider
        llm_service = self._llm_provider.get_llm_service()  # Returns BaseLLMService | None

        if llm_service is None:
            logger.warning("LLM service not available")
            return findings

        # Use the service (same API as before!)
        result = llm_service.analyse_data(content, prompt)
        # ...
```

### Testing (Mock Services)
```python
# Test with mock LLM service
class MockLLMService(BaseLLMService):
    def analyse_data(self, text, prompt):
        return '{"result": "mock"}'

# Register mock in container
container.register(
    BaseLLMService,
    lambda: MockLLMService(),  # Simple factory
    lifetime="singleton"
)

# Test analyser with mock
provider = LLMServiceProvider(container)
analyser = PersonalDataAnalyser(config, provider)
```

---

## References

- **ADR-0002:** `docs/adr/0002-dependency-injection-for-service-management.md`
- **ADR-0001:** `docs/adr/0001-explicit-schema-loading-over-autodiscovery.md`
- **.NET Core DI:** https://docs.microsoft.com/en-us/dotnet/core/extensions/dependency-injection
- **Spring Framework:** https://spring.io/guides/gs/spring-boot/
- **Python dependency-injector:** https://python-dependency-injector.ets-labs.org/
- **Michael Nygard ADR template:** https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
