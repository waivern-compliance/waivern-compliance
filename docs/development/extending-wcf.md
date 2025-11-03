# Extending the Waivern Compliance Framework

**Last Updated:** 2025-11-03
**Related:** [Building Custom Components](building-custom-components.md), [Remote Analyser Protocol](../architecture/remote-analyser-protocol.md)

## Overview

The Waivern Compliance Framework (WCF) is designed to be extended. This document explains the extensibility points and how you can build on top of WCF to create custom compliance solutions.

## Prerequisites

Before extending WCF, you should be familiar with:

- **[WCF Core Components](../core-concepts/wcf-core-components.md)** - Understanding of connectors, analysers, schemas, and messages
- **[Runbooks Documentation](../../apps/wct/runbooks/README.md)** - How WCT orchestrates components
- **Python 3.12+** - Modern Python features and type hints
- **Dependency Injection** - ComponentFactory and ServiceContainer patterns

**Recommended reading order:**
1. [WCF Core Components](../core-concepts/wcf-core-components.md) - Start here
2. This document - Understand extension mechanisms
3. [Building Custom Components](building-custom-components.md) - Detailed implementation guide
4. [Remote Analyser Protocol](../architecture/remote-analyser-protocol.md) - For remote execution

## WCF Extensibility Model

WCF provides three primary extension mechanisms:

1. **Component Development** - Create custom connectors, analysers, and rulesets
2. **Entry Points** - Automatic component discovery via Python entry points
3. **Remote Execution** - Host analysers as HTTP services

## Component Development

### Creating Custom Components

You can extend WCF by creating your own components:

**Connectors** - Extract data from custom sources:
```python
from waivern_core.connector import Connector, ConnectorConfig

class MyConnector(Connector):
    def extract(self) -> Message:
        # Extract from your data source
        pass
```

**Analysers** - Implement custom compliance checks:
```python
from waivern_core.analyser import Analyser, AnalyserConfig

class MyAnalyser(Analyser):
    def process_data(self, message: Message) -> Message:
        # Your compliance analysis logic
        pass
```

**Rulesets** - Define pattern-based detection rules:
```yaml
# my-ruleset.yaml
name: "My Custom Ruleset"
patterns:
  - pattern: "credit-card-number"
    regex: '\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'
```

**See:** [Building Custom Components](building-custom-components.md) for detailed implementation guide.

## Entry Points System

### Automatic Discovery

WCF uses Python entry points for automatic component discovery. When you install a package with registered entry points, WCT automatically discovers and makes those components available.

### Registering Your Components

```toml
# your-package/pyproject.toml
[project.entry-points."waivern.connectors"]
my_connector = "my_package:create_my_connector_factory"

[project.entry-points."waivern.analysers"]
my_analyser = "my_package:create_my_analyser_factory"

[project.entry-points."waivern.rulesets"]
my_ruleset = "my_package:create_my_ruleset_factory"
```

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
$ wct ls-connectors
Available Connectors:
[local] mysql
[local] sqlite
[local] filesystem
[local] my_connector  ← Your custom connector!
```

**See:** [Entry Points Epic (#188)](https://github.com/waivern-compliance/waivern-compliance/issues/188) for the implementation roadmap.

## Remote Execution Model

### Overview

WCF supports remote analyser execution via HTTP API. This enables:
- Analysers hosted as microservices
- Scalable deployment architectures
- Hybrid local/remote workflows
- Third-party hosted services

### Remote Analyser Protocol

Analysers can be hosted as HTTP services that implement the WCF remote analyser protocol:

```yaml
# runbook.yaml
analysers:
  - name: "remote_analyser"
    type: "custom_analyser"
    execution:
      mode: "remote"
      endpoint: "https://my-analyser-service.com/api/v1"
      authentication:
        type: "api_key"
        key: "${MY_API_KEY}"
```

When WCT encounters a remote analyser:
1. Serialises the input Message to JSON
2. POSTs to the remote endpoint
3. Validates the response against the output schema
4. Continues execution with the result

### Building Remote Analysers

Your service must implement the WCF remote analyser protocol. All analyses are asynchronous:

```http
POST /v1/analysers/{analyser_type}/execute
Content-Type: application/json
Accept: text/event-stream  # or application/json for polling
Authorization: Bearer {api_key}

{
  "request_id": "uuid-1234-5678",
  "message": {
    "id": "msg-5678-1234",
    "content": { /* analysis data */ },
    "schema": {
      "name": "standard_input",
      "version": "1.0.0"
    }
  }
}

→ Response (Streaming via SSE):
HTTP/1.1 202 Accepted
Content-Type: text/event-stream

event: started
data: {"request_id":"uuid-1234-5678","status":"processing"}

event: completed
data: {"request_id":"uuid-1234-5678","result_url":"/v1/analysers/results/uuid-1234-5678"}

→ Fetch Result:
GET /v1/analysers/results/uuid-1234-5678

{
  "request_id": "uuid-1234-5678",
  "message": {
    "id": "msg-5678-1234",
    "content": { /* findings */ },
    "schema": {
      "name": "my_finding",
      "version": "1.0.0"
    }
  }
}
```

**See:** [Remote Analyser Protocol](../architecture/remote-analyser-protocol.md) for complete API specification.

### Discovery Endpoint

Remote services should expose a discovery endpoint:

```
GET /v1/analysers

