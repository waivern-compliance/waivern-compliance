"""Unit tests for personal data indicator ruleset."""

import pytest
from pydantic import ValidationError

from waivern_rulesets import AbstractRuleset
from waivern_rulesets.personal_data_indicator import (
    PersonalDataIndicatorRule,
    PersonalDataIndicatorRuleset,
    PersonalDataIndicatorRulesetData,
)
from waivern_rulesets.testing import RulesetContractTests

# =============================================================================
# Contract Tests (inherited from RulesetContractTests)
# =============================================================================


class TestPersonalDataIndicatorRulesetContract(
    RulesetContractTests[PersonalDataIndicatorRule]
):
    """Contract tests for PersonalDataIndicatorRuleset."""

    @pytest.fixture
    def ruleset_class(self) -> type[AbstractRuleset[PersonalDataIndicatorRule]]:
        """Provide the ruleset class to test."""
        return PersonalDataIndicatorRuleset

    @pytest.fixture
    def rule_class(self) -> type[PersonalDataIndicatorRule]:
        """Provide the rule class used by the ruleset."""
        return PersonalDataIndicatorRule

    @pytest.fixture
    def expected_name(self) -> str:
        """Provide the expected canonical name of the ruleset."""
        return "personal_data_indicator"


# =============================================================================
# Model Validator Tests (our custom validation logic)
# =============================================================================


class TestPersonalDataIndicatorRulesetDataValidation:
    """Test our custom model validators on the ruleset data class."""

    def test_rejects_invalid_category(self) -> None:
        """Test that rules with category not in master list are rejected."""
        rule = PersonalDataIndicatorRule(
            name="invalid_rule",
            description="Rule with invalid category",
            patterns=("test",),
            category="invalid_category",
        )

        with pytest.raises(ValidationError, match="invalid category"):
            PersonalDataIndicatorRulesetData(
                name="personal_data_indicator",
                version="1.0.0",
                description="Test ruleset",
                categories=["email", "phone"],
                rules=[rule],
            )


# =============================================================================
# Pattern Coverage Regression Tests
# =============================================================================


class TestPersonalDataIndicatorPatternCoverage:
    """Pin patterns that must ship in the universal ruleset.

    Guards against gaps found in real codebases: `surname` and its siblings
    (the base only shipped first_name/last_name/full_name) and user-uploaded
    images, which had no pattern at all despite being personal data.
    """

    @pytest.fixture
    def patterns_by_category(self) -> dict[str, set[str]]:
        """Map each category to the set of patterns the shipped ruleset has."""
        ruleset = PersonalDataIndicatorRuleset()
        mapping: dict[str, set[str]] = {}
        for rule in ruleset.get_rules():
            mapping.setdefault(rule.category, set()).update(rule.patterns)
        return mapping

    @pytest.mark.parametrize("pattern", ["surname", "contact_name", "recipient_name"])
    def test_name_category_covers_common_name_fields(
        self, patterns_by_category: dict[str, set[str]], pattern: str
    ) -> None:
        """Common personal-name column names must be detectable."""
        assert pattern in patterns_by_category["name"]

    @pytest.mark.parametrize(
        "pattern",
        ["avatar", "photograph", "photo_url", "profile_photo", "profile_picture"],
    )
    def test_user_content_covers_user_uploaded_images(
        self, patterns_by_category: dict[str, set[str]], pattern: str
    ) -> None:
        """User-uploaded images are personal data and must be detectable."""
        assert pattern in patterns_by_category["user_content"]
