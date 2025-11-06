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
- File content analysis
- MySQL database analysis
- PHP source code analysis
- Personal data detection across multiple data sources
- Multi-analyser execution with different configurations
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
