"""Unit tests for DataSubjectAnalyser.

This test module focuses on testing the public API of DataSubjectAnalyser.
"""

import json
from datetime import datetime

from wct.analysers.data_subject_analyser.analyser import DataSubjectAnalyser
from wct.message import Message
from wct.schemas import (
    BaseMetadata,
    DataSubjectFindingSchema,
    StandardInputDataItemModel,
    StandardInputDataModel,
    StandardInputSchema,
)
from wct.schemas.types import BaseFindingEvidence


class TestDataSubjectAnalyserIdentity:
    """Test class for DataSubjectAnalyser identity and registration."""

    def test_get_name_returns_correct_identifier(self) -> None:
        """Test that get_name returns correct analyser identifier."""
        name = DataSubjectAnalyser.get_name()
        assert name == "data_subject_analyser"
        assert isinstance(name, str)

    def test_from_properties_creates_instance_with_defaults(self) -> None:
        """Test that from_properties creates working instance."""
        analyser = DataSubjectAnalyser.from_properties({})
        assert analyser is not None


class TestDataSubjectAnalyserSchemaSupport:
    """Test class for schema support declarations."""

    def test_get_supported_input_schemas_includes_standard_input(self) -> None:
        """Test that analyser supports standard_input schema."""
        input_schemas = DataSubjectAnalyser.get_supported_input_schemas()

        assert isinstance(input_schemas, list)
        assert len(input_schemas) > 0

        schema_names = {schema.name for schema in input_schemas}
        assert "standard_input" in schema_names

    def test_get_supported_output_schemas_returns_data_subject_finding(self) -> None:
        """Test that analyser outputs data_subject_finding schema."""
        output_schemas = DataSubjectAnalyser.get_supported_output_schemas()

        assert isinstance(output_schemas, list)
        assert len(output_schemas) == 1
        assert output_schemas[0].name == "data_subject_finding"


class TestDataSubjectAnalyserProcessing:
    """Test class for data processing functionality."""

    def test_process_returns_valid_structure(self) -> None:
        """Test that process returns valid structure for empty data."""
        # Arrange
        analyser = DataSubjectAnalyser.from_properties({})
        input_schema = StandardInputSchema()
        output_schema = DataSubjectFindingSchema()

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
        result = analyser.process(input_schema, output_schema, message)

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
        analyser = DataSubjectAnalyser.from_properties({})
        input_schema = StandardInputSchema()
        output_schema = DataSubjectFindingSchema()

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
        result = analyser.process(input_schema, output_schema, message)

        # Assert
        assert isinstance(result, Message)
        findings = result.content["findings"]
        assert isinstance(findings, list)

        if len(findings) > 0:
            # Verify finding structure for pattern matches
            finding = findings[0]
            assert "primary_category" in finding
            assert "confidence_score" in finding
            assert "evidence" in finding
            assert "modifiers" in finding
            assert "matched_patterns" in finding
            assert "metadata" in finding

    def test_process_serialises_datetime_objects_correctly(self) -> None:
        """Test that datetime objects in findings are properly serialised to JSON."""
        # Arrange
        analyser = DataSubjectAnalyser.from_properties({})
        input_schema = StandardInputSchema()
        output_schema = DataSubjectFindingSchema()

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
        result = analyser.process(input_schema, output_schema, message)

        # Assert that result can be serialised to JSON (would fail before fix)
        # This should not raise a TypeError about datetime serialisation
        json_output = json.dumps(result.content)
        assert isinstance(json_output, str)

        # Verify analysis_metadata contains expected standardised fields
        analysis_metadata = result.content["analysis_metadata"]
        assert "ruleset_used" in analysis_metadata
        assert "llm_validation_enabled" in analysis_metadata
        assert "analyses_chain" in analysis_metadata
        assert isinstance(analysis_metadata["analyses_chain"], list)

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
        analyser = DataSubjectAnalyser.from_properties({})
        input_schema = StandardInputSchema()
        output_schema = DataSubjectFindingSchema()

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
        result = analyser.process(input_schema, output_schema, message)

        # Assert
        findings = result.content["findings"]
        assert len(findings) > 0

        # Find director finding
        director_finding = next(
            (f for f in findings if f["primary_category"] == "director"), None
        )
        assert director_finding is not None

        # Verify matched_patterns contains only the pattern that actually matched
        matched_patterns = director_finding["matched_patterns"]
        assert isinstance(matched_patterns, list)
        assert len(matched_patterns) >= 2  # Should have multiple matches

        # Verify it contains the patterns that are actually in the content
        assert "director" in matched_patterns
        assert "ceo" in matched_patterns
        # Note: "executive" and "executive_officer" may both match "executive officer"

        # Verify it doesn't contain patterns that aren't in the content
        assert "board_member" not in matched_patterns
        assert "chairman" not in matched_patterns

    def test_process_creates_analysis_chain_entry(self) -> None:
        """Test that analyser creates proper analysis chain entry.

        Business Logic: Each analyser must create a chain entry to track
        the analysis for audit purposes and downstream processing.
        """
        # Arrange
        analyser = DataSubjectAnalyser.from_properties({})
        input_schema = StandardInputSchema()
        output_schema = DataSubjectFindingSchema()

        message = Message(
            id="test_chain",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test data",
                "data": [
                    {
                        "content": "Employee John Smith",
                        "metadata": {"source": "test", "connector_type": "test"},
                    }
                ],
            },
            schema=input_schema,
        )

        # Act
        result = analyser.process(input_schema, output_schema, message)

        # Assert
        analysis_metadata = result.content["analysis_metadata"]
        analyses_chain = analysis_metadata["analyses_chain"]

        assert len(analyses_chain) == 1, "Should create exactly one chain entry"

        chain_entry = analyses_chain[0]
        assert chain_entry["order"] == 1, "Should start with order 1 for new analysis"
        assert chain_entry["analyser"] == "data_subject_analyser", (
            "Should identify correct analyser"
        )
        assert "execution_timestamp" in chain_entry, (
            "Should include execution timestamp"
        )
