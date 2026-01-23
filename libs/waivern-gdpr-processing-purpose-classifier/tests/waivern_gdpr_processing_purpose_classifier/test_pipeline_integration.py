"""Integration tests for GDPR processing purpose classifier pipeline."""

import pytest
from waivern_core import Schema
from waivern_core.message import Message

from waivern_gdpr_processing_purpose_classifier import GDPRProcessingPurposeClassifier


class TestPipelineIntegration:
    """Test classifier integration in analysis pipelines."""

    @pytest.fixture
    def classifier(self) -> GDPRProcessingPurposeClassifier:
        """Create a classifier instance."""
        return GDPRProcessingPurposeClassifier()

    @pytest.fixture
    def output_schema(self) -> Schema:
        """Create output schema."""
        return Schema("gdpr_processing_purpose", "1.0.0")

    def test_processes_realistic_indicator_output(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test classifier processes realistic processing purpose indicator output."""
        # Simulate output from ProcessingPurposeAnalyser using actual purpose names
        indicator_output = {
            "findings": [
                {
                    "processing_purpose": "Behavioral Data Analysis for Product Improvement",
                    "evidence": [
                        {
                            "content": "$analytics->track('page_view', $user_id);",
                            "line_number": 42,
                        }
                    ],
                    "matched_patterns": [{"pattern": "analytics", "match_count": 1}],
                    "metadata": {
                        "source": "src/Controllers/PageController.php",
                        "context": {"function_name": "show"},
                    },
                },
                {
                    "processing_purpose": "Payment, Billing, and Invoicing",
                    "evidence": [
                        {
                            "content": "$stripe->charge($amount, $card);",
                            "line_number": 156,
                        }
                    ],
                    "matched_patterns": [{"pattern": "stripe", "match_count": 1}],
                    "metadata": {
                        "source": "src/Services/PaymentService.php",
                        "context": {"function_name": "processPayment"},
                    },
                },
                {
                    "processing_purpose": "Artificial Intelligence Model Training",
                    "evidence": [
                        {
                            "content": "$recommender->predict($user_preferences);",
                            "line_number": 89,
                        }
                    ],
                    "matched_patterns": [{"pattern": "predict", "match_count": 1}],
                    "metadata": {
                        "source": "src/Services/RecommendationService.php",
                        "context": {"function_name": "getRecommendations"},
                    },
                },
            ],
            "summary": {
                "total_findings": 3,
                "purposes": [
                    "Behavioral Data Analysis for Product Improvement",
                    "Payment, Billing, and Invoicing",
                    "Artificial Intelligence Model Training",
                ],
            },
        }

        input_msg = Message(
            id="processing_purpose_indicator",
            content=indicator_output,
            schema=Schema("processing_purpose_indicator", "1.0.0"),
        )

        result = classifier.process([input_msg], output_schema)

        # Verify output structure
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content

        # Verify all findings are classified
        findings = result.content["findings"]
        assert len(findings) == 3

        # Verify Analytics classification
        analytics_finding = next(
            f
            for f in findings
            if f["processing_purpose"]
            == "Behavioral Data Analysis for Product Improvement"
        )
        assert analytics_finding["purpose_category"] == "analytics"
        assert analytics_finding["sensitive_purpose"] is True
        assert (
            analytics_finding["metadata"]["source"]
            == "src/Controllers/PageController.php"
        )

        # Verify Payment Processing classification
        payment_finding = next(
            f
            for f in findings
            if f["processing_purpose"] == "Payment, Billing, and Invoicing"
        )
        assert payment_finding["purpose_category"] == "operational"
        assert payment_finding["sensitive_purpose"] is False

        # Verify AI and ML classification
        ai_finding = next(
            f
            for f in findings
            if f["processing_purpose"] == "Artificial Intelligence Model Training"
        )
        assert ai_finding["purpose_category"] == "ai_and_ml"
        assert ai_finding["sensitive_purpose"] is True
        assert ai_finding["dpia_recommendation"] == "required"

        # Verify summary
        summary = result.content["summary"]
        assert summary["total_findings"] == 3
        assert summary["sensitive_purposes_count"] == 2
        assert summary["dpia_required_count"] == 1

    def test_output_passes_schema_validation(
        self, classifier: GDPRProcessingPurposeClassifier, output_schema: Schema
    ) -> None:
        """Test that classifier output passes schema validation."""
        indicator_output: dict[str, object] = {
            "findings": [
                {
                    "processing_purpose": "Behavioral Data Analysis for Product Improvement",
                    "evidence": [{"content": "test", "line_number": 1}],
                    "matched_patterns": [{"pattern": "test", "match_count": 1}],
                    "metadata": {"source": "test.php", "context": {}},
                }
            ]
        }

        input_msg = Message(
            id="test",
            content=indicator_output,
            schema=Schema("processing_purpose_indicator", "1.0.0"),
        )

        result = classifier.process([input_msg], output_schema)

        # This should not raise - validation happens in result_builder
        result.validate()
