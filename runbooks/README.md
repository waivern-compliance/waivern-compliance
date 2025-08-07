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

## Creating New Runbooks

When creating new runbooks for specific scenarios:

1. Use relative paths from project root (e.g., `./tests/...`)
2. Follow the established naming convention: `scenario_description.yaml`
3. Include appropriate metadata for compliance frameworks
4. Document the purpose and expected outcomes

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

This will analyze a sample file and demonstrate:
- Email detection
- API key detection
- Password pattern detection
- Risk scoring and severity classification
