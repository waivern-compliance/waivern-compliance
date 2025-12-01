# Phase 3: Child Runbooks - Requirements Memo

- **Status:** Planned (design after Phase 2 completion)
- **Prerequisites:** Phase 2 complete
- **Reference:** [Main Design](../artifact-centric-orchestration-design.md)

## Problem

Complex compliance workflows may need to:
- Compose runbooks from smaller, reusable runbooks
- Dynamically generate runbooks (agentic workflows)
- Isolate child execution with separate resource limits

## Solution

Enable **recursive runbook execution** where an artifact's input can be executed as a child runbook.

## Key Requirements

1. `execute: { mode: child }` field triggers child runbook execution
2. `ScopedArtifactStore` isolates child writes while allowing parent reads
3. `max_child_depth` prevents infinite recursion
4. Child inherits parent's `ServiceContainer` (shared LLM service, etc.)
5. Child can override `timeout` and `cost_limit`

## Example Usage

```yaml
artifacts:
  generated_runbook:
    inputs: requirements
    transform: { type: runbook_generator }  # AI generates runbook

  analysis_results:
    inputs: generated_runbook
    execute:
      mode: child
      timeout: 300
      cost_limit: 5.0
    output: true
```

## Key Components

- `ScopedArtifactStore`: Child reads parent artifacts, writes locally
- `_run_child_runbook()`: Executor method for recursive execution
- Runbook registered as schema (enables runbook-as-artifact)

## Out of Scope

- Detailed ScopedArtifactStore design
- Error propagation strategy
- Cost/timeout aggregation rules

These will be defined in full design document after Phase 2.
