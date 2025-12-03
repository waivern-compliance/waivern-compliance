# Phase 3: Child Runbooks - Requirements Memo

- **Status:** Planned (design after Task 7 completion)
- **Prerequisites:** Task 7 (Export Infrastructure and Multi-Schema Fan-In) complete
- **Reference:** [Multi-Schema Fan-In](../../../future-plans/multi-schema-fan-in.md)

## Problem

Complex compliance workflows may need to:
- Compose runbooks from smaller, reusable runbooks
- Dynamically generate runbooks (agentic workflows)
- Isolate child execution with separate resource limits

## Solution

Enable **recursive runbook execution** where an artifact's input can be executed as a child runbook.

## Key Requirements

1. Runbook `inputs` section declares expected inputs with schemas
2. `execute: { mode: child }` field triggers child runbook execution
3. `input_mapping` maps parent artifacts to child's declared inputs
4. `ScopedArtifactStore` resolves mapped inputs from parent, isolates child writes
5. `max_child_depth` prevents infinite recursion
6. Child inherits parent's `ServiceContainer` (shared LLM service, etc.)
7. Child can override `timeout` and `cost_limit`
8. Validation at plan time: all required inputs must be mapped

## Runbook Input Declarations

Runbooks can declare explicit inputs they expect to receive:

```yaml
# Child runbook: analysis_workflow.yaml
name: "Analysis Sub-workflow"
inputs:  # Declares expected inputs as virtual source artifacts
  source_data:
    schema: standard_input/1.0.0
  config_data:
    schema: analysis_config/1.0.0
    optional: true  # Not required

artifacts:
  findings:
    inputs: source_data  # References declared input
    transform: { type: personal_data_analyser }
```

Parent runbook maps its artifacts to child's declared inputs:

```yaml
# Parent runbook
artifacts:
  db_schema:
    source: { type: mysql }

  child_results:
    inputs: child_runbook
    execute:
      mode: child
      timeout: 300
      cost_limit: 5.0
      input_mapping:
        source_data: db_schema  # Parent artifact → child input name
    output: true
```

**Key points:**
- Child declares what it needs via `inputs` section
- Parent provides mapping via `input_mapping`
- `ScopedArtifactStore` resolves mapped inputs from parent store
- Validation at plan time: all required inputs must be mapped

## Example Usage (Dynamic Runbook)

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
      input_mapping:
        source_data: db_schema  # Map parent data to generated runbook's input
    output: true
```

## Key Components

- `ScopedArtifactStore`: Child reads parent artifacts via `input_mapping`, writes locally
- `_run_child_runbook()`: Executor method for recursive execution
- `Runbook.inputs`: New field in Pydantic model for declared inputs
- `runbook/1.0.0` schema: Auto-generated from Pydantic model via `RunbookSchemaGenerator`

## Design Rationale

### Runbook as Schema

A runbook is just another schema (`runbook/1.0.0`). This means:

1. **Analysers can produce runbooks** - An analyser declares `get_supported_output_schemas()` returning `[Schema("runbook", "1.0.0")]` and outputs a `Message` containing runbook content
2. **No special handling needed** - Runbook flows through the system like any other artifact
3. **Executor interprets** - When `execute: { mode: child }` is specified, executor interprets the Message content as a runbook to execute

```python
class RunbookGeneratorAnalyser(Analyser):
    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("runbook", "1.0.0")]

    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        runbook_content = {
            "name": "Generated Analysis",
            "inputs": {"source_data": {"schema": "standard_input/1.0.0"}},
            "artifacts": {...}
        }
        return Message(schema=output_schema, content=runbook_content)
```

### Schema Auto-Generation

The `runbook/1.0.0` JSON Schema is auto-generated from the Pydantic `Runbook` model via `RunbookSchemaGenerator` in waivern-orchestration. No manual schema maintenance required - update the Pydantic model, regenerate the schema.

## Out of Scope

- Detailed ScopedArtifactStore design
- Error propagation strategy
- Cost/timeout aggregation rules

These will be defined in full design document after Task 7.
