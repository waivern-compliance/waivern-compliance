"""Unit tests for DataSubjectAnalyser.

This test module focuses on testing the public API of DataSubjectAnalyser.
"""

import json
from datetime import datetime

from waivern_core import InputRequirement
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseFindingEvidence,
    BaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)

from waivern_data_subject_analyser.analyser import (
    DataSubjectAnalyser,
)
from waivern_data_subject_analyser.types import (
    DataSubjectAnalyserConfig,
)


class TestDataSubjectAnalyserIdentity:
    """Test class for DataSubjectAnalyser identity and registration."""

    def test_get_name_returns_correct_identifier(self) -> None:
        """Test that get_name returns correct analyser identifier."""
        name = DataSubjectAnalyser.get_name()
        assert name == "data_subject_analyser"
        assert isinstance(name, str)

    def test_from_properties_creates_instance_with_defaults(self) -> None:
        """Test that analyser can be created with default configuration."""
        config = DataSubjectAnalyserConfig.from_properties({})
        analyser = DataSubjectAnalyser(config, llm_service=None)
        assert analyser is not None


class TestDataSubjectAnalyserSchemaSupport:
    """Test class for schema support declarations."""

    def test_get_input_requirements_includes_standard_input(self) -> None:
        """Test that analyser supports standard_input schema."""
        input_requirements = DataSubjectAnalyser.get_input_requirements()

        assert isinstance(input_requirements, list)
        assert len(input_requirements) > 0

        # Check that standard_input is in one of the requirement sets
        all_schema_names = {
            req.schema_name for req_set in input_requirements for req in req_set
        }
        assert "standard_input" in all_schema_names

        # Verify it returns InputRequirement objects
        first_req = input_requirements[0][0]
        assert isinstance(first_req, InputRequirement)
        assert first_req.schema_name == "standard_input"
        assert first_req.version == "1.0.0"

    def test_get_input_requirements_includes_source_code(self) -> None:
        """Test that analyser supports source_code schema as an alternative input."""
        input_requirements = DataSubjectAnalyser.get_input_requirements()

        # Check that source_code is in one of the requirement sets
        all_schema_names = {
            req.schema_name for req_set in input_requirements for req in req_set
        }
        assert "source_code" in all_schema_names

        # Verify it's a separate alternative (not combined with standard_input)
        source_code_req_set = next(
            req_set
            for req_set in input_requirements
            if any(req.schema_name == "source_code" for req in req_set)
        )
        assert len(source_code_req_set) == 1
        assert source_code_req_set[0].version == "1.0.0"

    def test_get_supported_output_schemas_returns_data_subject_indicator(self) -> None:
        """Test that analyser outputs data_subject_indicator schema."""
        output_schemas = DataSubjectAnalyser.get_supported_output_schemas()

        assert isinstance(output_schemas, list)
        assert len(output_schemas) == 1
        assert output_schemas[0].name == "data_subject_indicator"


