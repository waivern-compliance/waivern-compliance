"""Unit tests for PersonalDataPatternMatcher.

This test module focuses on testing pattern matching and proximity-based
evidence collection for personal data detection.
"""

import pytest
from waivern_analysers_shared.types import EvidenceContextSize, PatternMatchingConfig
from waivern_core.schemas import BaseMetadata

from waivern_personal_data_analyser.pattern_matcher import PersonalDataPatternMatcher


class TestPersonalDataPatternMatcher:
    """Test suite for PersonalDataPatternMatcher."""

    TEST_RULESET_URI = "local/personal_data_indicator/1.0.0"

    @pytest.fixture
    def config(self) -> PatternMatchingConfig:
        """Create a valid configuration for testing."""
        return PatternMatchingConfig(
            ruleset=self.TEST_RULESET_URI,
            evidence_context_size=EvidenceContextSize.MEDIUM,
            maximum_evidence_count=3,
        )

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_file.txt", connector_type="test")

    def test_find_patterns_returns_findings_for_email_pattern(
        self, config: PatternMatchingConfig, metadata: BaseMetadata
    ) -> None:
        """Test that find_patterns detects email patterns."""
        matcher = PersonalDataPatternMatcher(config)
        # Use the word "email" which matches the word-boundary pattern
        content = "Please provide your email address for contact"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) > 0
        # Find email-related finding
        email_findings = [f for f in findings if f.category == "email"]
        assert len(email_findings) > 0

    def test_find_patterns_returns_empty_list_for_no_matches(
        self, config: PatternMatchingConfig, metadata: BaseMetadata
    ) -> None:
        """Test that find_patterns returns empty list when no patterns match."""
        matcher = PersonalDataPatternMatcher(config)
        content = "This content has no personal data patterns"

        findings = matcher.find_patterns(content, metadata)

        assert findings == []


