# Step 4: Implement Execution Order Resolution

**Phase:** 2 - Implement Sequential Pipeline Execution
**Status:** Pending
**Prerequisites:** Step 3 (artifact storage added)

## Purpose

Add dependency graph validation to detect circular dependencies in pipeline execution steps, ensuring safe execution order.

## Decisions Made

1. **Build dependency graph** - Map step IDs to their dependencies
2. **Detect cycles using DFS** - Use depth-first search with recursion stack
3. **Sequential execution for now** - Return steps in declaration order (topological sort can come later)
4. **Fail fast** - Raise ExecutorError on cycle detection before execution begins

## Implementation

### File to Modify

`apps/wct/src/wct/executor.py`

### Changes Required

Add two new methods to the `Executor` class:

```python
def _build_execution_order(self, steps: list[ExecutionStep]) -> list[ExecutionStep]:
    """Build execution order respecting dependencies.

    For sequential execution, this validates there are no cycles
    and returns steps in declaration order. Future enhancement can
    add proper topological sorting for parallel execution.

    Args:
        steps: Execution steps from runbook

    Returns:
        Steps in valid execution order

    Raises:
        ExecutorError: If circular dependencies detected
    """
    # Build dependency graph
    dependencies: dict[str, set[str]] = {}
    for step in steps:
        step_id = step.id or step.name  # Use name as fallback for single-step mode
        dependencies[step_id] = set()
        if step.input_from:
            dependencies[step_id].add(step.input_from)

    # Validate no cycles using DFS
    visited: set[str] = set()
    for step_id in dependencies:
        if self._has_cycle(step_id, dependencies, visited, set()):
            raise ExecutorError(
                f"Circular dependency detected in execution steps involving '{step_id}'. "
                f"Pipeline steps cannot form dependency cycles."
            )

    logger.debug("Execution order validated - no circular dependencies found")

    # For sequential execution, return in declaration order
    # (Proper topological sort can be added later for parallel execution)
    return steps


def _has_cycle(
    self,
    step_id: str,
    dependencies: dict[str, set[str]],
    visited: set[str],
    rec_stack: set[str],
) -> bool:
    """Check for cycles in dependency graph using depth-first search.

    Args:
        step_id: Current step being checked
        dependencies: Dependency graph (step_id -> set of dependencies)
        visited: Set of all visited nodes
        rec_stack: Recursion stack for current DFS path

    Returns:
        True if cycle detected, False otherwise
    """
    visited.add(step_id)
    rec_stack.add(step_id)

    # Check all dependencies
    for dep in dependencies.get(step_id, set()):
        # If dependency not visited, recurse
        if dep not in visited:
            if self._has_cycle(dep, dependencies, visited, rec_stack):
                return True
        # If dependency is in current recursion stack, cycle found
        elif dep in rec_stack:
            return True

    # Remove from recursion stack as we backtrack
    rec_stack.remove(step_id)
    return False
```

Update `execute_runbook` to call the new method:

```python
def execute_runbook(self, runbook_path: Path) -> list[AnalysisResult]:
    """Load and execute a runbook file with pipeline support."""
    try:
        runbook = RunbookLoader.load(runbook_path)
    except Exception as e:
        raise ExecutorError(f"Failed to load runbook {runbook_path}: {e}") from e

    # NEW: Validate execution order and dependencies
    execution_order = self._build_execution_order(runbook.execution)

    # Artifact storage for passing data between steps
    artifacts: dict[str, Message] = {}

    results: list[AnalysisResult] = []
    for step in execution_order:  # Use validated order
        result = self._execute_step(step, runbook, artifacts)
        results.append(result)

        if step.save_output and step.id and result.message:
            logger.debug(f"Saving output artifact for step '{step.id}'")
            artifacts[step.id] = result.message

    return results
```

## Testing

### Unit Tests to Add

**File:** `apps/wct/tests/unit/test_executor.py`

