"""Unit tests for CryptoQualityPatternMatcher.

Uses synthetic rules injected into the matcher to decouple from
production ruleset data. Tests pattern matching, polarity derivation,
and proximity-based evidence collection independently of any specific ruleset.
"""

import pytest
from waivern_analysers_shared.types import EvidenceContextSize, PatternMatchingConfig
from waivern_rulesets.crypto_quality_indicator import CryptoQualityIndicatorRule
from waivern_schemas.connector_types import BaseMetadata

from waivern_crypto_quality_analyser.pattern_matcher import CryptoQualityPatternMatcher

# =============================================================================
# Synthetic rules for pattern matcher tests
# =============================================================================

RULE_STRONG = CryptoQualityIndicatorRule(
    name="Test Strong Algo",
    description="Strong algorithm detection",
    category="strong_algo",
    algorithm="test_strong",
    quality_rating="strong",
    patterns=("test_strong_pattern",),
)

RULE_WEAK = CryptoQualityIndicatorRule(
    name="Test Weak Algo",
    description="Weak algorithm detection",
    category="weak_algo",
    algorithm="test_weak",
    quality_rating="weak",
    patterns=("test_weak_pattern",),
)

RULE_DEPRECATED = CryptoQualityIndicatorRule(
    name="Test Deprecated Algo",
    description="Deprecated algorithm detection",
    category="deprecated_algo",
    algorithm="test_deprecated",
    quality_rating="deprecated",
    patterns=("test_deprecated_pattern",),
)

SYNTHETIC_RULES = (RULE_STRONG, RULE_WEAK, RULE_DEPRECATED)

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


class TestCryptoQualityPatternMatcher:
    """Test suite for basic pattern matching behaviour."""

    @pytest.fixture
    def matcher(self) -> CryptoQualityPatternMatcher:
        """Create a matcher with synthetic rules and default config."""
        return CryptoQualityPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(),
        )

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_file.txt", connector_type="test")

    def test_find_patterns_returns_finding_for_matching_content(
        self, matcher: CryptoQualityPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Matching content produces a finding with correct algorithm and category."""
        content = "Using test_strong_pattern for hashing"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert findings[0].algorithm == "test_strong"
        assert findings[0].quality_rating == "strong"

    def test_find_patterns_returns_empty_list_for_no_matches(
        self, matcher: CryptoQualityPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Content with no matching patterns produces an empty list."""
        content = "This content has no crypto algorithm patterns"

        findings = matcher.find_patterns(content, metadata)

        assert findings == []

    def test_polarity_derived_from_quality_rating(
        self, matcher: CryptoQualityPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Strong -> positive, weak -> negative, deprecated -> negative."""
        content = (
            "test_strong_pattern and test_weak_pattern and test_deprecated_pattern"
        )

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 3
        by_algorithm = {f.algorithm: f for f in findings}
        assert by_algorithm["test_strong"].polarity == "positive"
        assert by_algorithm["test_weak"].polarity == "negative"
        assert by_algorithm["test_deprecated"].polarity == "negative"


class TestProximityBasedEvidenceCollection:
    """Tests for proximity-based evidence collection in CryptoQualityPatternMatcher."""

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_file.txt", connector_type="test")

    def test_spread_matches_produce_multiple_evidence_items(
        self, metadata: BaseMetadata
    ) -> None:
        """Spread matches produce multiple evidence items up to maximum_evidence_count."""
        matcher = CryptoQualityPatternMatcher(
            rules=(RULE_STRONG,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=3,
                evidence_proximity_threshold=50,
            ),
        )

        # Occurrences >50 chars apart -> distinct proximity groups
        content = (
            "Your test_strong_pattern is required"
            + "x" * 100
            + "Provide test_strong_pattern address"
            + "x" * 100
            + "Contact test_strong_pattern needed"
        )

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert findings[0].algorithm == "test_strong"
        assert len(findings[0].evidence) > 1

    def test_dense_matches_produce_single_evidence_item(
        self, metadata: BaseMetadata
    ) -> None:
        """Dense matches of the same pattern produce single evidence item."""
        matcher = CryptoQualityPatternMatcher(
            rules=(RULE_STRONG,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=3,
                evidence_proximity_threshold=200,
            ),
        )

        # Same pattern repeated close together — all within 200 char threshold
        content = "Your test_strong_pattern here and test_strong_pattern there and test_strong_pattern everywhere"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        pattern = next(
            (
                p
                for p in findings[0].matched_patterns
                if p.pattern == "test_strong_pattern"
            ),
            None,
        )
        assert pattern is not None
        assert pattern.match_count == 3

    def test_maximum_evidence_count_is_respected(self, metadata: BaseMetadata) -> None:
        """Evidence collection respects maximum_evidence_count limit."""
        matcher = CryptoQualityPatternMatcher(
            rules=(RULE_STRONG,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=2,
                evidence_proximity_threshold=50,
            ),
        )

        content = (
            "test_strong_pattern here"
            + "x" * 100
            + "test_strong_pattern there"
            + "x" * 100
            + "test_strong_pattern elsewhere"
            + "x" * 100
            + "test_strong_pattern again"
        )

        findings = matcher.find_patterns(content, metadata)

        for finding in findings:
            assert len(finding.evidence) <= 2
