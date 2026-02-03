"""Tests for PersonalDataAnalyser LLM validation behaviour.

These tests verify the expected behaviour of LLM validation integration
in the analyser's public API using mocked LLM service.
"""

from unittest.mock import AsyncMock, Mock

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
from waivern_llm.v2 import ItemGroup, LLMCompletionResult, LLMService

from waivern_personal_data_analyser.analyser import PersonalDataAnalyser
from waivern_personal_data_analyser.schemas.types import PersonalDataIndicatorModel
from waivern_personal_data_analyser.types import PersonalDataAnalyserConfig


class TestPersonalDataAnalyserLLMValidationBehaviour:
    """Test LLM validation behaviour in the analyser process method."""

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create mock LLM service."""
        service = Mock(spec=LLMService)
        service.complete = AsyncMock()
        return service

    @pytest.fixture
    def mock_llm_service_unavailable(self) -> None:
        """Create unavailable LLM service (None)."""
        return None

    @pytest.fixture
    def test_message_with_patterns(self) -> Message:
        """Create test message with content that matches personal data patterns."""
        test_data = StandardInputDataModel(
            schemaVersion="1.0.0",
            name="test_data",
            description="Test data for LLM validation",
            source="test",
            metadata={},
            data=[
                StandardInputDataItemModel(
                    content="Contact email: john.doe@company.com",
                    metadata=BaseMetadata(
                        source="mysql_database_(prod)_table_(users)",
                        connector_type="mysql",
                    ),
                ),
                StandardInputDataItemModel(
                    content="Phone: +44 20 7123 4567",
                    metadata=BaseMetadata(
                        source="contact_database", connector_type="mysql"
                    ),
                ),
            ],
        )
        return Message(
            id="test",
            content=test_data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
            run_id="test-run-id",  # Set by executor in production
        )

    # =========================================================================
    # LLM Service Interaction
    # =========================================================================

    def test_llm_validation_enabled_calls_llm_service_when_findings_exist(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM validation calls LLM service when findings exist."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        mock_llm_service.complete.return_value = LLMCompletionResult(
            responses=[LLMValidationResponseModel(results=[])],
            skipped=[],
        )

        config = PersonalDataAnalyserConfig.from_properties(properties)
        analyser = PersonalDataAnalyser(config, mock_llm_service)

        # Act
        analyser.process(
            [test_message_with_patterns],
            Schema("personal_data_indicator", "1.0.0"),
        )

        # Assert
        mock_llm_service.complete.assert_called_once()

    def test_llm_validation_disabled_skips_validation(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that disabled LLM validation skips the validation step."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": False}}

        config = PersonalDataAnalyserConfig.from_properties(properties)
        analyser = PersonalDataAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("personal_data_indicator", "1.0.0"),
        )

        # Assert
        mock_llm_service.complete.assert_not_called()
        assert "validation_summary" not in result.content.get("analysis_metadata", {})

    # =========================================================================
    # Finding Filtering
    # =========================================================================

    def test_llm_validation_filters_out_false_positives(
        self,
        mock_llm_service: Mock,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that LLM validation filters out findings marked as false positives."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        # We need to capture the call to get finding IDs from the prompt
        async def mock_complete(
            groups: list[ItemGroup[PersonalDataIndicatorModel]], **_kwargs: object
        ) -> LLMCompletionResult[
            PersonalDataIndicatorModel, LLMValidationResponseModel
        ]:
            # Extract finding IDs from items
            finding_ids = [f.id for g in groups for f in g.items]
            if len(finding_ids) >= 2:
                return LLMCompletionResult(
                    responses=[
                        LLMValidationResponseModel(
                            results=[
                                LLMValidationResultModel(
                                    finding_id=finding_ids[0],
                                    validation_result="FALSE_POSITIVE",
                                    confidence=0.95,
                                    reasoning="Test data email pattern",
                                    recommended_action="discard",
                                ),
                                LLMValidationResultModel(
                                    finding_id=finding_ids[1],
                                    validation_result="TRUE_POSITIVE",
                                    confidence=0.9,
                                    reasoning="Actual phone number",
                                    recommended_action="keep",
                                ),
                            ]
                        )
                    ],
                    skipped=[],
                )
            return LLMCompletionResult(
                responses=[LLMValidationResponseModel(results=[])],
                skipped=[],
            )

        mock_llm_service.complete.side_effect = mock_complete

        config = PersonalDataAnalyserConfig.from_properties(properties)
        analyser = PersonalDataAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("personal_data_indicator", "1.0.0"),
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
                .get("personal_data_llm_validated")
            ), "All kept findings should be marked as validated"

    # =========================================================================
    # Graceful Degradation
    # =========================================================================

    def test_llm_validation_unavailable_service_returns_original_findings(
        self,
        mock_llm_service_unavailable: None,
        test_message_with_patterns: Message,
    ) -> None:
        """Test that unavailable LLM service returns original findings safely."""
        # Arrange
        properties = {"llm_validation": {"enable_llm_validation": True}}

        config = PersonalDataAnalyserConfig.from_properties(properties)
        analyser = PersonalDataAnalyser(config, mock_llm_service_unavailable)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("personal_data_indicator", "1.0.0"),
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
        mock_llm_service.complete.side_effect = Exception("LLM service error")

        config = PersonalDataAnalyserConfig.from_properties(properties)
        analyser = PersonalDataAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message_with_patterns],
            Schema("personal_data_indicator", "1.0.0"),
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

    # =========================================================================
    # Edge Cases
    # =========================================================================

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
                    content="this content has no personal data patterns",
                    metadata=BaseMetadata(source="test", connector_type="test"),
                )
            ],
        )
        test_message = Message(
            id="test_no_patterns",
            content=test_data.model_dump(exclude_none=True),
            schema=Schema("standard_input", "1.0.0"),
            run_id="test-run-id",  # Required for v2 strategies
        )

        config = PersonalDataAnalyserConfig.from_properties(properties)
        analyser = PersonalDataAnalyser(config, mock_llm_service)

        # Act
        result = analyser.process(
            [test_message],
            Schema("personal_data_indicator", "1.0.0"),
        )

        # Assert
        mock_llm_service.complete.assert_not_called()
        assert "validation_summary" not in result.content.get("analysis_metadata", {})
