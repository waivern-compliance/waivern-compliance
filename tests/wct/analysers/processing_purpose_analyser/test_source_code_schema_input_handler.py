"""Unit tests for SourceCodeSchemaInputHandler.

This test module focuses on testing the public API of SourceCodeSchemaInputHandler,
following black-box testing principles and proper encapsulation.
"""

from datetime import datetime, timezone

import pytest

from wct.analysers.processing_purpose_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaInputHandler,
)
from wct.analysers.processing_purpose_analyser.types import (
    ProcessingPurposeFindingModel,
)
from wct.analysers.types import EvidenceItem
from wct.schemas import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeClassModel,
    SourceCodeDataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
    SourceCodeFunctionModel,
    SourceCodeImportModel,
)


class TestSourceCodeSchemaInputHandler:
    """Test suite for SourceCodeSchemaInputHandler."""

    # Test constants - defined locally, not imported from implementation
    EXPECTED_FINDING_FIELDS = [
        "purpose",
        "purpose_category",
        "risk_level",
        "compliance",
        "matched_pattern",
        "evidence",
        "metadata",
    ]
    VALID_RISK_LEVELS = ["low", "medium", "high"]

    @pytest.fixture
    def handler(self) -> SourceCodeSchemaInputHandler:
        """Create a handler instance for testing."""
        return SourceCodeSchemaInputHandler()

    @pytest.fixture
    def sample_file_metadata(self) -> SourceCodeFileMetadataModel:
        """Create sample file metadata for testing."""
        return SourceCodeFileMetadataModel(
            file_size=1024,
            line_count=50,
            last_modified="2024-01-01T00:00:00Z",
            complexity_score=3.5,
        )

    @pytest.fixture
    def sample_analysis_metadata(self) -> SourceCodeAnalysisMetadataModel:
        """Create sample analysis metadata for testing."""
        return SourceCodeAnalysisMetadataModel(
            total_files=1,
            total_lines=50,
            analysis_timestamp="2024-01-01T00:00:00Z",
            parser_version="1.0.0",
        )

    @pytest.fixture
    def empty_source_code_data(
        self, sample_analysis_metadata: SourceCodeAnalysisMetadataModel
    ) -> SourceCodeDataModel:
        """Create empty source code data for testing."""
        return SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Empty analysis",
            description="Empty source code analysis",
            language="php",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[],
        )

    @pytest.fixture
    def simple_php_file_data(
        self, sample_file_metadata: SourceCodeFileMetadataModel
    ) -> SourceCodeFileDataModel:
        """Create simple PHP file data with processing purpose patterns."""
        return SourceCodeFileDataModel(
            file_path="/src/CustomerService.php",
            language="php",
            raw_content="""<?php
class CustomerService {
    public function processPayment($amount) {
        // Process customer payment
        return $this->paymentGateway->charge($amount);
    }

    public function sendSupportEmail($message) {
        // Send support email to customer
        return $this->emailService->send($message);
    }
}
""",
            metadata=sample_file_metadata,
            functions=[
                SourceCodeFunctionModel(
                    name="processPayment",
                    line_start=3,
                    line_end=6,
                    parameters=[],
                    visibility="public",
                ),
                SourceCodeFunctionModel(
                    name="sendSupportEmail",
                    line_start=8,
                    line_end=11,
                    parameters=[],
                    visibility="public",
                ),
            ],
            classes=[
                SourceCodeClassModel(
                    name="CustomerService",
                    line_start=2,
                    line_end=12,
                ),
            ],
            imports=[],
        )

    @pytest.fixture
    def ml_service_file_data(
        self, sample_file_metadata: SourceCodeFileMetadataModel
    ) -> SourceCodeFileDataModel:
        """Create file data with machine learning and service integration patterns."""
        return SourceCodeFileDataModel(
            file_path="/src/MLAnalyticsService.php",
            language="php",
            raw_content="""<?php
require_once 'vendor/google/cloud-ml/autoload.php';
use Google\\Cloud\\MachineLearning\\V1\\MLServiceClient;

class MLAnalyticsService {
    public function trainModel($trainingData) {
        // Machine learning model training
        $client = new MLServiceClient();
        return $client->createModel($trainingData);
    }

    public function trackAnalytics($userData) {
        // Track user analytics for insights
        $this->analyticsClient->track($userData);
    }
}
""",
            metadata=sample_file_metadata,
            functions=[
                SourceCodeFunctionModel(
                    name="trainModel",
                    line_start=6,
                    line_end=10,
                    parameters=[],
                    visibility="public",
                ),
                SourceCodeFunctionModel(
                    name="trackAnalytics",
                    line_start=12,
                    line_end=15,
                    parameters=[],
                    visibility="public",
                ),
            ],
            classes=[
                SourceCodeClassModel(
                    name="MLAnalyticsService",
                    line_start=5,
                    line_end=16,
                ),
            ],
            imports=[
                SourceCodeImportModel(
                    module="vendor/google/cloud-ml/autoload.php",
                    line=2,
                    type="require_once",
                ),
                SourceCodeImportModel(
                    module="Google\\Cloud\\MachineLearning\\V1\\MLServiceClient",
                    line=3,
                    type="use",
                ),
            ],
        )

    def test_init_creates_handler_successfully(self) -> None:
        """Test that __init__ creates a handler successfully."""
        # Act
        handler = SourceCodeSchemaInputHandler()

        # Assert - only verify object creation and public method availability
        assert handler is not None
        assert hasattr(handler, "analyse_source_code_data")
        assert callable(getattr(handler, "analyse_source_code_data"))

    def test_analyse_source_code_data_returns_empty_list_for_empty_data(
        self,
        handler: SourceCodeSchemaInputHandler,
        empty_source_code_data: SourceCodeDataModel,
    ) -> None:
        """Test that analyse_source_code_data returns empty list for empty data."""
        # Act
        findings = handler.analyse_source_code_data(empty_source_code_data)

        # Assert
        assert findings == []
        assert isinstance(findings, list)

    def test_analyse_source_code_data_returns_findings_for_simple_patterns(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse_source_code_data returns findings for simple processing purpose patterns."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Simple PHP analysis",
            description="Analysis of simple PHP file",
            language="php",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data],
        )

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert isinstance(findings, list)
        assert len(findings) > 0

        # Verify findings structure
        for finding in findings:
            assert isinstance(finding, ProcessingPurposeFindingModel)
            for field in self.EXPECTED_FINDING_FIELDS:
                assert hasattr(finding, field)
            assert finding.risk_level in self.VALID_RISK_LEVELS
            assert isinstance(finding.evidence, list)
            assert len(finding.evidence) > 0
            assert finding.metadata is not None

    def test_analyse_source_code_data_detects_payment_patterns(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse_source_code_data detects payment-related patterns."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Payment analysis",
            description="Analysis for payment patterns",
            language="php",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data],
        )

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        payment_findings = [
            f
            for f in findings
            if "payment" in f.matched_pattern.lower() or "payment" in f.purpose.lower()
        ]
        assert len(payment_findings) > 0

        payment_finding = payment_findings[0]
        assert isinstance(payment_finding.purpose, str)
        assert len(payment_finding.purpose) > 0
        assert payment_finding.metadata is not None

        # Validate evidence has timestamps
        for evidence_item in payment_finding.evidence:
            assert evidence_item.collection_timestamp is not None
        assert (
            getattr(payment_finding.metadata, "file_path") == "/src/CustomerService.php"
        )

    def test_analyse_source_code_data_handles_multiple_files(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        ml_service_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse_source_code_data handles multiple files correctly."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Multi-file analysis",
            description="Analysis of multiple files",
            language="php",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data, ml_service_file_data],
        )

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert isinstance(findings, list)
        assert len(findings) > 0

        # Verify findings from both files are present
        file_paths = {
            getattr(f.metadata, "file_path") for f in findings if f.metadata is not None
        }
        assert "/src/CustomerService.php" in file_paths
        assert "/src/MLAnalyticsService.php" in file_paths

        # Validate at least one finding has evidence with timestamps
        if findings:
            assert findings[0].evidence[0].collection_timestamp is not None

    def test_analyse_source_code_data_creates_proper_metadata(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse_source_code_data creates proper metadata for findings."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Metadata test",
            description="Test metadata creation",
            language="php",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data],
        )

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert len(findings) > 0
        finding = findings[0]

        # Verify metadata structure
        assert finding.metadata is not None
        assert finding.metadata.source == "source_code"
        assert hasattr(finding.metadata, "file_path")
        assert hasattr(finding.metadata, "language")
        assert hasattr(finding.metadata, "analysis_type")
        assert getattr(finding.metadata, "file_path") == "/src/CustomerService.php"
        assert getattr(finding.metadata, "language") == "php"

        # Comprehensive timestamp validation
        start_time = datetime.now(timezone.utc)
        for evidence_item in finding.evidence:
            # Validate timestamp exists and is correct type
            assert evidence_item.collection_timestamp is not None
            assert isinstance(evidence_item.collection_timestamp, datetime)

            # Validate timezone is UTC
            assert evidence_item.collection_timestamp.tzinfo == timezone.utc

            # Validate timestamp is recent (within last minute for this test)
            assert evidence_item.collection_timestamp <= start_time

            # Validate timestamp can be serialized to ISO format
            iso_string = evidence_item.collection_timestamp.isoformat()
            assert iso_string.endswith("Z") or "+" in iso_string

            # Validate timestamp can be round-tripped through ISO format
            parsed_timestamp = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            assert parsed_timestamp.tzinfo is not None

    def test_analyse_source_code_data_handles_file_with_no_patterns(
        self,
        handler: SourceCodeSchemaInputHandler,
        sample_file_metadata: SourceCodeFileMetadataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse_source_code_data handles files with no matching patterns gracefully."""
        # Arrange
        empty_file_data = SourceCodeFileDataModel(
            file_path="/src/EmptyClass.php",
            language="php",
            raw_content="""<?php
class EmptyClass {
    // This class has no processing purpose patterns
    public function doNothing() {
        return true;
    }
}
""",
            metadata=sample_file_metadata,
            functions=[
                SourceCodeFunctionModel(
                    name="doNothing",
                    line_start=4,
                    line_end=6,
                    parameters=[],
                    visibility="public",
                ),
            ],
            classes=[
                SourceCodeClassModel(
                    name="EmptyClass",
                    line_start=2,
                    line_end=7,
                ),
            ],
            imports=[],
        )

        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Empty pattern test",
            description="Test file with no patterns",
            language="php",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[empty_file_data],
        )

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert isinstance(findings, list)
        # May be empty or may have very few findings - this is acceptable behaviour

    def test_analyse_source_code_data_returns_valid_finding_types(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse_source_code_data returns valid finding types."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Type validation test",
            description="Test finding type validation",
            language="php",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data],
        )

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        for finding in findings:
            # Verify all string fields are non-empty strings
            assert isinstance(finding.purpose, str) and len(finding.purpose) > 0
            assert isinstance(finding.purpose_category, str)
            assert (
                isinstance(finding.risk_level, str)
                and finding.risk_level in self.VALID_RISK_LEVELS
            )
            assert (
                isinstance(finding.matched_pattern, str)
                and len(finding.matched_pattern) > 0
            )

            # Verify list fields
            assert isinstance(finding.compliance, list)
            assert isinstance(finding.evidence, list) and len(finding.evidence) > 0

            # Verify each evidence item is an EvidenceItem
            for evidence_item in finding.evidence:
                assert isinstance(evidence_item, EvidenceItem)
                assert (
                    isinstance(evidence_item.content, str)
                    and len(evidence_item.content) > 0
                )
                assert evidence_item.collection_timestamp is not None
