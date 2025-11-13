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

**Future runbook format (not yet used):**
```yaml
execution:
  - id: "extract"
    connector:
      type: "mysql"
      properties: {...}
    analyser: personal_data_analyser
    save_output: true

  - id: "classify"
    connector:
      type: "artifact"  # NEW connector type
      properties:
        step_id: "extract"
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

    def get_supported_output_schemas() -> list[Schema]:
        # Cannot know output schema until extraction
        # Return empty list or special marker
        return []

    def extract(output_schema: Schema) -> Message:
        try:
            message = self.artifact_store.get(self.config.step_id)
            # Message already has schema, return as-is
            return message
        except ArtifactNotFoundError as e:
            raise ConnectorError(f"Artifact not found: {self.config.step_id}") from e
```

**Key design decisions:**
- `get_supported_output_schemas()` returns empty list (schema determined at runtime)
- `extract()` retrieves Message from store
- Error conversion: ArtifactNotFoundError → ConnectorError
- No schema validation needed (Message already validated)

#### 3. Create ComponentFactory for ArtifactConnector

**Location:** Same package

**Purpose:** Factory for instantiating ArtifactConnector with dependencies

**Algorithm (pseudo-code):**
```python
class ArtifactConnectorFactory(ComponentFactory[Connector]):
    def __init__(artifact_store: ArtifactStore):
        self.artifact_store = artifact_store

    def create(config: dict) -> Connector:
        connector_config = ArtifactConnectorConfig(**config)
        return ArtifactConnector(connector_config, self.artifact_store)
```

**Dependency injection:**
- Factory receives ArtifactStore from Executor
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
