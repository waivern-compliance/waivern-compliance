# Building Custom Components

**Status:** DRAFT - Will be used as input for cookiecutter template
**Last Updated:** 2025-11-03
**Related:** [Extending WCF](extending-wcf.md), [WCF Core Components](../core-concepts/wcf-core-components.md)

> **Note:** This guide is currently in draft status and serves as the design document for creating a `cookiecutter` project template. Once the code structure is stable, this will be used to generate:
> ```bash
> cookiecutter gh:waivern-compliance/cookiecutter-waivern-analyser
> ```

## Overview

This guide walks you through creating custom connectors, analysers, and rulesets for WCF. You'll learn how to implement components that integrate seamlessly with WCT and can be distributed to others.

## Prerequisites

- Python 3.12+
- Familiarity with [WCF concepts](../core-concepts/wcf-core-components.md) (connectors, analysers, schemas)
- Understanding of dependency injection and factory patterns

**Recommended Reading:**
- [Extending WCF](extending-wcf.md)

## Quick Start

### 1. Create Package Structure

```bash
# Create your package
mkdir my-wcf-components
cd my-wcf-components

# Initialise with uv
uv init

# Project structure
my-wcf-components/
├── src/
│   └── my_wcf_components/
│       ├── __init__.py
│       ├── connector.py
│       ├── analyser.py
│       └── schemas/
│           └── json_schemas/
│               └── my_finding/
│                   └── 1.0.0/
│                       └── my_finding.json
├── tests/
│   ├── test_connector.py
│   └── test_analyser.py
├── examples/
│   └── sample-runbook.yaml
├── pyproject.toml
└── README.md
```

### 2. Configure Dependencies

```toml
# pyproject.toml
[project]
name = "my-wcf-components"
version = "1.0.0"
description = "Custom compliance components for WCF"
requires-python = ">=3.12"
dependencies = [
    "waivern-core>=1.0.0,<2.0.0",
    "waivern-llm>=1.0.0,<2.0.0",  # If using LLM features
]

[project.entry-points."waivern.connectors"]
my_connector = "my_wcf_components:create_my_connector_factory"

[project.entry-points."waivern.analysers"]
my_analyser = "my_wcf_components:create_my_analyser_factory"
```

### 3. Implement Your Connector

```python
# src/my_wcf_components/connector.py
from typing import override
from pydantic import BaseModel, Field
from waivern_core.connector import Connector, ConnectorConfig
from waivern_core.message import Message
from waivern_core.schema import Schema

class MyConnectorConfig(ConnectorConfig):
    """Configuration for MyConnector."""
    api_endpoint: str = Field(description="API endpoint URL")
    api_key: str = Field(description="API authentication key")
    timeout: int = Field(default=30, description="Request timeout in seconds")

class MyConnector(Connector[MyConnectorConfig]):
    """Extracts data from MyService API."""

    def __init__(self, config: MyConnectorConfig):
        super().__init__(config)
        # Initialize your connection here

    @override
    def get_supported_output_schemas(self) -> list[Schema]:
        """Declare what schemas this connector can produce."""
        return [
            Schema(name="standard_input", version="1.0.0")
        ]

    @override
    def extract(self) -> Message:
        """Extract data from your source."""
        # Your extraction logic here
        data = self._fetch_from_api()

        # Transform to WCF schema format
        schema_data = {
            "source": "my_service",
            "entities": [
                {
                    "entity_type": "field",
                    "entity_name": entity["name"],
                    "content": entity["value"],
                    "metadata": {}
                }
                for entity in data
            ]
        }

        # Return as Message (automatically validates against schema)
        return Message(
            schema_name="standard_input",
            schema_version="1.0.0",
            data=schema_data
        )

    def _fetch_from_api(self) -> list[dict]:
        """Fetch data from your API."""
        # Implementation details
        pass
```

### 4. Implement Your Analyser

