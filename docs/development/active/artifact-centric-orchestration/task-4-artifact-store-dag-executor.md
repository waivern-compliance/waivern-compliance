# Task 4: Update ArtifactStore and Implement DAGExecutor

- **Phase:** 2 - Execution
- **Status:** TODO
- **Prerequisites:** Task 3 (planner)
- **GitHub Issue:** #245 (close via PR)
- **Design:** [artifact-centric-orchestration-design.md](../artifact-centric-orchestration-design.md)

## Context

Tasks 1-3 established the planning infrastructure. This task implements the execution layer: updating ArtifactStore with observability support and creating the DAGExecutor for parallel artifact production.

## Purpose

1. Add `list_artifacts()` to ArtifactStore for observability
2. Implement DAGExecutor that executes artifacts in parallel using asyncio with ThreadPoolExecutor for sync component bridging

## Problem

The current executor is sequential, processing steps one at a time. The DAGExecutor enables parallel execution of independent artifacts while respecting dependencies, significantly improving performance for multi-branch pipelines.

## Decisions Made

1. **asyncio + ThreadPoolExecutor** - Async orchestration with sync→async bridge for existing sync components
2. **Semaphore-based concurrency** - Limit parallel artifacts via `max_concurrency` from RunbookConfig
3. **Skip dependents on failure** - When artifact fails, skip all downstream artifacts
4. **Timeout enforcement** - Use `asyncio.timeout()` for RunbookConfig.timeout
5. **ComponentRegistry** - Centralised component discovery in waivern-core, shared between Planner and Executor (implemented in this task)

## Implementation

### Files Modified/Created

```
libs/waivern-artifact-store/src/waivern_artifact_store/
├── base.py                    # MODIFIED: added list_artifacts() abstract method
└── in_memory.py               # MODIFIED: implemented list_artifacts()

libs/waivern-core/src/waivern_core/services/
└── registry.py                # NEW: ComponentRegistry for centralised discovery

libs/waivern-orchestration/src/waivern_orchestration/
├── __init__.py                # MODIFIED: export DAGExecutor
├── executor.py                # NEW: DAGExecutor class
└── planner.py                 # MODIFIED: use ComponentRegistry

libs/waivern-orchestration/tests/waivern_orchestration/
├── conftest.py                # NEW: shared test helpers
└── test_executor.py           # NEW: DAGExecutor tests
```

### Changes Required

#### 1. Update ArtifactStore interface

**File:** `libs/waivern-artifact-store/src/waivern_artifact_store/base.py`

Add abstract method:
```python
@abstractmethod
def list_artifacts(self) -> list[str]:
    """Return list of all stored artifact IDs."""
    ...
```

Update InMemoryArtifactStore implementation:
```python
def list_artifacts(self) -> list[str]:
    return list(self._artifacts.keys())
```

#### 2. Implement DAGExecutor

**File:** `libs/waivern-orchestration/src/waivern_orchestration/executor.py`

**Class structure:**
```
DAGExecutor
  __init__(registry: ComponentRegistry)
    - Store registry for component factory access

  async execute(plan: ExecutionPlan) -> ExecutionResult
    - Main entry point
    - Create semaphore and thread pool from config
    - Run execution loop with TopologicalSorter
    - Handle timeout from config
    - Return ExecutionResult

  async _produce(artifact_id, plan, store, semaphore, thread_pool) -> ArtifactResult
    - Produce single artifact
    - Acquire semaphore for concurrency control
    - Route to connector, analyser, or child runbook
    - Save to store on success
    - Return ArtifactResult

  async _run_connector(source, thread_pool) -> Message
    - Run sync connector in thread pool
    - Bridge sync → async

  async _run_analyser(transform, input_message, thread_pool) -> Message
    - Run sync analyser in thread pool
    - Bridge sync → async

  _gather_inputs(from_artifacts, store) -> list[Message]
    - Retrieve input messages from store
    - Handle single or list of artifact IDs

  _merge(inputs) -> Message
    - Merge multiple inputs using concatenate strategy
    - Combine content lists from all inputs

  _skip_dependents(artifact_id, dag, skipped) -> None
    - Mark all downstream artifacts as skipped
    - Use dag.get_dependents() for lookup
```

**Execution loop (pseudo-code):**
```
async function execute(plan):
    config = plan.runbook.config
    semaphore = Semaphore(config.max_concurrency)
    thread_pool = ThreadPoolExecutor(max_workers=config.max_concurrency)

    store = container.get_service(ArtifactStore)
    store.clear()

    sorter = plan.dag.get_sorter()
    results = {}
    skipped = set()

    try:
        async with asyncio.timeout(config.timeout):
            while sorter.is_active():
                ready = [aid for aid in sorter.get_ready() if aid not in skipped]

                # Execute ready artifacts in parallel
                tasks = [produce(aid, ...) for aid in ready]
                batch_results = await gather(*tasks, return_exceptions=True)

                for aid, result in zip(ready, batch_results):
                    results[aid] = result
                    sorter.done(aid)

                    if is_failure(result):
                        skip_dependents(aid, plan.dag, skipped)

    except TimeoutError:
        # Mark remaining as skipped due to timeout
        ...
    finally:
        thread_pool.shutdown(wait=False)

    return ExecutionResult(artifacts=results, skipped=skipped)
```

**Sync→async bridge (pseudo-code):**
```
async function run_connector(source, thread_pool):
    loop = get_event_loop()

    def sync_extract():
        factory = get_connector_factory(source.type)
        connector = factory.create(source.properties)
        return connector.extract()

    return await loop.run_in_executor(thread_pool, sync_extract)
```

#### 3. Component instantiation

The executor needs to instantiate connectors and analysers from the plan.

**Chosen approach: ComponentRegistry**

