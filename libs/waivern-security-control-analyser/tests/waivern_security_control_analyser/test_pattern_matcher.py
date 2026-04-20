"""Unit tests for SecurityControlPatternMatcher.

Uses synthetic rules injected into the matcher to decouple from
production ruleset data. Tests pattern matching, polarity/domain
assignment, and proximity-based evidence collection independently
of any specific ruleset.
"""

import pytest
from waivern_analysers_shared.types import EvidenceContextSize, PatternMatchingConfig
from waivern_rulesets.security_control_indicator import SecurityControlIndicatorRule
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.security_domain import SecurityDomain

from waivern_security_control_analyser.pattern_matcher import (
    SecurityControlPatternMatcher,
)

# =============================================================================
# Synthetic rules for pattern matcher tests
# =============================================================================

RULE_POSITIVE = SecurityControlIndicatorRule(
    name="Test Positive Auth",
    description="Positive authentication control detection",
    category="positive_auth",
    security_domain=SecurityDomain.AUTHENTICATION,
    polarity="positive",
    patterns=("test_positive_auth_pattern",),
)

RULE_NEGATIVE = SecurityControlIndicatorRule(
    name="Test Negative Network",
    description="Negative network security control detection",
    category="negative_network",
    security_domain=SecurityDomain.NETWORK_SECURITY,
    polarity="negative",
    patterns=("test_negative_network_pattern",),
)

SYNTHETIC_RULES = (RULE_POSITIVE, RULE_NEGATIVE)

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


class TestSecurityControlPatternMatcher:
    """Test suite for basic pattern matching behaviour."""

    @pytest.fixture
    def matcher(self) -> SecurityControlPatternMatcher:
        """Create a matcher with synthetic rules and default config."""
        return SecurityControlPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(),
        )

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_file.php", connector_type="test")

    def test_find_patterns_returns_finding_for_positive_rule_match(
        self, matcher: SecurityControlPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Positive-polarity rule match produces finding with correct polarity and domain."""
        content = "Using test_positive_auth_pattern for login"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert findings[0].polarity == "positive"
        assert findings[0].security_domain == SecurityDomain.AUTHENTICATION

    def test_find_patterns_returns_finding_for_negative_rule_match(
        self, matcher: SecurityControlPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Negative-polarity rule match produces finding with correct polarity and domain."""
        content = "Using test_negative_network_pattern in firewall"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert findings[0].polarity == "negative"
        assert findings[0].security_domain == SecurityDomain.NETWORK_SECURITY

    def test_find_patterns_returns_empty_list_for_no_matches(
        self, matcher: SecurityControlPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Content with no matching patterns produces an empty list."""
        content = "This content has no security control patterns"

        findings = matcher.find_patterns(content, metadata)

        assert findings == []

    def test_description_includes_rule_name_and_match_count(
        self, matcher: SecurityControlPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Finding description includes the rule name and total match count."""
        content = "test_positive_auth_pattern here and test_positive_auth_pattern there"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert "Test Positive Auth" in findings[0].description
        assert "2 match(es)" in findings[0].description


class TestProximityBasedEvidenceCollection:
    """Tests for proximity-based evidence collection in SecurityControlPatternMatcher."""

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_file.php", connector_type="test")

    def test_spread_matches_produce_multiple_evidence_items(
        self, metadata: BaseMetadata
    ) -> None:
        """Spread matches produce multiple evidence items up to maximum_evidence_count."""
        matcher = SecurityControlPatternMatcher(
            rules=(RULE_POSITIVE,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=3,
                evidence_proximity_threshold=50,
            ),
        )

        content = (
            "Your test_positive_auth_pattern is required"
            + "x" * 100
            + "Provide test_positive_auth_pattern here"
            + "x" * 100
            + "Contact test_positive_auth_pattern needed"
        )

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert findings[0].polarity == "positive"
        assert len(findings[0].evidence) > 1

    def test_dense_matches_produce_single_evidence_item(
        self, metadata: BaseMetadata
    ) -> None:
        """Dense matches of the same pattern produce single evidence item."""
        matcher = SecurityControlPatternMatcher(
            rules=(RULE_POSITIVE,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=3,
                evidence_proximity_threshold=200,
            ),
        )

        content = "Your test_positive_auth_pattern here and test_positive_auth_pattern there and test_positive_auth_pattern everywhere"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert "3 match(es)" in findings[0].description

    def test_maximum_evidence_count_is_respected(self, metadata: BaseMetadata) -> None:
        """Evidence collection respects maximum_evidence_count limit."""
        matcher = SecurityControlPatternMatcher(
            rules=(RULE_POSITIVE,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=2,
                evidence_proximity_threshold=50,
            ),
        )

        content = (
            "test_positive_auth_pattern here"
            + "x" * 100
            + "test_positive_auth_pattern there"
            + "x" * 100
            + "test_positive_auth_pattern elsewhere"
            + "x" * 100
            + "test_positive_auth_pattern again"
        )

        findings = matcher.find_patterns(content, metadata)

        for finding in findings:
            assert len(finding.evidence) <= 2
