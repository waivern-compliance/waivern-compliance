# Extending the Waivern Compliance Framework

**Related:** [WCF Core Components](../core-concepts/wcf-core-components.md)

## Overview

The Waivern Compliance Framework (WCF) is designed to be extended. This document explains the extensibility points and how you can build on top of WCF to create custom compliance solutions.

## Prerequisites

Before extending WCF, you should be familiar with:

- **[WCF Core Components](../core-concepts/wcf-core-components.md)** - Connectors, analysers, schemas, and messages
- **[Runbooks Documentation](../../apps/wct/runbooks/README.md)** - How WCT orchestrates components (artifact-centric format)
- **Python 3.12+** - Modern Python features and type hints
- **Dependency Injection** - ComponentFactory and ServiceContainer patterns (see [DI Factory Patterns](../../libs/waivern-core/docs/di-factory-patterns.md))

## WCF Extensibility Model

WCF provides three primary extension mechanisms:

1. **Custom components** — connectors, analysers, and rulesets
2. **Entry points** — automatic component discovery
3. **Source-code language plugins** — register new languages for the source-code analyser

## Component Development

### Creating Custom Components

You can extend WCF by creating your own components:

**Connectors** - Extract data from custom sources:
```python
from waivern_core import Connector, Schema, Message

class MyConnector(Connector[MyConnectorConfig]):
    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("my_output", "1.0.0")]

    def extract(self, output_schema: Schema) -> Message:
        # Extract from your data source
        data = self._fetch_data()
        return Message(content=data, schema=output_schema)
```

**Processors (Analysers)** - Implement custom compliance checks:
```python
from waivern_core import Processor, Schema, Message, InputRequirement

class MyAnalyser(Processor[MyAnalyserConfig]):
    @classmethod
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [[InputRequirement("standard_input", "1.0.0")]]

    @classmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("my_finding", "1.0.0")]

    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        # Your compliance analysis logic
        findings = self._analyse(inputs[0].content)
        return Message(content=findings, schema=output_schema)
```

**Rulesets** - Define pattern-based detection rules:
```yaml
# my-ruleset.yaml
name: "My Custom Ruleset"
patterns:
  - pattern: "credit-card-number"
    regex: '\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
```

**See:** Framework packages in `libs/` for reference implementations.

## Entry Points System

### Automatic Discovery

WCF uses Python entry points for automatic component discovery. When you install a package with registered entry points, WCT automatically discovers and makes those components available.

### Registering Your Components

```toml
# your-package/pyproject.toml

# Register connectors
[project.entry-points."waivern.connectors"]
my_connector = "my_package:create_my_connector_factory"

# Register processors (analysers)
[project.entry-points."waivern.processors"]
my_analyser = "my_package:create_my_analyser_factory"

```

**Available entry point groups:**
- `waivern.connectors` - Data source connectors
- `waivern.processors` - Analysers and processors
- `waivern.source_code_languages` - Language support for source code analysis

### Factory Functions

```python
# your-package/src/my_package/__init__.py
from waivern_core.factory import ComponentFactory
from my_package.connector import MyConnector, MyConnectorConfig

def create_my_connector_factory():
    """Entry point for connector discovery."""
    return ComponentFactory(
        component_class=MyConnector,
        config_class=MyConnectorConfig
    )
```

### Discovery Process

1. User installs your package: `pip install my-wcf-components`
2. Entry points are registered automatically
3. WCT discovers your components at runtime
4. Users can use them in runbooks immediately

```bash
$ wct connectors
Available Connectors:
[local] mysql
[local] sqlite
[local] filesystem
[local] my_connector  ← Your custom connector!
```

