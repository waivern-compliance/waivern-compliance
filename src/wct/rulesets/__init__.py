"""WCT Rulesets package for compliance pattern definitions."""

from wct.rulesets.base import (
    RulesetError,
    RulesetLoader,
    RulesetNotFoundError,
    RulesetRegistry,
)

# Import rule types for registration
from wct.rulesets.data_collection import DataCollectionRule, DataCollectionRuleset
from wct.rulesets.data_subjects import DataSubjectRule, DataSubjectsRuleset
from wct.rulesets.personal_data import PersonalDataRule, PersonalDataRuleset
from wct.rulesets.processing_purposes import (
    ProcessingPurposeRule,
    ProcessingPurposesRuleset,
)
from wct.rulesets.service_integrations import (
    ServiceIntegrationRule,
    ServiceIntegrationsRuleset,
)

# Built-in rulesets with their corresponding rule types
_BUILTIN_RULESETS = [
    ("personal_data", PersonalDataRuleset, PersonalDataRule),
    ("processing_purposes", ProcessingPurposesRuleset, ProcessingPurposeRule),
    ("data_collection", DataCollectionRuleset, DataCollectionRule),
    ("service_integrations", ServiceIntegrationsRuleset, ServiceIntegrationRule),
    ("data_subjects", DataSubjectsRuleset, DataSubjectRule),
]

# Register all built-in rulesets automatically on import with type information
_registry = RulesetRegistry()
for _ruleset_name, _ruleset_class, _rule_type in _BUILTIN_RULESETS:
    _registry.register(_ruleset_name, _ruleset_class, _rule_type)

__all__ = (
    "RulesetError",
    "RulesetLoader",
    "RulesetNotFoundError",
)
