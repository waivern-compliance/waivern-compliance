# Lightweight DAG Orchestration Layer for WCT

- **Status:** Design Proposal
- **Last Updated:** 2025-11-26
- **Related:** [Artifact-Centric Runbook](./artifact-centric-runbook.md), [Business-Logic-Centric Analysers](./business-logic-centric-analysers.md)

## Overview

Design for a lightweight DAG orchestration layer using Python's stdlib `graphlib.TopologicalSorter` with asyncio-native parallel execution. The layer focuses purely on step sequencing and parallel execution - complex behaviours (HTTP, polling, retries) remain at the analyser/service layer.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| DAG Library | `graphlib.TopologicalSorter` | Stdlib, zero deps, designed for parallel execution |
| Parallelism | Always parallel | Independent steps run concurrently by default |
| Fan-in | Supported | `input_from` accepts list of step IDs |
| Error Handling | Minimal | `continue_on_error` per step, skip dependents on failure |
| Execution Model | asyncio + ThreadPool | Async orchestration, sync analysers via thread pool |

## Architecture

### Separation of Concerns

The orchestration layer is split into **Planner** (builds execution plan) and **Executor** (runs the plan):

```
┌─────────────────────────────────────────────────────────┐
│              waivern-orchestration (package)            │
│                                                         │
│  Planner                                                │
│    ├── Parse runbook                                    │
│    ├── Build artifact dependency graph (DAG)            │
│    ├── Validate (cycles, missing refs, schema compat)   │
│    └── Produce immutable ExecutionPlan                  │
│                                                         │
│  Dependencies: waivern-core only                        │
└─────────────────────────────────────────────────────────┘
                          │
                          │ ExecutionPlan
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Executor (in wct or other apps)            │
│                                                         │
│    ├── Execute plan (parallel, respecting deps)         │
│    ├── Manage ArtifactStore                             │
│    ├── Handle errors (skip dependents)                  │
│    ├── Spawn child executors (recursive runbooks)       │
│    └── Track progress, costs, timing                    │
└─────────────────────────────────────────────────────────┘
```

### Interface Contract

```python
# waivern-orchestration package

class ExecutionPlan:
    """Immutable, validated execution plan."""
    dag: ExecutionDAG
    artifacts: dict[str, ArtifactDef]

class Planner:
    """Builds execution plans from runbooks."""
    def plan(self, runbook_path: Path) -> ExecutionPlan: ...
    def plan_from_dict(self, runbook: dict) -> ExecutionPlan: ...

# Executor protocol (implemented by apps)

class Executor(Protocol):
    """Any executor must implement this."""
    def execute(self, plan: ExecutionPlan) -> ExecutionResult: ...
```

### Benefits of Separation

| Concern | Planner | Executor |
|---------|---------|----------|
| Validation | All upfront | None needed |
| DAG building | Yes | Just follows plan |
| Testability | Test graph logic | Test execution logic |
| Reuse | Visualization, dry-run, validation | Different runtimes |

### Schema Validation at Plan Time

The Planner validates schema compatibility **before execution** using the component registry:

```python
class Planner:
    def __init__(self, registry: ComponentRegistry):
        self._registry = registry

    def plan(self, runbook_path: Path) -> ExecutionPlan:
        runbook = self._parse(runbook_path)
        dag = self._build_dag(runbook.artifacts)
        self._validate_dag(dag)
        self._validate_schemas(runbook.artifacts)
        return ExecutionPlan(dag=dag, artifacts=runbook.artifacts)

    def _validate_schemas(self, artifacts: dict[str, ArtifactDef]) -> None:
        for artifact_id, defn in artifacts.items():
            if defn.source:
                # Validate connector outputs schema
                connector = self._registry.get_connector(defn.source.type)
                output_schema = connector.get_output_schema()
            if defn.transform:
                # Validate analyser input/output compatibility
                analyser = self._registry.get_analyser(defn.transform.type)
                input_schema = analyser.get_input_schema()
                # Validate upstream produces compatible schema
                ...
```

**Validation Responsibilities:**

| Validation | Stage | Description |
|------------|-------|-------------|
| YAML parsing | Plan | Runbook syntax and structure |
| Cycle detection | Plan | No circular dependencies |
| Missing refs | Plan | All `from` references exist |
| Schema compatibility | Plan | Upstream output matches downstream input |
| Component existence | Plan | All connectors/analysers registered |
| Runtime errors | Execute | Connection failures, data issues |

### Executor Variants

- **LocalExecutor** - Current WCT implementation
- **DryRunExecutor** - Validation only, no execution
- **DebugExecutor** - Step-through with breakpoints
- **DistributedExecutor** - Future, for scale-out

## Core Components

### ExecutionDAG

