"""Waivern Compliance Framework - Rulesets package."""

from waivern_core import RulesetError

# Core infrastructure
from waivern_rulesets.core import (
    AbstractRuleset,
    RulesetLoader,
    RulesetNotFoundError,
    RulesetRegistry,
    RulesetURI,
    RulesetURIParseError,
    UnsupportedProviderError,
)

# Detection rulesets
from waivern_rulesets.data_collection import (
    DataCollectionRule,
    DataCollectionRuleset,
)
from waivern_rulesets.data_subject_indicator import (
    DataSubjectIndicatorRule,
    DataSubjectIndicatorRuleset,
)

# Classification rulesets
from waivern_rulesets.gdpr_data_subject_classification import (
    GDPRDataSubjectClassificationRule,
    GDPRDataSubjectClassificationRuleset,
    RiskModifiers,
)
from waivern_rulesets.gdpr_personal_data_classification import (
    GDPRPersonalDataClassificationRule,
    GDPRPersonalDataClassificationRuleset,
)
from waivern_rulesets.personal_data_indicator import (
    PersonalDataIndicatorRule,
    PersonalDataIndicatorRuleset,
)
from waivern_rulesets.processing_purposes import (
    ProcessingPurposeRule,
    ProcessingPurposesRuleset,
)

# Protocols
from waivern_rulesets.protocols import DataSubjectClassificationRulesetProtocol
from waivern_rulesets.service_integrations import (
    ServiceIntegrationRule,
    ServiceIntegrationsRuleset,
)

# Built-in rulesets with their corresponding rule types
# Each ruleset class must define ruleset_name and ruleset_version ClassVars
_BUILTIN_RULESETS = [
    (PersonalDataIndicatorRuleset, PersonalDataIndicatorRule),
    (ProcessingPurposesRuleset, ProcessingPurposeRule),
    (DataCollectionRuleset, DataCollectionRule),
    (ServiceIntegrationsRuleset, ServiceIntegrationRule),
    (DataSubjectIndicatorRuleset, DataSubjectIndicatorRule),
    (GDPRPersonalDataClassificationRuleset, GDPRPersonalDataClassificationRule),
    (GDPRDataSubjectClassificationRuleset, GDPRDataSubjectClassificationRule),
]

# Register all built-in rulesets automatically on import with type information
_registry = RulesetRegistry()
for _ruleset_class, _rule_type in _BUILTIN_RULESETS:
    _registry.register(_ruleset_class, _rule_type)

__all__ = [
    # Errors
    "RulesetError",
    "RulesetNotFoundError",
    "RulesetURIParseError",
    "UnsupportedProviderError",
    # URI and Loader
    "RulesetURI",
    "RulesetLoader",
    # Base classes
    "AbstractRuleset",
    # Protocols
    "DataSubjectClassificationRulesetProtocol",
    # Rulesets
    "PersonalDataIndicatorRuleset",
    "ProcessingPurposesRuleset",
    "DataCollectionRuleset",
    "ServiceIntegrationsRuleset",
    "DataSubjectIndicatorRuleset",
    "GDPRPersonalDataClassificationRuleset",
    "GDPRDataSubjectClassificationRuleset",
    # Rule types
    "PersonalDataIndicatorRule",
    "ProcessingPurposeRule",
    "DataCollectionRule",
    "ServiceIntegrationRule",
    "DataSubjectIndicatorRule",
    "GDPRPersonalDataClassificationRule",
    "GDPRDataSubjectClassificationRule",
    # Supporting types
    "RiskModifiers",
]
