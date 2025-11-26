# Implementation Plan: Artifact-Centric Orchestration

- **Design:** [artifact-centric-orchestration-design.md](./artifact-centric-orchestration-design.md)
- **Epics:** #189, #190
- **Status:** Ready for Implementation
- **Last Updated:** 2025-11-26

## Overview

Implementation plan for Phase 1 of the artifact-centric orchestration system. This replaces the current step-based runbook format and sequential executor with an artifact-centric model and DAG-based parallel execution.

## Implementation Order

The implementation follows a bottom-up approach: models → infrastructure → planner → executor → CLI → migration.

```
1. waivern-orchestration package (new)
   ├── models.py        ← Start here
   ├── errors.py
   ├── parser.py
   ├── dag.py
   └── planner.py

2. waivern-artifact-store (update)
   └── base.py          ← Add list_artifacts()

3. apps/wct (update)
   ├── executor.py      ← DAGExecutor
   └── cli.py           ← wct inspect

4. Sample runbooks      ← Migration
```

## Tasks

### Task 1: Create `waivern-orchestration` Package

**Goal:** Set up the new package structure with proper configuration.

**Files to create:**
```
libs/waivern-orchestration/
├── pyproject.toml
├── scripts/
│   ├── lint.sh
│   ├── format.sh
│   └── type-check.sh
├── src/waivern_orchestration/
│   ├── __init__.py
│   └── py.typed
└── tests/
    └── __init__.py
```

**pyproject.toml dependencies:**
- `waivern-core` (for Schema, Message types)
- `pyyaml` (for YAML parsing)
- `pydantic` (for models)

**Update root pyproject.toml:**
- Add `waivern-orchestration = { workspace = true }` to `[tool.uv.sources]`

---

### Task 2: Implement Data Models

**Goal:** Create all Pydantic models for the artifact-centric runbook format.

**File:** `libs/waivern-orchestration/src/waivern_orchestration/models.py`

**Models to implement:**
```python
# Configuration models
class SourceConfig(BaseModel): ...
class TransformConfig(BaseModel): ...
class RunbookConfig(BaseModel): ...
class ExecuteConfig(BaseModel): ...

# Core models
class ArtifactDefinition(BaseModel): ...
class Runbook(BaseModel): ...

# Execution models
class ExecutionPlan: ...  # dataclass
class ArtifactResult: ...
class ExecutionResult: ...
```

**Validation logic:**
- `ArtifactDefinition.validate_source_xor_from()` - source XOR from (mutually exclusive)
- `ArtifactDefinition.validate_transform_requires_from()` - transform requires from (unless source has inline transform)

**Tests:** `tests/test_models.py`
- Valid artifact definitions (source, derived, fan-in)
- Invalid combinations (both source and from, neither source nor from)
- Runbook serialization/deserialization
- Config defaults

---

### Task 3: Implement Error Types

**Goal:** Define custom exceptions for orchestration errors.

**File:** `libs/waivern-orchestration/src/waivern_orchestration/errors.py`

**Exceptions:**
```python
class OrchestrationError(Exception): ...
class RunbookParseError(OrchestrationError): ...
class CycleDetectedError(OrchestrationError): ...
class MissingArtifactError(OrchestrationError): ...
class SchemaCompatibilityError(OrchestrationError): ...
class ComponentNotFoundError(OrchestrationError): ...
```

**Tests:** `tests/test_errors.py`
- Error messages include context (artifact ID, cycle path, etc.)

---

### Task 4: Implement YAML Parser

**Goal:** Parse YAML runbook files into Runbook models with environment variable substitution.

**File:** `libs/waivern-orchestration/src/waivern_orchestration/parser.py`

**Functions:**
```python
def parse_runbook(path: Path) -> Runbook: ...
def parse_runbook_from_dict(data: dict[str, Any]) -> Runbook: ...
def _substitute_env_vars(value: str) -> str: ...
```

