"""Tests for personal data LLM validation strategy."""

import json
from unittest.mock import Mock

import pytest

from wct.analysers.personal_data_analyser.llm_validation_strategy import (
    personal_data_validation_strategy,
)
from wct.analysers.personal_data_analyser.types import (
    PersonalDataFindingMetadata,
    PersonalDataFindingModel,
)
from wct.analysers.types import EvidenceItem, LLMValidationConfig
from wct.llm_service import AnthropicLLMService


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
    def sample_findings(self) -> list[PersonalDataFindingModel]:
        """Create sample findings for testing."""
        return [
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level="medium",
                special_category=False,
                matched_patterns=["test@example.com"],
                evidence=[EvidenceItem(content="Contact us at test@example.com")],
                metadata=PersonalDataFindingMetadata(source="contact_form.php"),
            ),
            PersonalDataFindingModel(
                type="phone",
                data_type="basic_profile",
                risk_level="high",
                special_category=False,
                matched_patterns=["123-456-7890"],
                evidence=[EvidenceItem(content="Call us at 123-456-7890")],
                metadata=PersonalDataFindingMetadata(source="customer_db"),
            ),
        ]

    def test_returns_empty_list_when_no_findings_provided(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test that empty list is returned when no findings are provided."""
        # Arrange
        findings: list[PersonalDataFindingModel] = []

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert result == []
        assert success is True
        mock_llm_service.analyse_data.assert_not_called()

    def test_validates_findings_and_keeps_true_positives(
        self,
        sample_findings: list[PersonalDataFindingModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that true positive findings are kept after validation."""
        # Arrange
        mock_llm_response = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.95,
                    "reasoning": "Valid email address in contact context",
                    "recommended_action": "keep",
                },
                {
                    "finding_index": 1,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.88,
                    "reasoning": "Customer phone number in database",
                    "recommended_action": "keep",
                },
            ]
        )
        mock_llm_service.analyse_data.return_value = mock_llm_response

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 2
        assert result[0].type == "email"
        assert result[1].type == "phone"
        assert success is True
        mock_llm_service.analyse_data.assert_called_once()

    def test_filters_out_false_positive_findings(
        self,
        sample_findings: list[PersonalDataFindingModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that false positive findings are filtered out."""
        # Arrange
        mock_llm_response = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "FALSE_POSITIVE",
                    "confidence": 0.92,
                    "reasoning": "Documentation example email",
                    "recommended_action": "discard",
                },
                {
                    "finding_index": 1,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.85,
                    "reasoning": "Actual customer phone number",
                    "recommended_action": "keep",
                },
            ]
        )
        mock_llm_service.analyse_data.return_value = mock_llm_response

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 1
        assert result[0].type == "phone"
        assert success is True

    def test_handles_mixed_validation_results_correctly(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test handling of mixed validation results across multiple findings."""
        # Arrange
        findings = [
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level="low",
                special_category=False,
                matched_patterns=["admin@domain.com"],
                evidence=[EvidenceItem(content="Email: admin@domain.com")],
                metadata=PersonalDataFindingMetadata(source="config.txt"),
            ),
            PersonalDataFindingModel(
                type="ssn",
                data_type="identification",
                risk_level="high",
                special_category=True,
                matched_patterns=["123-45-6789"],
                evidence=[EvidenceItem(content="SSN: 123-45-6789")],
                metadata=PersonalDataFindingMetadata(source="employee_records"),
            ),
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level="medium",
                special_category=False,
                matched_patterns=["user@test.com"],
                evidence=[EvidenceItem(content="Example: user@test.com")],
                metadata=PersonalDataFindingMetadata(source="documentation.md"),
            ),
        ]

        # Configure to process all in one batch to avoid batch complexity
        llm_config.llm_batch_size = 5

        mock_llm_response = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.78,
                    "reasoning": "Administrative email address",
                    "recommended_action": "keep",
                },
                {
                    "finding_index": 1,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.98,
                    "reasoning": "Sensitive employee data",
                    "recommended_action": "keep",
                },
                {
                    "finding_index": 2,
                    "validation_result": "FALSE_POSITIVE",
                    "confidence": 0.94,
                    "reasoning": "Documentation example",
                    "recommended_action": "discard",
                },
            ]
        )
        mock_llm_service.analyse_data.return_value = mock_llm_response

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 2
        assert result[0].type == "email"
        assert "admin@domain.com" in result[0].matched_patterns
        assert result[1].type == "ssn"
        assert success is True

    def test_processes_findings_in_configured_batches(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test that findings are processed in batches according to configuration."""
        # Arrange
        findings = [
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level="medium",
                special_category=False,
                matched_patterns=[f"user{i}@example.com"],
                evidence=[EvidenceItem(content=f"Email: user{i}@example.com")],
                metadata=PersonalDataFindingMetadata(source="database"),
            )
            for i in range(5)  # Create 5 findings
        ]

        # Configure batch size of 2
        llm_config.llm_batch_size = 2

        # Mock responses for 3 batches (2+2+1)
        batch_responses = [
            json.dumps(
                [
                    {
                        "finding_index": 0,
                        "validation_result": "TRUE_POSITIVE",
                        "confidence": 0.9,
                        "reasoning": "Valid",
                        "recommended_action": "keep",
                    },
                    {
                        "finding_index": 1,
                        "validation_result": "TRUE_POSITIVE",
                        "confidence": 0.9,
                        "reasoning": "Valid",
                        "recommended_action": "keep",
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "finding_index": 0,
                        "validation_result": "FALSE_POSITIVE",
                        "confidence": 0.95,
                        "reasoning": "Example",
                        "recommended_action": "discard",
                    },
                    {
                        "finding_index": 1,
                        "validation_result": "TRUE_POSITIVE",
                        "confidence": 0.85,
                        "reasoning": "Valid",
                        "recommended_action": "keep",
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "finding_index": 0,
                        "validation_result": "TRUE_POSITIVE",
                        "confidence": 0.88,
                        "reasoning": "Valid",
                        "recommended_action": "keep",
                    },
                ]
            ),
        ]

        mock_llm_service.analyse_data.side_effect = batch_responses

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 4  # 2 + 1 + 1 = 4 kept findings
        assert mock_llm_service.analyse_data.call_count == 3  # 3 batch calls
        assert success is True

    def test_handles_llm_service_errors_gracefully(
        self,
        sample_findings: list[PersonalDataFindingModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test graceful handling of LLM service errors."""
        # Arrange
        mock_llm_service.analyse_data.side_effect = Exception("LLM service unavailable")

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
        sample_findings: list[PersonalDataFindingModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test graceful handling of malformed LLM responses."""
        # Arrange
        mock_llm_service.analyse_data.return_value = "Invalid JSON response"

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        # Should return original findings when JSON parsing fails
        assert len(result) == 2
        assert result == sample_findings
        assert success is False

    def test_handles_incomplete_validation_results(
        self,
        sample_findings: list[PersonalDataFindingModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test handling of incomplete validation results from LLM."""
        # Arrange
        mock_llm_response = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    # Missing confidence, reasoning, recommended_action
                },
                {
                    "finding_index": 1,
                    "validation_result": "UNKNOWN_RESULT",  # Invalid result
                    "confidence": 0.5,
                    "reasoning": "Uncertain",
                    "recommended_action": "unknown",
                },
            ]
        )
        mock_llm_service.analyse_data.return_value = mock_llm_response

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        # Should handle missing fields gracefully
        assert len(result) == 2  # Both kept due to conservative approach
        assert result == sample_findings
        assert success is True

    def test_preserves_original_finding_objects(
        self,
        sample_findings: list[PersonalDataFindingModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test that original finding objects are preserved unchanged."""
        # Arrange
        mock_llm_response = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.95,
                    "reasoning": "Valid email",
                    "recommended_action": "keep",
                },
                {
                    "finding_index": 1,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.88,
                    "reasoning": "Valid phone",
                    "recommended_action": "keep",
                },
            ]
        )
        mock_llm_service.analyse_data.return_value = mock_llm_response

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
        assert result[0].type == "email"
        assert len(result[0].evidence) == 1
        assert result[0].evidence[0].content == "Contact us at test@example.com"
        assert result[1].type == "phone"
        assert result[1].metadata.source == "customer_db"

    def test_handles_mismatched_result_count(
        self,
        sample_findings: list[PersonalDataFindingModel],
        llm_config: LLMValidationConfig,
        mock_llm_service: Mock,
    ) -> None:
        """Test handling when validation results count doesn't match findings count."""
        # Arrange - Only one result for two findings
        mock_llm_response = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.95,
                    "reasoning": "Valid email",
                    "recommended_action": "keep",
                },
                # Missing second result
            ]
        )
        mock_llm_service.analyse_data.return_value = mock_llm_response

        # Act
        result, success = personal_data_validation_strategy(
            sample_findings, llm_config, mock_llm_service
        )

        # Assert
        # Should only process the findings that have validation results
        assert len(result) == 1
        assert result[0].type == "email"
        assert success is True

    def test_handles_various_batch_sizes(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test handling of various batch sizes including edge cases."""
        # Arrange
        findings = [
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level="medium",
                special_category=False,
                matched_patterns=[f"test{i}@example.com"],
                evidence=[EvidenceItem(content=f"Email {i}")],
                metadata=PersonalDataFindingMetadata(source="test"),
            )
            for i in range(3)
        ]

        # Test with batch size larger than findings count
        llm_config.llm_batch_size = 10

        mock_llm_response = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Valid",
                    "recommended_action": "keep",
                },
                {
                    "finding_index": 1,
                    "validation_result": "FALSE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Example",
                    "recommended_action": "discard",
                },
                {
                    "finding_index": 2,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.9,
                    "reasoning": "Valid",
                    "recommended_action": "keep",
                },
            ]
        )
        mock_llm_service.analyse_data.return_value = mock_llm_response

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 2  # Two kept, one discarded
        assert mock_llm_service.analyse_data.call_count == 1  # Single batch
        assert success is True

    def test_handles_single_finding_validation(
        self, llm_config: LLMValidationConfig, mock_llm_service: Mock
    ) -> None:
        """Test validation of a single finding."""
        # Arrange
        findings = [
            PersonalDataFindingModel(
                type="credit_card",
                data_type="financial",
                risk_level="high",
                special_category=False,
                matched_patterns=["4111-1111-1111-1111"],
                evidence=[EvidenceItem(content="Card: 4111-1111-1111-1111")],
                metadata=PersonalDataFindingMetadata(source="payment_form"),
            )
        ]

        mock_llm_response = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "FALSE_POSITIVE",
                    "confidence": 0.99,
                    "reasoning": "Test credit card number",
                    "recommended_action": "discard",
                }
            ]
        )
        mock_llm_service.analyse_data.return_value = mock_llm_response

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
            PersonalDataFindingModel(
                type="phone",
                data_type="basic_profile",
                risk_level="medium",
                special_category=False,
                matched_patterns=["+44 20 7946 0958"],
                evidence=[EvidenceItem(content="Contact: +44 20 7946 0958")],
                metadata=PersonalDataFindingMetadata(source="customer_database"),
            )
        ]

        mock_llm_response = json.dumps(
            [
                {
                    "finding_index": 0,
                    "validation_result": "TRUE_POSITIVE",
                    "confidence": 0.92,
                    "reasoning": "Valid UK phone number in customer database",
                    "recommended_action": "keep",
                }
            ]
        )
        mock_llm_service.analyse_data.return_value = mock_llm_response

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
            PersonalDataFindingModel(
                type="email",
                data_type="basic_profile",
                risk_level="medium",
                special_category=False,
                matched_patterns=[f"user{i}@test.com"],
                evidence=[EvidenceItem(content=f"Email: user{i}@test.com")],
                metadata=PersonalDataFindingMetadata(source="test"),
            )
            for i in range(3)
        ]

        llm_config.llm_batch_size = batch_size

        # Mock responses based on expected batch sizes
        if batch_size == 1:
            # 3 calls, each with 1 finding
            mock_responses = [
                json.dumps(
                    [
                        {
                            "finding_index": 0,
                            "validation_result": "TRUE_POSITIVE",
                            "confidence": 0.9,
                            "reasoning": "Valid",
                            "recommended_action": "keep",
                        }
                    ]
                ),
                json.dumps(
                    [
                        {
                            "finding_index": 0,
                            "validation_result": "TRUE_POSITIVE",
                            "confidence": 0.9,
                            "reasoning": "Valid",
                            "recommended_action": "keep",
                        }
                    ]
                ),
                json.dumps(
                    [
                        {
                            "finding_index": 0,
                            "validation_result": "TRUE_POSITIVE",
                            "confidence": 0.9,
                            "reasoning": "Valid",
                            "recommended_action": "keep",
                        }
                    ]
                ),
            ]
        elif batch_size == 2:
            # 2 calls: first with 2 findings, second with 1 finding
            mock_responses = [
                json.dumps(
                    [
                        {
                            "finding_index": 0,
                            "validation_result": "TRUE_POSITIVE",
                            "confidence": 0.9,
                            "reasoning": "Valid",
                            "recommended_action": "keep",
                        },
                        {
                            "finding_index": 1,
                            "validation_result": "TRUE_POSITIVE",
                            "confidence": 0.9,
                            "reasoning": "Valid",
                            "recommended_action": "keep",
                        },
                    ]
                ),
                json.dumps(
                    [
                        {
                            "finding_index": 0,
                            "validation_result": "TRUE_POSITIVE",
                            "confidence": 0.9,
                            "reasoning": "Valid",
                            "recommended_action": "keep",
                        },
                    ]
                ),
            ]
        else:
            # 1 call with all 3 findings
            mock_responses = [
                json.dumps(
                    [
                        {
                            "finding_index": 0,
                            "validation_result": "TRUE_POSITIVE",
                            "confidence": 0.9,
                            "reasoning": "Valid",
                            "recommended_action": "keep",
                        },
                        {
                            "finding_index": 1,
                            "validation_result": "TRUE_POSITIVE",
                            "confidence": 0.9,
                            "reasoning": "Valid",
                            "recommended_action": "keep",
                        },
                        {
                            "finding_index": 2,
                            "validation_result": "TRUE_POSITIVE",
                            "confidence": 0.9,
                            "reasoning": "Valid",
                            "recommended_action": "keep",
                        },
                    ]
                )
            ]

        mock_llm_service.analyse_data.side_effect = mock_responses

        # Act
        result, success = personal_data_validation_strategy(
            findings, llm_config, mock_llm_service
        )

        # Assert
        assert len(result) == 3  # All findings kept
        assert mock_llm_service.analyse_data.call_count == expected_calls
        assert success is True
