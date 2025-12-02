# Design: Artifact-Centric Orchestration

- **Epics:** #189, #190
- **Status:** Ready for Review
- **Last Updated:** 2025-11-26

## Overview

Replace the current step-based runbook format and sequential executor with an artifact-centric model and DAG-based parallel execution.

## Current State

```
┌─────────────────────────────────────────────────────────────┐
│  Current Architecture                                        │
│                                                              │
│  Runbook (3 sections)     Executor (sequential)              │
│  ├── connectors: [...]    ├── for step in steps:            │
│  ├── analysers: [...]     │     extract or get artifact      │
│  └── execution: [...]     │     process                      │
│                           │     save if save_output          │
│                           └── return results                 │
└─────────────────────────────────────────────────────────────┘
```

**Issues:**
- Three separate sections with cross-references
- Sequential execution (no parallelism)
- `save_output: true` required for pipeline chaining
- Schema resolution scattered across executor methods

## Target State

```
┌─────────────────────────────────────────────────────────────┐
│  New Architecture                                            │
│                                                              │
│  Runbook (1 section)      Planner           Executor         │
│  └── artifacts:           ├── parse         ├── parallel     │
│        a: source(...)     ├── build DAG     ├── async        │
│        b: inputs: a       ├── validate      └── fan-in       │
│        c: inputs: [a,b]   └── ExecutionPlan                  │
└─────────────────────────────────────────────────────────────┘
```

## Package Structure

```
libs/
└── waivern-orchestration/          # NEW PACKAGE
    └── src/waivern_orchestration/
        ├── __init__.py
        ├── models.py               # ArtifactDef, ExecutionPlan
        ├── parser.py               # YAML → models
        ├── dag.py                  # ExecutionDAG (graphlib wrapper)
        ├── planner.py              # Planner class
        ├── executor.py             # DAGExecutor class
        └── errors.py

apps/wct/
└── src/wct/
    ├── executor.py                 # REMOVE: replaced by waivern_orchestration.executor
    ├── runbook.py                  # REMOVE: import from waivern-orchestration
    └── cli.py                      # UPDATE: use Planner + DAGExecutor
```

## Data Models

### ArtifactDefinition

```python
class SourceConfig(BaseModel):
    """Connector configuration for source artifacts."""
    type: str                           # e.g., "mysql", "filesystem"
    properties: dict[str, Any] = {}

class TransformConfig(BaseModel):
    """Analyser configuration for derived artifacts."""
    type: str                           # e.g., "personal_data_analyser"
    properties: dict[str, Any] = {}

class RunbookConfig(BaseModel):
    """Execution configuration for the runbook."""
    timeout: int | None = None          # Total execution timeout (seconds)
    cost_limit: float | None = None     # Total LLM cost cap
    max_concurrency: int = 10           # Max parallel artifacts
    max_child_depth: int = 3            # Max recursive depth for child runbooks

class ExecuteConfig(BaseModel):
    """Configuration for recursive runbook execution (child override)."""
    mode: Literal["child"] = "child"
    timeout: int | None = None          # Override parent timeout for this child
    cost_limit: float | None = None     # Override parent cost limit for this child

class ArtifactDefinition(BaseModel):
    """Single artifact in the runbook."""
    # Metadata (business requirements)
    name: str | None = None             # Human-readable name
    description: str | None = None      # What this artifact represents
    contact: str | None = None          # Responsible party

    # Data source (mutually exclusive)
    source: SourceConfig | None = None
    inputs: str | list[str] | None = None

    # Transformation
    transform: TransformConfig | None = None
    merge: Literal["concatenate"] = "concatenate"  # See ADR-0003

    # Schema override (optional - inferred from components if not specified)
    input_schema: str | None = None
    output_schema: str | None = None

    # Behaviour
    output: bool = False                # Export this artifact
    optional: bool = False              # Skip dependents on failure

    # Recursive execution (Phase 2 - model now, implement later)
    execute: ExecuteConfig | None = None  # Execute input artifact as child runbook

    @model_validator
    def validate_source_xor_inputs(self) -> Self:
        # source XOR inputs (not both, not neither)
        ...
```

### Runbook

