"""Unit tests for DataSubjectPatternMatcher.

Uses synthetic rules injected into the matcher to decouple from
production ruleset data. Tests pattern matching, confidence scoring,
category grouping, and proximity-based evidence collection independently
of any specific ruleset.
"""

import pytest
from waivern_analysers_shared.types import EvidenceContextSize, PatternMatchingConfig
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule
from waivern_schemas.connector_types import BaseMetadata

from waivern_data_subject_analyser.pattern_matcher import (
    DataSubjectPatternMatcher,
)

# =============================================================================
# Synthetic rules for pattern matcher tests
# =============================================================================

RULE_EMPLOYEE_PRIMARY = DataSubjectIndicatorRule(
    name="Test Employee Primary",
    description="Primary employee indicator",
    subject_category="test_employee",
    indicator_type="primary",
    confidence_weight=45,
    patterns=("test_employee_primary_kw",),
)

RULE_EMPLOYEE_SECONDARY = DataSubjectIndicatorRule(
    name="Test Employee Secondary",
    description="Secondary employee indicator",
    subject_category="test_employee",
    indicator_type="secondary",
    confidence_weight=25,
    patterns=("test_employee_secondary_kw",),
)

RULE_CUSTOMER_PRIMARY = DataSubjectIndicatorRule(
    name="Test Customer Primary",
    description="Primary customer indicator",
    subject_category="test_customer",
    indicator_type="primary",
    confidence_weight=50,
    patterns=("test_customer_primary_kw",),
)

SYNTHETIC_RULES = (
    RULE_EMPLOYEE_PRIMARY,
    RULE_EMPLOYEE_SECONDARY,
    RULE_CUSTOMER_PRIMARY,
)

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


class TestDataSubjectPatternMatcher:
    """Test suite for DataSubjectPatternMatcher."""

    @pytest.fixture
    def matcher(self) -> DataSubjectPatternMatcher:
        """Create a matcher with synthetic rules and default config."""
        return DataSubjectPatternMatcher(
            rules=SYNTHETIC_RULES,
            config=_make_config(),
        )

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_table", connector_type="test")

    def test_confidence_score_equals_sum_of_matched_rule_weights(
        self, matcher: DataSubjectPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Confidence score for a category equals the sum of its matched rule weights."""
        content = "test_employee_primary_kw and test_employee_secondary_kw found"

        findings = matcher.find_patterns(content, metadata)

        employee_findings = [
            f for f in findings if f.subject_category == "test_employee"
        ]
        assert len(employee_findings) == 1
        assert employee_findings[0].confidence_score == 70  # 45 + 25

    def test_single_rule_match_produces_single_category_finding(
        self, matcher: DataSubjectPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """A single rule match produces one finding for its category."""
        content = "only test_customer_primary_kw here"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert findings[0].subject_category == "test_customer"
        assert findings[0].confidence_score == 50

    def test_no_matching_patterns_produces_empty_list(
        self, matcher: DataSubjectPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Content with no matching patterns produces an empty list."""
        content = "this content has no data subject patterns"

        findings = matcher.find_patterns(content, metadata)

        assert findings == []

    def test_multiple_categories_produce_separate_findings(
        self, matcher: DataSubjectPatternMatcher, metadata: BaseMetadata
    ) -> None:
        """Matches across categories produce one finding per category."""
        content = "test_employee_primary_kw and test_customer_primary_kw together"

        findings = matcher.find_patterns(content, metadata)

        categories = {f.subject_category for f in findings}
        assert categories == {"test_employee", "test_customer"}


class TestProximityBasedEvidenceCollection:
    """Tests for proximity-based evidence collection in DataSubjectPatternMatcher."""

    @pytest.fixture
    def metadata(self) -> BaseMetadata:
        """Create sample metadata for testing."""
        return BaseMetadata(source="test_table", connector_type="test")

    def test_spread_matches_produce_multiple_evidence_items(
        self, metadata: BaseMetadata
    ) -> None:
        """Spread matches produce multiple evidence items up to maximum_evidence_count."""
        matcher = DataSubjectPatternMatcher(
            rules=(RULE_EMPLOYEE_PRIMARY,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=3,
                evidence_proximity_threshold=50,
            ),
        )

        content = (
            "test_employee_primary_kw here "
            + "x " * 60
            + "test_employee_primary_kw there "
            + "x " * 60
            + "test_employee_primary_kw elsewhere"
        )

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert len(findings[0].evidence) > 1

    def test_dense_matches_produce_single_evidence_item(
        self, metadata: BaseMetadata
    ) -> None:
        """Dense matches within the proximity threshold produce a single evidence item."""
        matcher = DataSubjectPatternMatcher(
            rules=(RULE_EMPLOYEE_PRIMARY,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=3,
                evidence_proximity_threshold=200,
            ),
        )

        content = "test_employee_primary_kw here and test_employee_primary_kw there and test_employee_primary_kw everywhere"

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) == 1
        assert len(findings[0].evidence) == 1
        # All three occurrences are counted despite single evidence item
        total_matches = sum(p.match_count for p in findings[0].matched_patterns)
        assert total_matches == 3

    def test_maximum_evidence_count_is_respected(self, metadata: BaseMetadata) -> None:
        """Evidence collection respects maximum_evidence_count limit."""
        matcher = DataSubjectPatternMatcher(
            rules=(RULE_EMPLOYEE_PRIMARY,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=2,
                evidence_proximity_threshold=50,
            ),
        )

        content = (
            "test_employee_primary_kw here "
            + "x " * 60
            + "test_employee_primary_kw there "
            + "x " * 60
            + "test_employee_primary_kw elsewhere "
            + "x " * 60
            + "test_employee_primary_kw again"
        )

        findings = matcher.find_patterns(content, metadata)

        for finding in findings:
            assert len(finding.evidence) <= 2

    def test_match_count_reflects_total_occurrences(
        self, metadata: BaseMetadata
    ) -> None:
        """match_count reflects total matches regardless of evidence count."""
        matcher = DataSubjectPatternMatcher(
            rules=(RULE_EMPLOYEE_PRIMARY,),
            config=_make_config(
                evidence_context_size=EvidenceContextSize.SMALL,
                maximum_evidence_count=2,
                evidence_proximity_threshold=50,
            ),
        )

        content = (
            "test_employee_primary_kw "
            + "x " * 30
            + "test_employee_primary_kw "
            + "x " * 30
            + "test_employee_primary_kw "
            + "x " * 30
            + "test_employee_primary_kw"
        )

        findings = matcher.find_patterns(content, metadata)

        assert len(findings) > 0
        finding = findings[0]
        assert len(finding.evidence) <= 2
        total_matches = sum(p.match_count for p in finding.matched_patterns)
        assert total_matches >= len(finding.evidence)
