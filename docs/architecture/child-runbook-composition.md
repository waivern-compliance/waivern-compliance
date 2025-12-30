# Child Runbook Composition

- **Status:** Implemented
- **Last Updated:** 2025-12-30
- **Related:** [Artifact-Centric Orchestration](artifact-centric-orchestration.md)

## Overview

Child runbook composition enables modular, reusable compliance workflows through plan-time flattening. Child runbooks are parameterised modules that the Planner inlines into the parent's execution plan.

**Key insight:** This is not a new execution mode. The Planner flattens child runbooks at plan time, producing a single `ExecutionPlan` with a unified DAG. The Executor remains unchanged—it simply executes the flattened plan.

---

## Design Principles

### 1. Plan-Time Flattening

All child runbook resolution happens in the Planner. The Executor receives a flat DAG and executes it without knowing about the original composition structure.

### 2. Schema as Contract

Child runbooks declare their inputs using schemas—the shared, unambiguous language between WCF components. Schema compatibility is validated at plan time.

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

The friction of creating a configuration schema is **desirable friction**—it ensures runbook authors think carefully about their module's interface.

---

## Runbook Input Declarations

Child runbooks declare expected inputs in a top-level `inputs` section:

```yaml
# child_runbook.yaml
name: "Reusable Analysis Module"
description: "Analyses data for personal information"

inputs:
  source_data:
    input_schema: standard_input/1.0.0
    description: "Data to analyse"

  config_data:
    input_schema: analysis_config/1.0.0
    optional: true
    default: null
    description: "Optional configuration overrides"

  api_credentials:
    input_schema: credential/1.0.0
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
| `input_schema` | string | Yes | Schema identifier (e.g., `standard_input/1.0.0`) |
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

## Data Models

### RunbookInputDeclaration

```python
class RunbookInputDeclaration(BaseModel):
    """Declares an expected input for a child runbook."""

    input_schema: str
    """Schema identifier (e.g., 'standard_input/1.0.0')."""

    optional: bool = False
    """If true, input doesn't need to be mapped."""

    default: Any = None
    """Default value if not mapped (requires optional=True)."""

    sensitive: bool = False
    """If true, value is redacted from logs and execution results."""

    description: str | None = None
    """Human-readable description."""
```

### RunbookOutputDeclaration

```python
class RunbookOutputDeclaration(BaseModel):
    """Declares an output that this runbook exposes."""

    artifact: str
    """Reference to an artifact in this runbook."""

    description: str | None = None
    """Human-readable description."""
```

### ChildRunbookConfig

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
```

### ExecutionContext in Message

Execution metadata is stored in `Message.extensions.execution`:

```python
@dataclass
class ExecutionContext:
    status: Literal["pending", "success", "error"]
    error: str | None = None
    duration_seconds: float | None = None
    origin: str = "parent"  # "parent" or "child:{runbook_name}"
    alias: str | None = None  # Parent artifact name for aliased child artifacts
```

Access via convenience properties: `message.is_success`, `message.execution_origin`, `message.execution_alias`.

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
    input_schema: standard_input/1.0.0

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

Child runbooks can reference other child runbooks, enabling deep composition:

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
    input_schema: standard_input/1.0.0

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

## Future Considerations

### Variable Interpolation

```yaml
artifacts:
  configured_analysis:
    inputs: source_data
    process:
      type: analyser
      properties:
        depth: ${inputs.analysis_depth.level}  # Future syntax
```

This would require an expression parser and variable resolution during flattening.

### Runbook Registry

For larger deployments:

- Central registry of reusable runbooks
- Version management for child runbooks
- Dependency resolution (like package managers)

---

## Related Documentation

- [Artifact-Centric Orchestration](artifact-centric-orchestration.md) - Parent architecture document
- [Child Runbook User Guide](../../libs/waivern-orchestration/docs/child-runbook-composition.md) - How to use child runbooks
- [WCF Core Components](../core-concepts/wcf-core-components.md) - Core framework concepts
