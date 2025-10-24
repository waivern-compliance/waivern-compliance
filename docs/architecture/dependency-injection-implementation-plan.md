# Dependency Injection System Implementation Plan

**Status:** Approved
**Created:** 2025-10-23
**Updated:** 2025-10-24
**Related ADR:** [ADR-0002](../adr/0002-dependency-injection-for-service-management.md)
**Related Document:** [Component Factory DI Plan](./component-factory-di-plan.md)

## Executive Summary

This document outlines the implementation plan for introducing a **Dependency Injection (DI) system** into the Waivern Compliance Framework. The DI system extends beyond just replacing `LLMServiceManager` to include **all analysers and connectors** as DI-managed components via a factory pattern.

### Scope

1. **Generic DI Infrastructure** - ServiceContainer, protocols, lifecycle management in waivern-core
2. **Infrastructure Services** - LLM services managed via DI (singleton lifecycle)
3. **Component Factories** - Analysers and connectors as DI-managed components (factory pattern)
4. **Executor Integration** - WCT executor uses DI container for all service and component management

### Key Principles

- **Generic DI infrastructure** lives in `waivern-core/services/`
- **Service-specific DI adapters** live with their services (e.g., `waivern-llm/di/`)
- **Component factories** provide singleton factories that create transient instances
- **Three-tier architecture**: Infrastructure Services (singleton) → Factories (singleton) → Instances (transient)
- **Constructor injection** with explicit typed dependencies
- **No backwards compatibility** (pre-1.0 breaking changes accepted)

---

## Phase 0: Architecture Decision Record

**Goal:** Document decision and design before implementation

### Tasks

- [x] Create `docs/adr/0002-dependency-injection-for-service-management.md`
- [x] Document context, alternatives, decision, and consequences
- [x] Add component factory pattern section
- [x] Update `docs/adr/README.md` index
- [x] Create comprehensive reference: `docs/architecture/component-factory-di-plan.md`
- [x] Update this implementation plan with component factory phases

**Deliverable:** ADR approved and comprehensive documentation complete

---

## Phase 1: Core DI Infrastructure

**Goal:** Generic DI container in waivern-core

### 1.1 Create Package Structure

- [x] Create `libs/waivern-core/src/waivern_core/services/` directory
- [x] Create `__init__.py` with public API exports

### 1.2 Implement Service Protocols

- [x] Create `services/protocols.py`
- [x] Define `ServiceFactory[T]` protocol with `create()` and `can_create()`
- [x] Add comprehensive docstrings
- [x] Write integration tests for protocol (3 tests):
  - Container works with protocol-compliant factory
  - Factory availability indication through container
  - Container handles unavailable factory gracefully

**Note:** `ServiceProvider` protocol deferred - not needed for initial implementation

### 1.3 Implement Service Lifecycle

- [ ] Create `services/lifecycle.py`
- [ ] Implement `ServiceDescriptor[T]` dataclass
- [ ] Add lifetime management (singleton, transient)
- [ ] Add health check configuration
- [ ] Write unit tests (5+ tests)

### 1.4 Implement Service Container

- [ ] Create `services/container.py`
- [ ] Implement `ServiceContainer` class:
  - `register(service_type, factory, lifetime)` method
  - `get_service(service_type)` method with lazy creation
  - Singleton caching
  - Type-safe generics
- [ ] Add error handling (service not found, creation failures)
- [ ] Add logging for service lifecycle events
- [ ] Write comprehensive unit tests (20+ tests):
  - Service registration
  - Singleton caching
  - Transient creation
  - Error conditions
  - Multiple service types

### 1.5 Export from waivern-core

- [ ] Update `waivern_core/__init__.py` with service exports
- [ ] Add comprehensive module docstrings
- [ ] Run type checker (basedpyright strict)
- [ ] Run linter (ruff)

**Deliverable:** Generic DI container that works for any service type

---

## Phase 2: Component Factory Abstraction

**Goal:** Add ComponentFactory to waivern-core for analysers/connectors

### 2.1 Create ComponentFactory ABC

