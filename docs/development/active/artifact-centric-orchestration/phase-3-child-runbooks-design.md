# Phase 3: Child Runbooks - Design Document

- **Status:** Design Complete
- **Prerequisites:** Task 7 (Export Infrastructure and Multi-Schema Fan-In) complete
- **Last Updated:** 2025-12-12

## Table of Contents

1. [Overview](#overview)
2. [Use Cases](#use-cases)
3. [Design Principles](#design-principles)
4. [Runbook Input Declarations](#runbook-input-declarations)
5. [Child Runbook Directive](#child-runbook-directive)
6. [Output Mapping](#output-mapping)
7. [Planner Flattening](#planner-flattening)
8. [Path Resolution](#path-resolution)
9. [Validation Rules](#validation-rules)
10. [Model Changes](#model-changes)
11. [Execution Results](#execution-results)
12. [Terraform-Style Extensions](#terraform-style-extensions)
13. [Examples](#examples)
14. [Implementation Plan](#implementation-plan)
15. [Future Considerations](#future-considerations)

---

## Overview

### Problem

Complex compliance workflows need to:

- Compose runbooks from smaller, reusable runbooks
- Share common analysis patterns across projects
- Enable modular, maintainable runbook design

### Solution

Enable **runbook composition** through plan-time flattening, where child runbooks are treated as parameterised modules that the Planner inlines into the parent's execution plan.

### Key Insight

This is **not** a new execution mode. The Planner flattens child runbooks at plan time, producing a single `ExecutionPlan` with a unified DAG. The Executor remains unchanged - it simply executes the flattened plan.

---

## Use Cases

### Use Case 1: Processor-Driven Dynamic Execution

A Processor internally decides to generate and execute a child runbook. The parent runbook is unaware of this - it simply invokes a Processor and receives results.

```
Parent Runbook                     Processor (internally)
┌─────────────────────┐           ┌─────────────────────────────┐
│ artifacts:          │           │ 1. Receive inputs           │
│   requirements:     │           │ 2. Generate runbook content │
│     source: ...     │           │ 3. Call Planner.plan()      │
│                     │           │ 4. Call Executor.execute()  │
│   analysis_results: │──inputs──▶│ 5. Return result as Message │
│     inputs: reqs    │           └─────────────────────────────┘
│     process:        │◀──result──
│       type: smart_analyser
└─────────────────────┘
```

**Characteristics:**

- Parent doesn't know a child runbook was involved
- Processor has full control over runbook generation
- Processor receives pre-built Planner + Executor via dependency injection
- Returns standard `Message` (like any Processor)

**Framework Support Required:**

- Inject Planner and Executor into Processor factories
- Pass execution context (remaining timeout, cost budget) to Processor

### Use Case 2: Declarative Runbook Composition (Primary Focus)

Parent runbook explicitly references child runbooks as reusable modules. The Planner flattens the composition at plan time.

```
Parent Runbook                     Child Runbook (file)
┌─────────────────────┐           ┌─────────────────────────────┐
│ artifacts:          │           │ inputs:                     │
│   db_schema:        │           │   source_data:              │
│     source: mysql   │           │     schema: standard_input  │
│                     │           │                             │
│   child_analysis:   │──refs────▶│ artifacts:                  │
│     inputs: db_schema           │   findings:                 │
│     child_runbook:  │           │     inputs: source_data     │
│       path: ./child.yaml        │     process: personal_data  │
│       output: findings          └─────────────────────────────┘
└─────────────────────┘
```

**Characteristics:**

- Explicit composition in parent runbook
- Planner flattens at plan time
- Single ExecutionPlan, single ArtifactStore
- Full upfront validation (schemas, dependencies, cycles)

---

## Design Principles

### 1. Plan-Time Flattening

All child runbook resolution happens in the Planner. The Executor receives a flat DAG and executes it without knowing about the original composition structure.

### 2. Schema as Contract

Child runbooks declare their inputs using schemas - the shared, unambiguous language between WCF components. Schema compatibility is validated at plan time.

### 3. No Scoped Artifact Store

Since flattening produces a single DAG, all artifacts live in one ArtifactStore. No need for nested scopes or complex isolation mechanisms.

### 4. Security by Default

Child runbook paths are restricted: no absolute paths, no parent directory traversal. Search is limited to parent directory and configured template paths.

### 5. Explicit Over Implicit

- All required inputs must be explicitly mapped
- Outputs must be explicitly declared
- No magic conventions or hidden behaviour

### 6. Configuration as Schema-Validated Input

Configuration values (paths, options, credentials) are passed as schema-validated input artifacts, not loose key-value pairs.

**Rationale:**

Child runbooks should be **well-considered compliance modules**, not copy-paste YAML snippets. Schema-validated configuration reinforces this by:

1. **Forcing deliberate interface design** - Authors must think about what configuration their module needs
2. **Providing type safety** - Catch misconfigurations at plan time, not runtime
3. **Enabling self-documentation** - The schema documents expected configuration
4. **Supporting audit trails** - Clear, typed data contracts for compliance records
5. **Reducing misuse surface** - Invalid configurations fail fast with clear errors

**Industry alignment:**

Modern workflow tools (Dagster, Prefect, dbt) have moved toward strong typing after learning from the pain of loose configuration in earlier systems. For a compliance framework where misconfigurations can have regulatory consequences, this rigour is essential.

**Example:**

```yaml
# Configuration passed as schema-validated input
inputs:
  source_data:
    schema: standard_input/1.0.0

  config:
    schema: analysis_config/1.0.0  # Explicit contract
    optional: true
    default:
      analysis_depth: "standard"
      include_recommendations: true
```

The friction of creating a configuration schema is **desirable friction** - it ensures runbook authors think carefully about their module's interface.

---

## Runbook Input Declarations

Child runbooks declare expected inputs in a top-level `inputs` section:

```yaml
# child_runbook.yaml
name: "Reusable Analysis Module"
description: "Analyses data for personal information"

inputs:
  source_data:
    schema: standard_input/1.0.0
    description: "Data to analyse"

  config_data:
    schema: analysis_config/1.0.0
    optional: true
    default: null
    description: "Optional configuration overrides"

  api_credentials:
    schema: credential/1.0.0
    sensitive: true
    description: "API credentials (redacted from logs)"

outputs:
  findings:
    artifact: analysis_findings
    description: "Personal data findings"

artifacts:
  validated:
    inputs: source_data
    process:
      type: validator

  analysis_findings:
    inputs: validated
    process:
      type: personal_data
```

### Input Declaration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema` | string | Yes | Schema identifier (e.g., `standard_input/1.0.0`) |
| `optional` | boolean | No | If `true`, input doesn't need to be mapped (default: `false`) |
| `default` | any | No | Default value if not mapped (requires `optional: true`) |
| `sensitive` | boolean | No | If `true`, value is redacted from logs and execution results (default: `false`) |
| `description` | string | No | Human-readable description |

### Sensitive Inputs

Inputs marked as `sensitive: true` are protected:

- **Redacted from logs**: Value replaced with `[REDACTED]` in debug output
- **Redacted from execution results**: Not included in JSON output
- **Passed normally to processors**: Processors receive the actual value

Use for credentials, API keys, or any data that shouldn't appear in logs or audit trails.

### Output Declaration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact` | string | Yes | Reference to an artifact in this runbook |
| `description` | string | No | Human-readable description |

### Constraint: No Source Artifacts

If a runbook has an `inputs` section, it **cannot** have `source` artifacts. All data must come through declared inputs. This ensures child runbooks are truly reusable and don't have hidden dependencies on external systems.

```yaml
# INVALID - has both inputs and source
inputs:
  source_data:
    schema: standard_input/1.0.0

artifacts:
  db_data:
    source:           # ERROR: Cannot have source when inputs declared
      type: mysql
```

---

## Child Runbook Directive

Parent runbooks reference children using the `child_runbook` directive:

```yaml
# parent_runbook.yaml
artifacts:
  db_schema:
    source:
      type: mysql
      properties:
        database: mydb

  child_analysis:
    inputs: db_schema
    child_runbook:
      path: ./analysis_workflow.yaml
      input_mapping:
        source_data: db_schema
      output: findings
    output: true
```

### Directive Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | Yes | Relative path to child runbook |
| `input_mapping` | object | Yes | Maps child input names to parent artifacts |
| `output` | string | Conditional | Single output artifact from child |
| `output_mapping` | object | Conditional | Multiple outputs: `{child_artifact: parent_name}` |

**Note:** Either `output` or `output_mapping` must be specified, but not both.

### Artifact with Child Runbook

When an artifact has `child_runbook`:

- It **must** have `inputs` (to provide data to child)
- It **cannot** have `source` (not a data source)
- It **cannot** have `process` (child runbook handles processing)

---

## Output Mapping

### Single Output

For child runbooks that produce one result:

```yaml
child_analysis:
  inputs: db_schema
  child_runbook:
    path: ./child.yaml
    input_mapping:
      source_data: db_schema
    output: findings  # Child's 'findings' artifact becomes 'child_analysis'
```

### Multiple Outputs

For child runbooks that produce multiple results:

```yaml
detailed_analysis:
  inputs: db_schema
  child_runbook:
    path: ./detailed.yaml
    input_mapping:
      source_data: db_schema
    output_mapping:
      findings: detail_findings    # Child artifact → parent artifact name
      summary: detail_summary      # Another mapping
      metrics: detail_metrics
```

Each mapped output creates a parent artifact that downstream artifacts can reference.

### Validation

- All outputs in `output` or `output_mapping` must exist in child's declared `outputs`
- Schema compatibility is validated (output schema flows through)

---

## Planner Flattening

### Algorithm Overview

The Planner uses an **iterative queue-based algorithm** to flatten child runbooks:

```
1. Parse parent runbook
2. Initialise queue with parent artifacts
3. While queue not empty:
   a. Dequeue artifact
   b. If has child_runbook directive:
      i.   Resolve child path (security checks)
      ii.  Check for circular references
      iii. Parse child runbook
      iv.  Validate input_mapping against child's declared inputs
      v.   Generate unique namespace for child
      vi.  Rewrite child artifacts (remap inputs, namespace IDs)
      vii. Queue child artifacts for processing
      viii. Record output aliases
   c. Else:
      Add artifact to flattened plan
4. Build DAG from flattened artifacts
5. Resolve schemas for all artifacts
6. Return ExecutionPlan with aliases
```

### Namespacing

Child artifacts are namespaced to prevent collisions:

```
Format: {runbook_name}__{unique_id}__{artifact_id}

Example:
  analysis_workflow__a1b2c3d4__findings
  analysis_workflow__a1b2c3d4__validated
```

### Input Remapping

Child artifact inputs are remapped based on `input_mapping`:

| Child References | Remapped To |
|------------------|-------------|
| Declared input (`source_data`) | Parent artifact (`db_schema`) |
| Internal artifact (`validated`) | Namespaced artifact (`analysis_workflow__a1b2c3d4__validated`) |

### Alias Resolution

The flattened plan includes an alias map:

```python
aliases = {
    "child_analysis": "analysis_workflow__a1b2c3d4__findings",
    "detail_findings": "detailed__e5f6g7h8__findings",
    "detail_summary": "detailed__e5f6g7h8__summary",
}
```

Downstream artifacts reference the alias names; the executor resolves them.

---

## Path Resolution

### Security Constraints

1. **No absolute paths** - All paths must be relative
2. **No parent traversal** - Paths cannot contain `..`
3. **Contained within tree** - Resolved path must be within allowed directories

### Search Order

1. **Parent runbook directory** - Relative to where parent runbook is located
2. **Template paths** - Configured directories for shared runbooks

### Configuration

Template paths are configured at the runbook level:

```yaml
# parent_runbook.yaml
config:
  template_paths:
    - ./templates
    - ./shared/runbooks

artifacts:
  child_analysis:
    inputs: db_schema
    child_runbook:
      path: common/analysis.yaml  # Found in template_paths
```

### Resolution Algorithm

```python
def resolve_child_path(parent_path, child_ref, template_paths):
    # 1. Reject absolute paths
    if is_absolute(child_ref):
        raise InvalidPathError("Absolute paths not allowed")

    # 2. Reject parent traversal
    if ".." in child_ref:
        raise InvalidPathError("Parent directory traversal not allowed")

    # 3. Search relative to parent
    candidate = parent_path.parent / child_ref
    if candidate.exists() and is_within(candidate, parent_path.parent):
        return candidate

    # 4. Search template paths
    for template_dir in template_paths:
        candidate = template_dir / child_ref
        if candidate.exists():
            return candidate

    raise ChildRunbookNotFoundError(f"Not found: {child_ref}")
```

---

## Validation Rules

All validation occurs at plan time:

| Rule | Error Type | Description |
|------|------------|-------------|
| Path is relative | `InvalidPathError` | No absolute paths allowed |
| No `..` in path | `InvalidPathError` | No parent directory traversal |
| Child exists | `ChildRunbookNotFoundError` | File must exist in search paths |
| No circular refs | `CircularRunbookError` | A → B → A detected |
| Required inputs mapped | `MissingInputMappingError` | All non-optional inputs need mapping |
| Schema compatible | `SchemaCompatibilityError` | Parent artifact schema matches child input |
| Output exists | `InvalidOutputMappingError` | Referenced output must exist in child |
| No source with inputs | `ValidationError` | Child with inputs cannot have source artifacts |
| Artifact type valid | `ValidationError` | Cannot combine `child_runbook` with `source` or `process` |

---

## Model Changes

### New: `RunbookInputDeclaration`

```python
class RunbookInputDeclaration(BaseModel):
    """Declares an expected input for a child runbook."""

    schema: str
    """Schema identifier (e.g., 'standard_input/1.0.0')."""

    optional: bool = False
    """If true, input doesn't need to be mapped."""

    default: Any = None
    """Default value if not mapped (requires optional=True)."""

    sensitive: bool = False
    """If true, value is redacted from logs and execution results."""

    description: str | None = None
    """Human-readable description."""

    @model_validator(mode="after")
    def validate_default_requires_optional(self) -> Self:
        if self.default is not None and not self.optional:
            raise ValueError("'default' requires 'optional: true'")
        return self
```

### New: `RunbookOutputDeclaration`

```python
class RunbookOutputDeclaration(BaseModel):
    """Declares an output that this runbook exposes."""

    artifact: str
    """Reference to an artifact in this runbook."""

    description: str | None = None
    """Human-readable description."""
```

### New: `ChildRunbookConfig`

```python
class ChildRunbookConfig(BaseModel):
    """Configuration for child runbook directive."""

    path: str
    """Relative path to child runbook file."""

    input_mapping: dict[str, str]
    """Maps child input names to parent artifact IDs."""

    output: str | None = None
    """Single output artifact from child (mutually exclusive with output_mapping)."""

    output_mapping: dict[str, str] | None = None
    """Multiple outputs: {child_artifact: parent_artifact_name}."""

    @model_validator(mode="after")
    def validate_output_config(self) -> Self:
        if self.output is None and self.output_mapping is None:
            raise ValueError("Either 'output' or 'output_mapping' required")
        if self.output is not None and self.output_mapping is not None:
            raise ValueError("Cannot specify both 'output' and 'output_mapping'")
        return self
```

### Updated: `RunbookConfig`

```python
class RunbookConfig(BaseModel):
    timeout: int = 300
    max_concurrency: int = 10
    cost_limit: float | None = None

    # NEW
    template_paths: list[str] = Field(default_factory=list)
    """Directories to search for child runbooks."""
```

### Updated: `Runbook`

```python
class Runbook(BaseModel):
    name: str
    description: str
    contact: str | None = None
    config: RunbookConfig = Field(default_factory=RunbookConfig)

    # NEW
    inputs: dict[str, RunbookInputDeclaration] | None = None
    """Declared inputs (makes this a child runbook)."""

    # NEW
    outputs: dict[str, RunbookOutputDeclaration] | None = None
    """Declared outputs (what this runbook exposes)."""

    artifacts: dict[str, ArtifactDefinition]

    @model_validator(mode="after")
    def validate_child_runbook_constraints(self) -> Self:
        if self.inputs:
            for artifact_id, artifact in self.artifacts.items():
                if artifact.source is not None:
                    raise ValueError(
                        f"Runbook with inputs cannot have source artifacts. "
                        f"Found source in '{artifact_id}'."
                    )
        return self

    @model_validator(mode="after")
    def validate_outputs_reference_artifacts(self) -> Self:
        if self.outputs:
            for output_name, output_decl in self.outputs.items():
                if output_decl.artifact not in self.artifacts:
                    raise ValueError(
                        f"Output '{output_name}' references non-existent "
                        f"artifact '{output_decl.artifact}'."
                    )
        return self
```

### Updated: `ArtifactDefinition`

```python
class ArtifactDefinition(BaseModel):
    name: str | None = None
    description: str | None = None
    contact: str | None = None

    source: SourceConfig | None = None
    inputs: str | list[str] | None = None
    process: ProcessConfig | None = None
    merge: Literal["concatenate"] = "concatenate"

    # NEW
    child_runbook: ChildRunbookConfig | None = None
    """Child runbook directive for composition."""

    output: bool = False
    optional: bool = False
    output_schema: str | None = None

    @model_validator(mode="after")
    def validate_artifact_type(self) -> Self:
        has_source = self.source is not None
        has_child = self.child_runbook is not None
        has_inputs = self.inputs is not None

        if has_child:
            if has_source:
                raise ValueError("Cannot combine 'child_runbook' with 'source'")
            if self.process is not None:
                raise ValueError("Cannot combine 'child_runbook' with 'process'")
            if not has_inputs:
                raise ValueError("'child_runbook' requires 'inputs'")

        return self
```

### Updated: `ArtifactResult`

```python
class ArtifactResult(BaseModel):
    artifact_id: str
    success: bool
    message: Message | None = None
    error: str | None = None
    duration_seconds: float

    # NEW
    origin: str = "parent"
    """Origin of artifact: 'parent' or 'child:{runbook_name}'."""

    alias: str | None = None
    """Parent artifact name if this is an aliased child artifact."""
```

### Updated: `ExecutionPlan`

```python
@dataclass(frozen=True)
class ExecutionPlan:
    runbook: Runbook
    dag: ExecutionDAG
    artifact_schemas: dict[str, tuple[Schema | None, Schema]]

    # NEW
    aliases: dict[str, str] = field(default_factory=dict)
    """Maps parent artifact names to namespaced child artifacts."""
```

---

## Execution Results

Execution results include full visibility into flattened artifacts:

```json
{
  "run_id": "abc123",
  "start_timestamp": "2025-01-15T10:30:00Z",
  "total_duration_seconds": 5.3,
  "artifacts": {
    "db_schema": {
      "artifact_id": "db_schema",
      "success": true,
      "origin": "parent",
      "alias": null,
      "duration_seconds": 1.2
    },
    "analysis_workflow__a1b2c3d4__validated": {
      "artifact_id": "analysis_workflow__a1b2c3d4__validated",
      "success": true,
      "origin": "child:analysis_workflow",
      "alias": null,
      "duration_seconds": 0.8
    },
    "analysis_workflow__a1b2c3d4__findings": {
      "artifact_id": "analysis_workflow__a1b2c3d4__findings",
      "success": true,
      "origin": "child:analysis_workflow",
      "alias": "child_analysis",
      "duration_seconds": 2.1
    }
  },
  "skipped": []
}
```

### Benefits of Full Visibility

- **Debugging**: See exactly which artifact failed
- **Auditing**: Complete trace of execution
- **Performance analysis**: Timing for each artifact
- **Understanding**: Learn how composition works

---

## Terraform-Style Extensions

The design supports Terraform-inspired patterns for reusable infrastructure:

### Current Support

| Terraform Concept | WCF Equivalent | Status |
|-------------------|----------------|--------|
| Variables | `inputs` section | ✅ Included |
| Variable types | `schema` field | ✅ Included |
| Optional variables | `optional` field | ✅ Included |
| Default values | `default` field | ✅ Included |
| Sensitive variables | `sensitive` field | ✅ Included |
| Variable descriptions | `description` field | ✅ Included |
| Resources | `artifacts` section | ✅ Existing |
| Outputs | `outputs` section | ✅ Included |
| Output descriptions | `description` field | ✅ Included |

### Future Extensions (Deferred)

| Terraform Concept | Description | Complexity |
|-------------------|-------------|------------|
| Variable interpolation | `${inputs.foo}` syntax in properties | High |
| Validation rules | Custom validation beyond schema | Medium |
| Local values | Computed intermediate values | Medium |
| Data sources | Read-only external data | Medium |

### Example: Full Terraform-Style Runbook

```yaml
name: "GDPR Analysis Module"
description: "Reusable GDPR compliance analysis"

inputs:
  source_data:
    schema: standard_input/1.0.0
    description: "Data to analyse for GDPR compliance"

  analysis_depth:
    schema: analysis_config/1.0.0
    optional: true
    default:
      level: "standard"
      include_recommendations: true
    description: "Analysis configuration (defaults to standard depth)"

  compliance_frameworks:
    schema: framework_list/1.0.0
    optional: true
    default:
      frameworks: ["GDPR", "UK_GDPR"]
    description: "Which frameworks to check against"

outputs:
  findings:
    artifact: gdpr_findings
    description: "Personal data findings with GDPR context"

  summary:
    artifact: analysis_summary
    description: "Executive summary of compliance status"

artifacts:
  validated:
    inputs: source_data
    process:
      type: validator

  gdpr_findings:
    inputs: validated
    process:
      type: personal_data

  analysis_summary:
    inputs: gdpr_findings
    process:
      type: summariser
```

---

## Examples

### Example 1: Simple Composition

**Parent:**

```yaml
name: "Database Analysis"
artifacts:
  db_schema:
    source:
      type: mysql
      properties:
        database: production

  analysis:
    inputs: db_schema
    child_runbook:
      path: ./personal_data_analysis.yaml
      input_mapping:
        source_data: db_schema
      output: findings
    output: true
```

**Child:**

```yaml
name: "Personal Data Analysis"
inputs:
  source_data:
    schema: standard_input/1.0.0

outputs:
  findings:
    artifact: personal_data_findings

artifacts:
  personal_data_findings:
    inputs: source_data
    process:
      type: personal_data
```

### Example 2: Multiple Outputs

**Parent:**

```yaml
name: "Comprehensive Analysis"
artifacts:
  db_schema:
    source:
      type: mysql

  detailed:
    inputs: db_schema
    child_runbook:
      path: ./comprehensive.yaml
      input_mapping:
        source_data: db_schema
      output_mapping:
        personal_data: personal_findings
        data_subjects: subject_findings
        purposes: purpose_findings

  final_report:
    inputs:
      - personal_findings
      - subject_findings
      - purpose_findings
    process:
      type: report_generator
    output: true
```

### Example 3: Nested Composition

**Parent:**

```yaml
name: "Full Compliance Suite"
artifacts:
  db_schema:
    source:
      type: mysql

  gdpr_analysis:
    inputs: db_schema
    child_runbook:
      path: ./gdpr_suite.yaml
      input_mapping:
        source_data: db_schema
      output: compliance_report
    output: true
```

**Child (gdpr_suite.yaml):**

```yaml
name: "GDPR Suite"
inputs:
  source_data:
    schema: standard_input/1.0.0

outputs:
  compliance_report:
    artifact: final_report

artifacts:
  personal_data:
    inputs: source_data
    child_runbook:
      path: ./personal_data_analysis.yaml
      input_mapping:
        source_data: source_data
      output: findings

  data_subjects:
    inputs: source_data
    child_runbook:
      path: ./data_subject_analysis.yaml
      input_mapping:
        source_data: source_data
      output: findings

  final_report:
    inputs:
      - personal_data
      - data_subjects
    process:
      type: gdpr_report_generator
```

**Grandchild (personal_data_analysis.yaml):**

```yaml
name: "Personal Data Analysis"
inputs:
  source_data:
    schema: standard_input/1.0.0

outputs:
  findings:
    artifact: analysis_results

artifacts:
  analysis_results:
    inputs: source_data
    process:
      type: personal_data
```

### Flattened Result

The nested example flattens to:

```
Artifacts:
├── db_schema (source: mysql)
├── gdpr_suite__abc__personal_data_analysis__xyz__analysis_results
├── gdpr_suite__abc__data_subject_analysis__uvw__analysis_results
└── gdpr_suite__abc__final_report

Aliases:
├── gdpr_analysis → gdpr_suite__abc__final_report
├── gdpr_suite__abc__personal_data → gdpr_suite__abc__personal_data_analysis__xyz__analysis_results
└── gdpr_suite__abc__data_subjects → gdpr_suite__abc__data_subject_analysis__uvw__analysis_results
```

---

## Implementation Plan

### Phase 1: Model Changes

1. Add `RunbookInputDeclaration` model
2. Add `RunbookOutputDeclaration` model
3. Add `ChildRunbookConfig` model
4. Update `RunbookConfig` with `template_paths`
5. Update `Runbook` with `inputs` and `outputs`
6. Update `ArtifactDefinition` with `child_runbook`
7. Update `ArtifactResult` with `origin` and `alias`
8. Update `ExecutionPlan` with `aliases`
9. Add validation rules to models

### Phase 2: Path Resolution

1. Implement path security checks
2. Implement template path search
3. Add `template_paths` to configuration
4. Unit tests for path resolution

### Phase 3: Planner Flattening

1. Implement circular reference detection
2. Implement iterative flattening algorithm
3. Implement input remapping
4. Implement namespace generation
5. Implement alias recording
6. Implement schema validation for input mapping
7. Update `Planner.plan()` to call flattening
8. Comprehensive tests for flattening

### Phase 4: Executor Updates

1. Add origin tracking to `ArtifactResult`
2. Add alias lookup for results
3. Update result formatting

### Phase 5: Integration & Documentation

1. End-to-end integration tests
2. Sample runbooks demonstrating composition
3. User documentation
4. Update CLAUDE.md with new patterns

---

## Future Considerations

### Use Case 1 Support (Processor-Driven)

When implementing Use Case 1:

- Inject Planner and Executor into processor factories via ServiceContainer
- Create `ExecutionContext` to pass resource limits (timeout, cost)
- Processors return standard `Message`, hiding internal runbook execution

### Variable Interpolation

If needed in future:

```yaml
artifacts:
  configured_analysis:
    inputs: source_data
    process:
      type: analyser
      properties:
        depth: ${inputs.analysis_depth.level}  # Future syntax
```

This requires:

- Expression parser
- Variable resolution during flattening
- Type coercion rules

### Runbook Registry

For larger deployments:

- Central registry of reusable runbooks
- Version management for child runbooks
- Dependency resolution (like package managers)

---

## References

- [Multi-Schema Fan-In](../../../future-plans/multi-schema-fan-in.md)
- [Artifact-Centric Orchestration Overview](./README.md)
- [WCF Core Components](../../../core-concepts/wcf-core-components.md)
