# Component Factory Pattern - DI Integration Plan

**Status:** Proposed
**Created:** 2025-10-24
**Related:** [ADR-0002](../adr/0002-dependency-injection-for-service-management.md)

## Executive Summary

This document outlines the plan to integrate analysers and connectors into the Dependency Injection (DI) system using a **component factory pattern**. This enables:

- **AI agent discovery:** Agents can query available analysers by capability/schema
- **Plugin architecture:** Third-party components register seamlessly
- **Remote services:** Health checking and SaaS analyser integration
- **Unified pattern:** Same approach for analysers, connectors, and future components

## Rationale

### Why Analysers & Connectors as DI Services?

#### 1. WCT Orchestration Context

WCT is a middleware/orchestrator that:
- Doesn't need intimate knowledge of how components work internally
- Communicates through schema contracts (Message objects)
- Needs to swap components in/out dynamically
- Should support third-party components

Analysers and connectors behave like **services** from WCT's perspective:
- Well-defined interfaces (input/output schemas)
- Configurable via properties
- May depend on infrastructure services (LLM, database pools)
- Can be local or remote

#### 2. AI Agent Integration

Future AI agents will use analysers as **tools** to complete atomic tasks:
- Agent queries: "Which analysers can produce personal data findings?"
- Framework responds: PersonalDataAnalyser, ThirdPartyPDAnalyser, RemotePDAnalyser
- Agent selects best option based on availability, cost, latency
- Agent executes analyser with specific config

**Requirements:**
- Analysers must be discoverable (query by schema/capability)
- Analysers must declare dependencies (LLM service required?)
- Health checking (is remote service available?)

#### 3. Remote/SaaS Analysers

Some analysers will be **wrappers for external services**:
- Analyser receives input data
- Forwards to SaaS API (e.g., compliance-analysis-as-a-service)
- Returns results in WCF schema format
- Main task: Configuration management + data pass-through

**Requirements:**
- Health checking before execution (is service available?)
- Graceful degradation (use fallback if primary unavailable)
- Dynamic registration (service URL configured at runtime)

#### 4. Plugin Architecture (Phase 5 Monorepo Plan)

Future plugin system needs:
- Auto-discovery of third-party components
- Automatic dependency injection for plugins
- Registration without modifying WCT core
- Type-safe component interfaces

**DI enables:**
```python
# Plugin package
from waivern_core import ComponentFactory

class MyCustomAnalyserFactory(ComponentFactory[MyCustomAnalyser]):
    def __init__(self, llm_service: BaseLLMService):
        self._llm = llm_service

# WCT automatically discovers and registers
executor.register_plugin_package("acme-custom-analyser")
# Factory gets LLM service injected automatically
```

## Three-Tier Service Architecture

The DI system manages three distinct tiers of services:

```
┌─────────────────────────────────────────────────────────┐
│ Tier 1: Infrastructure Services (Singleton)             │
│                                                          │
│  - LLMService       (Anthropic/OpenAI/Google)          │
│  - DatabasePool     (MySQL/PostgreSQL connection pools) │
│  - CacheService     (Redis/Memcached)                   │
│  - HTTPClient       (Shared HTTP client for APIs)       │
│                                                          │
│  Created once at WCT startup                            │
│  Managed by ServiceContainer                            │
│  Expensive to create, shared across all components      │
└─────────────────────────────────────────────────────────┘
                          ↓ injected into
┌─────────────────────────────────────────────────────────┐
│ Tier 2: Component Factories (Singleton)                 │
│                                                          │
│  - PersonalDataAnalyserFactory(llm_service)             │
│  - MySQLConnectorFactory(db_pool)                       │
│  - ProcessingPurposeAnalyserFactory(llm_service)        │
│                                                          │
│  Created once per executor initialisation               │
│  Have infrastructure dependencies injected              │
│  Registered in executor factory registries              │
│  Implement ComponentFactory[T] interface                │
└─────────────────────────────────────────────────────────┘
                          ↓ create
┌─────────────────────────────────────────────────────────┐
│ Tier 3: Component Instances (Transient)                 │
│                                                          │
│  - PersonalDataAnalyser(config, llm_service)            │
│  - MySQLConnector(config, db_pool)                      │
│                                                          │
│  Created per execution step (new instance each time)    │
│  Configured with execution-specific config from runbook │
│  Disposed after execution completes                     │
│  Safe for stateful processing                           │
└─────────────────────────────────────────────────────────┘
```

