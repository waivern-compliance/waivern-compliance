# Design: Artifact-Centric Orchestration

- **Status:** Completed
- **Last Updated:** 2025-12-15

## Overview

The artifact-centric orchestration system replaces the previous step-based runbook format with a unified artifact model and DAG-based parallel execution. This design treats data artifacts as first-class citizens, with transformations as edges between them.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Architecture                                                │
│                                                              │
│  Runbook (1 section)      Planner           Executor         │
│  └── artifacts:           ├── parse         ├── parallel     │
│        a: source(...)     ├── flatten       ├── async        │
│        b: inputs: a       ├── build DAG     └── fan-in       │
│        c: inputs: [a,b]   ├── validate                       │
│        d: child_runbook   └── ExecutionPlan                  │
└─────────────────────────────────────────────────────────────┘
```

## Package Structure

```
libs/waivern-orchestration/
└── src/waivern_orchestration/
    ├── __init__.py
    ├── models.py               # Runbook, ArtifactDefinition, ExecutionResult
    ├── parser.py               # YAML → Runbook model
    ├── dag.py                  # ExecutionDAG (graphlib wrapper)
    ├── planner.py              # Planner class, ExecutionPlan
    ├── flattener.py            # Child runbook flattening
    ├── path_resolver.py        # Secure child runbook path resolution
    ├── executor.py             # DAGExecutor class
    ├── utils.py                # Shared utilities (schema parsing, namespacing)
    └── errors.py               # Typed exceptions
```

## Data Models

### ArtifactDefinition

```python
class SourceConfig(BaseModel):
    """Connector configuration for source artifacts."""
    type: str                           # e.g., "mysql", "filesystem"
    properties: dict[str, Any] = {}

class ProcessConfig(BaseModel):
    """Processor configuration for derived artifacts."""
    type: str                           # e.g., "personal_data"
    properties: dict[str, Any] = {}

class ChildRunbookConfig(BaseModel):
    """Configuration for child runbook composition."""
    path: str                           # Relative path to child runbook
    input_mapping: dict[str, str]       # Maps child input names to parent artifacts
    output: str | None = None           # Single output (mutually exclusive with output_mapping)
    output_mapping: dict[str, str] | None = None  # Multiple outputs

class RunbookConfig(BaseModel):
    """Execution configuration for the runbook."""
    timeout: int | None = None          # Total execution timeout (seconds)
    cost_limit: float | None = None     # Total LLM cost cap
    max_concurrency: int = 10           # Max parallel artifacts
    template_paths: list[str] = []      # Directories for child runbook search

class ArtifactDefinition(BaseModel):
    """Single artifact in the runbook."""
    # Metadata (business requirements)
    name: str | None = None             # Human-readable name
    description: str | None = None      # What this artifact represents
    contact: str | None = None          # Responsible party

    # Data source (mutually exclusive with inputs)
    source: SourceConfig | None = None
    inputs: str | list[str] | None = None

    # Processing
    process: ProcessConfig | None = None
    child_runbook: ChildRunbookConfig | None = None  # Runbook composition
    merge: Literal["concatenate"] = "concatenate"

    # Schema override (optional - inferred from components if not specified)
    output_schema: str | None = None

    # Behaviour
    output: bool = False                # Export this artifact
    optional: bool = False              # Skip dependents on failure

    @model_validator
    def validate_artifact_type(self) -> Self:
        # source XOR inputs (not both, not neither for non-child artifacts)
        # child_runbook cannot combine with source or process
        ...
```

### Runbook

```python
class Runbook(BaseModel):
    """Artifact-centric runbook.

    Runbooks with `inputs` and `outputs` sections can be used as child runbooks
    for composable/modular workflows.
    """
    name: str
    description: str
    contact: str | None = None
    config: RunbookConfig = Field(default_factory=RunbookConfig)

    # Child runbook interface (optional)
    inputs: dict[str, RunbookInputDeclaration] | None = None
    outputs: dict[str, RunbookOutputDeclaration] | None = None

    artifacts: dict[str, ArtifactDefinition]
```

### ExecutionPlan

```python
@dataclass(frozen=True)
class ExecutionPlan:
    """Immutable, validated execution plan."""
    runbook: Runbook
    dag: ExecutionDAG
    artifact_schemas: dict[str, tuple[Schema | None, Schema]]  # input, output per artifact
    aliases: dict[str, str] = field(default_factory=dict)  # parent name → namespaced child
    reversed_aliases: dict[str, str] = field(default_factory=dict)  # namespaced → parent name
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
2. Flatten child runbooks into parent (plan-time composition)
3. Build ExecutionDAG from artifact dependencies
4. Validate: cycles, missing refs, schema compatibility
5. Produce immutable ExecutionPlan

The Planner uses a ComponentRegistry for component discovery:

```python
class Planner:
    def __init__(self, registry: ComponentRegistry) -> None:
        self._registry = registry
        self._flattener = ChildRunbookFlattener(registry)

    def plan(self, runbook_path: Path) -> ExecutionPlan:
        runbook = parse_runbook(runbook_path)

        # Flatten child runbooks into parent
        flattened_artifacts, aliases = self._flattener.flatten(runbook, runbook_path)

        # Build DAG from flattened artifacts
        dag = ExecutionDAG(flattened_artifacts)
        dag.validate()

        # Validate references and resolve schemas
        self._validate_refs(flattened_artifacts)
        schemas = self._resolve_schemas(flattened_artifacts)

        return ExecutionPlan(
            runbook=runbook,
            dag=dag,
            artifact_schemas=schemas,
            aliases=aliases,
            reversed_aliases={v: k for k, v in aliases.items()},
        )
```

