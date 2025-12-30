"""Unit tests for ProcessingPurposePatternMatcher.

This test module focuses on testing the public API of ProcessingPurposePatternMatcher,
following black-box testing principles and proper encapsulation.
"""

import pytest
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core.schemas import BaseMetadata

from waivern_processing_purpose_analyser.pattern_matcher import (
    ProcessingPurposePatternMatcher,
)
from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeFindingMetadata,
    ProcessingPurposeFindingModel,
)


class TestProcessingPurposePatternMatcher:
    """Test suite for ProcessingPurposePatternMatcher."""

    # Test constants - defined locally, not imported from implementation
    TEST_RULESET_URI = "local/processing_purposes/1.0.0"

    @pytest.fixture
    def valid_config(self) -> PatternMatchingConfig:
        """Create a valid configuration for testing."""
        return PatternMatchingConfig(
            ruleset=self.TEST_RULESET_URI,
            evidence_context_size="medium",
            maximum_evidence_count=3,
        )

    @pytest.fixture
    def sample_metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_file.php", connector_type="test")

    def test_init_creates_pattern_matcher_with_valid_config(
        self, valid_config: PatternMatchingConfig
    ) -> None:
        """Test that __init__ creates a pattern matcher with valid configuration."""
        # Act
        pattern_matcher = ProcessingPurposePatternMatcher(valid_config)

        # Assert - only verify that the object was created successfully
        # by testing it can perform its primary function
        assert pattern_matcher is not None
        assert hasattr(pattern_matcher, "find_patterns")
        assert callable(getattr(pattern_matcher, "find_patterns"))

    def test_find_patterns_returns_empty_list_when_no_patterns_match(
        self,
        valid_config: PatternMatchingConfig,
        sample_metadata: BaseMetadata,
    ) -> None:
        """Test that find_patterns returns empty list when no patterns match."""
        # Arrange
        pattern_matcher = ProcessingPurposePatternMatcher(valid_config)
        content_with_no_matches = (
            "This content has no matching patterns for processing purposes"
        )

        # Act
        findings = pattern_matcher.find_patterns(
            content_with_no_matches, sample_metadata
        )

        # Assert
        assert findings == []

    def test_find_patterns_creates_findings_for_matched_patterns(
        self,
        valid_config: PatternMatchingConfig,
        sample_metadata: BaseMetadata,
    ) -> None:
        """Test that find_patterns creates findings for matched patterns."""
        # Arrange
        pattern_matcher = ProcessingPurposePatternMatcher(valid_config)
        content_with_support = "Please contact our support team"

        # Act
        findings = pattern_matcher.find_patterns(content_with_support, sample_metadata)

        # Assert
        assert len(findings) > 0
        # Look for a support-related finding
        support_findings = [
            f
            for f in findings
            if any("support" in pattern.lower() for pattern in f.matched_patterns)
        ]
        assert len(support_findings) > 0

        support_finding = support_findings[0]
        assert isinstance(support_finding, ProcessingPurposeFindingModel)
        assert "support" in support_finding.matched_patterns
        assert len(support_finding.evidence) > 0

    def test_find_patterns_creates_multiple_findings_for_multiple_matches(
        self,
        valid_config: PatternMatchingConfig,
        sample_metadata: BaseMetadata,
    ) -> None:
        """Test that find_patterns creates multiple findings for multiple pattern matches."""
        # Arrange
        pattern_matcher = ProcessingPurposePatternMatcher(valid_config)
        content_with_multiple_matches = "Contact support for payment assistance"

        # Act
        findings = pattern_matcher.find_patterns(
            content_with_multiple_matches, sample_metadata
        )

        # Assert
        assert len(findings) > 1

        # Verify we get findings for different purposes
        all_matched_patterns = set()
        for f in findings:
            all_matched_patterns.update(f.matched_patterns)
        assert len(all_matched_patterns) > 1

        # Verify all findings have evidence
        for finding in findings:
            assert finding.evidence is not None
            assert len(finding.evidence) > 0

    def test_find_patterns_handles_case_insensitive_matching(
        self,
        valid_config: PatternMatchingConfig,
        sample_metadata: BaseMetadata,
    ) -> None:
        """Test that find_patterns performs case-insensitive pattern matching."""
        # Arrange
        pattern_matcher = ProcessingPurposePatternMatcher(valid_config)
        content_with_uppercase = "CUSTOMER DATA ANALYSIS"

        # Act
        findings = pattern_matcher.find_patterns(
            content_with_uppercase, sample_metadata
        )

        # Assert
        assert len(findings) > 0
        # Should find patterns regardless of case
        customer_findings = [
            f
            for f in findings
            if any("customer" in pattern.lower() for pattern in f.matched_patterns)
        ]
        assert len(customer_findings) > 0

    def test_find_patterns_creates_metadata_from_input_metadata(
        self,
        valid_config: PatternMatchingConfig,
        sample_metadata: BaseMetadata,
    ) -> None:
        """Test that find_patterns creates finding metadata from input metadata."""
        # Arrange
        pattern_matcher = ProcessingPurposePatternMatcher(valid_config)
        content_with_support = "Support contact information"

        # Act
        findings = pattern_matcher.find_patterns(content_with_support, sample_metadata)

        # Assert
        assert len(findings) > 0
        finding = findings[0]
        assert finding.metadata is not None
        assert isinstance(finding.metadata, ProcessingPurposeFindingMetadata)
        assert finding.metadata.source == "test_file.php"
        # Verify that metadata contains source and context fields
        metadata_dict = finding.metadata.model_dump()
        assert "source" in metadata_dict
        assert "context" in metadata_dict

    def test_find_patterns_handles_none_metadata_gracefully(
        self,
        valid_config: PatternMatchingConfig,
    ) -> None:
        """Test that find_patterns handles None metadata gracefully."""
        # Arrange
        pattern_matcher = ProcessingPurposePatternMatcher(valid_config)
        content_with_support = "Support contact information"

        # Act
        findings = pattern_matcher.find_patterns(content_with_support, None)  # type: ignore[arg-type]

        # Assert
        assert len(findings) > 0
        finding = findings[0]
        assert finding.metadata is None

    def test_find_patterns_returns_valid_finding_structure(
        self,
        valid_config: PatternMatchingConfig,
        sample_metadata: BaseMetadata,
    ) -> None:
        """Test that find_patterns returns properly structured findings."""
        # Arrange
        pattern_matcher = ProcessingPurposePatternMatcher(valid_config)
        content_with_payment = "Process payment transactions"

        # Act
        findings = pattern_matcher.find_patterns(content_with_payment, sample_metadata)

        # Assert
        assert len(findings) > 0
        finding = findings[0]

        # Verify all required fields are present and valid
        assert isinstance(finding.purpose, str)
        assert len(finding.purpose) > 0
        assert isinstance(finding.purpose_category, str)
        assert isinstance(finding.risk_level, str)
        assert finding.risk_level in ["low", "medium", "high"]
        assert isinstance(finding.compliance, list)
        assert len(finding.compliance) > 0
        assert hasattr(finding.compliance[0], "regulation")
        assert hasattr(finding.compliance[0], "relevance")
        assert isinstance(finding.matched_patterns, list)
        assert len(finding.matched_patterns) > 0
        assert isinstance(finding.evidence, list)
        assert len(finding.evidence) > 0