### Key Benefits

**Infrastructure Services:**
- Singleton lifecycle eliminates expensive recreation
- Shared across all components (connection pooling, LLM API clients)
- Managed by DI container (lazy creation, graceful degradation)

**Component Factories:**
- Single source of truth for component metadata (schemas, capabilities)
- Pre-wired with infrastructure dependencies
- Cached and reused (lightweight objects)
- Enable health checking and discovery

**Component Instances:**
- Transient lifecycle matches current behavior
- Execution-specific configuration per step
- No cross-execution state pollution
- Easy to test (new instance per test)

## ComponentFactory Abstraction

### Core Interface

```python
# waivern-core/src/waivern_core/component_factory.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
from waivern_core.schemas import Schema

T = TypeVar('T')

class ComponentFactory(ABC, Generic[T]):
    """Factory for creating framework components (analysers, connectors).

    Factories are registered in the executor and have infrastructure
    services injected via constructor. They create component instances
    with execution-specific configuration from runbooks.

    Type parameter T is the component type this factory creates
    (e.g., PersonalDataAnalyser, MySQLConnector).
    """

    @abstractmethod
    def create(self, config: dict[str, Any]) -> T:
        """Create component instance with given configuration.

        This method is called by the executor for each execution step.
        The config parameter comes from the runbook's analyser/connector
        properties and varies per execution.

        Args:
            config: Execution-specific configuration from runbook

        Returns:
            Configured component instance ready to process data

        Example:
            ```python
            config = {
                "llm_validation": True,
                "evidence_context_size": "medium"
            }
            analyser = factory.create(config)
            ```
        """

    @abstractmethod
    def get_component_name(self) -> str:
        """Get the component type name used in runbooks.

        This name is used in runbook YAML to identify the component:

        ```yaml
        analysers:
          - name: "pd_analyser"
            type: "personal_data"  # <-- This value
        ```

        Returns:
            Component type identifier (e.g., "personal_data", "mysql")
        """

    @abstractmethod
    def get_input_schemas(self) -> list[Schema]:
        """Get schemas this component can accept as input.

        Used for:
        - Runbook validation (does connector output match analyser input?)
        - AI agent discovery (which analysers accept this schema?)
        - Type checking in executor

        Returns:
            List of supported input schemas
        """

    @abstractmethod
    def get_output_schemas(self) -> list[Schema]:
        """Get schemas this component produces as output.

        Used for:
        - Runbook validation
        - AI agent discovery (which analysers produce this schema?)
        - Chaining analysers (output of A → input of B)

        Returns:
            List of supported output schemas
        """

    @abstractmethod
    def can_create(self, config: dict[str, Any]) -> bool:
        """Check if factory can create component with given config.

        This method enables:
        - **Health checking:** For remote services, ping endpoint
        - **Config validation:** Ensure required properties present
        - **Dependency checking:** Verify required services available
        - **Graceful degradation:** Fail fast with clear error

        Called by executor before attempting to create component instance.

        Args:
            config: Configuration that would be passed to create()

        Returns:
            True if factory can create component, False otherwise

        Example (remote service):
            ```python
            def can_create(self, config: dict) -> bool:
                endpoint = config.get("endpoint")
                try:
                    response = self._http.get(f"{endpoint}/health")
                    return response.status_code == 200
                except:
                    return False
            ```

        Example (local service):
            ```python
            def can_create(self, config: dict) -> bool:
                if config.get("llm_validation") and not self._llm_service:
                    return False  # LLM required but unavailable
                return True
            ```
        """

    @classmethod
    def get_service_dependencies(cls) -> dict[str, type]:
        """Declare infrastructure service dependencies (optional).

        This class method documents what services the factory needs.
        Used for:
        - **Documentation:** Generate dependency graphs
        - **Validation:** Warn if services unavailable
        - **Auto-injection:** Plugin loader knows what to inject

        Returns:
            Mapping of parameter name → service type

        Example:
            ```python
            @classmethod
            def get_service_dependencies(cls) -> dict[str, type]:
                return {
                    "llm_service": BaseLLMService,
                    "db_pool": DatabasePool,
                }
            ```

        Default implementation returns empty dict (no dependencies).
        """
        return {}
```

