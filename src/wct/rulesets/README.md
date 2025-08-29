# WCT Rulesets

Versioned static rulesets for WCT's compliance analysis.

## Architecture

```
src/wct/rulesets/
├── data/                      # Versioned ruleset data files
│   ├── data_collection/1.0.0/data_collection.yaml
│   ├── personal_data/1.0.0/personal_data.yaml
│   ├── processing_purposes/1.0.0/processing_purposes.yaml
│   └── service_integrations/1.0.0/service_integrations.yaml
├── base.py                    # Abstract base class and registry
├── types.py                   # Shared types (RulesetData, RuleData, RuleComplianceData)
├── {ruleset_name}.py          # Python loaders for rulesets
└── README.md
```

**Key Features:**
- **External Configuration**: Business teams can update ruleset data independently of code
- **Versioned**: Each ruleset has semantic versioning (`data/{name}/{version}/{name}.yaml`)
- **Type-Safe**: Ruleset data validation ensures data integrity
- **Compliance-Ready**: Version tracking for regulatory audit trails

## Available Rulesets

### 📊 `data_collection` (9 categories, 35 patterns)
Detects technical data collection mechanisms (PHP POST/GET, JavaScript, HTML forms, APIs, database connections).

### 🔍 `personal_data` (18 categories, 270+ patterns)
GDPR-compliant personal data detection including Article 9 special categories (health, biometric, genetic data).

### 🎯 `processing_purposes` (20 categories, 180+ patterns)
Business processing purposes for GDPR Article 6 lawful basis (AI/ML, operational, analytics, marketing, security).

### 🔗 `service_integrations` (6 categories, 58 patterns)
Third-party service integrations for GDPR Article 28 processor compliance (cloud, communication, identity, payments, analytics, social media).

## Quick Usage

```python
from wct.rulesets import RulesetLoader

# Load any ruleset (loads from versioned YAML automatically)
rules = RulesetLoader.load_ruleset("personal_data")

for rule in rules:
    print(f"{rule.name}: {len(rule.patterns)} patterns")
    print(f"Risk: {rule.risk_level}")
    print(f"Compliance: {[c.regulation for c in rule.compliance]}")
```

## Creating New Rulesets

### 1. Create Ruleset Data
```yaml
# data/your_ruleset/1.0.0/your_ruleset.yaml
name: "your_ruleset"
version: "1.0.0"
description: "What this detects"

rules:
  category_name:
    description: "Specific detection purpose"
    patterns: ["pattern1", "pattern2"]
    risk_level: "medium"
    compliance:
      - regulation: "GDPR"
        relevance: "Article reference and explanation"
    metadata:
      special_category: "N"
```

### 2. Create Python Loader
```python
from pathlib import Path
from typing import Final
import yaml
from wct.rulesets.base import AbstractRuleset
from wct.rulesets.types import Rule, RulesetData

_RULESET_DATA_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "your_ruleset"

class YourRuleset(Ruleset):
    @property
    def name(self) -> str:
        return _RULESET_NAME

    @property
    def version(self) -> str:
        return _RULESET_DATA_VERSION

    def get_rules(self) -> tuple[Rule, ...]:
        if self.rules is None:
            yaml_file = Path(__file__).parent / "data" / _RULESET_NAME / _RULESET_DATA_VERSION / f"{_RULESET_NAME}.yaml"
            with yaml_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            ruleset_data = RulesetData(**data)
            self.rules = ruleset_data.to_rules()
        return self.rules
```

## Version Management

**Updating rulesets:**
1. Create new version: `data/ruleset_name/1.1.0/ruleset_name.yaml`
2. Update version constant: `_RULESET_DATA_VERSION = "1.1.0"`
3. Deploy together (class version must match YAML version)

**Benefits:**
- Business-driven ruleset updates without code changes
- Clear audit trail for compliance
- Easy rollback by changing version constant
- A/B testing different versions

## Testing

```bash
# Test all rulesets (includes YAML loading and Pydantic validation)
uv run pytest tests/wct/rulesets/ -v

# Type checking and linting
uv run basedpyright src/wct/rulesets/
uv run ruff check src/wct/rulesets/
```

## GDPR Compliance

All rulesets include comprehensive compliance mappings:
- **GDPR Article 9 special categories** properly marked with detailed compliance relevance
- **Multi-framework coverage**: GDPR, EU AI Act, CCPA/CPRA, PCI DSS, SOX, ePrivacy, COPPA, NIST AI RMF
- **Structured compliance data** with regulation references and specific article explanations

---

**Quality rulesets = accurate compliance analysis** 🎯
