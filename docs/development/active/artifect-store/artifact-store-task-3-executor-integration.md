# Task: Integrate ArtifactStore with Executor

- **Phase:** ArtifactStore Service - Executor Integration
- **Status:** TODO
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

#### 1. Update Executor Initialisation

**Location:** `apps/wct/src/wct/executor.py` - `__init__` method

**Changes:**
- Accept ServiceContainer as parameter (if not already)
- Store reference to artifact store: `self.artifact_store = service_container.get_artifact_store()`

**Pseudo-code:**
```python
def __init__(service_container: ServiceContainer, ...):
    self.service_container = service_container
    self.artifact_store = service_container.get_artifact_store()
    # ... rest of init
```

#### 2. Replace Artifact Dict with Service Calls

**Location:** `apps/wct/src/wct/executor.py` - `execute_runbook` method

**Changes:**
- Line ~265: Replace `artifacts = {}` with `self.artifact_store.clear()`
- Line ~306: Replace `artifacts[step.id] = output_message` with `self.artifact_store.save(step.id, output_message)`
- Line ~347-351: Replace dict lookup with `self.artifact_store.get(step.input_from)`
- Add cleanup: `self.artifact_store.clear()` in finally block or at end

**Save operation (pseudo-code):**
```python
# OLD:
if step.save_output and output_message is not None:
    artifacts[step.id] = output_message

# NEW:
if step.save_output and output_message is not None:
    self.artifact_store.save(step.id, output_message)
```

**Retrieve operation (pseudo-code):**
```python
# OLD:
if step.input_from not in artifacts:
    raise ExecutorError(f"Step '{step.name}' depends on '{step.input_from}' ...")
input_message = artifacts[step.input_from]

# NEW:
try:
    input_message = self.artifact_store.get(step.input_from)
except ArtifactNotFoundError:
    raise ExecutorError(f"Step '{step.name}' depends on '{step.input_from}' ...")
```

#### 3. Add Cleanup Logic

**Purpose:** Ensure artifacts are cleared after execution completes or fails

**Changes:**
- Call `self.artifact_store.clear()` at start of execute_runbook
- Call `self.artifact_store.clear()` in finally block (cleanup on error)

**Pseudo-code:**
```python
def execute_runbook(runbook_path):
    try:
        self.artifact_store.clear()  # Start fresh
        # ... execution logic
    finally:
        self.artifact_store.clear()  # Always cleanup
```

#### 4. Update Error Handling

**Purpose:** Maintain existing error messages and behaviour

**Consideration:**
- ArtifactNotFoundError should be caught and re-raised as ExecutorError
- Error message should match existing format exactly
- This ensures tests continue passing without modification

## Testing

### Testing Strategy

Verify behaviour unchanged through existing test suite. Add specific tests for service integration.

### Test Scenarios

#### 1. Existing Tests Pass

**Setup:**
- Run full WCT test suite

**Expected behaviour:**
- All existing pipeline execution tests pass
- No behaviour changes visible to users
- Artifact passing works identically

#### 2. Artifact Storage and Retrieval

**Setup:**
- Create runbook with save_output and input_from
- Execute runbook

**Expected behaviour:**
- First step output saved via service
- Second step retrieves via service
- Results identical to dict-based approach

#### 3. Error Handling - Missing Artifact

**Setup:**
- Create runbook where step references non-existent artifact
- Execute runbook

**Expected behaviour:**
- ExecutorError raised with helpful message
- Error message matches current format
- Execution fails at correct point

#### 4. Cleanup After Execution

**Setup:**
- Execute runbook
- Check artifact store state after completion

**Expected behaviour:**
- Store cleared after successful execution
- Store cleared after failed execution (finally block)

#### 5. Multiple Runbook Executions

**Setup:**
- Execute two runbooks sequentially with same Executor

**Expected behaviour:**
- Second execution starts with clean store
- No artifacts leaked between executions

### Validation Commands

```bash
# Run all WCT tests
uv run pytest apps/wct/tests/ -v

# Run executor tests specifically
uv run pytest apps/wct/tests/test_executor.py -v

# Run pipeline execution tests
uv run pytest apps/wct/tests/ -k "pipeline" -v

# Run quality checks
./scripts/dev-checks.sh
```

## Implementation Notes

**Key principles:**
- Maintain exact backward compatibility
- No changes to runbook format or public API
- Existing tests should pass without modification
- Service integration is internal refactoring only

**Migration strategy:**
- Replace operations one at a time
- Test after each change
- Verify error messages match exactly
- Ensure cleanup happens in all code paths

## Issue Tracking

**Related Issue:** #227

**Upon completion:**
- **Close issue #227** - this is the final task (3 of 3)
- Update this task status to COMPLETED
- Commit with message: `feat: integrate artifact store with Executor

Closes #227`