## Implementation Examples

### Example 1: Local Analyser Factory

```python
# waivern-personal-data-analyser/src/.../factory.py

from waivern_core import ComponentFactory, Schema
from waivern_llm.services import BaseLLMService
from .analyser import PersonalDataAnalyser, PersonalDataAnalyserConfig
from .schemas import PersonalDataFindingSchema
from waivern_core.schemas import StandardInputSchema

class PersonalDataAnalyserFactory(ComponentFactory[PersonalDataAnalyser]):
    """Factory for creating PersonalDataAnalyser instances.

    This factory has LLM service injected and creates analysers
    configured for specific execution contexts.
    """

    def __init__(
        self,
        llm_service: BaseLLMService | None = None,
        default_config: dict | None = None
    ):
        """Initialise factory with infrastructure dependencies.

        Args:
            llm_service: Optional LLM service (injected by DI container)
            default_config: Factory-level defaults (timeouts, retries, etc.)
        """
        self._llm_service = llm_service
        self._default_config = default_config or {}

    def create(self, config: dict) -> PersonalDataAnalyser:
        """Create analyser with execution-specific config."""
        # Merge factory defaults with execution config
        merged_config = {**self._default_config, **config}

        # Parse into typed config object
        config_obj = PersonalDataAnalyserConfig.from_dict(merged_config)

        # Create analyser with injected LLM service
        return PersonalDataAnalyser(
            config=config_obj,
            llm_service=self._llm_service
        )

    def get_component_name(self) -> str:
        return "personal_data"

    def get_input_schemas(self) -> list[Schema]:
        return [StandardInputSchema()]

    def get_output_schemas(self) -> list[Schema]:
        return [PersonalDataFindingSchema()]

    def can_create(self, config: dict) -> bool:
        """Validate config and check dependencies."""
        # Check if LLM validation requested but service unavailable
        if config.get("llm_validation", {}).get("enable_llm_validation"):
            if not self._llm_service:
                return False

        # Validate config structure
        try:
            PersonalDataAnalyserConfig.from_dict(config)
            return True
        except Exception:
            return False

    @classmethod
    def get_service_dependencies(cls) -> dict[str, type]:
        return {"llm_service": BaseLLMService}
```

### Example 2: Remote SaaS Analyser Factory

```python
# third-party-package/remote_pd_analyser.py

from waivern_core import ComponentFactory, Schema
from waivern_core.http import HTTPClient  # Hypothetical

class RemotePDAnalyserFactory(ComponentFactory[RemotePDAnalyser]):
    """Factory for remote SaaS personal data analyser.

    This analyser is a wrapper for an external compliance analysis service.
    The factory handles health checking and service availability.
    """

    def __init__(self, http_client: HTTPClient):
        """Initialise with HTTP client for API communication.

        Args:
            http_client: Shared HTTP client (injected by DI)
        """
        self._http = http_client

    def create(self, config: dict) -> RemotePDAnalyser:
        """Create remote analyser wrapper."""
        return RemotePDAnalyser(
            api_key=config["api_key"],
            endpoint=config["endpoint"],
            timeout=config.get("timeout", 30),
            http_client=self._http
        )

    def get_component_name(self) -> str:
        return "remote_personal_data"

    def get_input_schemas(self) -> list[Schema]:
        return [StandardInputSchema()]

    def get_output_schemas(self) -> list[Schema]:
        return [PersonalDataFindingSchema()]

    def can_create(self, config: dict) -> bool:
        """Health check remote service before creating wrapper."""
        endpoint = config.get("endpoint")
        if not endpoint:
            return False

        try:
            # Ping health endpoint
            response = self._http.get(
                f"{endpoint}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False  # Service unavailable

    @classmethod
    def get_service_dependencies(cls) -> dict[str, type]:
        return {"http_client": HTTPClient}
```

### Example 3: MySQL Connector Factory

