# Step 4: Implement Execution Order Resolution

- **Phase:** 2 - Implement Sequential Pipeline Execution
- **Status:** ✅ Completed (2025-01-11)
- **Prerequisites:** Step 3 (artifact storage added)

## Context

This is part of implementing pipeline execution for WCF, enabling multi-step analysis workflows where data flows between steps.

**See:** [Pipeline Execution and Component Decoupling](../pipeline-execution-and-component-decoupling.md) for full context and roadmap.

## Purpose

Add dependency graph validation to detect circular dependencies in pipeline execution steps, ensuring safe execution order.

## Problem

Pipeline steps can reference each other via `input_from`, creating dependency chains. Without validation, circular dependencies (A→B→C→A) would cause infinite loops or incorrect execution order.

**Example problematic scenario:**
```yaml
execution:
  - id: "step_a"
    input_from: "step_c"  # Depends on C
  - id: "step_b"
    input_from: "step_a"  # Depends on A
  - id: "step_c"
    input_from: "step_b"  # Depends on B → CYCLE!
```

## Solution

Use graph-based cycle detection with depth-first search (DFS) before execution starts. This validates the dependency graph is a **Directed Acyclic Graph (DAG)** and fails fast with a helpful error message.

## Decisions Made

1. **Build dependency graph** - Map step IDs to their dependencies from `input_from` fields
2. **Detect cycles using DFS** - Use depth-first search with recursion stack (standard algorithm)
3. **Sequential execution for now** - Return steps in declaration order (no reordering)
4. **Fail fast** - Raise ExecutorError on cycle detection before execution begins
5. **Future-proof** - Design allows adding topological sort later for parallel execution

## Implementation

### File to Modify

`apps/wct/src/wct/executor.py`

### Changes Required

#### 1. Add cycle detection method to Executor

**Method:** `_build_execution_order(steps: list[ExecutionStep]) -> list[ExecutionStep]`

**Purpose:** Validate dependency graph and return steps in safe execution order

**Algorithm (pseudo-code):**
```
function build_execution_order(steps):
    # Build dependency graph
    graph = {}
    for each step in steps:
        graph[step.id] = set()
        if step.input_from exists:
            graph[step.id].add(step.input_from)

    # Validate no cycles
    visited = set()
    for each step_id in graph:
        if has_cycle(step_id, graph, visited, recursion_stack=set()):
            raise ExecutorError("Circular dependency detected involving '{step_id}'")

    log("Execution order validated - no cycles")

    # For now, return in declaration order
    # (Future: topological sort for optimal ordering)
    return steps
```

**Error handling:**
- Raise `ExecutorError` with helpful message including step ID involved in cycle
- Message should explain that pipeline steps cannot form dependency cycles

#### 2. Add DFS cycle detection helper

**Method:** `_has_cycle(step_id, graph, visited, rec_stack) -> bool`

**Purpose:** Detect cycles using depth-first search with recursion stack

**Algorithm (pseudo-code):**
```
function has_cycle(node, graph, visited, rec_stack):
    visited.add(node)
    rec_stack.add(node)  # Track current DFS path

    for each dependency in graph[node]:
        if dependency not in visited:
            # Recursively check dependency
            if has_cycle(dependency, graph, visited, rec_stack):
                return true
        elif dependency in rec_stack:
            # Found back edge → cycle detected
            return true

    rec_stack.remove(node)  # Backtrack
    return false
```

**Key insight:** If we encounter a node already in the current recursion stack, we've found a back edge (cycle).

**Complexity:** O(V + E) where V = number of steps, E = number of dependencies

#### 3. Update execute_runbook

**Changes:**
1. Call `_build_execution_order(runbook.execution)` after loading runbook
2. Use returned order for execution loop (currently same as declaration order)
3. Let ExecutorError propagate if cycle detected

**Pseudo-code:**
```
function execute_runbook(runbook_path):
    runbook = load_runbook(runbook_path)

    # NEW: Validate execution order (fails fast on cycles)
    execution_order = _build_execution_order(runbook.execution)

    artifacts = {}
    results = []

    for step in execution_order:  # Use validated order
        result, message = _execute_step(step, runbook, artifacts)
        results.append(result)

        if step.save_output:
            artifacts[step.id] = message

    return results
```

