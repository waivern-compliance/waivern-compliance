"""Integration test: ProcessingPurposeAnalyser → GDPRProcessingPurposeClassifier.

This test verifies the real analyser output is compatible with the classifier input.
It catches format mismatches that unit tests with mocked data wouldn't reveal.
"""

from typing import Any

import pytest
from waivern_analysers_shared.types import (
    EvidenceContextSize,
    LLMValidationConfig,
    PatternMatchingConfig,
)
from waivern_core import Schema
from waivern_core.message import Message
from waivern_processing_purpose_analyser import ProcessingPurposeAnalyser
from waivern_processing_purpose_analyser.types import ProcessingPurposeAnalyserConfig

from waivern_gdpr_processing_purpose_classifier import GDPRProcessingPurposeClassifier


class TestAnalyserToClassifierPipeline:
    """Test that real analyser output flows correctly into the classifier."""

    @pytest.fixture
    def analyser(self) -> ProcessingPurposeAnalyser:
        """Create analyser with pattern matching only (no LLM)."""
        config = ProcessingPurposeAnalyserConfig(
            pattern_matching=PatternMatchingConfig(
                ruleset="local/processing_purposes/1.0.0",
                evidence_context_size=EvidenceContextSize.MEDIUM,
                maximum_evidence_count=3,
            ),
            llm_validation=LLMValidationConfig(enable_llm_validation=False),
        )
        return ProcessingPurposeAnalyser(config=config)

    @pytest.fixture
    def classifier(self) -> GDPRProcessingPurposeClassifier:
        """Create classifier with default config."""
        return GDPRProcessingPurposeClassifier()

    @pytest.fixture
    def standard_input_with_processing_purposes(self) -> Message:
        """Create input containing code patterns that trigger processing purpose detection."""
        content: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "name": "Test data with processing purposes",
            "data": [
                {
                    "content": "$analytics->track('page_view', $userId);",
                    "metadata": {
                        "source": "analytics.php",
                        "connector_type": "filesystem",
                        "context": {},
                    },
                },
                {
                    "content": "$stripe->charges->create(['amount' => $total]);",
                    "metadata": {
                        "source": "payment.php",
                        "connector_type": "filesystem",
                        "context": {},
                    },
                },
            ],
        }
        return Message(
            id="test_input",
            content=content,
            schema=Schema("standard_input", "1.0.0"),
        )

    def test_real_analyser_output_flows_into_classifier(
        self,
        analyser: ProcessingPurposeAnalyser,
        classifier: GDPRProcessingPurposeClassifier,
        standard_input_with_processing_purposes: Message,
    ) -> None:
        """Test that real analyser output is accepted by the classifier.

        This catches format mismatches between components that unit tests
        with mocked data wouldn't reveal.
        """
        # Run real analyser
        indicator_output = analyser.process(
            [standard_input_with_processing_purposes],
            Schema("processing_purpose_indicator", "1.0.0"),
        )

        # Verify analyser produced output
        assert indicator_output.schema.name == "processing_purpose_indicator"
        assert len(indicator_output.content.get("findings", [])) > 0

        # Run real classifier on analyser output
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_processing_purpose", "1.0.0"),
        )

        # Verify classifier accepted the input and produced valid output
        assert gdpr_output.schema.name == "gdpr_processing_purpose"
        assert "findings" in gdpr_output.content
        assert "summary" in gdpr_output.content
        assert "analysis_metadata" in gdpr_output.content

        # Verify GDPR enrichment fields exist (without checking specific values)
        for finding in gdpr_output.content["findings"]:
            assert "purpose_category" in finding
            assert "sensitive_purpose" in finding
            assert "dpia_recommendation" in finding
