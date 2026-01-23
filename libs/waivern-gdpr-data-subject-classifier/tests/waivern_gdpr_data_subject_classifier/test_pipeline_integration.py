"""Integration test: DataSubjectAnalyser → GDPRDataSubjectClassifier.

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
from waivern_data_subject_analyser.analyser import DataSubjectAnalyser
from waivern_data_subject_analyser.types import DataSubjectAnalyserConfig

from waivern_gdpr_data_subject_classifier.classifier import GDPRDataSubjectClassifier


class TestDataSubjectToGDPRPipeline:
    """Integration tests for the full data subject → GDPR classification pipeline."""

    @pytest.fixture
    def analyser(self) -> DataSubjectAnalyser:
        """Create a DataSubjectAnalyser with pattern matching only."""
        config = DataSubjectAnalyserConfig(
            pattern_matching=PatternMatchingConfig(
                ruleset="local/data_subject_indicator/1.0.0",
                evidence_context_size=EvidenceContextSize.MEDIUM,
                maximum_evidence_count=3,
            ),
            llm_validation=LLMValidationConfig(enable_llm_validation=False),
        )
        return DataSubjectAnalyser(config=config)

    @pytest.fixture
    def classifier(self) -> GDPRDataSubjectClassifier:
        """Create a GDPRDataSubjectClassifier."""
        return GDPRDataSubjectClassifier()

    @pytest.fixture
    def standard_input_with_data_subjects(self) -> Message:
        """Create input containing data subject indicators."""
        content: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "name": "Test data with data subjects",
            "data": [
                {
                    "content": "Employee John Smith, Department: Engineering",
                    "metadata": {
                        "source": "hr_database",
                        "connector_type": "mysql",
                        "context": {},
                    },
                },
                {
                    "content": "Customer order #12345 by Jane Doe",
                    "metadata": {
                        "source": "orders_database",
                        "connector_type": "postgresql",
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
        analyser: DataSubjectAnalyser,
        classifier: GDPRDataSubjectClassifier,
        standard_input_with_data_subjects: Message,
    ) -> None:
        """Test that real analyser output is accepted by the classifier.

        This catches format mismatches between components that unit tests
        with mocked data wouldn't reveal.
        """
        # Run real analyser
        indicator_output = analyser.process(
            [standard_input_with_data_subjects],
            Schema("data_subject_indicator", "1.0.0"),
        )

        # Verify analyser produced output
        assert indicator_output.schema.name == "data_subject_indicator"
        assert len(indicator_output.content.get("findings", [])) > 0

        # Run real classifier on analyser output
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_data_subject", "1.0.0"),
        )

        # Verify classifier accepted the input and produced valid output
        assert gdpr_output.schema.name == "gdpr_data_subject"
        assert "findings" in gdpr_output.content
        assert "summary" in gdpr_output.content
        assert "analysis_metadata" in gdpr_output.content

        # Verify GDPR enrichment fields exist (without checking specific values)
        for finding in gdpr_output.content["findings"]:
            assert "data_subject_category" in finding
            assert "article_references" in finding
            assert "typical_lawful_bases" in finding
            assert "risk_modifiers" in finding