```python
# src/my_wcf_components/analyser.py
from typing import override
from pydantic import BaseModel, Field
from waivern_core.analyser import Analyser, AnalyserConfig
from waivern_core.message import Message
from waivern_core.schema import Schema

class MyAnalyserConfig(AnalyserConfig):
    """Configuration for MyAnalyser."""
    sensitivity_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Detection sensitivity threshold"
    )
    enable_advanced_checks: bool = Field(
        default=False,
        description="Enable advanced compliance checks"
    )

class MyAnalyser(Analyser[MyAnalyserConfig]):
    """Analyses data for custom compliance requirements."""

    def __init__(self, config: MyAnalyserConfig):
        super().__init__(config)
        self.threshold = config.sensitivity_threshold

    @override
    def get_supported_input_schemas(self) -> list[Schema]:
        """Declare what input schemas this analyser accepts."""
        return [
            Schema(name="standard_input", version="1.0.0")
        ]

    @override
    def get_supported_output_schemas(self) -> list[Schema]:
        """Declare what output schemas this analyser produces."""
        return [
            Schema(name="my_finding", version="1.0.0")
        ]

    @override
    def process_data(self, message: Message) -> Message:
        """Process input data and return findings."""
        # Message is already validated against input schema
        input_data = message.data

        # Your analysis logic
        findings = []
        for entity in input_data["entities"]:
            if self._should_flag(entity):
                findings.append({
                    "entity_name": entity["entity_name"],
                    "finding_type": "compliance_issue",
                    "severity": "high",
                    "description": f"Issue found in {entity['entity_name']}",
                    "evidence": entity.get("content", "")
                })

        # Return as Message (automatically validates against output schema)
        return Message(
            schema_name="my_finding",
            schema_version="1.0.0",
            data={"findings": findings}
        )

    def _should_flag(self, entity: dict) -> bool:
        """Determine if entity should be flagged."""
        # Your compliance detection logic
        pass
```

### 5. Create Component Factories

```python
# src/my_wcf_components/__init__.py
from waivern_core.factory import ComponentFactory
from my_wcf_components.connector import MyConnector, MyConnectorConfig
from my_wcf_components.analyser import MyAnalyser, MyAnalyserConfig

def create_my_connector_factory() -> ComponentFactory:
    """Entry point for connector discovery."""
    return ComponentFactory(
        component_class=MyConnector,
        config_class=MyConnectorConfig
    )

def create_my_analyser_factory() -> ComponentFactory:
    """Entry point for analyser discovery."""
    return ComponentFactory(
        component_class=MyAnalyser,
        config_class=MyAnalyserConfig
    )

__all__ = [
    "MyConnector",
    "MyConnectorConfig",
    "MyAnalyser",
    "MyAnalyserConfig",
    "create_my_connector_factory",
    "create_my_analyser_factory",
]
```

### 6. Define Custom Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MyFinding",
  "type": "object",
  "properties": {
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "entity_name": {
            "type": "string",
            "description": "Name of the entity where issue was found"
          },
          "finding_type": {
            "type": "string",
            "description": "Type of compliance issue"
          },
          "severity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"]
          },
          "description": {
            "type": "string",
            "description": "Human-readable description"
          },
          "evidence": {
            "type": "string",
            "description": "Supporting evidence"
          }
        },
        "required": ["entity_name", "finding_type", "severity", "description"]
      }
    }
  },
  "required": ["findings"]
}
```

Save as: `src/my_wcf_components/schemas/json_schemas/my_finding/1.0.0/my_finding.json`

### 7. Write Tests

```python
# tests/test_connector.py
import pytest
from my_wcf_components import MyConnector, MyConnectorConfig

def test_connector_extraction():
    """Test connector can extract data."""
    config = MyConnectorConfig(
        api_endpoint="https://api.example.com",
        api_key="test_key"
    )
    connector = MyConnector(config)

    message = connector.extract()

    assert message.schema_name == "standard_input"
    assert "entities" in message.data
    assert len(message.data["entities"]) > 0

