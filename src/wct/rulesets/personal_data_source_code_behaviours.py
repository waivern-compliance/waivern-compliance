"""Personal data source code behaviour detection ruleset.

This module is an extension of the personal data ruleset, providing patterns for
detecting personal data handling in source code through function names, class names,
SQL queries, and third-party integrations.

IMPORTANT: This ruleset is designed to work WITH the 'personal_data' ruleset,
not replace it. For complete source code analysis:
- Use 'personal_data' ruleset for field/parameter/property name detection
- Use this ruleset for function/class/SQL/third-party service detection

The SourceCodeSchemaInputHandler automatically loads both rulesets.
"""

from typing import Any, Final

from typing_extensions import override

from wct.rulesets.base import Ruleset

# Source code specific patterns (function/class/SQL/third-party patterns only)
# Field patterns are now handled directly by the enhanced personal_data ruleset
SOURCE_CODE_PERSONAL_DATA_PATTERNS: Final = {
    "function_patterns": {
        "user_management": {
            "patterns": [
                "createuser",
                "getuser",
                "updateuser",
                "deleteuser",
                "registeruser",
            ],
            "data_type": "user_data",
            "risk_level": "medium",
            "special_category": "N",
        },
        "email_handling": {
            "patterns": ["sendemail", "validateemail", "getemail", "setemail"],
            "data_type": "email",
            "risk_level": "medium",
            "special_category": "N",
        },
        "authentication": {
            "patterns": ["authenticate", "login", "signin", "authorize"],
            "data_type": "authentication_data",
            "risk_level": "medium",
            "special_category": "N",
        },
        "profile_management": {
            "patterns": ["getprofile", "updateprofile", "saveprofile"],
            "data_type": "profile_data",
            "risk_level": "medium",
            "special_category": "N",
        },
    },
    "class_patterns": {
        "user_model": {
            "patterns": ["user", "person", "customer", "client", "member"],
            "data_type": "user_data",
            "risk_level": "medium",
            "special_category": "N",
        },
        "profile_model": {
            "patterns": ["profile", "account", "identity"],
            "data_type": "profile_data",
            "risk_level": "medium",
            "special_category": "N",
        },
        "contact_model": {
            "patterns": ["contact", "address", "phone", "email"],
            "data_type": "contact_data",
            "risk_level": "medium",
            "special_category": "N",
        },
        "health_model": {
            "patterns": ["patient", "medical", "health", "diagnosis"],
            "data_type": "health_data",
            "risk_level": "high",
            "special_category": "Y",
        },
    },
    "sql_table_patterns": {
        "users": {
            "data_type": "user_data",
            "risk_level": "medium",
            "special_category": "N",
        },
        "customers": {
            "data_type": "user_data",
            "risk_level": "medium",
            "special_category": "N",
        },
        "profiles": {
            "data_type": "profile_data",
            "risk_level": "medium",
            "special_category": "N",
        },
        "contacts": {
            "data_type": "contact_data",
            "risk_level": "medium",
            "special_category": "N",
        },
        "addresses": {
            "data_type": "address",
            "risk_level": "medium",
            "special_category": "N",
        },
        "emails": {
            "data_type": "email",
            "risk_level": "medium",
            "special_category": "N",
        },
        "phones": {
            "data_type": "phone",
            "risk_level": "medium",
            "special_category": "N",
        },
        "payments": {
            "data_type": "financial",
            "risk_level": "high",
            "special_category": "N",
        },
        "orders": {
            "data_type": "transaction_data",
            "risk_level": "medium",
            "special_category": "N",
        },
    },
    "sql_column_patterns": {
        "email": {
            "data_type": "email",
            "risk_level": "medium",
            "special_category": "N",
        },
        "phone": {
            "data_type": "phone",
            "risk_level": "medium",
            "special_category": "N",
        },
        "first_name": {
            "data_type": "name",
            "risk_level": "medium",
            "special_category": "N",
        },
        "last_name": {
            "data_type": "name",
            "risk_level": "medium",
            "special_category": "N",
        },
        "address": {
            "data_type": "address",
            "risk_level": "medium",
            "special_category": "N",
        },
        "ssn": {
            "data_type": "government_id",
            "risk_level": "high",
            "special_category": "N",
        },
        "credit_card": {
            "data_type": "financial",
            "risk_level": "high",
            "special_category": "N",
        },
        "date_of_birth": {
            "data_type": "date_of_birth",
            "risk_level": "medium",
            "special_category": "N",
        },
    },
    "third_party_services": {
        "high_risk": {
            "patterns": [
                "stripe",
                "paypal",
                "payment",
                "analytics",
                "facebook",
                "google",
                "tracking",
            ],
            "risk_level": "high",
        },
        "medium_risk": {
            "patterns": [
                "sendgrid",
                "mailgun",
                "twilio",
                "slack",
                "email",
                "sms",
            ],
            "risk_level": "medium",
        },
    },
}


class PersonalDataSourceCodeBehavioursRuleset(Ruleset):
    """Class-based personal data source code behaviour detection ruleset.

    This class provides structured access to patterns for detecting personal data
    handling in source code through naming conventions, function signatures,
    database queries, and third-party integrations.
    """

    def __init__(
        self, ruleset_name: str = "personal_data_source_code_behaviours"
    ) -> None:
        """Initialize the personal data source code behaviours ruleset.

        Args:
            ruleset_name: Name of the ruleset for logging purposes
        """
        super().__init__(ruleset_name)
        self.logger.debug(f"Initialized {self.__class__.__name__} ruleset")

    @override
    def get_patterns(self) -> dict[str, Any]:
        """Get source code specific behaviour patterns.

        IMPORTANT: This ruleset only provides source code analysis patterns
        (function/class/SQL/third-party). For complete personal data detection
        in source code, you MUST also use the 'personal_data' ruleset for
        field pattern matching.

        Returns:
            Dictionary containing source code specific patterns only

        See Also:
            - RulesetLoader.load_ruleset('personal_data') for field patterns
            - Use both rulesets together for complete source code analysis
        """
        self.logger.debug(
            f"Returning {len(SOURCE_CODE_PERSONAL_DATA_PATTERNS)} source code specific pattern categories"
        )
        return SOURCE_CODE_PERSONAL_DATA_PATTERNS