```python
# waivern-mysql/src/waivern_mysql/factory.py

from waivern_core import ComponentFactory, Schema
from waivern_core.database import DatabasePool  # Hypothetical
from .connector import MySQLConnector, MySQLConfig
from .schemas import MySQLDataSchema

class MySQLConnectorFactory(ComponentFactory[MySQLConnector]):
    """Factory for creating MySQLConnector instances."""

    def __init__(self, db_pool: DatabasePool | None = None):
        """Initialise with optional database connection pool.

        Args:
            db_pool: Shared database connection pool (injected by DI)
                    If None, connector creates its own connections
        """
        self._db_pool = db_pool

    def create(self, config: dict) -> MySQLConnector:
        """Create MySQL connector with execution-specific config."""
        config_obj = MySQLConfig.from_dict(config)

        return MySQLConnector(
            config=config_obj,
            db_pool=self._db_pool
        )

    def get_component_name(self) -> str:
        return "mysql"

    def get_input_schemas(self) -> list[Schema]:
        return []  # Connectors typically don't have input schemas

    def get_output_schemas(self) -> list[Schema]:
        return [MySQLDataSchema(), StandardInputSchema()]

    def can_create(self, config: dict) -> bool:
        """Validate MySQL config and test connection."""
        try:
            config_obj = MySQLConfig.from_dict(config)
            # Could test connection here
            return True
        except Exception:
            return False

    @classmethod
    def get_service_dependencies(cls) -> dict[str, type]:
        return {"db_pool": DatabasePool}
```

## WCT Executor Integration

### Updated Executor Class

```python
# apps/wct/src/wct/executor.py

from waivern_core import Analyser, Connector, ComponentFactory
from waivern_core.services import ServiceContainer
from waivern_llm.services import BaseLLMService
from waivern_llm.di import LLMServiceFactory

from waivern_community.analysers import BUILTIN_ANALYSER_FACTORIES
from waivern_community.connectors import BUILTIN_CONNECTOR_FACTORIES

class Executor:
    """WCT executor with DI-managed component factories."""

    def __init__(self, container: ServiceContainer):
        """Initialise executor with DI container.

        Args:
            container: Service container managing infrastructure services
        """
        self._container = container
        self.analyser_factories: dict[str, ComponentFactory[Analyser]] = {}
        self.connector_factories: dict[str, ComponentFactory[Connector]] = {}

    @classmethod
    def create_with_built_ins(cls) -> "Executor":
        """Create executor with built-in components and infrastructure.

        This method:
        1. Creates DI container
        2. Registers infrastructure services (LLM, DB pools, etc.)
        3. Creates executor with container
        4. Registers component factories with injected dependencies

        Returns:
            Configured executor ready to execute runbooks
        """
        # Create DI container
        container = ServiceContainer()

        # Register infrastructure services (singleton)
        container.register(
            BaseLLMService,
            LLMServiceFactory(),
            lifetime="singleton"
        )

        # Could register database pools, cache services, etc.
        # container.register(DatabasePool, DatabasePoolFactory(), ...)

        # Create executor
        executor = cls(container)

        # Get infrastructure services from container
        llm_service = container.get_service(BaseLLMService)
        # db_pool = container.get_service(DatabasePool)

        # Register analyser factories with dependencies injected
        for factory_class in BUILTIN_ANALYSER_FACTORIES:
            factory = factory_class(llm_service=llm_service)
            executor.register_analyser_factory(factory)
            logger.debug("Registered analyser factory: %s", factory.get_component_name())

        # Register connector factories
        for factory_class in BUILTIN_CONNECTOR_FACTORIES:
            factory = factory_class()  # Connectors may have different deps
            executor.register_connector_factory(factory)
            logger.debug("Registered connector factory: %s", factory.get_component_name())

        logger.info(
            "Executor initialised with %d analyser factories and %d connector factories",
            len(executor.analyser_factories),
            len(executor.connector_factories)
        )

        return executor

    def register_analyser_factory(self, factory: ComponentFactory[Analyser]) -> None:
        """Register an analyser factory.

        Args:
            factory: Factory instance (already has dependencies injected)
        """
        self.analyser_factories[factory.get_component_name()] = factory

    def register_connector_factory(self, factory: ComponentFactory[Connector]) -> None:
        """Register a connector factory.

        Args:
            factory: Factory instance (already has dependencies injected)
        """
        self.connector_factories[factory.get_component_name()] = factory

    def list_available_analysers(self) -> dict[str, ComponentFactory[Analyser]]:
        """Get all registered analyser factories."""
        return self.analyser_factories.copy()

    def list_available_connectors(self) -> dict[str, ComponentFactory[Connector]]:
        """Get all registered connector factories."""
        return self.connector_factories.copy()

    def _instantiate_components(
        self,
        analyser_type: str,
        connector_type: str,
        analyser_config: AnalyserConfig,
        connector_config: ConnectorConfig,
    ) -> tuple[Analyser, Connector]:
        """Instantiate analyser and connector via factories.

        This replaces the old approach of calling `from_properties()` directly.
        Now we:
        1. Get factory from registry
        2. Check health/availability with can_create()
        3. Create instance with factory.create()

        Args:
            analyser_type: Analyser type name from runbook
            connector_type: Connector type name from runbook
            analyser_config: Analyser configuration from runbook
            connector_config: Connector configuration from runbook

        Returns:
            Tuple of (analyser instance, connector instance)

        Raises:
            ExecutorError: If factory not found or cannot create component
        """
        # Get factories from registries
        analyser_factory = self.analyser_factories.get(analyser_type)
        if not analyser_factory:
            raise ExecutorError(f"Unknown analyser type: {analyser_type}")

        connector_factory = self.connector_factories.get(connector_type)
        if not connector_factory:
            raise ExecutorError(f"Unknown connector type: {connector_type}")

        # Check availability (health check for remote services)
        if not analyser_factory.can_create(analyser_config.properties):
            raise ExecutorError(
                f"Analyser '{analyser_type}' cannot be created with given config. "
                "Possible reasons: missing dependencies, invalid config, remote service unavailable"
            )

        if not connector_factory.can_create(connector_config.properties):
            raise ExecutorError(
                f"Connector '{connector_type}' cannot be created with given config"
            )

        # Create instances (transient lifecycle)
        analyser = analyser_factory.create(analyser_config.properties)
        connector = connector_factory.create(connector_config.properties)

        return analyser, connector
```