## DAGExecutor

Async orchestration with sync processor execution via ThreadPoolExecutor:

```python
class DAGExecutor:
    def __init__(self, registry: ComponentRegistry) -> None:
        self._registry = registry

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        config = plan.runbook.config
        semaphore = asyncio.Semaphore(config.max_concurrency)
        thread_pool = ThreadPoolExecutor(max_workers=config.max_concurrency)

        store = self._registry.container.get_service(ArtifactStore)
        store.clear()

        sorter = plan.dag.create_sorter()
        results: dict[str, Message] = {}
        skipped: set[str] = set()

        while sorter.is_active():
            ready = [aid for aid in sorter.get_ready() if aid not in skipped]
            tasks = [self._produce(aid, plan, store) for aid in ready]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for aid, result in zip(ready, batch_results):
                results[aid] = result
                sorter.done(aid)
                if isinstance(result, Exception) or not result.is_success:
                    self._skip_dependents(aid, plan.dag, skipped)

        return ExecutionResult(artifacts=results, skipped=skipped)

    async def _produce(self, artifact_id: str, plan: ExecutionPlan, store: ArtifactStore) -> Message:
        """Produce a single artifact."""
        # Note: Child runbooks are flattened at plan time, so executor
        # only sees regular source/derived artifacts
        defn = plan.artifact_definitions[artifact_id]

        if defn.source:
            message = await self._run_connector(defn.source)
        else:
            input_messages = [store.get(ref) for ref in self._normalise_inputs(defn.inputs)]
            message = await self._run_processor(defn.process, input_messages)

        store.save(artifact_id, message)

        # Add execution context to message
        origin = get_origin_from_artifact_id(artifact_id)
        alias = plan.reversed_aliases.get(artifact_id)
        execution = ExecutionContext(status="success", origin=origin, alias=alias)

        return replace(message, extensions=MessageExtensions(execution=execution))
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
      type: filesystem
      properties:
        path: "./logs"

  findings:
    name: "Personal Data Findings"
    description: "Personal data detected in log files"
    contact: "DPO <dpo@company.com>"
    inputs: log_content
    process:
      type: personal_data
      properties:
        llm_validation:
          enable_llm_validation: false
    output: true
```

## Features Implemented

### Core Orchestration

- `waivern-orchestration` package with models, parser, DAG, planner, executor
- `DAGExecutor` with parallel execution via asyncio + ThreadPoolExecutor
- `ComponentRegistry` for centralised component discovery
- Schema validation at plan time
- Fan-in support with multi-schema matching via `InputRequirement`
- `RunbookConfig` enforcement (timeout, cost_limit, max_concurrency)
- `list_artifacts()` for observability

### Multi-Schema Fan-In

Analysers can declare multiple supported input combinations:

```python
@classmethod
def get_input_requirements(cls) -> list[list[InputRequirement]]:
    return [
        [InputRequirement("personal_data_finding", "1.0.0")],
        [
            InputRequirement("personal_data_finding", "1.0.0"),
            InputRequirement("processing_purpose_finding", "1.0.0"),
        ],
    ]
```

The Planner matches provided inputs against declared requirements using exact set matching.

### Child Runbook Composition

Modular runbook design through plan-time flattening:
- Child runbooks declare inputs/outputs as schema-validated contracts
- Parent runbooks reference children via `child_runbook` directive
- `ChildRunbookFlattener` inlines child artifacts with unique namespaces
- Aliases map parent artifact names to namespaced child artifacts
- Security constraints on path resolution (no absolute paths, no `..`)

See [Child Runbook Composition](artifact-centric-orchestration/child-runbooks-design.md) for details.

### Export Infrastructure

- `Exporter` protocol for regulation-specific output formats
- `ExporterRegistry` for exporter discovery
- Auto-detection based on analyser compliance frameworks
- `JsonExporter` as default generic exporter
- CLI: `wct run --exporter`, `wct ls-exporters`

## Design Decisions

1. **Component Discovery** - The `ComponentRegistry` centralises component discovery via entry points. Both Planner and Executor share the same registry instance.

2. **Schema Handling** - Schemas are inferred from component declarations by default, with optional explicit `output_schema` overrides for extensibility.

3. **Artifact Metadata** - Per-artifact metadata (`name`, `description`, `contact`) is preserved as these are business requirements for compliance audit trails.

4. **Multi-Schema Fan-In** - Analysers declare supported input combinations via `InputRequirement`. The Planner validates provided inputs match exactly one declared combination.

5. **Plan-Time Flattening** - Child runbooks are flattened into the parent at plan time, producing a single unified DAG. The Executor has no composition awareness—it simply executes the flattened plan.

6. **Namespace Isolation** - Child artifacts receive unique namespaces (`{runbook_name}__{uuid}__{artifact_id}`) to prevent collisions when the same child runbook is used multiple times.

7. **Executor Location** - DAGExecutor lives in `waivern-orchestration` alongside Planner, keeping all orchestration logic in one package. WCT imports and wires these components together.

## Related Documentation

- [Child Runbook Composition](artifact-centric-orchestration/child-runbooks-design.md) - Detailed design for modular runbook composition
- [Child Runbook User Guide](../../libs/waivern-orchestration/docs/child-runbook-composition.md) - How to use child runbooks
