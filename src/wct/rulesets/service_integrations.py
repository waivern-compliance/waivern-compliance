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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Article 28 requires data processing agreements with cloud service providers as they act as data processors. Article 44-49 govern international data transfers, requiring adequacy decisions or appropriate safeguards for cloud storage outside the EU. Data localisation requirements may apply for certain cloud storage locations.",
            },
            {
                "regulation": "CCPA",
                "relevance": "Cloud service providers must be covered by service provider agreements under CCPA Section 1798.140(v), limiting their use of personal information to providing services and prohibiting sale or retention of data.",
            },
        ],
        "metadata": {
            "service_category": "cloud_infrastructure",
            "purpose_category": "OPERATIONAL",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Article 28 requires data processing agreements with communication service providers as they act as data processors when handling personal data in emails, messages, or notifications. Controllers must ensure processors implement appropriate technical and organisational measures.",
            },
            {
                "regulation": "ePrivacy",
                "relevance": "Electronic communications services may be subject to ePrivacy Directive requirements for confidentiality of communications, especially for email and messaging services. Consent may be required for certain electronic direct marketing communications.",
            },
            {
                "regulation": "CCPA",
                "relevance": "Communication service providers must be covered by service provider agreements limiting their use of personal information to providing communication services and prohibiting unauthorised disclosure or sale of personal data.",
            },
        ],
        "metadata": {
            "service_category": "communication",
            "purpose_category": "OPERATIONAL",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Article 25 requires data protection by design and by default in identity systems. Article 28 applies to identity service providers as data processors. Special category data protections under Article 9 may apply if biometric authentication is used. Identity verification must have appropriate legal basis under Article 6.",
            },
            {
                "regulation": "CCPA",
                "relevance": "Identity verification services processing personal information for authentication require service provider agreements. Consumers have rights to request deletion and correction of identity data, though verification purposes may provide grounds for retention exceptions under CCPA Section 1798.105(d).",
            },
        ],
        "metadata": {
            "service_category": "identity_management",
            "purpose_category": "OPERATIONAL",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Article 28 requires data processing agreements with payment processors as they act as data processors. Article 25 mandates data protection by design and by default in payment systems. Financial data processing requires appropriate legal basis under Article 6 and enhanced security measures.",
            },
            {
                "regulation": "PCI_DSS",
                "relevance": "Payment Card Industry Data Security Standard applies to all entities that store, process, or transmit cardholder data. Payment service integrations must maintain PCI DSS compliance through secure transmission, tokenisation, and proper handling of payment card information.",
            },
            {
                "regulation": "SOX",
                "relevance": "Sarbanes-Oxley Act requires internal controls over financial reporting. Payment processing systems must maintain audit trails, financial transaction integrity, and proper access controls to ensure accurate financial reporting and prevent fraud.",
            },
            {
                "regulation": "CCPA",
                "relevance": "Payment processors handling financial personal information require service provider agreements limiting use to payment processing services. Financial information constitutes personal information under CCPA Section 1798.140(o), subject to consumer rights including access and deletion requests.",
            },
        ],
        "metadata": {
            "service_category": "payment_processing",
            "purpose_category": "OPERATIONAL",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Article 6 requires appropriate legal basis for analytics processing, typically legitimate interest with balancing test. Article 21 provides users right to object to analytics processing. Cookie-based analytics require consent under Cookie Directive. Analytics providers typically act as joint controllers or processors requiring appropriate agreements.",
            },
            {
                "regulation": "ePrivacy",
                "relevance": "Cookie Directive and ePrivacy regulations require consent for non-essential cookies used by analytics services. Users must be informed about tracking technologies and given meaningful choice to accept or decline analytics cookies.",
            },
            {
                "regulation": "CCPA",
                "relevance": "Analytics services collecting personal information must provide opt-out rights under CCPA Section 1798.120. Cross-device tracking and profiling may constitute 'sale' of personal information requiring prominent 'Do Not Sell My Personal Information' links and respect for opt-out signals.",
            },
            {
                "regulation": "CPRA",
                "relevance": "California Privacy Rights Act expands analytics regulation by requiring opt-out for 'sharing' personal information for cross-context behavioural advertising. Analytics profiling may constitute 'sensitive personal information' processing requiring separate consent under CPRA Section 1798.121.",
            },
        ],
        "metadata": {
            "service_category": "user_analytics",
            "purpose_category": "ANALYTICS",
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
        "compliance": [
            {
                "regulation": "GDPR",
                "relevance": "Article 26 governs joint controller relationships when sharing data with social media platforms for marketing. Both parties must determine respective responsibilities through joint controller agreements. Users must be informed of joint processing and can exercise rights against either controller.",
            },
            {
                "regulation": "ePrivacy",
                "relevance": "Social media tracking pixels and plugins require consent under Cookie Directive. Cross-site tracking for advertising purposes needs user consent before placing tracking technologies on user devices.",
            },
            {
                "regulation": "CCPA",
                "relevance": "Sharing personal information with social media platforms for advertising may constitute 'sale' under CCPA Section 1798.140(t), requiring 'Do Not Sell My Personal Information' opt-out mechanisms. Custom audiences and lookalike advertising involve data sharing subject to consumer rights.",
            },
            {
                "regulation": "CPRA",
                "relevance": "Social media integrations for cross-context behavioural advertising require opt-out rights under CPRA 'sharing' provisions. Custom audience matching and interest-based advertising may process 'sensitive personal information' requiring explicit consent under CPRA Section 1798.121.",
            },
        ],
        "metadata": {
            "service_category": "social_media",
            "purpose_category": "MARKETING_AND_ADVERTISING",
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
                        compliance=rule_data["compliance"],
                        metadata=rule_data["metadata"],
                    )
                )
            self.rules = tuple(rules_list)
            logger.debug(f"Generated {len(self.rules)} service integration rules")

        return self.rules
