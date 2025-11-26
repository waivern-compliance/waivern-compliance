# Task 4: Update ArtifactStore and Implement DAGExecutor

- **Phase:** 2 - Execution
- **Status:** TODO
- **Prerequisites:** Task 3 (planner)
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

## Implementation

### Files to Modify/Create

```
libs/waivern-artifact-store/src/waivern_artifact_store/
└── base.py                    # MODIFY: add list_artifacts()

apps/wct/src/wct/
└── dag_executor.py            # NEW: DAGExecutor class
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

**File:** `apps/wct/src/wct/dag_executor.py`

**Class structure:**
```
DAGExecutor
  __init__(container: ServiceContainer)
    - Store container for service access
    - Get connector/analyser factories from container or entry points

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

  _merge(inputs, strategy) -> Message
    - Merge multiple inputs based on strategy
    - "concatenate": combine content lists
    - "first": take first input only

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

The executor needs to instantiate connectors and analysers from the plan. Two approaches:

**Option A: Re-discover entry points**
- Load entry points in executor (duplicates planner work)
- Simpler, self-contained

**Option B: Pass factories from planner**
- Planner passes discovered factories to executor
- More efficient, no duplicate discovery

Recommend Option A for simplicity - entry point loading is fast.

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

#### 1. Parallel execution verification
- Create runbook with 2 independent source artifacts
- Mock connectors with sleep to simulate work
- Execute and verify total time < sum of individual times
- Verifies parallelism is working

#### 2. Sequential dependencies
- Create A → B → C chain
- Verify execution order: A completes before B starts, B before C
- Use timing or order tracking

#### 3. Fan-in execution
- Create A, B → C (C depends on both)
- Verify C only starts after both A and B complete
- Verify C receives merged input

#### 4. Merge strategies
- Test "concatenate": verify content combined
- Test "first": verify only first input used

#### 5. Error propagation and dependent skipping
- Create A → B → C
- Make A fail
- Verify B and C are skipped
- Verify error message in result

#### 6. Optional artifact
- Create A (optional) → B
- Make A fail
- Verify B is skipped but no error raised
- Verify warning logged

#### 7. Timeout enforcement
- Set short timeout (e.g., 1 second)
- Create slow artifacts
- Verify TimeoutError handled gracefully
- Verify partial results returned

#### 8. Concurrency limit
- Set max_concurrency = 2
- Create 5 parallel artifacts
- Verify at most 2 run simultaneously

#### 9. list_artifacts observability
- Execute runbook
- Call store.list_artifacts()
- Verify all produced artifacts listed

### Validation Commands

```bash
# Run WCT tests
uv run pytest apps/wct/tests/ -v

# Run DAG executor tests specifically
uv run pytest apps/wct/tests/test_dag_executor.py -v

# Run ArtifactStore tests
uv run pytest libs/waivern-artifact-store/tests/ -v

# Run full dev-checks
./scripts/dev-checks.sh
```

## Implementation Notes

- Use `asyncio.get_running_loop()` instead of deprecated `get_event_loop()`
- ThreadPoolExecutor context manager ensures cleanup
- Consider using `asyncio.TaskGroup` (Python 3.11+) for cleaner task management
- Semaphore must be created inside async context, not in `__init__`
- For merge, handle schema compatibility (already validated by planner)
