"""SQL schemas containing personal data."""

from typing import Final

from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RuleData

PERSONAL_DATA_CODE_SQL_SCHEMA_PATTERNS: Final[dict[str, RuleData]] = {
    "users_table": {
        "description": "Database table storing user information",
        "patterns": ("users",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "user_data",
            "special_category": "N",
            "database_object": "table",
        },
    },
    "customers_table": {
        "description": "Database table storing customer information",
        "patterns": ("customers",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "user_data",
            "special_category": "N",
            "database_object": "table",
        },
    },
    "profiles_table": {
        "description": "Database table storing profile information",
        "patterns": ("profiles",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "profile_data",
            "special_category": "N",
            "database_object": "table",
        },
    },
    "contacts_table": {
        "description": "Database table storing contact information",
        "patterns": ("contacts",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "contact_data",
            "special_category": "N",
            "database_object": "table",
        },
    },
    "addresses_table": {
        "description": "Database table storing address information",
        "patterns": ("addresses",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "address",
            "special_category": "N",
            "database_object": "table",
        },
    },
    "emails_table": {
        "description": "Database table storing email addresses",
        "patterns": ("emails",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "email",
            "special_category": "N",
            "database_object": "table",
        },
    },
    "phones_table": {
        "description": "Database table storing phone numbers",
        "patterns": ("phones",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "phone",
            "special_category": "N",
            "database_object": "table",
        },
    },
    "payments_table": {
        "description": "Database table storing payment information",
        "patterns": ("payments",),
        "risk_level": "high",
        "metadata": {
            "data_type": "financial",
            "special_category": "N",
            "database_object": "table",
        },
    },
    "orders_table": {
        "description": "Database table storing order information",
        "patterns": ("orders",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "transaction_data",
            "special_category": "N",
            "database_object": "table",
        },
    },
    "email_column": {
        "description": "Database column storing email addresses",
        "patterns": ("email",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "email",
            "special_category": "N",
            "database_object": "column",
        },
    },
    "phone_column": {
        "description": "Database column storing phone numbers",
        "patterns": ("phone",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "phone",
            "special_category": "N",
            "database_object": "column",
        },
    },
    "first_name_column": {
        "description": "Database column storing first names",
        "patterns": ("first_name",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "name",
            "special_category": "N",
            "database_object": "column",
        },
    },
    "last_name_column": {
        "description": "Database column storing last names",
        "patterns": ("last_name",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "name",
            "special_category": "N",
            "database_object": "column",
        },
    },
    "address_column": {
        "description": "Database column storing addresses",
        "patterns": ("address",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "address",
            "special_category": "N",
            "database_object": "column",
        },
    },
    "ssn_column": {
        "description": "Database column storing social security numbers",
        "patterns": ("ssn",),
        "risk_level": "high",
        "metadata": {
            "data_type": "government_id",
            "special_category": "N",
            "database_object": "column",
        },
    },
    "credit_card_column": {
        "description": "Database column storing credit card information",
        "patterns": ("credit_card",),
        "risk_level": "high",
        "metadata": {
            "data_type": "financial",
            "special_category": "N",
            "database_object": "column",
        },
    },
    "date_of_birth_column": {
        "description": "Database column storing birth dates",
        "patterns": ("date_of_birth",),
        "risk_level": "medium",
        "metadata": {
            "data_type": "date_of_birth",
            "special_category": "N",
            "database_object": "column",
        },
    },
}


class PersonalDataSqlSchemasRuleset(Ruleset):
    """SQL schemas containing personal data.

    This ruleset identifies database table and column names that typically
    store personal data in SQL queries and database schemas.
    """

    def __init__(self, ruleset_name: str = "personal_data_sql_schemas") -> None:
        """Initialize the personal data SQL schemas ruleset.

        Args:
            ruleset_name: Name of the ruleset for logging purposes
        """
        super().__init__(ruleset_name)
        self.logger.debug(f"Initialized {self.__class__.__name__} ruleset")

    @override
    def get_rules(self) -> list[Rule]:
        """Get the personal data SQL schema rules.

        Returns:
            List of Rule objects containing SQL schema personal data patterns
        """
        rules = []
        for rule_name, rule_data in PERSONAL_DATA_CODE_SQL_SCHEMA_PATTERNS.items():
            rules.append(
                Rule(
                    name=rule_name,
                    description=rule_data["description"],
                    patterns=rule_data["patterns"],
                    risk_level=rule_data["risk_level"],
                    metadata=rule_data["metadata"],
                )
            )

        self.logger.debug(f"Returning {len(rules)} personal data SQL schema rules")
        return rules