def test_connector_schema_validation():
    """Test connector output validates against schema."""
    config = MyConnectorConfig(
        api_endpoint="https://api.example.com",
        api_key="test_key"
    )
    connector = MyConnector(config)

    # This will raise if schema validation fails
    message = connector.extract()
    assert message is not None
```

```python
# tests/test_analyser.py
import pytest
from my_wcf_components import MyAnalyser, MyAnalyserConfig
from waivern_core.message import Message

def test_analyser_processing():
    """Test analyser processes data correctly."""
    config = MyAnalyserConfig(sensitivity_threshold=0.5)
    analyser = MyAnalyser(config)

    input_message = Message(
        schema_name="standard_input",
        schema_version="1.0.0",
        data={
            "source": "test",
            "entities": [
                {
                    "entity_type": "field",
                    "entity_name": "test_field",
                    "content": "test_value",
                    "metadata": {}
                }
            ]
        }
    )

    result = analyser.process_data(input_message)

    assert result.schema_name == "my_finding"
    assert "findings" in result.data

def test_analyser_threshold():
    """Test sensitivity threshold affects detection."""
    high_threshold = MyAnalyser(MyAnalyserConfig(sensitivity_threshold=0.9))
    low_threshold = MyAnalyser(MyAnalyserConfig(sensitivity_threshold=0.1))

    # Test with same input
    # Verify different threshold behavior
```

### 8. Create Example Runbook

```yaml
# examples/sample-runbook.yaml
name: "Test My Custom Components"
description: "Example runbook using custom connector and analyser"

connectors:
  - name: "my_data_source"
    type: "my_connector"
    properties:
      api_endpoint: "https://api.example.com"
      api_key: "${MY_API_KEY}"
      timeout: 30

analysers:
  - name: "my_compliance_checker"
    type: "my_analyser"
    properties:
      sensitivity_threshold: 0.8
      enable_advanced_checks: true

execution:
  - name: "Check compliance"
    connector: "my_data_source"
    analyser: "my_compliance_checker"
    input_schema: "standard_input"
    output_schema: "my_finding"
```

### 9. Install and Test

```bash
# Install in editable mode for development
uv pip install -e .

# Verify discovery
wct ls-connectors
# Should show: [local] my_connector

wct ls-analysers
# Should show: [local] my_analyser

# Run example runbook
wct run examples/sample-runbook.yaml
```

## Advanced Topics

### Working with LLM Services

```python
from waivern_llm.service import LLMService, LLMServiceConfig

class MyLLMAnalyser(Analyser[MyAnalyserConfig]):
    def __init__(self, config: MyAnalyserConfig):
        super().__init__(config)
        # Initialize LLM service
        self.llm = LLMService(LLMServiceConfig(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929"
        ))

    def process_data(self, message: Message) -> Message:
        # Use LLM for validation
        prompt = self._build_prompt(message.data)
        response = self.llm.complete(prompt)
        findings = self._parse_llm_response(response)

        return Message(
            schema_name="my_finding",
            schema_version="1.0.0",
            data={"findings": findings}
        )
```

### Using Rulesets

```python
from waivern_rulesets import PersonalDataRuleset

class MyRulesetAnalyser(Analyser[MyAnalyserConfig]):
    def __init__(self, config: MyAnalyserConfig):
        super().__init__(config)
        self.ruleset = PersonalDataRuleset()

    def process_data(self, message: Message) -> Message:
        findings = []
        for entity in message.data["entities"]:
            # Apply ruleset patterns
            matches = self.ruleset.match(entity["content"])
            if matches:
                findings.append({
                    "entity_name": entity["entity_name"],
                    "patterns_matched": [m.pattern_name for m in matches],
                    # ...
                })

        return Message(
            schema_name="my_finding",
            schema_version="1.0.0",
            data={"findings": findings}
        )
