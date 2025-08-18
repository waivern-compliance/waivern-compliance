"""Service integrations ruleset for detecting third-party service usage.

This module defines patterns for detecting third-party service integrations
in source code, such as cloud platforms, payment processors, analytics services,
and communication tools. These patterns are optimized for structured analysis
of imports, class names, and function names.
"""

import logging
from typing import Final

from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RuleData

logger = logging.getLogger(__name__)

# Version constant for this ruleset (private)
_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "service_integrations"

_SERVICE_INTEGRATIONS: Final[dict[str, RuleData]] = {
    # ===== CLOUD INFRASTRUCTURE SERVICES =====
    "cloud_infrastructure": {
        "description": "Cloud storage and platform service integrations",
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
            "purpose_category": "OPERATIONAL",
            "compliance_relevance": ["GDPR"],
            "regulatory_impact": "GDPR Article 28, Data Localisation Requirements",
        },
    },
    # ===== COMMUNICATION SERVICES =====
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
            "sms",
            "notification",
        ),
        "risk_level": "medium",
        "metadata": {
            "service_category": "communication",
            "purpose_category": "OPERATIONAL",
            "compliance_relevance": ["GDPR"],
            "regulatory_impact": "GDPR Article 28 (Data Processors)",
        },
    },
    # ===== IDENTITY MANAGEMENT SERVICES =====
    "identity_management": {
        "description": "Third-party authentication and identity service integrations",
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
            "purpose_category": "OPERATIONAL",
            "compliance_relevance": ["GDPR"],
            "regulatory_impact": "GDPR Article 25 (Data Protection by Design)",
        },
    },
    # ===== PAYMENT PROCESSING SERVICES =====
    "payment_processing": {
        "description": "Payment processing service integrations",
        "patterns": (
            "stripe",
            "paypal",
            "square",
            "braintree",
            "authorize.net",
            "worldpay",
            "adyen",
            "charge",
        ),
        "risk_level": "high",
        "metadata": {
            "service_category": "payment_processing",
            "purpose_category": "OPERATIONAL",
            "compliance_relevance": ["GDPR", "PCI_DSS", "SOX"],
            "regulatory_impact": "PCI DSS, GDPR Article 25",
        },
    },
    # ===== USER ANALYTICS SERVICES =====
    "user_analytics": {
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
        ),
        "risk_level": "medium",
        "metadata": {
            "service_category": "user_analytics",
            "purpose_category": "ANALYTICS",
            "compliance_relevance": ["GDPR", "CCPA", "CPRA"],
            "regulatory_impact": "GDPR Article 6, Cookie Directive",
        },
    },
    # ===== SOCIAL MEDIA SERVICES =====
    "social_media": {
        "description": "Social media platform integrations for marketing",
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
            "purpose_category": "MARKETING_AND_ADVERTISING",
            "compliance_relevance": ["GDPR", "CCPA", "CPRA"],
            "regulatory_impact": "GDPR Article 26 (Joint Controllers)",
        },
    },
}


class ServiceIntegrationsRuleset(Ruleset):
    """Ruleset for detecting third-party service integrations in source code.

    This ruleset focuses on identifying service integrations through:
    - Import statements (e.g., 'import stripe')
    - Class names (e.g., 'StripePaymentProcessor')
    - Function names (e.g., 'sendViaMailchimp')
    - Configuration references (e.g., 'STRIPE_API_KEY')

    Service integrations are critical for GDPR compliance as they represent
    data processor relationships that require data processing agreements.
    """

    def __init__(self) -> None:
        """Initialise the service integrations ruleset."""
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
        """Get the service integration rules.

        Returns:
            Immutable tuple of Rule objects containing all service integration patterns

        """
        if self.rules is None:
            rules_list: list[Rule] = []
            for rule_name, rule_data in _SERVICE_INTEGRATIONS.items():
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
            logger.debug(f"Generated {len(self.rules)} service integration rules")

        return self.rules
