"""Data subject classification ruleset for GDPR Article 30(1)(c) compliance.

This module implements automated data subject categorisation with confidence scoring
and metadata-aware pattern matching for comprehensive privacy compliance analysis.
"""

import logging
from pathlib import Path
from typing import Final, Literal, override

import yaml
from pydantic import Field, model_validator
from waivern_core import BaseRule, RulesetData

from waivern_rulesets.base import AbstractRuleset

logger = logging.getLogger(__name__)

# Version constant for this ruleset and its data (private)
_RULESET_DATA_VERSION: Final[str] = "1.0.0"
_RULESET_NAME: Final[str] = "data_subjects"


class DataSubjectRule(BaseRule):
    """Data subject classification rule with confidence scoring.

    This rule type provides pattern-based data subject identification with
    configurable confidence weights for accurate classification.
    """

    subject_category: str = Field(
        description="Data subject category (e.g., employee, customer)"
    )
    indicator_type: Literal["primary", "secondary", "contextual"] = Field(
        description="Classification strength of this indicator"
    )
    confidence_weight: int = Field(
        ge=1, le=50, description="Confidence points awarded when this rule matches"
    )
    applicable_contexts: list[str] = Field(
        min_length=1,
        description="Data source contexts where this rule applies (e.g., database, filesystem, source_code)",
    )


class DataSubjectRulesetData(RulesetData[DataSubjectRule]):
    """Data subject ruleset data model with category management."""

    # Ruleset-specific properties
    subject_categories: list[str] = Field(
        min_length=1, description="Master list of valid data subject categories"
    )
    applicable_contexts: list[str] = Field(
        min_length=1, description="Master list of valid applicable contexts"
    )
    risk_increasing_modifiers: list[str] = Field(
        min_length=1,
        description="Risk-increasing modifiers (e.g., minor, vulnerable group)",
    )
    risk_decreasing_modifiers: list[str] = Field(
        min_length=1, description="Risk-decreasing modifiers (e.g., non-EU-resident)"
    )

    @model_validator(mode="after")
    def validate_rule_categories(self) -> "DataSubjectRulesetData":
        """Validate all rule subject_category values against master list."""
        valid_categories = set(self.subject_categories)

        for rule in self.rules:
            if rule.subject_category not in valid_categories:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid subject_category '{rule.subject_category}'. Valid: {valid_categories}"
                )
        return self

    @model_validator(mode="after")
    def validate_rule_contexts(self) -> "DataSubjectRulesetData":
        """Validate all rule applicable_contexts values against master list."""
        valid_contexts = set(self.applicable_contexts)

        for rule in self.rules:
            invalid_contexts = set(rule.applicable_contexts) - valid_contexts
            if invalid_contexts:
                raise ValueError(
                    f"Rule '{rule.name}' has invalid applicable_contexts {sorted(invalid_contexts)}. Valid: {sorted(valid_contexts)}"
                )
        return self


class DataSubjectsRuleset(AbstractRuleset[DataSubjectRule]):
    """Class-based data subject classification ruleset with confidence scoring.

    This class provides structured access to data subject classification patterns
    with built-in logging capabilities for debugging and monitoring.

    Data subject classification helps identify categories of individuals whose
    personal data is processed, which is crucial for GDPR Article 30(1)(c) compliance.
    """

    def __init__(self) -> None:
        """Initialise the data subjects ruleset."""
        self._rules: tuple[DataSubjectRule, ...] | None = None
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
    def get_rules(self) -> tuple[DataSubjectRule, ...]:
        """Get the data subject classification rules.

        Returns:
            Immutable tuple of DataSubjectRule objects with confidence scoring

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

            ruleset_data = DataSubjectRulesetData.model_validate(data)
            self._rules = tuple(ruleset_data.rules)
            logger.debug(
                f"Loaded {len(self._rules)} data subject classification patterns"
            )

        return self._rules
