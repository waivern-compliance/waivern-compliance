# Child Runbook Composition

This document explains the child runbook composition feature in waivern-orchestration, which enables modular, reusable runbook design through plan-time flattening.

## Table of Contents

1. [Overview](#overview)
2. [Use Cases](#use-cases)
3. [Design Principles](#design-principles)
4. [User Guide](#user-guide)
   - [Declaring Inputs and Outputs](#declaring-inputs-and-outputs)
   - [Using the Child Runbook Directive](#using-the-child-runbook-directive)
   - [Output Mapping](#output-mapping)
   - [Template Paths](#template-paths)
5. [Technical Reference](#technical-reference)
   - [Flattening Algorithm](#flattening-algorithm)
   - [Namespacing](#namespacing)
   - [Alias Resolution](#alias-resolution)
   - [Path Resolution](#path-resolution)
   - [Validation Rules](#validation-rules)
   - [Model Reference](#model-reference)
6. [Examples](#examples)
7. [Execution Results](#execution-results)
8. [Future Considerations](#future-considerations)

---

## Overview

### Problem

Complex compliance workflows often need to:

- Compose runbooks from smaller, reusable runbooks
- Share common analysis patterns across projects
- Enable modular, maintainable runbook design

Without composition, users must duplicate YAML configurations across runbooks, leading to maintenance burden and inconsistency.

### Solution

Child runbook composition enables **runbook modularity** through plan-time flattening. Child runbooks are parameterised modules that the Planner inlines into the parent's execution plan.

### Key Insight

This is **not** a separate execution mode. The Planner flattens child runbooks at plan time, producing a single `ExecutionPlan` with a unified DAG. The Executor remains unchanged—it simply executes the flattened plan without knowing about the original composition structure.

```
┌─────────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Parent Runbook │────▶│   Planner   │────▶│  Flattened DAG   │
│  + Child Refs   │     │ (flattens)  │     │  (unified plan)  │
└─────────────────┘     └─────────────┘     └────────┬─────────┘
                                                     │
                                                     ▼
                                            ┌──────────────────┐
                                            │    Executor      │
                                            │ (no composition  │
                                            │   awareness)     │
                                            └──────────────────┘
```

---

## Use Cases

### Reusable Analysis Modules

Create standardised analysis patterns that can be shared across projects:

```yaml
# shared/personal_data_analysis.yaml
name: "Personal Data Analysis Module"
inputs:
  source_data:
    input_schema: standard_input/1.0.0

outputs:
  findings:
    artifact: analysis_results

artifacts:
  analysis_results:
    inputs: source_data
    process:
      type: personal_data
```

This module can be used by any parent runbook that produces `standard_input/1.0.0` data.

### Multi-Database Analysis

Analyse multiple databases using the same analysis pattern:

```yaml
# parent_runbook.yaml
artifacts:
  mysql_data:
    source:
      type: mysql
      properties:
        database: production

  postgres_data:
    source:
      type: postgres
      properties:
        database: analytics

  mysql_analysis:
    inputs: mysql_data
    child_runbook:
      path: ./shared/analysis.yaml
      input_mapping:
        source_data: mysql_data
      output: findings

  postgres_analysis:
    inputs: postgres_data
    child_runbook:
      path: ./shared/analysis.yaml
      input_mapping:
        source_data: postgres_data
      output: findings
```

### Nested Composition

Build complex workflows from smaller building blocks:

```
Full Compliance Suite
├── GDPR Analysis (child)
│   ├── Personal Data (grandchild)
│   └── Data Subjects (grandchild)
└── Security Analysis (child)
    └── Vulnerability Scan (grandchild)
```

---

## Design Principles

### 1. Plan-Time Flattening

All child runbook resolution happens in the Planner. The Executor receives a flat DAG and executes it without knowing about the original composition structure. This keeps the execution model simple.

### 2. Schema as Contract

Child runbooks declare their inputs using schemas—the shared, unambiguous language between WCF components. Schema compatibility is validated at plan time, catching mismatches before execution.

### 3. No Scoped Artifact Store

Since flattening produces a single DAG, all artifacts live in one ArtifactStore. No need for nested scopes or complex isolation mechanisms.

### 4. Security by Default

Child runbook paths are restricted:
- No absolute paths
- No parent directory traversal (`..`)
- Search limited to parent directory and configured template paths

### 5. Explicit Over Implicit

- All required inputs must be explicitly mapped
- Outputs must be explicitly declared
- No magic conventions or hidden behaviour

### 6. Configuration as Schema-Validated Input

Configuration values (paths, options, credentials) are passed as schema-validated input artifacts, not loose key-value pairs.

**Rationale:** Child runbooks should be well-considered compliance modules, not copy-paste YAML snippets. Schema-validated configuration reinforces this by:

1. **Forcing deliberate interface design**—Authors must think about what configuration their module needs
2. **Providing type safety**—Catch misconfigurations at plan time, not runtime
3. **Enabling self-documentation**—The schema documents expected configuration
4. **Supporting audit trails**—Clear, typed data contracts for compliance records

---

## User Guide

### Declaring Inputs and Outputs

Child runbooks declare expected inputs and exposed outputs at the top level:

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

#### Input Declaration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `input_schema` | string | Yes | Schema identifier (e.g., `standard_input/1.0.0`) |
| `optional` | boolean | No | If `true`, input doesn't need to be mapped (default: `false`) |
| `default` | any | No | Default value if not mapped (requires `optional: true`) |
| `sensitive` | boolean | No | If `true`, value is redacted from logs and results (default: `false`) |
| `description` | string | No | Human-readable description |

#### Output Declaration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `artifact` | string | Yes | Reference to an artifact in this runbook |
| `description` | string | No | Human-readable description |

#### Sensitive Inputs

Inputs marked as `sensitive: true` are protected:

- **Redacted from logs**: Value replaced with `[REDACTED]` in debug output
- **Redacted from execution results**: Not included in JSON output
- **Passed normally to processors**: Processors receive the actual value

Use for credentials, API keys, or any data that shouldn't appear in logs or audit trails.

#### Constraint: No Source Artifacts

If a runbook has an `inputs` section, it **cannot** have `source` artifacts. All data must come through declared inputs. This ensures child runbooks are truly reusable and don't have hidden dependencies on external systems.

```yaml
# INVALID - has both inputs and source
inputs:
  source_data:
    input_schema: standard_input/1.0.0

artifacts:
  db_data:
    source:           # ERROR: Cannot have source when inputs declared
      type: mysql
```

### Using the Child Runbook Directive

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

#### Directive Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | Yes | Relative path to child runbook |
| `input_mapping` | object | Yes | Maps child input names to parent artifacts |
| `output` | string | Conditional | Single output artifact from child |
| `output_mapping` | object | Conditional | Multiple outputs: `{child_output: parent_name}` |

**Note:** Either `output` or `output_mapping` must be specified, but not both.

#### Artifact Constraints

When an artifact has `child_runbook`:

- It **must** have `inputs` (to provide data to child)
- It **cannot** have `source` (not a data source)
- It **cannot** have `process` (child runbook handles processing)

### Output Mapping

#### Single Output

For child runbooks that produce one result:

```yaml
child_analysis:
  inputs: db_schema
  child_runbook:
    path: ./child.yaml
    input_mapping:
      source_data: db_schema
    output: findings  # Child's 'findings' output becomes 'child_analysis'
```

#### Multiple Outputs

For child runbooks that produce multiple results:

```yaml
detailed_analysis:
  inputs: db_schema
  child_runbook:
    path: ./detailed.yaml
    input_mapping:
      source_data: db_schema
    output_mapping:
      findings: detail_findings    # Child output → parent artifact name
      summary: detail_summary
      metrics: detail_metrics
```

Each mapped output creates a parent artifact that downstream artifacts can reference.

### Template Paths

Configure directories where shared runbooks are stored:

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
      input_mapping:
        source_data: db_schema
      output: findings
```

The Planner searches for child runbooks in this order:
1. Parent runbook directory (relative paths)
2. Configured template paths

---

## Technical Reference

### Flattening Algorithm

The Planner uses an iterative queue-based algorithm:

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

The iterative approach (vs. recursive) handles arbitrary nesting depth without stack overflow concerns.

### Namespacing

Child artifacts are namespaced to prevent collisions when the same child runbook is used multiple times or when different runbooks have artifacts with the same name:

```
Format: {runbook_name}__{unique_id}__{artifact_id}

Example:
  analysis_workflow__a1b2c3d4__findings
  analysis_workflow__a1b2c3d4__validated
```

The namespace consists of:
- Sanitised runbook name (spaces/hyphens converted to underscores, lowercased)
- 8-character UUID for uniqueness
- Original artifact ID

### Alias Resolution

The flattened plan maintains an alias map that connects parent artifact names to namespaced child artifacts:

```python
aliases = {
    "child_analysis": "analysis_workflow__a1b2c3d4__findings",
    "detail_findings": "detailed__e5f6g7h8__findings",
    "detail_summary": "detailed__e5f6g7h8__summary",
}
```

Downstream artifacts reference the alias names; the Executor resolves them when looking up dependencies.

### Path Resolution

#### Security Constraints

1. **No absolute paths**—All paths must be relative
2. **No parent traversal**—Paths cannot contain `..`
3. **Contained within tree**—Resolved path must be within allowed directories

#### Search Order

1. **Parent runbook directory**—Relative to where parent runbook is located
2. **Template paths**—Configured directories for shared runbooks

#### Resolution Algorithm

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

### Validation Rules

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

### Model Reference

#### RunbookInputDeclaration

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

#### RunbookOutputDeclaration

```python
class RunbookOutputDeclaration(BaseModel):
    """Declares an output that this runbook exposes."""

    artifact: str
    """Reference to an artifact in this runbook."""

    description: str | None = None
    """Human-readable description."""
```

#### ChildRunbookConfig

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
    """Multiple outputs: {child_output: parent_artifact_name}."""
```

#### ExecutionPlan

```python
@dataclass(frozen=True)
class ExecutionPlan:
    runbook: Runbook
    dag: ExecutionDAG
    artifact_schemas: dict[str, tuple[Schema | None, Schema]]
    aliases: dict[str, str] = field(default_factory=dict)
    """Maps parent artifact names to namespaced child artifacts."""
    reversed_aliases: dict[str, str] = field(default_factory=dict)
    """Maps artifact IDs to alias names (reverse of aliases)."""
```

#### ArtifactResult

```python
class ArtifactResult(BaseModel):
    artifact_id: str
    success: bool
    message: Message | None = None
    error: str | None = None
    duration_seconds: float
    origin: str = "parent"
    """Origin of artifact: 'parent' or 'child:{runbook_name}'."""
    alias: str | None = None
    """Parent artifact name if this is an aliased child artifact."""
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

## Execution Results

Execution results provide full visibility into flattened artifacts:

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

## Future Considerations

### Variable Interpolation

If needed in future, expressions could allow dynamic configuration:

```yaml
artifacts:
  configured_analysis:
    inputs: source_data
    process:
      type: analyser
      properties:
        depth: ${inputs.analysis_depth.level}  # Potential future syntax
```

This would require:
- Expression parser
- Variable resolution during flattening
- Type coercion rules

### Runbook Registry

For larger deployments:
- Central registry of reusable runbooks
- Version management for child runbooks
- Dependency resolution (like package managers)

### Processor-Driven Dynamic Execution

A future use case where Processors internally generate and execute child runbooks. The parent runbook would be unaware of this—it simply invokes a Processor and receives results. This requires injecting Planner and Executor into processor factories via dependency injection.