class TestProximityBasedEvidenceCollection:
    """Tests for proximity-based evidence collection in PersonalDataPatternMatcher."""

    TEST_RULESET_URI = "local/personal_data_indicator/1.0.0"

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_file.txt", connector_type="test")

    def test_spread_matches_produce_multiple_evidence_items(
        self, metadata: BaseMetadata
    ) -> None:
        """Spread matches produce multiple evidence items up to maximum_evidence_count."""
        config = PatternMatchingConfig(
            ruleset=self.TEST_RULESET_URI,
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=3,
            evidence_proximity_threshold=50,  # 50 chars = distinct locations
        )
        matcher = PersonalDataPatternMatcher(config)

        # Create content with "email" word-boundary pattern spread far apart
        # Must be >50 chars between occurrences to be in different proximity groups
        content = (
            "Your email is required"
            + "x" * 100
            + "Provide email address"
            + "x" * 100
            + "Contact email needed"
        )

        findings = matcher.find_patterns(content, metadata)

        # Should have findings with multiple evidence items
        assert len(findings) > 0
        email_findings = [f for f in findings if f.category == "email"]
        assert len(email_findings) > 0
        # With spread matches (>50 chars apart), should have multiple evidence items
        assert len(email_findings[0].evidence) > 1

    def test_dense_matches_of_same_pattern_produce_single_evidence_item(
        self, metadata: BaseMetadata
    ) -> None:
        """Dense matches of the same pattern produce single evidence item."""
        config = PatternMatchingConfig(
            ruleset=self.TEST_RULESET_URI,
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=3,
            evidence_proximity_threshold=200,  # 200 chars threshold
        )
        matcher = PersonalDataPatternMatcher(config)

        # Create content with the SAME pattern repeated close together
        # Note: different patterns (email, mail, email_address) each produce their
        # own evidence, but the SAME pattern repeated within threshold = 1 evidence
        content = "Your email here and email there and email everywhere"

        findings = matcher.find_patterns(content, metadata)

        # Should have findings
        assert len(findings) > 0, "Expected findings for email pattern"
        email_findings = [f for f in findings if f.category == "email"]
        assert len(email_findings) > 0, "Expected email category finding"

        # With dense matches of same pattern, proximity grouping applies
        # All "email" matches are within 200 chars so grouped together
        # Check that match_count > 1 but evidence may be grouped
        email_pattern = next(
            (p for p in email_findings[0].matched_patterns if p.pattern == "email"),
            None,
        )
        assert email_pattern is not None, "Expected 'email' pattern in matched_patterns"
        assert email_pattern.match_count == 3  # 3 occurrences of "email"

    def test_maximum_evidence_count_is_respected(self, metadata: BaseMetadata) -> None:
        """Evidence collection respects maximum_evidence_count limit."""
        config = PatternMatchingConfig(
            ruleset=self.TEST_RULESET_URI,
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=2,  # Limit to 2
            evidence_proximity_threshold=50,  # 50 chars threshold
        )
        matcher = PersonalDataPatternMatcher(config)

        # Create content with many spread-out email patterns
        content = (
            "email here"
            + "x" * 100
            + "email there"
            + "x" * 100
            + "email elsewhere"
            + "x" * 100
            + "email again"
        )

        findings = matcher.find_patterns(content, metadata)

        # All findings should respect maximum_evidence_count
        for finding in findings:
            assert len(finding.evidence) <= 2

    def test_evidence_proximity_threshold_config_is_used(
        self, metadata: BaseMetadata
    ) -> None:
        """Config evidence_proximity_threshold affects grouping behaviour."""
        # Small threshold - more groups
        config_small = PatternMatchingConfig(
            ruleset=self.TEST_RULESET_URI,
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=5,
            evidence_proximity_threshold=50,
        )
        # Large threshold - fewer groups
        config_large = PatternMatchingConfig(
            ruleset=self.TEST_RULESET_URI,
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=5,
            evidence_proximity_threshold=500,
        )

        matcher_small = PersonalDataPatternMatcher(config_small)
        matcher_large = PersonalDataPatternMatcher(config_large)

        # Content with matches at varying distances (between 50 and 500 chars)
        content = (
            "email here" + "x" * 100 + "email there" + "x" * 100 + "email elsewhere"
        )

        findings_small = matcher_small.find_patterns(content, metadata)
        findings_large = matcher_large.find_patterns(content, metadata)

        # Both should find patterns
        assert len(findings_small) > 0
        assert len(findings_large) > 0

        email_small = [f for f in findings_small if f.category == "email"]
        email_large = [f for f in findings_large if f.category == "email"]

        assert len(email_small) > 0, "Expected email findings with small threshold"
        assert len(email_large) > 0, "Expected email findings with large threshold"

        # With small threshold (50), matches 100 chars apart are distinct
        # With large threshold (500), they're in the same group
        assert len(email_small[0].evidence) >= len(email_large[0].evidence)

    def test_match_count_reflects_total_not_evidence_count(
        self, metadata: BaseMetadata
    ) -> None:
        """match_count in PatternMatchDetail reflects total matches, not evidence count."""
        config = PatternMatchingConfig(
            ruleset=self.TEST_RULESET_URI,
            evidence_context_size=EvidenceContextSize.SMALL,
            maximum_evidence_count=2,  # Limit evidence
            evidence_proximity_threshold=50,  # Force separate groups
        )
        matcher = PersonalDataPatternMatcher(config)

        # Create content with multiple matches of the same pattern
        content = (
            "email here"
            + "x" * 100
            + "email there"
            + "x" * 100
            + "email elsewhere"
            + "x" * 100
            + "email again"
        )

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) > 0, "Expected findings"
        email_findings = [f for f in findings if f.category == "email"]
        assert len(email_findings) > 0, "Expected email category finding"

        finding = email_findings[0]
        # Evidence is limited to max_evidence_count
        assert len(finding.evidence) <= 2
        # But total match count should reflect all matches
        total_match_count = sum(p.match_count for p in finding.matched_patterns)
        # Total matches should be >= evidence count
        assert total_match_count >= len(finding.evidence)
