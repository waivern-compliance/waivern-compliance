# Dependency Injection System Implementation Plan

**Status:** Complete (All Phases 0-6 Complete - Framework Fully DI-Enabled)
**Created:** 2025-10-23
**Updated:** 2025-10-30
**Related ADR:** [ADR-0002](../adr/0002-dependency-injection-for-service-management.md)
**Related Document:** [DI Factory Patterns](./di-factory-patterns.md)

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

## Phase 0: Architecture Decision Record ✅

**Goal:** Document decision and design before implementation

### Tasks

- [x] Create `docs/adr/0002-dependency-injection-for-service-management.md`
- [x] Document context, alternatives, decision, and consequences
- [x] Add component factory pattern section
- [x] Update `docs/adr/README.md` index
- [x] Create comprehensive reference: `docs/architecture/di-factory-patterns.md`
- [x] Update this implementation plan with component factory phases

**Deliverable:** ADR approved and comprehensive documentation complete

---

## Phase 1: Core DI Infrastructure ✅

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

- [x] Create `services/lifecycle.py`
- [x] Implement `ServiceDescriptor[T]` dataclass
- [x] Add lifetime management (singleton, transient)

**Note:** Health check configuration deferred - `ServiceFactory.can_create()` provides health checking. Tests not needed - dataclass has no business logic to test.

### 1.4 Implement Service Container

- [x] Create `services/container.py`
- [x] Implement `ServiceContainer` class:
  - `register(service_type, factory, lifetime)` method
  - `get_service(service_type)` method with lazy creation
  - Singleton caching
  - Type-safe generics
- [x] Add error handling (service not found, creation failures)
- [x] Add logging for service lifecycle events
- [x] Write comprehensive unit tests (10 tests):
  - Service registration
  - Singleton caching
  - Transient creation
  - Error conditions
  - Multiple service types

### 1.5 Export from waivern-core

- [x] Update `waivern_core/__init__.py` with service exports
- [x] Add comprehensive module docstrings
- [x] Run type checker (basedpyright strict)
- [x] Run linter (ruff)

**Deliverable:** Generic DI container that works for any service type

---

## Phase 2: Component Factory Abstraction ✅

**Goal:** Add ComponentFactory to waivern-core for analysers/connectors

### 2.1 Create ComponentFactory ABC

- [x] Create `waivern_core/component_factory.py`
- [x] Implement `ComponentFactory[T]` abstract base class:
  - `create(config: ComponentConfig) -> T` - Create component with execution-specific config
  - `get_component_name() -> str` - Component type name for runbooks
  - `get_input_schemas() -> list[Schema]` - Supported input schemas
  - `get_output_schemas() -> list[Schema]` - Supported output schemas
  - `can_create(config: ComponentConfig) -> bool` - Health check/validation
  - `get_service_dependencies() -> dict[str, type]` - Optional dependency declaration
- [x] Add comprehensive docstrings with examples
- [x] Add type hints with Generic[T] (using PEP 695 syntax)
- [x] Add ComponentConfig type alias (`type ComponentConfig = dict[str, Any]`)

### 2.2 Export from waivern-core

- [x] Add to `waivern_core/__init__.py`
- [x] Export ComponentFactory and ComponentConfig in public API

### 2.3 Contract Testing Pattern

- [x] Create `tests/test_component_factory.py`
- [x] Implement `ComponentFactoryContractTests[T]` abstract test class
- [x] Define 7 behavioral contract tests for factory implementations
- [x] Test default `get_service_dependencies()` implementation
- [x] Add comprehensive documentation explaining contract testing pattern

**Deliverable:** ComponentFactory abstraction available framework-wide with contract testing pattern

---

## Phase 3: LLM Service Integration ✅

**Goal:** LLM as DI-managed service in waivern-llm/di/

### 3.1 Create LLM DI Package Structure

- [x] Create `libs/waivern-llm/src/waivern_llm/di/` directory
- [x] Create `__init__.py` with public API exports
- [x] Add dependency on `waivern-core` in `pyproject.toml`

### 3.2 Implement LLM Service Factory

- [x] Create `di/factory.py`
- [x] Implement `LLMServiceFactory(ServiceFactory[BaseLLMService])`
- [x] Wrap existing `waivern_llm.factory.LLMServiceFactory.create_service()`
- [x] Implement `can_create()` validation logic
- [x] Handle provider, model, api_key configuration
- [x] Add detailed logging
- [x] Write unit tests (8 tests)

### 3.3 Implement LLM Service Provider

