# WCT Runbooks

This directory contains various runbook configurations for different testing and analysis scenarios.

## Available Runbooks

### Sample Runbooks (`samples/` directory)

#### `samples/file_content_analysis.yaml`
A simple demonstration runbook showing:
- Basic file content analysis using the personal_data_analyser
- Detection of personal data and sensitive information
- Ideal for learning WCT basics and testing file analysis functionality

#### `samples/LAMP_stack.yaml`
A comprehensive example runbook that demonstrates:
- **Pipeline execution** (Filesystem → SourceCode → ProcessingPurpose)
- Multi-step analyser chaining with `input_from`
- MySQL database analysis
- PHP source code analysis
- Personal data detection across multiple data sources
- Complete LAMP stack compliance analysis

## Usage

Run any runbook from the project root:

```bash
# Validate a runbook
uv run wct validate-runbook runbooks/samples/file_content_analysis.yaml

# Execute sample runbooks
uv run wct run runbooks/samples/file_content_analysis.yaml
uv run wct run runbooks/samples/LAMP_stack.yaml

# Execute with debug logging
uv run wct run runbooks/samples/file_content_analysis.yaml --log-level DEBUG
uv run wct run runbooks/samples/LAMP_stack.yaml -v
```

## Pipeline Execution

Pipeline execution enables multi-step analysis workflows where the output of one step becomes the input to the next. This is WCF's most powerful feature for complex compliance analysis.

### When to Use Pipelines

Use pipeline execution when you need to:
- Transform data through multiple stages (e.g., parse → analyse → classify)
- Chain analysers that require different input schemas
- Reuse intermediate results across multiple downstream steps
- Build modular, composable analysis workflows

### Pipeline Basics

**Key fields:**
- `id`: Unique identifier for each step (required)
- `input_from`: Reference to previous step's ID (pipeline mode)
- `connector`: Extract from external source (connector mode)
- `save_output`: Store step output for downstream steps (default: false)

**Execution modes:**
- **Connector mode:** Step has `connector` field - extracts from external source
- **Pipeline mode:** Step has `input_from` field - reads from previous step's output

### Example: Source Code Analysis Pipeline

```yaml
execution:
  # Step 1: Read PHP files from filesystem
  - id: "read_files"
    connector: "filesystem"
    analyser: "source_code_analyser"
    input_schema: "standard_input"
    output_schema: "source_code"
    save_output: true  # Required for downstream steps

  # Step 2: Analyse parsed code for processing purposes
  - id: "analyse_purposes"
    input_from: "read_files"  # Uses output from step 1
    analyser: "processing_purpose_analyser"
    input_schema: "source_code"
    output_schema: "processing_purpose_finding"
```

**How it works:**
1. `read_files` extracts files via filesystem connector
2. `source_code_analyser` transforms standard_input → source_code schema
3. `save_output: true` stores the Message for downstream use
4. `analyse_purposes` reads from artifacts (no connector needed)
5. Executor validates schema compatibility automatically

### Schema Compatibility

The executor validates that:
- Step's input schema matches previous step's output schema
- Analyser supports the input schema
- Schema names and versions are compatible

If schemas don't match, WCT provides clear error messages listing supported schemas.

### Real-World Example

See `samples/LAMP_stack.yaml` lines 174-191 for a complete pipeline:
```yaml
- id: "read_php_files"
  connector: "php_files"
  analyser: "source_code_analyser_for_php"
  output_schema: "source_code"
  save_output: true

- id: "php_processing_purpose"
  input_from: "read_php_files"
  analyser: "processing_purpose_analyser_for_source_code"
  input_schema: "source_code"
```

## Schema Version Specification

Execution steps support optional version pinning for input and output schemas.

### Auto-Selection (Recommended)

By default, WCT automatically selects the latest compatible schema version:

```yaml
execution:
  - name: "Analyse data"
    connector: "mysql_connector"
    analyser: "personal_data_analyser"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
    # Versions auto-selected
```

### Explicit Version Pinning

Pin specific schema versions when needed:

```yaml
execution:
  - name: "Analyse data with specific versions"
    connector: "mysql_connector"
    analyser: "personal_data_analyser"
    input_schema: "standard_input"
    input_schema_version: "1.0.0"     # Pin input to v1.0.0
    output_schema: "personal_data_finding"
    output_schema_version: "1.0.0"    # Pin output to v1.0.0
```

**Version Format:** Must be semantic versioning `major.minor.patch` (e.g., "1.0.0", "2.10.5")

### When to Pin Versions

**Use auto-selection when:**
- You want latest features and improvements
- Components are regularly updated
- You trust component maintainers

**Pin versions when:**
- Reproducible results required (compliance audits)
- Testing specific version combinations
- Avoiding breaking changes temporarily
- Integration with external systems requiring specific format

### Version Compatibility

WCT validates version compatibility:
- Connector must support requested input schema version
- Analyser must support requested input schema version
- Analyser must support requested output schema version

If no compatible versions found, WCT provides clear error message with available versions.

## Creating New Runbooks

When creating new runbooks for specific scenarios:

1. Use relative paths from project root (e.g., `./tests/...`)
2. Follow the established naming convention: `scenario_description.yaml`
3. Include appropriate metadata for compliance frameworks
4. Document the purpose and expected outcomes

### IDE Support for Runbook Creation

For enhanced development experience with autocomplete, validation, and documentation:

```bash
# Generate JSON Schema for IDE support
uv run wct generate-schema
```

This enables real-time validation and autocomplete in VS Code, PyCharm, and other IDEs. See [IDE Integration Guide](../docs/ide-integration.md) for setup instructions.

### How Schema Generation Works

WCT uses Pydantic models as the single source of truth for runbook validation:

1. **Runtime validation**: Pydantic validates runbooks when `wct run` executes
2. **IDE support**: JSON Schema is auto-generated from Pydantic via `model_json_schema()`
3. **Single source**: One definition serves both purposes (no duplication)

When you run `wct generate-schema`, it:
- Extracts JSON Schema from the Pydantic `Runbook` model
- Adds WCT-specific metadata (version, title, description)
- Outputs to file for IDE consumption

This ensures runtime validation and IDE autocomplete are always in sync. Field descriptions, constraints, and validation rules defined in the Pydantic model automatically appear in both runtime errors and IDE tooltips.

**Regenerate schema after WCT updates:**
```bash
wct generate-schema --output runbook.schema.json
```

## Scenario Ideas

Future runbooks could include:
- `database_only_analysis.yaml` - MySQL/database-specific analysis
- `source_code_only_analysis.yaml` - Source code analysis without other connectors
- `llm_validation_test.yaml` - Testing LLM validation features
- `performance_test.yaml` - Large dataset performance testing
- `wordpress_stack_analysis.yaml` - WordPress-specific compliance analysis
- `api_security_analysis.yaml` - Focus on API key and authentication analysis

## Quick Start

For new users, start with the simple file analysis:
```bash
uv run wct run runbooks/samples/file_content_analysis.yaml -v
```

This will analyse a sample file and demonstrate:
- Email detection
- API key detection
- Password pattern detection
- Risk scoring and severity classification