→ Response:
{
  "analysers": [
    {
      "name": "custom_analyser",
      "type": "custom_analyser",
      "version": "1.0.0",
      "supported_input_schemas": [
        {"name": "standard_input", "version": "1.0.0"}
      ],
      "supported_output_schemas": [
        {"name": "my_finding", "version": "1.0.0"}
      ]
    }
  ]
}
```

## Remote Rulesets

### Overview

In addition to remote analysers, WCF supports **remote rulesets** - pattern-based detection rules hosted as HTTP services. This enables:
- Expert-curated compliance patterns (legal, regulatory, industry-specific)
- Regularly updated pattern libraries without package reinstalls
- Monetisation of compliance expertise by legal and regulatory professionals
- Hybrid approach: run analysers locally with premium patterns

### Use Case

OSS analysers (e.g., `personal_data_analyser`) can use either:
- **Local rulesets**: Free, community-maintained patterns installed via pip packages
- **Remote rulesets**: Premium, expert-curated patterns accessed via API key

This provides a **low-friction upgrade path** - users keep their local setup but gain access to professional-grade patterns.

### Configuration

Configure analysers to use remote rulesets:

```yaml
# runbook.yaml
analysers:
  - name: "personal_data_checker"
    type: "personal_data_analyser"
    properties:
      ruleset:
        source: "remote"
        endpoint: "https://api.example.com/v1/rulesets"
        ruleset_name: "gdpr_personal_data_patterns"
        version: "2024.11"
        authentication:
          type: "api_key"
          key: "${PATTERNS_API_KEY}"
        cache:
          enabled: true
          ttl_seconds: 3600
```

### Remote Ruleset Protocol

Remote ruleset services should implement a simple HTTP API:

```http
GET /v1/rulesets/{ruleset_name}
Authorization: Bearer {api_key}
Accept: application/json

→ Response:
{
  "name": "gdpr_personal_data_patterns",
  "version": "2024.11",
  "description": "GDPR personal data detection patterns curated by legal experts",
  "patterns": [
    {
      "pattern": "email_address",
      "regex": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
      "category": "contact_information",
      "confidence": 0.95
    },
    {
      "pattern": "uk_national_insurance",
      "regex": "[A-Z]{2}\\d{6}[A-D]",
      "category": "government_identifier",
      "confidence": 0.98
    }
  ],
  "metadata": {
    "last_updated": "2024-11-01",
    "jurisdiction": "EU",
    "regulation": "GDPR"
  }
}
```

### Value Proposition

**For Legal/Compliance Professionals:**
- Monetise regulatory expertise without building full analysers
- Maintain authoritative pattern libraries
- Provide jurisdiction-specific compliance patterns
- Regular updates as regulations evolve

**For Users:**
- Access expert-curated patterns with minimal setup
- No package reinstalls for pattern updates
- Pay only for what you use
- Run locally (no data leaves your infrastructure)

**For Third-Party Service Providers:**
- Offer industry-specific pattern libraries (healthcare, financial services, etc.)
- Build subscription-based compliance pattern services
- Integrate with existing compliance tools

### Example: Upgrading OSS Analyser with Premium Patterns

```yaml
# Before: Using free community patterns
analysers:
  - name: "basic_checker"
    type: "personal_data_analyser"
    # Uses built-in OSS rulesets

# After: Upgrade to expert patterns with API key
analysers:
  - name: "expert_checker"
    type: "personal_data_analyser"
    properties:
      ruleset:
        source: "remote"
        endpoint: "https://legal-patterns.example.com/v1/rulesets"
        ruleset_name: "gdpr_legal_expert_patterns"
        authentication:
          api_key: "${LEGAL_PATTERNS_KEY}"
```

Same analyser, better patterns - no code changes required!

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

### Self-Hosted Services

Deploy your analysers as HTTP services:

```bash
# Your service
uvicorn my_analyser.api:app --host 0.0.0.0 --port 8000

# Users configure endpoint in runbook
analysers:
  - name: "my_analyser"
    execution:
      endpoint: "https://my-analyser.example.com"
```

### Hybrid Models

Combine local and remote components:

```yaml
analysers:
  # Local analyser (entry point)
  - name: "pattern_matcher"
    type: "personal_data_analyser"
    properties:
      pattern_matching:
        enable: true

  # Remote analyser (your hosted service)
  - name: "advanced_validator"
    type: "my_advanced_analyser"
    execution:
      mode: "remote"
      endpoint: "https://api.mycompany.com"

execution:
  # Pattern match locally (fast, cheap)
  - connector: "database"
    analyser: "pattern_matcher"
    output: "candidates"

  # Validate remotely (your proprietary logic)
  - analyser: "advanced_validator"
    inputs: ["candidates"]
    output: "validated_findings"
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

### Schema Discovery

Place schemas in your package:
```
my-package/
└── schemas/
    └── json_schemas/
        └── my_custom_finding/
            └── 1.0.0/
                └── my_custom_finding.json
```

WCF discovers schemas automatically from installed packages.

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
3. **Authentication** - Secure remote endpoints
4. **Rate limiting** - Protect remote services
5. **API versioning** - Support backward compatibility

## Example: Building a Custom Compliance Package

Complete example structure:

```
my-compliance-package/
├── src/
│   └── my_compliance/
│       ├── __init__.py           # Entry point functions
│       ├── connector.py          # Custom connector
│       ├── analyser.py           # Custom analyser
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

[project.entry-points."waivern.analysers"]
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

## Related Documentation

- [Building Custom Components](building-custom-components.md) - Detailed implementation guide
- [Remote Analyser Protocol](../architecture/remote-analyser-protocol.md) - HTTP API specification
- [WCF Core Components](../core-concepts/wcf-core-components.md) - Framework architecture
- [Entry Points Epic (#188)](https://github.com/waivern-compliance/waivern-compliance/issues/188) - Discovery mechanism

## Enterprise Extensions

> **Note:** For enterprise deployment options and commercial offerings, visit https://www.waivern.com

Third-party developers can build and distribute their own premium components using the patterns
described in this guide.