- [x] Create `di/provider.py`
- [x] Implement `LLMServiceProvider(ServiceProvider)`
- [x] Provide `get_llm_service()` convenience method
- [x] Add `is_available` property
- [x] Implement generic `get_service()` from protocol
- [x] Write unit tests (6 tests)

### 3.4 Implement LLM Configuration

- [x] Create `di/configuration.py`
- [x] Implement `LLMServiceConfiguration` (Pydantic BaseModel)
- [x] Add `from_properties()` factory method with validation
- [x] Write unit tests (10 tests)
- [x] Refactor LLMServiceFactory to use configuration (eliminate duplication)

### 3.5 Integration Tests

- [x] Write integration tests for full LLM service flow (8 tests)
- [x] Test container + factory + provider working together
- [x] Test with real BaseLLMService
- [x] Test graceful degradation when service unavailable
- [x] Test singleton caching across multiple provider instances

### 3.6 Component Configuration Base Class

- [x] Create `BaseComponentConfiguration` in `waivern_core/services/configuration.py`
- [x] Implement with Pydantic BaseModel (frozen, extra="forbid")
- [x] Add `from_properties()` factory method for dictionary-based creation
- [x] Mirror same design pattern as `BaseServiceConfiguration`
- [x] Update `ComponentConfig` type alias to `dict[str, Any]` (factories parse internally)
- [x] Export from `waivern_core/services/__init__.py` and `waivern_core/__init__.py`
- [x] Write unit tests (4 tests for instantiation, immutability, validation, from_properties)
- [x] Update ComponentFactory contract tests to use typed configs

**Deliverable:** LLM services managed via DI + BaseComponentConfiguration implemented (36 tests, all passing)

---

## Phase 4: Analyser Factory Implementation ✅

**Status:** ✅ Complete (All 3 Analysers DI-Enabled)
**Goal:** All analysers have DI-enabled factories

### Common Implementation Pattern

All three analysers followed these steps:

1. **Configuration Migration** - Inherit from `BaseComponentConfiguration` (from Pydantic `BaseModel`)
2. **Constructor Update** - Change from 3 params (config, pattern_matcher, llm_service_manager) to 2 params (config, llm_service)
3. **Pattern Matcher** - Create internally from config (not a service dependency)
4. **LLM Service** - Direct `BaseLLMService | None` injection (replaces `LLMServiceManager`)
5. **from_properties()** - Update to DI-aware wrapper for backward compatibility (removed in Phase 6)
6. **Factory Creation** - Implement `ComponentFactory[T]` with 6 abstract methods
7. **Factory Tests** - 8 tests (6 contract + 2 factory-specific)
8. **Analyser Tests** - Update to use direct DI constructor instead of `from_properties()`
9. **Export** - Add factory to package `__init__.py`

**Key Lessons Learned:**
- **Standalone package architecture** - PersonalDataAnalyser required moving prompts from waivern-community
- **Test DI constructors directly** - Don't use `from_properties()` in tests (Phase 4.3 discovery)
- **Pattern matcher is not a dependency** - Created from config, not shared across instances
- **LLM service is a shared dependency** - Injected as singleton infrastructure service

### 4.1 PersonalDataAnalyser ✅

**Location:** `libs/waivern-personal-data-analyser/`
**Unique Aspects:** Resolved circular dependency by moving prompts from waivern-community to standalone package
**Tests:** 807 tests passing + 8 factory tests
**Commits:** Multiple commits during Phase 4.1

### 4.2 ProcessingPurposeAnalyser ✅

**Location:** `libs/waivern-community/analysers/processing_purpose_analyser/`
**Unique Aspects:**
- Supports 2 input schemas (StandardInputSchema, SourceCodeSchema)
- Added integration tests with real LLM API (2 tests marked `@pytest.mark.integration`)
**Tests:** 815 tests passing + 8 factory tests + 2 integration tests
**Commits:**
- `feat: complete ProcessingPurposeAnalyser DI migration` (aeb6601)
- `fix: implement proper DI-aware from_properties() wrapper` (95fedbb)
- `test: add integration tests with real LLM` (3af9bf8)

### 4.3 DataSubjectAnalyser ✅

**Location:** `libs/waivern-community/analysers/data_subject_analyser/`
**Unique Aspects:**
- Only supports StandardInputSchema (simpler than ProcessingPurposeAnalyser)
- Discovered and fixed test quality issue: 6 analyser tests + 1 ProcessingPurposeAnalyser test were using `from_properties()` instead of direct DI constructor
**Tests:** 823 tests passing + 8 factory tests
**Commits:** `feat: migrate DataSubjectAnalyser to DI with ComponentFactory pattern` (548d2b5)

