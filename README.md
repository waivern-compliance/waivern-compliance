# Waivern Compliance Framework

An open-source framework for automated compliance analysis across any technology stack and regulatory framework (GDPR, ePrivacy, EU AI Act, NIS2, DORA, etc.). Integrates directly into CI/CD pipelines to generate compliance documentation without manual questionnaires or spreadsheets.

## Overview

The Waivern Compliance Framework provides:

- **Framework Libraries** - Core abstractions, multi-provider LLM support, and built-in components
- **WCT (Waivern Compliance Tool)** - CLI application for orchestrating compliance analysis
- **Schema-Driven Architecture** - Type-safe component communication through JSON Schema
- **Extensible Design** - Open standards for connectors, analysers, and rulesets

### Core Components

- **Connectors** - Extract data from sources (MySQL, SQLite, files, source code)
- **Analysers** - Detect compliance issues (personal data, processing purposes, data subjects)
- **Rulesets** - YAML-based pattern definitions for static analysis
- **Runbooks** - YAML configurations defining analysis pipelines
- **Executor** - Orchestrates runbook execution with automatic schema matching

📋 **[Development Roadmap](docs/development_roadmap.md)** - Current progress and planned features

🚀 **[Contribution Opportunities](docs/development_roadmap.md#contribution-opportunities)** - Browse [good first issues](https://github.com/waivern-compliance/waivern-compliance/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

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
uv run wct ls-analysers

# Validate runbook
uv run wct validate-runbook apps/wct/runbooks/samples/file_content_analysis.yaml

# Generate JSON Schema for IDE support
uv run wct generate-schema
```

## Runbook Example

```yaml
name: "Personal Data Analysis"
description: "Detect personal data in files and databases"

connectors:
  - name: "filesystem_reader"
    type: "filesystem"
    properties:
      path: "./sample_file.txt"

analysers:
  - name: "content_analyser"
    type: "personal_data_analyser"
    properties:
      pattern_matching:
        ruleset: "personal_data"
        evidence_context_size: "medium"
      llm_validation:
        enable_llm_validation: true

execution:
  - connector: "filesystem_reader"
    analyser: "content_analyser"
    input_schema: "standard_input"
    output_schema: "personal_data_finding"
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
├── libs/                           # Framework libraries
│   ├── waivern-core/              # Core abstractions (Connector, Analyser, Schema, Message)
│   ├── waivern-llm/               # Multi-provider LLM (Anthropic, OpenAI, Google)
│   └── waivern-community/         # Built-in connectors, analysers, rulesets
└── apps/
    └── wct/                        # CLI application
        ├── runbooks/               # Runbook configurations
        ├── src/wct/                # Application code
        └── tests/                  # Application tests
```

**Framework Independence:**
- Libraries have no WCT dependencies
- Can be used by other applications
- Independent versioning and releases
- Clear separation of concerns

### Data Flow

```
Runbook (YAML) → Executor → Connector → Schema Validation → Analyser → Findings (JSON)
```

1. **Runbook** defines connectors, analysers, and execution steps
2. **Executor** loads and validates configuration
3. **Connectors** extract data and transform to WCF schemas
4. **Message objects** provide automatic schema validation
5. **Analysers** process data using rulesets and/or LLM validation
6. **Results** output as structured JSON

### Schema-Driven Design

- Components declare input/output schemas (JSON Schema format)
- Executor automatically matches schemas between connectors and analysers
- Runtime validation through Message objects
- Type-safe interfaces throughout

**See:** [WCF Core Concepts](docs/wcf_core_concepts.md) for detailed framework documentation.

## Development

### Testing

```bash
uv run pytest                       # Run all tests (738 tests)
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

#### Connector Example

```python
from typing import Any
from typing_extensions import Self, override
from waivern_core import Connector, Message
from waivern_core.schemas.base import WctSchema

class MyConnector(Connector[dict[str, Any]]):
    @classmethod
    @override
    def get_name(cls) -> str:
        return "my_connector"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls(**properties)

    @override
    def extract(self, schema: WctSchema[dict[str, Any]]) -> Message:
        data = {"data": "extracted_content"}
        return Message(
            id="connector_output",
            content=data,
            schema=self.get_output_schema()
        )

    @override
    def get_output_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="my_data", type=dict[str, Any])
```

#### Analyser Example

```python
from typing import Any
from typing_extensions import Self, override
from waivern_core import Analyser, Message
from waivern_core.schemas.base import WctSchema

class MyAnalyser(Analyser):
    @classmethod
    @override
    def get_name(cls) -> str:
        return "my_analyser"

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls(**properties)

    @override
    def process_data(self, message: Message) -> Message:
        # Input is automatically validated
        input_data = message.content

        # Perform analysis
        findings = self._analyse(input_data)

        # Return validated output
        return Message(
            id=f"results_{message.id}",
            content={"findings": findings},
            schema=self.get_output_schema()
        )

    @override
    def get_input_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="my_data", type=dict[str, Any])

    @override
    def get_output_schema(self) -> WctSchema[dict[str, Any]]:
        return WctSchema(name="my_results", type=dict[str, Any])
```

**Key Features:**
- Automatic validation via Message objects
- No manual validation needed
- Type-safe interfaces
- Schema-aware processing

## IDE Support

Runbooks support JSON Schema validation for:
- Real-time validation
- Autocomplete
- Documentation on hover
- Structure guidance

📖 **Setup:** [IDE Integration Guide](docs/ide-integration.md)

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
- Comprehensive test coverage (738 tests)
- British English spelling

Run `./scripts/dev-checks.sh` before committing.

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Development guide for AI assistants
- **[WCF Core Concepts](docs/wcf_core_concepts.md)** - Framework architecture
- **[Configuration Guide](docs/configuration.md)** - Environment configuration
- **[Runbook Documentation](apps/wct/runbooks/README.md)** - Runbook usage
- **[Migration History](docs/architecture/monorepo-migration-completed.md)** - Monorepo migration

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
