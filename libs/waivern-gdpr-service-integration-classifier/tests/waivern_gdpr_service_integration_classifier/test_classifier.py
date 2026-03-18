"""Unit tests for GDPRServiceIntegrationClassifier."""

from typing import Any

import pytest
from waivern_core import ClassifierContractTests, Schema
from waivern_core.message import Message

from waivern_gdpr_service_integration_classifier import (
    GDPRServiceIntegrationClassifier,
)


class TestGDPRServiceIntegrationClassifierContract(
    ClassifierContractTests[GDPRServiceIntegrationClassifier]
):
    """Contract tests inherited from ClassifierContractTests."""

    @pytest.fixture
    def processor_class(self) -> type[GDPRServiceIntegrationClassifier]:
        """Provide the classifier class to test."""
        return GDPRServiceIntegrationClassifier


# =============================================================================
# Synthetic classification map for unit tests
# =============================================================================

# Plain dict literal — intentionally NOT built from rule objects, so bugs in the
# classifier's _build_classification_map() logic would be caught by tests.
SYNTHETIC_CLASSIFICATION_MAP: dict[str, dict[str, Any]] = {
    "cloud_infrastructure": {
        "gdpr_purpose_category": "operational",
        "article_references": ("Article 28", "Article 32"),
        "typical_lawful_bases": ("contract", "legitimate_interests"),
        "sensitive_purpose": False,
        "dpia_recommendation": "not_required",
    },
    "communication": {
        "gdpr_purpose_category": "context_dependent",
        "article_references": ("Article 6", "Article 13"),
        "typical_lawful_bases": ("contract", "consent", "legitimate_interests"),
        "sensitive_purpose": False,
        "dpia_recommendation": "recommended",
    },
    "user_analytics": {
        "gdpr_purpose_category": "analytics",
        "article_references": ("Article 6(1)(a)", "Article 22"),
        "typical_lawful_bases": ("consent", "legitimate_interests"),
        "sensitive_purpose": True,
        "dpia_recommendation": "recommended",
    },
    "ai_ml_services": {
        "gdpr_purpose_category": "ai_and_ml",
        "article_references": ("Article 22", "Article 35"),
        "typical_lawful_bases": ("consent", "legitimate_interests"),
        "sensitive_purpose": True,
        "dpia_recommendation": "required",
    },
    "healthcare_integrations": {
        "gdpr_purpose_category": "healthcare",
        "article_references": ("Article 9", "Article 6(1)(b)"),
        "typical_lawful_bases": ("contract", "explicit_consent"),
        "sensitive_purpose": True,
        "dpia_recommendation": "required",
    },
}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def classifier() -> GDPRServiceIntegrationClassifier:
    """Create a classifier with a synthetic classification map.

    Constructs normally (loading the real ruleset), then replaces the
    classification map with synthetic data so unit tests are decoupled
    from YAML ruleset content.
    """
    instance = GDPRServiceIntegrationClassifier()
    instance._classification_map = SYNTHETIC_CLASSIFICATION_MAP  # pyright: ignore[reportPrivateUsage]
    return instance


@pytest.fixture
def output_schema() -> Schema:
    """Create output schema for tests."""
    return Schema("gdpr_service_integration", "1.0.0")


def make_indicator_finding(
    service_category: str,
    purpose_category: str,
    source: str = "test.php",
) -> dict[str, object]:
    """Create a mock service integration indicator finding.

    Both service_category and purpose_category are required — no defaults,
    so every test explicitly documents the indicator values it depends on.
    """
    return {
        "service_category": service_category,
        "purpose_category": purpose_category,
        "evidence": [{"content": "test content", "line_number": 1}],
        "matched_patterns": [{"pattern": "test_pattern", "match_count": 1}],
        "metadata": {"source": source, "context": {}},
    }


def make_input_message(findings: list[dict[str, object]]) -> Message:
    """Create a mock input message with findings."""
    return Message(
        id="test_input",
        content={"findings": findings},
        schema=Schema("service_integration_indicator", "1.0.0"),
    )


# =============================================================================
# Classification Tests
# =============================================================================