```

> **Note:** Rulesets can also be hosted remotely as HTTP services, allowing analysers to access premium, expert-curated patterns via API key. See [Remote Rulesets](extending-wcf.md#remote-rulesets) for details.

### Multi-Schema Support

```python
class FlexibleAnalyser(Analyser[MyAnalyserConfig]):
    @override
    def get_supported_input_schemas(self) -> list[Schema]:
        # Accept multiple input types
        return [
            Schema(name="standard_input", version="1.0.0"),
            Schema(name="personal_data_finding", version="1.0.0"),
            Schema(name="processing_purpose_finding", version="1.0.0"),
        ]

    @override
    def process_data(self, message: Message) -> Message:
        # Branch based on input schema
        if message.schema_name == "standard_input":
            return self._process_raw_data(message)
        elif message.schema_name == "personal_data_finding":
            return self._process_findings(message)
        # ...
```

### Error Handling

```python
from waivern_core.exceptions import ComponentExecutionError

class RobustConnector(Connector[MyConnectorConfig]):
    def extract(self) -> Message:
        try:
            data = self._fetch_from_api()
            return self._transform_to_message(data)
        except ConnectionError as e:
            raise ComponentExecutionError(
                f"Failed to connect to API: {e}",
                component_name="my_connector"
            )
        except ValueError as e:
            raise ComponentExecutionError(
                f"Invalid data format: {e}",
                component_name="my_connector"
            )
```

## Best Practices

### Configuration

1. **Use Pydantic models** for type safety
2. **Provide defaults** where sensible
3. **Add field descriptions** for documentation
4. **Validate constraints** (ranges, enums, etc.)

```python
class MyConfig(ConnectorConfig):
    endpoint: str = Field(description="API endpoint")
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout in seconds"
    )
    mode: str = Field(
        default="standard",
        pattern="^(standard|advanced|debug)$",
        description="Operation mode"
    )
```

### Schema Design

1. **Version schemas** from the start
2. **Use clear names** (noun_verb format)
3. **Include descriptions** in JSON Schema
4. **Plan for evolution** (additive changes only in minor versions)

### Testing

1. **Unit test components** independently
2. **Integration test** with WCT
3. **Test schema validation** explicitly
4. **Mock external dependencies**
5. **Test error conditions**

### Documentation

1. **Write clear README** with usage examples
2. **Document configuration** options
3. **Provide example runbooks**
4. **Explain schema contracts**
5. **Include troubleshooting** guide

## Distribution

### Publishing to PyPI

```bash
# Build distribution
uv build

# Publish to PyPI
uv publish
```

### Private Distribution

For proprietary components:

```bash
# Publish to private PyPI
uv publish --repository-url https://pypi.yourcompany.com

# Or GitHub Packages
uv publish --repository-url https://pypi.pkg.github.com/yourorg
```

Users install with:
```bash
pip install my-wcf-components --extra-index-url https://pypi.yourcompany.com
```

## Examples from the Framework

**Reference implementations:**
- **Simple connector:** `waivern-filesystem` - Minimal connector example
- **Database connector:** `waivern-mysql` - SQL connector with shared utilities
- **Complex connector:** `waivern-source-code` - Custom schema, tree-sitter integration
- **Simple analyser:** `waivern-personal-data-analyser` - Ruleset-based analysis
- **Complex analyser:** `waivern-processing-purpose-analyser` - Multi-schema support, LLM validation

**Study these for patterns:**
- Entry point registration
- Configuration design with Pydantic
- Error handling
- Testing approaches
- Schema co-location
- Documentation style

## Getting Help

- **GitHub Discussions:** Ask questions
- **Issues:** Report bugs or request features
- **Documentation:** Browse core concepts and examples

## Related Documentation

- [Extending WCF](extending-wcf.md) - Extension mechanisms overview
- [Remote Analyser Protocol](../architecture/remote-analyser-protocol.md) - HTTP API spec
- [WCF Core Components](../core-concepts/wcf-core-components.md) - Framework architecture
- [Component Extraction Template](guides/component-extraction-template.md) - Internal extraction guide

## Next Steps

1. Clone the example package structure
2. Implement your connector or analyser
3. Write tests
4. Create example runbooks
5. Share with the community!

Happy building! 🚀