- [ ] Create `waivern_core/component_factory.py`
- [ ] Implement `ComponentFactory[T]` abstract base class:
  - `create(config: dict) -> T` - Create component with execution-specific config
  - `get_component_name() -> str` - Component type name for runbooks
  - `get_input_schemas() -> list[Schema]` - Supported input schemas
  - `get_output_schemas() -> list[Schema]` - Supported output schemas
  - `can_create(config: dict) -> bool` - Health check/validation
  - `get_service_dependencies() -> dict[str, type]` - Optional dependency declaration
- [ ] Add comprehensive docstrings with examples
- [ ] Add type hints with Generic[T]

### 2.2 Export from waivern-core

- [ ] Add to `waivern_core/__init__.py`
- [ ] Export ComponentFactory in public API

### 2.3 Unit Tests

- [ ] Create `tests/test_component_factory.py`
- [ ] Test ABC structure
- [ ] Test generic type handling
- [ ] Mock implementations for testing (5+ tests)

**Deliverable:** ComponentFactory abstraction available framework-wide

---

## Phase 3: LLM Service Integration

**Goal:** LLM as DI-managed service in waivern-llm/di/

### 3.1 Create LLM DI Package Structure

- [ ] Create `libs/waivern-llm/src/waivern_llm/di/` directory
- [ ] Create `__init__.py` with public API exports
- [ ] Add dependency on `waivern-core` in `pyproject.toml`

### 3.2 Implement LLM Service Factory

- [ ] Create `di/factory.py`
- [ ] Implement `LLMServiceFactory(ServiceFactory[BaseLLMService])`
- [ ] Wrap existing `waivern_llm.services.factory.LLMServiceFactory.create_service()`
- [ ] Implement `can_create()` validation logic
- [ ] Handle provider, model, api_key configuration
- [ ] Add detailed logging
- [ ] Write unit tests (8+ test cases)

### 3.3 Implement LLM Service Provider

- [ ] Create `di/provider.py`
- [ ] Implement `LLMServiceProvider(ServiceProvider)`
- [ ] Provide `get_llm_service()` convenience method
- [ ] Add `is_available` property
- [ ] Implement generic `get_service()` from protocol
- [ ] Write unit tests (6+ test cases)

### 3.4 Implement LLM Configuration

- [ ] Create `di/configuration.py`
- [ ] Implement `LLMServiceConfiguration` dataclass
- [ ] Add `from_dict()` factory method with validation
- [ ] Support health_check_enabled and health_check_interval
- [ ] Write unit tests (5+ test cases)

### 3.5 Integration Tests

- [ ] Write integration tests for full LLM service flow
- [ ] Test container + factory + provider working together
- [ ] Test with mock BaseLLMService
- [ ] Test graceful degradation when service unavailable
- [ ] Test singleton caching across multiple provider instances

**Deliverable:** LLM services managed via DI

---

## Phase 4: Analyser Factory Implementation

**Goal:** All analysers have DI-enabled factories

### 4.1 PersonalDataAnalyser

**Create factory:**
- [ ] Create `libs/waivern-personal-data-analyser/src/.../factory.py`
- [ ] Implement `PersonalDataAnalyserFactory(ComponentFactory[PersonalDataAnalyser])`
- [ ] Constructor accepts `llm_service: BaseLLMService | None`
- [ ] Implement all abstract methods (create, get_component_name, get_schemas, can_create)
- [ ] Add `get_service_dependencies()` returning `{"llm_service": BaseLLMService}`

**Update analyser:**
- [ ] Update `PersonalDataAnalyser.__init__()` signature:
  - `def __init__(self, config: PersonalDataAnalyserConfig, llm_service: BaseLLMService | None = None)`
- [ ] Remove `from_properties()` classmethod
- [ ] Update all internal references

**Update tests:**
- [ ] Update tests to use factory pattern
- [ ] Add factory unit tests
- [ ] Verify all existing tests still pass

### 4.2 ProcessingPurposeAnalyser

