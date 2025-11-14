# Task: Implement ArtifactConnector

- **Phase:** Unified Connector Architecture - Phase 1
- **Status:** TODO
- **Prerequisites:** ArtifactStore Service (Tasks 1-3)
- **Related Issue:** #226

## Context

Creates ArtifactConnector, a new connector type that retrieves data from the artifact store instead of external sources. This is the first step towards unified connector architecture where every step has a connector. Full plan: `docs/development/active/unified-connector-architecture-plan.md`.

## Purpose

Enable pipeline steps to explicitly declare artifact retrieval as a connector operation, unifying the execution model (connector → analyser for all steps).

## Problem

Currently, pipeline steps use `input_from` field and have no connector:
```yaml
- id: "classify"
  input_from: "extract"  # Implicit artifact retrieval
  analyser: data_subject_analyser
```

This creates two execution modes in Executor (lines 330-371):
- Mode 1: Connector-based (extract from external source)
- Mode 2: Pipeline-based (retrieve from artifacts)

The dual-mode logic increases complexity and uses optional types (`Connector | None`).

## Proposed Solution

Create ArtifactConnector that implements Connector interface and retrieves Messages from ArtifactStore. This allows explicit declaration of artifact retrieval as a connector operation.

## Decisions Made

1. **Interface compliance** - ArtifactConnector implements full Connector interface
2. **Configuration** - Takes `step_id` property specifying which artifact to retrieve
3. **Output schema** - Dynamically resolves from retrieved Message
4. **Error handling** - Propagate ArtifactStoreError as ConnectorError
5. **Dependency injection** - Receives ArtifactStore via constructor

## Expected Outcome & Usage Example

**Updated runbook format:**
```yaml
connectors:
  - name: "mysql_source"
    type: "mysql"
    properties: {...}
  - name: "previous_step"
    type: "artifact"  # NEW connector type
    properties:
      step_id: "extract"

execution:
  - id: "extract"
    connector: "mysql_source"
    analyser: personal_data_analyser
    save_output: true

  - id: "classify"
    connector: "previous_step"  # Required field, no more input_from
    analyser: data_subject_analyser
```

## Implementation

### Changes Required

#### 1. Create ArtifactConnector Configuration Class

**Location:** `libs/waivern-artifact-connector/src/waivern_artifact_connector/config.py` (new package)

**Purpose:** Define configuration schema for ArtifactConnector

**Configuration:**
```python
class ArtifactConnectorConfig(BaseModel):
    step_id: str  # Which artifact to retrieve
```

**Validation:**
- step_id must be non-empty string
- Pydantic handles validation automatically

#### 2. Implement ArtifactConnector Class

**Location:** `libs/waivern-artifact-connector/src/waivern_artifact_connector/artifact_connector.py`

**Purpose:** Connector that retrieves Messages from artifact store

**Algorithm (pseudo-code):**
```python
class ArtifactConnector(Connector):
    def __init__(config: ArtifactConnectorConfig, artifact_store: ArtifactStore):
        self.config = config
        self.artifact_store = artifact_store
        self._cached_message: Message | None = None  # Cache for schema resolution

    def get_supported_output_schemas() -> list[Schema]:
        # CRITICAL: Executor calls this BEFORE extract() to match schemas
        # Must peek at artifact to get schema WITHOUT consuming it
        if self._cached_message is None:
            try:
                self._cached_message = self.artifact_store.get(self.config.step_id)
            except ArtifactNotFoundError as e:
                # Artifact doesn't exist yet - return empty (will fail schema matching)
                logger.warning(f"Artifact '{self.config.step_id}' not found during schema resolution")
                return []

        if self._cached_message.schema is None:
            return []

        return [self._cached_message.schema]

    def extract(output_schema: Schema) -> Message:
        # Return cached message if available (from schema resolution)
        if self._cached_message:
            message = self._cached_message
            self._cached_message = None  # Clear cache after consumption
            return message

        # Otherwise fetch fresh (fallback case)
        try:
            return self.artifact_store.get(self.config.step_id)
        except ArtifactNotFoundError as e:
            raise ConnectorError(f"Artifact not found: {self.config.step_id}") from e
```

