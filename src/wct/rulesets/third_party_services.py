"""Third-party services ruleset.

This module defines patterns for detecting third-party service integrations
that commonly handle personal data, such as payment processors, analytics,
and communication services. The data_types reference personal_data ruleset categories.
"""

import logging
from typing import Final

from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RuleData

logger = logging.getLogger(__name__)

# Version constant for this ruleset (private)
_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "third_party_services"

_THIRD_PARTY_SERVICES: Final[dict[str, RuleData]] = {
    "payment_processors": {
        "description": "Payment processing service integrations",
        "patterns": (
            "stripe",
            "paypal",
            "square",
            "braintree",
            "authorize.net",
            "worldpay",
            "adyen",
            "payment",
            "charge",
            "billing",
        ),
        "risk_level": "high",
        "metadata": {
            "service_category": "payment_processing",
            "data_types": [
                "payment_data",
                "financial_data",
                "basic_profile",
            ],  # References personal_data categories
            "compliance_relevance": "Payment processors handle sensitive financial and personal data",
            "regulatory_impact": "PCI DSS, GDPR Article 25",
        },
    },
    "analytics_tracking": {
        "description": "User analytics and tracking service integrations",
        "patterns": (
            "google-analytics",
            "googleanalytics",
            "gtag",
            "mixpanel",
            "amplitude",
            "segment",
            "hotjar",
            "fullstory",
            "logrocket",
            "analytics",
            "tracking",
        ),
        "risk_level": "medium",
        "metadata": {
            "service_category": "user_analytics",
            "data_types": [
                "behavioral_event_data",
                "technical_device_and_network_data",
                "location_data",
            ],
            "compliance_relevance": "Analytics services collect user behavior and device data",
            "regulatory_impact": "GDPR Article 6, Cookie Directive",
        },
    },
    "social_media_platforms": {
        "description": "Social media platform integrations",
        "patterns": (
            "facebook",
            "fb.com",
            "twitter",
            "linkedin",
            "instagram",
            "tiktok",
            "youtube",
            "pinterest",
            "social",
        ),
        "risk_level": "medium",
        "metadata": {
            "service_category": "social_media",
            "data_types": [
                "basic_profile",
                "user_generated_content",
                "behavioral_event_data",
            ],
            "compliance_relevance": "Social media integrations may share user data with platforms",
            "regulatory_impact": "GDPR Article 26 (Joint Controllers)",
        },
    },
    "communication_services": {
        "description": "Email and communication service integrations",
        "patterns": (
            "sendgrid",
            "mailchimp",
            "mailgun",
            "postmark",
            "twilio",
            "slack",
            "discord",
            "intercom",
            "zendesk",
            "email",
            "sms",
            "notification",
        ),
        "risk_level": "medium",
        "metadata": {
            "service_category": "communication",
            "data_types": ["basic_profile", "user_generated_content"],
            "compliance_relevance": "Communication services process contact information and messages",
            "regulatory_impact": "GDPR Article 28 (Data Processors)",
        },
    },
    "cloud_storage": {
        "description": "Cloud storage and platform services",
        "patterns": (
            "aws",
            "amazon",
            "s3.amazonaws",
            "firebase",
            "gcp",
            "google.cloud",
            "azure",
            "microsoft",
            "dropbox",
            "storage",
            "upload",
        ),
        "risk_level": "medium",
        "metadata": {
            "service_category": "cloud_infrastructure",
            "data_types": [
                "basic_profile",
                "user_generated_content",
                "technical_device_and_network_data",
            ],
            "compliance_relevance": "Cloud services store and process user data",
            "regulatory_impact": "GDPR Article 28, Data Localisation Requirements",
        },
    },
    "authentication_services": {
        "description": "Third-party authentication and identity services",
        "patterns": (
            "auth0",
            "okta",
            "onelogin",
            "oauth",
            "openid",
            "saml",
            "azure.ad",
            "authenticate",
            "authorization",
            "identity",
        ),
        "risk_level": "high",
        "metadata": {
            "service_category": "identity_management",
            "data_types": ["basic_profile", "account_data"],
            "compliance_relevance": "Authentication services handle identity and credential data",
            "regulatory_impact": "GDPR Article 25 (Data Protection by Design)",
        },
    },
}


class ThirdPartyServicesRuleset(Ruleset):
    """Ruleset for detecting third-party service integrations in source code."""

    def __init__(self) -> None:
        """Initialise the third-party services ruleset."""
        super().__init__()
        self.rules: tuple[Rule, ...] | None = None
        logger.debug(f"Initialised {self.name} ruleset version {self.version}")

    @property
    @override
    def name(self) -> str:
        """Get the canonical name of this ruleset."""
        return _RULESET_NAME

    @property
    @override
    def version(self) -> str:
        """Get the version of this ruleset."""
        return _VERSION

    @override
    def get_rules(self) -> tuple[Rule, ...]:
        """Get the third-party services rules.

        Returns:
            Immutable tuple of Rule objects containing all third-party service patterns

        """
        if self.rules is None:
            rules_list: list[Rule] = []
            for rule_name, rule_data in _THIRD_PARTY_SERVICES.items():
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
            logger.debug(f"Generated {len(self.rules)} third-party services rules")

        return self.rules
