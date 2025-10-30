# Dependency Injection in WCF

The Waivern Compliance Framework uses dependency injection to manage component lifecycles and service dependencies.

## ComponentFactory Pattern

Each connector and analyser has a corresponding factory responsible for component instantiation.

**Structure:**
- Factories implement the `ComponentFactory[T]` interface
- Factories receive configuration dictionaries from runbooks
- Factories convert configuration to typed Pydantic models
- Factories instantiate components with validated configuration

**Example:**
```python
class MySQLConnectorFactory(ComponentFactory[MySQLConnector]):
    def create(self, properties: dict) -> MySQLConnector:
        config = MySQLConnectorConfig.from_properties(properties)
        return MySQLConnector(config)
```

## ServiceContainer

The `ServiceContainer` manages singleton services like LLM providers.

**Lifecycle:**
- Services registered once at application startup
- Shared across all components requiring them
- Factories retrieve services from the container when creating components

**Example:**
```python
container = ServiceContainer()
llm_service = LLMServiceFactory().create(llm_config)
container.register_service(BaseLLMService, llm_service)
```

## Configuration Flow

1. User writes runbook with component properties (YAML dictionaries)
2. Executor reads runbook configuration
3. Executor converts properties to `BaseComponentConfiguration` objects
4. Executor calls factory with configuration
5. Factory validates configuration via Pydantic models
6. Factory instantiates component with dependencies

## Component Instantiation

**Old approach (removed):**
```python
connector = MySQLConnector.from_properties(properties)
```

**Current approach:**
```python
factory = MySQLConnectorFactory()
connector = factory.create(properties)
```

Analysers requiring LLM services receive them via constructor injection:

```python
class PersonalDataAnalyser:
    def __init__(self, config: PersonalDataAnalyserConfig, llm_service: BaseLLMService):
        self.config = config
        self.llm_service = llm_service
```

## Architecture Layers

```
Runbook (YAML) → Executor → Factory → Component
                      ↓
                ServiceContainer
```

The executor holds factories, not component classes. When execution begins, the executor uses factories to create component instances with their required dependencies.
