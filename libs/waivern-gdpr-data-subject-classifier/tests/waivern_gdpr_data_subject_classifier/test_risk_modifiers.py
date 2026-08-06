"""Tests for RiskModifierDetector pattern dispatch.

The detector is the only route by which Article 8 and Article 9 signals reach
a finding on the regex path, and a modifier that never fires produces no
downstream trace. These tests cover the dispatch mechanism — word boundary
patterns, regex value_patterns, and aggregation across evidence texts — rather
than the ruleset vocabulary itself.
"""

from waivern_rulesets.gdpr_data_subject_classification.ruleset import (
    RiskModifier,
    RiskModifiers,
)

from waivern_gdpr_data_subject_classifier.classifier import RiskModifierDetector


def _modifier(
    modifier: str,
    *,
    patterns: list[str] | None = None,
    value_patterns: list[str] | None = None,
    article_references: list[str] | None = None,
) -> RiskModifier:
    """Build a single risk modifier, defaulting the article references."""
    return RiskModifier(
        patterns=patterns or [],
        value_patterns=value_patterns or [],
        modifier=modifier,
        article_references=article_references or ["Article 8"],
    )


def _make_detector(
    *,
    risk_increasing: list[RiskModifier] | None = None,
    risk_decreasing: list[RiskModifier] | None = None,
) -> RiskModifierDetector:
    """Build a detector over an explicit modifier set, independent of the shipped ruleset."""
    return RiskModifierDetector(
        RiskModifiers(
            risk_increasing=risk_increasing or [],
            risk_decreasing=risk_decreasing or [],
        )
    )


class TestRiskModifierDetectorDispatch:
    """Tests that both pattern kinds route to their matcher."""

    def test_word_boundary_pattern_detects_modifier(self) -> None:
        """A ``patterns`` entry matches a standalone word in the evidence."""
        detector = _make_detector(
            risk_increasing=[_modifier("minor", patterns=["child"])]
        )

        assert detector.detect(["a child their age can picture"]) == ["minor"]

    def test_word_boundary_pattern_rejects_embedded_substring(self) -> None:
        """A ``patterns`` entry does not match when embedded in a longer word.

        This is what keeps 'child' from firing on 'grandchild', and equally why
        plural forms need their own entry in the ruleset.
        """
        detector = _make_detector(
            risk_increasing=[_modifier("minor", patterns=["child"])]
        )

        assert detector.detect(["grandchild of the account holder"]) == []

    def test_value_pattern_regex_detects_modifier(self) -> None:
        """A ``value_patterns`` entry is matched as a regular expression."""
        detector = _make_detector(
            risk_increasing=[_modifier("minor", value_patterns=["under.*years"])]
        )

        assert detector.detect(["pupils under eleven years old"]) == ["minor"]

    def test_risk_decreasing_modifiers_are_detected(self) -> None:
        """Risk-decreasing modifiers are searched alongside risk-increasing ones."""
        detector = _make_detector(
            risk_increasing=[_modifier("minor", patterns=["child"])],
            risk_decreasing=[
                _modifier(
                    "non_eu_resident",
                    patterns=["non-EU"],
                    article_references=["Article 3"],
                )
            ],
        )

        assert detector.detect(["non-EU data subject"]) == ["non_eu_resident"]


class TestRiskModifierDetectorAggregation:
    """Tests for how results across patterns and evidence texts combine."""

    def test_modifier_reported_once_across_multiple_evidence_texts(self) -> None:
        """The same modifier matching several evidence texts yields one entry."""
        detector = _make_detector(
            risk_increasing=[_modifier("minor", patterns=["child"])]
        )

        detected = detector.detect(["a child aged 7", "another child aged 9"])

        assert detected == ["minor"]

    def test_multiple_distinct_modifiers_returned_sorted(self) -> None:
        """Several matching modifiers are returned in sorted order."""
        detector = _make_detector(
            risk_increasing=[
                _modifier("minor", patterns=["child"]),
                _modifier(
                    "health_related",
                    patterns=["patient"],
                    article_references=["Article 9"],
                ),
            ]
        )

        detected = detector.detect(["child patient admitted to ward"])

        assert detected == ["health_related", "minor"]
