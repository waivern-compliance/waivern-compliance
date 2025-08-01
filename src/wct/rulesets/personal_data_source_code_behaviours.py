"""Personal data source code behaviour detection ruleset."""

from typing import Any, Final

from typing_extensions import override

from wct.rulesets.base import Ruleset

# Source code specific patterns (function/class/SQL/third-party patterns only)
# Field patterns are now handled directly by the enhanced personal_data ruleset
SOURCE_CODE_SPECIFIC_PATTERNS: Final = {
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
        """Get the source code specific behaviour patterns.

        Returns:
            Dictionary containing source code specific patterns (function/class/SQL/third-party)
            Field patterns are handled directly by the personal_data ruleset
        """
        self.logger.debug(
            f"Returning {len(SOURCE_CODE_SPECIFIC_PATTERNS)} source code specific pattern categories"
        )
        return SOURCE_CODE_SPECIFIC_PATTERNS

    def get_field_patterns(self) -> dict[str, Any]:
        """Get field name patterns for personal data detection.

        Note: Field patterns are now handled directly by the personal_data ruleset.
        This method is deprecated - use get_ruleset('personal_data') directly.

        Returns:
            Empty dictionary - field patterns are in personal_data ruleset
        """
        self.logger.warning(
            "get_field_patterns() is deprecated - field patterns are now in personal_data ruleset"
        )
        return {}

    def get_function_patterns(self) -> dict[str, Any]:
        """Get function name patterns for personal data handling detection.

        Returns:
            Dictionary of function patterns organized by operation type
        """
        function_patterns = SOURCE_CODE_SPECIFIC_PATTERNS.get("function_patterns", {})
        self.logger.debug(f"Returning {len(function_patterns)} function patterns")
        return function_patterns

    def get_class_patterns(self) -> dict[str, Any]:
        """Get class name patterns for personal data model detection.

        Returns:
            Dictionary of class patterns organized by model type
        """
        class_patterns = SOURCE_CODE_SPECIFIC_PATTERNS.get("class_patterns", {})
        self.logger.debug(f"Returning {len(class_patterns)} class patterns")
        return class_patterns

    def get_sql_patterns(self) -> dict[str, dict[str, Any]]:
        """Get SQL table and column patterns for personal data detection.

        Returns:
            Dictionary with 'tables' and 'columns' sub-dictionaries
        """
        sql_patterns = {
            "tables": SOURCE_CODE_SPECIFIC_PATTERNS.get("sql_table_patterns", {}),
            "columns": SOURCE_CODE_SPECIFIC_PATTERNS.get("sql_column_patterns", {}),
        }
        self.logger.debug(
            f"Returning SQL patterns: {len(sql_patterns['tables'])} tables, "
            f"{len(sql_patterns['columns'])} columns"
        )
        return sql_patterns

    def get_third_party_service_patterns(self) -> dict[str, Any]:
        """Get third-party service patterns for risk classification.

        Returns:
            Dictionary of service patterns organized by risk level
        """
        service_patterns = SOURCE_CODE_SPECIFIC_PATTERNS.get("third_party_services", {})
        self.logger.debug(f"Returning {len(service_patterns)} service risk categories")
        return service_patterns

    def validate_pattern_structure(self) -> bool:
        """Validate that all source code specific patterns have required fields.

        Note: Field patterns are now validated by the personal_data ruleset.

        Returns:
            True if all patterns are valid, False otherwise
        """
        invalid_patterns = []

        # Validate source code specific patterns
        # Validate function and class patterns
        for category in ["function_patterns", "class_patterns"]:
            patterns = SOURCE_CODE_SPECIFIC_PATTERNS.get(category, {})
            for name, pattern in patterns.items():
                required_fields = {
                    "patterns",
                    "data_type",
                    "risk_level",
                    "special_category",
                }
                if not all(field in pattern for field in required_fields):
                    invalid_patterns.append(f"{category}.{name}")

        # Validate SQL patterns
        for pattern_type in ["sql_table_patterns", "sql_column_patterns"]:
            patterns = SOURCE_CODE_SPECIFIC_PATTERNS.get(pattern_type, {})
            for name, pattern in patterns.items():
                required_fields = {"data_type", "risk_level", "special_category"}
                if not all(field in pattern for field in required_fields):
                    invalid_patterns.append(f"{pattern_type}.{name}")

        # Validate third-party service patterns
        service_patterns = SOURCE_CODE_SPECIFIC_PATTERNS.get("third_party_services", {})
        for risk_level, pattern in service_patterns.items():
            if "patterns" not in pattern or "risk_level" not in pattern:
                invalid_patterns.append(f"third_party_services.{risk_level}")

        if invalid_patterns:
            self.logger.warning(
                f"Found {len(invalid_patterns)} invalid source code patterns: {invalid_patterns}"
            )
            return False

        self.logger.info("All source code specific patterns are valid")
        return True
