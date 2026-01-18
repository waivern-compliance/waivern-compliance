"""Known processing purposes to search for during analysis.

This ruleset contains processing purpose patterns for GDPR compliance analysis.
Version 1.0.0 has separated service integration patterns into dedicated service_integrations ruleset.
"""

import logging
from pathlib import Path
from typing import ClassVar, Final, override

import yaml
from pydantic import Field, ValidationInfo, field_validator, model_validator
from waivern_core import DetectionRule, RulesetData

from waivern_rulesets.base import AbstractRuleset

logger = logging.getLogger(__name__)

# Version constant for this ruleset and its data (private)
_RULESET_DATA_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "processing_purposes"


class ProcessingPurposeRule(DetectionRule):
    """Processing purpose rule with category and risk information."""

    purpose_category: str = Field(description="Category of this processing purpose")


class ProcessingPurposesRulesetData(RulesetData[ProcessingPurposeRule]):
    """Processing purposes ruleset data model with category management."""

    # Ruleset-specific properties
    purpose_categories: list[str] = Field(
        min_length=1, description="Master list of valid purpose categories"
    )
    sensitive_categories: list[str] = Field(
        default_factory=list,
        description="Subset of purpose_categories considered privacy-sensitive",
    )

    @field_validator("sensitive_categories")
    @classmethod
    def validate_sensitive_categories_subset(
        cls, v: list[str], info: ValidationInfo
    ) -> list[str]:
        """Ensure sensitive_categories is subset of purpose_categories."""
        purpose_categories = info.data.get("purpose_categories", [])
        invalid = [cat for cat in v if cat not in purpose_categories]
        if invalid:
            raise ValueError(
                f"Sensitive categories must be subset of purpose_categories. Invalid: {invalid}"
            )
        return v

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "ProcessingPurposesRulesetData":
        """Validate all rule purpose_categories against master list."""
        purpose_categories = set(self.purpose_categories)

        for rule in self.rules:
            if rule.purpose_category not in purpose_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid purpose_category '{rule.purpose_category}'. Valid: {purpose_categories}"
                )
        return self


class ProcessingPurposesRuleset(AbstractRuleset[ProcessingPurposeRule]):
    """Class-based processing purposes detection ruleset with logging support.

    This class provides structured access to processing purposes patterns
    with built-in logging capabilities for debugging and monitoring.

    Processing purposes help identify what business activities or data uses
    are mentioned in content, which is crucial for privacy compliance,
    consent management, and understanding data processing activities.

    Processing purposes are business activities or intentions for data use,
    complementary to technical data collection patterns and service integrations.
    """

    ruleset_name: ClassVar[str] = _RULESET_NAME
    ruleset_version: ClassVar[str] = _RULESET_DATA_VERSION

    def __init__(self) -> None:
        """Initialise the processing purposes ruleset."""
        self._rules: tuple[ProcessingPurposeRule, ...] | None = None
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
    def get_rules(self) -> tuple[ProcessingPurposeRule, ...]:
        """Get the processing purposes rules.

        Returns:
            Immutable tuple of ProcessingPurposeRule objects with strongly typed properties

        """
        if self._rules is None:
            # Load from external configuration file with validation
            ruleset_file = (
                Path(__file__).parent
                / "data"
                / _RULESET_NAME
                / _RULESET_DATA_VERSION
                / f"{_RULESET_NAME}.yaml"
            )
            with ruleset_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            ruleset_data = ProcessingPurposesRulesetData.model_validate(data)
            self._rules = tuple(ruleset_data.rules)
            logger.debug(f"Loaded {len(self._rules)} processing purpose patterns")

        return self._rules
