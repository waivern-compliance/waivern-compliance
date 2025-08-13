# WCT Rulesets

This directory contains the **rulesets** that power WCT's compliance analysis capabilities.

Rulesets define patterns and metadata for static analyses.

## Architecture Overview

WCT uses a **unified, consolidated ruleset architecture** designed for maintainability and comprehensive coverage:

```
src/wct/rulesets/
├── base.py                    # Abstract base class and registry
├── types.py                   # Type definitions and data structures
├── personal_data.py           # Personal data patterns
├── processing_purposes.py     # Processing purpose patterns
└── README.md                  # This file
```

### Key Design Principles

- **Single Source of Truth**: One unified ruleset per concept (no duplication)
- **Semantic Organisation**: Patterns grouped by meaningful categories, not technical distinctions
- **Immutable Returns**: All rulesets return immutable tuples for thread safety
- **Type Safety**: Full type annotation support with runtime validation
- **Security**: Registration overwrite protection prevents accidental overwrites

## Current Rulesets

### 📊 `personal_data.py` - Personal Data Detection
**The unified, optimized ruleset for all personal data patterns** (consolidated and deduplicated from 4 previous rulesets)

**Categories (19 total)**:
- `basic_profile` - Names, emails, addresses, phones (49 patterns)
- `account_data` - Subscriptions, transactions, memberships (14 patterns)
- `payment_data` - Billing, invoices, payment methods (13 patterns)
- `financial_data` - Bank details, credit cards, SSNs (32 patterns)
- `behavioral_event_data` - User interactions, analytics (23 patterns)
- `technical_device_and_network_data` - IPs, cookies, devices (32 patterns)
- `inferred_profile_data` - AI-generated user characteristics (5 patterns)
- `User_enriched_profile_data` - User-declared preferences (4 patterns)
- `location_data` - Countries, cities, regions (26 patterns)
- `user_generated_content` - Comments, reviews, messages (4 patterns)
- `accurate_location` - GPS, coordinates (GDPR Article 9) (24 patterns)
- `health_data` - Medical information (GDPR Article 9) (7 patterns)
- `political_data` - Political opinions (GDPR Article 9) (3 patterns)
- `racial_ethnic_data` - Racial/ethnic data (GDPR Article 9) (4 patterns)
- `religious_philosophical_data` - Religious beliefs (GDPR Article 9) (4 patterns)
- `genetic_data` - Genetic information (GDPR Article 9) (4 patterns)
- `biometric_data` - Fingerprints, face recognition (GDPR Article 9) (6 patterns)
- `sexual_orientation_data` - Sexual orientation (GDPR Article 9) (4 patterns)
- `date_of_birth` - Birth dates and age information (16 patterns)

**Pattern Optimization Features**:
- ✅ **Deduplicated patterns**: Removed 53+ redundant substring patterns for efficiency
- ✅ **Essential pattern preservation**: Core patterns like `"email"` retained despite algorithmic deduplication
- ✅ **Multi-context coverage**: Generic fields, SQL schemas, functions, and models
- ✅ **Smart pattern selection**: Longer, more specific patterns preferred over generic substrings

### 🎯 `processing_purposes.py` - GDPR Processing Purposes
Detects data processing purposes for GDPR Article 6 lawful basis analysis.

**Categories (14 total)**:
- `legitimate_interests`, `contract_performance`, `legal_compliance`
- `vital_interests`, `public_task`, `consent_based`
- `marketing`, `analytics`, `security`, `hr_employment`
- `research`, `legal_proceedings`, `regulatory_reporting`, `business_operations`

## Quick Start Guide

### Using Existing Rulesets

```python
from wct.rulesets import RulesetLoader
from wct.rulesets.personal_data import PersonalDataRuleset

# Load via registry (recommended)
rules = RulesetLoader.load_ruleset("personal_data")

# Direct instantiation
ruleset = PersonalDataRuleset()
print(f"Version: {ruleset.version}")  # e.g., "1.0.0"
print(f"Rule count: {len(ruleset.get_rules())}")

# Inspect patterns
for rule in rules:
    print(f"{rule.name}: {len(rule.patterns)} patterns")
    print(f"Risk: {rule.risk_level}")
    print(f"GDPR Special Category: {rule.metadata.get('special_category', 'N/A')}")
```

