# Waivern Compliance Framework

An open-source framework for automated compliance analysis across any technology stack and regulatory framework (GDPR, ePrivacy, EU AI Act, NIS2, DORA, etc.). Integrates directly into CI/CD pipelines to generate compliance documentation without manual questionnaires or spreadsheets.

## Overview

The Waivern Compliance Framework provides:

- **Framework Libraries** - Core abstractions, multi-provider LLM support, and built-in components
- **WCT (Waivern Compliance Tool)** - CLI application for orchestrating compliance analysis
- **Schema-Driven Architecture** - Type-safe component communication through JSON Schema
- **Extensible Design** - Open standards for connectors, processors, and rulesets

### Core Components

- **Connectors** - Extract data from sources (MySQL, SQLite, files, source code)
- **Processors** - Detect compliance issues (personal data, processing purposes, data subjects)
- **Rulesets** - YAML-based pattern definitions for static analysis
- **Runbooks** - YAML configurations defining artifacts and their dependencies
- **Orchestration** - Planner validates and flattens runbooks; DAGExecutor runs artifacts in parallel

📋 **[Development Roadmap](https://github.com/orgs/waivern-compliance/projects/3)** - Current progress and planned features

🚀 Browse [good first issues](https://github.com/waivern-compliance/waivern-compliance/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

## Quick Start

### Installation

This project uses `uv` for dependency management. Install via [standalone installer](https://github.com/astral-sh/uv?tab=readme-ov-file#installation) or [homebrew](https://formulae.brew.sh/formula/uv).

```bash
# Install all dependencies
uv sync

# Install with development tools
uv sync --group dev

# Install pre-commit hooks (recommended)
uv run pre-commit install
```

### Configure LLM Provider

```bash
# Copy environment template
cp apps/wct/.env.example apps/wct/.env

# Edit apps/wct/.env with your API key
# ANTHROPIC_API_KEY=your_api_key_here

# Test configuration
uv run wct test-llm
```

### Run Your First Analysis

```bash
# Simple file analysis
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml

# Comprehensive LAMP stack analysis
uv run wct run apps/wct/runbooks/samples/LAMP_stack_lite.yaml

# Run with verbose logging
uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml -v
```

**Output:** JSON results are written to `./outputs` directory.

### Available Commands

```bash
# List components
uv run wct ls-connectors
uv run wct ls-processors

# Validate runbook
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml

# Generate JSON Schema for IDE support
uv run wct generate-schema
```

## Runbook Example

```yaml
name: "Personal Data Analysis"
description: "Detect personal data in files and databases"

artifacts:
  # Source artifact - extracts data from filesystem
  file_content:
    name: "File Content Extraction"
    description: "Read files from the filesystem"
    source:
      type: "filesystem"
      properties:
        path: "./sample_file.txt"

  # Derived artifact - processes file content for personal data
  personal_data_findings:
    name: "Personal Data Detection"
    description: "Detect personal data patterns in content"
    inputs: file_content
    process:
      type: "personal_data"
      properties:
        pattern_matching:
          ruleset: "personal_data"
          evidence_context_size: "medium"
        llm_validation:
          enable_llm_validation: true
    output: true  # Include in final output
```

**Sample Runbooks:**
- `apps/wct/runbooks/samples/file_content_analysis.yaml` - Basic file analysis
- `apps/wct/runbooks/samples/LAMP_stack_lite.yaml` - File, database, and source code analysis
- `apps/wct/runbooks/samples/LAMP_stack.yaml` - Advanced MySQL-based analysis
- See `apps/wct/runbooks/README.md` for detailed documentation

## Architecture

### Monorepo Structure

```
waivern-compliance/
├── libs/                           # Framework libraries (13 standalone packages)
│   ├── waivern-core/              # Core abstractions
│   ├── waivern-llm/               # Multi-provider LLM support
│   ├── waivern-connectors-*/      # Connectors (mysql, sqlite, filesystem, source-code)
│   ├── waivern-*-analyser/        # Analysers (personal-data, data-subject, processing-purpose)
│   └── waivern-*-shared/          # Shared utilities (rulesets, analyser utils, database utils)
└── apps/
    └── wct/                        # CLI application (plugin host)
        ├── runbooks/               # YAML runbook configurations
        └── src/wct/                # Component discovery via entry points
```

**Framework Independence:**
- Libraries have no WCT dependencies
- Can be used by other applications
- Independent versioning and releases
- Clear separation of concerns

### Data Flow

```
Runbook (YAML) → Planner → DAGExecutor → Connector/Processor → Findings (JSON)
```

1. **Runbook** defines artifacts (sources and transformations) and their dependencies
2. **Planner** parses runbook, flattens child runbooks, builds DAG, validates schemas
3. **DAGExecutor** runs artifacts in dependency order (parallel where possible)
4. **Connectors** extract data; **Processors** transform data
5. **Message objects** provide automatic schema validation
6. **Results** output as structured JSON

### Schema-Driven Design

- Components declare input/output schemas (JSON Schema format)
- Executor automatically matches schemas between connectors and analysers
- Runtime validation through Message objects
- Type-safe interfaces throughout

**See:** [WCF Core Concepts](docs/core-concepts/wcf-core-components.md) for detailed framework documentation.

## Development

### Testing

```bash
uv run pytest                       # Run all tests
uv run pytest -v                    # Verbose output
uv run pytest -m integration        # Integration tests (requires API keys)
```

### Quality Checks

Package-centric architecture where each package owns its configuration:

```bash
# Workspace-level (all packages)
./scripts/lint.sh               # Lint all packages
./scripts/format.sh             # Format all packages
./scripts/type-check.sh         # Type check all packages
./scripts/dev-checks.sh         # Run all checks + tests

# Package-level
cd libs/waivern-core && ./scripts/lint.sh
cd apps/wct && ./scripts/type-check.sh

# Pre-commit hooks
uv run pre-commit install         # Install (once)
uv run pre-commit run --all-files # Run manually
```

### Creating Components

Components use the ComponentFactory pattern with dependency injection:

#### Connector Example

```python
from typing import override
from pydantic import BaseModel
from waivern_core import Connector, Message, Schema, ComponentFactory
from waivern_core.schemas import StandardInputSchema

class MyConnectorConfig(BaseModel):
    """Configuration for MyConnector."""
    path: str
    encoding: str = "utf-8"

class MyConnector(Connector):
    def __init__(self, config: MyConnectorConfig):
        self.config = config

    @classmethod
    @override
    def get_name(cls) -> str:
        return "my_connector"

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [StandardInputSchema()]

    @override
    def extract(self, output_schema: Schema) -> Message:
        data = {"text": "extracted_content"}
        return Message(
            id="connector_output",
            content=data,
            schema=StandardInputSchema()
        )

class MyConnectorFactory(ComponentFactory[MyConnector]):
    @override
    def create(self, properties: dict) -> MyConnector:
        config = MyConnectorConfig.from_properties(properties)
        return MyConnector(config)
```

#### Processor Example

```python
from typing import override
from pydantic import BaseModel
from waivern_core import Analyser, Message, Schema, ComponentFactory, InputRequirement

class MyAnalyserConfig(BaseModel):
    """Configuration for MyAnalyser."""
    threshold: float = 0.8

class MyAnalyser(Analyser):
    def __init__(self, config: MyAnalyserConfig):
        self.config = config

    @classmethod
    @override
    def get_name(cls) -> str:
        return "my_analyser"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        # Declare supported input schema combinations
        return [[InputRequirement("standard_input", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [MyFindingSchema()]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        # Process all input messages (supports fan-in)
        findings = []
        for message in inputs:
            findings.extend(self._analyse(message.content))

        return Message(
            id="results",
            content={"findings": findings},
            schema=output_schema
        )

class MyAnalyserFactory(ComponentFactory[MyAnalyser]):
    @override
    def create(self, properties: dict) -> MyAnalyser:
        config = MyAnalyserConfig.from_properties(properties)
        return MyAnalyser(config)
```

**Key Features:**
- ComponentFactory pattern for instantiation
- Configuration via Pydantic models
- Dependency injection support
- Automatic schema validation
- Type-safe interfaces

## IDE Support

Runbooks support JSON Schema validation for:
- Real-time validation
- Autocomplete
- Documentation on hover
- Structure guidance

📖 **Setup:** [IDE Integration Guide](docs/how-tos/ide-integration.md)

## Contributing

1. Fork the repository
2. Create a feature branch (`feature/your-feature-name`)
3. Make your changes
4. Run quality checks: `./scripts/dev-checks.sh`
5. Submit a pull request

### Code Standards

- Type annotations required (basedpyright strict mode)
- Code formatting with ruff
- Security checks with bandit
- Comprehensive test coverage

Run `./scripts/dev-checks.sh` before committing.

## Documentation

- **[WCF Core Concepts](docs/core-concepts/wcf-core-components.md)** - Framework architecture
- **[Configuration Guide](docs/how-tos/configuration.md)** - Environment configuration
- **[Runbook Documentation](apps/wct/runbooks/README.md)** - Runbook usage

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE.txt) file for details.

## Support

### Community Support

🔗 **[Discord Server](https://discord.gg/wj2RV4zUYM)**

- General help and installation support
- Development discussions
- Bug reports and feature requests
- Community showcase

### Other Channels

- **GitHub Issues** - [Report bugs and request features](https://github.com/waivern-compliance/waivern-compliance/issues)
- **GitHub Discussions** - General questions and community discussions
