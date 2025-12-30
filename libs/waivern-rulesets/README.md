# waivern-rulesets

Compliance rulesets for Waivern Compliance Framework.

## Overview

This package provides GDPR and privacy compliance rulesets used by analysers:

- **personal_data**: Detects personal data patterns (GDPR Article 4)
- **processing_purposes**: Identifies data processing purposes (GDPR Article 30)
- **data_collection**: Detects data collection methods
- **service_integrations**: Identifies third-party service integrations
- **data_subjects**: Detects data subject categories

Each ruleset includes:
- Strongly-typed Pydantic rule models
- YAML-based pattern definitions
- GDPR compliance mappings
- Risk level assessments

## Installation

```bash
uv add waivern-rulesets
```

## Usage

```python
from waivern_rulesets import RulesetLoader, PersonalDataRule

# Load a ruleset using URI format: provider/name/version
rules = RulesetLoader.load_ruleset("local/personal_data/1.0.0", PersonalDataRule)

# Access rule properties
for rule in rules:
    print(f"{rule.name}: {rule.patterns}")
    print(f"Risk level: {rule.risk_level}")
    print(f"Special category: {rule.special_category}")
```

### Using the Registry

```python
from waivern_rulesets import RulesetRegistry, PersonalDataRuleset, PersonalDataRule

# Get a ruleset class from the registry
registry = RulesetRegistry()
ruleset_class = registry.get_ruleset_class("personal_data", PersonalDataRule)

# Instantiate and use
ruleset = ruleset_class()
print(f"Ruleset: {ruleset.name} v{ruleset.version}")
rules = ruleset.get_rules()
```

## Dependencies

- `waivern-core` - Core abstractions (BaseRule, RulesetData)
- `pydantic>=2.11.5` - Runtime validation
- `pyyaml>=6.0.2` - YAML ruleset loading

## Development

This package follows a **package-centric development approach**:

```bash
# From package directory
cd libs/waivern-rulesets

# Run quality checks
./scripts/lint.sh          # Lint this package
./scripts/format.sh        # Format this package
./scripts/type-check.sh    # Type check this package

# From workspace root
./scripts/dev-checks.sh    # Check all packages + run tests
```

### Package Configuration

Each package owns its complete quality tool configuration:
- **Type checking**: basedpyright in strict mode (`pyproject.toml`)
- **Linting/Formatting**: ruff with compliance-focused rules (`pyproject.toml`)
- **Scripts**: Package-specific quality check scripts (`scripts/`)

This enables independent development and ensures consistent standards across all packages.

## Ruleset Structure

Rulesets are stored as versioned YAML files:

```
src/waivern_rulesets/data/
├── personal_data/
│   └── 1.0.0/
│       └── personal_data.yaml
├── processing_purposes/
│   └── 1.0.0/
│       └── processing_purposes.yaml
...
```

Each YAML file defines:
- Ruleset metadata (name, version, description)
- List of rules with patterns
- GDPR compliance information
- Risk assessments

## License

Same as main waivern-compliance project
