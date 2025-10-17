"""Tests for database extraction utility functions following TDD/BDD methodology."""

from waivern_core.schemas import (
    RelationalDatabaseMetadata,
    StandardInputDataItemModel,
)

from waivern_connectors_database import DatabaseExtractionUtils


class TestDatabaseExtractionUtils:
    """Test suite for DatabaseExtractionUtils following BDD patterns."""

    def test_filter_non_empty_cell_accepts_valid_content(self) -> None:
        """Test that filter_non_empty_cell accepts valid content.

        GIVEN non-null, non-empty cell values
        WHEN filtering cell content
        THEN it should return True for valid content.
        """
        # Arrange - Various valid cell content types
        valid_contents = [
            "hello world",  # String
            "   content   ",  # String with spaces (but not empty)
            123,  # Integer
            45.67,  # Float
            True,  # Boolean
            "0",  # String zero
            0,  # Numeric zero
        ]

        # Act & Assert
        for content in valid_contents:
            result = DatabaseExtractionUtils.filter_non_empty_cell(content)
            assert result is True, f"Expected True for content: {repr(content)}"

    def test_filter_non_empty_cell_rejects_invalid_content(self) -> None:
        """Test that filter_non_empty_cell rejects invalid content.

        GIVEN null, empty, or whitespace-only cell values
        WHEN filtering cell content
        THEN it should return False for invalid content.
        """
        # Arrange - Various invalid cell content types
        invalid_contents = [
            None,  # Null value
            "",  # Empty string
            "   ",  # Whitespace only
            "\t",  # Tab only
            "\n",  # Newline only
            "\r\n",  # Carriage return + newline
            "  \t  \n  ",  # Mixed whitespace
        ]

        # Act & Assert
        for content in invalid_contents:
            result = DatabaseExtractionUtils.filter_non_empty_cell(content)
            assert result is False, f"Expected False for content: {repr(content)}"

    def test_create_cell_data_item_creates_correct_structure(self) -> None:
        """Test that create_cell_data_item creates correct structure.

        GIVEN cell value and RelationalDatabaseMetadata
        WHEN creating cell data item
        THEN it should return StandardInputDataItemModel with proper typing.
        """
        # Arrange
        cell_value = "test content"
        metadata = RelationalDatabaseMetadata(
            source="test_database_(mydb)_table_(users)_column_(name)_row_(1)",
            connector_type="test",
            table_name="users",
            column_name="name",
            schema_name="mydb",
        )

        # Act
        result = DatabaseExtractionUtils.create_cell_data_item(cell_value, metadata)

        # Assert - Check type and structure
        assert isinstance(result, StandardInputDataItemModel)
        assert hasattr(result, "content")
        assert hasattr(result, "metadata")

        # Assert - Check values
        assert result.content == str(cell_value)  # Should be converted to string
        assert result.metadata == metadata  # Should be the actual metadata object

        # Assert - Check that we can still convert to dict if needed (for compatibility)
        as_dict = result.model_dump()
        assert "content" in as_dict
        assert "metadata" in as_dict

    def test_create_cell_data_item_converts_content_to_string(self) -> None:
        """Test that create_cell_data_item converts content to string.

        GIVEN various data types (int, float, date, etc.)
        WHEN creating cell data item
        THEN content should be converted to string representation.
        """
        # Arrange
        metadata = RelationalDatabaseMetadata(
            source="test_database_(mydb)_table_(data)_column_(value)_row_(1)",
            connector_type="test",
            table_name="data",
            column_name="value",
            schema_name="mydb",
        )

        # Test various data types that databases can return
        test_values = [
            (123, "123"),  # Integer
            (45.67, "45.67"),  # Float
            (True, "True"),  # Boolean True
            (False, "False"),  # Boolean False
            (0, "0"),  # Zero integer
            (0.0, "0.0"),  # Zero float
            ("already string", "already string"),  # String (should remain unchanged)
        ]

        for original_value, expected_string in test_values:
            # Act
            result = DatabaseExtractionUtils.create_cell_data_item(
                original_value, metadata
            )

            # Assert
            assert result.content == expected_string, (
                f"Expected {expected_string!r} for input {original_value!r}, got {result.content!r}"
            )
            assert isinstance(result.content, str), (
                f"Content should be string, got {type(result.content)}"
            )
