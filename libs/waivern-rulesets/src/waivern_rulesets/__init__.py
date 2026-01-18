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

# Auto-discover and register all rulesets from entry points
# Each ruleset declares an entry point in pyproject.toml under [project.entry-points."waivern.rulesets"]
# The rule type is extracted automatically from the generic parameter
_registry = RulesetRegistry()
_registry.discover_from_entry_points()

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