```python
class Runbook(BaseModel):
    """Artifact-centric runbook.

    Also registered as a schema - enabling runbooks to be artifact outputs
    for composable/recursive execution (agentic workflows).
    """
    name: str
    description: str
    contact: str | None = None
    config: RunbookConfig = Field(default_factory=RunbookConfig)
    artifacts: dict[str, ArtifactDefinition]
```

### ExecutionPlan

```python
@dataclass(frozen=True)
class ExecutionPlan:
    """Immutable, validated execution plan."""
    runbook: Runbook
    dag: ExecutionDAG
    artifact_schemas: dict[str, tuple[Schema, Schema]]  # input, output per artifact
```

## ExecutionDAG

Thin wrapper around `graphlib.TopologicalSorter`:

```python
class ExecutionDAG:
    def __init__(self, artifacts: dict[str, ArtifactDefinition]) -> None:
        self._graph: dict[str, set[str]] = {}
        self._build(artifacts)

    def _build(self, artifacts: dict[str, ArtifactDefinition]) -> None:
        for aid, defn in artifacts.items():
            deps = self._extract_deps(defn.inputs)
            self._graph[aid] = deps

    def validate(self) -> None:
        """Raises CycleError if cycles detected."""
        TopologicalSorter(self._graph).prepare()

    def create_sorter(self) -> TopologicalSorter[str]:
        ts = TopologicalSorter(self._graph)
        ts.prepare()
        return ts
```

## Planner

Responsibilities:

1. Parse YAML into Runbook model
2. Build ExecutionDAG from artifact dependencies
3. Validate: cycles, missing refs, schema compatibility
4. Produce immutable ExecutionPlan

The Planner discovers components via entry points directly - self-contained with no external registry dependency:

```python
class Planner:
    def __init__(self) -> None:
        # Discover component factories from entry points
        self._connector_factories = self._load_entry_points("waivern.connectors")
        self._analyser_factories = self._load_entry_points("waivern.analysers")

    def _load_entry_points(self, group: str) -> dict[str, ComponentFactory]:
        """Load component factories from entry points."""
        factories = {}
        for ep in importlib.metadata.entry_points(group=group):
            factories[ep.name] = ep.load()()
        return factories

    def plan(self, runbook_path: Path) -> ExecutionPlan:
        runbook = self._parse(runbook_path)
        dag = ExecutionDAG(runbook.artifacts)
        dag.validate()
        self._validate_refs(runbook)
        schemas = self._resolve_schemas(runbook)
        return ExecutionPlan(runbook=runbook, dag=dag, artifact_schemas=schemas)

    def _validate_refs(self, runbook: Runbook) -> None:
        """Validate all `inputs` references point to existing artifacts."""
        ...

    def _resolve_schemas(self, runbook: Runbook) -> dict[str, tuple[Schema, Schema]]:
        """Resolve and validate schema compatibility for each artifact."""
        ...
```

## DAGExecutor

Async orchestration with sync analyser execution via ThreadPoolExecutor:

```python
class DAGExecutor:
    def __init__(self, container: ServiceContainer) -> None:
        self._container = container

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        # Use config from runbook
        config = plan.runbook.config
        semaphore = asyncio.Semaphore(config.max_concurrency)
        thread_pool = ThreadPoolExecutor(max_workers=config.max_concurrency)

        store = self._container.get_service(ArtifactStore)
        store.clear()

        sorter = plan.dag.create_sorter()
        results: dict[str, ArtifactResult] = {}
        skipped: set[str] = set()

        while sorter.is_active():
            ready = [aid for aid in sorter.get_ready() if aid not in skipped]
            tasks = [self._produce(aid, plan, store, skipped) for aid in ready]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for aid, result in zip(ready, batch_results):
                results[aid] = result
                sorter.done(aid)
                if isinstance(result, Exception) or not result.success:
                    self._skip_dependents(aid, plan.dag, skipped)

        return ExecutionResult(artifacts=results, skipped=skipped)

    async def _produce(
        self,
        artifact_id: str,
        plan: ExecutionPlan,
        store: ArtifactStore,
        skipped: set[str],
    ) -> ArtifactResult:
        async with self._semaphore:
            defn = plan.runbook.artifacts[artifact_id]

            if defn.source:
                message = await self._run_connector(defn.source)
            elif defn.execute:
                # Phase 3: Recursive execution
                message = await self._run_child_runbook(defn, store)
            else:
                input_messages = self._gather_inputs(defn.inputs, store)
                merged = self._merge(input_messages)  # Always concatenate (ADR-0003)
                message = await self._run_analyser(defn.transform, merged)

            store.save(artifact_id, message)
            return ArtifactResult(artifact_id=artifact_id, success=True, message=message)

    async def _run_child_runbook(
        self,
        defn: ArtifactDefinition,
        store: ArtifactStore,
    ) -> Message:
        """Execute input artifact as child runbook. (Phase 3)"""
        raise NotImplementedError("Recursive runbook execution not yet implemented")

    async def _run_connector(self, source: SourceConfig) -> Message:
        """Run connector in thread pool (sync → async bridge)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._thread_pool,
            self._sync_extract,
            source,
        )
```