### Pattern Matching Example

```python
def detect_personal_data(content: str) -> list[str]:
    rules = RulesetLoader.load_ruleset("personal_data")
    matches = []

    content_lower = content.lower()
    for rule in rules:
        for pattern in rule.patterns:
            if pattern in content_lower:
                matches.append(f"{rule.name}:{pattern}")

    return matches

# Example usage
content = "Please update your email address and phone number"
matches = detect_personal_data(content)
# Returns: ["basic_profile:email", "basic_profile:phone"]
```

## Creating New Rulesets

### 1. Define Pattern Data Structure

```python
# In your_new_ruleset.py
from typing import Final
from wct.rulesets.types import RuleData

_NEW_PATTERNS: Final[dict[str, RuleData]] = {
    "category_name": {
        "description": "Clear description of what this detects",
        "patterns": (
            "pattern1", "pattern2", "pattern3"  # Use tuples for immutability
        ),
        "risk_level": "medium",  # "low", "medium", or "high"
        "metadata": {
            "special_category": "N",  # "Y" for GDPR Article 9, "N" otherwise
            "compliance_relevance": ["GDPR", "CCPA"],  # Relevant frameworks
            # Add custom metadata as needed
        },
    },
}
```

### 2. Implement Ruleset Class

```python
from typing_extensions import override
from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule

class YourNewRuleset(Ruleset):
    """Description of what this ruleset detects."""

    def __init__(self) -> None:
        """Initialise the ruleset."""
        super().__init__()
        self.rules: tuple[Rule, ...] | None = None

    @property
    @override
    def name(self) -> str:
        """Get the canonical name of this ruleset."""
        return "your_new_ruleset"  # Must be unique

    @property
    @override
    def version(self) -> str:
        """Get the version of this ruleset."""
        return "1.0.0"  # Semantic versioning

    @override
    def get_rules(self) -> tuple[Rule, ...]:
        """Get the rules defined by this ruleset."""
        if self.rules is None:
            rules_list: list[Rule] = []
            for rule_name, rule_data in _NEW_PATTERNS.items():
                rules_list.append(
                    Rule(
                        name=rule_name,
                        description=rule_data["description"],
                        patterns=rule_data["patterns"],
                        risk_level=rule_data["risk_level"],
                        metadata=rule_data["metadata"],
                    )
                )
            self.rules = tuple(rules_list)

        return self.rules
```

### 3. Register the Ruleset

```python
# In __init__.py, add your ruleset to imports and registration
from wct.rulesets.your_new_ruleset import YourNewRuleset

_BUILTIN_RULESETS = (
    PersonalDataRuleset,
    ProcessingPurposesRuleset,
    YourNewRuleset,  # Add here
)
```

### 4. Add Tests

```python
# In tests/wct/rulesets/test_your_new_ruleset.py
import pytest
from wct.rulesets.your_new_ruleset import YourNewRuleset
from wct.rulesets.types import Rule

class TestYourNewRuleset:
    def setup_method(self):
        self.ruleset = YourNewRuleset()

    def test_name_property_returns_canonical_name(self):
        assert self.ruleset.name == "your_new_ruleset"

    def test_version_property_follows_semver(self):
        version = self.ruleset.version
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_get_rules_returns_immutable_tuple(self):
        rules = self.ruleset.get_rules()
        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, Rule) for rule in rules)

    # Add more specific tests for your patterns
```

## Best Practices

### ✅ Do's

1. **Use Semantic Categories**: Group patterns by what they represent, not how they're used
   ```python
   # ✅ Good: Semantic grouping
   "contact_information": ["email", "phone", "address"]

   # ❌ Bad: Technical grouping
   "database_columns": ["email", "phone"], "form_fields": ["email", "phone"]
   ```

2. **Follow Immutability Patterns**: Use tuples for patterns, implement caching
   ```python
   # ✅ Good: Immutable patterns with caching
   "patterns": ("email", "phone"),  # Tuple
   if self.rules is None:  # Cache rules
       self.rules = tuple(rules_list)
   ```

3. **Include Comprehensive Metadata**: Add compliance relevance and special categories
   ```python
   # ✅ Good: Rich metadata
   "metadata": {
       "special_category": "Y",  # GDPR Article 9
       "compliance_relevance": ["GDPR", "CCPA", "UK_GDPR"],
       "data_sensitivity": "high"
   }
   ```