### Updated Component Constructor Pattern

**Old pattern (removed):**
```python
class PersonalDataAnalyser:
    @classmethod
    def from_properties(cls, properties: dict) -> Self:
        """Old instantiation method - REMOVED."""
        config = PersonalDataAnalyserConfig.from_dict(properties)
        # Had to create LLM service internally
        llm_service = LLMServiceManager().llm_service
        return cls(config, llm_service)
```

**New pattern (DI-enabled):**
```python
class PersonalDataAnalyser:
    """Analyser with explicit service dependencies."""

    def __init__(
        self,
        config: PersonalDataAnalyserConfig,
        llm_service: BaseLLMService | None = None
    ):
        """Initialise analyser with config and injected services.

        Args:
            config: Typed configuration object
            llm_service: LLM service (injected by factory)
        """
        self._config = config
        self._llm_service = llm_service

    # process() method unchanged
    def process(self, input_schema, output_schema, message):
        # Use self._llm_service if needed
        ...
```

## AI Agent Discovery

With the factory pattern, AI agents can discover and query analysers:

```python
# Agent: Find all analysers that can produce personal data findings

def find_analysers_by_output_schema(
    executor: Executor,
    schema_name: str
) -> list[ComponentFactory[Analyser]]:
    """Find analysers that produce given output schema."""
    matching = []
    for factory in executor.list_available_analysers().values():
        if any(s.name == schema_name for s in factory.get_output_schemas()):
            matching.append(factory)
    return matching

# Usage
pd_analysers = find_analysers_by_output_schema(executor, "personal_data_finding")
# Returns: [PersonalDataAnalyserFactory, ThirdPartyPDAnalyserFactory, ...]

# Agent selects best based on availability
available = [f for f in pd_analysers if f.can_create(config)]
selected = available[0]  # Or use cost/latency heuristics

# Agent executes
analyser = selected.create(config)
result = analyser.process(input_schema, output_schema, message)
```

## Plugin Architecture (Phase 5 Monorepo)

Third-party plugins register factories:

