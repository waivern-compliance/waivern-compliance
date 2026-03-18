"""Integration test: DataCollectionAnalyser -> GDPRDataCollectionClassifier.

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
from waivern_data_collection_analyser import DataCollectionAnalyser
from waivern_data_collection_analyser.types import (
    DataCollectionAnalyserConfig,
)
from waivern_source_code_analyser.schemas.source_code import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
)

from waivern_gdpr_data_collection_classifier import (
    GDPRDataCollectionClassifier,
)


class TestAnalyserToClassifierPipeline:
    """Test that real analyser output flows correctly into the classifier."""

    @pytest.fixture
    def analyser(self) -> DataCollectionAnalyser:
        """Create analyser with pattern matching only."""
        config = DataCollectionAnalyserConfig(
            pattern_matching=PatternMatchingConfig(
                ruleset="local/data_collection/1.0.0",
                evidence_context_size=EvidenceContextSize.MEDIUM,
                maximum_evidence_count=3,
            ),
        )
        return DataCollectionAnalyser(config=config)

    @pytest.fixture
    def classifier(self) -> GDPRDataCollectionClassifier:
        """Create classifier with default config."""
        return GDPRDataCollectionClassifier()

    @pytest.fixture
    def source_code_with_data_collection(self) -> Message:
        """Create input containing code patterns that trigger data collection detection."""
        source_code = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Test data with data collection",
            description="Test",
            source="test_repo",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=2,
                total_lines=2,
                analysis_timestamp="2025-01-01T00:00:00Z",
            ),
            data=[
                SourceCodeFileDataModel(
                    file_path="form.php",
                    language="php",
                    raw_content="$name = $_POST['username'];",
                    metadata=SourceCodeFileMetadataModel(
                        file_size=28, line_count=1, last_modified=None
                    ),
                ),
                SourceCodeFileDataModel(
                    file_path="session.php",
                    language="php",
                    raw_content="$_SESSION['user_id'] = $id;",
                    metadata=SourceCodeFileMetadataModel(
                        file_size=28, line_count=1, last_modified=None
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
        analyser: DataCollectionAnalyser,
        classifier: GDPRDataCollectionClassifier,
        source_code_with_data_collection: Message,
    ) -> None:
        """Test that real analyser output is accepted by the classifier.

        This catches format mismatches between components that unit tests
        with mocked data wouldn't reveal.
        """
        # Run real analyser
        indicator_output = analyser.process(
            [source_code_with_data_collection],
            Schema("data_collection_indicator", "1.0.0"),
        )

        # Verify analyser produced output
        assert indicator_output.schema.name == "data_collection_indicator"
        assert len(indicator_output.content.get("findings", [])) > 0

        # Run real classifier on analyser output
        gdpr_output = classifier.process(
            [indicator_output],
            Schema("gdpr_data_collection", "1.0.0"),
        )

        # Verify classifier accepted the input and produced valid output
        assert gdpr_output.schema.name == "gdpr_data_collection"
        assert "findings" in gdpr_output.content
        assert "summary" in gdpr_output.content
        assert "analysis_metadata" in gdpr_output.content

        # Verify GDPR enrichment fields exist (without checking specific values)
        for finding in gdpr_output.content["findings"]:
            assert "collection_type" in finding
            assert "data_source" in finding
            assert "gdpr_purpose_category" in finding
            assert "sensitive_purpose" in finding
            assert "dpia_recommendation" in finding