- [ ] Same steps as PersonalDataAnalyser
- [ ] Create factory in waivern-community package
- [ ] Update analyser constructor
- [ ] Remove `from_properties()`
- [ ] Update tests

### 4.3 DataSubjectAnalyser

- [ ] Same steps as PersonalDataAnalyser
- [ ] Create factory in waivern-community package
- [ ] Update analyser constructor
- [ ] Remove `from_properties()`
- [ ] Update tests

### 4.4 Export Factories

- [ ] Update `waivern-community/analysers/__init__.py`:
  ```python
  BUILTIN_ANALYSER_FACTORIES = [
      PersonalDataAnalyserFactory,
      ProcessingPurposeAnalyserFactory,
      DataSubjectAnalyserFactory,
  ]
  ```
- [ ] Remove old `BUILTIN_ANALYSERS` list

### 4.5 Update Base Classes

- [ ] Remove `from_properties()` from `waivern_core.Analyser` base class
- [ ] Update docstrings to reference factory pattern
- [ ] Update type hints

**Deliverable:** All 3 analysers DI-enabled with factories

---

## Phase 5: Connector Factory Implementation

**Goal:** All connectors have DI-enabled factories

### 5.1 FilesystemConnector

- [ ] Create `FilesystemConnectorFactory` in waivern-community
- [ ] Implement ComponentFactory[FilesystemConnector]
- [ ] Update connector constructor (no services needed currently)
- [ ] Remove `from_properties()`
- [ ] Update tests

### 5.2 SourceCodeConnector

- [ ] Create `SourceCodeConnectorFactory` in waivern-community
- [ ] Implement ComponentFactory[SourceCodeConnector]
- [ ] Update connector constructor
- [ ] Remove `from_properties()`
- [ ] Update tests

### 5.3 MySQLConnector

- [ ] Create `MySQLConnectorFactory` in waivern-mysql package
- [ ] Implement ComponentFactory[MySQLConnector]
- [ ] Constructor could accept `db_pool: DatabasePool | None` (future)
- [ ] Update connector constructor
- [ ] Remove `from_properties()`
- [ ] Update tests

### 5.4 SQLiteConnector

- [ ] Create `SQLiteConnectorFactory` in waivern-community
- [ ] Implement ComponentFactory[SQLiteConnector]
- [ ] Update connector constructor
- [ ] Remove `from_properties()`
- [ ] Update tests

### 5.5 Export Factories

- [ ] Update `waivern-community/connectors/__init__.py`:
  ```python
  BUILTIN_CONNECTOR_FACTORIES = [
      FilesystemConnectorFactory,
      SourceCodeConnectorFactory,
      SQLiteConnectorFactory,
  ]
  ```
- [ ] Update `waivern-mysql` to export `MySQLConnectorFactory`
- [ ] Remove old `BUILTIN_CONNECTORS` list

### 5.6 Update Base Classes

- [ ] Remove `from_properties()` from `waivern_core.Connector` base class
- [ ] Update docstrings to reference factory pattern
- [ ] Update type hints

**Deliverable:** All connectors DI-enabled with factories

---

## Phase 6: Executor Integration

**Goal:** Executor uses DI container and factories

### 6.1 Update Executor Class

- [ ] Update `Executor.__init__()` to accept `ServiceContainer`:
  ```python
  def __init__(self, container: ServiceContainer):
      self._container = container
      self.analyser_factories: dict[str, ComponentFactory[Analyser]] = {}
      self.connector_factories: dict[str, ComponentFactory[Connector]] = {}
  ```

- [ ] Update `create_with_built_ins()`:
  ```python
  @classmethod
  def create_with_built_ins(cls) -> Executor:
      # Create DI container
      container = ServiceContainer()

      # Register infrastructure services
      container.register(BaseLLMService, LLMServiceFactory(), lifetime="singleton")

      # Create executor
      executor = cls(container)

      # Get infrastructure services
      llm_service = container.get_service(BaseLLMService)

      # Register component factories with dependencies injected
      for factory_class in BUILTIN_ANALYSER_FACTORIES:
          factory = factory_class(llm_service=llm_service)
          executor.register_analyser_factory(factory)

      for factory_class in BUILTIN_CONNECTOR_FACTORIES:
          factory = factory_class()
          executor.register_connector_factory(factory)

      return executor
  ```

