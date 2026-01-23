"""Unit tests for GDPRProcessingPurposeClassifier."""

import pytest
from waivern_core import Schema
from waivern_core.message import Message

from waivern_gdpr_processing_purpose_classifier import GDPRProcessingPurposeClassifier


@pytest.fixture
def classifier() -> GDPRProcessingPurposeClassifier:
    """Create a classifier instance with default config."""
    return GDPRProcessingPurposeClassifier()


@pytest.fixture
def output_schema() -> Schema:
    """Create output schema for tests."""
    return Schema("gdpr_processing_purpose", "1.0.0")


def make_indicator_finding(
    processing_purpose: str,
    source: str = "test.php",
) -> dict[str, object]:
    """Create a mock processing purpose indicator finding."""
    return {
        "processing_purpose": processing_purpose,
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
    """Test GDPR classification enrichment."""

    def test_classifies_analytics_as_sensitive(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that Analytics is classified as sensitive with appropriate fields."""
        # Use actual purpose name from processing_purposes ruleset
        finding = make_indicator_finding(
            "Behavioral Data Analysis for Product Improvement"
        )
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "analytics"
        assert classified["sensitive_purpose"] is True
        assert "consent" in classified["typical_lawful_bases"]
        assert classified["dpia_recommendation"] == "recommended"

    def test_classifies_payment_processing_as_operational(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that Payment Processing is classified as operational."""
        # Use actual purpose name from processing_purposes ruleset
        finding = make_indicator_finding("Payment, Billing, and Invoicing")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "operational"
        assert classified["sensitive_purpose"] is False
        assert "contract" in classified["typical_lawful_bases"]

    def test_classifies_ai_and_ml_as_sensitive_with_dpia_required(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that AI and ML is classified as sensitive with DPIA required."""
        # Use actual purpose name from processing_purposes ruleset
        finding = make_indicator_finding("Artificial Intelligence Model Training")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "ai_and_ml"
        assert classified["sensitive_purpose"] is True
        assert classified["dpia_recommendation"] == "required"

    def test_classifies_security_as_operational(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that Security is classified correctly."""
        # Use actual purpose name from processing_purposes ruleset
        finding = make_indicator_finding(
            "Security, Fraud Prevention, and Abuse Detection"
        )
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "security"
        assert classified["sensitive_purpose"] is False
        assert "legitimate_interests" in classified["typical_lawful_bases"]

    def test_classifies_marketing_as_sensitive(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that Marketing is classified as sensitive."""
        # Use actual purpose name from processing_purposes ruleset
        finding = make_indicator_finding("Consumer Marketing Within Owned Products")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "marketing_and_advertising"
        assert classified["sensitive_purpose"] is True

    def test_unknown_purpose_classified_as_unclassified(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that unknown purposes are marked as unclassified."""
        finding = make_indicator_finding("Unknown Purpose XYZ")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["purpose_category"] == "unclassified"
        assert classified["sensitive_purpose"] is False


# =============================================================================
# Summary Tests
# =============================================================================


class TestSummaryGeneration:
    """Test summary statistics generation."""

    def test_summary_counts_by_category(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that summary counts findings by purpose category."""
        findings = [
            make_indicator_finding(
                "Behavioral Data Analysis for Product Improvement"
            ),  # analytics
            make_indicator_finding(
                "Dynamic Personalization of Products and Services"
            ),  # analytics
            make_indicator_finding("Payment, Billing, and Invoicing"),  # operational
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["total_findings"] == 3
        assert summary["purpose_categories"]["analytics"] == 2
        assert summary["purpose_categories"]["operational"] == 1

    def test_summary_counts_sensitive_purposes(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that summary counts sensitive purpose findings."""
        findings = [
            make_indicator_finding(
                "Behavioral Data Analysis for Product Improvement"
            ),  # sensitive
            make_indicator_finding(
                "Consumer Marketing Within Owned Products"
            ),  # sensitive
            make_indicator_finding("Payment, Billing, and Invoicing"),  # not sensitive
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["sensitive_purposes_count"] == 2

    def test_summary_counts_dpia_required(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that summary counts DPIA required findings."""
        findings = [
            make_indicator_finding(
                "Artificial Intelligence Model Training"
            ),  # dpia required
            make_indicator_finding(
                "Behavioral Data Analysis for Product Improvement"
            ),  # dpia recommended
            make_indicator_finding(
                "Payment, Billing, and Invoicing"
            ),  # dpia not required
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
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that classifier raises ValueError on empty inputs."""
        with pytest.raises(ValueError, match="requires at least one input message"):
            classifier.process([], output_schema)

    def test_handles_multiple_input_messages(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that classifier aggregates findings from multiple inputs."""
        msg1 = make_input_message(
            [make_indicator_finding("Behavioral Data Analysis for Product Improvement")]
        )
        msg2 = make_input_message(
            [make_indicator_finding("Security, Fraud Prevention, and Abuse Detection")]
        )

        result = classifier.process([msg1, msg2], output_schema)

        assert result.content["summary"]["total_findings"] == 2

    def test_handles_finding_without_metadata(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that classifier handles findings without metadata gracefully."""
        # Note: evidence and matched_patterns must have at least 1 item (BaseFindingModel constraint)
        finding: dict[str, object] = {
            "processing_purpose": "Behavioral Data Analysis for Product Improvement",
            "evidence": [{"content": "test", "line_number": 1}],
            "matched_patterns": [{"pattern": "test", "match_count": 1}],
            # No metadata field
        }
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        # Should default to "unknown" source when metadata is missing
        assert classified["metadata"]["source"] == "unknown"
