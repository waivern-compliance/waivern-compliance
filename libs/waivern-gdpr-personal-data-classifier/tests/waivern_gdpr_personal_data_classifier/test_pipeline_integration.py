"""End-to-end pipeline tests: PersonalDataAnalyser → GDPRPersonalDataClassifier.

These tests verify the complete personal data analysis pipeline works together,
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
from waivern_personal_data_analyser.analyser import PersonalDataAnalyser
from waivern_personal_data_analyser.types import PersonalDataAnalyserConfig

from waivern_gdpr_personal_data_classifier.classifier import GDPRPersonalDataClassifier


class TestPersonalDataToGDPRPipeline:
    """Integration tests for the full personal data → GDPR classification pipeline."""

    @pytest.fixture
    def analyser(self) -> PersonalDataAnalyser:
        """Create a PersonalDataAnalyser with pattern matching only."""
        config = PersonalDataAnalyserConfig(
            pattern_matching=PatternMatchingConfig(
                ruleset="local/personal_data_indicator/1.0.0",
                evidence_context_size="medium",
                maximum_evidence_count=3,
            ),
            llm_validation=LLMValidationConfig(
                enable_llm_validation=False,
            ),
        )
        return PersonalDataAnalyser(config=config)

    @pytest.fixture
    def classifier(self) -> GDPRPersonalDataClassifier:
        """Create a GDPRPersonalDataClassifier."""
        return GDPRPersonalDataClassifier()

    @pytest.fixture
    def standard_input_with_pii(self) -> Message:
        """Create standard_input containing various PII types.

        Uses correct BaseMetadata structure:
        - source: required identifier
        - connector_type: required connector identifier
        - context: extensible dict for additional metadata
        """
        content: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "name": "Database extract with PII",
            "data": [
                {
                    "content": "Customer record: john.doe@example.com, SSN: 123-45-6789",
                    "metadata": {
                        "source": "customers_table",
                        "connector_type": "mysql",
                        "context": {
                            "database": "crm_db",
                            "table": "customers",
                        },
                    },
                },
                {
                    "content": "Patient notes: Diagnosis of diabetes, DOB: 1985-03-15",
                    "metadata": {
                        "source": "medical_records",
                        "connector_type": "filesystem",
                        "context": {
                            "file_path": "/data/patients/notes.txt",
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
        analyser: PersonalDataAnalyser,
        classifier: GDPRPersonalDataClassifier,
        standard_input_with_pii: Message,
    ) -> None:
        """Test that the full pipeline produces valid GDPR-classified output."""
        # Step 1: Run PersonalDataAnalyser
        indicator_output = analyser.process(
            [standard_input_with_pii],
            Schema("personal_data_indicator", "1.0.0"),
        )

        # Verify intermediate output
        assert indicator_output.schema.name == "personal_data_indicator"
        assert indicator_output.schema.version == "1.0.0"
        assert len(indicator_output.content["findings"]) > 0

        # Step 2: Run GDPRPersonalDataClassifier
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_personal_data", "1.0.0"),
        )

        # Verify final output
        assert gdpr_output.schema.name == "gdpr_personal_data"
        assert gdpr_output.schema.version == "1.0.0"
        assert len(gdpr_output.content["findings"]) > 0

        # Verify GDPR-specific fields exist
        for finding in gdpr_output.content["findings"]:
            assert "privacy_category" in finding
            assert "special_category" in finding
            assert "article_references" in finding
            assert "indicator_type" in finding

    def test_pipeline_preserves_metadata_through_chain(
        self,
        analyser: PersonalDataAnalyser,
        classifier: GDPRPersonalDataClassifier,
        standard_input_with_pii: Message,
    ) -> None:
        """Test that source metadata flows through the entire pipeline."""
        # Run full pipeline
        indicator_output = analyser.process(
            [standard_input_with_pii],
            Schema("personal_data_indicator", "1.0.0"),
        )
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_personal_data", "1.0.0"),
        )

        # Find a finding that should have metadata from customers_table
        findings_with_metadata = [
            f
            for f in gdpr_output.content["findings"]
            if f.get("metadata") and f["metadata"].get("source") == "customers_table"
        ]

        assert len(findings_with_metadata) > 0, (
            "Expected at least one finding with metadata.source='customers_table'"
        )

        # Verify full metadata chain preserved
        finding = findings_with_metadata[0]
        assert finding["metadata"]["context"]["database"] == "crm_db"
        assert finding["metadata"]["context"]["table"] == "customers"

    def test_pipeline_correctly_classifies_special_categories(
        self,
        analyser: PersonalDataAnalyser,
        classifier: GDPRPersonalDataClassifier,
        standard_input_with_pii: Message,
    ) -> None:
        """Test that health data is correctly marked as special category."""
        # Run full pipeline
        indicator_output = analyser.process(
            [standard_input_with_pii],
            Schema("personal_data_indicator", "1.0.0"),
        )
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_personal_data", "1.0.0"),
        )

        # Check that we have some special category findings (from health data)
        special_category_findings = [
            f for f in gdpr_output.content["findings"] if f["special_category"] is True
        ]

        assert gdpr_output.content["summary"]["special_category_count"] == len(
            special_category_findings
        )

    def test_pipeline_builds_complete_analysis_chain(
        self,
        analyser: PersonalDataAnalyser,
        classifier: GDPRPersonalDataClassifier,
        standard_input_with_pii: Message,
    ) -> None:
        """Test that analysis chain shows both components."""
        # Run full pipeline
        indicator_output = analyser.process(
            [standard_input_with_pii],
            Schema("personal_data_indicator", "1.0.0"),
        )
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_personal_data", "1.0.0"),
        )

        # Verify output structure
        assert "findings" in gdpr_output.content
        assert "analysis_metadata" in gdpr_output.content