```python
# third-party-package/__init__.py

from waivern_core import ComponentFactory, Analyser

class AcmeComplianceAnalyserFactory(ComponentFactory[AcmeComplianceAnalyser]):
    """Third-party factory following same pattern."""

    def __init__(self, llm_service, http_client):
        self._llm = llm_service
        self._http = http_client

    # Implement all abstract methods...

# Plugin registration (auto-discovery in Phase 5)
def register_plugin(executor: Executor, container: ServiceContainer):
    """Called by WCT plugin loader."""
    llm = container.get_service(BaseLLMService)
    http = container.get_service(HTTPClient)

    factory = AcmeComplianceAnalyserFactory(
        llm_service=llm,
        http_client=http
    )

    executor.register_analyser_factory(factory)
```

**Auto-injection pattern (future):**
```python
# Executor inspects constructor signature, injects automatically
def register_analyser_factory_class(
    executor: Executor,
    factory_class: type[ComponentFactory[Analyser]]
):
    """Register factory class - executor handles dependency injection."""
    # Inspect constructor to find required services
    deps = factory_class.get_service_dependencies()

    # Resolve dependencies from container
    kwargs = {}
    for param_name, service_type in deps.items():
        kwargs[param_name] = executor._container.get_service(service_type)

    # Create factory with auto-injected dependencies
    factory = factory_class(**kwargs)
    executor.register_analyser_factory(factory)
```

## Implementation Phases

### Phase 0: Update Documentation

**Goal:** Document decision and design before implementation

**Tasks:**
- Update ADR-0002 with component factory section
- Create this reference document
- Update implementation plan with new phases

**Deliverable:** Complete documentation approved

### Phase 1: Core DI Infrastructure

**Goal:** Generic DI container in waivern-core

**Tasks:**
- Create `services/protocols.py` with ServiceFactory, ServiceProvider
- Create `services/container.py` with ServiceContainer
- Create `services/lifecycle.py` with ServiceDescriptor
- Write comprehensive unit tests (20+ tests)

**Deliverable:** Generic DI container working for any service type

### Phase 2: Component Factory Abstraction

**Goal:** Add ComponentFactory to waivern-core

**Tasks:**
- Create `component_factory.py` with ComponentFactory ABC
- Implement all abstract methods with comprehensive docstrings
- Add to waivern-core public API exports
- Write unit tests for ABC structure

**Files:**
- `waivern-core/src/waivern_core/component_factory.py`
- `waivern-core/tests/test_component_factory.py`

**Deliverable:** ComponentFactory available framework-wide

### Phase 3: LLM Service Integration

**Goal:** LLM as DI-managed service in waivern-llm/di/

**Tasks:**
- Create `di/factory.py` with LLMServiceFactory(ServiceFactory[BaseLLMService])
- Create `di/provider.py` with LLMServiceProvider
- Create `di/configuration.py` with config types
- Write integration tests

**Deliverable:** LLM services managed via DI

### Phase 4: Analyser Factory Implementation

**Goal:** All analysers have DI-enabled factories

**4.1 PersonalDataAnalyser:**
- Create PersonalDataAnalyserFactory in package
- Update PersonalDataAnalyser.__init__() with explicit service injection
- Remove `from_properties()` classmethod
- Update all tests to use factory pattern

**4.2 ProcessingPurposeAnalyser:**
- Same steps as PersonalDataAnalyser

**4.3 DataSubjectAnalyser:**
- Same steps as PersonalDataAnalyser

**4.4 Export factories:**
```python
# waivern-community/analysers/__init__.py
BUILTIN_ANALYSER_FACTORIES = [
    PersonalDataAnalyserFactory,
    ProcessingPurposeAnalyserFactory,
    DataSubjectAnalyserFactory,
]
```

**Deliverable:** All 3 analysers DI-enabled with factories

### Phase 5: Connector Factory Implementation

**Goal:** All connectors have DI-enabled factories

**Tasks:**
- Create FilesystemConnectorFactory
- Create SourceCodeConnectorFactory
- Create MySQLConnectorFactory (in waivern-mysql package)
- Create SQLiteConnectorFactory
- Update connector constructors
- Export BUILTIN_CONNECTOR_FACTORIES

**Deliverable:** All connectors DI-enabled with factories

### Phase 6: Executor Integration

**Goal:** Executor uses DI container and factories

