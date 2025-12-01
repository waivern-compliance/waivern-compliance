# Task 5: Update CLI and Migrate Sample Runbooks

- **Phase:** 3 - Integration
- **Status:** TODO
- **GitHub Issue:** #246 (close via PR)
- **Prerequisites:** Task 4 (DAGExecutor)
- **Design:** [artifact-centric-orchestration-design.md](../artifact-centric-orchestration-design.md)

## Context

Tasks 1-4 built the complete orchestration infrastructure. This task integrates it into WCT by updating the CLI to use the new Planner and DAGExecutor, and migrates all sample runbooks to the artifact-centric format.

## Purpose

1. Update `wct run` to use Planner + DAGExecutor
2. Add `wct inspect` command for artifact observability
3. Migrate all sample runbooks to the new format

## Problem

The CLI currently uses the old sequential executor and three-section runbook format. This task completes the transition by wiring up the new components and ensuring all sample runbooks work with the new system.

## Decisions Made

1. **Replace, don't deprecate** - Old format no longer supported (per user guidance)
2. **wct inspect** - New command for viewing artifact contents post-execution
3. **Async CLI entry point** - Use `asyncio.run()` to bridge CLI to async executor
4. **ComponentRegistry** - Both Planner and DAGExecutor require ComponentRegistry (from Task 4)

## Implementation

### Files to Modify/Create/Delete

```
apps/wct/src/wct/
├── cli.py             # MODIFY: update run, validate, ls-* commands, add inspect
├── executor.py        # DELETE: replaced by DAGExecutor
├── runbook.py         # DELETE: replaced by waivern_orchestration models
└── analysis.py        # DELETE: AnalysisResult replaced by ExecutionResult

apps/wct/tests/
├── test_executor.py   # DELETE
├── test_runbook.py    # DELETE
└── test_cli.py        # UPDATE
```

### Changes Required

#### 1. Update `wct run` command

**Current flow:**
```
run command → load runbook → Executor.execute_runbook()
```

**New flow:**
```
run command → ComponentRegistry → Planner.plan() → asyncio.run(DAGExecutor.execute())
```

**Changes to run command:**
```
function run_command(runbook_path, options):
    # Build registry with container and component factories
    container = build_service_container()
    registry = ComponentRegistry(container)

    # Create planner and plan
    planner = Planner(registry)
    plan = planner.plan(runbook_path)

    # Create executor with same registry
    executor = DAGExecutor(registry)

    # Execute (async → sync bridge)
    result = asyncio.run(executor.execute(plan))

    # Output results
    output_results(result, options)
```

**Output format updates:**
- Show parallel execution info (which artifacts ran together)
- Show timing per artifact
- Show skipped artifacts with reason
- Maintain existing JSON output format for findings

**Logging updates:**
- Log artifact start/complete with timing
- Log parallel batch info
- Log skip reasons

#### 2. Implement `wct inspect` command

**Usage:**
```bash
wct inspect <runbook.yaml> <artifact_id>
```

**Behaviour:**
1. Run the runbook (if not already executed)
2. Retrieve specified artifact from store
3. Display artifact content (JSON formatted)

**Implementation approach:**

Option A: Execute on-demand
- Run full execution, then retrieve artifact
- Simple but slow for repeated inspections

Option B: Persist artifacts
- Save artifacts to disk after execution
- Inspect reads from disk
- Faster for repeated access

Recommend Option A for simplicity. Option B can be added later if needed.

**Command implementation (pseudo-code):**
```
function inspect_command(runbook_path, artifact_id):
    # Build registry
    container = build_service_container()
    registry = ComponentRegistry(container)

    # Plan and execute
    planner = Planner(registry)
    plan = planner.plan(runbook_path)

    # Verify artifact exists in plan
    if artifact_id not in plan.runbook.artifacts:
        raise error("Artifact not found in runbook")

    executor = DAGExecutor(registry)
    result = asyncio.run(executor.execute(plan))

    # Get artifact from store
    store = registry.container.get_service(ArtifactStore)
    if not store.exists(artifact_id):
        if artifact_id in result.skipped:
            print("Artifact was skipped: " + skip_reason)
        else:
            print("Artifact failed: " + result.artifacts[artifact_id].error)
        return

    message = store.get(artifact_id)
    print(json.dumps(message.content, indent=2))
```

