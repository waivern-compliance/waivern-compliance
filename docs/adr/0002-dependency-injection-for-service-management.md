# ADR-0002: Dependency Injection Container for Service Management

## Status

Proposed

## Context

### Current State

The Waivern Compliance Framework currently uses `LLMServiceManager` in `waivern-analysers-shared/utilities/` to manage LLM service lifecycle. This utility class provides lazy initialisation and basic caching for LLM services used across all analysers.

**Note:** While currently in `waivern-analysers-shared`, service management is core infrastructure that should be available to all components (connectors, analysers, etc.), not just analysers.

**Current implementation:**
```python
class LLMServiceManager:
    """Utility for managing LLM service lifecycle and configuration."""

    def __init__(self, enable_llm_validation: bool = True):
        self._enable_llm_validation = enable_llm_validation
        self._llm_service: BaseLLMService | None = None

    @property
    def llm_service(self) -> BaseLLMService | None:
        if self._llm_service is None and self._enable_llm_validation:
            try:
                self._llm_service = LLMServiceFactory.create_service()
                logger.info("LLM service initialised")
            except LLMServiceError as e:
                logger.warning(f"Failed to initialise: {e}")
                self._enable_llm_validation = False  # Side effect!
        return self._llm_service
```

### Problems with Current Approach

1. **Limited Scope**: Only manages LLM services
   - Cannot be used for databases, caches, HTTP clients, or other services
   - Each new service type would need its own manager class
   - No standardised pattern across the framework

2. **Hidden Complexity**: Service creation buried in property getter
   - Property access has side effects (mutates `_enable_llm_validation`)
   - Violates Command-Query Separation principle
   - Makes debugging harder

3. **Hard to Test**: Difficult to inject mock services
   - Cannot easily substitute test implementations
   - Mocking requires patching `LLMServiceFactory.create_service()`
   - No explicit dependency declaration

4. **No Extensibility**: Pattern doesn't scale
   - Adding health checking would complicate property getter further
   - No support for different service lifetimes (singleton vs transient)
   - Retry logic would make property getter even more complex

5. **Implicit Dependencies**: Analysers don't declare requirements
   - Looking at analyser constructor doesn't show it needs LLM service
   - Dependencies discovered at runtime through property access
   - Unclear service lifecycle

### Framework Growth Requirements

As the framework matures, we need to manage more services:

- **LLM Services**: Already in use (Anthropic, OpenAI, Google)
- **Database Services**: Connection pools for MySQL, PostgreSQL, SQLite
- **Cache Services**: Redis, Memcached for performance optimisation
- **HTTP Clients**: For API integrations and vendor services
- **Metrics/Telemetry**: Prometheus, DataDog for observability
- **Message Queues**: For asynchronous processing