```python
from graphlib import TopologicalSorter

@dataclass
class StepNode:
    step_id: str
    step: ExecutionStep
    dependencies: set[str]
    continue_on_error: bool = False

class ExecutionDAG:
    def __init__(self, steps: list[ExecutionStep]) -> None:
        self._nodes: dict[str, StepNode] = {}
        self._build_graph(steps)

    def _extract_dependencies(self, input_from: str | list[str] | None) -> set[str]:
        if input_from is None:
            return set()
        if isinstance(input_from, str):
            return {input_from}
        return set(input_from)  # Fan-in support

    def validate(self) -> None:
        graph = {n.step_id: n.dependencies for n in self._nodes.values()}
        ts = TopologicalSorter(graph)
        ts.prepare()  # Raises CycleError if cycles

    def get_sorter(self) -> TopologicalSorter[str]:
        graph = {n.step_id: n.dependencies for n in self._nodes.values()}
        ts = TopologicalSorter(graph)
        ts.prepare()
        return ts
```

### DAGExecutor

```python
class DAGExecutor:
    def __init__(self, dag: ExecutionDAG, max_concurrency: int = 10) -> None:
        self._dag = dag
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._thread_pool = ThreadPoolExecutor(max_workers=max_concurrency)

    async def execute(self, context: ExecutionContext, step_fn) -> list[StepResult]:
        results: list[StepResult] = []
        sorter = self._dag.get_sorter()

        while sorter.is_active():
            ready_ids = sorter.get_ready()
            executable = [sid for sid in ready_ids if sid not in context.skipped_steps]

            # Execute ready steps in parallel
            tasks = [self._execute_step(sid, context, step_fn) for sid in executable]
            step_results = await asyncio.gather(*tasks)

            for result in step_results:
                results.append(result)
                sorter.done(result.step_id)
                if not result.success:
                    self._handle_failure(result, context)

        return results

    def _handle_failure(self, result: StepResult, context: ExecutionContext) -> None:
        node = self._dag.get_node(result.step_id)
        context.failed_steps.add(result.step_id)
        if not node.continue_on_error:
            self._skip_dependents(result.step_id, context)
```

## Schema Changes

### ExecutionStep Extension

```python
class ExecutionStep(BaseModel):
    # CHANGED: Support list for fan-in
    input_from: str | list[str] | None = Field(
        default=None,
        description="Step ID(s) to read input from. List for fan-in."
    )

    # NEW: Merge strategy for fan-in
    merge_strategy: Literal["concatenate", "first"] = Field(
        default="concatenate",
        description="How to merge multiple inputs"
    )

    # Existing context field - used for continue_on_error
    context: dict[str, Any] = Field(default_factory=dict)
```

## Usage Examples

### Fan-in Pattern

```yaml
execution:
  - id: "extract_mysql"
    connector: "mysql_db"
    analyser: "personal_data_analyser"
    output_schema: "personal_data_finding"
    save_output: true

  - id: "extract_files"
    connector: "log_files"
    analyser: "personal_data_analyser"
    output_schema: "personal_data_finding"
    save_output: true

  - id: "merge_findings"
    input_from:
      - "extract_mysql"
      - "extract_files"
    merge_strategy: "concatenate"
    analyser: "findings_aggregator"
    output_schema: "personal_data_finding"
```

### Error Handling

```yaml
execution:
  - id: "optional_llm_step"
    connector: "my_connector"
    analyser: "llm_analyser"
    save_output: true
    context:
      continue_on_error: true  # Continue even if this fails

  - id: "dependent_step"
    input_from: "optional_llm_step"
    analyser: "processor"
    # Skipped if optional_llm_step fails (unless continue_on_error: true)
```

## Observability

### Must Have (v1)

**Step-by-step logging:**
```
[INFO] Starting artifact: db_schema
[INFO] Completed artifact: db_schema (1.2s)
[INFO] Starting artifacts: db_findings, log_findings (parallel)
[INFO] Completed artifact: db_findings (3.4s)
[ERROR] Failed artifact: log_findings - ConnectionError
[WARN] Skipping artifact: combined_findings (dependency failed)
```

**Artifact inspection:**
- `wct inspect <runbook> <artifact_id>` - View artifact contents after execution
- Artifacts stored with metadata (schema, timing, status)
- Failed artifacts include error context

### Nice to Have (Future)

**DAG visualisation:**
- `wct visualize <runbook>` - Generate DOT/Mermaid graph
- Shows artifact dependencies and execution order
- Colour-coded by status (pending, running, completed, failed, skipped)

**Execution timeline:**
- Wall-clock timing per artifact
- Parallel execution visibility
- Critical path identification

## What NOT to Implement

1. **No workflow persistence** - Steps run in-memory only (future: pluggable store)
2. **No distributed execution** - Single process, multi-threaded
3. **No retry logic** - Retries belong at service/analyser layer
4. **No complex error handlers** - Just skip dependents on failure
5. **No observability infrastructure** - Standard logging is sufficient for v1

## Related Documents

- [Artifact-Centric Runbook](./artifact-centric-runbook.md) - Runbook format design
- [Business-Logic-Centric Analysers](./business-logic-centric-analysers.md) - Service injection pattern
- [Dynamic and Agentic Workflows](./dynamic-and-agentic-workflows.md) - Future evolution
- [Remote Analyser Protocol](./remote-analyser-protocol.md) - Async remote services