#### 3. Update `wct validate-runbook`

Update to use new Planner for validation:
```
function validate_runbook_command(runbook_path):
    # Build registry (no container services needed for validation)
    container = build_service_container()
    registry = ComponentRegistry(container)

    planner = Planner(registry)
    try:
        plan = planner.plan(runbook_path)
        print("Runbook valid")
        print(f"Artifacts: {len(plan.runbook.artifacts)}")
        print(f"DAG depth: {calculate_depth(plan.dag)}")
    except OrchestrationError as e:
        print(f"Validation failed: {e}")
        exit(1)
```

#### 4. Update `wct ls-connectors` and `wct ls-analysers`

Use ComponentRegistry directly instead of Executor:
```
function list_connectors_command():
    container = build_service_container()
    registry = ComponentRegistry(container)

    for name, factory in registry.connector_factories.items():
        print(name, factory)

function list_analysers_command():
    container = build_service_container()
    registry = ComponentRegistry(container)

    for name, factory in registry.analyser_factories.items():
        print(name, factory)
```

#### 5. Migrate sample runbooks

**Files to migrate:**
- `apps/wct/runbooks/samples/file_content_analysis.yaml`
- `apps/wct/runbooks/samples/LAMP_stack.yaml`
- Any other sample runbooks

**Migration pattern:**

Before (three-section):
```yaml
connectors:
  - name: "connector_name"
    type: "connector_type"
    properties: {...}

analysers:
  - name: "analyser_name"
    type: "analyser_type"
    properties: {...}

execution:
  - id: "step_id"
    connector: "connector_name"
    analyser: "analyser_name"
    input_schema: "..."
    output_schema: "..."
```

After (artifact-centric):
```yaml
name: "Runbook Name"
description: "What this runbook does"

artifacts:
  data_source:
    source:
      type: connector_type
      properties: {...}

  findings:
    inputs: data_source
    transform:
      type: analyser_type
      properties: {...}
    output: true
```

**Migration checklist per runbook:**
- [ ] Add `name` and `description` at top level
- [ ] Convert each connector to source artifact
- [ ] Convert each execution step to derived artifact
- [ ] Set `output: true` on terminal artifacts
- [ ] Remove explicit schema declarations (inferred)
- [ ] Test with `wct run`

## Testing

### Test Scenarios for CLI

#### 1. wct run with new format
- Create artifact-centric runbook
- Run `wct run <runbook>`
- Verify execution completes
- Verify output format correct

#### 2. wct run error handling
- Create runbook with missing component
- Verify helpful error message
- Verify non-zero exit code

#### 3. wct inspect valid artifact
- Run runbook, then inspect artifact
- Verify JSON content displayed

#### 4. wct inspect missing artifact
- Inspect non-existent artifact ID
- Verify helpful error message

#### 5. wct inspect skipped artifact
- Create runbook where artifact is skipped
- Inspect that artifact
- Verify skip reason displayed

#### 6. wct validate-runbook
- Validate valid runbook
- Validate invalid runbook (cycle, missing ref)
- Verify error messages helpful

### Test Scenarios for Migrated Runbooks

#### 1. file_content_analysis.yaml
- Run migrated runbook
- Verify output matches previous format
- Verify findings generated

#### 2. LAMP_stack.yaml
- Run migrated runbook
- Verify multi-step pipeline works
- Verify all analysers execute

### Validation Commands

```bash
# Run CLI tests
uv run pytest apps/wct/tests/test_cli.py -v

# Test sample runbooks manually
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct run apps/wct/runbooks/samples/LAMP_stack.yaml -v

# Test inspect command
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml
uv run wct inspect apps/wct/runbooks/samples/file_content_analysis.yaml findings

# Run full dev-checks
./scripts/dev-checks.sh
```

## Implementation Notes

- Use `asyncio.run()` for async→sync bridge in CLI
- ComponentRegistry must be created once and shared between Planner and DAGExecutor
- ArtifactStore must have transient lifetime in ServiceContainer (fresh store per execution)
- Consider adding `--dry-run` flag that just validates without executing
- Consider adding `--format` flag to inspect (json, yaml, pretty)
