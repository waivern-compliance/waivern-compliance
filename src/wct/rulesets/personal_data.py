"""Personal data detection ruleset.

This module defines a ruleset for detecting personal data patterns.
It serves as a base for compliance with GDPR and other privacy regulations.
"""

import logging
from typing import Final

from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RuleData

logger = logging.getLogger(__name__)

# Version constant for this ruleset (private)
_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "personal_data"

_PERSONAL_DATA: Final[dict[str, RuleData]] = {
    "basic_profile": {
        "description": "Basic identifying information about individuals",
        "patterns": (
            "first_name",
            "last_name",
            "middle_name",
            "full_name",
            "display_name",
            "email",
            "mobile",
            "telephone",
            "street_address",
            "city",
            "state",
            "country",
            "zip",
            "postal_code",
            "title",
            "username",
            "account_id",
            "user_id",
            "customer_id",
            "users",
            "customers",
            "contacts",
            "firstname",
            "lastname",
            "e_mail",
            "cell",
            "user_profiles",
            "customer_profiles",
            "personal_info",
            "identities",
            "phone_number",
            "contact_phone",
            "home_address",
            "mailing_address",
            "postcode",
            "salutation",
            "prefix",
            "suffix",
            "login",
            "fullname",
            "client",
            "member",
            "createuser",
            "getuser",
            "updateuser",
            "deleteuser",
            "registeruser",
            "authenticate",
            "authorise",
            "getprofile",
            "updateprofile",
            "saveprofile",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": [
                "GDPR",
                "EU_AI_ACT",
                "NIST_AI_RMF",
                "CCPA",
                "UK_GDPR",
            ],
        },
    },
    "account_data": {
        "description": "Account and subscription related data",
        "patterns": (
            "subscriptions",
            "memberships",
            "transactions",
            "purchases",
            "orders",
            "registrations",
            "enrollments",
            "cancellation",
            "user_accounts",
            "account_details",
            "subscription_data",
            "membership_info",
            "order_history",
            "transaction_log",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF", "CCPA"],
        },
    },
    "payment_data": {
        "description": "Payment and billing information",
        "patterns": (
            "payments",
            "invoices",
            "receipts",
            "payment_methods",
            "credit",
            "card",
            "billing_info",
            "payment_history",
            "invoice_details",
            "billing_addresses",
            "invoice_number",
            "receipt_id",
            "billing_email",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "NIST_AI_RMF", "PCI_DSS"],
        },
    },
    "financial_data": {
        "description": "Financial identifiers and sensitive financial information",
        "patterns": (
            "financial_data",
            "bank_accounts",
            "credit_cards",
            "payment_cards",
            "wallets",
            "financial_profiles",
            "credit_info",
            "banking_details",
            "card_details",
            "credit_rating",
            "payment_history",
            "ssn",
            "id_number",
            "national_id",
            "social_security_number",
            "tax_id",
            "passport_number",
            "drivers_license",
            "government_id",
            "identity_document",
            "account_number",
            "routing_number",
            "iban",
            "swift_code",
            "credit_card_number",
            "debit_card",
            "cvv",
            "security_code",
            "credit_score",
            "financial_rating",
            "credit_history",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": [
                "GDPR",
                "EU_AI_ACT",
                "NIST_AI_RMF",
                "PCI_DSS",
                "SOX",
            ],
        },
    },
    "behavioral_event_data": {
        "description": "User behavioral and interaction data",
        "patterns": (
            "user_events",
            "activity_logs",
            "user_sessions",
            "interactions",
            "analytics",
            "page_views",
            "click_events",
            "user_actions",
            "behavior_data",
            "tracking_data",
            "form_completion",
            "timestamp",
            "app_usage",
            "event_type",
            "action_type",
            "click_data",
            "session_id",
            "duration",
            "referrer",
            "utm_source",
            "utm_campaign",
            "scroll_depth",
            "conversion_event",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": ["GDPR", "CCPA", "ePrivacy"],
        },
    },
    "technical_device_and_network_data": {
        "description": "Technical device and network identifiers",
        "patterns": (
            "user_devices",
            "device_info",
            "network_data",
            "system_info",
            "browser_data",
            "platform_data",
            "technical_profiles",
            "device_fingerprints",
            "device_id",
            "device_uuid",
            "hardware_id",
            "ip_address",
            "remote_addr",
            "client_ip",
            "network_id",
            "user_agent",
            "browser_version",
            "operating_system",
            "os_version",
            "device_type",
            "device_model",
            "screen_resolution",
            "language",
            "locale",
            "timezone",
            "screen_size",
            "viewport_size",
            "cookie_id",
            "session_cookie",
            "tracking_cookie",
            "advertisement_id",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": [
                "GDPR",
                "ePrivacy",
                "CCPA",
                "EU_AI_ACT",
                "NIST_AI_RMF",
            ],
        },
    },
    "inferred_profile_data": {
        "description": "Algorithmically inferred or predicted user characteristics",
        "patterns": (
            "predicted",
            "inferred",
            "calculated",
            "profiling",
            "machine_learning",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": ["GDPR", "EU_AI_ACT"],
        },
    },
    "User_enriched_profile_data": {
        "description": "User-declared preferences and interests",
        "patterns": (
            "interests",
            "preferences",
            "declared",
            "user_provided",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR"],
        },
    },
    "location_data": {
        "description": "General location information",
        "patterns": (
            "locations",
            "addresses",
            "geographic_data",
            "location_history",
            "places",
            "regions",
            "countries",
            "cities",
            "postal_codes",
            "geographic_info",
            "country_code",
            "state",
            "province",
            "territory",
            "city",
            "town",
            "suburb",
            "district",
            "neighborhood",
            "locality",
            "zip_code",
            "postcode",
            "area_code",
            "general_location",
            "approximate_location",
            "region_code",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR", "CCPA"],
        },
    },
    "user_generated_content": {
        "description": "Content created by users",
        "patterns": (
            "comment",
            "review",
            "feedback",
            "message",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR"],
        },
    },
    "accurate_location": {
        "description": "Precise location data (GDPR Article 9 special category)",
        "patterns": (
            "gps_data",
            "precise_locations",
            "geolocation",
            "tracking_data",
            "location_tracking",
            "gps_tracking",
            "position_data",
            "waypoints",
            "routes",
            "latitude",
            "longitude",
            "lng",
            "gps_coordinates",
            "exact_location",
            "location_accuracy",
            "altitude",
            "elevation",
            "bearing",
            "heading",
            "speed",
            "velocity",
            "tracking_point",
            "geofence",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
            "compliance_relevance": ["GDPR"],
        },
    },
    "health_data": {
        "description": "Health and medical information (GDPR Article 9 special category)",
        "patterns": (
            "health",
            "medical",
            "illness",
            "condition",
            "diagnosis",
            "treatment",
            "patient",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR"],
        },
    },
    "political_data": {
        "description": "Political opinions and trade union membership (GDPR Article 9 special category)",
        "patterns": (
            "political",
            "trade_union",
            "affiliation",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR"],
        },
    },
    "racial_ethnic_data": {
        "description": "Racial or ethnic origin data (GDPR Article 9 special category)",
        "patterns": (
            "race",
            "ethnic",
            "origin",
            "nationality",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR"],
        },
    },
    "religious_philosophical_data": {
        "description": "Religious or philosophical beliefs (GDPR Article 9 special category)",
        "patterns": (
            "religion",
            "belief",
            "philosophy",
            "faith",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR"],
        },
    },
    "genetic_data": {
        "description": "Genetic information (GDPR Article 9 special category)",
        "patterns": (
            "genetic",
            "dna",
            "genome",
            "sequence",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR"],
        },
    },
    "biometric_data": {
        "description": "Biometric identifiers (GDPR Article 9 special category)",
        "patterns": (
            "biometric",
            "fingerprint",
            "iris",
            "facial_recognition",
            "face",
            "voice",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR"],
        },
    },
    "sexual_orientation_data": {
        "description": "Sexual orientation and sex life data (GDPR Article 9 special category)",
        "patterns": (
            "sexual",
            "orientation",
            "sex_life",
            "gender_identity",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR"],
        },
    },
    "date_of_birth": {
        "description": "Birth date and age-related information",
        "patterns": (
            "birth_data",
            "age_data",
            "demographic_data",
            "personal_demographics",
            "date_of_birth",
            "birth_date",
            "birthday",
            "dob",
            "birth_day",
            "birth_year",
            "birth_month",
            "age_group",
            "age_range",
            "age_category",
            "date_born",
            "born_on",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
            "compliance_relevance": ["GDPR", "EU_AI_ACT", "UK_GDPR", "COPPA"],
        },
    },
}


class PersonalDataRuleset(Ruleset):
    """Class-based personal data detection ruleset with logging support.

    This class provides structured access to personal data patterns
    with built-in logging capabilities for debugging and monitoring.
    """

    def __init__(self) -> None:
        """Initialise the personal data ruleset."""
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
        """Get the personal data rules.

        Returns:
            Immutable tuple of Rule objects containing all GDPR-compliant personal data patterns
        """
        if self.rules is None:
            rules_list: list[Rule] = []
            for rule_name, rule_data in _PERSONAL_DATA.items():
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
            logger.debug(f"Generated {len(self.rules)} personal data rules")

        return self.rules