- [ ] Add `register_analyser_factory(factory: ComponentFactory[Analyser])`
- [ ] Add `register_connector_factory(factory: ComponentFactory[Connector])`
- [ ] Update `list_available_analysers()` to return factories
- [ ] Update `list_available_connectors()` to return factories

### 6.2 Update Component Instantiation

- [ ] Update `_instantiate_components()` method:
  ```python
  def _instantiate_components(
      self,
      analyser_type: str,
      connector_type: str,
      analyser_config: AnalyserConfig,
      connector_config: ConnectorConfig,
  ) -> tuple[Analyser, Connector]:
      # Get factories from registries
      analyser_factory = self.analyser_factories.get(analyser_type)
      if not analyser_factory:
          raise ExecutorError(f"Unknown analyser type: {analyser_type}")

      connector_factory = self.connector_factories.get(connector_type)
      if not connector_factory:
          raise ExecutorError(f"Unknown connector type: {connector_type}")

      # Check availability (health check for remote services)
      if not analyser_factory.can_create(analyser_config.properties):
          raise ExecutorError(f"Analyser unavailable with given config")

      if not connector_factory.can_create(connector_config.properties):
          raise ExecutorError(f"Connector unavailable with given config")

      # Create instances (transient lifecycle)
      analyser = analyser_factory.create(analyser_config.properties)
      connector = connector_factory.create(connector_config.properties)

      return analyser, connector
  ```

- [ ] Remove all direct `from_properties()` calls
- [ ] Add health checking via `can_create()`
- [ ] Add detailed logging for component creation

### 6.3 Update Executor Tests

- [ ] Update all executor tests to use factory pattern
- [ ] Test factory registration
- [ ] Test component creation via factories
- [ ] Test health checking (`can_create()`)
- [ ] Test error handling (unknown type, creation failure)
- [ ] Mock factories for unit tests
- [ ] Integration tests with real factories

**Deliverable:** Executor fully DI-integrated

---

## Phase 7: Testing & Documentation

**Goal:** Comprehensive tests and updated docs

### 7.1 Comprehensive Test Suite

- [ ] Ensure 90%+ test coverage for new DI code
- [ ] Unit tests for all protocols (5+ tests)
- [ ] Unit tests for ServiceDescriptor (5+ tests)
- [ ] Unit tests for ServiceContainer (20+ tests)
- [ ] Unit tests for LLMServiceFactory (8+ tests)
- [ ] Unit tests for LLMServiceProvider (6+ tests)
- [ ] Unit tests for LLMServiceConfiguration (5+ tests)
- [ ] Unit tests for ComponentFactory implementations (20+ tests)
- [ ] Integration tests (10+ tests)
- [ ] **Target: 80+ new tests for DI system**

### 7.2 Update Package Documentation

- [ ] Update `waivern-core/README.md`:
  - Add Services section
  - Document DI system overview
  - Provide usage examples
  - Document that services are available to all components
- [ ] Update inline documentation:
  - Comprehensive docstrings for all classes
  - Type hints with explanations
  - Usage examples in docstrings

### 7.3 Update Framework Documentation

- [ ] Update `CLAUDE.md`:
  - Add DI system overview
  - Document component factory pattern
  - Link to ADR-0002
  - Add Service Management section
  - Explain DI container role
  - Document service lifecycle
  - Document breaking changes (no `from_properties()`)
- [ ] Update `docs/wcf_core_concepts.md`:
  - Add ComponentFactory to core concepts
  - Explain factory pattern and three-tier architecture
  - Update component creation examples

**Deliverable:** Complete documentation suite

---

## Phase 8: Cleanup & Finalisation

**Goal:** Remove deprecated code, final verification

### 8.1 Code Review