**Phase 4 Deliverable:** All 3 analysers DI-enabled with factories, backward compatible via `from_properties()` (removed in Phase 6)

---

## Phase 5: Connector Factory Implementation

**Goal:** All connectors have DI-enabled factories

### 5.1 FilesystemConnector

- [x] Create `FilesystemConnectorFactory` in waivern-community
- [x] Implement ComponentFactory[FilesystemConnector]
- [x] Update connector constructor (no services needed currently)
- [ ] Remove `from_properties()` (deferred to Phase 6.4)
- [x] Update tests

**Completed:** Issue #176, PR #177 (merged Oct 29, 2025)

### 5.2 SourceCodeConnector

- [x] Create `SourceCodeConnectorFactory` in waivern-community
- [x] Implement ComponentFactory[SourceCodeConnector]
- [x] Update connector constructor
- [ ] Remove `from_properties()` (deferred to Phase 6.4)
- [x] Update tests

**Completed:** Issue #180, PR #181 (merged Oct 30, 2025)

### 5.3 MySQLConnector

- [x] Create `MySQLConnectorFactory` in waivern-mysql package
- [x] Implement ComponentFactory[MySQLConnector]
- [x] Constructor could accept `db_pool: DatabasePool | None` (future)
- [x] Update connector constructor
- [ ] Remove `from_properties()` (deferred to Phase 6.4)
- [x] Update tests

**Completed:** Issue #178, PR #179 (merged Oct 30, 2025)

### 5.4 SQLiteConnector

- [x] Create `SQLiteConnectorFactory` in waivern-community
- [x] Implement ComponentFactory[SQLiteConnector]
- [x] Update connector constructor
- [ ] Remove `from_properties()` (deferred to Phase 6.4)
- [x] Update tests

**Completed:** Issue #182, PR #183 (merged Oct 30, 2025)

### 5.5 Export Factories

- [x] Export each connector factory from its package `__init__.py`
  - [x] MySQLConnectorFactory exported from waivern-mysql
  - [x] FilesystemConnectorFactory, SourceCodeConnectorFactory, SQLiteConnectorFactory exported from waivern-community
- [x] Update docstrings to reference factory pattern

**Completed:** All factories exported and documented

**Deliverable:** All connectors DI-enabled with factories, backward compatible via `from_properties()`

---

**Phase 5 Status: ✅ Complete** - All 4 connectors have DI-enabled factories with contract tests. Backward compatibility maintained via `from_properties()` wrappers (to be removed in Phase 6.4).

---

## Phase 6: Executor Integration ✅

**Status:** ✅ Complete (Executor DI-Enabled)
**Goal:** Executor uses DI container and factories

### 6.1 Update Executor Class ✅

- [x] Update `Executor.__init__()` to accept `ServiceContainer`
- [x] Update `create_with_built_ins()` to use DI container
- [x] Add `register_analyser_factory()` and `register_connector_factory()`
- [x] Update `list_available_analysers()` and `list_available_connectors()` to return factories
- [x] Direct factory registration with injected dependencies

### 6.2 Update Component Instantiation ✅

- [x] Update `_instantiate_components()` to use factory pattern
- [x] Pass raw dict properties to factory `create()` and `can_create()`
- [x] Add availability checking via `can_create()`
- [x] Factories parse config internally using `from_properties()`
- [x] Add detailed error messages and logging

### 6.3 Update Executor Tests ✅

- [x] Update all 34 executor and integration tests
- [x] Add LLM service mocking to avoid requiring API keys
- [x] Test factory registration and component creation
- [x] Test availability checking and error handling
- [x] All 847 tests passing, 0 type errors

### 6.4 Remove Backward Compatibility Wrappers ✅

**Status:** ✅ Complete

- [x] Remove `from_properties()` from all analyser implementations:
  - [x] Remove from `PersonalDataAnalyser` (waivern-personal-data-analyser)
  - [x] Remove from `ProcessingPurposeAnalyser` (waivern-community)
  - [x] Remove from `DataSubjectAnalyser` (waivern-community)
- [x] Remove `from_properties()` from all connector implementations:
  - [x] Remove from `FilesystemConnector` (waivern-community)
  - [x] Remove from `SourceCodeConnector` (waivern-community)
  - [x] Remove from `SQLiteConnector` (waivern-community)
  - [x] Remove from `MySQLConnector` (waivern-mysql)
