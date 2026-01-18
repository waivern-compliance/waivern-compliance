"""Personal data indicator detection ruleset.

This module defines a ruleset for detecting personal data patterns.
It provides framework-agnostic indicators that can be consumed by
regulatory classifiers (e.g., GDPR, CCPA) for framework-specific enrichment.
"""

import logging
from pathlib import Path
from typing import ClassVar, Final, override

import yaml
from pydantic import Field, model_validator
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.core.base import AbstractRuleset

logger = logging.getLogger(__name__)

# Version constant for this ruleset and its data (private)
_RULESET_DATA_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "personal_data_indicator"


class PersonalDataIndicatorRule(DetectionRule):
    """Personal data indicator detection rule.

    This is a framework-agnostic detection rule. Regulatory classification
    (e.g., GDPR Article 9 special categories) is performed by downstream
    classifiers, not by this ruleset.
    """

    category: str = Field(
        description="Category of personal data this rule detects (e.g., 'basic_profile', 'health_data')"
    )


class PersonalDataIndicatorRulesetData(RulesetData[PersonalDataIndicatorRule]):
    """Personal data indicator ruleset data structure."""

    # Ruleset-specific properties
    categories: list[str] = Field(
        min_length=1,
        description="Master list of valid personal data indicator categories",
    )

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "PersonalDataIndicatorRulesetData":
        """Validate all rule category values against master list."""
        valid_categories = set(self.categories)

        for rule in self.rules:
            if rule.category not in valid_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid category '{rule.category}'. Valid: {valid_categories}"
                )
        return self


class PersonalDataIndicatorRuleset(AbstractRuleset[PersonalDataIndicatorRule]):
    """Class-based personal data indicator detection ruleset.

    This class provides structured access to personal data patterns
    with built-in logging capabilities for debugging and monitoring.
    """

    ruleset_name: ClassVar[str] = _RULESET_NAME
    ruleset_version: ClassVar[str] = _RULESET_DATA_VERSION

    def __init__(self) -> None:
        """Initialise the personal data indicator ruleset."""
        self._rules: tuple[PersonalDataIndicatorRule, ...] | None = None
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
        return _RULESET_DATA_VERSION

    @override
    def get_rules(self) -> tuple[PersonalDataIndicatorRule, ...]:
        """Get the personal data indicator rules.

        Returns:
            Immutable tuple of Rule objects containing all personal data patterns

        """
        if self._rules is None:
            # Load from YAML file with Pydantic validation
            yaml_file = (
                Path(__file__).parent
                / "data"
                / _RULESET_DATA_VERSION
                / f"{_RULESET_NAME}.yaml"
            )
            with yaml_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            ruleset_data = PersonalDataIndicatorRulesetData.model_validate(data)
            self._rules = tuple(ruleset_data.rules)
            logger.debug(f"Loaded {len(self._rules)} personal data indicator rules")

        return self._rules
