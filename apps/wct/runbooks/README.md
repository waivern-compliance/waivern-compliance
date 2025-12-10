# WCT Runbooks

Runbooks define compliance analysis pipelines using an artifact-centric format. Each runbook declares artifacts (data sources and processors) and their dependencies, enabling parallel execution where possible.

## Runbook Structure

```yaml
name: str                    # Required: Runbook name
description: str             # Required: What this runbook analyses
contact: str                 # Optional: Contact person

config:                      # Optional: Execution settings
  timeout: int               # Total timeout in seconds
  max_concurrency: int       # Parallel artifacts (default: 10)

artifacts:                   # Required: Artifact definitions
  <artifact_id>:
    # ... artifact definition
```

## Artifact Types

### Source Artifacts

Source artifacts extract data from external systems (databases, filesystems, APIs):

```yaml
artifacts:
  mysql_data:
    name: "MySQL Database Content"
    description: "Extract data from MySQL database"
    source:
      type: "mysql"
      properties:
        max_rows_per_table: 10
```

**Fields:**
- `source.type`: Connector type (e.g., `mysql`, `sqlite`, `filesystem`)
- `source.properties`: Connector-specific configuration

### Derived Artifacts

Derived artifacts transform data from upstream artifacts:

```yaml
artifacts:
  personal_data_findings:
    name: "Personal Data Detection"
    description: "Analyse database for PII"
    inputs: mysql_data              # Reference to upstream artifact
    process:
      type: "personal_data"
      properties:
        pattern_matching:
          ruleset: "personal_data"
    output: true                    # Include in final output
```

**Fields:**
- `inputs`: Single artifact ID or list of IDs (fan-in)
- `process.type`: Processor type (e.g., `personal_data`, `processing_purpose`, `data_subject`)
- `process.properties`: Processor-specific configuration
- `output`: Whether to include in results (default: false)

### Fan-In (Multiple Inputs)

Artifacts can consume from multiple upstream sources:

```yaml
artifacts:
  combined_analysis:
    inputs:
      - mysql_findings
      - filesystem_findings
    process:
      type: "personal_data"
    merge: "concatenate"           # Only strategy supported
    output: true
```

## Pipeline Execution

WCT automatically determines execution order from artifact dependencies:

```yaml
artifacts:
  # Stage 1: Source extraction (runs in parallel)
  php_files:
    source:
      type: "filesystem"
      properties:
        path: "./src"
        include_patterns: ["*.php"]

  # Stage 2: Parse source code
  php_source_code:
    inputs: php_files
    process:
      type: "source_code_analyser"
      properties:
        language: "php"

  # Stage 3: Analyse for processing purposes
  processing_purposes:
    inputs: php_source_code
    process:
      type: "processing_purpose"
    output: true
```

**Execution flow:**
1. `php_files` extracts files (source artifact)
2. `php_source_code` parses files (waits for step 1)
3. `processing_purposes` analyses code (waits for step 2)

Independent artifacts execute in parallel automatically.

## Available Runbooks

### Sample Runbooks (`samples/` directory)

#### `samples/file_content_analysis.yaml`

Simple demonstration runbook showing:
- Basic file content analysis using personal_data analyser
- Detection of personal data and sensitive information
- Ideal for learning WCT basics

#### `samples/LAMP_stack.yaml`

Comprehensive example demonstrating:
- Multiple source artifacts (MySQL, filesystem)
- Pipeline execution: Filesystem → SourceCode → ProcessingPurpose
- Fan-out pattern (one source, multiple analysers)
- Personal data, data subject, and processing purpose detection

#### `samples/LAMP_stack_lite.yaml`

Lightweight version of LAMP_stack without MySQL dependency.

## Usage

```bash
# Validate a runbook
uv run wct validate-runbook runbooks/samples/file_content_analysis.yaml

# Execute a runbook
uv run wct run runbooks/samples/file_content_analysis.yaml

# Execute with verbose logging
uv run wct run runbooks/samples/LAMP_stack.yaml -v

# Execute with debug logging
uv run wct run runbooks/samples/file_content_analysis.yaml --log-level DEBUG
```

## IDE Support

Generate JSON Schema for autocomplete and validation:

```bash
uv run wct generate-schema
```

This enables real-time validation in VS Code, PyCharm, and other IDEs.

## Field Reference

### Runbook Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Runbook name |
| `description` | string | Yes | What this runbook analyses |
| `contact` | string | No | Contact person (e.g., "Name <email>") |
| `config` | object | No | Execution configuration |
| `artifacts` | object | Yes | Artifact definitions |

### Config Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timeout` | int | None | Total execution timeout (seconds) |
| `max_concurrency` | int | 10 | Maximum parallel artifacts |

### Artifact Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Human-readable name |
| `description` | string | No | What this artifact produces |
| `contact` | string | No | Responsible person |
| `source` | object | * | Data extraction config (source artifacts) |
| `inputs` | string/list | * | Upstream artifact(s) (derived artifacts) |
| `process` | object | ** | Processor config (derived artifacts) |
| `merge` | string | No | Fan-in merge strategy ("concatenate") |
| `output` | bool | No | Include in final output (default: false) |
| `optional` | bool | No | Continue on failure (default: false) |

\* Either `source` or `inputs` required (mutually exclusive)
\** Required when `inputs` is specified

### Source Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Connector type |
| `properties` | object | No | Connector configuration |

### Process Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Processor type |
| `properties` | object | No | Processor configuration |

## Available Components

List available connectors and processors:

```bash
uv run wct ls-connectors
uv run wct ls-processors
```

### Connectors

- `mysql` - MySQL database extraction
- `sqlite` - SQLite database extraction
- `filesystem` - File and directory reading

### Processors

- `personal_data` - PII detection
- `data_subject` - Data subject classification
- `processing_purpose` - Processing purpose detection
- `source_code_analyser` - Source code parsing

## Creating New Runbooks

1. Start with a sample runbook as template
2. Define source artifacts for data extraction
3. Define derived artifacts for analysis
4. Set `output: true` on artifacts to include in results
5. Validate with `wct validate-runbook`
6. Test with `wct run`

### Tips

- Use meaningful artifact IDs (they appear in output)
- Set `output: true` only on final analysis artifacts
- Use `optional: true` for non-critical artifacts
- Group related properties under `pattern_matching` and `llm_validation`
