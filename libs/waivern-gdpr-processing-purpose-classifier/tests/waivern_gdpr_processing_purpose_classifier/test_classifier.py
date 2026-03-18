"""Unit tests for GDPRProcessingPurposeClassifier."""

from typing import Any

import pytest
from waivern_core import ClassifierContractTests, Schema
from waivern_core.message import Message

from waivern_gdpr_processing_purpose_classifier import GDPRProcessingPurposeClassifier


class TestGDPRProcessingPurposeClassifierContract(
    ClassifierContractTests[GDPRProcessingPurposeClassifier]
):
    """Contract tests inherited from ClassifierContractTests."""

    @pytest.fixture
    def processor_class(self) -> type[GDPRProcessingPurposeClassifier]:
        """Provide the classifier class to test."""
        return GDPRProcessingPurposeClassifier


# =============================================================================
# Synthetic classification map for unit tests
# =============================================================================

# Plain dict literal — intentionally NOT built from rule objects, so bugs in the
# classifier's _build_classification_map() logic would be caught by tests.
SYNTHETIC_CLASSIFICATION_MAP: dict[str, dict[str, Any]] = {
    "payment_processing": {
        "purpose_category": "operational",
        "article_references": ("Article 6(1)(b)", "Article 6(1)(c)"),
        "typical_lawful_bases": ("contract", "legal_obligation"),
        "sensitive_purpose": False,
        "dpia_recommendation": "not_required",
    },
    "behavioural_analytics": {
        "purpose_category": "analytics",
        "article_references": ("Article 22", "Article 35"),
        "typical_lawful_bases": ("consent", "legitimate_interests"),
        "sensitive_purpose": True,
        "dpia_recommendation": "recommended",
    },
    "ai_model_training": {
        "purpose_category": "ai_and_ml",
        "article_references": ("Article 22", "Article 35"),
        "typical_lawful_bases": ("consent", "legitimate_interests"),
        "sensitive_purpose": True,
        "dpia_recommendation": "required",
    },
    "fraud_detection": {
        "purpose_category": "security",
        "article_references": ("Article 6(1)(f)", "Article 32"),
        "typical_lawful_bases": ("legitimate_interests", "legal_obligation"),
        "sensitive_purpose": False,
        "dpia_recommendation": "not_required",
    },
    "targeted_advertising": {
        "purpose_category": "marketing_and_advertising",
        "article_references": ("Article 6(1)(a)", "Article 7"),
        "typical_lawful_bases": ("consent", "legitimate_interests"),
        "sensitive_purpose": True,
        "dpia_recommendation": "recommended",
    },
}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def classifier() -> GDPRProcessingPurposeClassifier:
    """Create a classifier with a synthetic classification map.

    Constructs normally (loading the real ruleset), then replaces the
    classification map with synthetic data so unit tests are decoupled
    from YAML ruleset content.
    """
    instance = GDPRProcessingPurposeClassifier()
    instance._classification_map = SYNTHETIC_CLASSIFICATION_MAP  # pyright: ignore[reportPrivateUsage]
    return instance


@pytest.fixture
def output_schema() -> Schema:
    """Create output schema for tests."""
    return Schema("gdpr_processing_purpose", "1.0.0")


def make_indicator_finding(
    purpose: str,
    source: str = "test.php",
) -> dict[str, object]:
    """Create a mock processing purpose indicator finding.

    purpose is required — no default, so every test explicitly documents
    the indicator value it depends on.
    """
    return {
        "purpose": purpose,
        "evidence": [{"content": "test content", "line_number": 1}],
        "matched_patterns": [{"pattern": "test_pattern", "match_count": 1}],
        "metadata": {"source": source, "context": {}},
    }


def make_input_message(findings: list[dict[str, object]]) -> Message:
    """Create a mock input message with findings."""
    return Message(
        id="test_input",
        content={"findings": findings},
        schema=Schema("processing_purpose_indicator", "1.0.0"),
    )


# =============================================================================
# Classification Tests
# =============================================================================


