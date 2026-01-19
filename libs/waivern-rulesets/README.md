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

### For WCF Components (Recommended)

WCF components (analysers, classifiers, etc.) should use `RulesetManager` from `waivern-analysers-shared`, which provides caching and is the standard API:

```python
from waivern_analysers_shared.utilities import RulesetManager
from waivern_rulesets import PersonalDataRule

# Load a ruleset using URI format: provider/name/version
rules = RulesetManager.get_rules("local/personal_data/1.0.0", PersonalDataRule)

# Access rule properties
for rule in rules:
    print(f"{rule.name}: {rule.patterns}")
    print(f"Data type: {rule.data_type}")
```

### For Internal/Testing Use

`RulesetLoader` is the low-level loader used internally by `RulesetManager`. Direct usage is appropriate for testing utilities and internal infrastructure:

```python
from waivern_rulesets import RulesetLoader, PersonalDataRule

# Direct loading (no caching) - use for tests or internal utilities
rules = RulesetLoader.load_ruleset("local/personal_data/1.0.0", PersonalDataRule)
```

## Dependencies

- `waivern-core` - Core abstractions (Rule, DetectionRule, ClassificationRule, RulesetData)
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

## Package Structure

Each ruleset is a self-contained directory with its implementation and data:

```
src/waivern_rulesets/
├── core/                              # Infrastructure (internal)
│   ├── base.py                        # AbstractRuleset, YAMLRuleset
│   ├── registry.py                    # RulesetRegistry
│   ├── loader.py                      # RulesetLoader
│   ├── uri.py                         # RulesetURI
│   └── exceptions.py                  # All errors
├── personal_data_indicator/           # Each ruleset is self-contained
│   ├── __init__.py
│   ├── ruleset.py
│   └── data/1.0.0/personal_data_indicator.yaml
├── processing_purposes/
│   ├── __init__.py
│   ├── ruleset.py
│   └── data/1.0.0/processing_purposes.yaml
├── ...                                # Other rulesets follow same pattern
├── protocols.py                       # Protocol definitions
├── types.py                           # Type definitions
├── testing.py                         # Contract test utilities
└── __init__.py                        # Re-exports public API
```

Each YAML file defines:
- Ruleset metadata (name, version, description)
- List of rules with patterns
- GDPR compliance information
- Risk assessments

## License

Same as main waivern-compliance project
