"""WCT Rulesets package for compliance pattern definitions."""

from waivern_core import RulesetError

from waivern_community.rulesets.base import (
    RulesetLoader,
    RulesetNotFoundError,
    RulesetRegistry,
)

# Import rule types for registration
from waivern_community.rulesets.data_collection import (
    DataCollectionRule,
    DataCollectionRuleset,
)
from waivern_community.rulesets.data_subjects import (
    DataSubjectRule,
    DataSubjectsRuleset,
)
from waivern_community.rulesets.personal_data import (
    PersonalDataRule,
    PersonalDataRuleset,
)
from waivern_community.rulesets.processing_purposes import (
    ProcessingPurposeRule,
    ProcessingPurposesRuleset,
)
from waivern_community.rulesets.service_integrations import (
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

__all__ = [
    "RulesetError",
    "RulesetLoader",
    "RulesetNotFoundError",
    "RulesetRegistry",
    # Rulesets
    "PersonalDataRuleset",
    "ProcessingPurposesRuleset",
    "DataCollectionRuleset",
    "ServiceIntegrationsRuleset",
    "DataSubjectsRuleset",
    # Rule types
    "PersonalDataRule",
    "ProcessingPurposeRule",
    "DataCollectionRule",
    "ServiceIntegrationRule",
    "DataSubjectRule",
]
