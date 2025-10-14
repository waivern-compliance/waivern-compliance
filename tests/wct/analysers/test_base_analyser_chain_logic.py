"""Tests for base analyser chain logic functionality."""

from waivern_core.message import Message

from wct.analysers.base import Analyser
from wct.schemas.standard_input import StandardInputSchema


class TestAnalyserChainLogic:
    """Test chain logic in the base Analyser class."""

    def test_update_analyses_chain_creates_first_entry_for_empty_input(self) -> None:
        """Test that chain starts with order 1 when no existing chain present.

        Business Logic: When analysers process input without existing analysis
        metadata, they should start a new chain with order 1.
        """
        # Arrange
        input_message = Message(
            id="test_input",
            content={
                "schemaVersion": "1.0.0",
                "name": "Test data",
                "data": [{"content": "test content", "metadata": {"source": "test"}}],
            },
            schema=StandardInputSchema(),
        )

        # Act
        result_chain = Analyser.update_analyses_chain(input_message, "test_analyser")

        # Assert
        assert len(result_chain) == 1, (
            "Should create single chain entry for new analysis"
        )
        assert result_chain[0].order == 1, "First entry should have order 1"
        assert result_chain[0].analyser == "test_analyser", (
            "Should use provided analyser name"
        )
        assert result_chain[0].execution_timestamp is not None, (
            "Should have execution timestamp"
        )

    def test_update_analyses_chain_extends_existing_chain_with_correct_order(
        self,
    ) -> None:
        """Test that existing chain is extended with next sequential order.

        Business Logic: When analysers receive input from another analyser,
        they must extend the existing chain with the correct next order number.
        """
        # Arrange
        existing_metadata = {
            "ruleset_used": "personal_data",
            "llm_validation_enabled": False,
            "analyses_chain": [
                {
                    "order": 1,
                    "analyser": "personal_data_analyser",
                    "execution_timestamp": "2024-08-21T10:30:00Z",
                },
                {
                    "order": 2,
                    "analyser": "data_subject_analyser",
                    "execution_timestamp": "2024-08-21T10:31:00Z",
                },
            ],
        }

        input_message = Message(
            id="test_input",
            content={
                "findings": [],
                "summary": {"total_findings": 0},
                "analysis_metadata": existing_metadata,
            },
            schema=StandardInputSchema(),
        )

        # Act
        result_chain = Analyser.update_analyses_chain(
            input_message, "processing_purpose_analyser"
        )

        # Assert
        assert len(result_chain) == 3, "Should extend existing chain with new entry"

        # Verify existing entries are preserved
        assert result_chain[0].order == 1
        assert result_chain[0].analyser == "personal_data_analyser"
        assert result_chain[1].order == 2
        assert result_chain[1].analyser == "data_subject_analyser"

        # Verify new entry has correct order
        assert result_chain[2].order == 3, "New entry should have next sequential order"
        assert result_chain[2].analyser == "processing_purpose_analyser"
        assert result_chain[2].execution_timestamp is not None

    def test_update_analyses_chain_handles_non_sequential_existing_orders(self) -> None:
        """Test chain extension when existing orders are not perfectly sequential.

        Business Logic: Chain order calculation should work with max + 1 even
        if existing orders have gaps (e.g., 1, 3, 7 -> next should be 8).
        """
        # Arrange
        existing_metadata = {
            "ruleset_used": "test_ruleset",
            "llm_validation_enabled": True,
            "analyses_chain": [
                {
                    "order": 1,
                    "analyser": "first_analyser",
                    "execution_timestamp": "2024-08-21T10:30:00Z",
                },
                {
                    "order": 5,  # Non-sequential gap
                    "analyser": "second_analyser",
                    "execution_timestamp": "2024-08-21T10:31:00Z",
                },
                {
                    "order": 3,  # Out of order
                    "analyser": "third_analyser",
                    "execution_timestamp": "2024-08-21T10:32:00Z",
                },
            ],
        }

        input_message = Message(
            id="test_input",
            content={
                "findings": [],
                "summary": {"total_findings": 0},
                "analysis_metadata": existing_metadata,
            },
            schema=StandardInputSchema(),
        )

        # Act
        result_chain = Analyser.update_analyses_chain(input_message, "new_analyser")

        # Assert
        assert len(result_chain) == 4, "Should extend existing chain"
        assert result_chain[-1].order == 6, "New order should be max(5) + 1 = 6"
        assert result_chain[-1].analyser == "new_analyser"

    def test_update_analyses_chain_handles_missing_analysis_metadata(self) -> None:
        """Test chain creation when input has no analysis_metadata field.

        Business Logic: Input from connectors won't have analysis_metadata,
        so analysers should create a new chain starting at order 1.
        """
        # Arrange
        input_message = Message(
            id="test_input",
            content={
                "some_field": "some_value",
                "data": {"content": "test content"},
            },
            schema=StandardInputSchema(),
        )

        # Act
        result_chain = Analyser.update_analyses_chain(input_message, "first_analyser")

        # Assert
        assert len(result_chain) == 1, "Should create new chain"
        assert result_chain[0].order == 1, "Should start with order 1"
        assert result_chain[0].analyser == "first_analyser"

    def test_update_analyses_chain_preserves_existing_entry_data(self) -> None:
        """Test that existing chain entries are fully preserved.

        Business Logic: When extending chains, all data from existing
        entries must be preserved for audit trail integrity.
        """
        # Arrange
        original_timestamp = "2024-08-21T10:30:45.123456Z"
        existing_metadata = {
            "ruleset_used": "personal_data",
            "llm_validation_enabled": True,
            "analyses_chain": [
                {
                    "order": 1,
                    "analyser": "personal_data_analyser",
                    "execution_timestamp": original_timestamp,
                }
            ],
        }

        input_message = Message(
            id="test_input",
            content={
                "findings": [],
                "analysis_metadata": existing_metadata,
            },
            schema=StandardInputSchema(),
        )

        # Act
        result_chain = Analyser.update_analyses_chain(
            input_message, "data_subject_analyser"
        )

        # Assert
        assert len(result_chain) == 2, "Should have original plus new entry"

        # Verify original entry is fully preserved
        original_entry = result_chain[0]
        assert original_entry.order == 1
        assert original_entry.analyser == "personal_data_analyser"
        # Compare timestamps by converting both to the same format
        expected_timestamp = original_timestamp.replace("Z", "+00:00")
        assert original_entry.execution_timestamp.isoformat() == expected_timestamp

        # Verify new entry is correct
        new_entry = result_chain[1]
        assert new_entry.order == 2
        assert new_entry.analyser == "data_subject_analyser"
        assert new_entry.execution_timestamp is not None
