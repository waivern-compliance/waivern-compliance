"""Unit tests for GDPRDataCollectionClassifier."""

from typing import Any

import pytest
from waivern_core import ClassifierContractTests, Schema
from waivern_core.message import Message

from waivern_gdpr_data_collection_classifier import (
    GDPRDataCollectionClassifier,
)


class TestGDPRDataCollectionClassifierContract(
    ClassifierContractTests[GDPRDataCollectionClassifier]
):
    """Contract tests inherited from ClassifierContractTests."""

    @pytest.fixture
    def processor_class(self) -> type[GDPRDataCollectionClassifier]:
        """Provide the classifier class to test."""
        return GDPRDataCollectionClassifier


# =============================================================================
# Synthetic classification map for unit tests
# =============================================================================

# Plain dict literal — intentionally NOT built from rule objects, so bugs in the
# classifier's _build_classification_map() logic would be caught by tests.
SYNTHETIC_CLASSIFICATION_MAP: dict[str, dict[str, Any]] = {
    "form_data": {
        "gdpr_purpose_category": "context_dependent",
        "article_references": ("Article 5", "Article 6", "Article 9", "Article 13"),
        "typical_lawful_bases": ("contract", "consent", "legitimate_interests"),
        "sensitive_purpose": False,
        "dpia_recommendation": "recommended",
    },
    "cookies": {
        "gdpr_purpose_category": "context_dependent",
        "article_references": (
            "Article 6",
            "Article 13",
            "ePrivacy Directive Article 5(3)",
        ),
        "typical_lawful_bases": ("contract", "consent", "legitimate_interests"),
        "sensitive_purpose": False,
        "dpia_recommendation": "recommended",
    },
    "database_query": {
        "gdpr_purpose_category": "context_dependent",
        "article_references": ("Article 5", "Article 6", "Article 32"),
        "typical_lawful_bases": (
            "contract",
            "consent",
            "legitimate_interests",
            "legal_obligation",
        ),
        "sensitive_purpose": False,
        "dpia_recommendation": "recommended",
    },
}


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def classifier() -> GDPRDataCollectionClassifier:
    """Create a classifier with a synthetic classification map.

    Constructs normally (loading the real ruleset), then replaces the
    classification map with synthetic data so unit tests are decoupled
    from YAML ruleset content.
    """
    instance = GDPRDataCollectionClassifier()
    instance._classification_map = SYNTHETIC_CLASSIFICATION_MAP  # pyright: ignore[reportPrivateUsage]
    return instance


@pytest.fixture
def output_schema() -> Schema:
    """Create output schema for tests."""
    return Schema("gdpr_data_collection", "1.0.0")


def make_indicator_finding(
    collection_type: str,
    data_source: str,
    source: str = "test.php",
) -> dict[str, object]:
    """Create a mock data collection indicator finding.

    Both collection_type and data_source are required — no defaults,
    so every test explicitly documents the indicator values it depends on.
    """
    return {
        "collection_type": collection_type,
        "data_source": data_source,
        "evidence": [{"content": "test content", "line_number": 1}],
        "matched_patterns": [{"pattern": "test_pattern", "match_count": 1}],
        "metadata": {"source": source, "context": {}},
    }


def make_input_message(findings: list[dict[str, object]]) -> Message:
    """Create a mock input message with findings."""
    return Message(
        id="test_input",
        content={"findings": findings},
        schema=Schema("data_collection_indicator", "1.0.0"),
    )


# =============================================================================
# Classification Tests
# =============================================================================


