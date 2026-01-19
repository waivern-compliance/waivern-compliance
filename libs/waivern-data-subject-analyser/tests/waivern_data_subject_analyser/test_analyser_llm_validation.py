"""Tests for DataSubjectAnalyser LLM validation behaviour.

These tests verify the expected behaviour of LLM validation integration
in the analyser's public API using mocked LLM service.
"""

import re
from unittest.mock import Mock

import pytest
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_core.message import Message
from waivern_core.schemas import (
    BaseMetadata,
    Schema,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_llm import BaseLLMService

from waivern_data_subject_analyser.analyser import DataSubjectAnalyser
from waivern_data_subject_analyser.types import DataSubjectAnalyserConfig


def _extract_finding_ids_from_prompt(prompt: str) -> list[str]:
    """Extract finding IDs from the validation prompt."""
    pattern = r"Finding \[([a-f0-9-]+)\]:"
    return re.findall(pattern, prompt)


class TestDataSubjectAnalyserLLMValidationBehaviour:
    """Test LLM validation behaviour in the analyser process method."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service."""
        return Mock(spec=BaseLLMService)

    @pytest.fixture
    def mock_llm_service_unavailable(self) -> None:
        """Create unavailable LLM service (None)."""
        return None

    @pytest.fixture
    def test_message_with_patterns(self) -> Message:
        """Create test message with content that matches data subject patterns."""
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="test_data",
            description="Test data for LLM validation",
            source="test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="customer_id field in database table",
                    metadata=BaseMetadata(
                        source="mysql_database", connector_type="mysql"
                    ),
                ),
                StandardInputDataItemModel(
                    content="employee records with employee_id",
                    metadata=BaseMetadata(source="hr_database", connector_type="mysql"),
                ),
            ],
        )
        return Message(
            id="test",
            content=test_data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

    # -------------------------------------------------------------------------
    # LLM Service Interaction
    # -------------------------------------------------------------------------

    def test_llm_validation_enabled_calls_llm_service_when_findings_exist(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM validation calls LLM service when findings exist."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            finding_ids = _extract_finding_ids_from_prompt(prompt)
            return LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=fid,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Valid data subject indicator",
                        recommended_action="keep",
                    )
                    for fid in finding_ids
                ]
            )

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response

        config = DataSubjectAnalyserConfig.from_properties(properties)
        analyser = DataSubjectAnalyser(config, mock_llm_service)

        # Act
        analyser.process(
            [test_message_with_patterns],
            Schema("data_subject_indicator", "1.0.0"),
        )

        # Assert
        mock_llm_service.invoke_with_structured_output.assert_called_once()
        call_args = mock_llm_service.invoke_with_structured_output.call_args
        # Check prompt contains key validation elements
        prompt = call_args[0][0]
        assert "TASK:" in prompt or "Validate" in prompt

    def test_llm_validation_disabled_skips_validation(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that disabled LLM validation skips the validation step."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": False}}

        config = DataSubjectAnalyserConfig.from_properties(properties)
        analyser = DataSubjectAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("data_subject_indicator", "1.0.0"),
        )

        # Assert
        mock_llm_service.invoke_with_structured_output.assert_not_called()
        assert "validation_summary" not in result.content.get("analysis_metadata", {})

    # -------------------------------------------------------------------------
    # Finding Filtering
    # -------------------------------------------------------------------------

    def test_llm_validation_filters_out_false_positives(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM validation filters out findings marked as false positives."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            finding_ids = _extract_finding_ids_from_prompt(prompt)
            return LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=finding_ids[0],
                        validation_result="FALSE_POSITIVE",
                        confidence=0.95,
                        reasoning="Comment reference, not actual data subject",
                        recommended_action="discard",
                    ),
                    LLMValidationResultModel(
                        finding_id=finding_ids[1],
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Actual data subject indicator",
                        recommended_action="keep",
                    ),
                ]
            )

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response

        config = DataSubjectAnalyserConfig.from_properties(properties)
        analyser = DataSubjectAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("data_subject_indicator", "1.0.0"),
        )

        # Assert
        findings = result.content["findings"]
        assert len(findings) >= 1, "Should have at least one finding remaining"

        metadata = result.content["analysis_metadata"]
        assert "validation_summary" in metadata
        assert metadata["validation_summary"]["strategy"] == "orchestrated"
        assert metadata["validation_summary"]["samples_validated"] > 0

        # Verify validated findings are marked
        for finding in findings:
            assert (
                finding.get("metadata", {})
                .get("context", {})
                .get("data_subject_llm_validated")
            ), "All kept findings should be marked as validated"

    # -------------------------------------------------------------------------
    # Graceful Degradation
    # -------------------------------------------------------------------------

    def test_llm_validation_unavailable_service_returns_original_findings(
        self,
        mock_llm_service_unavailable: None,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that unavailable LLM service returns original findings safely."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        config = DataSubjectAnalyserConfig.from_properties(properties)
        analyser = DataSubjectAnalyser(config, mock_llm_service_unavailable)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("data_subject_indicator", "1.0.0"),
        )

        # Assert
        assert result is not None
        assert "findings" in result.content
        assert "validation_summary" not in result.content.get("analysis_metadata", {})

    def test_llm_validation_error_returns_original_findings(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM service errors return original findings with failure status."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}
        mock_llm_service.invoke_with_structured_output.side_effect = Exception(
            "LLM service error"
        )

        config = DataSubjectAnalyserConfig.from_properties(properties)
        analyser = DataSubjectAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("data_subject_indicator", "1.0.0"),
        )

        # Assert - findings are preserved, validation attempted but failed
        assert result is not None
        assert "findings" in result.content
        assert len(result.content["findings"]) >= 1  # Original findings preserved

        # Validation summary shows attempt with failure
        metadata = result.content.get("analysis_metadata", {})
        assert "validation_summary" in metadata
        assert metadata["validation_summary"]["all_succeeded"] is False
        assert metadata["validation_summary"]["skipped_count"] > 0

    # -------------------------------------------------------------------------
    # Edge Cases
    # -------------------------------------------------------------------------

    def test_no_findings_skips_llm_validation(
        self,
        mock_llm_service: Mock,
    ) -> None:
        """Test that no findings means no LLM validation is attempted."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="no_patterns",
            description="Test data with no patterns",
            source="test",
            data=[
                StandardInputDataItemModel(
                    content="this content has no data subject patterns",
                    metadata=BaseMetadata(source="test", connector_type="test"),
                )
            ],
        )
        test_message = Message(
            id="test_no_patterns",
            content=test_data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
        )

        config = DataSubjectAnalyserConfig.from_properties(properties)
        analyser = DataSubjectAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message],
            Schema("data_subject_indicator", "1.0.0"),
        )

        # Assert
        mock_llm_service.invoke_with_structured_output.assert_not_called()
        assert "validation_summary" not in result.content.get("analysis_metadata", {})

    def test_validation_metadata_includes_removed_categories(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that removed subject categories are reported in metadata."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        # Mark ALL findings as false positives to trigger group removal
        def mock_llm_response(prompt: str, _schema: type) -> LLMValidationResponseModel:
            finding_ids = _extract_finding_ids_from_prompt(prompt)
            return LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=fid,
                        validation_result="FALSE_POSITIVE",
                        confidence=0.95,
                        reasoning="Not a real data subject indicator",
                        recommended_action="discard",
                    )
                    for fid in finding_ids
                ]
            )

        mock_llm_service.invoke_with_structured_output.side_effect = mock_llm_response

        config = DataSubjectAnalyserConfig.from_properties(properties)
        analyser = DataSubjectAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("data_subject_indicator", "1.0.0"),
        )

        # Assert
        metadata = result.content["analysis_metadata"]
        assert "validation_summary" in metadata

        # When all findings in a group are FP, the group should be removed
        if "subject_categories_removed" in metadata:
            removed = metadata["subject_categories_removed"]
            assert isinstance(removed, list)
            for item in removed:
                assert "subject_category" in item
                assert "reason" in item
