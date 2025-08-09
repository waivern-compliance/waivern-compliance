"""Personal data handling functions in source code."""

from typing import Final

from typing_extensions import override

from wct.rulesets.base import Ruleset
from wct.rulesets.types import Rule, RuleData

# Version constant for this ruleset
VERSION: Final[str] = "1.0.0"

PERSONAL_DATA_CODE_FUNCTION_PATTERNS: Final[dict[str, RuleData]] = {
    "user_management": {
        "description": "Functions that manage user accounts and profiles",
        "patterns": (
            "createuser",
            "getuser",
            "updateuser",
            "deleteuser",
            "registeruser",
        ),
        "risk_level": "medium",
        "metadata": {
            "data_type": "user_data",
            "special_category": "N",
        },
    },
    "email_handling": {
        "description": "Functions that process email addresses",
        "patterns": ("sendemail", "validateemail", "getemail", "setemail"),
        "risk_level": "medium",
        "metadata": {
            "data_type": "email",
            "special_category": "N",
        },
    },
    "authentication": {
        "description": "Functions that handle user authentication",
        "patterns": ("authenticate", "login", "signin", "authorise"),
        "risk_level": "medium",
        "metadata": {
            "data_type": "authentication_data",
            "special_category": "N",
        },
    },
    "profile_management": {
        "description": "Functions that manage user profiles",
        "patterns": ("getprofile", "updateprofile", "saveprofile"),
        "risk_level": "medium",
        "metadata": {
            "data_type": "profile_data",
            "special_category": "N",
        },
    },
}


class PersonalDataCodeFunctionsRuleset(Ruleset):
    """Personal data handling functions in source code.

    This ruleset identifies function names that typically handle personal data
    in source code, helping to detect data processing activities.
    """

    def __init__(self, ruleset_name: str = "personal_data_code_functions") -> None:
        """Initialize the personal data code functions ruleset.

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
        """Get the personal data code function rules.

        Returns:
            List of Rule objects containing personal data function patterns
        """
        rules: list[Rule] = []
        for rule_name, rule_data in PERSONAL_DATA_CODE_FUNCTION_PATTERNS.items():
            rules.append(
                Rule(
                    name=rule_name,
                    description=rule_data["description"],
                    patterns=rule_data["patterns"],
                    risk_level=rule_data["risk_level"],
                    metadata=rule_data["metadata"],
                )
            )

        self.logger.debug(f"Returning {len(rules)} personal data code function rules")
        return rules