class TestDataSubjectAnalyserProcessing:
    """Test class for data processing functionality."""

    def test_process_returns_valid_structure(self) -> None:
        """Test that process returns valid structure for empty data."""
        # Arrange
        config = DataSubjectAnalyserConfig.from_properties({})
        analyser = DataSubjectAnalyser(config, llm_service=None)
        input_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("data_subject_indicator", "1.0.0")

        empty_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Empty test data",
            description="Test with no data items",
            source="test",
            metadata={},
            data=[],
        )
        message = Message(
            id="test_empty",
            content=empty_data.model_dump(exclude_none=True),
            schema=input_schema,
        )

        # Act
        result = analyser.process([message], output_schema)

        # Assert
        assert isinstance(result, Message)
        assert result.schema == output_schema
        assert isinstance(result.content, dict)

        # Verify required structure
        assert "findings" in result.content
        assert "summary" in result.content
        assert "analysis_metadata" in result.content
        assert isinstance(result.content["findings"], list)
        assert len(result.content["findings"]) == 0

    def test_process_standard_input_with_pattern_matches(self) -> None:
        """Test that process creates findings for pattern matches."""
        # Arrange
        config = DataSubjectAnalyserConfig.from_properties({})
        analyser = DataSubjectAnalyser(config, llm_service=None)
        input_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("data_subject_indicator", "1.0.0")

        # Create test data with employee patterns
        test_metadata = BaseMetadata(source="test_hr_table", connector_type="mysql")
        test_item = StandardInputDataItemModel[BaseMetadata](
            content="employee john doe staff member employee_id 12345",
            metadata=test_metadata,
        )
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Employee test data",
            description="Test data with employee patterns",
            source="test",
            metadata={},
            data=[test_item],
        )
        message = Message(
            id="test_patterns",
            content=test_data.model_dump(exclude_none=True),
            schema=input_schema,
        )

        # Act
        result = analyser.process([message], output_schema)

        # Assert
        assert isinstance(result, Message)
        findings = result.content["findings"]
        assert isinstance(findings, list)

        if len(findings) > 0:
            # Verify indicator structure for pattern matches
            finding = findings[0]
            assert "subject_category" in finding
            assert "confidence_score" in finding
            assert "evidence" in finding
            assert "matched_patterns" in finding
            assert "metadata" in finding

    def test_process_serialises_datetime_objects_correctly(self) -> None:
        """Test that datetime objects in findings are properly serialised to JSON."""
        # Arrange
        config = DataSubjectAnalyserConfig.from_properties({})
        analyser = DataSubjectAnalyser(config, llm_service=None)
        input_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("data_subject_indicator", "1.0.0")

        # Create test data with employee patterns
        test_metadata = BaseMetadata(source="test_hr_table", connector_type="mysql")
        test_item = StandardInputDataItemModel[BaseMetadata](
            content="employee john doe staff member",
            metadata=test_metadata,
        )
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Employee test data",
            description="Test data with employee patterns",
            source="test",
            metadata={},
            data=[test_item],
        )
        message = Message(
            id="test_datetime_serialisation",
            content=test_data.model_dump(exclude_none=True),
            schema=input_schema,
        )

        # Act
        result = analyser.process([message], output_schema)

        # Assert that result can be serialised to JSON (would fail before fix)
        # This should not raise a TypeError about datetime serialisation
        json_output = json.dumps(result.content)
        assert isinstance(json_output, str)

        # Verify analysis_metadata contains expected standardised fields
        analysis_metadata = result.content["analysis_metadata"]
        assert "ruleset_used" in analysis_metadata
        assert "llm_validation_enabled" in analysis_metadata

        # Verify findings contain properly serialised evidence items
        findings = result.content["findings"]
        if findings:
            # Check that evidence items with collection_timestamp are serialised
            for finding in findings:
                if finding["evidence"]:
                    for evidence_item in finding["evidence"]:
                        assert "collection_timestamp" in evidence_item
                        assert isinstance(evidence_item["collection_timestamp"], str)

    def test_evidence_item_datetime_serialisation(self) -> None:
        """Test that BaseFindingEvidence datetime fields are properly serialised to JSON."""
        # Arrange
        evidence_item = BaseFindingEvidence(content="employee record found in database")

        # Act - This should not raise a TypeError about datetime serialisation
        json_output = json.dumps(evidence_item.model_dump(mode="json"))

        # Assert
        assert isinstance(json_output, str)

        # Parse back to verify structure
        parsed_data = json.loads(json_output)
        assert "content" in parsed_data
        assert "collection_timestamp" in parsed_data
        assert isinstance(parsed_data["collection_timestamp"], str)

        # Verify timestamp is in ISO format
        # This should not raise an exception if properly formatted
        datetime.fromisoformat(
            parsed_data["collection_timestamp"].replace("Z", "+00:00")
        )

    def test_matched_patterns_only_includes_actual_matches(self) -> None:
        """Test that matched_patterns only contains patterns that actually matched, not all patterns from matched rules."""
        # Arrange
        config = DataSubjectAnalyserConfig.from_properties({})
        analyser = DataSubjectAnalyser(config, llm_service=None)
        input_schema = Schema("standard_input", "1.0.0")
        output_schema = Schema("data_subject_indicator", "1.0.0")

        # Create test data with multiple director patterns that should all match
        # Test content contains director, ceo, and executive patterns
        test_metadata = BaseMetadata(source="test_company_db", connector_type="mysql")
        test_item = StandardInputDataItemModel[BaseMetadata](
            content="director john smith is also the ceo and executive officer",
            metadata=test_metadata,
        )
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="Director test data",
            description="Test data with multiple director patterns",
            source="test",
            metadata={},
            data=[test_item],
        )
        message = Message(
            id="test_matched_patterns",
            content=test_data.model_dump(exclude_none=True),
            schema=input_schema,
        )

        # Act
        result = analyser.process([message], output_schema)

        # Assert
        findings = result.content["findings"]
        assert len(findings) > 0

        # Find director finding
        director_finding = next(
            (f for f in findings if f["subject_category"] == "director"), None
        )
        assert director_finding is not None

        # Verify matched_patterns contains only the pattern that actually matched
        matched_patterns_raw = director_finding["matched_patterns"]
        assert isinstance(matched_patterns_raw, list)
        assert len(matched_patterns_raw) >= 2  # Should have multiple matches

        # Extract pattern strings from PatternMatchDetail objects
        matched_pattern_names = [p["pattern"] for p in matched_patterns_raw]

        # Verify it contains the patterns that are actually in the content
        assert "director" in matched_pattern_names
        assert "ceo" in matched_pattern_names
        # Note: "executive" and "executive_officer" may both match "executive officer"

        # Verify it doesn't contain patterns that aren't in the content
        assert "board_member" not in matched_pattern_names
        assert "chairman" not in matched_pattern_names

    def test_process_source_code_with_pattern_matches(self) -> None:
        """Test that process handles source_code schema correctly."""
        from waivern_source_code_analyser import SourceCodeDataModel
        from waivern_source_code_analyser.schemas.source_code import (
            SourceCodeAnalysisMetadataModel,
            SourceCodeFileDataModel,
            SourceCodeFileMetadataModel,
        )

        # Arrange
        config = DataSubjectAnalyserConfig.from_properties({})
        analyser = DataSubjectAnalyser(config, llm_service=None)
        input_schema = Schema("source_code", "1.0.0")
        output_schema = Schema("data_subject_indicator", "1.0.0")

        # Create test data with employee patterns in source code
        file_data = SourceCodeFileDataModel(
            file_path="/src/EmployeeService.php",
            language="php",
            raw_content="""<?php
class EmployeeService {
    private $employee;
    private $staff;

    public function getEmployee() {
        return $this->employee;
    }
}
""",
            metadata=SourceCodeFileMetadataModel(
                file_size=200, line_count=10, last_modified="2024-01-01T00:00:00Z"
            ),
        )
        source_data = SourceCodeDataModel(
            schemaVersion="1.0.0",
            name="Employee source code",
            description="Test data with employee patterns",
            source="source_code",
            metadata=SourceCodeAnalysisMetadataModel(
                total_files=1, total_lines=10, analysis_timestamp="2024-01-01T00:00:00Z"
            ),
            data=[file_data],
        )
        message = Message(
            id="test_source_code",
            content=source_data.model_dump(exclude_none=True),
            schema=input_schema,
        )

        # Act
        result = analyser.process([message], output_schema)

        # Assert
        assert isinstance(result, Message)
        assert result.schema == output_schema

        findings = result.content["findings"]
        assert isinstance(findings, list)
        assert len(findings) > 0, "Expected at least one finding for employee patterns"

        # Find employee finding
        employee_finding = next(
            (f for f in findings if f["subject_category"] == "employee"), None
        )
        assert employee_finding is not None

        # Verify metadata includes source file path
        assert employee_finding["metadata"]["source"] == "/src/EmployeeService.php"
        # Verify line number is present for source code findings
        assert employee_finding["metadata"]["line_number"] is not None
        assert employee_finding["metadata"]["line_number"] > 0
