# Task 2: Implement Parser and ExecutionDAG

- **Phase:** 1 - Foundation
- **Status:** TODO
- **Prerequisites:** Task 1 (models and errors)
- **Design:** [artifact-centric-orchestration-design.md](../artifact-centric-orchestration-design.md)

## Context

Task 1 established the data models. This task adds YAML parsing and dependency graph building, enabling runbook files to be loaded and their execution order determined.

## Purpose

Implement the YAML parser for artifact-centric runbooks and the ExecutionDAG class that builds and validates the dependency graph using Python's stdlib `graphlib.TopologicalSorter`.

## Problem

Runbook files need to be parsed into the Runbook model, with environment variable substitution. The artifact dependencies (via `inputs` field) form a directed graph that must be validated for cycles and used to determine execution order.

## Decisions Made

1. **PyYAML for parsing** - Standard, well-tested YAML library
2. **graphlib.TopologicalSorter** - Python stdlib, zero external dependencies, designed for parallel execution
3. **Environment variable substitution** - Use `${VAR_NAME}` syntax, consistent with existing runbooks
4. **Fail-fast validation** - Detect cycles and missing references before execution

## Implementation

### Files to Create/Modify

```
libs/waivern-orchestration/src/waivern_orchestration/
├── parser.py      # NEW
└── dag.py         # NEW
```

### Changes Required

#### 1. Implement parser.py

**Functions:**

```
parse_runbook(path: Path) -> Runbook
  - Read YAML file
  - Substitute environment variables
  - Parse into Runbook model
  - Raise RunbookParseError on failure

parse_runbook_from_dict(data: dict) -> Runbook
  - Parse dict directly into Runbook model
  - Useful for testing and programmatic use

_substitute_env_vars(value: Any) -> Any
  - Recursively walk data structure
  - Replace ${VAR_NAME} patterns with os.environ values
  - Raise RunbookParseError if variable not found
```

**Algorithm for env var substitution (pseudo-code):**
```
function substitute(value):
    if value is string:
        find all ${VAR_NAME} patterns
        for each pattern:
            lookup VAR_NAME in os.environ
            if not found: raise error with var name
            replace pattern with value
        return substituted string
    if value is dict:
        return {k: substitute(v) for k, v in dict}
    if value is list:
        return [substitute(item) for item in list]
    return value  # numbers, booleans, None unchanged
```

**Error handling:**
- Include file path in error messages
- Include variable name for missing env vars
- Wrap Pydantic ValidationError with context

#### 2. Implement dag.py

**Class: ExecutionDAG**

```
ExecutionDAG
  - __init__(artifacts: dict[str, ArtifactDefinition])
    Build internal graph representation

  - validate() -> None
    Check for cycles using TopologicalSorter.prepare()
    Raises CycleDetectedError if cycles found

  - get_sorter() -> TopologicalSorter[str]
    Return prepared sorter for parallel execution

  - get_dependents(artifact_id: str) -> set[str]
    Return all artifacts that depend on this one
    Used for skipping dependents on failure

  - get_dependencies(artifact_id: str) -> set[str]
    Return all artifacts this one depends on
```

**Graph building (pseudo-code):**
```
function build_graph(artifacts):
    graph = {}
    for artifact_id, definition in artifacts:
        deps = extract_dependencies(definition.inputs)
        graph[artifact_id] = deps
    return graph

function extract_dependencies(inputs_field):
    if inputs_field is None:
        return empty set  # Source artifact
    if inputs_field is string:
        return {inputs_field}
    if inputs_field is list:
        return set(inputs_field)  # Fan-in
```

**Cycle detection:**
- Use `TopologicalSorter(graph).prepare()`
- Catches `graphlib.CycleError`
- Transform to `CycleDetectedError` with cycle path

**Dependent tracking:**
- Build reverse graph for efficient `get_dependents()` lookup
- Used when artifact fails to skip all downstream artifacts

### Update __init__.py exports

Add:
```python
from .parser import parse_runbook, parse_runbook_from_dict
from .dag import ExecutionDAG
```

## Testing

### Test Scenarios for Parser

#### 1. Valid runbook parsing
- Create YAML file with source and derived artifacts
- Parse and verify Runbook model is correct
- Verify all artifacts present

#### 2. Environment variable substitution
- Set env vars before test
- Create YAML with `${VAR_NAME}` patterns
- Parse and verify values substituted

#### 3. Missing environment variable
- Create YAML with undefined `${MISSING_VAR}`
- Verify RunbookParseError raised
- Verify error message includes variable name

#### 4. Invalid YAML syntax
- Create file with malformed YAML
- Verify RunbookParseError raised
- Verify error includes file path

#### 5. parse_runbook_from_dict
- Create dict matching runbook structure
- Parse and verify Runbook model correct
- Useful for testing without file I/O

### Test Scenarios for ExecutionDAG

#### 1. Linear chain (A → B → C)
- Create artifacts where C depends on B, B depends on A
- Build DAG and verify dependencies correct
- Verify get_sorter() returns valid sorter

#### 2. Parallel independent artifacts
- Create multiple source artifacts (no dependencies)
- Verify all returned together from get_ready()

#### 3. Fan-in (A, B → C)
- Create C with `inputs: [A, B]`
- Verify C has both A and B as dependencies
- Verify C only ready after both complete

#### 4. Fan-out (A → B, C)
- Create B and C both depending on A
- Verify get_dependents(A) returns {B, C}

#### 5. Cycle detection (A → B → A)
- Create circular dependency
- Call validate()
- Verify CycleDetectedError raised

#### 6. Complex cycle (A → B → C → A)
- Create indirect cycle
- Verify detected by validate()

#### 7. Self-reference
- Create artifact with `inputs: self_id`
- Verify CycleDetectedError raised

### Validation Commands

```bash
# Run package tests
uv run pytest libs/waivern-orchestration/tests/ -v

# Run specific test files
uv run pytest libs/waivern-orchestration/tests/test_parser.py -v
uv run pytest libs/waivern-orchestration/tests/test_dag.py -v

# Run full dev-checks
./scripts/dev-checks.sh
```

## Implementation Notes

- Use `re.sub` with callback for env var substitution
- Pattern for env vars: `\$\{([^}]+)\}`
- TopologicalSorter is designed for the producer/consumer pattern - perfect for DAG execution
- Consider using `functools.cached_property` for reverse graph if performance matters