- [ ] Self-review all new code
- [ ] Check for consistent naming conventions
- [ ] Verify all type hints are correct
- [ ] Ensure all docstrings are comprehensive
- [ ] Review error handling and logging

### 8.2 Performance Verification

- [ ] Benchmark service creation overhead
- [ ] Verify singleton caching works efficiently
- [ ] Check no memory leaks in long-running scenarios
- [ ] Profile analyser initialisation time

### 8.3 Final Testing

- [ ] Run full test suite (752+ existing + 80+ new tests)
- [ ] Run all sample runbooks
- [ ] Test with all three LLM providers (Anthropic, OpenAI, Google)
- [ ] Test service unavailable scenarios
- [ ] Verify graceful degradation

### 8.4 Release Preparation

- [ ] Create feature branch `feature/dependency-injection-system`
- [ ] Commit all changes with conventional commits
- [ ] Create comprehensive PR description
- [ ] Link to ADR-0002
- [ ] Request code review

**Deliverable:** Production-ready DI system with component factories

---

## Success Criteria

### Functionality ✅

- [ ] All existing tests pass (752+ tests)
- [ ] All new tests pass (80+ new DI tests)
- [ ] Sample runbooks execute successfully
- [ ] LLM services created and cached correctly
- [ ] Component factories create instances correctly
- [ ] Health checking works (`can_create()`)
- [ ] Graceful degradation when services unavailable

### Code Quality ✅

- [ ] Basedpyright type checking passes (strict mode)
- [ ] Ruff linting passes (no errors)
- [ ] Test coverage > 90% for new DI code
- [ ] All docstrings comprehensive and accurate
- [ ] Conventional commit messages throughout

### Documentation ✅

- [ ] ADR-0002 approved and published
- [ ] Component factory reference document complete
- [ ] Package README updated
- [ ] CLAUDE.md updated
- [ ] Implementation plan saved
- [ ] Inline documentation complete
- [ ] Breaking changes documented

### Extensibility ✅

- [ ] Easy to add new service types
- [ ] Clear patterns for future services
- [ ] No changes needed to waivern-core for new components
- [ ] Third-party components can register seamlessly
- [ ] Plugin architecture ready (component discovery, auto-injection)

---

## Architecture Overview

### Three-Tier Service Architecture

```
┌─────────────────────────────────────────────────┐
│ Tier 1: Infrastructure Services (Singleton)     │
│  - LLMService, DatabasePool, CacheService       │
│  - Managed by ServiceContainer                  │
└─────────────────────────────────────────────────┘
                    ↓ injected into
┌─────────────────────────────────────────────────┐
│ Tier 2: Component Factories (Singleton)         │
│  - PersonalDataAnalyserFactory                  │
│  - MySQLConnectorFactory                        │
│  - Registered in executor                       │
└─────────────────────────────────────────────────┘
                    ↓ create
┌─────────────────────────────────────────────────┐
│ Tier 3: Component Instances (Transient)         │
│  - PersonalDataAnalyser(config, llm_service)    │
│  - Created per execution step                   │
└─────────────────────────────────────────────────┘
```

### Package Structure

```
waivern-core/
├── services/                      # NEW: Generic DI infrastructure
│   ├── protocols.py               # ServiceFactory, ServiceProvider
│   ├── container.py               # ServiceContainer (DI core)
│   └── lifecycle.py               # ServiceDescriptor
└── component_factory.py           # NEW: Factory abstraction

waivern-llm/
├── services/                      # Pure LLM services (no DI)
│   ├── base.py
│   ├── anthropic.py
│   ├── factory.py
│   └── errors.py
└── di/                            # NEW: LLM DI adapters
    ├── factory.py                 # ServiceFactory[BaseLLMService]
    ├── provider.py                # LLMServiceProvider
    └── configuration.py           # Config types

waivern-personal-data-analyser/
├── analyser.py                    # PersonalDataAnalyser
└── factory.py                     # NEW: PersonalDataAnalyserFactory

waivern-mysql/
├── connector.py                   # MySQLConnector
└── factory.py                     # NEW: MySQLConnectorFactory

waivern-community/
├── analysers/
│   ├── processing_purpose_analyser/
│   │   ├── analyser.py
│   │   └── factory.py             # NEW
│   ├── data_subject_analyser/
│   │   ├── analyser.py
│   │   └── factory.py             # NEW
│   └── __init__.py                # Export BUILTIN_ANALYSER_FACTORIES
└── connectors/
    ├── filesystem/
    │   ├── connector.py
    │   └── factory.py             # NEW
    ├── source_code/
    │   ├── connector.py
    │   └── factory.py             # NEW
    ├── sqlite/
    │   ├── connector.py
    │   └── factory.py             # NEW
    └── __init__.py                # Export BUILTIN_CONNECTOR_FACTORIES

apps/wct/src/wct/
└── executor.py                    # UPDATED: Uses DI container + factories
```

