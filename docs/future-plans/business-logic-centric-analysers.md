# Business-Logic-Centric Analysers with Service Injection

- **Status:** Design Proposal
- **Last Updated:** 2025-11-26
- **Related:** [Artifact-Centric Orchestration](../architecture/artifact-centric-orchestration.md)

## Overview

This document proposes a pattern for building **business-logic-centric analysers** that abstract away implementation details (HTTP calls, AI agents, human approval) through service injection. Rather than creating implementation-specific components like `HttpAnalyser` or `AgentAnalyser`, we create domain-focused analysers like `Nis2PolicyAnalyser` that consume injected services.

## Design Principles

1. **Business Logic First** - Analyser names reflect their compliance domain, not implementation
2. **Service Abstraction** - Implementation details (HTTP, AI, human) are injected services
3. **Artifact-Based I/O** - Use `ArtifactStore` as the standard inter-step data exchange
4. **Existing Patterns** - Build on the established `ServiceContainer` and `ComponentFactory` patterns

## Current State

The framework already has the foundational patterns:

```
ServiceContainer (singleton services)
       ↓
ComponentFactory (bridges services → components)
       ↓
Analyser (receives services via constructor)
```

**Existing Services:**

- `BaseLLMService` - LLM provider abstraction
- `ArtifactStore` - Inter-step message storage

## Proposed Services

### HttpService

A service for making HTTP calls to remote endpoints:

```python
class HttpService(ABC):
    def post(url, payload, headers, timeout) -> HttpResponse: ...
    def get(url, params, headers, timeout) -> HttpResponse: ...
```

Follows existing `ServiceFactory` pattern for registration.

### Enhanced ArtifactStore

Extend existing `ArtifactStore` with raw data support:

```python
class ArtifactStore(ABC):
    # Existing (async, run_id per operation)
    async def save(self, run_id: str, key: str, message: Message) -> None: ...
    async def get(self, run_id: str, key: str) -> Message: ...
    async def list_keys(self, run_id: str, prefix: str = "") -> list[str]: ...

    # Proposed additions for raw data
    async def save_raw(self, run_id: str, key: str, data: bytes, content_type: str) -> None: ...
    async def get_raw(self, run_id: str, key: str) -> tuple[bytes, str]: ...
```

## Business-Logic-Centric Analyser Pattern

### Example: Nis2PolicyAnalyser

```python
class Nis2PolicyAnalyser(Analyser):
    """Analyses systems against NIS2 policy requirements."""

    def __init__(self, config, http_service: HttpService | None = None):
        self._config = config
        self._http_service = http_service  # Injected via factory

    def process_data(self, message: Message) -> Message:
        # Transform input → call remote service → transform output
        request = self._build_request(message)
        response = self._http_service.post(self._config.endpoint, request)
        findings = self._parse_response(response)
        return Message(content={"findings": findings}, schema=NIS2_FINDING_SCHEMA)
```

### Factory

```python
class Nis2PolicyAnalyserFactory(ComponentFactory):
    def create(self, config) -> Nis2PolicyAnalyser:
        http_service = self._container.get_service(HttpService)
        return Nis2PolicyAnalyser(config, http_service)
```

## More Examples

### AI Agent Analyser (Long-Running)

```python
class GdprRiskAssessmentAnalyser(Analyser):
    """GDPR risk assessment using multi-step LLM reasoning."""

    def __init__(self, config, llm_service: BaseLLMService | None = None):
        self._llm_service = llm_service

    def process_data(self, message: Message) -> Message:
        # Multi-step agent workflow using injected LLM service
        for entity in message.content["entities"]:
            sensitivity = self._classify_sensitivity(entity)
            activities = self._identify_activities(entity)
            risk = self._assess_risk(entity, sensitivity, activities)
        return Message(content={"findings": risks}, schema=RISK_FINDING_SCHEMA)
```

### Human Approval Analyser (Blocking)

```python
class LegalReviewAnalyser(Analyser):
    """Routes findings to legal team for review."""

    def __init__(self, config, http_service: HttpService | None = None):
        self._http_service = http_service

    def process_data(self, message: Message) -> Message:
        # Submit to workflow system, poll until approved/rejected
        submission = self._http_service.post(workflow_url, findings)
        while True:
            status = self._http_service.get(status_url)
            if status["approved"]:
                return Message(content=reviewed_findings)
            sleep(poll_interval)
```

## Benefits

1. **Separation of Concerns** - Analysers focus on compliance logic, services handle HTTP/polling/retries
2. **Testability** - Mock services in tests, test analyser logic independently
3. **Flexibility** - Same analyser can use different service implementations
4. **Consistency** - Follows established WCF DI patterns

## Implementation Phases

1. **HttpService Package** - Create `waivern-http` with `HttpService` interface
2. **First Business-Logic Analyser** - Validate pattern end-to-end
3. **Enhanced ArtifactStore** - Add raw storage and fan-in support
4. **Additional Analysers** - Build out as needed

## Related Documents

- [Artifact-Centric Orchestration](../architecture/artifact-centric-orchestration.md) - Execution engine
- [Dynamic and Agentic Workflows](./dynamic-and-agentic-workflows.md) - Future evolution