**Key design decisions:**
- `get_supported_output_schemas()` peeks at artifact and caches the Message
- Cached Message reused in `extract()` to avoid double-fetching
- Error conversion: ArtifactNotFoundError → ConnectorError
- No schema validation needed (Message already validated)
- Cache cleared after extraction to prevent stale data

#### 3. Create ComponentFactory for ArtifactConnector

**Location:** Same package

**Purpose:** Factory for instantiating ArtifactConnector with dependencies

**Algorithm (pseudo-code):**
```python
class ArtifactConnectorFactory(ComponentFactory[Connector]):
    def __init__(self, container: ServiceContainer):
        self._container = container

    def get_component_name(self) -> str:
        return "artifact"

    def can_create(self, properties: dict) -> bool:
        # Validate config and check ArtifactStore availability
        try:
            ArtifactConnectorConfig.model_validate(properties)
            artifact_store = self._container.get_service(ArtifactStore)
            return artifact_store is not None
        except (ValidationError, Exception):
            return False

    def create(self, properties: dict) -> Connector:
        config = ArtifactConnectorConfig.model_validate(properties)
        artifact_store = self._container.get_service(ArtifactStore)
        return ArtifactConnector(config, artifact_store)
```

**Dependency injection:**
- Factory receives ServiceContainer (matches pattern used by MySQL, Filesystem connectors)
- Resolves ArtifactStore from container using Service Locator pattern
- Passes store to each ArtifactConnector instance

#### 4. Register as Entry Point

**Location:** `libs/waivern-artifact-connector/pyproject.toml`

**Purpose:** Make ArtifactConnector discoverable by Executor

**Entry point:**
```toml
[project.entry-points."waivern.connectors"]
artifact = "waivern_artifact_connector:ArtifactConnectorFactory"
```

#### 5. Create Package Structure

**New package:** `libs/waivern-artifact-connector/`

**Structure:**
```
libs/waivern-artifact-connector/
├── pyproject.toml
├── src/waivern_artifact_connector/
│   ├── __init__.py
│   ├── artifact_connector.py
│   └── config.py
├── tests/
│   └── test_artifact_connector.py
└── scripts/
    ├── lint.sh
    ├── format.sh
    └── type-check.sh
```

## Testing

### Testing Strategy

Unit tests for connector operations and integration tests with artifact store.

### Test Scenarios

#### 1. Successful Artifact Retrieval

**Setup:**
- Create ArtifactStore with saved Message
- Create ArtifactConnector configured for that step_id
- Call extract()

**Expected behaviour:**
- Returns exact Message from store
- No schema conversion or validation

#### 2. Missing Artifact Error

**Setup:**
- Create empty ArtifactStore
- Create ArtifactConnector for non-existent step_id
- Call extract()

**Expected behaviour:**
- Raises ConnectorError
- Error message mentions step_id
- Original ArtifactNotFoundError as cause

#### 3. Configuration Validation

**Setup:**
- Create ArtifactConnectorConfig with invalid data
- Attempt instantiation

**Expected behaviour:**
- Pydantic validation raises error
- Empty step_id rejected

#### 4. Factory Pattern

**Setup:**
- Create factory with artifact store
- Create multiple connectors via factory

**Expected behaviour:**
- Each connector receives same store instance
- Configuration parsed correctly
- Connectors function independently

#### 5. Schema Declaration

**Setup:**
- Create ArtifactConnector
- Call get_supported_output_schemas()

**Expected behaviour:**
- Returns empty list (or appropriate marker)
- Schema resolution deferred to runtime

### Validation Commands

```bash
# Run artifact connector tests
uv run pytest libs/waivern-artifact-connector/tests/ -v

# Run quality checks
cd libs/waivern-artifact-connector && ./scripts/dev-checks.sh

# Run all workspace checks
./scripts/dev-checks.sh
```

## Implementation Notes

**Package organisation:**
- Standalone package (follows waivern-mysql, waivern-filesystem pattern)
- Minimal dependencies: waivern-core, waivern-core[services]
- Standard scripts for quality checks

**Design principles:**
- Full Connector interface compliance
- Dependency injection for ArtifactStore
- Error handling with context preservation
- No special-case logic (standard connector behaviour)

**Future considerations:**
- Schema resolution might need refinement
- Consider caching retrieved Messages
- Support for artifact metadata (timestamps, provenance)
