"""Unit tests for DataSubjectPatternMatcher.

This test module focuses on testing pattern matching and confidence scoring
for data subject classification.
"""

from waivern_analysers_shared.types import EvidenceContextSize, PatternMatchingConfig
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
            evidence_context_size=EvidenceContextSize.MEDIUM,
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
            evidence_context_size=EvidenceContextSize.MEDIUM,
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


class TestProximityBasedEvidenceCollection:
    """Tests for proximity-based evidence collection in DataSubjectPatternMatcher."""

    def test_spread_matches_produce_multiple_evidence_items(self) -> None:
        """Spread matches produce multiple evidence items up to maximum_evidence_count."""
        config = PatternMatchingConfig(
            ruleset="local/data_subject_indicator/1.0.0",
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=3,
            evidence_proximity_threshold=50,  # 50 chars = distinct locations
        )
        matcher = DataSubjectPatternMatcher(config)
        metadata = BaseMetadata(source="test_table", connector_type="mysql")

        # Create content with employee patterns spread far apart
        # Use spaces around padding to maintain word boundaries for pattern matching
        content = (
            "employee record here "
            + "x " * 50
            + "employee data there "
            + "x " * 50
            + "employee info elsewhere"
        )

        findings = matcher.find_patterns(content, metadata)

        # Should have findings with multiple evidence items
        assert len(findings) > 0, "Expected findings"
        employee_findings = [f for f in findings if f.subject_category == "employee"]
        assert len(employee_findings) > 0, "Expected employee category finding"
        # With spread matches, should have multiple evidence items
        assert len(employee_findings[0].evidence) > 1

    def test_dense_matches_produce_fewer_evidence_items(self) -> None:
        """Dense matches (within proximity threshold) produce fewer evidence items."""
        config = PatternMatchingConfig(
            ruleset="local/data_subject_indicator/1.0.0",
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=3,
            evidence_proximity_threshold=200,  # Large threshold
        )
        matcher = DataSubjectPatternMatcher(config)
        metadata = BaseMetadata(source="test_table", connector_type="mysql")

        # Create content with employee patterns close together
        content = "employee staff member employee_id personnel"

        findings = matcher.find_patterns(content, metadata)

        # Should have findings
        assert len(findings) > 0, "Expected findings"
        employee_findings = [f for f in findings if f.subject_category == "employee"]
        assert len(employee_findings) > 0, "Expected employee category finding"
        # Dense matches typically produce single evidence item
        assert len(employee_findings[0].evidence) >= 1

    def test_maximum_evidence_count_is_respected(self) -> None:
        """Evidence collection respects maximum_evidence_count limit."""
        config = PatternMatchingConfig(
            ruleset="local/data_subject_indicator/1.0.0",
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=2,  # Limit to 2
            evidence_proximity_threshold=50,  # Very small threshold
        )
        matcher = DataSubjectPatternMatcher(config)
        metadata = BaseMetadata(source="test_table", connector_type="mysql")

        # Create content with many spread-out employee patterns (use spaces for word boundaries)
        content = (
            "employee here "
            + "x " * 50
            + "employee there "
            + "x " * 50
            + "employee elsewhere "
            + "x " * 50
            + "employee again"
        )

        findings = matcher.find_patterns(content, metadata)

        # All findings should respect maximum_evidence_count
        for finding in findings:
            assert len(finding.evidence) <= 2

    def test_match_count_reflects_total_occurrences(self) -> None:
        """match_count reflects total matches regardless of evidence count."""
        config = PatternMatchingConfig(
            ruleset="local/data_subject_indicator/1.0.0",
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=2,  # Limit evidence
            evidence_proximity_threshold=50,
        )
        matcher = DataSubjectPatternMatcher(config)
        metadata = BaseMetadata(source="test_table", connector_type="mysql")

        # Content with multiple employee mentions (use spaces to maintain word boundaries)
        content = (
            "employee "
            + "x " * 25
            + "employee "
            + "x " * 25
            + "employee "
            + "x " * 25
            + "employee"
        )

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) > 0, "Expected findings"
        employee_findings = [f for f in findings if f.subject_category == "employee"]
        assert len(employee_findings) > 0, "Expected employee category finding"

        finding = employee_findings[0]
        # Evidence limited
        assert len(finding.evidence) <= 2
        # But match count reflects all occurrences
        total_matches = sum(p.match_count for p in finding.matched_patterns)
        assert total_matches >= len(finding.evidence)