Created `ComponentRegistry` in waivern-core that centralises component discovery:
- Single source of truth for connector/analyser factories
- Lazy discovery from entry points on first access
- Shared between Planner and Executor (no duplicate discovery)
- Lives in `libs/waivern-core/src/waivern_core/services/registry.py`

```python
class ComponentRegistry:
    def __init__(self, container: ServiceContainer) -> None

    @property
    def container(self) -> ServiceContainer

    @property
    def connector_factories(self) -> Mapping[str, ComponentFactory[Connector]]

    @property
    def analyser_factories(self) -> Mapping[str, ComponentFactory[Analyser]]
```

Both Planner and DAGExecutor accept `ComponentRegistry` in their constructors.

#### 4. Error handling

**Artifact failure:**
- Catch exceptions in `_produce()`
- Create ArtifactResult with `success=False` and error message
- Call `_skip_dependents()` to mark downstream as skipped

**Optional artifacts:**
- Check `artifact.optional` flag
- If True: log warning, skip dependents, continue pipeline
- If False: same as above (pipeline continues with independent branches)

**Timeout:**
- Use `async with asyncio.timeout(config.timeout)`
- On TimeoutError: mark remaining artifacts as skipped
- Return partial results

## Testing

### Test Scenarios

#### 1. Parallel execution verification ✅
- Create runbook with 2 independent source artifacts
- Mock connectors with sleep to simulate work
- Execute and verify total time < sum of individual times
- Verifies parallelism is working
- **Test:** `test_execute_parallel_independent_artifacts`

#### 2. Sequential dependencies ✅
- Create A → B → C chain
- Verify execution order: A completes before B starts, B before C
- Use timing or order tracking
- **Test:** `test_execute_chain_respects_dependency_order`

#### 3. Fan-in execution ⚠️ (partial)
- Create A, B → C (C depends on both)
- Verify C only starts after both A and B complete
- Verify C receives merged input
- **Test:** `test_execute_fan_in_sources_succeed_merge_not_implemented` (documents that merge raises NotImplementedError)

#### 4. Merge strategy (concatenate) ⏭️
- Test fan-in with multiple inputs
- Verify content from all inputs is combined
- **Deferred to Phase 2**

#### 5. Error propagation and dependent skipping ✅
- Create A → B → C
- Make A fail
- Verify B and C are skipped
- Verify error message in result
- **Test:** `test_failed_artifact_skips_dependents`

#### 6. Optional artifact ✅
- Create A (optional) → B
- Make A fail
- Verify B is skipped but no error raised
- Verify warning logged
- **Test:** `test_optional_artifact_failure_logs_warning`

#### 7. Timeout enforcement ✅
- Set short timeout (1 second)
- Create slow artifacts (2 second connectors)
- Verify TimeoutError handled gracefully
- Verify partial results returned
- **Test:** `test_timeout_marks_remaining_as_skipped`

#### 8. Concurrency limit ✅
- Set max_concurrency = 2
- Create 5 parallel artifacts
- Verify at most 2 run simultaneously
- **Test:** `test_concurrency_limit_respected`

#### 9. list_artifacts observability ✅
- Execute runbook
- Call store.list_artifacts()
- Verify all produced artifacts listed
- **Test:** `test_list_artifacts_after_execution`

#### 10. Transform/analyser execution ✅
- Create source → analyser chain
- Verify analyser receives input message and schemas
- Verify analyser output stored correctly
- **Test:** `test_execute_derived_with_transform`

#### 11. Analyser not found error ✅
- Reference non-existent analyser type
- Verify clear error message returned
- **Test:** `test_analyser_not_found_returns_error`

### Additional Tests Implemented

- `test_execute_single_source_artifact` - Happy path for single source artifact
- `test_connector_not_found_returns_error` - Error handling for missing connector
- `test_execution_result_contains_duration` - Total duration tracking
- `test_artifact_result_contains_duration` - Per-artifact duration tracking

### Validation Commands

```bash
# Run orchestration tests (includes DAGExecutor)
uv run pytest libs/waivern-orchestration/tests/ -v

# Run DAG executor tests specifically
uv run pytest libs/waivern-orchestration/tests/waivern_orchestration/test_executor.py -v

# Run ArtifactStore tests
uv run pytest libs/waivern-artifact-store/tests/ -v

# Run full dev-checks
./scripts/dev-checks.sh
```

## Implementation Notes

- DAGExecutor lives in `waivern-orchestration` alongside Planner, ExecutionPlan, and ExecutionDAG
- Update `waivern_orchestration/__init__.py` to export `DAGExecutor`
- Use `asyncio.get_running_loop()` instead of deprecated `get_event_loop()`
- ThreadPoolExecutor context manager ensures cleanup
- Consider using `asyncio.TaskGroup` (Python 3.11+) for cleaner task management
- Semaphore must be created inside async context, not in `__init__`
- Merge uses concatenate strategy only (per ADR-0003); schema compatibility already validated by planner

## Completion Status

### Implemented

1. **ArtifactStore `list_artifacts()`** - Added to base class and InMemoryArtifactStore
2. **ComponentRegistry** - Centralised component discovery in waivern-core
3. **DAGExecutor core** - Parallel execution with TopologicalSorter
4. **Concurrency control** - Semaphore-based limiting via `max_concurrency`
5. **Error handling** - Dependent skipping, optional artifact support
6. **Timeout enforcement** - `asyncio.timeout()` with remaining artifacts marked as skipped
7. **Transform/analyser execution** - `_run_analyser()` method with sync→async bridge

### Deferred

- **Fan-in merge** - Deferred to [Phase 2](phase-2-transformers-design.md)
- **Child runbook execution** - Deferred to [Phase 3](phase-3-child-runbooks-design.md)
