# Dependency Injection in WCF

The Waivern Compliance Framework uses dependency injection to manage service lifecycles and inject dependencies into components.

## ServiceContainer

The `ServiceContainer` manages singleton services like LLM providers that are shared across multiple components.

**Key concepts:**

- Services are registered once at application startup
- Service factories handle lazy creation (only created when first requested)
- Services are cached as singletons (reused across all components)
- Components receive services through their factories

**Example - Registering a service:**

```python
from waivern_core.services import ServiceContainer, ServiceDescriptor
from waivern_artifact_store import ArtifactStore, ArtifactStoreFactory
from waivern_llm import LLMService, LLMServiceFactory

# Create container
container = ServiceContainer()

# Register services (order doesn't matter - resolution is lazy)
container.register(
    ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(), "singleton")
)
container.register(
    ServiceDescriptor(LLMService, LLMServiceFactory(container), "singleton")
)

# Note: LLMServiceFactory requires the container for lazy dependency resolution
# (it needs ArtifactStore for caching). The factory resolves dependencies
# at create() time, not construction time, enabling registration order independence.
```

## ComponentFactory Pattern

Each connector and analyser has a corresponding factory that creates component instances with their required dependencies.

**How it works:**

1. Factories receive the `ServiceContainer` when constructed
2. Factories resolve services from the container when creating components
3. Factories validate configuration from runbooks
4. Factories instantiate components with configuration and services

**Example - Factory with dependency injection:**

```python
class PersonalDataAnalyserFactory(ComponentFactory[PersonalDataAnalyser]):
    def __init__(self, container: ServiceContainer):
        """Factory receives container to resolve services."""
        self._container = container

    def create(self, config: ComponentConfig) -> PersonalDataAnalyser:
        """Create analyser with injected LLM service."""
        # Parse configuration
        analyser_config = PersonalDataAnalyserConfig.from_properties(config)

        # Resolve LLM service from container
        llm_service = self._container.get_service(LLMService)

        # Create component with dependencies
        return PersonalDataAnalyser(
            config=analyser_config,
            llm_service=llm_service
        )
```

## Complete Flow: From Runbook to Component

Here's how dependency injection works end-to-end in WCF:

**1. Application Startup (WCT)**

```python
from waivern_core.services import ServiceContainer, ServiceDescriptor
from waivern_artifact_store import ArtifactStore, ArtifactStoreFactory
from waivern_llm import LLMService, LLMServiceFactory

# Create service container
container = ServiceContainer()

# Register services (LLMService depends on ArtifactStore for caching)
container.register(
    ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(), "singleton")
)
container.register(
    ServiceDescriptor(LLMService, LLMServiceFactory(container), "singleton")
)

# Create factories with container
personal_data_factory = PersonalDataAnalyserFactory(container)
mysql_factory = MySQLConnectorFactory(container)
```

**2. User writes runbook (YAML)**

```yaml
analysers:
  - name: "personal_data_detector"
    type: "personal_data_analyser"
    properties:
      pattern_matching:
        ruleset: "local/personal_data/1.0.0"
      llm_validation:
        enable_llm_validation: true
```

**3. Executor creates component**

```python
# Executor gets factory by type
factory = executor.get_analyser_factory("personal_data_analyser")

# Factory creates component with runbook config
analyser = factory.create(runbook_properties)

# Component now has config + LLM service injected!
```

**4. Component receives dependencies**

```python
class PersonalDataAnalyser:
    def __init__(
        self,
        config: PersonalDataAnalyserConfig,
        llm_service: LLMService | None = None
    ):
        """Component receives validated config + services."""
        self._config = config
        self._llm_service = llm_service  # Injected by factory!
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│ Application Startup                             │
│  - ServiceContainer created                     │
│  - Services registered (LLM, etc.)              │
│  - Factories created with container             │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Runbook Execution                               │
│  - User writes YAML config                      │
│  - Executor reads runbook                       │
│  - Factory creates component                    │
│  - Factory injects services from container      │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Component Instance                              │
│  - Has validated configuration                  │
│  - Has injected services (LLM, etc.)            │
│  - Ready to process data                        │
└─────────────────────────────────────────────────┘
```

## Key Principles

**Services vs Components:**

- **Services** (LLM, database pools) - Long-lived, shared, managed by ServiceContainer
- **Components** (analysers, connectors) - Short-lived, created per execution, receive services

**Why factories?**

- Factories separate component creation from usage
- Factories handle dependency resolution (get services from container)
- Components stay focused on their business logic
- Easy to test (inject mock services through factory)

**Configuration validation:**

- Runbook properties (dict) → Pydantic model → Validated config
- Factories perform validation before creating components
- Type-safe configuration throughout the framework