**Critical tasks:**
- Update Executor.__init__() to accept ServiceContainer
- Update create_with_built_ins() to setup DI + register factories
- Update _instantiate_components() to use factories
- Add health checking via can_create()
- Remove all direct from_properties() calls
- Update all executor tests

**Deliverable:** Executor fully DI-integrated

### Phase 7: Testing & Documentation

**Goal:** Comprehensive tests and updated docs

**Tasks:**
- Unit tests for all factories (60+ new tests)
- Integration tests for full flow
- Update CLAUDE.md with factory pattern
- Update package READMEs
- Create architecture diagrams

**Deliverable:** Complete test coverage and documentation

### Phase 8: Cleanup & Finalization

**Goal:** Remove deprecated code, final verification

**Tasks:**
- Remove from_properties() from Analyser/Connector base classes
- Remove old BUILTIN_ANALYSERS/BUILTIN_CONNECTORS lists
- Run all quality checks
- Verify all sample runbooks work
- Document breaking changes

**Deliverable:** Production-ready DI system

## Success Criteria

✅ **Infrastructure services managed by DI container** (LLM, DB pools)
✅ **Component factories registered in executor** (analysers + connectors)
✅ **Factories have dependencies injected** (constructor injection)
✅ **Executor creates instances via factories** (transient lifecycle)
✅ **Health checking works** (can_create() validates availability)
✅ **AI agents can discover components** (query by schema/capability)
✅ **Plugin architecture ready** (third-party factories register seamlessly)
✅ **All tests passing** (752+ existing + 60+ new factory tests)
✅ **Sample runbooks working** (LAMP stack, file analysis, etc.)
✅ **Type checking passes** (strict mode, full type safety)
✅ **Documentation complete** (ADR, guides, API docs)

## Breaking Changes

### Removed

1. **`Analyser.from_properties()` classmethod**
   - Old: `analyser = AnalyserClass.from_properties(config)`
   - New: `analyser = factory.create(config)`

2. **`Connector.from_properties()` classmethod**
   - Old: `connector = ConnectorClass.from_properties(config)`
   - New: `connector = factory.create(config)`

3. **`BUILTIN_ANALYSERS` list** (replaced with `BUILTIN_ANALYSER_FACTORIES`)

4. **`BUILTIN_CONNECTORS` list** (replaced with `BUILTIN_CONNECTOR_FACTORIES`)

5. **Direct component instantiation in executor**

### Migration Path

**Before (old code):**
```python
from waivern_community.analysers import BUILTIN_ANALYSERS

for analyser_class in BUILTIN_ANALYSERS:
    executor.register_available_analyser(analyser_class)

# Later
analyser = analyser_class.from_properties(config)
```

**After (new code):**
```python
from waivern_community.analysers import BUILTIN_ANALYSER_FACTORIES

llm_service = container.get_service(BaseLLMService)
for factory_class in BUILTIN_ANALYSER_FACTORIES:
    factory = factory_class(llm_service=llm_service)
    executor.register_analyser_factory(factory)

# Later
analyser = factory.create(config)
```

## Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Registration** | Hybrid (factories are singleton, create transient instances) | Matches current transient behavior, factories cached |
| **Lifecycle** | Transient instances per execution step | Safe for stateful analysers, matches current behavior |
| **Pattern scope** | Unified (analysers AND connectors) | Consistency, both have same needs (deps, plugins, remote) |
| **Dependency injection** | Constructor injection with explicit types | Type-safe, clear, testable, IDE-friendly |
| **Container access** | Limited (specific services injected, not full container) | Clear interfaces, explicit dependencies |
| **Backwards compatibility** | None (clean break, pre-1.0) | Simpler migration, no technical debt |
| **Factory abstraction** | ABC (Abstract Base Class) | Provides base implementations, clear inheritance |
| **Dependency declaration** | Optional class method get_service_dependencies() | Documentation, validation, auto-injection for plugins |

## References

- [ADR-0002: Dependency Injection for Service Management](../adr/0002-dependency-injection-for-service-management.md)
- [DI Implementation Plan](./dependency-injection-implementation-plan.md)
- [Monorepo Migration Plan - Phase 5](./monorepo-migration-plan.md#phase-5-dynamic-plugin-loading)
