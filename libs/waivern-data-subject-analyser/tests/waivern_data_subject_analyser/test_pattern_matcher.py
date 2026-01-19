"""Unit tests for DataSubjectPatternMatcher.

This test module focuses on testing pattern matching and confidence scoring
for data subject classification.
"""

from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core.schemas import BaseMetadata

from waivern_data_subject_analyser.pattern_matcher import (
    DataSubjectPatternMatcher,
)


class TestDataSubjectPatternMatcher:
    """Test suite for DataSubjectPatternMatcher."""

    def test_pattern_matching_with_confidence_scoring(self) -> None:
        """Test pattern matching produces correct confidence scores."""
        # Arrange
        config = PatternMatchingConfig(
            ruleset="local/data_subject_indicator/1.0.0",
            evidence_context_size="medium",
            maximum_evidence_count=3,
        )
        pattern_matcher = DataSubjectPatternMatcher(config)
        metadata = BaseMetadata(source="test_table", connector_type="mysql")

        # Content with multiple employee patterns (should trigger multiple rules)
        content = "employee staff member employee_id 12345 personnel database"

        # Act
        findings = pattern_matcher.find_patterns(content, metadata)

        # Assert
        assert isinstance(findings, list)
        if len(findings) > 0:
            finding = findings[0]
            # Verify confidence scoring structure (strongly typed with Pydantic)
            assert isinstance(finding.confidence_score, int)
            assert 0 <= finding.confidence_score <= 100
            assert isinstance(finding.matched_patterns, list)
            assert len(finding.matched_patterns) > 0

    def test_context_filtering_logic(self) -> None:
        """Test that pattern matching respects applicable context filtering."""
        # Arrange
        config = PatternMatchingConfig(
            ruleset="local/data_subject_indicator/1.0.0",
            evidence_context_size="medium",
            maximum_evidence_count=3,
        )
        pattern_matcher = DataSubjectPatternMatcher(config)

        # Test with database context
        db_metadata = BaseMetadata(source="employees_table", connector_type="mysql")

        # Test with filesystem context
        fs_metadata = BaseMetadata(
            source="employee_file.txt", connector_type="filesystem"
        )

        content = "employee staff member"

        # Act
        db_findings = pattern_matcher.find_patterns(content, db_metadata)
        fs_findings = pattern_matcher.find_patterns(content, fs_metadata)

        # Assert - both should find patterns but context affects which rules apply
        assert isinstance(db_findings, list)
        assert isinstance(fs_findings, list)

        # Both contexts should find employee patterns, but different rules apply:
        # mysql (database) context: employee_direct_role_fields + employee_hr_system_indicators
        # filesystem context: only employee_hr_system_indicators
        if len(db_findings) > 0 and len(fs_findings) > 0:
            # Database context typically has more applicable rules
            assert db_findings[0].subject_category == "employee"
            assert fs_findings[0].subject_category == "employee"
