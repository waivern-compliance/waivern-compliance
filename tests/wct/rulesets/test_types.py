"""Unit tests for ruleset types."""

import pytest
from pydantic import ValidationError

from wct.rulesets.types import (
    BaseRule,
    DataCollectionRule,
    PersonalDataRule,
    ProcessingPurposeRule,
    ProcessingPurposesRulesetData,
    ServiceIntegrationRule,
)


class TestBaseRule:
    """Test cases for the BaseRule class."""

    def test_base_rule_initialisation_with_required_parameters(self):
        """Test BaseRule initialisation with all required parameters."""
        rule = BaseRule(
            name="test_rule",
            description="A test rule",
            patterns=("pattern1", "pattern2"),
            risk_level="low",
        )

        assert rule.name == "test_rule"
        assert rule.description == "A test rule"
        assert rule.patterns == ("pattern1", "pattern2")

    def test_base_rule_must_contain_at_least_one_pattern(self):
        """Test BaseRule initialisation with empty patterns raises ValidationError."""
        with pytest.raises(
            ValidationError, match="Tuple should have at least 1 item after validation"
        ):
            BaseRule(
                name="empty_rule",
                description="Rule with no patterns",
                patterns=(),
                risk_level="low",
            )

    def test_base_rule_patterns_cannot_be_empty_strings(self):
        """Test BaseRule patterns cannot contain empty strings."""
        with pytest.raises(
            ValidationError, match="All patterns must be non-empty strings"
        ):
            BaseRule(
                name="empty_pattern_rule",
                description="Rule with empty pattern",
                patterns=("valid_pattern", ""),
                risk_level="low",
            )

    def test_base_rule_attributes_are_immutable(self):
        """Test that BaseRule attributes cannot be modified after initialisation."""
        rule = BaseRule(
            name="immutable_rule",
            description="Original description",
            patterns=("original",),
            risk_level="low",
        )

        # Attempt to modify attributes should raise ValidationError (Pydantic frozen)
        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.name = "modified_rule"

        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.description = "Modified description"

        with pytest.raises(ValidationError, match="Instance is frozen"):
            rule.patterns = ("modified", "pattern")

        # Original values should remain unchanged
        assert rule.name == "immutable_rule"
        assert rule.description == "Original description"
        assert rule.patterns == ("original",)


class TestPersonalDataRule:
    """Test cases for the PersonalDataRule class."""

    def test_personal_data_rule_with_all_fields(self):
        """Test PersonalDataRule with all fields."""
        rule = PersonalDataRule(
            name="email_rule",
            description="Email detection rule",
            patterns=("email", "e_mail"),
            special_category=False,
            risk_level="medium",
        )

        assert rule.name == "email_rule"
        assert rule.special_category is False
        assert rule.risk_level == "medium"
        assert len(rule.compliance) == 0

    def test_personal_data_rule_special_category_default(self):
        """Test PersonalDataRule special_category defaults to False."""
        rule = PersonalDataRule(
            name="basic_rule",
            description="Basic rule",
            patterns=("test",),
            risk_level="low",
        )

        assert rule.special_category is False


class TestProcessingPurposeRule:
    """Test cases for the ProcessingPurposeRule class."""

    def test_processing_purpose_rule_with_all_fields(self):
        """Test ProcessingPurposeRule with all fields."""
        rule = ProcessingPurposeRule(
            name="analytics_rule",
            description="Analytics processing rule",
            patterns=("analytics", "tracking"),
            purpose_category="ANALYTICS",
            risk_level="medium",
        )

        assert rule.name == "analytics_rule"
        assert rule.purpose_category == "ANALYTICS"
        assert rule.risk_level == "medium"


class TestProcessingPurposesRulesetData:
    """Test cases for the ProcessingPurposesRulesetData class."""

    def test_processing_purposes_ruleset_validation(self):
        """Test ProcessingPurposesRulesetData validates categories correctly."""
        rule = ProcessingPurposeRule(
            name="test_rule",
            description="Test rule",
            patterns=("test",),
            purpose_category="ANALYTICS",
            risk_level="medium",
        )

        ruleset = ProcessingPurposesRulesetData(
            name="test_ruleset",
            version="1.0.0",
            description="Test ruleset",
            purpose_categories=["ANALYTICS", "OPERATIONAL"],
            sensitive_categories=["ANALYTICS"],
            rules=[rule],
        )

        assert len(ruleset.rules) == 1
        assert "ANALYTICS" in ruleset.sensitive_categories
        assert "OPERATIONAL" in ruleset.purpose_categories

    def test_processing_purposes_ruleset_invalid_category(self):
        """Test ProcessingPurposesRulesetData rejects invalid rule categories."""
        rule = ProcessingPurposeRule(
            name="test_rule",
            description="Test rule",
            patterns=("test",),
            purpose_category="INVALID_CATEGORY",
            risk_level="medium",
        )

        with pytest.raises(ValidationError, match="invalid purpose_category"):
            ProcessingPurposesRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_categories=["ANALYTICS", "OPERATIONAL"],
                rules=[rule],
            )

    def test_processing_purposes_sensitive_categories_subset_validation(self):
        """Test sensitive_categories must be subset of purpose_categories."""
        with pytest.raises(
            ValidationError, match="must be subset of purpose_categories"
        ):
            ProcessingPurposesRulesetData(
                name="test_ruleset",
                version="1.0.0",
                description="Test ruleset",
                purpose_categories=["ANALYTICS"],
                sensitive_categories=["INVALID_SENSITIVE"],
                rules=[],
            )


class TestDataCollectionRule:
    """Test cases for the DataCollectionRule class."""

    def test_data_collection_rule_with_all_fields(self):
        """Test DataCollectionRule with all fields."""
        rule = DataCollectionRule(
            name="form_data_rule",
            description="Form data collection rule",
            patterns=("$_POST", "form_data"),
            collection_type="form_data",
            data_source="http_post",
            risk_level="medium",
        )

        assert rule.name == "form_data_rule"
        assert rule.collection_type == "form_data"
        assert rule.data_source == "http_post"
        assert rule.risk_level == "medium"


class TestServiceIntegrationRule:
    """Test cases for the ServiceIntegrationRule class."""

    def test_service_integration_rule_with_all_fields(self):
        """Test ServiceIntegrationRule with all fields."""
        rule = ServiceIntegrationRule(
            name="aws_integration",
            description="AWS integration rule",
            patterns=("aws", "s3.amazonaws"),
            service_category="cloud_infrastructure",
            purpose_category="OPERATIONAL",
            risk_level="medium",
        )

        assert rule.name == "aws_integration"
        assert rule.service_category == "cloud_infrastructure"
        assert rule.purpose_category == "OPERATIONAL"
        assert rule.risk_level == "medium"