---

## Risk Mitigation

### Risk: Performance regression

**Mitigation:** Benchmark before/after, singleton caching minimises overhead

### Risk: Test coverage gaps

**Mitigation:** Target 90%+ coverage, integration tests, comprehensive unit tests

### Risk: Complexity overwhelming contributors

**Mitigation:** Comprehensive documentation, clear examples, component-factory-di-plan.md reference

### Risk: Breaking changes affecting users

**Mitigation:** Pre-1.0 status, comprehensive migration guide, clear documentation of breaking changes

---

## Breaking Changes

### Removed

1. **`Analyser.from_properties()` classmethod**
   - Old: `analyser = AnalyserClass.from_properties(config)`
   - New: `analyser = factory.create(config)`

2. **`Connector.from_properties()` classmethod**
   - Old: `connector = ConnectorClass.from_properties(config)`
   - New: `connector = factory.create(config)`

3. **`BUILTIN_ANALYSERS` list**
   - Replaced with `BUILTIN_ANALYSER_FACTORIES`

4. **`BUILTIN_CONNECTORS` list**
   - Replaced with `BUILTIN_CONNECTOR_FACTORIES`

5. **Direct component instantiation in executor**
   - Now uses factory pattern

### Migration Path

**Before:**
```python
from waivern_community.analysers import BUILTIN_ANALYSERS

for analyser_class in BUILTIN_ANALYSERS:
    executor.register_available_analyser(analyser_class)

# Later
analyser = analyser_class.from_properties(config)
```

**After:**
```python
from waivern_community.analysers import BUILTIN_ANALYSER_FACTORIES
from waivern_core.services import ServiceContainer

container = ServiceContainer()
container.register(BaseLLMService, LLMServiceFactory(), lifetime="singleton")

llm_service = container.get_service(BaseLLMService)
for factory_class in BUILTIN_ANALYSER_FACTORIES:
    factory = factory_class(llm_service=llm_service)
    executor.register_analyser_factory(factory)

# Later
analyser = factory.create(config)
```

---

## Future Enhancements (Post-Implementation)

### Phase 9: Additional Infrastructure Services

- [ ] Database connection pool factory
- [ ] Cache service factory (Redis/Memcached)
- [ ] HTTP client factory
- [ ] Metrics/telemetry services

### Phase 10: Advanced DI Features

- [ ] Scoped lifetime (per-runbook execution)
- [ ] Service disposal and cleanup
- [ ] Health checking intervals
- [ ] Circuit breaker pattern for failed services
- [ ] Retry logic with exponential backoff
- [ ] Connection pooling support

### Phase 11: Plugin System (Monorepo Phase 5)

- [ ] Auto-discovery of third-party component factories
- [ ] Automatic dependency injection for plugins
- [ ] Plugin package validation
- [ ] Marketplace support for compliance components

---

## References

- [ADR-0002: Dependency Injection for Service Management](../adr/0002-dependency-injection-for-service-management.md)
- [Component Factory DI Plan](./component-factory-di-plan.md) - Comprehensive reference
- [Monorepo Migration Plan - Phase 5](./monorepo-migration-plan.md#phase-5-dynamic-plugin-loading)
- [WCF Core Concepts](../wcf_core_concepts.md)