## Testing

### Testing Strategy

**Critical principle:** Test through the **public API** (`execute_runbook`), not by calling private methods directly.

Create temporary runbook YAML files with various dependency patterns and verify behavior through `execute_runbook()`.

### Test Scenarios

**File:** `apps/wct/tests/test_executor.py`

#### 1. Direct Cycle (A → B → A)

**Setup:**
- Create runbook with 2 steps where `step_a.input_from = "step_b"` and `step_b.input_from = "step_a"`
- Use mock connector and analyser

**Expected behavior:**
- `execute_runbook()` raises `ExecutorError`
- Error message contains "Circular dependency detected"
- Error message helpful (mentions step ID involved)

#### 2. Indirect Cycle (A → B → C → A)

**Setup:**
- Create runbook with 3 steps forming indirect cycle
- Chain: A depends on C, B depends on A, C depends on B

**Expected behavior:**
- `execute_runbook()` raises `ExecutorError`
- Error message contains "Circular dependency detected"

#### 3. Valid Linear Chain (A → B → C)

**Setup:**
- Create runbook with 3 steps in valid dependency chain
- Step A uses connector (no `input_from`)
- Step B has `input_from: "step_a"` with `save_output: true` on A
- Step C has `input_from: "step_b"` with `save_output: true` on B

**Expected behavior:**
- Execution succeeds without raising errors
- All 3 steps execute
- Results returned in correct order

#### 4. Valid DAG with Branch

**Setup:**
- Create runbook where multiple steps depend on same ancestor
- Example: A (connector), B depends on A, C depends on A (parallel branches)

**Expected behavior:**
- Execution succeeds
- Both branches execute correctly

### Implementation Notes

- Use `tempfile.NamedTemporaryFile` to create runbook YAML in tests
- Use existing mock connector and analyser from test fixtures
- Clean up temp files in `finally` blocks
- Test error messages are helpful (include step IDs)

### Validation Commands

```bash
# Run all WCT tests
uv run pytest apps/wct/tests/ -v

# Run cycle detection tests specifically
uv run pytest apps/wct/tests/test_executor.py -k "cycle" -v

# Run all quality checks
./scripts/dev-checks.sh
```

## Success Criteria

**Functional:**
- [x] ✅ Direct cycles (A → B → A) are detected and rejected before execution
- [x] ✅ Indirect cycles (A → B → C → A) are detected and rejected
- [x] ✅ Valid linear chains (A → B → C) execute successfully
- [x] ✅ Valid DAGs with branches execute successfully
- [x] ✅ Helpful error messages that include step IDs involved in cycles
- [x] ✅ `execute_runbook` calls validation before execution loop
- [x] ✅ Validation happens before any step executes (fail fast)

**Quality:**
- [x] ✅ All tests pass (including new cycle detection tests)
- [x] ✅ Type checking passes (strict mode)
- [x] ✅ Linting passes
- [x] ✅ No regressions in existing functionality

**Code Quality:**
- [x] ✅ Private methods (`_build_execution_order`, `_has_cycle`) not tested directly
- [x] ✅ All tests use public API (`execute_runbook`)
- [x] ✅ Clean separation: validation logic separate from execution logic
- [x] ✅ Code follows existing patterns in Executor

## Implementation Notes

**Key design decisions:**
- Cycle detection only (no topological reordering yet)
- Steps returned in declaration order for sequential execution
- Graph traversal: standard DFS with recursion stack
- Complexity: O(V + E) where V = steps, E = dependencies

**Future enhancements:**
- Topological sort for optimal execution order
- Parallel execution of independent branches
- Dependency graph visualization for debugging

**Edge cases to consider:**
- Steps without `input_from` (connector-based) have no dependencies
- Self-referencing step (`input_from: "self"`) should be caught
- Missing step IDs referenced in `input_from` already caught by Step 2 validation

## Next Steps

- **Step 5:** Update `_execute_step` to support pipeline mode (use `input_from`)
- **Step 6:** Add pipeline schema resolution method