4. **Use Private Constants**: Keep internal data structures private
   ```python
   # ✅ Good: Private pattern data
   _YOUR_PATTERNS: Final[dict[str, RuleData]] = {...}
   _VERSION: Final[str] = "1.0.0"
   ```

### ❌ Don'ts

1. **Don't Create Duplicate Patterns**: Check existing rulesets first
2. **Don't Use Mutable Collections**: Always use tuples for patterns
3. **Don't Skip Tests**: Every ruleset must have comprehensive tests
4. **Don't Ignore Type Safety**: Use proper type annotations


## GDPR Compliance Notes

### Special Categories (Article 9)
All GDPR Article 9 special categories are properly marked with `"special_category": "Y"` and include comprehensive compliance coverage:

**Special Category Data Types**:
- **Health and medical data** - Includes EU AI Act compliance for AI health applications
- **Biometric data** (fingerprints, facial recognition) - Critical for AI identification systems
- **Genetic data** - DNA, genome sequences with AI Act coverage
- **Precise location data** (GPS coordinates) - GDPR-only due to specific location tracking rules
- **Racial/ethnic origin** - Enhanced with AI Act for bias prevention
- **Political opinions, religious beliefs** - AI Act relevant for content moderation
- **Sexual orientation** - Comprehensive privacy and AI compliance

### Enhanced Compliance Framework Coverage
The ruleset now includes comprehensive compliance relevance mapping:

**Primary Frameworks**:
- **GDPR**: EU General Data Protection Regulation (all categories)
- **EU_AI_ACT**: EU AI Act (special categories + AI-relevant data)
- **UK_GDPR**: UK implementation of GDPR (all special categories)
- **CCPA/CPRA**: California Consumer Privacy Act (behavioral/marketing data)
- **PCI_DSS**: Payment Card Industry standards (financial data)
- **SOX**: Sarbanes-Oxley Act (financial compliance)
- **ePrivacy**: EU ePrivacy Directive (cookies, tracking)
- **COPPA**: Children's Online Privacy Protection Act (age data)
- **NIST_AI_RMF**: NIST AI Risk Management Framework

**Strategic Compliance Integration**:
- All GDPR Article 9 categories now include `EU_AI_ACT` compliance relevance
- User-generated content includes AI Act coverage for training data compliance
- Cross-jurisdictional coverage with UK GDPR alignment
- AI-specific frameworks (NIST AI RMF) integrated where relevant

## Migration from Old Architecture

**If you're migrating code from the previous multi-ruleset architecture:**

```python
# ❌ Old way (4 separate rulesets)
personal_rules = RulesetLoader.load_ruleset("personal_data")
sql_rules = RulesetLoader.load_ruleset("personal_data_sql_schemas")
function_rules = RulesetLoader.load_ruleset("personal_data_code_functions")
model_rules = RulesetLoader.load_ruleset("personal_data_code_models")

# ✅ New way (unified ruleset)
unified_rules = RulesetLoader.load_ruleset("personal_data")  # Contains all patterns
```

**The unified `personal_data` ruleset now includes all patterns that were previously split across multiple files.**

## Testing Your Rulesets

```bash
# Run tests for specific ruleset
uv run pytest tests/wct/rulesets/test_your_ruleset.py -v

# Run all ruleset tests
uv run pytest tests/wct/rulesets/ -v

# Verify WCT loads your ruleset correctly
uv run wct ls-analysers  # Should show analysers using your patterns
```

## Contributing

1. **Follow the patterns above** for consistency
2. **Add comprehensive tests** - aim for >90% coverage
3. **Update this README** if you add new concepts
4. **Consider impact on existing analysers** that use patterns
5. **Test with real data** to validate pattern effectiveness

## Questions?

- Check existing rulesets for examples: `personal_data.py`, `processing_purposes.py`
- Review the base class: `base.py`
- Look at the test patterns: `tests/wct/rulesets/`
- See the main README: `CLAUDE.md` for development workflow

---

**Remember**: Rulesets are the foundation of WCT's detection capabilities. Quality patterns lead to accurate compliance analysis! 🎯
