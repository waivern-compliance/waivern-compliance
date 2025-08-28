"""WCT Rulesets package for compliance pattern definitions."""

from wct.rulesets.base import (
    RulesetError,
    RulesetLoader,
    RulesetNotFoundError,
    RulesetRegistry,
)
from wct.rulesets.data_collection import DataCollectionRuleset
from wct.rulesets.personal_data import PersonalDataRuleset
from wct.rulesets.processing_purposes import ProcessingPurposesRuleset
from wct.rulesets.service_integrations import ServiceIntegrationsRuleset

# Import rule types for registration
from wct.rulesets.types import (
    DataCollectionRule,
    PersonalDataRule,
    ProcessingPurposeRule,
    ServiceIntegrationRule,
)

# Built-in rulesets with their corresponding rule types
_BUILTIN_RULESETS = [
    ("personal_data", PersonalDataRuleset, PersonalDataRule),
    ("processing_purposes", ProcessingPurposesRuleset, ProcessingPurposeRule),
    ("data_collection", DataCollectionRuleset, DataCollectionRule),
    ("service_integrations", ServiceIntegrationsRuleset, ServiceIntegrationRule),
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
