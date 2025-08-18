"""Tests for personal data pattern matcher."""

import pytest

from wct.analysers.personal_data_analyser.pattern_matcher import (
    PersonalDataPatternMatcher,
)
from wct.analysers.personal_data_analyser.types import PersonalDataFindingModel
from wct.analysers.runners.types import PatternMatchingConfig
from wct.rulesets.types import Rule
from wct.schemas import StandardInputDataItemMetadataModel


class TestPersonalDataPatternMatcher:
    """Test suite for personal data pattern matcher class."""

    @pytest.fixture
    def sample_rule(self) -> Rule:
        """Create a sample rule for testing."""
        return Rule(
            name="email",
            description="Email address pattern",
            patterns=("support@example.com", "@"),
            risk_level="medium",
            metadata={"special_category": "N"},
        )

    @pytest.fixture
    def pattern_config(self) -> PatternMatchingConfig:
        """Create pattern matching config for testing."""
        return PatternMatchingConfig(
            ruleset="test_ruleset",
            maximum_evidence_count=3,
            evidence_context_size="medium",
        )

    @pytest.fixture
    def basic_metadata(self) -> StandardInputDataItemMetadataModel:
        """Create basic metadata for testing."""
        return StandardInputDataItemMetadataModel(source="test_file.txt")

    @pytest.fixture
    def pattern_matcher(
        self, pattern_config: PatternMatchingConfig
    ) -> PersonalDataPatternMatcher:
        """Create pattern matcher instance for testing."""
        return PersonalDataPatternMatcher(pattern_config)

    def test_creates_finding_when_evidence_found(
        self,
        sample_rule: Rule,
        basic_metadata: StandardInputDataItemMetadataModel,
        pattern_matcher: PersonalDataPatternMatcher,
    ) -> None:
        """Test that PersonalDataFindingModel is created when evidence is found."""
        # Arrange
        content = "Contact us at support@example.com for assistance"

        # Act
        results = pattern_matcher.match_patterns(sample_rule, content, basic_metadata)

        # Assert
        assert len(results) > 0
        result = results[0]  # Get first finding
        assert isinstance(result, PersonalDataFindingModel)
        assert result.type == "email"
        assert result.matched_pattern == "support@example.com"
        assert result.risk_level == "medium"
        assert result.special_category == "N"
        assert len(result.evidence) > 0

    def test_returns_empty_list_when_no_evidence_found(
        self,
        sample_rule: Rule,
        basic_metadata: StandardInputDataItemMetadataModel,
        pattern_matcher: PersonalDataPatternMatcher,
    ) -> None:
        """Test that empty list is returned when no evidence is found."""
        # Arrange
        content = "This content has no email patterns"

        # Act
        results = pattern_matcher.match_patterns(sample_rule, content, basic_metadata)

        # Assert
        assert results == []

    def test_handles_empty_content(
        self,
        sample_rule: Rule,
        basic_metadata: StandardInputDataItemMetadataModel,
        pattern_matcher: PersonalDataPatternMatcher,
    ) -> None:
        """Test that empty content is handled gracefully."""
        # Arrange
        content = ""

        # Act
        results = pattern_matcher.match_patterns(sample_rule, content, basic_metadata)

        # Assert
        assert results == []

    def test_handles_whitespace_only_content(
        self,
        sample_rule: Rule,
        basic_metadata: StandardInputDataItemMetadataModel,
        pattern_matcher: PersonalDataPatternMatcher,
    ) -> None:
        """Test that whitespace-only content is handled gracefully."""
        # Arrange
        content = "   \n\t  "

        # Act
        results = pattern_matcher.match_patterns(sample_rule, content, basic_metadata)

        # Assert
        assert results == []

    def test_preserves_metadata_fields(
        self,
        basic_metadata: StandardInputDataItemMetadataModel,
        pattern_matcher: PersonalDataPatternMatcher,
    ) -> None:
        """Test that metadata fields are preserved in the finding."""
        # Arrange
        content = "Email: admin@company.com"
        rule_with_metadata = Rule(
            name="admin_email",
            description="Admin email pattern",
            patterns=("admin@company.com",),
            risk_level="high",
            metadata={
                "special_category": "Y",
                "gdpr_category": "contact_details",
            },
        )

        # Act
        results = pattern_matcher.match_patterns(
            rule_with_metadata, content, basic_metadata
        )

        # Assert
        assert len(results) > 0
        result = results[0]
        assert result.special_category == "Y"
        # Verify metadata is properly populated
        assert result.metadata is not None
        assert hasattr(result.metadata, "source")

    def test_uses_context_configuration(self) -> None:
        """Test that the pattern matcher uses configuration from context."""
        # Arrange
        content = "Send message to user@domain.com for more info"
        rule = Rule(
            name="test_rule",
            description="Test rule",
            patterns=("user@domain.com",),
            risk_level="low",
            metadata={"special_category": "N"},
        )

        metadata = StandardInputDataItemMetadataModel(source="test")
        config = PatternMatchingConfig(
            ruleset="test_ruleset",
            maximum_evidence_count=1,  # Limit evidence to 1
            evidence_context_size="small",
        )
        pattern_matcher = PersonalDataPatternMatcher(config)

        # Act
        results = pattern_matcher.match_patterns(rule, content, metadata)

        # Assert
        assert len(results) > 0
        result = results[0]
        # Check that maximum_evidence_count=1 was respected
        assert len(result.evidence) <= 1

    def test_finds_multiple_patterns_in_rule(
        self,
        basic_metadata: StandardInputDataItemMetadataModel,
        pattern_matcher: PersonalDataPatternMatcher,
    ) -> None:
        """Test that multiple patterns in a rule can create multiple findings."""
        # Arrange
        content = "Contact support@example.com or admin@example.com"
        rule_with_multiple_patterns = Rule(
            name="email",
            description="Email patterns",
            patterns=("support@example.com", "admin@example.com"),
            risk_level="medium",
            metadata={"special_category": "N"},
        )

        # Act
        results = pattern_matcher.match_patterns(
            rule_with_multiple_patterns, content, basic_metadata
        )

        # Assert
        assert len(results) == 2  # Should find both patterns
        matched_patterns = {result.matched_pattern for result in results}
        assert "support@example.com" in matched_patterns
        assert "admin@example.com" in matched_patterns