**Features:**
- Environment variable substitution (`${VAR_NAME}`)
- Clear error messages with line numbers where possible
- Support for both file path and dict input

**Tests:** `tests/test_parser.py`
- Valid runbook parsing
- Environment variable substitution
- Missing required fields
- Invalid YAML syntax

---

### Task 5: Implement ExecutionDAG

**Goal:** Build and validate the dependency graph using `graphlib.TopologicalSorter`.

**File:** `libs/waivern-orchestration/src/waivern_orchestration/dag.py`

**Class:**
```python
class ExecutionDAG:
    def __init__(self, artifacts: dict[str, ArtifactDefinition]) -> None: ...
    def validate(self) -> None: ...  # Raises CycleDetectedError
    def get_sorter(self) -> TopologicalSorter[str]: ...
    def get_dependents(self, artifact_id: str) -> set[str]: ...
    def get_dependencies(self, artifact_id: str) -> set[str]: ...
```

**Tests:** `tests/test_dag.py`
- Linear dependency chain
- Parallel independent artifacts
- Fan-in (multiple inputs)
- Fan-out (multiple dependents)
- Cycle detection
- Missing reference detection

---

### Task 6: Implement Planner

**Goal:** Orchestrate parsing, DAG building, validation, and schema resolution.

**File:** `libs/waivern-orchestration/src/waivern_orchestration/planner.py`

**Class:**
```python
class Planner:
    def __init__(self) -> None: ...  # Discovers components via entry points
    def plan(self, runbook_path: Path) -> ExecutionPlan: ...
    def plan_from_dict(self, runbook: dict[str, Any]) -> ExecutionPlan: ...
```

**Internal methods:**
```python
def _load_entry_points(self, group: str) -> dict[str, ComponentFactory]: ...
def _validate_refs(self, runbook: Runbook) -> None: ...
def _resolve_schemas(self, runbook: Runbook) -> dict[str, tuple[Schema, Schema]]: ...
def _validate_schema_compatibility(self, output: Schema, input: Schema) -> None: ...
```

**Tests:** `tests/test_planner.py`
- End-to-end planning with mock components
- Component not found error
- Schema incompatibility error
- Explicit schema override

---

### Task 7: Update ArtifactStore Interface

**Goal:** Add `list_artifacts()` method to the ArtifactStore ABC.

**File:** `libs/waivern-artifact-store/src/waivern_artifact_store/base.py`

**Changes:**
```python
class ArtifactStore(ABC):
    # ... existing methods ...

    @abstractmethod
    def list_artifacts(self) -> list[str]: ...
```

**Update implementations:**
- `InMemoryArtifactStore` in the same package

**Tests:** Update existing tests to cover `list_artifacts()`

---

### Task 8: Implement DAGExecutor

**Goal:** Replace the current sequential executor with async DAG-based execution.

**File:** `apps/wct/src/wct/executor.py`

**Approach:** Create new `DAGExecutor` class alongside existing `Executor` class, then swap.

**Class:**
```python
class DAGExecutor:
    def __init__(self, container: ServiceContainer) -> None: ...

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult: ...

    async def _produce(
        self,
        artifact_id: str,
        plan: ExecutionPlan,
        store: ArtifactStore,
        semaphore: asyncio.Semaphore,
        thread_pool: ThreadPoolExecutor,
    ) -> ArtifactResult: ...

    async def _run_connector(self, source: SourceConfig, ...) -> Message: ...
    async def _run_analyser(self, transform: TransformConfig, input: Message, ...) -> Message: ...

    def _gather_inputs(self, from_artifacts: str | list[str], store: ArtifactStore) -> list[Message]: ...
    def _merge(self, inputs: list[Message], strategy: str) -> Message: ...
    def _skip_dependents(self, artifact_id: str, dag: ExecutionDAG, skipped: set[str]) -> None: ...
```

