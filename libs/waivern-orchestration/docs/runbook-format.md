# Artifact-Centric Runbook Format

This document describes the artifact-centric runbook format used by waivern-orchestration for defining compliance analysis workflows.

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [Runbook Structure](#runbook-structure)
4. [Artifact Types](#artifact-types)
   - [Source Artifacts](#source-artifacts)
   - [Derived Artifacts](#derived-artifacts)
   - [Reused Artifacts](#reused-artifacts)
   - [Fan-In Artifacts](#fan-in-artifacts)
5. [Configuration](#configuration)
6. [DAG Execution Model](#dag-execution-model)
7. [Error Handling](#error-handling)
8. [Model Reference](#model-reference)
9. [Examples](#examples)

---

## Overview

### Problem

Traditional workflow formats often separate component definitions from execution flow, leading to:

- **Redundant structure**—Components defined separately but typically used once
- **Component-centric focus**—Describes "what runs" rather than "what data flows"
- **Implicit dependencies**—Hidden relationships between steps
- **Verbose configuration**—Multiple sections to express simple pipelines

### Solution

The artifact-centric runbook format treats **data artifacts as first-class citizens**. Transformations are edges between artifacts, and the execution DAG emerges naturally from declared dependencies.

### Key Insight

The natural unit of compliance analysis is the **artifact** (data), not the component. Compliance workflows are about:

- **Extracting data** → producing artifacts
- **Transforming data** → deriving new artifacts from existing ones
- **Exporting results** → marking artifacts for output

```
Runbook (YAML) → Planner → DAGExecutor → Connector/Processor → Findings (JSON)
```

---

## Design Principles

### 1. Artifacts Are Nodes, Transformations Are Edges

```yaml
artifacts:
  db_schema: # Node: data source
    source:
      type: mysql

  findings: # Node: derived data
    inputs: db_schema # Edge: depends on db_schema
    process:
      type: personal_data
```

### 2. Implicit DAG

Dependencies declared via `inputs` fields automatically form the execution DAG. No explicit ordering required.

### 3. Parallel by Default

Independent artifacts execute concurrently. The executor maximises parallelism while respecting dependencies.

### 4. Schema-Driven Validation

All data exchange uses schema-validated Messages. The Planner validates schema compatibility at plan time, catching mismatches before execution.

### 5. Explicit Output Declaration

Only artifacts marked with `output: true` are included in final results. This keeps outputs focused and intentional.

---

## Runbook Structure

```yaml
name: "Runbook Name" # Required: Human-readable name
description: "What this does" # Required: Description
contact: "team@company.com" # Optional: Responsible party

config: # Optional: Execution settings
  timeout: 3600 # Total execution timeout (seconds)
  cost_limit: 50.0 # LLM cost budget
  max_concurrency: 10 # Max parallel artifacts

artifacts: # Required: Artifact definitions
  <artifact_id>:
    # ... artifact definition
```

### Top-Level Fields

| Field         | Type   | Required | Description                          |
| ------------- | ------ | -------- | ------------------------------------ |
| `name`        | string | Yes      | Human-readable runbook name          |
| `description` | string | Yes      | What this runbook does               |
| `contact`     | string | No       | Responsible party (email, team name) |
| `config`      | object | No       | Execution configuration              |
| `artifacts`   | object | Yes      | Map of artifact ID → definition      |

---

## Artifact Types

### Source Artifacts

Source artifacts extract data from external systems using connectors.

```yaml
artifacts:
  db_schema:
    name: "Database Schema" # Optional: display name
    description: "MySQL production" # Optional: description
    source:
      type: mysql # Connector type
      properties: # Connector configuration
        host: "${MYSQL_HOST}"
        database: "${MYSQL_DATABASE}"
```

#### Source Configuration

| Field        | Type   | Required | Description                                  |
| ------------ | ------ | -------- | -------------------------------------------- |
| `type`       | string | Yes      | Connector type (e.g., `mysql`, `filesystem`) |
| `properties` | object | No       | Connector-specific configuration             |

#### Available Connectors

| Type          | Description       | Key Properties                                 |
| ------------- | ----------------- | ---------------------------------------------- |
| `mysql`       | MySQL database    | `host`, `port`, `database`, `user`, `password` |
| `sqlite`      | SQLite database   | `database_path`                                |
| `filesystem`  | File system       | `path`, `pattern`, `recursive`                 |
| `source_code` | Source code (PHP) | `path`, `extensions`                           |

### Derived Artifacts

Derived artifacts transform data from other artifacts using processors.

```yaml
artifacts:
  findings:
    inputs: db_schema # Reference to upstream artifact
    process:
      type: personal_data # Processor type
      properties: # Processor configuration
        pattern_matching:
          ruleset: "local/personal_data/1.0.0"
        llm_validation:
          enable_llm_validation: true
    output: true # Include in final results
```

#### Derived Artifact Fields

| Field      | Type           | Required | Description                                 |
| ---------- | -------------- | -------- | ------------------------------------------- |
| `inputs`   | string \| list | Yes      | Upstream artifact(s)                        |
| `process`  | object         | Yes      | Processor configuration                     |
| `merge`    | string         | No       | Merge strategy (`concatenate`)              |
| `output`   | boolean        | No       | Include in results (default: false)         |
| `optional` | boolean        | No       | Skip dependents on failure (default: false) |

#### Process Configuration

| Field        | Type   | Required | Description                            |
| ------------ | ------ | -------- | -------------------------------------- |
| `type`       | string | Yes      | Processor type (e.g., `personal_data`) |
| `properties` | object | No       | Processor-specific configuration       |

### Reused Artifacts

Reused artifacts copy data from a previous run instead of re-executing. This is useful for:

- **Iterative development** - Reuse expensive connector extractions while iterating on analysis
- **Cost optimisation** - Skip LLM-intensive processing when upstream data hasn't changed
- **Workflow composition** - Build on results from previous analyses

```yaml
artifacts:
  # Reuse source data from a previous run
  db_schema:
    reuse:
      from_run: "550e8400-e29b-41d4-a716-446655440000" # Run ID (UUID)
      artifact: "db_schema" # Artifact to copy

  # Process the reused data normally
  findings:
    inputs: db_schema
    process:
      type: personal_data
    output: true
```

#### Reuse Configuration

| Field      | Type   | Required | Description                   |
| ---------- | ------ | -------- | ----------------------------- |
| `from_run` | string | Yes      | Run ID (UUID) to copy from    |
| `artifact` | string | Yes      | Artifact ID in the source run |

#### Behaviour

- **Copy semantics** - The artifact is copied into the new run (not referenced)
- **Mutually exclusive** - Cannot combine `reuse` with `source` or `inputs`
- **Validation** - Fails fast if the source run or artifact doesn't exist

### Fan-In Artifacts

Fan-in artifacts combine multiple upstream artifacts. The processor receives all inputs and processes them together.

```yaml
artifacts:
  mysql_findings:
    inputs: mysql_schema
    process:
      type: personal_data

  file_findings:
    inputs: file_content
    process:
      type: personal_data

  combined_findings:
    inputs: # List of upstream artifacts
      - mysql_findings
      - file_findings
    merge: concatenate # Merge strategy
    process:
      type: findings_aggregator
    output: true
```

#### Same-Schema Fan-In

When multiple artifacts produce the same schema, they can be merged and processed together:

```yaml
combined:
  inputs:
    - mysql_findings # personal_data_finding schema
    - postgres_findings # personal_data_finding schema
  process:
    type: summary_generator
```

The processor receives all findings combined into a single list.

#### Multi-Schema Fan-In

When artifacts have different schemas, the processor must declare support for the combination:

```yaml
gdpr_report:
  inputs:
    - personal_data_findings # personal_data_finding schema
    - processing_purposes # processing_purpose_finding schema
  process:
    type: gdpr_article_30
```

See [Processor Input Requirements](../../waivern-core/docs/processor-input-requirements.md) for details on multi-schema support.

---

## Configuration

### RunbookConfig

```yaml
config:
  timeout: 3600 # Execution timeout in seconds
  cost_limit: 50.0 # Maximum LLM cost (API charges)
  max_concurrency: 10 # Maximum parallel artifacts
  template_paths: # Directories for child runbooks
    - ./templates
    - ./shared
```

| Field             | Type    | Default | Description                       |
| ----------------- | ------- | ------- | --------------------------------- |
| `timeout`         | integer | None    | Total execution timeout (seconds) |
| `cost_limit`      | float   | None    | Maximum LLM API cost              |
| `max_concurrency` | integer | 10      | Max parallel artifact execution   |
| `template_paths`  | list    | []      | Search paths for child runbooks   |

### Environment Variable Substitution

Properties support environment variable substitution using `${VAR_NAME}` syntax:

```yaml
source:
  type: mysql
  properties:
    host: "${MYSQL_HOST}" # From environment
    port: "${MYSQL_PORT:-3306}" # With default value
    database: "${DB_NAME}"
```

---

## DAG Execution Model

### How It Works

```
1. Planner parses runbook YAML
2. Planner builds ExecutionDAG from `inputs` relationships
3. Planner validates schemas (connectors → processors compatibility)
4. DAGExecutor runs artifacts using TopologicalSorter
5. Independent artifacts execute in parallel
6. Dependent artifacts wait for inputs
7. Results saved to ArtifactStore
```

### Execution Flow

```
     db_schema          log_content
     (source)           (source)
         │                   │
         ▼                   ▼
    db_findings        log_findings
         │                   │
         └───────┬───────────┘
                 ▼
        combined_findings
                 │
                 ▼
          final_report
          (output: true)
```

In this example:

- `db_schema` and `log_content` run in parallel (no dependencies)
- `db_findings` and `log_findings` run in parallel after their sources
- `combined_findings` waits for both findings
- `final_report` runs last

### Parallel Execution

The executor uses `asyncio` with `graphlib.TopologicalSorter`:

```python
while sorter.is_active():
    ready = sorter.get_ready()           # Get artifacts with no pending deps
    await asyncio.gather(*[              # Execute in parallel
        produce(artifact_id) for artifact_id in ready
    ])
    for artifact_id in ready:
        sorter.done(artifact_id)         # Mark complete
```

---

## Error Handling

### Default Behaviour

When an artifact fails, all dependent artifacts are skipped.

### Optional Artifacts

Use `optional: true` for non-critical artifacts:

```yaml
llm_enriched:
  inputs: findings
  process:
    type: llm_enricher
  optional: true # Skip dependents on failure, continue pipeline
```

When an `optional: true` artifact fails:

1. Warning logged
2. Artifact marked as failed in results
3. All dependents skipped
4. Independent branches continue

### Execution Result

```json
{
  "run_id": "abc123",
  "total_duration_seconds": 12.5,
  "artifacts": {
    "db_schema": {"success": true, ...},
    "findings": {"success": true, ...},
    "enriched": {"success": false, "error": "LLM unavailable"}
  },
  "skipped": ["report"]
}
```

---

## Model Reference

### Runbook

```python
class Runbook(BaseModel):
    name: str
    description: str
    contact: str | None = None
    config: RunbookConfig = Field(default_factory=RunbookConfig)
    artifacts: dict[str, ArtifactDefinition]
```

### ArtifactDefinition

```python
class ArtifactDefinition(BaseModel):
    # Metadata
    name: str | None = None
    description: str | None = None
    contact: str | None = None

    # Production method (mutually exclusive: exactly one required)
    source: SourceConfig | None = None      # Extract from connector
    inputs: str | list[str] | None = None   # Transform from other artifacts
    reuse: ReuseConfig | None = None        # Copy from previous run

    # Processing
    process: ProcessConfig | None = None
    merge: Literal["concatenate"] = "concatenate"
    child_runbook: ChildRunbookConfig | None = None

    # Schema override
    output_schema: str | None = None

    # Behaviour
    output: bool = False
    optional: bool = False
```

### SourceConfig

```python
class SourceConfig(BaseModel):
    type: str
    properties: dict[str, Any] = {}
```

### ProcessConfig

```python
class ProcessConfig(BaseModel):
    type: str
    properties: dict[str, Any] = {}
```

### ReuseConfig

```python
class ReuseConfig(BaseModel):
    from_run: str   # Run ID (UUID) to copy from
    artifact: str   # Artifact ID in the source run
```

---

## Examples

### Example 1: Simple File Analysis

```yaml
name: "File Content Analysis"
description: "Analyse files for personal data"

artifacts:
  file_content:
    source:
      type: filesystem
      properties:
        path: "./data"

  findings:
    inputs: file_content
    process:
      type: personal_data
      properties:
        pattern_matching:
          ruleset: "local/personal_data/1.0.0"
    output: true
```

### Example 2: Multi-Source Analysis

```yaml
name: "LAMP Stack Analysis"
description: "Analyse MySQL, files, and PHP source code"

artifacts:
  # Sources (run in parallel)
  db_schema:
    source:
      type: mysql
      properties:
        database: "${MYSQL_DATABASE}"

  log_files:
    source:
      type: filesystem
      properties:
        path: "./logs"

  php_code:
    source:
      type: source_code
      properties:
        path: "./src"

  # Analysis (runs after sources complete)
  db_findings:
    inputs: db_schema
    process:
      type: personal_data
    output: true

  log_findings:
    inputs: log_files
    process:
      type: personal_data
    output: true

  code_findings:
    inputs: php_code
    process:
      type: personal_data
    output: true
```

### Example 3: Chained Processing

```yaml
name: "Processing Purpose Detection"
description: "Detect personal data then infer processing purposes"

artifacts:
  db_schema:
    source:
      type: mysql
      properties:
        database: mydb

  personal_data:
    inputs: db_schema
    process:
      type: personal_data

  processing_purposes:
    inputs: personal_data
    process:
      type: processing_purpose
    output: true
```

---

## Related Documentation

- [Child Runbook Composition](child-runbook-composition.md) - Modular runbook design
- [Processor Input Requirements](../../waivern-core/docs/processor-input-requirements.md) - Multi-schema fan-in support
- [Sample Runbooks](../../../apps/wct/runbooks/samples/) - Working examples
