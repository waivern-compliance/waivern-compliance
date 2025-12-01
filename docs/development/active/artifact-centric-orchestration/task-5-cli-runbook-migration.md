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
2. Update `wct validate-runbook` to use Planner
3. Update `wct ls-connectors` and `wct ls-analysers` to use ComponentRegistry
4. Migrate all sample runbooks to the new format

## Problem

The CLI currently uses the old sequential executor and three-section runbook format. This task completes the transition by wiring up the new components and ensuring all sample runbooks work with the new system.

## Decisions Made

1. **Replace, don't deprecate** - Old format no longer supported (per user guidance)
2. **Async executor** - DAGExecutor is async; CLI calls it via `asyncio.run()`
3. **ComponentRegistry** - Both Planner and DAGExecutor require ComponentRegistry (from Task 4)
4. **Defer `wct inspect`** - Requires artifact persistence; deferred to future work (see [execution-persistence.md](../../future-plans/execution-persistence.md))

## Output Format Design

### Core Export Format

Universal format for all exporters. Regulation-specific exporters (GDPR, CCPA) add their own context.

```json
{
  "format_version": "2.0.0",

  "run": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-12-01T14:30:00Z",
    "duration_seconds": 12.34,
    "status": "completed"
  },

  "runbook": {
    "path": "runbooks/gdpr_analysis.yaml",
    "name": "GDPR Compliance Analysis",
    "description": "Analyse database for personal data",
    "contact": "John Smith <john@example.com>"
  },

  "summary": {
    "total": 5,
    "succeeded": 3,
    "failed": 1,
    "skipped": 1
  },

  "outputs": [
    {
      "artifact_id": "personal_data_findings",
      "name": "Personal Data Detection",
      "description": "PII detection in customer database",
      "contact": "analyst@company.com",
      "schema": {
        "name": "personal_data_finding",
        "version": "1.0.0"
      },
      "duration_seconds": 2.1,
      "content": { ... }
    }
  ],

  "errors": [
    {
      "artifact_id": "external_api_check",
      "error": "Connection refused"
    }
  ],

  "skipped": ["dependent_report"]
}
```

### Design Decisions

1. **Runbook metadata carried in ExecutionResult** - name, description, contact, path only. Full artifact definitions not stored (may contain resolved secrets).

2. **Regulation-specific info is exporter responsibility** - Core format has no `organisation` field. `GdprExporter` reads `organisation.yaml` and adds Article 30(1)(a) compliance info at export time.

3. **Replay uses source files** - To replay, re-execute from runbook file (optionally at specific git commit). Stored execution is for inspection/audit, not replay.

4. **`outputs` is array** - Ordered, natural for iteration. Only includes artifacts with `output: true`.

5. **`status` values** - `completed` (all succeeded), `failed` (any failed), `partial` (some skipped, none failed).

### Exporter Architecture

```
ExecutionResult (core data)
        │
        ├── JsonExporter        → core format
        ├── GdprExporter        → core + organisation (Article 30(1)(a))
        ├── CcpaExporter        → core + CCPA-specific fields
        └── ReportExporter      → formatted PDF/HTML
```

Each exporter reads from ExecutionResult (or ExecutionStore in future) and adds regulation-specific context as needed.

## Implementation

### Files to Modify/Create/Delete

```
apps/wct/src/wct/
├── cli.py             # MODIFY: update run, validate, ls-* commands
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

**Logging updates:**
- Log artifact start/complete with timing
- Log parallel batch info
- Log skip reasons

#### 2. Update `wct validate-runbook`

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

#### 3. Update `wct ls-connectors` and `wct ls-analysers`

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

#### 4. Migrate sample runbooks

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

#### 3. wct validate-runbook
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

# Run full dev-checks
./scripts/dev-checks.sh
```

## Implementation Notes

- Use `asyncio.run()` to call DAGExecutor from CLI
- ComponentRegistry must be created once and shared between Planner and DAGExecutor
- ArtifactStore must have transient lifetime in ServiceContainer (fresh store per execution)
- Consider adding `--dry-run` flag that just validates without executing
