# Dependency Injection Factory Patterns

**Updated:** 2025-10-30
**Related:** [ADR-0002](../adr/0002-dependency-injection-for-service-management.md)

## Overview

WCF uses dependency injection with two factory patterns: one for infrastructure services, one for WCF [components](../core-concepts/wcf-core-components.md).

## ServiceFactory[T] - Infrastructure Services

Lightweight protocol for creating singleton services (LLM providers, database pools, HTTP clients).

```python
class ServiceFactory[T](Protocol):
    def create(self) -> T | None: ...
    def can_create(self) -> bool: ...
```

**Characteristics:**
- Configuration in factory constructor (not `create()`)
- No parameters in `create()` or `can_create()`
- Singleton lifecycle via ServiceContainer
- Not visible in runbooks

**Example:**
```python
# Zero-config (reads environment)
container.register(BaseLLMService, LLMServiceFactory(), lifetime="singleton")

# With explicit config
config = LLMServiceConfiguration(provider="anthropic", api_key="...")
container.register(BaseLLMService, LLMServiceFactory(config), lifetime="singleton")
```

## ComponentFactory[T] - WCF Components

Abstract base class for creating analysers and connectors with rich metadata.

```python
class ComponentFactory[T](ABC):
    def create(self, config: dict) -> T: ...
    def can_create(self, config: dict) -> bool: ...
    def get_component_name(self) -> str: ...
    def get_input_schemas(self) -> list[Schema]: ...
    def get_output_schemas(self) -> list[Schema]: ...
```

**Characteristics:**
- Configuration passed to `create()` method (per-execution)
- Schema declarations for component discovery
- Component name maps to runbook `type:` field
- Transient component instances

**Example:**
```python
class PersonalDataAnalyserFactory(ComponentFactory[PersonalDataAnalyser]):
    def __init__(self, llm_service: BaseLLMService | None = None):
        self._llm_service = llm_service

    def create(self, config: dict) -> PersonalDataAnalyser:
        config_obj = PersonalDataAnalyserConfig.from_properties(config)
        return PersonalDataAnalyser(config_obj, self._llm_service)

    def get_component_name(self) -> str:
        return "personal_data"
```

## Why Two Patterns?

| Aspect | ServiceFactory | ComponentFactory |
|--------|----------------|------------------|
| **Purpose** | Infrastructure | WCF components |
| **Type** | Protocol | ABC |
| **Config timing** | Factory creation | Component creation |
| **Lifecycle** | Singleton | Transient |
| **Runbook visible** | No | Yes |
| **Schemas** | None | Input/output |

## Three-Tier Architecture

```
Infrastructure Services (Singleton)
  ↓ injected into
Component Factories (Singleton)
  ↓ create
Component Instances (Transient)
```

**Tier 1: Infrastructure Services**
- Created once at startup
- Managed by ServiceContainer
- Examples: LLMService, DatabasePool

**Tier 2: Component Factories**
- Created once per executor
- Hold infrastructure dependencies
- Registered in executor registries

**Tier 3: Component Instances**
- Created per execution step
- Configured from runbook properties
- Disposed after execution

## Executor Integration

```python
class Executor:
    def __init__(self, container: ServiceContainer):
        self._container = container
        self.analyser_factories: dict[str, ComponentFactory[Analyser]] = {}
        self.connector_factories: dict[str, ComponentFactory[Connector]] = {}

    @classmethod
    def create_with_built_ins(cls) -> "Executor":
        # Create container and register services
        container = ServiceContainer()
        container.register(BaseLLMService, LLMServiceFactory(), lifetime="singleton")

        executor = cls(container)
        llm_service = container.get_service(BaseLLMService)

        # Register component factories with dependencies
        for factory_class in BUILTIN_ANALYSER_FACTORIES:
            factory = factory_class(llm_service=llm_service)
            executor.register_analyser_factory(factory)

        return executor
```

## Configuration Flow

1. User writes runbook with component properties (YAML dict)
2. Executor reads runbook configuration
3. Executor calls `factory.create(properties_dict)`
4. Factory converts dict to typed Config class
5. Factory creates component with validated config

## Component Pattern

Components receive dependencies via constructor:

```python
class PersonalDataAnalyser:
    def __init__(
        self,
        config: PersonalDataAnalyserConfig,
        llm_service: BaseLLMService | None = None
    ):
        self._config = config
        self._llm_service = llm_service
```

Factories handle instantiation:

```python
# In factory.create()
config_obj = PersonalDataAnalyserConfig.from_properties(properties)
return PersonalDataAnalyser(config_obj, self._llm_service)
```

## References

- [ADR-0002: Dependency Injection for Service Management](../adr/0002-dependency-injection-for-service-management.md)
- [Dependency Injection Core Concepts](../core-concepts/dependency-injection.md)