class TestGDPRDataCollectionClassification:
    """Test GDPR classification enrichment.

    Uses a synthetic classification map injected into the classifier to
    decouple from production ruleset data. This tests the classifier's
    behaviour independently of any specific ruleset.
    """

    def test_classifies_form_data_as_context_dependent_with_review(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that form data is classified as context_dependent with require_review."""
        finding = make_indicator_finding("form_data", "http_post")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "context_dependent"
        assert classified["sensitive_purpose"] is False
        assert "consent" in classified["typical_lawful_bases"]
        assert classified["dpia_recommendation"] == "recommended"
        assert classified["require_review"] is True

    def test_classifies_cookies_as_context_dependent(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that cookies are classified as context_dependent."""
        finding = make_indicator_finding("cookies", "http_cookie")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "context_dependent"
        assert classified["require_review"] is True

    def test_classifies_database_query_as_context_dependent(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that database queries are classified as context_dependent."""
        finding = make_indicator_finding("database_query", "mysql")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "context_dependent"
        assert classified["require_review"] is True
        assert "legal_obligation" in classified["typical_lawful_bases"]

    def test_unknown_collection_type_classified_as_unclassified(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that unknown collection types are marked as unclassified."""
        finding = make_indicator_finding("unknown_type_xyz", "unknown_source")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["gdpr_purpose_category"] == "unclassified"
        assert classified["sensitive_purpose"] is False

    def test_propagates_indicator_fields(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that collection_type and data_source are propagated to the output."""
        finding = make_indicator_finding("form_data", "http_post")
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        assert classified["collection_type"] == "form_data"
        assert classified["data_source"] == "http_post"
        assert classified["gdpr_purpose_category"] == "context_dependent"


# =============================================================================
# Summary Tests
# =============================================================================


class TestSummaryGeneration:
    """Test summary statistics generation."""

    def test_summary_counts_by_gdpr_purpose_category(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts findings by GDPR purpose category."""
        findings = [
            make_indicator_finding("form_data", "http_post"),
            make_indicator_finding("cookies", "http_cookie"),
            make_indicator_finding("database_query", "mysql"),
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["total_findings"] == 3
        assert summary["gdpr_purpose_categories"]["context_dependent"] == 3

    def test_summary_counts_sensitive_purposes(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts sensitive purpose findings (zero for DC)."""
        findings = [
            make_indicator_finding("form_data", "http_post"),
            make_indicator_finding("cookies", "http_cookie"),
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["sensitive_purposes_count"] == 0

    def test_summary_counts_dpia_required(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts DPIA required findings (zero for DC — all recommended)."""
        findings = [
            make_indicator_finding("form_data", "http_post"),
            make_indicator_finding("database_query", "mysql"),
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["dpia_required_count"] == 0

    def test_summary_counts_requires_review(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that summary counts findings requiring human review."""
        findings = [
            make_indicator_finding("form_data", "http_post"),
            make_indicator_finding("cookies", "http_cookie"),
        ]
        input_msg = make_input_message(findings)

        result = classifier.process([input_msg], output_schema)
        summary = result.content["summary"]

        assert summary["requires_review_count"] == 2


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_raises_on_empty_inputs(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that classifier raises ValueError on empty inputs."""
        with pytest.raises(ValueError, match="requires at least one input message"):
            classifier.process([], output_schema)

    def test_handles_multiple_input_messages(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that classifier aggregates findings from multiple inputs."""
        msg1 = make_input_message([make_indicator_finding("form_data", "http_post")])
        msg2 = make_input_message([make_indicator_finding("cookies", "http_cookie")])

        result = classifier.process([msg1, msg2], output_schema)

        assert result.content["summary"]["total_findings"] == 2

    def test_handles_finding_without_metadata(
        self,
        classifier: GDPRDataCollectionClassifier,
        output_schema: Schema,
    ) -> None:
        """Test that classifier handles findings without metadata gracefully."""
        finding: dict[str, object] = {
            "collection_type": "form_data",
            "data_source": "http_post",
            "evidence": [{"content": "test", "line_number": 1}],
            "matched_patterns": [{"pattern": "test", "match_count": 1}],
            # No metadata field
        }
        input_msg = make_input_message([finding])

        result = classifier.process([input_msg], output_schema)
        classified = result.content["findings"][0]

        # Should default to "unknown" source when metadata is missing
        assert classified["metadata"]["source"] == "unknown"
