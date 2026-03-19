"""Integration test: ServiceIntegrationAnalyser → GDPRServiceIntegrationClassifier.

This test verifies the real analyser output is compatible with the classifier input.
It catches format mismatches that unit tests with mocked data wouldn't reveal.
"""

import pytest
from waivern_analysers_shared.types import (
    EvidenceContextSize,
    PatternMatchingConfig,
)
from waivern_core import Schema
from waivern_core.message import Message
from waivern_service_integration_analyser import ServiceIntegrationAnalyser
from waivern_service_integration_analyser.types import (
    ServiceIntegrationAnalyserConfig,
)
from waivern_source_code_analyser.schemas.source_code import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
)

from waivern_gdpr_service_integration_classifier import (
    GDPRServiceIntegrationClassifier,
)


class TestAnalyserToClassifierPipeline:
    """Test that real analyser output flows correctly into the classifier."""

    @pytest.fixture
    def analyser(self) -> ServiceIntegrationAnalyser:
        """Create analyser with pattern matching only."""
        config = ServiceIntegrationAnalyserConfig(
            pattern_matching=PatternMatchingConfig(
                ruleset="local/service_integrations/1.0.0",
                evidence_context_size=EvidenceContextSize.MEDIUM,
                maximum_evidence_count=3,
            ),
        )
        return ServiceIntegrationAnalyser(config=config)

    @pytest.fixture
    def classifier(self) -> GDPRServiceIntegrationClassifier:
        """Create classifier with default config."""
        return GDPRServiceIntegrationClassifier()

    @pytest.fixture
    def source_code_with_service_integrations(self) -> Message:
        """Create input containing code patterns that trigger service integration detection."""
        source_code = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Test data with service integrations",
            description="Test",
            source="test_repo",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=2,
                total_lines=2,
                analysis_timestamp="2025-01-01T00:00:00Z",
            ),
            data=[
                SourceCodeFileDataModel(
                    file_path="payment.php",
                    language="php",
                    raw_content="$stripe->charges->create(['amount' => $total]);",
                    metadata=SourceCodeFileMetadataModel(
                        file_size=48, line_count=1, last_modified=None
                    ),
                ),
                SourceCodeFileDataModel(
                    file_path="storage.php",
                    language="php",
                    raw_content="$s3 = new Aws\\S3\\S3Client($config);",
                    metadata=SourceCodeFileMetadataModel(
                        file_size=35, line_count=1, last_modified=None
                    ),
                ),
            ],
        )
        return Message(
            id="test_input",
            content=source_code.model_dump(mode="json"),
            schema=Schema("source_code", "1.0.0"),
        )

    def test_real_analyser_output_flows_into_classifier(
        self,
        analyser: ServiceIntegrationAnalyser,
        classifier: GDPRServiceIntegrationClassifier,
        source_code_with_service_integrations: Message,
    ) -> None:
        """Test that real analyser output is accepted by the classifier.

        This catches format mismatches between components that unit tests
        with mocked data wouldn't reveal.
        """
        # Run real analyser
        indicator_output = analyser.process(
            [source_code_with_service_integrations],
            Schema("service_integration_indicator", "1.0.0"),
        )

        # Verify analyser produced output
        assert indicator_output.schema.name == "service_integration_indicator"
        assert len(indicator_output.content.get("findings", [])) > 0

        # Run real classifier on analyser output
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_service_integration", "1.0.0"),
        )

        # Verify classifier accepted the input and produced valid output
        assert gdpr_output.schema.name == "gdpr_service_integration"
        assert "findings" in gdpr_output.content
        assert "summary" in gdpr_output.content
        assert "analysis_metadata" in gdpr_output.content

        # Verify GDPR enrichment fields exist (without checking specific values)
        for finding in gdpr_output.content["findings"]:
            assert "service_category" in finding
            assert "service_integration_purpose" in finding
            assert "gdpr_purpose_category" in finding
            assert "sensitive_purpose" in finding
            assert "dpia_recommendation" in finding
