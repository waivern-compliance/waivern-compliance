"""Personal data models and classes in source code."""

from typing import Final

from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RuleData

PERSONAL_DATA_CODE_CLASS_PATTERNS: Final[dict[str, RuleData]] = {
    "user_model": {
        "description": "Classes and models representing users or persons",
        "patterns": ["user", "person", "customer", "client", "member"],
        "risk_level": "medium",
        "metadata": {
            "data_type": "user_data",
            "special_category": "N",
        },
    },
    "profile_model": {
        "description": "Classes and models representing user profiles",
        "patterns": ["profile", "account", "identity"],
        "risk_level": "medium",
        "metadata": {
            "data_type": "profile_data",
            "special_category": "N",
        },
    },
    "contact_model": {
        "description": "Classes and models representing contact information",
        "patterns": ["contact", "address", "phone", "email"],
        "risk_level": "medium",
        "metadata": {
            "data_type": "contact_data",
            "special_category": "N",
        },
    },
    "health_model": {
        "description": "Classes and models representing health data (GDPR Article 9 special category)",
        "patterns": ["patient", "medical", "health", "diagnosis"],
        "risk_level": "high",
        "metadata": {
            "data_type": "health_data",
            "special_category": "Y",
        },
    },
}


class PersonalDataCodeModelsRuleset(Ruleset):
    """Personal data models and classes in source code.

    This ruleset identifies class and model names that typically represent
    personal data entities in source code.
    """

    def __init__(self, ruleset_name: str = "personal_data_code_models") -> None:
        """Initialize the personal data code models ruleset.

        Args:
            ruleset_name: Name of the ruleset for logging purposes
        """
        super().__init__(ruleset_name)
        self.logger.debug(f"Initialized {self.__class__.__name__} ruleset")

    @override
    def get_rules(self) -> list[Rule]:
        """Get the personal data code model rules.

        Returns:
            List of Rule objects containing personal data model patterns
        """
        rules = []
        for rule_name, rule_data in PERSONAL_DATA_CODE_CLASS_PATTERNS.items():
            rules.append(
                Rule(
                    name=rule_name,
                    description=rule_data["description"],
                    patterns=rule_data["patterns"],
                    risk_level=rule_data["risk_level"],
                    metadata=rule_data["metadata"],
                )
            )

        self.logger.debug(f"Returning {len(rules)} personal data code model rules")
        return rules
