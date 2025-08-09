"""Personal data detection ruleset.

This module defines a ruleset for detecting personal data patterns.
It serves as a base for compliance with GDPR and other privacy regulations.
"""

from typing import Final

from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RuleData

# Version constant for this ruleset
VERSION: Final[str] = "1.0.0"

PERSONAL_DATA: Final[dict[str, RuleData]] = {
    "basic_profile": {
        "description": "Basic identifying information about individuals",
        "patterns": (
            "first_name",
            "last_name",
            "middle_name",
            "address",
            "telephone",
            "email",
            "title",
            "account_id",
            "name",
            "firstname",
            "lastname",
            "fullname",
            "username",
            "mail",
            "e_mail",
            "phone",
            "tel",
            "mobile",
            "cell",
            "street",
            "city",
            "zip",
            "postal",
            "country",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
        },
    },
    "account_data": {
        "description": "Account and subscription related data",
        "patterns": ("transaction", "subscription", "purchase", "cancellation"),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
        },
    },
    "payment_data": {
        "description": "Payment and billing information",
        "patterns": (
            "payment_method",
            "invoice",
            "receipt",
            "credit",
            "card",
            "payment",
            "billing",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
        },
    },
    "financial_data": {
        "description": "Financial identifiers and sensitive financial information",
        "patterns": (
            "credit_rating",
            "payment_history",
            "bank",
            "account",
            "ssn",
            "social",
            "passport",
            "license",
            "id_number",
            "national_id",
            "credit_card",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "N",
        },
    },
    "behavioral_event_data": {
        "description": "User behavioral and interaction data",
        "patterns": (
            "page_view",
            "click",
            "scroll",
            "form_completion",
            "timestamp",
            "app_usage",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
        },
    },
    "technical_device_and_network_data": {
        "description": "Technical device and network identifiers",
        "patterns": (
            "device_id",
            "ip_address",
            "cookie",
            "language",
            "screen",
            "network",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
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
        },
    },
    "User_enriched_profile_data": {
        "description": "User-declared preferences and interests",
        "patterns": ("interests", "preferences", "declared", "user_provided"),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
        },
    },
    "location_data": {
        "description": "General location information",
        "patterns": ("country", "region", "city", "suburb"),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
        },
    },
    "user_generated_content": {
        "description": "Content created by users",
        "patterns": ("comment", "review", "feedback", "message"),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
        },
    },
    "accurate_location": {
        "description": "Precise location data (GDPR Article 9 special category)",
        "patterns": (
            "precise_location",
            "exact_location",
            "gps",
            "coordinates",
            "latitude",
            "longitude",
        ),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
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
        },
    },
    "political_data": {
        "description": "Political opinions and trade union membership (GDPR Article 9 special category)",
        "patterns": ("political", "trade_union", "affiliation"),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
        },
    },
    "racial_ethnic_data": {
        "description": "Racial or ethnic origin data (GDPR Article 9 special category)",
        "patterns": ("race", "ethnic", "origin", "nationality"),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
        },
    },
    "religious_philosophical_data": {
        "description": "Religious or philosophical beliefs (GDPR Article 9 special category)",
        "patterns": ("religion", "belief", "philosophy", "faith"),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
        },
    },
    "genetic_data": {
        "description": "Genetic information (GDPR Article 9 special category)",
        "patterns": ("genetic", "dna", "genome", "sequence"),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
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
        },
    },
    "sexual_orientation_data": {
        "description": "Sexual orientation and sex life data (GDPR Article 9 special category)",
        "patterns": ("sexual", "orientation", "sex_life", "gender_identity"),
        "risk_level": "high",
        "metadata": {
            "special_category": "Y",
        },
    },
    "date_of_birth": {
        "description": "Birth date and age-related information",
        "patterns": (
            "date_of_birth",
            "birthday",
            "birth",
            "dob",
            "age",
        ),
        "risk_level": "medium",
        "metadata": {
            "special_category": "N",
        },
    },
}


class PersonalDataRuleset(Ruleset):
    """Class-based personal data detection ruleset with logging support.

    This class provides structured access to personal data patterns
    with built-in logging capabilities for debugging and monitoring.
    """

    def __init__(self, ruleset_name: str = "personal_data") -> None:
        """Initialize the personal data ruleset.

        Args:
            ruleset_name: Name of the ruleset for logging purposes
        """
        super().__init__(ruleset_name)
        self.logger.debug(f"Initialized {self.__class__.__name__} ruleset")

    @property
    @override
    def version(self) -> str:
        """Get the version of this ruleset."""
        return VERSION

    @override
    def get_rules(self) -> list[Rule]:
        """Get the personal data rules.

        Returns:
            List of Rule objects containing all GDPR-compliant personal data patterns
        """
        rules: list[Rule] = []
        for rule_name, rule_data in PERSONAL_DATA.items():
            rules.append(
                Rule(
                    name=rule_name,
                    description=rule_data["description"],
                    patterns=rule_data["patterns"],
                    risk_level=rule_data["risk_level"],
                    metadata=rule_data["metadata"],
                )
            )

        self.logger.debug(f"Returning {len(rules)} personal data rules")
        return rules