**Features:**
- Parallel execution via `asyncio.gather()`
- Sync→async bridge via `ThreadPoolExecutor`
- Semaphore for concurrency control
- Skip dependents on failure
- Timeout enforcement (from RunbookConfig)

**Tests:** `apps/wct/tests/test_dag_executor.py`
- Parallel execution (verify timing)
- Sequential dependencies
- Fan-in merging
- Error handling and dependent skipping
- Timeout enforcement

---

### Task 9: Update CLI

**Goal:** Add `wct inspect` command and update `wct run` to use new executor.

**File:** `apps/wct/src/wct/cli.py`

**New command:**
```bash
wct inspect <runbook.yaml> <artifact_id>
```

**Changes to `wct run`:**
- Use `Planner` to create `ExecutionPlan`
- Use `DAGExecutor` to execute plan
- Update output format to show parallel execution info

**Tests:** `apps/wct/tests/test_cli.py`
- `wct inspect` with valid artifact
- `wct inspect` with missing artifact
- `wct run` with new format runbook

---

### Task 10: Migrate Sample Runbooks

**Goal:** Update all sample runbooks to the new artifact-centric format.

**Files:**
- `apps/wct/runbooks/samples/file_content_analysis.yaml`
- `apps/wct/runbooks/samples/LAMP_stack.yaml`
- Any other sample runbooks

**Migration pattern:**
```yaml
# Before
connectors:
  - name: "x"
    type: "y"
analysers:
  - name: "a"
    type: "b"
execution:
  - connector: "x"
    analyser: "a"

# After
artifacts:
  data:
    source:
      type: "y"
  findings:
    inputs: data
    transform:
      type: "b"
    output: true
```

---

### Task 11: Update Documentation

**Goal:** Update user-facing documentation for the new runbook format.

**Files:**
- `apps/wct/runbooks/README.md` - Update runbook format documentation
- `docs/development/extending-wcf.md` - Remove legacy format note (already has it)
- `CLAUDE.md` - Update runbook format section

---

### Task 12: Clean Up Old Code

**Goal:** Remove the old executor and runbook code after migration is complete.

**Files to remove/update:**
- `apps/wct/src/wct/runbook.py` - Replace with imports from waivern-orchestration
- `apps/wct/src/wct/executor.py` - Remove old `Executor` class

**Note:** Do this last, after all tests pass with the new implementation.

---

## Testing Strategy

### Unit Tests
- Models validation
- Parser edge cases
- DAG building and cycle detection
- Schema resolution

### Integration Tests
- End-to-end runbook execution with mock components
- Parallel execution verification
- Error propagation

### Manual Testing
- Run migrated sample runbooks
- Verify output matches previous behaviour

---

## Suggested PR Breakdown

| PR | Tasks | Description |
|----|-------|-------------|
| 1 | 1-3 | New package + models + errors |
| 2 | 4-5 | Parser + DAG |
| 3 | 6 | Planner |
| 4 | 7-8 | ArtifactStore + DAGExecutor |
| 5 | 9-10 | CLI + runbook migration |
| 6 | 11-12 | Docs + cleanup |

Each PR is independently testable and can be reviewed separately.

---

## Dependencies

```
PR1 (models) ──┬── PR2 (parser, DAG)
               │
               └── PR3 (planner) ──── PR4 (executor) ──── PR5 (CLI) ──── PR6 (cleanup)
                                           │
                        PR7 (ArtifactStore)┘
```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Entry point discovery complexity | Test with mock entry points first |
| Async execution edge cases | Comprehensive timeout and error handling tests |
| Schema compatibility validation | Reuse existing schema validation logic from current executor |
| Breaking existing runbooks | Run both old and new formats in parallel during transition |

## Success Criteria

1. All existing sample runbooks work with new format
2. Parallel execution demonstrable (timing improvement)
3. `wct inspect` works for any artifact
4. All dev-checks pass
5. No regression in existing functionality