## Schema Resolution

Schema resolution moves from executor to planner. The planner validates compatibility upfront using discovered component factories:

```python
def _resolve_schemas(self, runbook: Runbook) -> dict[str, tuple[Schema, Schema]]:
    result = {}

    for aid, defn in runbook.artifacts.items():
        # Use explicit schema override if specified
        if defn.output_schema:
            explicit_output = self._get_schema(defn.output_schema)
        else:
            explicit_output = None

        if defn.source:
            factory = self._connector_factories[defn.source.type]
            output_schema = explicit_output or factory.component_class.get_output_schema()

            if defn.transform:
                analyser_factory = self._analyser_factories[defn.transform.type]
                self._validate_compatible(output_schema, analyser_factory.component_class.get_input_schema())
                final_schema = analyser_factory.component_class.get_output_schema()
            else:
                final_schema = output_schema

            result[aid] = (output_schema, final_schema)
        else:
            # Derived artifact - input schema from upstream
            upstream_schemas = [result[up][1] for up in self._get_deps(defn)]
            # Validate all upstream schemas are compatible
            ...

    return result
```

## ArtifactStore Changes

Add `list_artifacts()` for observability:

```python
class ArtifactStore(ABC):
    @abstractmethod
    def save(self, artifact_id: str, message: Message) -> None: ...

    @abstractmethod
    def get(self, artifact_id: str) -> Message: ...

    @abstractmethod
    def exists(self, artifact_id: str) -> bool: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def list_artifacts(self) -> list[str]: ...  # NEW
```

### ScopedArtifactStore (Phase 3)

For recursive runbook execution, child runbooks use a scoped store that can read parent artifacts but writes to its own namespace:

```python
class ScopedArtifactStore(ArtifactStore):
    """Scoped store for child runbook execution.

    - Child can read any parent artifact (inherited context)
    - Child writes to its own namespace (no collision risk)
    - Specified outputs promoted to parent on completion
    """
    def __init__(self, parent: ArtifactStore) -> None:
        self._parent = parent
        self._local: dict[str, Message] = {}

    def get(self, artifact_id: str) -> Message:
        if artifact_id in self._local:
            return self._local[artifact_id]
        return self._parent.get(artifact_id)  # Delegate to parent

    def save(self, artifact_id: str, message: Message) -> None:
        self._local[artifact_id] = message  # Always write locally

    def promote(self, artifact_id: str, parent_id: str) -> None:
        """Promote local artifact to parent store."""
        self._parent.save(parent_id, self._local[artifact_id])
```

## CLI Changes

```bash
# Existing (unchanged)
wct run <runbook.yaml>
wct validate-runbook <runbook.yaml>

# New
wct inspect <runbook.yaml> <artifact_id>   # View artifact after execution
wct visualize <runbook.yaml>               # Future: DAG visualization
```

## Error Handling

Per-artifact `optional` flag:

```yaml
artifacts:
  llm_enriched:
    inputs: findings
    transform:
      type: llm_enricher
    optional: true  # Skip dependents on failure
```

When `optional: true` artifact fails:
1. Log warning
2. Mark as failed in results
3. Skip all dependents
4. Continue with independent branches

