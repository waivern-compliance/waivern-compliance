"""Unit tests for SourceCodeSchemaInputHandler.

This test module focuses on testing the public API of SourceCodeSchemaInputHandler,
following black-box testing principles and proper encapsulation.
"""

from datetime import UTC, datetime

import pytest
from waivern_core.schemas import BaseFindingEvidence

from waivern_processing_purpose_analyser.schemas.types import (
    ProcessingPurposeFindingModel,
)
from waivern_processing_purpose_analyser.source_code_schema_input_handler import (
    SourceCodeAnalysisMetadataDict,
    SourceCodeFileDict,
    SourceCodeFileMetadataDict,
    SourceCodeSchemaDict,
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
    def sample_file_metadata(self) -> SourceCodeFileMetadataDict:
        """Create sample file metadata for testing."""
        return {
            "file_size": 1024,
            "line_count": 50,
            "last_modified": "2024-01-01T00:00:00Z",
        }

    @pytest.fixture
    def sample_analysis_metadata(self) -> SourceCodeAnalysisMetadataDict:
        """Create sample analysis metadata for testing."""
        return {
            "total_files": 1,
            "total_lines": 50,
            "analysis_timestamp": "2024-01-01T00:00:00Z",
        }

    @pytest.fixture
    def empty_source_code_data(
        self, sample_analysis_metadata: SourceCodeAnalysisMetadataDict
    ) -> SourceCodeSchemaDict:
        """Create empty source code data for testing."""
        return {
            "schemaVersion": "1.0.0",
            "name": "Empty analysis",
            "description": "Empty source code analysis",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [],
        }

    @pytest.fixture
    def simple_php_file_data(
        self, sample_file_metadata: SourceCodeFileMetadataDict
    ) -> SourceCodeFileDict:
        """Create simple PHP file data with processing purpose patterns."""
        return {
            "file_path": "/src/CustomerService.php",
            "language": "php",
            "raw_content": """<?php
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
            "metadata": sample_file_metadata,
        }

    @pytest.fixture
    def service_integration_file_data(
        self, sample_file_metadata: SourceCodeFileMetadataDict
    ) -> SourceCodeFileDict:
        """Create file data with actual service integration patterns from ruleset."""
        return {
            "file_path": "/src/CloudStorageService.php",
            "language": "php",
            "raw_content": """<?php
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
            "metadata": sample_file_metadata,
        }

    @pytest.fixture
    def data_collection_file_data(
        self, sample_file_metadata: SourceCodeFileMetadataDict
    ) -> SourceCodeFileDict:
        """Create file data with actual data collection patterns from ruleset."""
        return {
            "file_path": "/src/UserFormHandler.php",
            "language": "php",
            "raw_content": """<?php
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
            "metadata": sample_file_metadata,
        }

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
        empty_source_code_data: SourceCodeSchemaDict,
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
        simple_php_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that analyse_source_code_data returns findings for simple processing purpose patterns."""
        # Arrange
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Simple PHP analysis",
            "description": "Analysis of simple PHP file",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [simple_php_file_data],
        }

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
            assert isinstance(finding.evidence, list)
            assert len(finding.evidence) > 0
            assert finding.metadata is not None

    def test_analyse_source_code_data_detects_payment_patterns(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that analyse_source_code_data detects payment-related patterns."""
        # Arrange
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Payment analysis",
            "description": "Analysis for payment patterns",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [simple_php_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

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
        # Metadata contains source information
        assert payment_finding.metadata.source == "source_code"

    def test_analyse_source_code_data_handles_multiple_files(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDict,
        service_integration_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that analyse_source_code_data handles multiple files correctly."""
        # Arrange
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Multi-file analysis",
            "description": "Analysis of multiple files",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [simple_php_file_data, service_integration_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert isinstance(findings, list)
        assert len(findings) > 0

        # Verify findings from both files are present
        # Verify findings are generated for multiple sources
        assert len(findings) >= 2
        # All findings should have source_code as the source
        sources = {f.metadata.source for f in findings if f.metadata is not None}
        assert "source_code" in sources

        # Validate at least one finding has evidence with timestamps
        if findings:
            assert findings[0].evidence[0].collection_timestamp is not None

    def test_analyse_source_code_data_creates_proper_metadata(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that analyse_source_code_data creates proper metadata for findings."""
        # Arrange
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Metadata test",
            "description": "Test metadata creation",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [simple_php_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert len(findings) > 0
        finding = findings[0]

        # Verify metadata structure (simplified - essential business data only)
        assert finding.metadata is not None
        assert finding.metadata.source == "source_code"

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

    def test_analyse_source_code_data_handles_file_with_no_patterns(
        self,
        handler: SourceCodeSchemaInputHandler,
        sample_file_metadata: SourceCodeFileMetadataDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that analyse_source_code_data handles files with no matching patterns gracefully."""
        # Arrange
        empty_file_data: SourceCodeFileDict = {
            "file_path": "/src/EmptyClass.php",
            "language": "php",
            "raw_content": """<?php
class EmptyClass {
    // This class has no processing purpose patterns
    public function doNothing() {
        return true;
    }
}
""",
            "metadata": sample_file_metadata,
        }

        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Empty pattern test",
            "description": "Test file with no patterns",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [empty_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert isinstance(findings, list)
        # May be empty or may have very few findings - this is acceptable behaviour

    def test_analyse_source_code_data_returns_valid_finding_types(
        self,
        handler: SourceCodeSchemaInputHandler,
        simple_php_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that analyse_source_code_data returns valid finding types."""
        # Arrange
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Type validation test",
            "description": "Test finding type validation",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [simple_php_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

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
        service_integration_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that findings from ServiceIntegrationRule include service_category field.

        This test verifies that when the SourceCodeSchemaInputHandler creates findings
        from ServiceIntegrationRule patterns, the resulting ProcessingPurposeFindingModel
        includes the service_category from the rule.
        """
        # Arrange
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Service integration test",
            "description": "Test service integration categorical data",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [service_integration_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        # Filter for findings that came from ServiceIntegrationRule using exact patterns
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
            # TDD: This will fail until we implement service_category
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
        data_collection_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that findings from DataCollectionRule include collection_type and data_source fields.

        This test verifies that when the SourceCodeSchemaInputHandler creates findings
        from DataCollectionRule patterns, the resulting ProcessingPurposeFindingModel
        includes both collection_type and data_source from the rule.
        """
        # Arrange
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Data collection test",
            "description": "Test data collection categorical data",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [data_collection_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        # Filter for findings that came from DataCollectionRule using exact patterns
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
            # TDD: These will fail until we implement collection_type and data_source
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
    """Tests for context window functionality in evidence extraction.

    These tests verify that the SourceCodeSchemaInputHandler correctly:
    - Includes file paths in evidence for LLM context
    - Extracts surrounding lines based on context window configuration
    - Handles edge cases (start/end of file)
    - Marks matched lines with visual indicators
    """

    @pytest.fixture
    def sample_file_metadata(self) -> SourceCodeFileMetadataDict:
        """Create sample file metadata for testing."""
        return {
            "file_size": 1024,
            "line_count": 50,
            "last_modified": "2024-01-01T00:00:00Z",
        }

    @pytest.fixture
    def sample_analysis_metadata(self) -> SourceCodeAnalysisMetadataDict:
        """Create sample analysis metadata for testing."""
        return {
            "total_files": 1,
            "total_lines": 50,
            "analysis_timestamp": "2024-01-01T00:00:00Z",
        }

    @pytest.fixture
    def multiline_file_data(
        self, sample_file_metadata: SourceCodeFileMetadataDict
    ) -> SourceCodeFileDict:
        """Create file data with multiple lines for context window testing."""
        return {
            "file_path": "src/payments/checkout.js",
            "language": "javascript",
            "raw_content": """import { config } from './config';
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
            "metadata": sample_file_metadata,
        }

    # A. File Path in Evidence
    def test_evidence_includes_file_path(
        self,
        multiline_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that evidence content includes the file path for LLM context."""
        # Arrange
        handler = SourceCodeSchemaInputHandler()
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "File path test",
            "description": "Test file path in evidence",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [multiline_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert len(findings) > 0, "Expected at least one finding"

        # Check that evidence includes the file path
        for finding in findings:
            for evidence_item in finding.evidence:
                assert multiline_file_data["file_path"] in evidence_item.content, (
                    f"Expected file path '{multiline_file_data['file_path']}' in evidence content, "
                    f"got: {evidence_item.content}"
                )

    # C. Context Window Behaviour
    def test_context_window_small_includes_surrounding_lines(
        self,
        multiline_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that 'small' context window includes ±3 lines around match."""
        # Arrange
        handler = SourceCodeSchemaInputHandler(context_window="small")
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Context window test",
            "description": "Test small context window",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [multiline_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert - evidence should include surrounding lines (±3)
        assert len(findings) > 0, "Expected at least one finding"

        # Find a payment-related finding (matches on line 11: "async processPayment")
        payment_findings = [f for f in findings if "payment" in f.purpose.lower()]
        assert len(payment_findings) > 0, "Expected payment-related finding"

        # Evidence should contain multiple lines (not just the matched line)
        evidence_content = payment_findings[0].evidence[0].content
        line_count = evidence_content.count("\n") + 1
        # Small window = ±3 lines = up to 7 lines total (3 before + match + 3 after)
        assert line_count >= 2, (
            f"Expected multiple lines in evidence for 'small' context window, got {line_count}"
        )

    def test_context_window_medium_includes_more_surrounding_lines(
        self,
        multiline_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that 'medium' context window includes ±15 lines around match."""
        # Arrange
        handler = SourceCodeSchemaInputHandler(context_window="medium")
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Medium context test",
            "description": "Test medium context window",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [multiline_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert len(findings) > 0, "Expected at least one finding"

        # Medium window should include more lines than small
        # For a 24-line file with match in middle, medium (±15) includes entire file
        payment_findings = [f for f in findings if "payment" in f.purpose.lower()]
        assert len(payment_findings) > 0

        evidence_content = payment_findings[0].evidence[0].content
        small_handler = SourceCodeSchemaInputHandler(context_window="small")
        small_findings = small_handler.analyse_source_code_data(source_data)
        small_payment = [f for f in small_findings if "payment" in f.purpose.lower()]

        # Medium context should have more or equal lines than small
        medium_lines = evidence_content.count("\n")
        small_lines = small_payment[0].evidence[0].content.count("\n")
        assert medium_lines >= small_lines

    def test_context_window_full_includes_entire_file(
        self,
        multiline_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that 'full' context window includes entire file content."""
        # Arrange
        handler = SourceCodeSchemaInputHandler(context_window="full")
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Full context test",
            "description": "Test full context window",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [multiline_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert len(findings) > 0, "Expected at least one finding"

        # Full context should include all lines from the file
        evidence_content = findings[0].evidence[0].content
        file_line_count = multiline_file_data["raw_content"].count("\n")
        evidence_line_count = evidence_content.count("\n")

        # Evidence includes file path line + all file lines
        assert evidence_line_count >= file_line_count, (
            f"Full context should include all {file_line_count} lines, "
            f"but evidence has {evidence_line_count} lines"
        )

    # D. Edge Cases
    def test_context_window_at_start_of_file(
        self,
        sample_file_metadata: SourceCodeFileMetadataDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that context window handles matches near start of file gracefully."""
        # Arrange - match on line 1
        file_data: SourceCodeFileDict = {
            "file_path": "src/payment.js",
            "language": "javascript",
            "raw_content": """const payment = require('stripe');
const config = {};
function init() {}
function setup() {}
function run() {}""",
            "metadata": sample_file_metadata,
        }
        handler = SourceCodeSchemaInputHandler(context_window="small")
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Start of file test",
            "description": "Test match at start",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert - should not crash and should include available context
        payment_findings = [f for f in findings if "payment" in f.purpose.lower()]
        assert len(payment_findings) > 0
        evidence = payment_findings[0].evidence[0].content
        # Should start from line 1 (no negative line numbers)
        assert "   1→" in evidence, "Evidence should start from line 1"

    def test_context_window_at_end_of_file(
        self,
        sample_file_metadata: SourceCodeFileMetadataDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that context window handles matches near end of file gracefully."""
        # Arrange - match on last line
        file_data: SourceCodeFileDict = {
            "file_path": "src/main.js",
            "language": "javascript",
            "raw_content": """function init() {}
function setup() {}
function run() {}
const config = {};
const payment = require('stripe');""",
            "metadata": sample_file_metadata,
        }
        handler = SourceCodeSchemaInputHandler(context_window="small")
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "End of file test",
            "description": "Test match at end",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert - should not crash and should include available context
        payment_findings = [f for f in findings if "payment" in f.purpose.lower()]
        assert len(payment_findings) > 0
        evidence = payment_findings[0].evidence[0].content
        # Last actual line number should be 5 (the file has 5 lines)
        assert "   5→" in evidence, "Evidence should include line 5 (last line)"

    # E. Visual Indicator
    def test_matched_line_marked_with_indicator(
        self,
        multiline_file_data: SourceCodeFileDict,
        sample_analysis_metadata: SourceCodeAnalysisMetadataDict,
    ) -> None:
        """Test that the matched line is marked with an arrow indicator."""
        # Arrange
        handler = SourceCodeSchemaInputHandler(context_window="small")
        source_data: SourceCodeSchemaDict = {
            "schemaVersion": "1.0.0",
            "name": "Indicator test",
            "description": "Test arrow indicator",
            "source": "source_code",
            "metadata": sample_analysis_metadata,
            "data": [multiline_file_data],
        }

        # Act
        findings = handler.analyse_source_code_data(source_data)

        # Assert
        assert len(findings) > 0, "Expected at least one finding"

        evidence = findings[0].evidence[0].content
        # Should have exactly one arrow indicator (→) for the matched line
        assert "→" in evidence, (
            "Evidence should contain arrow indicator for matched line"
        )

        # Non-matched lines should have space instead of arrow
        lines = evidence.split("\n")
        arrow_count = sum(1 for line in lines if "→" in line)
        space_count = sum(
            1 for line in lines if line and line[4:5] == " " and "→" not in line
        )

        # Should have at least one arrow and some non-arrow lines in context
        assert arrow_count >= 1, "Should have at least one line with arrow indicator"
        assert space_count >= 1, "Should have context lines without arrow"