- [x] Remove `from_properties()` abstract method from base classes:
  - [x] Remove from `waivern_core.Analyser` base class
  - [x] Remove from `waivern_core.Connector` base class
- [x] Update base class docstrings to reference factory pattern only
- [x] Update base class type hints
- [x] Verify all tests still pass (845 tests passing)
- [x] Run full integration test suite
- [x] Add config validation tests to close coverage gap (8 new tests)

**Deliverable:** Breaking change complete. All `from_properties()` methods removed. Framework fully DI-enabled. Test coverage maintained (845 tests passing, coverage improved through better organization).

### Phase 6 Summary

**Status:** ✅ **COMPLETE**

Phase 6 successfully migrated the Executor to use DI container and ComponentFactory pattern, then removed all backward compatibility wrappers. This was the final integration step.

**Commits:**
1. `c285104` - docs: update the DI implementation plan
2. `548d2b5` - feat: migrate DataSubjectAnalyser to DI with ComponentFactory pattern (Phases 6.1-6.3)
3. `9ddd67b` - feat!: remove from_properties() backward compatibility layer (Phase 6.4)
4. `328a0a4` - test: add config validation tests for ProcessingPurposeAnalyserConfig

**Test Results:**
- All 845 tests passing (837 existing + 8 new config tests)
- 10 obsolete tests removed (validated at wrong layer)
- 4 tests updated to use factory pattern
- Coverage gap analysis: 100% of requirements from deleted tests still covered

**Key Achievements:**
- Executor fully DI-integrated
- All 7 component factories registered and working
- ServiceContainer managing singleton LLM service
- ComponentFactory pattern enforced throughout
- No `from_properties()` methods remaining
- Config validation moved to dedicated test files (better organization)

**Branch:** `feature/executor-di-integration` (ready for PR)

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
│   │   └── factory.py             # NEW: Exported from package __init__.py
│   ├── data_subject_analyser/
│   │   ├── analyser.py
│   │   └── factory.py             # NEW: Exported from package __init__.py
│   └── __init__.py                # No BUILTIN_ANALYSER_FACTORIES list
└── connectors/
    ├── filesystem/
    │   ├── connector.py
    │   └── factory.py             # NEW: Exported from package __init__.py
    ├── source_code/
    │   ├── connector.py
    │   └── factory.py             # NEW: Exported from package __init__.py
    ├── sqlite/
    │   ├── connector.py
    │   └── factory.py             # NEW: Exported from package __init__.py
    └── __init__.py                # No BUILTIN_CONNECTOR_FACTORIES list

apps/wct/src/wct/
└── executor.py                    # UPDATED: Direct factory imports + registration
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
   - Replaced with direct factory registration in executor

4. **`BUILTIN_CONNECTORS` list**
   - Replaced with direct factory registration in executor

5. **Direct component instantiation in executor**
   - Now uses factory pattern

**Note:** No intermediate `BUILTIN_ANALYSER_FACTORIES` or `BUILTIN_CONNECTOR_FACTORIES` lists are created. The executor uses direct imports and registration or dynamic discovery.

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
from waivern_core.services import ServiceContainer
from waivern_llm.di import LLMServiceFactory
from waivern_llm import BaseLLMService
from waivern_personal_data_analyser import PersonalDataAnalyserFactory
from waivern_community.analysers.processing_purpose_analyser import ProcessingPurposeAnalyserFactory
from waivern_community.analysers.data_subject_analyser import DataSubjectAnalyserFactory

# Create DI container and register services
container = ServiceContainer()
container.register(BaseLLMService, LLMServiceFactory(), lifetime="singleton")
llm_service = container.get_service(BaseLLMService)

# Create executor
executor = Executor(container)

# Register factories directly (no intermediate list)
executor.register_analyser_factory(PersonalDataAnalyserFactory(llm_service))
executor.register_analyser_factory(ProcessingPurposeAnalyserFactory(llm_service))
executor.register_analyser_factory(DataSubjectAnalyserFactory(llm_service))

# Later - executor gets factory by component name and creates instance
analyser = executor.create_analyser("personal_data", config)
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
- [DI Factory Patterns](./di-factory-patterns.md) - Comprehensive reference
- [Monorepo Migration Plan - Phase 5](./monorepo-migration-plan.md#phase-5-dynamic-plugin-loading)
- [WCF Core Concepts](../wcf_core_concepts.md)
