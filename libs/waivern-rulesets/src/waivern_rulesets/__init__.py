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
from waivern_rulesets.crypto_quality_indicator import (
    CryptoQualityIndicatorRule,
    CryptoQualityIndicatorRuleset,
)
from waivern_rulesets.data_collection import (
    DataCollectionRule,
    DataCollectionRuleset,
)
from waivern_rulesets.data_subject_indicator import (
    DataSubjectIndicatorRule,
    DataSubjectIndicatorRuleset,
)
from waivern_rulesets.gdpr_data_subject_classification import (
    GDPRDataSubjectClassificationRule,
    GDPRDataSubjectClassificationRuleset,
    RiskModifier,
    RiskModifiers,
)
from waivern_rulesets.gdpr_personal_data_classification import (
    GDPRPersonalDataClassificationRule,
    GDPRPersonalDataClassificationRuleset,
)
from waivern_rulesets.gdpr_processing_purpose_classification import (
    GDPRProcessingPurposeClassificationRule,
    GDPRProcessingPurposeClassificationRuleset,
)
from waivern_rulesets.gdpr_service_integration_classification import (
    GDPRServiceIntegrationClassificationRule,
    GDPRServiceIntegrationClassificationRuleset,
)
from waivern_rulesets.iso27001_domains import (
    ISO27001DomainsRule,
    ISO27001DomainsRuleset,
)
from waivern_rulesets.personal_data_indicator import (
    PersonalDataIndicatorRule,
    PersonalDataIndicatorRuleset,
)
from waivern_rulesets.personal_data_indicator_erp import PersonalDataIndicatorERPRuleset
from waivern_rulesets.processing_purposes import (
    ProcessingPurposeRule,
    ProcessingPurposesRuleset,
)
from waivern_rulesets.processing_purposes_erp import ProcessingPurposesERPRuleset
from waivern_rulesets.protocols import DataSubjectClassificationRulesetProtocol
from waivern_rulesets.security_control_indicator import (
    SecurityControlIndicatorRule,
    SecurityControlIndicatorRuleset,
)
from waivern_rulesets.security_control_indicator_erp import (
    SecurityControlIndicatorERPRuleset,
)
from waivern_rulesets.security_control_indicator_nodejs import (
    SecurityControlIndicatorNodejsRuleset,
)
from waivern_rulesets.security_evidence_domain_mapping import (
    SecurityEvidenceDomainMappingRule,
    SecurityEvidenceDomainMappingRuleset,
)
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
    # Detection rulesets
    "CryptoQualityIndicatorRuleset",
    "DataCollectionRuleset",
    "DataSubjectIndicatorRuleset",
    "PersonalDataIndicatorRuleset",
    "ProcessingPurposesRuleset",
    "ServiceIntegrationsRuleset",
    # Classification rulesets
    "GDPRDataSubjectClassificationRuleset",
    "GDPRPersonalDataClassificationRuleset",
    "GDPRProcessingPurposeClassificationRuleset",
    "GDPRServiceIntegrationClassificationRuleset",
    # Security rulesets
    "ISO27001DomainsRuleset",
    "SecurityControlIndicatorRuleset",
    "SecurityEvidenceDomainMappingRuleset",
    # Extension rulesets
    "PersonalDataIndicatorERPRuleset",
    "ProcessingPurposesERPRuleset",
    "SecurityControlIndicatorERPRuleset",
    "SecurityControlIndicatorNodejsRuleset",
    # Detection rule types
    "CryptoQualityIndicatorRule",
    "DataCollectionRule",
    "DataSubjectIndicatorRule",
    "PersonalDataIndicatorRule",
    "ProcessingPurposeRule",
    "ServiceIntegrationRule",
    # Classification rule types
    "GDPRDataSubjectClassificationRule",
    "GDPRPersonalDataClassificationRule",
    "GDPRProcessingPurposeClassificationRule",
    "GDPRServiceIntegrationClassificationRule",
    # Security rule types
    "ISO27001DomainsRule",
    "SecurityControlIndicatorRule",
    "SecurityEvidenceDomainMappingRule",
    # Supporting types
    "RiskModifier",
    "RiskModifiers",
]
