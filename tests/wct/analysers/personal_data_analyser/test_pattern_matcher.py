"""Tests for personal data pattern matcher."""

from typing import Any

import pytest

from wct.analysers.personal_data_analyser.pattern_matcher import (
    personal_data_pattern_matcher,
)
from wct.analysers.personal_data_analyser.types import PersonalDataFinding
from wct.analysers.runners.types import (
    PatternMatcherContext,
    PatternMatchingRunnerConfig,
)
from wct.analysers.utilities import EvidenceExtractor


class TestPersonalDataPatternMatcher:
    """Test suite for personal data pattern matcher function."""

    @pytest.fixture
    def evidence_extractor(self) -> EvidenceExtractor:
        """Create a real evidence extractor for testing."""
        return EvidenceExtractor()

    @pytest.fixture
    def pattern_config(self) -> PatternMatchingRunnerConfig:
        """Create standard pattern matching configuration for testing."""
        return PatternMatchingRunnerConfig(
            ruleset_name="personal_data",
            maximum_evidence_count=3,
            evidence_context_size="small",
        )

    @pytest.fixture
    def basic_context(
        self,
        evidence_extractor: EvidenceExtractor,
        pattern_config: PatternMatchingRunnerConfig,
    ) -> PatternMatcherContext:
        """Create basic pattern matcher context for testing."""
        return PatternMatcherContext(
            rule_name="email",
            rule_description="Email address pattern",
            risk_level="medium",
            metadata={"source": "test_file.txt"},
            config=pattern_config,
            evidence_extractor=evidence_extractor,
        )

    def test_creates_finding_when_evidence_found(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test that a PersonalDataFinding is created when evidence is found."""
        # Arrange
        content = "Contact us at support@example.com for assistance"
        pattern = "support@example.com"
        rule_metadata: dict[str, Any] = {"special_category": "N"}

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is not None
        assert isinstance(result, PersonalDataFinding)
        assert result.type == "email"
        assert result.risk_level == "medium"
        assert result.special_category == "N"
        assert result.matched_pattern == pattern
        assert result.evidence is not None
        assert len(result.evidence) == 1
        assert "support@example.com" in result.evidence[0]
        assert result.metadata == {"source": "test_file.txt"}

    def test_returns_none_when_no_evidence_found(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test that None is returned when no evidence is found."""
        # Arrange
        content = "This content has no email addresses"
        pattern = "nonexistent@nowhere.com"
        rule_metadata: dict[str, Any] = {"special_category": "N"}

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is None

    def test_returns_none_when_no_content(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test that None is returned when content is empty."""
        # Arrange
        content = ""
        pattern = "anything"
        rule_metadata: dict[str, Any] = {}

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is None

    def test_uses_configuration_values_correctly(
        self, evidence_extractor: EvidenceExtractor
    ) -> None:
        """Test that configuration values are used correctly."""
        # Arrange
        config = PatternMatchingRunnerConfig(
            ruleset_name="test_ruleset",
            maximum_evidence_count=2,  # Limit to 2 pieces of evidence
            evidence_context_size="large",
        )
        context = PatternMatcherContext(
            rule_name="phone",
            rule_description="Phone number pattern",
            risk_level="high",
            metadata={},
            config=config,
            evidence_extractor=evidence_extractor,
        )

        content = "Call us at 123-456-7890 or 987-654-3210 or 555-123-4567"
        pattern = "123-456-7890"
        rule_metadata: dict[str, Any] = {}

        # Act
        result = personal_data_pattern_matcher(content, pattern, rule_metadata, context)

        # Assert
        assert result is not None
        assert result.evidence is not None
        # Should respect the maximum_evidence_count of 2
        assert len(result.evidence) <= 2

    def test_handles_special_category_metadata_correctly(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test that special category metadata is handled correctly."""
        # Arrange
        content = "Patient has diabetes condition"
        pattern = "diabetes"
        rule_metadata: dict[str, Any] = {"special_category": "Y"}

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is not None
        assert result.special_category == "Y"

    def test_handles_missing_special_category_metadata(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test that missing special category metadata is handled gracefully."""
        # Arrange
        content = "John Smith lives here"
        pattern = "John Smith"
        rule_metadata: dict[str, Any] = {}  # No special_category key

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is not None
        assert result.special_category is None

    def test_creates_copy_of_metadata(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test that metadata is copied, not referenced directly."""
        # Arrange
        content = "Contact test@example.com"
        pattern = "test@example.com"
        rule_metadata: dict[str, Any] = {}
        original_metadata = {"source": "original.txt", "mutable": "data"}

        basic_context.metadata = original_metadata

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is not None
        assert result.metadata == original_metadata
        assert result.metadata is not original_metadata  # Ensure it's a copy

    def test_handles_empty_metadata_gracefully(
        self,
        evidence_extractor: EvidenceExtractor,
        pattern_config: PatternMatchingRunnerConfig,
    ) -> None:
        """Test that empty metadata is handled gracefully."""
        # Arrange
        context = PatternMatcherContext(
            rule_name="ssn",
            rule_description="Social Security Number",
            risk_level="high",
            metadata={},
            config=pattern_config,
            evidence_extractor=evidence_extractor,
        )

        content = "SSN: 123-45-6789"
        pattern = "123-45-6789"
        rule_metadata: dict[str, Any] = {"special_category": "Y"}

        # Act
        result = personal_data_pattern_matcher(content, pattern, rule_metadata, context)

        # Assert
        assert result is not None
        assert result.metadata == {}

    def test_preserves_all_context_information(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test that all context information is preserved in the finding."""
        # Arrange
        content = "Credit card: 4111-1111-1111-1111"
        pattern = "4111-1111-1111-1111"
        rule_metadata: dict[str, Any] = {
            "special_category": "N",
            "category": "financial",
        }

        basic_context.rule_name = "credit_card"
        basic_context.risk_level = "high"

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is not None
        assert result.type == "credit_card"
        assert result.risk_level == "high"
        assert result.matched_pattern == pattern

    def test_handles_multiple_evidence_items(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test that multiple evidence items are handled correctly."""
        # Arrange
        content = "Emails: john@example.com, jane@test.com, admin@company.org"
        pattern = "john@example.com"  # Look for one specific email
        rule_metadata: dict[str, Any] = {"special_category": "N"}

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is not None
        assert result.evidence is not None
        assert len(result.evidence) >= 1  # Should find at least one match
        # Evidence should contain email addresses
        evidence_text = " ".join(result.evidence)
        assert "@" in evidence_text

    def test_handles_complex_metadata_structures(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test that complex metadata structures are handled correctly."""
        # Arrange
        content = "Phone: +44 20 1234 5678"
        pattern = "+44 20 1234 5678"
        rule_metadata: dict[str, Any] = {"special_category": "N"}
        complex_metadata = {
            "source": "database.sql",
            "table": "customers",
            "column": "phone_number",
            "row_id": 42,
            "extracted_at": "2024-01-15T10:30:00Z",
            "nested": {"depth": 1, "values": [1, 2, 3]},
        }

        basic_context.metadata = complex_metadata

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is not None
        assert result.metadata == complex_metadata
        assert result.metadata is not None
        assert result.metadata["nested"]["values"] == [1, 2, 3]

    @pytest.mark.parametrize(
        "risk_level,rule_description",
        [
            ("low", "Public information"),
            ("medium", "Personal identifier"),
            ("high", "Sensitive data"),
        ],
    )
    def test_different_risk_levels(
        self,
        risk_level: str,
        rule_description: str,
        evidence_extractor: EvidenceExtractor,
        pattern_config: PatternMatchingRunnerConfig,
    ) -> None:
        """Test that different risk levels are preserved correctly."""
        # Arrange
        context = PatternMatcherContext(
            rule_name="test_rule",
            rule_description=rule_description,
            risk_level=risk_level,
            metadata={"test": "data"},
            config=pattern_config,
            evidence_extractor=evidence_extractor,
        )

        content = "test content with keyword"
        pattern = "keyword"
        rule_metadata: dict[str, Any] = {}

        # Act
        result = personal_data_pattern_matcher(content, pattern, rule_metadata, context)

        # Assert
        assert result is not None
        assert result.risk_level == risk_level

    @pytest.mark.parametrize(
        "special_category,description",
        [
            ("Y", "Special category data"),
            ("N", "Non-special category data"),
            (None, "Unspecified category"),
            ("", "Empty category"),
        ],
    )
    def test_various_special_category_values(
        self,
        special_category: str | None,
        description: str,
        basic_context: PatternMatcherContext,
    ) -> None:
        """Test that various special category values are handled correctly."""
        # Arrange
        content = f"Data contains {description} information"
        pattern = description  # Use description as pattern for simplicity
        rule_metadata: dict[str, Any] = {}
        if special_category is not None:
            rule_metadata["special_category"] = special_category

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is not None
        assert result.special_category == special_category

    def test_edge_case_empty_pattern(
        self, basic_context: PatternMatcherContext
    ) -> None:
        """Test handling of empty pattern."""
        # Arrange
        content = "Some content here"
        pattern = ""
        rule_metadata: dict[str, Any] = {}

        # Act
        result = personal_data_pattern_matcher(
            content, pattern, rule_metadata, basic_context
        )

        # Assert
        assert result is None  # Empty pattern should not match anything