class TestGDPRProcessingPurposeClassification:
    """Test GDPR classification enrichment.

    Uses a synthetic classification map injected into the classifier to
    decouple from production ruleset data. This tests the classifier's
    behaviour independently of any specific ruleset.
    """

    def test_classifies_operational_purpose(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that operational purposes are classified correctly with no review required."""
        finding = make_indicator_finding("payment_processing")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "operational"
        assert classified["sensitive_purpose"] is False
        assert "contract" in classified["typical_lawful_bases"]
        assert classified["dpia_recommendation"] == "not_required"
        # require_review is excluded from JSON output when not True (to reduce noise)
        assert "require_review" not in classified

    def test_classifies_analytics_as_sensitive(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that analytics is classified as sensitive with DPIA recommended."""
        finding = make_indicator_finding("behavioural_analytics")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "analytics"
        assert classified["sensitive_purpose"] is True
        assert "consent" in classified["typical_lawful_bases"]
        assert classified["dpia_recommendation"] == "recommended"

    def test_classifies_ai_and_ml_as_sensitive_with_dpia_required(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that AI/ML purposes are classified as sensitive with DPIA required."""
        finding = make_indicator_finding("ai_model_training")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "ai_and_ml"
        assert classified["sensitive_purpose"] is True
        assert classified["dpia_recommendation"] == "required"

    def test_classifies_security_correctly(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that security purposes are classified correctly."""
        finding = make_indicator_finding("fraud_detection")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "security"
        assert classified["sensitive_purpose"] is False
        assert "legitimate_interests" in classified["typical_lawful_bases"]

    def test_classifies_marketing_as_sensitive(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that marketing is classified as sensitive."""
        finding = make_indicator_finding("targeted_advertising")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "marketing_and_advertising"
        assert classified["sensitive_purpose"] is True

    def test_unknown_purpose_classified_as_unclassified(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that unknown purposes are marked as unclassified."""
        finding = make_indicator_finding("unknown_purpose_xyz")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "unclassified"
        assert classified["sensitive_purpose"] is False

    def test_propagates_processing_purpose_field(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that the original processing purpose is propagated to the output."""
        finding = make_indicator_finding("behavioural_analytics")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["processing_purpose"] == "behavioural_analytics"


# =============================================================================
# Summary Tests
# =============================================================================


class TestSummaryGeneration:
    """Test summary statistics generation."""

    def test_summary_counts_by_category(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts findings by purpose category."""
        findings = [
            make_indicator_finding("behavioural_analytics"),  # analytics
            make_indicator_finding("ai_model_training"),  # ai_and_ml
            make_indicator_finding("payment_processing"),  # operational
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["total_findings"] == 3
        assert summary["purpose_categories"]["analytics"] == 1
        assert summary["purpose_categories"]["ai_and_ml"] == 1
        assert summary["purpose_categories"]["operational"] == 1

    def test_summary_counts_sensitive_purposes(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts sensitive purpose findings."""
        findings = [
            make_indicator_finding("behavioural_analytics"),  # sensitive
            make_indicator_finding("targeted_advertising"),  # sensitive
            make_indicator_finding("payment_processing"),  # not sensitive
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["sensitive_purposes_count"] == 2

    def test_summary_counts_dpia_required(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts DPIA required findings."""
        findings = [
            make_indicator_finding("ai_model_training"),  # required
            make_indicator_finding("behavioural_analytics"),  # recommended
            make_indicator_finding("payment_processing"),  # not required
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["dpia_required_count"] == 1


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_raises_on_empty_inputs(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that classifier raises ValueError on empty inputs."""
        with pytest.raises(ValueError, match="requires at least one input message"):
            classifier.process([], output_schema)

    def test_handles_multiple_input_messages(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that classifier aggregates findings from multiple inputs."""
        msg1 = make_input_message([make_indicator_finding("behavioural_analytics")])
        msg2 = make_input_message([make_indicator_finding("fraud_detection")])

        result = classifier.process([msg1, msg2], output_schema)

        assert result.content["summary"]["total_findings"] == 2

    def test_handles_finding_without_metadata(
        self,
        classifier: GDPRProcessingPurposeClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that classifier handles findings without metadata gracefully."""
        finding: dict[str, object] = {
            "purpose": "payment_processing",
            "evidence": [{"content": "test", "line_number": 1}],
            "matched_patterns": [{"pattern": "test", "match_count": 1}],
            # No metadata field
        }
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        # Should default to "unknown" source when metadata is missing
        assert classified["metadata"]["source"] == "unknown"
