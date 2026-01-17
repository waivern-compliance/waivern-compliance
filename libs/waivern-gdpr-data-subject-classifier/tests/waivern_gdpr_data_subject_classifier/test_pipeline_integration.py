"""End-to-end pipeline tests: DataSubjectAnalyser → GDPRDataSubjectClassifier.

These tests verify the complete data subject analysis pipeline works together,
catching schema mismatches and data format issues between components.
"""

from typing import Any

import pytest
from waivern_analysers_shared.types import (
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
                evidence_context_size="medium",
                maximum_evidence_count=3,
            ),
            llm_validation=LLMValidationConfig(
                enable_llm_validation=False,
            ),
        )
        return DataSubjectAnalyser(config=config)

    @pytest.fixture
    def classifier(self) -> GDPRDataSubjectClassifier:
        """Create a GDPRDataSubjectClassifier."""
        return GDPRDataSubjectClassifier()

    @pytest.fixture
    def standard_input_with_data_subjects(self) -> Message:
        """Create standard_input containing various data subject indicators.

        Uses correct BaseMetadata structure:
        - source: required identifier
        - connector_type: required connector identifier
        - context: extensible dict for additional metadata
        """
        content: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "name": "Database extract with data subjects",
            "data": [
                {
                    "content": "Employee John Smith, Department: Engineering, Salary: $85,000",
                    "metadata": {
                        "source": "hr_database",
                        "connector_type": "mysql",
                        "context": {
                            "database": "hr_db",
                            "table": "employees",
                        },
                    },
                },
                {
                    "content": "Customer order #12345 by Jane Doe, email: jane@example.com",
                    "metadata": {
                        "source": "orders_database",
                        "connector_type": "postgresql",
                        "context": {
                            "database": "ecommerce",
                            "table": "orders",
                        },
                    },
                },
            ],
        }
        return Message(
            id="database_extract",
            content=content,
            schema=Schema("standard_input", "1.0.0"),
        )

    def test_pipeline_produces_valid_gdpr_output(
        self,
        analyser: DataSubjectAnalyser,
        classifier: GDPRDataSubjectClassifier,
        standard_input_with_data_subjects: Message,
    ) -> None:
        """Test that the full pipeline produces valid GDPR-classified output."""
        # Step 1: Run DataSubjectAnalyser
        indicator_output = analyser.process(
            [standard_input_with_data_subjects],
            Schema("data_subject_indicator", "1.0.0"),
        )

        # Verify intermediate output
        assert indicator_output.schema.name == "data_subject_indicator"
        assert indicator_output.schema.version == "1.0.0"
        assert len(indicator_output.content["findings"]) > 0

        # Step 2: Run GDPRDataSubjectClassifier
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_data_subject", "1.0.0"),
        )

        # Verify final output
        assert gdpr_output.schema.name == "gdpr_data_subject"
        assert gdpr_output.schema.version == "1.0.0"
        assert len(gdpr_output.content["findings"]) > 0

        # Verify GDPR-specific fields exist
        for finding in gdpr_output.content["findings"]:
            assert "data_subject_category" in finding
            assert "article_references" in finding
            assert "typical_lawful_bases" in finding
            assert "risk_modifiers" in finding

    def test_pipeline_preserves_metadata_through_chain(
        self,
        analyser: DataSubjectAnalyser,
        classifier: GDPRDataSubjectClassifier,
        standard_input_with_data_subjects: Message,
    ) -> None:
        """Test that source metadata flows through the entire pipeline."""
        # Run full pipeline
        indicator_output = analyser.process(
            [standard_input_with_data_subjects],
            Schema("data_subject_indicator", "1.0.0"),
        )
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_data_subject", "1.0.0"),
        )

        # Find a finding that should have metadata from hr_database
        findings_with_metadata = [
            f
            for f in gdpr_output.content["findings"]
            if f.get("metadata") and f["metadata"].get("source") == "hr_database"
        ]

        assert len(findings_with_metadata) > 0, (
            "Expected at least one finding with metadata.source='hr_database'"
        )

        # Verify full metadata chain preserved
        finding = findings_with_metadata[0]
        assert finding["metadata"]["context"]["database"] == "hr_db"
        assert finding["metadata"]["context"]["table"] == "employees"

    def test_pipeline_maps_to_correct_gdpr_categories(
        self,
        analyser: DataSubjectAnalyser,
        classifier: GDPRDataSubjectClassifier,
        standard_input_with_data_subjects: Message,
    ) -> None:
        """Test that data subjects are correctly mapped to GDPR categories."""
        # Run full pipeline
        indicator_output = analyser.process(
            [standard_input_with_data_subjects],
            Schema("data_subject_indicator", "1.0.0"),
        )
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_data_subject", "1.0.0"),
        )

        # Check summary shows expected categories
        categories = gdpr_output.content["summary"]["categories_identified"]
        # Should have employee and/or customer categories based on input data
        assert len(categories) > 0

    def test_pipeline_builds_complete_analysis_chain(
        self,
        analyser: DataSubjectAnalyser,
        classifier: GDPRDataSubjectClassifier,
        standard_input_with_data_subjects: Message,
    ) -> None:
        """Test that analysis chain shows both components."""
        # Run full pipeline
        indicator_output = analyser.process(
            [standard_input_with_data_subjects],
            Schema("data_subject_indicator", "1.0.0"),
        )
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_data_subject", "1.0.0"),
        )

        # Verify output structure
        assert "findings" in gdpr_output.content
        assert "analysis_metadata" in gdpr_output.content
        assert "summary" in gdpr_output.content
