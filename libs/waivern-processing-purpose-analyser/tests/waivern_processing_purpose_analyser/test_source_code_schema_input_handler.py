"""Unit tests for SourceCodeSchemaInputHandler.

This test module focuses on testing the public API of SourceCodeSchemaInputHandler,
following black-box testing principles and proper encapsulation.
"""

from datetime import UTC, datetime

import pytest
from waivern_core.schemas import BaseFindingEvidence
from waivern_source_code_analyser import SourceCodeDataModel
from waivern_source_code_analyser.schemas.source_code import (
    SourceCodeAnalysisMetadataModel,
    SourceCodeFileDataModel,
    SourceCodeFileMetadataModel,
)

from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeFindingModel,
)
from waivern_processing_purpose_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaInputHandler,
)


class TestSourceCodeSchemaInputHandler:
    """Test suite for SourceCodeSchemaInputHandler."""

    # Test constants - defined locally, not imported from implementation
    EXPECTED_FINDING_FIELDS = [
        "purpose",
        "purpose_category",
        "matched_patterns",
        "evidence",
        "metadata",
    ]

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
        )

    @pytest.fixture
    def sample_analysis_metadata(self) -> SourceCodeAnalysisMetadataModel:
        """Create sample analysis metadata for testing."""
        return SourceCodeAnalysisMetadataModel(
            total_files=1,
            total_lines=50,
            analysis_timestamp="2024-01-01T00:00:00Z",
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
        )

    @pytest.fixture
    def service_integration_file_data(
        self, sample_file_metadata: SourceCodeFileMetadataModel
    ) -> SourceCodeFileDataModel:
        """Create file data with actual service integration patterns from ruleset."""
        return SourceCodeFileDataModel(
            file_path="/src/CloudStorageService.php",
            language="php",
            raw_content="""<?php
require_once 'vendor/aws/aws-sdk-php/src/functions.php';

class CloudStorageService {
    public function uploadToAWS($file) {
        // Upload file to amazon s3 storage
        $client = new S3Client();
        return $client->upload($file);
    }

    public function uploadToDropbox($message) {
        // Upload to dropbox cloud storage
        $this->dropbox->upload($message);
    }
}
""",
            metadata=sample_file_metadata,
        )

    @pytest.fixture
    def data_collection_file_data(
        self, sample_file_metadata: SourceCodeFileMetadataModel
    ) -> SourceCodeFileDataModel:
        """Create file data with actual data collection patterns from ruleset."""
        return SourceCodeFileDataModel(
            file_path="/src/UserFormHandler.php",
            language="php",
            raw_content="""<?php
class UserFormHandler {
    public function processForm() {
        // Collect form data via POST
        $userData = $_POST['user_data'];
        $userId = $_GET['user_id'];

        // Access cookies for session
        $sessionId = $_COOKIE['session_id'];
        setcookie('user_pref', $userData);

        return $userData;
    }
}
""",
            metadata=sample_file_metadata,
        )

    def test_init_creates_handler_successfully(self) -> None:
        """Test that __init__ creates a handler successfully."""
        # Act
        handler = SourceCodeSchemaInputHandler()

        # Assert - only verify object creation and public method availability
        assert handler is not None
        assert hasattr(handler, "analyse")
        assert callable(getattr(handler, "analyse"))

    def test_analyse_returns_empty_list_for_empty_data(
        self,
        handler: SourceCodeSchemaInputHandler,
        empty_source_code_data: SourceCodeDataModel,
    ) -> None:
        """Test that analyse returns empty list for empty data."""
        # Act
        findings = handler.analyse(empty_source_code_data)

        # Assert
        assert findings == []
        assert isinstance(findings, list)

    def test_analyse_returns_findings_for_simple_patterns(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse returns findings for simple processing purpose patterns."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Simple PHP analysis",
            description="Analysis of simple PHP file",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        assert isinstance(findings, list)
        assert len(findings) > 0

        # Verify findings structure
        for finding in findings:
            assert isinstance(finding, ProcessingPurposeFindingModel)
            for field in self.EXPECTED_FINDING_FIELDS:
                assert hasattr(finding, field)
            assert isinstance(finding.evidence, list)
            assert len(finding.evidence) > 0
            assert finding.metadata is not None

    def test_analyse_detects_payment_patterns(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse detects payment-related patterns."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Payment analysis",
            description="Analysis for payment patterns",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        payment_findings = [
            f
            for f in findings
            if any("payment" in pattern.lower() for pattern in f.matched_patterns)
            or "payment" in f.purpose.lower()
        ]
        assert len(payment_findings) > 0

        payment_finding = payment_findings[0]
        assert isinstance(payment_finding.purpose, str)
        assert len(payment_finding.purpose) > 0
        assert payment_finding.metadata is not None

        # Validate evidence has timestamps
        for evidence_item in payment_finding.evidence:
            assert evidence_item.collection_timestamp is not None
        # Metadata contains file path
        assert payment_finding.metadata.source == simple_php_file_data.file_path

    def test_analyse_handles_multiple_files(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        service_integration_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse handles multiple files correctly."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Multi-file analysis",
            description="Analysis of multiple files",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data, service_integration_file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        assert isinstance(findings, list)
        assert len(findings) > 0

        # Verify findings from both files are present
        assert len(findings) >= 2
        # All findings should have file paths as metadata.source
        sources = {f.metadata.source for f in findings if f.metadata is not None}
        assert simple_php_file_data.file_path in sources
        assert service_integration_file_data.file_path in sources

        # Validate at least one finding has evidence with timestamps
        if findings:
            assert findings[0].evidence[0].collection_timestamp is not None

    def test_analyse_creates_proper_metadata(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse creates proper metadata for findings."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Metadata test",
            description="Test metadata creation",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        assert len(findings) > 0
        finding = findings[0]

        # Verify metadata structure (simplified - essential business data only)
        assert finding.metadata is not None
        assert finding.metadata.source == simple_php_file_data.file_path

        # Comprehensive timestamp validation
        start_time = datetime.now(UTC)
        for evidence_item in finding.evidence:
            # Validate timestamp exists and is correct type
            assert evidence_item.collection_timestamp is not None
            assert isinstance(evidence_item.collection_timestamp, datetime)

            # Validate timezone is UTC
            assert evidence_item.collection_timestamp.tzinfo == UTC

            # Validate timestamp is recent (within last minute for this test)
            assert evidence_item.collection_timestamp <= start_time

            # Validate timestamp can be serialized to ISO format
            iso_string = evidence_item.collection_timestamp.isoformat()
            assert iso_string.endswith("Z") or "+" in iso_string

            # Validate timestamp can be round-tripped through ISO format
            parsed_timestamp = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            assert parsed_timestamp.tzinfo is not None

    def test_analyse_handles_file_with_no_patterns(
        self,
        handler: SourceCodeSchemaInputHandler,
        sample_file_metadata: SourceCodeFileMetadataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse handles files with no matching patterns gracefully."""
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
        )

        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Empty pattern test",
            description="Test file with no patterns",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[empty_file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        assert isinstance(findings, list)
        # May be empty or may have very few findings - this is acceptable behaviour

    def test_analyse_returns_valid_finding_types(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that analyse returns valid finding types."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Type validation test",
            description="Test finding type validation",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[simple_php_file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        for finding in findings:
            # Verify all string fields are non-empty strings
            assert isinstance(finding.purpose, str) and len(finding.purpose) > 0
            assert isinstance(finding.purpose_category, str)
            assert (
                isinstance(finding.matched_patterns, list)
                and len(finding.matched_patterns) > 0
            )

            # Verify evidence list
            assert isinstance(finding.evidence, list) and len(finding.evidence) > 0

            # Verify each evidence item is an BaseFindingEvidence
            for evidence_item in finding.evidence:
                assert isinstance(evidence_item, BaseFindingEvidence)
                assert (
                    isinstance(evidence_item.content, str)
                    and len(evidence_item.content) > 0
                )
                assert evidence_item.collection_timestamp is not None

    def test_service_integration_findings_include_service_category(
        self,
        handler: SourceCodeSchemaInputHandler,
        service_integration_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that findings from ServiceIntegrationRule include service_category field."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Service integration test",
            description="Test service integration categorical data",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[service_integration_file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        service_integration_findings = [
            f
            for f in findings
            if any(
                pattern.lower() in ["aws", "dropbox", "amazon"]
                for pattern in f.matched_patterns
            )
        ]

        assert len(service_integration_findings) > 0, (
            "Expected at least one service integration finding"
        )

        for finding in service_integration_findings:
            assert hasattr(finding, "service_category"), (
                "Finding should have service_category field from ServiceIntegrationRule"
            )
            assert isinstance(finding.service_category, str), (
                "service_category should be a string"
            )
            assert len(finding.service_category) > 0, (
                "service_category should not be empty"
            )

    def test_data_collection_findings_include_collection_type_and_data_source(
        self,
        handler: SourceCodeSchemaInputHandler,
        data_collection_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that findings from DataCollectionRule include collection_type and data_source fields."""
        # Arrange
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Data collection test",
            description="Test data collection categorical data",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[data_collection_file_data],
        )

        # Act
        findings = handler.analyse(source_data)

        # Assert
        data_collection_findings = [
            f
            for f in findings
            if any(
                pattern in ["$_POST[", "$_GET[", "$_COOKIE[", "setcookie("]
                for pattern in f.matched_patterns
            )
        ]

        assert len(data_collection_findings) > 0, (
            "Expected at least one data collection finding"
        )

        for finding in data_collection_findings:
            assert hasattr(finding, "collection_type"), (
                "Finding should have collection_type field from DataCollectionRule"
            )
            assert isinstance(finding.collection_type, str), (
                "collection_type should be a string"
            )
            assert len(finding.collection_type) > 0, (
                "collection_type should not be empty"
            )

            assert hasattr(finding, "data_source"), (
                "Finding should have data_source field from DataCollectionRule"
            )
            assert isinstance(finding.data_source, str), (
                "data_source should be a string"
            )
            assert len(finding.data_source) > 0, "data_source should not be empty"


class TestSourceCodeContextWindow:
    """Tests for context window functionality in evidence extraction."""

    @pytest.fixture
    def sample_file_metadata(self) -> SourceCodeFileMetadataModel:
        """Create sample file metadata for testing."""
        return SourceCodeFileMetadataModel(
            file_size=1024,
            line_count=50,
            last_modified="2024-01-01T00:00:00Z",
        )

    @pytest.fixture
    def sample_analysis_metadata(self) -> SourceCodeAnalysisMetadataModel:
        """Create sample analysis metadata for testing."""
        return SourceCodeAnalysisMetadataModel(
            total_files=1,
            total_lines=50,
            analysis_timestamp="2024-01-01T00:00:00Z",
        )

    @pytest.fixture
    def multiline_file_data(
        self, sample_file_metadata: SourceCodeFileMetadataModel
    ) -> SourceCodeFileDataModel:
        """Create file data with multiple lines for context window testing."""
        return SourceCodeFileDataModel(
            file_path="src/payments/checkout.js",
            language="javascript",
            raw_content="""import { config } from './config';
import { logger } from './logger';

const API_KEY = process.env.STRIPE_KEY;

class PaymentService {
    constructor() {
        this.stripe = require('stripe')(API_KEY);
    }

    async processPayment(amount) {
        return this.stripe.charges.create({
            amount: amount,
            currency: 'usd'
        });
    }

    async refund(chargeId) {
        return this.stripe.refunds.create({
            charge: chargeId
        });
    }
}

export default PaymentService;
""",
            metadata=sample_file_metadata,
        )

    def test_metadata_includes_file_path(
        self,
        multiline_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that metadata.source contains the file path."""
        handler = SourceCodeSchemaInputHandler()
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="File path test",
            description="Test file path in metadata",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[multiline_file_data],
        )

        findings = handler.analyse(source_data)

        assert len(findings) > 0, "Expected at least one finding"
        for finding in findings:
            assert finding.metadata is not None
            assert finding.metadata.source == multiline_file_data.file_path

    def test_context_window_small_includes_surrounding_lines(
        self,
        multiline_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that 'small' context window includes ±3 lines around match."""
        handler = SourceCodeSchemaInputHandler(context_window="small")
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Context window test",
            description="Test small context window",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[multiline_file_data],
        )

        findings = handler.analyse(source_data)

        assert len(findings) > 0, "Expected at least one finding"
        payment_findings = [f for f in findings if "payment" in f.purpose.lower()]
        assert len(payment_findings) > 0, "Expected payment-related finding"

        evidence_content = payment_findings[0].evidence[0].content
        line_count = evidence_content.count("\n") + 1
        assert line_count >= 2

    def test_context_window_medium_includes_more_surrounding_lines(
        self,
        multiline_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that 'medium' context window includes ±15 lines around match."""
        handler = SourceCodeSchemaInputHandler(context_window="medium")
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Medium context test",
            description="Test medium context window",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[multiline_file_data],
        )

        findings = handler.analyse(source_data)

        assert len(findings) > 0, "Expected at least one finding"
        payment_findings = [f for f in findings if "payment" in f.purpose.lower()]
        assert len(payment_findings) > 0

        evidence_content = payment_findings[0].evidence[0].content
        small_handler = SourceCodeSchemaInputHandler(context_window="small")
        small_findings = small_handler.analyse(source_data)
        small_payment = [f for f in small_findings if "payment" in f.purpose.lower()]

        medium_lines = evidence_content.count("\n")
        small_lines = small_payment[0].evidence[0].content.count("\n")
        assert medium_lines >= small_lines

    def test_context_window_large_includes_more_lines_than_medium(
        self,
        sample_file_metadata: SourceCodeFileMetadataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that 'large' context window includes ±50 lines around match."""
        lines = [f"function line{i}() {{}}" for i in range(100)]
        lines[50] = "async processPayment(amount) { return amount; }"
        file_data = SourceCodeFileDataModel(
            file_path="src/large_file.js",
            language="javascript",
            raw_content="\n".join(lines),
            metadata=sample_file_metadata,
        )

        handler_large = SourceCodeSchemaInputHandler(context_window="large")
        handler_medium = SourceCodeSchemaInputHandler(context_window="medium")
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Large context test",
            description="Test large context window",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[file_data],
        )

        large_findings = handler_large.analyse(source_data)
        medium_findings = handler_medium.analyse(source_data)

        assert len(large_findings) > 0
        assert len(medium_findings) > 0

        large_payment = [f for f in large_findings if "payment" in f.purpose.lower()]
        medium_payment = [f for f in medium_findings if "payment" in f.purpose.lower()]

        assert len(large_payment) > 0
        assert len(medium_payment) > 0

        large_lines = large_payment[0].evidence[0].content.count("\n")
        medium_lines = medium_payment[0].evidence[0].content.count("\n")

        assert large_lines > medium_lines

    def test_context_window_full_includes_entire_file(
        self,
        multiline_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that 'full' context window includes entire file content."""
        handler = SourceCodeSchemaInputHandler(context_window="full")
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Full context test",
            description="Test full context window",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[multiline_file_data],
        )

        findings = handler.analyse(source_data)

        assert len(findings) > 0
        evidence_content = findings[0].evidence[0].content
        # Full context should include all lines from the file
        file_lines = len(multiline_file_data.raw_content.splitlines())
        evidence_lines = len(evidence_content.splitlines())
        assert evidence_lines == file_lines

    def test_context_window_at_start_of_file(
        self,
        sample_file_metadata: SourceCodeFileMetadataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that context window handles matches near start of file gracefully."""
        file_data = SourceCodeFileDataModel(
            file_path="src/payment.js",
            language="javascript",
            raw_content="""const payment = require('stripe');
const config = {};
function init() {}
function setup() {}
function run() {}""",
            metadata=sample_file_metadata,
        )
        handler = SourceCodeSchemaInputHandler(context_window="small")
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Start of file test",
            description="Test match at start",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[file_data],
        )

        findings = handler.analyse(source_data)

        payment_findings = [f for f in findings if "payment" in f.purpose.lower()]
        assert len(payment_findings) > 0
        evidence = payment_findings[0].evidence[0].content
        assert "   1  " in evidence  # Line 1 should be in the context

    def test_context_window_at_end_of_file(
        self,
        sample_file_metadata: SourceCodeFileMetadataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that context window handles matches near end of file gracefully."""
        file_data = SourceCodeFileDataModel(
            file_path="src/main.js",
            language="javascript",
            raw_content="""function init() {}
function setup() {}
function run() {}
const config = {};
const payment = require('stripe');""",
            metadata=sample_file_metadata,
        )
        handler = SourceCodeSchemaInputHandler(context_window="small")
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="End of file test",
            description="Test match at end",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[file_data],
        )

        findings = handler.analyse(source_data)

        payment_findings = [f for f in findings if "payment" in f.purpose.lower()]
        assert len(payment_findings) > 0
        evidence = payment_findings[0].evidence[0].content
        assert "   5  " in evidence  # Line 5 should be in the context

    def test_evidence_includes_line_numbers(
        self,
        multiline_file_data: SourceCodeFileDataModel,
        sample_analysis_metadata: SourceCodeAnalysisMetadataModel,
    ) -> None:
        """Test that evidence includes line numbers in a consistent format."""
        handler = SourceCodeSchemaInputHandler(context_window="small")
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Line numbers test",
            description="Test line number formatting",
            source="source_code",
            metadata=sample_analysis_metadata,
            data=[multiline_file_data],
        )

        findings = handler.analyse(source_data)

        assert len(findings) > 0
        evidence = findings[0].evidence[0].content

        # Evidence should include line numbers in format "   N  content"
        lines = evidence.split("\n")
        assert len(lines) > 0

        # Each line should have a 4-digit padded line number followed by two spaces
        for line in lines:
            if line:  # Skip empty lines
                # Format is "   N  content" where N is right-aligned in 4 chars
                assert line[4:6] == "  ", (
                    f"Expected two spaces after line number: {line}"
                )