**See:** [Entry Points Epic (#188)](https://github.com/waivern-compliance/waivern-compliance/issues/188) for the implementation roadmap.

## Deployment Models for Custom Components

### Local Development

Package and distribute your components as Python packages:

```bash
# Your users install your package
pip install my-wcf-components

# Components automatically available
wct ls-analysers
wct run my-runbook.yaml
```

## Schema-Driven Extension

### Defining Custom Schemas

Create JSON Schema files for your data contracts:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MyCustomFinding",
  "type": "object",
  "properties": {
    "finding_type": {"type": "string"},
    "severity": {"enum": ["low", "medium", "high"]},
    "details": {"type": "object"}
  },
  "required": ["finding_type", "severity"]
}
```

### Schema Definitions

All schema types (Pydantic models) and JSON schema files are centralised in the `waivern-schemas` package. When creating a new analyser, add your output schema as a sub-package in `waivern-schemas` with directory-based versioning.

## Source Code Language Extensions

The Source Code Analyser supports multiple programming languages through a plugin architecture. You can add support for new languages by implementing the `LanguageSupport` protocol.

### Adding Language Support

Create a language support module:

```python
# my_package/languages/rust/__init__.py


class RustLanguageSupport:
    """Rust language support for source code analysis."""

    @property
    def name(self) -> str:
        return "rust"

    @property
    def file_extensions(self) -> list[str]:
        return [".rs"]
```

The `LanguageSupport` protocol requires:
- `name` - Canonical language name
- `file_extensions` - List of supported file extensions

### Registering Language Support

Register via entry points:

```toml
# pyproject.toml
[project.entry-points."waivern.source_code_languages"]
rust = "my_package.languages.rust:RustLanguageSupport"
```

### Built-in Languages

WCF includes support for:
- **PHP** - `.php`, `.php3`, `.php4`, `.php5`, `.phtml`
- **TypeScript** - `.ts`, `.tsx`, `.mts`, `.cts`

## Package Distribution

### Public Distribution (PyPI)

For open-source components:

```bash
# Build your package
uv build

# Publish to PyPI
uv publish
```

Users install with:
```bash
pip install my-wcf-components
```

### Private Distribution

For proprietary components:

**Option 1: Private PyPI**
```bash
# Publish to private index
uv publish --repository-url https://pypi.mycompany.com
```

**Option 2: GitHub Packages**
```bash
uv publish --repository-url https://pypi.pkg.github.com/myorg
```

**Option 3: Direct Installation**
```bash
pip install git+https://github.com/myorg/my-wcf-components.git
```

## Best Practices

### Component Design

1. **Follow WCF patterns** - Implement base abstractions correctly
2. **Schema-driven** - Define clear input/output schemas
3. **Pure functions** - Analysers should be stateless where possible
4. **Error handling** - Graceful failures with clear error messages
5. **Testing** - Comprehensive unit and integration tests

### Packaging

1. **Declare dependencies** - Specify WCF version requirements
2. **Entry points** - Register all components
3. **Documentation** - Clear usage examples
4. **Versioning** - Follow semantic versioning
5. **Licensing** - Clearly specify license terms

### Security

1. **Validate inputs** - Don't trust data from connectors
2. **Sanitise outputs** - Prevent injection attacks

## Example: Building a Custom Compliance Package

Complete example structure:

```
my-compliance-package/
├── src/
│   └── my_compliance/
│       ├── __init__.py           # Entry point functions
│       ├── connector.py          # Custom connector
│       └── analyser.py           # Custom analyser
├── tests/
│   ├── test_connector.py
│   └── test_analyser.py
├── examples/
│   └── sample-runbook.yaml
├── pyproject.toml
└── README.md
```

> **Note:** Schema definitions (Pydantic models and JSON schema files) are centralised in the `waivern-schemas` package, not in individual component packages.

```toml
# pyproject.toml
[project]
name = "my-compliance-package"
version = "1.0.0"
dependencies = [
    "waivern-core>=1.0.0,<2.0.0",
    "waivern-llm>=1.0.0,<2.0.0",
]

[project.entry-points."waivern.connectors"]
my_connector = "my_compliance:create_my_connector_factory"

[project.entry-points."waivern.processors"]
my_analyser = "my_compliance:create_my_analyser_factory"
```

## Community and Support

### Resources

- **GitHub Discussions:** Ask questions and share components
- **Examples Repository:** Sample implementations
- **API Documentation:** Complete framework reference

### Sharing Your Components

Consider open-sourcing your components:
1. Publish to PyPI for easy installation
2. Add to the WCF community registry
3. Share in GitHub Discussions
4. Tag with `waivern-component`

## Related Documents

- [WCF Core Components](../core-concepts/wcf-core-components.md) - Framework architecture
- [Runbooks Documentation](../../apps/wct/runbooks/README.md) - Runbook format and examples
- [Artifact-Centric Orchestration](../../libs/waivern-orchestration/docs/artifact-centric-orchestration.md) - Execution engine design

## Enterprise Extensions

> **Note:** For enterprise deployment options and commercial offerings, visit https://www.waivern.com

Third-party developers can build and distribute their own premium components using the patterns
described in this guide.
