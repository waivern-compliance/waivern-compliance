"""Tests for personal data LLM validation strategy."""

from unittest.mock import Mock

import pytest
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.schemas import BaseFindingEvidence
from waivern_llm import AnthropicLLMService

from waivern_personal_data_analyser.llm_validation_strategy import (
    personal_data_validation_strategy,
)
from waivern_personal_data_analyser.schemas.types import (
    PersonalDataIndicatorMetadata,
    PersonalDataIndicatorModel,
)


class TestPersonalDataValidationStrategy:
    """Test suite for personal data validation strategy function."""

    @pytest.fixture
    def llm_config(self) -> LLMValidationConfig:
        """Create standard LLM configuration for testing."""
        return LLMValidationConfig(
            enable_llm_validation=True,
            llm_batch_size=2,
            llm_validation_mode="standard",
        )

    @pytest.fixture
    def mock_llm_service(self) -> Mock:
        """Create a mock LLM service for testing."""
        return Mock(spec=AnthropicLLMService)

    @pytest.fixture
    def sample_findings(self) -> list[PersonalDataIndicatorModel]:
        """Create sample findings for testing."""
        return [
            PersonalDataIndicatorModel(
                category="email",
                matched_patterns=["test@example.com"],
                evidence=[
                    BaseFindingEvidence(content="Contact us at test@example.com")
                ],
                metadata=PersonalDataIndicatorMetadata(source="contact_form.php"),
            ),
            PersonalDataIndicatorModel(
                category="phone",
                matched_patterns=["123-456-7890"],
                evidence=[BaseFindingEvidence(content="Call us at 123-456-7890")],
                metadata=PersonalDataIndicatorMetadata(source="customer_db"),
            ),
        ]

    def test_returns_empty_list_when_no_findings_provided(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test that empty list is returned when no findings are provided."""
        # Arrange
        findings: list[PersonalDataIndicatorModel] = []

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert result == []
        assert success is True
        mock_llm_service.invoke_with_structured_output.assert_not_called()

    def test_validates_findings_and_keeps_true_positives(
        self,
        sample_findings: list[PersonalDataIndicatorModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that true positive findings are kept after validation."""
        # Arrange
        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=sample_findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.95,
                        reasoning="Valid email address in contact context",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=sample_findings[1].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.88,
                        reasoning="Customer phone number in database",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 2
        assert result[0].category == "email"
        assert result[1].category == "phone"
        assert success is True
        mock_llm_service.invoke_with_structured_output.assert_called_once()

    def test_filters_out_false_positive_findings(
        self,
        sample_findings: list[PersonalDataIndicatorModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that false positive findings are filtered out."""
        # Arrange
        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=sample_findings[0].id,
                        validation_result="FALSE_POSITIVE",
                        confidence=0.92,
                        reasoning="Documentation example email",
                        recommended_action="discard",
                    ),
                    LLMValidationResultModel(
                        finding_id=sample_findings[1].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.85,
                        reasoning="Actual customer phone number",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 1
        assert result[0].category == "phone"
        assert success is True

    def test_handles_mixed_validation_results_correctly(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test handling of mixed validation results across multiple findings."""
        # Arrange
        findings = [
            PersonalDataIndicatorModel(
                category="email",
                matched_patterns=["admin@domain.com"],
                evidence=[BaseFindingEvidence(content="Email: admin@domain.com")],
                metadata=PersonalDataIndicatorMetadata(source="config.txt"),
            ),
            PersonalDataIndicatorModel(
                category="government_id",
                matched_patterns=["123-45-6789"],
                evidence=[BaseFindingEvidence(content="SSN: 123-45-6789")],
                metadata=PersonalDataIndicatorMetadata(source="employee_records"),
            ),
            PersonalDataIndicatorModel(
                category="email",
                matched_patterns=["user@test.com"],
                evidence=[BaseFindingEvidence(content="Example: user@test.com")],
                metadata=PersonalDataIndicatorMetadata(source="documentation.md"),
            ),
        ]

        # Configure to process all in one batch to avoid batch complexity
        llm_config.llm_batch_size = 5

        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.78,
                        reasoning="Administrative email address",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[1].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.98,
                        reasoning="Sensitive employee data",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[2].id,
                        validation_result="FALSE_POSITIVE",
                        confidence=0.94,
                        reasoning="Documentation example",
                        recommended_action="discard",
                    ),
                ]
            )
        )

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 2
        assert result[0].category == "email"
        assert "admin@domain.com" in result[0].matched_patterns
        assert result[1].category == "government_id"
        assert success is True

    def test_processes_findings_in_configured_batches(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test that findings are processed in batches according to configuration."""
        # Arrange
        findings = [
            PersonalDataIndicatorModel(
                category="email",
                matched_patterns=[f"user{i}@example.com"],
                evidence=[BaseFindingEvidence(content=f"Email: user{i}@example.com")],
                metadata=PersonalDataIndicatorMetadata(source="database"),
            )
            for i in range(5)  # Create 5 findings
        ]

        # Configure batch size of 2
        llm_config.llm_batch_size = 2

        # Mock responses for 3 batches (2+2+1)
        batch_responses = [
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[1].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                ]
            ),
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[2].id,
                        validation_result="FALSE_POSITIVE",
                        confidence=0.95,
                        reasoning="Example",
                        recommended_action="discard",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[3].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.85,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                ]
            ),
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[4].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.88,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                ]
            ),
        ]

        mock_llm_service.invoke_with_structured_output.side_effect = batch_responses

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 4  # 2 + 1 + 1 = 4 kept findings
        assert mock_llm_service.invoke_with_structured_output.call_count == 3
        assert success is True

    def test_handles_llm_service_errors_gracefully(
        self,
        sample_findings: list[PersonalDataIndicatorModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test graceful handling of LLM service errors."""
        # Arrange
        mock_llm_service.invoke_with_structured_output.side_effect = Exception(
            "LLM service unavailable"
        )

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        # Should return original findings when validation fails
        assert len(result) == 2
        assert result == sample_findings
        assert success is False

    def test_handles_malformed_llm_response_gracefully(
        self,
        sample_findings: list[PersonalDataIndicatorModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test graceful handling of malformed LLM responses.

        With structured output, malformed responses cause exceptions
        from LangChain/Pydantic validation.
        """
        # Arrange
        mock_llm_service.invoke_with_structured_output.side_effect = Exception(
            "Validation error: invalid response format"
        )

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        # Should return original findings when validation fails
        assert len(result) == 2
        assert result == sample_findings
        assert success is False

    def test_handles_incomplete_validation_results(
        self,
        sample_findings: list[PersonalDataIndicatorModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test handling of incomplete validation results from LLM.

        With structured output, missing fields get defaults from Pydantic model.
        """
        # Arrange - Model with defaults (UNKNOWN result, 0.0 confidence, etc.)
        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=sample_findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        # confidence uses default 0.0
                        # reasoning uses default
                        # recommended_action uses default "keep"
                    ),
                    LLMValidationResultModel(
                        finding_id=sample_findings[1].id,
                        validation_result="UNKNOWN",  # UNKNOWN result
                        confidence=0.5,
                        reasoning="Uncertain",
                        recommended_action="flag_for_review",
                    ),
                ]
            )
        )

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        # Should handle defaults gracefully
        assert len(result) == 2  # Both kept due to conservative approach
        assert result == sample_findings
        assert success is True

    def test_preserves_original_finding_objects(
        self,
        sample_findings: list[PersonalDataIndicatorModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that original finding objects are preserved unchanged."""
        # Arrange
        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=sample_findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.95,
                        reasoning="Valid email",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=sample_findings[1].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.88,
                        reasoning="Valid phone",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 2
        # Verify the returned objects are the same instances
        assert result[0] is sample_findings[0]
        assert result[1] is sample_findings[1]
        assert success is True
        # Verify all properties are unchanged
        assert result[0].category == "email"
        assert len(result[0].evidence) == 1
        assert result[0].evidence[0].content == "Contact us at test@example.com"
        assert result[1].category == "phone"
        assert result[1].metadata is not None
        assert result[1].metadata.source == "customer_db"

    def test_handles_mismatched_result_count(
        self,
        sample_findings: list[PersonalDataIndicatorModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test handling when validation results count doesn't match findings count.

        Fail-safe behavior: Findings omitted from LLM response are included
        (with warning) rather than silently dropped.
        """
        # Arrange - Only one result for two findings
        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=sample_findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.95,
                        reasoning="Valid email",
                        recommended_action="keep",
                    ),
                    # Missing second result - will be included unvalidated (fail-safe)
                ]
            )
        )

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert - Both findings included (one validated, one unvalidated fail-safe)
        assert len(result) == 2
        result_categories = {f.category for f in result}
        assert result_categories == {"email", "phone"}
        assert success is True

    def test_handles_various_batch_sizes(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test handling of various batch sizes including edge cases."""
        # Arrange
        findings = [
            PersonalDataIndicatorModel(
                category="email",
                matched_patterns=[f"test{i}@example.com"],
                evidence=[BaseFindingEvidence(content=f"Email {i}")],
                metadata=PersonalDataIndicatorMetadata(source="test"),
            )
            for i in range(3)
        ]

        # Test with batch size larger than findings count
        llm_config.llm_batch_size = 10

        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[1].id,
                        validation_result="FALSE_POSITIVE",
                        confidence=0.9,
                        reasoning="Example",
                        recommended_action="discard",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[2].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 2  # Two kept, one discarded
        assert mock_llm_service.invoke_with_structured_output.call_count == 1
        assert success is True

    def test_handles_single_finding_validation(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test validation of a single finding."""
        # Arrange
        findings = [
            PersonalDataIndicatorModel(
                category="payment",
                matched_patterns=["4111-1111-1111-1111"],
                evidence=[BaseFindingEvidence(content="Card: 4111-1111-1111-1111")],
                metadata=PersonalDataIndicatorMetadata(source="payment_form"),
            )
        ]

        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="FALSE_POSITIVE",
                        confidence=0.99,
                        reasoning="Test credit card number",
                        recommended_action="discard",
                    )
                ]
            )
        )

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 0  # Discarded as false positive
        assert success is True

    def test_validates_findings_with_complex_metadata(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test validation of findings with complex metadata structures."""
        # Arrange
        findings = [
            PersonalDataIndicatorModel(
                category="phone",
                matched_patterns=["+44 20 7946 0958"],
                evidence=[BaseFindingEvidence(content="Contact: +44 20 7946 0958")],
                metadata=PersonalDataIndicatorMetadata(source="customer_database"),
            )
        ]

        mock_llm_service.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.92,
                        reasoning="Valid UK phone number in customer database",
                        recommended_action="keep",
                    )
                ]
            )
        )

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 1
        assert result[0].metadata == findings[0].metadata
        assert result[0].metadata is not None
        assert result[0].metadata.source == "customer_database"
        assert success is True

    @pytest.mark.parametrize(
        "batch_size,expected_calls",
        [
            (1, 3),  # 3 findings, batch size 1 = 3 calls
            (2, 2),  # 3 findings, batch size 2 = 2 calls (2+1)
            (3, 1),  # 3 findings, batch size 3 = 1 call
            (5, 1),  # 3 findings, batch size 5 = 1 call
        ],
    )
    def test_batch_processing_with_various_sizes(
        self,
        batch_size: int,
        expected_calls: int,
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test batch processing with various batch sizes."""
        # Arrange
        findings = [
            PersonalDataIndicatorModel(
                category="email",
                matched_patterns=[f"user{i}@test.com"],
                evidence=[BaseFindingEvidence(content=f"Email: user{i}@test.com")],
                metadata=PersonalDataIndicatorMetadata(source="test"),
            )
            for i in range(3)
        ]

        llm_config.llm_batch_size = batch_size

        # Mock responses based on expected batch sizes
        if batch_size == 1:
            # 3 calls, each with 1 finding
            mock_responses = [
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=findings[0].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid",
                            recommended_action="keep",
                        )
                    ]
                ),
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=findings[1].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid",
                            recommended_action="keep",
                        )
                    ]
                ),
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=findings[2].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid",
                            recommended_action="keep",
                        )
                    ]
                ),
            ]
        elif batch_size == 2:
            # 2 calls: first with 2 findings, second with 1 finding
            mock_responses = [
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=findings[0].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid",
                            recommended_action="keep",
                        ),
                        LLMValidationResultModel(
                            finding_id=findings[1].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid",
                            recommended_action="keep",
                        ),
                    ]
                ),
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=findings[2].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid",
                            recommended_action="keep",
                        ),
                    ]
                ),
            ]
        else:
            # 1 call with all 3 findings
            mock_responses = [
                LLMValidationResponseModel(
                    results=[
                        LLMValidationResultModel(
                            finding_id=findings[0].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid",
                            recommended_action="keep",
                        ),
                        LLMValidationResultModel(
                            finding_id=findings[1].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid",
                            recommended_action="keep",
                        ),
                        LLMValidationResultModel(
                            finding_id=findings[2].id,
                            validation_result="TRUE_POSITIVE",
                            confidence=0.9,
                            reasoning="Valid",
                            recommended_action="keep",
                        ),
                    ]
                )
            ]

        mock_llm_service.invoke_with_structured_output.side_effect = mock_responses

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 3  # All findings kept
        assert (
            mock_llm_service.invoke_with_structured_output.call_count == expected_calls
        )
        assert success is True
