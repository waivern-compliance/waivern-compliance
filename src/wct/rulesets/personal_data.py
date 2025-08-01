"""Personal data detection ruleset."""

from typing import Any, Final

from typing_extensions import override

from wct.rulesets.base import Ruleset

PERSONAL_DATA_PATTERNS: Final = {
    "basic_profile": {
        "patterns": [
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
        ],
        "risk_level": "medium",
        "special_category": "N",
    },
    "account_data": {
        "patterns": ["transaction", "subscription", "purchase", "cancellation"],
        "risk_level": "medium",
        "special_category": "N",
    },
    "payment_data": {
        "patterns": [
            "payment_method",
            "invoice",
            "receipt",
            "credit",
            "card",
            "payment",
            "billing",
        ],
        "risk_level": "medium",
        "special_category": "N",
    },
    "financial_data": {
        "patterns": [
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
        ],
        "risk_level": "high",
        "special_category": "N",
    },
    "behavioral_event_data": {
        "patterns": [
            "page_view",
            "click",
            "scroll",
            "form_completion",
            "timestamp",
            "app_usage",
        ],
        "risk_level": "medium",
        "special_category": "N",
    },
    "technical_device_and_network_data": {
        "patterns": [
            "device_id",
            "ip_address",
            "cookie",
            "language",
            "screen",
            "network",
        ],
        "risk_level": "medium",
        "special_category": "N",
    },
    "inferred_profile_data": {
        "patterns": [
            "predicted",
            "inferred",
            "calculated",
            "profiling",
            "machine_learning",
        ],
        "risk_level": "medium",
        "special_category": "N",
    },
    "User_enriched_profile_data": {
        "patterns": ["interests", "preferences", "declared", "user_provided"],
        "risk_level": "medium",
        "special_category": "N",
    },
    "location_data": {
        "patterns": ["country", "region", "city", "suburb"],
        "risk_level": "medium",
        "special_category": "N",
    },
    "user_generated_content": {
        "patterns": ["comment", "review", "feedback", "message"],
        "risk_level": "medium",
        "special_category": "N",
    },
    "accurate_location": {
        "patterns": [
            "precise_location",
            "exact_location",
            "gps",
            "coordinates",
            "latitude",
            "longitude",
        ],
        "risk_level": "high",
        "special_category": "Y",
    },
    "health_data": {
        "patterns": [
            "health",
            "medical",
            "illness",
            "condition",
            "diagnosis",
            "treatment",
            "patient",
        ],
        "risk_level": "high",
        "special_category": "Y",
    },
    "political_data": {
        "patterns": ["political", "trade_union", "affiliation"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "racial_ethnic_data": {
        "patterns": ["race", "ethnic", "origin", "nationality"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "religious_philosophical_data": {
        "patterns": ["religion", "belief", "philosophy", "faith"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "genetic_data": {
        "patterns": ["genetic", "dna", "genome", "sequence"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "biometric_data": {
        "patterns": [
            "biometric",
            "fingerprint",
            "iris",
            "facial_recognition",
            "face",
            "voice",
        ],
        "risk_level": "high",
        "special_category": "Y",
    },
    "sexual_orientation_data": {
        "patterns": ["sexual", "orientation", "sex_life", "gender_identity"],
        "risk_level": "high",
        "special_category": "Y",
    },
    "date_of_birth": {
        "patterns": [
            "date_of_birth",
            "birthday",
            "birth",
            "dob",
            "age",
        ],
        "risk_level": "medium",
        "special_category": "N",
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

    @override
    def get_patterns(self) -> dict[str, Any]:
        """Get the personal data patterns.

        Returns:
            Dictionary containing all GDPR-compliant personal data patterns
        """
        self.logger.debug(
            f"Returning {len(PERSONAL_DATA_PATTERNS)} personal data patterns"
        )
        return PERSONAL_DATA_PATTERNS

    def get_high_risk_patterns(self) -> dict[str, Any]:
        """Get only high-risk personal data patterns.

        Returns:
            Dictionary containing patterns with 'high' risk level
        """
        high_risk_patterns = {
            name: pattern
            for name, pattern in PERSONAL_DATA_PATTERNS.items()
            if pattern.get("risk_level") == "high"
        }

        self.logger.debug(f"Returning {len(high_risk_patterns)} high-risk patterns")
        return high_risk_patterns

    def get_special_category_patterns(self) -> dict[str, Any]:
        """Get only special category personal data patterns under GDPR.

        Returns:
            Dictionary containing patterns marked as special category ('Y')
        """
        special_patterns = {
            name: pattern
            for name, pattern in PERSONAL_DATA_PATTERNS.items()
            if pattern.get("special_category") == "Y"
        }

        self.logger.debug(
            f"Returning {len(special_patterns)} special category patterns"
        )
        return special_patterns

    def validate_pattern_structure(self) -> bool:
        """Validate that all patterns have required fields.

        Returns:
            True if all patterns are valid, False otherwise
        """
        required_fields = {"patterns", "risk_level", "special_category"}
        invalid_patterns = []

        for name, pattern in PERSONAL_DATA_PATTERNS.items():
            if not all(field in pattern for field in required_fields):
                invalid_patterns.append(name)

        if invalid_patterns:
            self.logger.warning(
                f"Found {len(invalid_patterns)} invalid patterns: {invalid_patterns}"
            )
            return False

        self.logger.info(f"All {len(PERSONAL_DATA_PATTERNS)} patterns are valid")
        return True
