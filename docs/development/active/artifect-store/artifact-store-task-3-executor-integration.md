# Task: Integrate ArtifactStore with Executor

- **Phase:** ArtifactStore Service - Executor Integration
- **Status:** COMPLETED
- **Prerequisites:** Task 1 (Core service), Task 2 (ServiceContainer integration)
- **Related Issue:** #227

## Context

Replaces Executor's local dictionary-based artifact storage with ArtifactStore service. This completes the service integration and enables future unified connector architecture. Prerequisites provide the service implementation and DI integration.

## Purpose

Migrate Executor from inline artifact storage to service-based storage whilst maintaining existing behaviour and API compatibility.

## Problem

The Executor currently manages artifacts using a local dictionary:
- Line ~265: `artifacts = {}` - Local dict creation
- Line ~306: `artifacts[step.id] = output_message` - Save operation
- Line ~347-351: Retrieval logic with error handling

This creates tight coupling and prevents future extensibility (distributed storage, persistence).

## Proposed Solution

Inject ArtifactStore via ServiceContainer and replace dict operations with service calls. Maintain exact same behaviour and error messages for backward compatibility.

## Decisions Made

1. **Injection point** - ServiceContainer passed to Executor.__init__
2. **Storage access** - Use `self.artifact_store` throughout execution methods
3. **Lifecycle** - Call `clear()` at execution start and end
4. **Error handling** - Let ArtifactNotFoundError propagate (matches current error semantics)
5. **Backward compatibility** - No changes to runbook format or public API

## Expected Outcome & Usage Example

**No visible changes to runbook execution:**
```yaml
execution:
  - id: "extract"
    connector: mysql_connector
    analyser: personal_data_analyser
    save_output: true

  - id: "classify"
    input_from: "extract"  # Still works identically
    analyser: data_subject_analyser
```

**Internal implementation changes only.**

## Implementation

### Changes Required

#### 1. Add Imports

**Location:** `apps/wct/src/wct/executor.py` - Top of file

**Add:**
```python
from waivern_artifact_store import (
    ArtifactStore,
    ArtifactStoreFactory,
    ArtifactNotFoundError,
)
```

#### 2. Update Executor Initialisation

**Location:** `apps/wct/src/wct/executor.py` - `__init__` method (line ~48)

**Changes:**
- ServiceContainer already injected via parameter
- Register ArtifactStoreFactory with container
- Get artifact store singleton from container

**Implementation:**
```python
def __init__(self, container: ServiceContainer) -> None:
    self._container = container

    # Register artifact store factory
    self._container.register(
        ArtifactStore,
        ArtifactStoreFactory(),
        lifetime="singleton"
    )

    # Get artifact store instance
    self.artifact_store = self._container.get_service(ArtifactStore)

    # Existing code...
    self.connector_factories: dict[str, ComponentFactory[Connector]] = {}
    self.analyser_factories: dict[str, ComponentFactory[Analyser]] = {}
```

#### 3. Replace Artifact Dict with Service Calls

**Location:** `apps/wct/src/wct/executor.py` - `execute_runbook` method (line ~207)

**Changes:**
- Line ~210: Replace `artifacts: dict[str, Message] = {}` with `self.artifact_store.clear()`
- Line ~218: Replace `artifacts[step.id] = message` with `self.artifact_store.save(step.id, message)`
- Line ~347-353: Replace dict lookup with `self.artifact_store.get(step.input_from)`

**Note:** Line numbers are approximate and may shift during implementation.

**Save operation:**
```python
# OLD (line ~218):
if step.save_output:
    artifacts[step.id] = message

# NEW:
if step.save_output:
    self.artifact_store.save(step.id, message)
```

**Retrieve operation:**
```python
# OLD (line ~347-353):
if step.input_from not in artifacts:
    raise ExecutorError(
        f"Step '{step.name}' depends on '{step.input_from}' but artifact not found. "
        f"Ensure previous step has 'save_output: true'."
    )
input_message = artifacts[step.input_from]

# NEW:
try:
    input_message = self.artifact_store.get(step.input_from)
except ArtifactNotFoundError:
    raise ExecutorError(
        f"Step '{step.name}' depends on '{step.input_from}' but artifact not found. "
        f"Ensure previous step has 'save_output: true'."
    )
```

**Remove artifacts dict:**
```python
# OLD (line ~210):
results: list[AnalysisResult] = []
artifacts: dict[str, Message] = {}

# NEW (line ~210):
results: list[AnalysisResult] = []
self.artifact_store.clear()  # Start fresh
```

**Remove artifacts parameter:**
```python
# OLD (line ~213):
analysis_result, message = self._execute_step(step, runbook, artifacts)

# NEW:
analysis_result, message = self._execute_step(step, runbook)
```

**Update _execute_step signature:**
```python
# OLD (line ~301):
def _execute_step(
    self,
    step: ExecutionStep,
    runbook: Runbook,
    artifacts: dict[str, Message],
) -> tuple[AnalysisResult, Message]:

# NEW:
def _execute_step(
    self,
    step: ExecutionStep,
    runbook: Runbook,
) -> tuple[AnalysisResult, Message]:
```

#### 4. Cleanup Strategy

**Purpose:** Ensure clean state for each runbook execution

**Implementation:**
- Call `self.artifact_store.clear()` at start of `execute_runbook()` (line ~210)
- No finally block needed - singleton store is cleared per-execution
- Store lifetime tied to ServiceContainer (typically one per CLI invocation)

**Rationale:**
- Current code doesn't use try/finally for cleanup
- Clearing at start ensures clean state
- Singleton store persists across runbook executions in same container
- Each CLI invocation creates new container → natural cleanup boundary

## Testing

### Testing Strategy

Verify behavior unchanged through existing test suite. All existing Executor tests should pass without modification since this is an internal refactoring with no API changes.

### Test Scenarios

**All scenarios verified by existing tests:**

#### 1. All Existing Tests Pass

**Verify:**
- Run full WCT test suite: `uv run pytest apps/wct/tests/ -v`
- All ~350 existing tests should pass without modification
- Pipeline execution tests cover artifact save/retrieve behavior
- Error handling tests cover missing artifact scenarios

**Critical tests:**
- `test_executor.py` - Core executor behavior
- `test_executor_version_matching.py` - Schema matching with artifacts
- Integration tests with actual runbooks

### Validation Commands

```bash
# Run all WCT tests (should all pass without modification)
uv run pytest apps/wct/tests/ -v

# Run executor tests specifically
uv run pytest apps/wct/tests/test_executor.py -v
uv run pytest apps/wct/tests/test_executor_version_matching.py -v

# Run all quality checks
./scripts/dev-checks.sh
```

## Implementation Notes

**Key principles:**
- Internal refactoring only - no API changes
- Existing tests must pass without modification
- Error messages must match exactly
- Backward compatible with all existing runbooks

**Implementation order:**
1. Add imports
2. Update `__init__` to register and get ArtifactStore
3. Replace `artifacts = {}` with `self.artifact_store.clear()`
4. Remove `artifacts` parameter from `_execute_step()` signature
5. Update `_execute_step()` calls to remove artifacts argument
6. Replace `artifacts[step.id] = message` with `self.artifact_store.save()`
7. Replace dict lookup with `self.artifact_store.get()` and exception handling
8. Run tests after each change to verify behavior unchanged

## Issue Tracking

**Related Issue:** #227

**Upon completion:**
- **Close issue #227** - this is the final task (3 of 3)
- Update this task status to COMPLETED
- Commit with message: `feat: integrate artifact store with Executor

Closes #227`