## Observability

Logging format:

```
[INFO] Starting artifact: db_schema
[INFO] Completed artifact: db_schema (1.2s)
[INFO] Starting artifacts: db_findings, log_findings (parallel)
[INFO] Completed artifact: db_findings (3.4s)
[ERROR] Failed artifact: log_findings - ConnectionError
[WARN] Skipping artifact: combined_findings (dependency failed)
[INFO] Execution complete: 3 succeeded, 1 failed, 1 skipped
```

## Sample Runbook Migration

**Before (current):**
```yaml
connectors:
  - name: "log_files"
    type: "filesystem_connector"
    properties:
      path: "./logs"

analysers:
  - name: "pda"
    type: "personal_data_analyser"
    properties:
      llm_validation:
        enable_llm_validation: false

execution:
  - id: "analyse_logs"
    name: "Analyse Logs"
    connector: "log_files"
    analyser: "pda"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
```

**After (artifact-centric):**
```yaml
name: "Log Analysis"
description: "Analyse logs for personal data"
contact: "Security Team <security@company.com>"

config:
  timeout: 1800              # 30 minutes max
  cost_limit: 10.0           # $10 LLM budget
  max_concurrency: 5

artifacts:
  log_content:
    name: "Log Files"
    description: "Raw log file content from application servers"
    source:
      type: filesystem_connector
      properties:
        path: "./logs"

  findings:
    name: "Personal Data Findings"
    description: "Personal data detected in log files"
    contact: "DPO <dpo@company.com>"
    inputs: log_content
    transform:
      type: personal_data_analyser
      properties:
        llm_validation:
          enable_llm_validation: false
    output: true
```

## Phased Implementation

### Phase 1 - Foundation (This Design)

Core artifact-centric orchestration:
- `waivern-orchestration` package with models, parser, DAG, planner, executor
- `DAGExecutor` with parallel execution via asyncio + ThreadPoolExecutor
- Entry point discovery for components
- Schema validation at plan time
- Fan-in support with concatenate merge (same-schema only, see [ADR-0003](../../adr/0003-fan-in-handling-and-transformer-pattern.md))
- `RunbookConfig` enforcement (timeout, cost_limit, max_concurrency)
- `list_artifacts()` for observability

### Phase 2 - Transformers (Deferred)

Multi-schema fan-in via Transformer components:
- New component type: Transformer (multiple schemas in, single schema out)
- New entry point group: `waivern.transformers`
- Planner validates transformer input schemas match upstream outputs
- Enables combining different data types (e.g., database schema + source code findings)

See [ADR-0003](../../adr/0003-fan-in-handling-and-transformer-pattern.md) and [Phase 2 Design](artifact-centric-orchestration/phase-2-transformers-design.md) for details.

### Phase 3 - Child Runbooks (Deferred)

Recursive/composable runbook execution:
- `_run_child_runbook()` implementation in DAGExecutor
- `ScopedArtifactStore` implementation
- Child depth tracking and `max_child_depth` enforcement
- Runbook-as-schema registration

See [Phase 3 Design](artifact-centric-orchestration/phase-3-child-runbooks-design.md) for details.

**Models included now** (`RunbookConfig`, `ExecuteConfig`, `execute` field) to avoid schema changes later.

## Design Decisions

1. **Component Discovery** - The Planner discovers components via entry points directly, making it self-contained with no external registry dependency.

2. **Schema Handling** - Schemas are inferred from component declarations by default, with optional explicit `input_schema`/`output_schema` overrides for future extensibility.

3. **Artifact Metadata** - Per-artifact metadata (`name`, `description`, `contact`) is preserved as these are business requirements rather than functional requirements.

4. **Fan-In Handling** - All fan-in inputs must have the same schema (name AND version). Different-schema fan-in requires explicit Transformer components (Phase 2). Only "concatenate" merge strategy is supported. See [ADR-0003](../../adr/0003-fan-in-handling-and-transformer-pattern.md).

5. **Executor Location** - DAGExecutor lives in `waivern-orchestration` alongside Planner, keeping all orchestration logic in one package. WCT imports and wires these components together.