Each service needs:
- ✅ Lazy initialisation (don't create until needed)
- ✅ Singleton caching (reuse expensive instances)
- ✅ Graceful degradation (continue without service if unavailable)
- ✅ Health checking (detect failures, enable recovery)
- ✅ Testability (easy mocking for unit tests)
- ✅ Type safety (full type checker support)

### Requirements

A proper service management solution must:

- ✅ Support multiple service types with a unified pattern
- ✅ Enable easy testing through dependency injection
- ✅ Provide explicit dependency declaration
- ✅ Handle service lifecycle (creation, caching, disposal)
- ✅ Support graceful degradation when services unavailable
- ✅ Maintain separation of concerns (waivern-llm stays clean)
- ✅ Enable future health checking and retry logic
- ✅ Scale to dozens of service types without code duplication

---

## Alternative Approaches Considered

### 1. Keep Current LLMServiceManager (Status Quo)

**How it works:** Continue using the existing manager class, create similar classes for other services.

**Pros:**
- Already implemented and working
- Simple API familiar to existing code
- No breaking changes required
- Zero learning curve

**Cons:**
- Only works for LLM services
- Would need `DatabaseServiceManager`, `CacheServiceManager`, etc.
- Code duplication across manager classes
- No standardised pattern
- Hidden state mutations (property side effects)
- Difficult to test with mocks

**Verdict:** ❌ Doesn't scale for future needs

---

### 2. Service Locator Pattern

**How it works:** Global registry for services, accessed by string keys or types.

```python
# Registration
ServiceRegistry.register("llm", llm_service)
ServiceRegistry.register("cache", cache_service)

# Access
service = ServiceRegistry.get("llm")
```

**Pros:**
- Simple to implement
- Works for multiple service types
- Common pattern (Python's `logging.getLogger()` uses this)
- Minimal code changes required
- Familiar to Python developers

**Cons:**
- **Hidden dependencies**: Can't see what analyser needs from constructor
- **Global state**: Testing nightmare (services shared across tests)
- **No type safety**: String-based lookup loses type information
- **Considered anti-pattern**: DI community discourages this approach
- **Runtime failures**: Wrong key = runtime error, not compile-time

**Industry perspective:** Martin Fowler calls Service Locator "an anti-pattern" compared to Dependency Injection. Makes testing harder, not easier.

**Verdict:** ❌ Better than status quo, but has serious drawbacks

---

### 3. Dependency Injection Container (Chosen)

**How it works:** Explicit registration and type-safe retrieval through container.

```python
# Create container
container = ServiceContainer()

# Register services
container.register(BaseLLMService, LLMServiceFactory(...))
container.register(CacheService, RedisCacheFactory(...))

# Create provider
provider = LLMServiceProvider(container)

# Use in analyser
service = provider.get_llm_service()
```

**Pros:**
- **Explicit dependencies**: Constructor shows what analyser needs
- **Type safe**: Generic types provide compile-time safety
- **Testable**: Easy to inject mock services
- **Industry standard**: .NET Core DI, Spring Framework, fastapi.Depends
- **Scales infinitely**: Same pattern for any service type
- **Supports lifecycle**: Singleton, transient, scoped (future)
- **No global state**: Each container is independent

**Cons:**
- More code (3 new abstractions: Factory, Container, Provider)
- Slight learning curve for contributors
- Migration effort required (2-3 weeks)
- More files to maintain

**Industry examples:**
- **.NET Core**: `IServiceCollection`, `ServiceProvider`
- **Spring Framework**: `ApplicationContext`, `@Autowired`
- **Python fastapi**: `Depends(get_service)`
- **Python dependency-injector**: Full DI framework

**Verdict:** ✅ Best long-term solution

---

### 4. Constructor Injection Only (No Container)

**How it works:** Pass services directly to constructors, no centralized management.

```python
# Create all services manually
llm_service = create_llm_service()
cache_service = create_cache_service()
db_service = create_db_service()
# ... 10+ more services

# Pass to analyser
analyser = PersonalDataAnalyser(
    config=config,
    llm_service=llm_service,
    cache_service=cache_service,
    db_service=db_service,
    metrics_service=metrics_service,
    # ... 10+ more parameters
)
```

**Pros:**
- Simplest possible approach
- Very explicit
- No magic or hidden behaviour
- Easy to understand

**Cons:**
- **Constructor explosion**: 10+ parameters become unmanageable
- **No lifecycle management**: Manually create/dispose all services
- **Repetitive boilerplate**: Every analyser duplicates service creation
- **Testing pain**: Mock 10+ services for each test
- **No centralisation**: Can't change service configuration in one place

**Verdict:** ❌ Too simplistic for complex service graphs

---

### 5. Metaclass-Based Auto-Registration

**How it works:** Services automatically register via metaclass magic.

```python
class ServiceBase(metaclass=ServiceMeta):
    __service_registry__ = {}

class LLMService(ServiceBase):
    service_name = "llm"
    # Automatically registered!
```

**Pros:**
- Zero-configuration per service
- Automatic discovery
- Clean class-based approach

**Cons:**
- Heavy metaclass magic (hard to debug)
- Import order dependencies
- Type checkers struggle with metaclasses
- Unclear service lifecycle
- Over-engineering for our needs

**Industry perspective:** SQLAlchemy uses this for ORM models, but it's complex and can cause subtle bugs.

**Verdict:** ❌ Over-engineered, introduces unnecessary complexity

---

## Decision

We will implement a **Dependency Injection Container** in `waivern-core/services/` that provides:

### 1. Generic Service Management Abstractions

**ServiceFactory Protocol:**
```python
class ServiceFactory(Protocol[T]):
    """Protocol for service factories."""
    def create(self) -> T: ...
    def can_create(self) -> bool: ...
```

**ServiceContainer:**
```python
class ServiceContainer:
    """DI container for managing service lifecycle."""

    def register[T](
        self,
        service_type: type[T],
        factory: ServiceFactory[T],
        lifetime: Literal["singleton", "transient"] = "singleton"
    ) -> None: ...

    def get_service[T](self, service_type: type[T]) -> T | None: ...

    def is_healthy[T](self, service_type: type[T]) -> bool: ...
```

**ServiceProvider Protocol:**
```python
class ServiceProvider(Protocol):
    """Protocol for service providers."""
    def get_service[T](self, service_type: type[T]) -> T | None: ...
    def is_available[T](self, service_type: type[T]) -> bool: ...
```

### 2. LLM Service Integration (Adapter Pattern)

**LLMServiceFactory (wraps waivern-llm):**
```python
class LLMServiceFactory(ServiceFactory[BaseLLMService]):
    """Factory that wraps waivern-llm's factory for DI compatibility."""

    def create(self) -> BaseLLMService:
        # Delegates to waivern-llm
        return WaivernLLMFactory.create_service(...)

    def can_create(self) -> bool:
        # Pre-creation validation
        ...
```

**LLMServiceProvider (high-level API):**
```python
class LLMServiceProvider(ServiceProvider):
    """High-level provider for LLM services."""

    def __init__(self, container: ServiceContainer): ...

    def get_llm_service(self) -> BaseLLMService | None: ...

    @property
    def is_available(self) -> bool: ...
```

### 3. Service Lifetimes

- **Singleton**: Create once, reuse instance (default for expensive services)
- **Transient**: Create new instance per request (future: for stateful services)

### 4. Architecture

```
waivern-core (Core Framework)        # NEW: Generic DI infrastructure
└── services/                        # Service management abstractions
    ├── protocols.py                 # ServiceFactory, ServiceProvider protocols
    ├── container.py                 # ServiceContainer (DI core)
    └── lifecycle.py                 # ServiceDescriptor, lifecycle management

waivern-llm (LLM Services)           # LLM services + DI adapters
├── services/                        # Pure LLM services (no DI knowledge)
│   ├── base.py                      # BaseLLMService
│   ├── anthropic.py                 # AnthropicLLMService
│   ├── factory.py                   # Simple provider selection
│   └── errors.py                    # LLM errors
└── di/                              # Optional DI integration
    ├── factory.py                   # ServiceFactory[BaseLLMService] adapter
    ├── provider.py                  # LLMServiceProvider (high-level API)
    └── configuration.py             # LLM service configuration
```

**Architecture Rationale:**

**Generic DI in `waivern-core`:**
- Service management is foundational infrastructure, like schemas and messages
- Available to all components: connectors, analysers, and future tools
- Connectors may need services (database pools, caches, HTTP clients)
- Clean dependency: all components depend on `waivern-core` anyway
- Core stays clean with only generic abstractions

**LLM DI adapters in `waivern-llm`:**
- Co-location: LLM service + DI adapter together
- Optional: Use `waivern_llm.services` directly OR `waivern_llm.di` for DI integration
- Single source of truth for LLM service creation
- Other service libraries follow same pattern (e.g., `waivern-database/di/`)

---

## Consequences

### Positive ✅

**Unified Pattern for All Services:**
- Same approach for LLM, database, cache, HTTP clients
- Consistent learning curve across framework
- Reduced cognitive load for contributors

**Testability:**
- Easy to inject mock services for unit tests
- Explicit dependencies in constructor
- No global state to manage between tests
- Example:
  ```python
  # Test setup
  container.register(BaseLLMService, lambda: MockLLMService())
  analyser = PersonalDataAnalyser(config, LLMServiceProvider(container))
  ```

**Extensibility:**
- Add new service types without changing core container
- Support third-party services easily
- Future features (health checking, retry logic) slot in naturally

**Type Safety:**
- Full generic type support (`ServiceFactory[T]`, `get_service[T]()`)
- Basedpyright strict mode compatible
- Catch errors at compile time, not runtime

**Production Ready:**
- Lifecycle management (creation, caching, disposal)
- Graceful degradation (service unavailable = None, not crash)
- Health checking support (future)
- Retry logic infrastructure (future)

**Clean Separation:**
- `waivern-llm` remains pure service library
- DI concerns isolated in `waivern-core` as foundational infrastructure
- Infrastructure layer doesn't know about application layer
- Available to all components (connectors, analysers, tools)

**Industry Alignment:**
- Follows .NET Core DI, Spring Framework patterns
- Well-understood in enterprise Python
- Easier onboarding for experienced developers

---

### Negative ⚠️

**Additional Complexity:**
- 3 new abstractions (Factory, Container, Provider)
- Contributors must understand DI pattern
- More code to maintain (~500 lines vs ~40 for old manager)
- Learning curve for Python developers unfamiliar with DI

**Implementation Effort:**
- Update all 3 analysers (PersonalData, ProcessingPurpose, DataSubject)
- Update test files
- Write comprehensive tests for DI system
- Documentation updates

**Potential Misuse:**
- Developers might over-engineer simple scenarios
- Risk of creating "God Container" with too many services
- Need guidelines on when to use DI vs simple instantiation

---

### Neutral ➡️

**Pattern Follows Industry Standards:**
- Similar to .NET Core DI, Spring Framework
- Python libraries: `dependency-injector`, `pinject`
- Well-documented pattern with known trade-offs
- Clear migration path from other ecosystems

**Framework Evolution:**
- Natural progression as framework matures
- Aligns with growth in service types
- Prepares for enterprise-scale deployments
- Investment in future-proofing

**Code Volume Trade-off:**
- More lines of code in framework
- But less duplication per-analyser
- Net positive as service count grows
- Better than N manager classes

---

## Future Enhancements

### Phase 2 (Post-Initial Release): Additional Services

```python
# Database service
container.register(
    DatabaseConnectionPool,
    DatabasePoolFactory(max_connections=10),
    lifetime="singleton"
)

# Cache service
container.register(
    CacheService,
    RedisCacheFactory(host="localhost", port=6379),
    lifetime="singleton",
    health_check_interval=timedelta(minutes=1)
)

# HTTP client
container.register(
    HTTPClient,
    HTTPClientFactory(timeout=30, retries=3),
    lifetime="singleton"
)
```

### Phase 3 (Future): Advanced Features

- **Scoped services**: Per-request lifetime (like ASP.NET Core scopes)
- **Service discovery**: Dynamic registration from plugins
- **Circuit breaker**: Prevent cascading failures
- **Retry with backoff**: Automatic recovery from transient errors
- **Connection pooling**: Efficient resource management


---

## Success Metrics

**Before Implementation:**
- 1 service type managed (LLM)
- 1 manager class (~40 lines)
- Testing requires mocking factory methods
- No standardised pattern

**After Implementation:**
- ∞ service types supported (generic pattern)
- 1 container + N lightweight providers
- Testing via dependency injection (clean)
- Standardised DI pattern framework-wide

**Verification:**
- All existing tests pass
- New DI tests comprehensive
- Sample runbooks work
- Type checking passes (strict mode)
- Documentation complete

---

## Related Documents

- **Implementation Plan:** [dependency-injection-implementation-plan.md](../architecture/dependency-injection-implementation-plan.md)
- **ADR-0001:** [Explicit Schema Loading](0001-explicit-schema-loading-over-autodiscovery.md) - Similar principle of explicit over implicit

---

## References

### Industry Patterns
- **.NET Core Dependency Injection:** https://docs.microsoft.com/en-us/dotnet/core/extensions/dependency-injection
- **Spring Framework DI:** https://spring.io/guides/gs/spring-boot/
- **Python dependency-injector:** https://python-dependency-injector.ets-labs.org/
- **Inversion of Control Containers (Martin Fowler):** https://martinfowler.com/articles/injection.html

### Architecture Decision Records
- **Michael Nygard's ADR Template:** https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- **ADR GitHub:** https://adr.github.io/

### Existing WCF Patterns
- **Schema Explicit Loading:** ADR-0001 demonstrates preference for explicit over implicit patterns
- **Package Independence:** Monorepo structure values clean separation of concerns
- **Type Safety First:** Framework uses basedpyright strict mode throughout