class TestGDPRServiceIntegrationClassification:
    """Test GDPR classification enrichment.

    Uses a synthetic classification map injected into the classifier to
    decouple from production ruleset data. This tests the classifier's
    behaviour independently of any specific ruleset.
    """

    def test_classifies_cloud_infrastructure_as_operational(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that cloud infrastructure is classified as operational with no review required."""
        finding = make_indicator_finding("cloud_infrastructure", "operational")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "operational"
        assert classified["sensitive_purpose"] is False
        assert "contract" in classified["typical_lawful_bases"]
        assert classified["dpia_recommendation"] == "not_required"
        # require_review is excluded from JSON output when not True (to reduce noise)
        assert "require_review" not in classified

    def test_classifies_analytics_as_sensitive(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that analytics is classified as sensitive with DPIA recommended."""
        finding = make_indicator_finding("user_analytics", "analytics")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "analytics"
        assert classified["sensitive_purpose"] is True
        assert "consent" in classified["typical_lawful_bases"]
        assert classified["dpia_recommendation"] == "recommended"

    def test_classifies_ai_services_as_sensitive_with_dpia_required(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that AI/ML services are classified as sensitive with DPIA required."""
        finding = make_indicator_finding("ai_ml_services", "data_processing")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "ai_and_ml"
        assert classified["sensitive_purpose"] is True
        assert classified["dpia_recommendation"] == "required"

    def test_classifies_healthcare_as_sensitive_with_dpia_required(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that healthcare is classified as sensitive with DPIA required."""
        finding = make_indicator_finding("healthcare_integrations", "operational")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "healthcare"
        assert classified["sensitive_purpose"] is True
        assert classified["dpia_recommendation"] == "required"
        assert "explicit_consent" in classified["typical_lawful_bases"]

    def test_classifies_communication_as_context_dependent_with_review(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that communication is classified as context_dependent with require_review."""
        finding = make_indicator_finding("communication", "operational")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "context_dependent"
        assert classified["require_review"] is True

    def test_unknown_service_category_classified_as_unclassified(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that unknown service categories are marked as unclassified."""
        finding = make_indicator_finding("unknown_service_xyz", "operational")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "unclassified"
        assert classified["sensitive_purpose"] is False

    def test_propagates_indicator_fields_with_divergent_purpose(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that indicator fields are propagated and can diverge from GDPR classification.

        Communication has SI purpose_category "operational" but GDPR classifies it
        as "context_dependent" — both values should appear in the output.
        """
        finding = make_indicator_finding("communication", "operational")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["service_category"] == "communication"
        assert classified["service_integration_purpose"] == "operational"
        assert classified["gdpr_purpose_category"] == "context_dependent"


# =============================================================================
# Summary Tests
# =============================================================================


class TestSummaryGeneration:
    """Test summary statistics generation."""

    def test_summary_counts_by_gdpr_purpose_category(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts findings by GDPR purpose category."""
        findings = [
            make_indicator_finding("user_analytics", "analytics"),  # analytics
            make_indicator_finding(
                "cloud_infrastructure", "operational"
            ),  # operational
            make_indicator_finding("communication", "operational"),  # context_dependent
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["total_findings"] == 3
        assert summary["gdpr_purpose_categories"]["analytics"] == 1
        assert summary["gdpr_purpose_categories"]["operational"] == 1
        assert summary["gdpr_purpose_categories"]["context_dependent"] == 1

    def test_summary_counts_sensitive_purposes(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts sensitive purpose findings."""
        findings = [
            make_indicator_finding("user_analytics", "analytics"),  # sensitive
            make_indicator_finding("ai_ml_services", "data_processing"),  # sensitive
            make_indicator_finding(
                "cloud_infrastructure", "operational"
            ),  # not sensitive
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["sensitive_purposes_count"] == 2

    def test_summary_counts_dpia_required(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts DPIA required findings."""
        findings = [
            make_indicator_finding("ai_ml_services", "data_processing"),  # required
            make_indicator_finding("user_analytics", "analytics"),  # recommended
            make_indicator_finding(
                "cloud_infrastructure", "operational"
            ),  # not required
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["dpia_required_count"] == 1

    def test_summary_counts_requires_review(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts findings requiring human review."""
        findings = [
            make_indicator_finding("communication", "operational"),  # context_dependent
            make_indicator_finding(
                "cloud_infrastructure", "operational"
            ),  # operational
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["requires_review_count"] == 1


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_raises_on_empty_inputs(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that classifier raises ValueError on empty inputs."""
        with pytest.raises(ValueError, match="requires at least one input message"):
            classifier.process([], output_schema)

    def test_handles_multiple_input_messages(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that classifier aggregates findings from multiple inputs."""
        msg1 = make_input_message(
            [make_indicator_finding("user_analytics", "analytics")]
        )
        msg2 = make_input_message(
            [make_indicator_finding("cloud_infrastructure", "operational")]
        )

        result = classifier.process([msg1, msg2], output_schema)

        assert result.content["summary"]["total_findings"] == 2

    def test_handles_finding_without_metadata(
        self,
        classifier: GDPRServiceIntegrationClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that classifier handles findings without metadata gracefully."""
        finding: dict[str, object] = {
            "service_category": "cloud_infrastructure",
            "purpose_category": "operational",
            "evidence": [{"content": "test", "line_number": 1}],
            "matched_patterns": [{"pattern": "test", "match_count": 1}],
            # No metadata field
        }
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        # Should default to "unknown" source when metadata is missing
        assert classified["metadata"]["source"] == "unknown"
