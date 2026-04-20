"""Unit tests for PersonalDataPatternMatcher.

Uses synthetic rules injected into the matcher to decouple from
production ruleset data. This tests pattern matching and proximity-based
evidence collection independently of any specific ruleset.
"""

import pytest
from waivern_analysers_shared.types import EvidenceContextSize, PatternMatchingConfig
from waivern_rulesets.personal_data_indicator import PersonalDataIndicatorRule
from waivern_schemas.connector_types import BaseMetadata

from waivern_personal_data_analyser.pattern_matcher import PersonalDataPatternMatcher

# =============================================================================
# Synthetic rules for pattern matcher tests
# =============================================================================

RULE_EMAIL = PersonalDataIndicatorRule(
    name="Email Address",
    description="Email address detection",
    category="email",
    patterns=("email",),
)

SYNTHETIC_RULES = (RULE_EMAIL,)

# PatternMatchingConfig requires a ruleset URI but it is unused by the matcher
# after refactoring — the matcher receives rules via constructor instead.
_UNUSED_RULESET_URI = "unused/test/1.0.0"


def _make_config(
    *,
    evidence_context_size: EvidenceContextSize = EvidenceContextSize.MEDIUM,
    maximum_evidence_count: int = 3,
    evidence_proximity_threshold: int = 200,
) -> PatternMatchingConfig:
    """Build a PatternMatchingConfig with evidence extraction settings."""
    return PatternMatchingConfig(
        ruleset=_UNUSED_RULESET_URI,
        evidence_context_size=evidence_context_size,
        maximum_evidence_count=maximum_evidence_count,
        evidence_proximity_threshold=evidence_proximity_threshold,
    )


class TestPersonalDataPatternMatcher:
    """Test suite for PersonalDataPatternMatcher."""

    @pytest.fixture
    def matcher(self) -> PersonalDataPatternMatcher:
        """Create a matcher with synthetic rules and default config."""
        return PersonalDataPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(),
        )

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_file.txt", connector_type="test")

    def test_find_patterns_returns_findings_for_email_pattern(
        self, matcher: PersonalDataPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Matching content produces a finding with the correct category."""
        content = "Please provide your email address for contact"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert findings[0].category == "email"

    def test_find_patterns_returns_empty_list_for_no_matches(
        self, matcher: PersonalDataPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Content with no matching patterns produces an empty list."""
        content = "This content has no personal data patterns"

        findings = matcher.find_patterns(content, metadata)

        assert findings == []


class TestProximityBasedEvidenceCollection:
    """Tests for proximity-based evidence collection in PersonalDataPatternMatcher."""

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_file.txt", connector_type="test")

    def test_spread_matches_produce_multiple_evidence_items(
        self, metadata: BaseMetadata
    ) -> None:
        """Spread matches produce multiple evidence items up to maximum_evidence_count."""
        matcher = PersonalDataPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=3,
                evidence_proximity_threshold=50,
            ),
        )

        # "email" occurrences >50 chars apart → distinct proximity groups
        content = (
            "Your email is required"
            + "x" * 100
            + "Provide email address"
            + "x" * 100
            + "Contact email needed"
        )

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert findings[0].category == "email"
        assert len(findings[0].evidence) > 1

    def test_dense_matches_of_same_pattern_produce_single_evidence_item(
        self, metadata: BaseMetadata
    ) -> None:
        """Dense matches of the same pattern produce single evidence item."""
        matcher = PersonalDataPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=3,
                evidence_proximity_threshold=200,
            ),
        )

        # Same pattern repeated close together — all within 200 char threshold
        content = "Your email here and email there and email everywhere"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1, "Expected single finding for email category"

        email_pattern = next(
            (p for p in findings[0].matched_patterns if p.pattern == "email"),
            None,
        )
        assert email_pattern is not None, "Expected 'email' pattern in matched_patterns"
        assert email_pattern.match_count == 3

    def test_maximum_evidence_count_is_respected(self, metadata: BaseMetadata) -> None:
        """Evidence collection respects maximum_evidence_count limit."""
        matcher = PersonalDataPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=2,
                evidence_proximity_threshold=50,
            ),
        )

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

        for finding in findings:
            assert len(finding.evidence) <= 2

    def test_evidence_proximity_threshold_config_is_used(
        self, metadata: BaseMetadata
    ) -> None:
        """Config evidence_proximity_threshold affects grouping behaviour."""
        matcher_small = PersonalDataPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=5,
                evidence_proximity_threshold=50,
            ),
        )
        matcher_large = PersonalDataPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=5,
                evidence_proximity_threshold=500,
            ),
        )

        # Matches ~100 chars apart: distinct with threshold=50, grouped with threshold=500
        content = (
            "email here" + "x" * 100 + "email there" + "x" * 100 + "email elsewhere"
        )

        findings_small = matcher_small.find_patterns(content, metadata)
        findings_large = matcher_large.find_patterns(content, metadata)

        assert len(findings_small) == 1
        assert len(findings_large) == 1

        # Small threshold → more evidence items; large threshold → fewer
        assert len(findings_small[0].evidence) >= len(findings_large[0].evidence)

    def test_match_count_reflects_total_not_evidence_count(
        self, metadata: BaseMetadata
    ) -> None:
        """match_count in PatternMatchDetail reflects total matches, not evidence count."""
        matcher = PersonalDataPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=2,
                evidence_proximity_threshold=50,
            ),
        )

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

        assert len(findings) == 1, "Expected single finding for email category"
        finding = findings[0]
        # Evidence is limited to max_evidence_count
        assert len(finding.evidence) <= 2
        # But total match count should reflect all matches
        total_match_count = sum(p.match_count for p in finding.matched_patterns)
        assert total_match_count >= len(finding.evidence)
