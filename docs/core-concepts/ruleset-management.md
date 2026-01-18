# Ruleset Management

This guide explains how rulesets are loaded, cached, and used in WCF. Understanding this architecture helps when building analysers or debugging ruleset-related issues.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Your Analyser                           │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  RulesetManager (waivern-analysers-shared)                      │
│  ─────────────────────────────────────────                      │
│  • Caches loaded rulesets                                       │
│  • Prevents redundant loading during analysis                   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  RulesetLoader (waivern-rulesets)                               │
│  ────────────────────────────────                               │
│  • Parses URIs (provider/name/version)                          │
│  • Validates provider support                                   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  RulesetRegistry (waivern-rulesets)                             │
│  ─────────────────────────────────                              │
│  • Singleton registry of ruleset classes                        │
│  • Maps names → classes and rule types                          │
│  • Runtime type validation                                      │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  AbstractRuleset[T] implementations                             │
│  ──────────────────────────────────                             │
│  • PersonalDataIndicatorRuleset                                 │
│  • ProcessingPurposeRuleset                                     │
│  • GDPRDataSubjectClassificationRuleset (implements Protocol)   │
│  • etc.                                                         │
└─────────────────────────────────────────────────────────────────┘
```

**Why two packages?** `RulesetManager` lives in `waivern-analysers-shared` (not `waivern-rulesets`) to avoid circular dependencies—analysers depend on rulesets, and the caching layer is an analyser concern.

## URI Format

Rulesets are identified by URIs in the format:

```
{provider}/{name}/{version}
```

**Examples:**
- `local/personal_data/1.0.0`
- `local/processing_purposes/1.0.0`
- `local/gdpr_data_subject_classification/1.0.0`

**Currently supported providers:**
- `local` — Loads from bundled `waivern-rulesets` package

## Usage Patterns

### Pattern 1: Factory Validation

Validate that a ruleset exists before creating an analyser:

```python
from waivern_analysers_shared.utilities import RulesetManager
from waivern_rulesets import PersonalDataRule

# In factory.can_create()
try:
    RulesetManager.get_ruleset(config.ruleset, PersonalDataRule)
    return True
except (RulesetURIParseError, UnsupportedProviderError, RulesetNotFoundError):
    return False
```

### Pattern 2: Loading Rules for Analysis

Get rules for pattern matching:

```python
rules = RulesetManager.get_rules("local/personal_data/1.0.0", PersonalDataRule)

for rule in rules:
    if rule.matches(content):
        # Found a match
```

### Pattern 3: Full Ruleset Access

When you need more than just rules (e.g., risk modifiers):

```python
from typing import cast
from waivern_rulesets import (
    GDPRDataSubjectClassificationRule,
    DataSubjectClassificationRulesetProtocol,
)

ruleset = RulesetManager.get_ruleset(
    "local/gdpr_data_subject_classification/1.0.0",
    GDPRDataSubjectClassificationRule,
)

# Cast to protocol for extended interface
ruleset = cast(DataSubjectClassificationRulesetProtocol, ruleset)
risk_modifiers = ruleset.get_risk_modifiers()
```

## Protocols vs Concrete Classes

Some rulesets provide extended interfaces beyond `AbstractRuleset`. These are defined as **protocols** (structural subtyping):

| Protocol | Adds | Used By |
|----------|------|---------|
| `DataSubjectClassificationRulesetProtocol` | `get_risk_modifiers()` | Data subject classifier |

**Why protocols?** They allow custom implementations without inheritance. Your custom ruleset just needs to implement the required methods—no base class needed.

```python
# Protocol defines the contract
class DataSubjectClassificationRulesetProtocol(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> str: ...
    def get_rules(self) -> tuple[GDPRDataSubjectClassificationRule, ...]: ...
    def get_risk_modifiers(self) -> RiskModifiers: ...  # Extended interface
```

## Caching Behaviour

`RulesetManager` caches by **URI + rule type**:

```python
# Cache key: "local/personal_data/1.0.0:PersonalDataRule"
RulesetManager.get_ruleset("local/personal_data/1.0.0", PersonalDataRule)

# Same ruleset, different type = separate cache entry
# Cache key: "local/multi_type/1.0.0:RuleTypeA"
# Cache key: "local/multi_type/1.0.0:RuleTypeB"
```

Clear the cache when needed (e.g., in tests):

```python
RulesetManager.clear_cache()
```

## Testing with Rulesets

### Registry Isolation

`RulesetRegistry` is a singleton with global state. Tests must isolate this state:

```python
import pytest
from waivern_rulesets import RulesetRegistry

@pytest.fixture(autouse=True)
def isolate_registry():
    """Prevent test pollution."""
    state = RulesetRegistry.snapshot_state()
    yield
    RulesetRegistry.restore_state(state)
```

> **Note:** The workspace-level `conftest.py` provides this fixture automatically for all tests.

### Registering Test Rulesets

```python
from waivern_rulesets import RulesetRegistry

# Register a custom ruleset for testing
RulesetRegistry.register(MyTestRuleset, MyTestRule)
```

## Common Errors

| Exception | Cause | Fix |
|-----------|-------|-----|
| `RulesetURIParseError` | Invalid URI format | Use `provider/name/version` format |
| `UnsupportedProviderError` | Unknown provider | Use `local` (only supported provider) |
| `RulesetNotFoundError` | Ruleset not registered | Check ruleset name spelling |
| `TypeError` | Rule type mismatch | Pass correct rule type for the ruleset |

**Debugging tip:** If `can_create()` returns `False` silently, call `RulesetManager.get_ruleset()` directly to see the actual exception.

## Quick Reference

```python
from waivern_analysers_shared.utilities import (
    RulesetManager,
    RulesetURI,
    RulesetURIParseError,
    UnsupportedProviderError,
)

# Get full ruleset instance (cached)
ruleset = RulesetManager.get_ruleset(uri, RuleType)

# Get just the rules (convenience method)
rules = RulesetManager.get_rules(uri, RuleType)

# Clear cache
RulesetManager.clear_cache()

# Parse URI components
parsed = RulesetURI.parse("local/personal_data/1.0.0")
print(parsed.provider, parsed.name, parsed.version)
```