```python
import pytest
from wct.executor import Executor, ExecutorError
from wct.runbook import ExecutionStep


def test_execution_order_detects_direct_cycle(isolated_registry):
    """Cycle detection catches direct circular dependency."""
    executor = Executor.create_with_built_ins()

    # Create steps with direct cycle: A -> B -> A
    steps = [
        ExecutionStep(
            id="step_a",
            name="Step A",
            description="",
            input_from="step_b",  # Depends on B
            analyser="analyser",
            input_schema="standard_input",
            output_schema="standard_input",
        ),
        ExecutionStep(
            id="step_b",
            name="Step B",
            description="",
            input_from="step_a",  # Depends on A - CYCLE!
            analyser="analyser",
            input_schema="standard_input",
            output_schema="standard_input",
        ),
    ]

    with pytest.raises(ExecutorError) as exc_info:
        executor._build_execution_order(steps)

    assert "Circular dependency detected" in str(exc_info.value)


def test_execution_order_detects_indirect_cycle(isolated_registry):
    """Cycle detection catches indirect circular dependency."""
    executor = Executor.create_with_built_ins()

    # Create steps with indirect cycle: A -> B -> C -> A
    steps = [
        ExecutionStep(
            id="step_a",
            name="Step A",
            description="",
            input_from="step_c",  # Depends on C
            analyser="analyser",
            input_schema="standard_input",
            output_schema="standard_input",
        ),
        ExecutionStep(
            id="step_b",
            name="Step B",
            description="",
            input_from="step_a",  # Depends on A
            analyser="analyser",
            input_schema="standard_input",
            output_schema="standard_input",
        ),
        ExecutionStep(
            id="step_c",
            name="Step C",
            description="",
            input_from="step_b",  # Depends on B - CYCLE!
            analyser="analyser",
            input_schema="standard_input",
            output_schema="standard_input",
        ),
    ]

    with pytest.raises(ExecutorError) as exc_info:
        executor._build_execution_order(steps)

    assert "Circular dependency detected" in str(exc_info.value)


def test_execution_order_accepts_valid_dag(isolated_registry):
    """Valid directed acyclic graph is accepted."""
    executor = Executor.create_with_built_ins()

    # Create valid linear dependency: A -> B -> C
    steps = [
        ExecutionStep(
            id="step_a",
            name="Step A",
            description="",
            connector="filesystem",
            analyser="analyser",
            input_schema="standard_input",
            output_schema="standard_input",
            save_output=True,
        ),
        ExecutionStep(
            id="step_b",
            name="Step B",
            description="",
            input_from="step_a",
            analyser="analyser",
            input_schema="standard_input",
            output_schema="standard_input",
            save_output=True,
        ),
        ExecutionStep(
            id="step_c",
            name="Step C",
            description="",
            input_from="step_b",
            analyser="analyser",
            input_schema="standard_input",
            output_schema="standard_input",
        ),
    ]

    # Should not raise
    result = executor._build_execution_order(steps)
    assert len(result) == 3
```

### Manual Testing

Create a test YAML with circular dependency:

```yaml
name: "Circular Dependency Test"
description: "Should fail validation"

connectors:
  - name: "reader"
    type: "filesystem_connector"
    properties:
      path: "."

analysers:
  - name: "analyser"
    type: "personal_data_analyser"

execution:
  - id: "step_a"
    name: "Step A"
    input_from: "step_b"  # Circular!
    analyser: "analyser"
    input_schema: "standard_input"
    output_schema: "standard_input"

  - id: "step_b"
    name: "Step B"
    input_from: "step_a"  # Circular!
    analyser: "analyser"
    input_schema: "standard_input"
    output_schema: "standard_input"
```

Test:
```bash
uv run wct run circular_test.yaml
# Should error with "Circular dependency detected"
```

### Validation

```bash
# Run unit tests
cd apps/wct
uv run pytest tests/unit/test_executor.py::test_execution_order -v

# Type check
./scripts/type-check.sh

# Lint
./scripts/lint.sh
```

## Success Criteria

- [ ] `_build_execution_order` method added to Executor
- [ ] `_has_cycle` method correctly detects cycles using DFS
- [ ] Direct cycles are detected (A -> B -> A)
- [ ] Indirect cycles are detected (A -> B -> C -> A)
- [ ] Valid DAGs are accepted
- [ ] ExecutorError is raised with helpful message
- [ ] Unit tests pass
- [ ] Type checking passes
- [ ] Linting passes

## Notes

- This implements cycle detection only, not topological sorting
- Steps are returned in declaration order for sequential execution
- Future enhancement: proper topological sort for parallel execution
- The algorithm has O(V + E) complexity where V=steps, E=dependencies

## Next Step

Step 5: Update _execute_step to support pipeline mode
