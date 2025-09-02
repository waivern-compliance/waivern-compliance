"""Database data extraction and processing utilities."""

from wct.schemas import RelationalDatabaseMetadata, StandardInputDataItemModel

# Type alias for database cell values
CellValue = str | int | float | bool | None


class DatabaseExtractionUtils:
    """Utilities for database data extraction and processing."""

    @staticmethod
    def filter_non_empty_cell(cell_value: CellValue) -> bool:
        """Filter out null, empty, or whitespace-only cell values.

        Args:
            cell_value: The cell value to check

        Returns:
            True if the cell value is valid (non-null, non-empty)

        """
        # Check for None/null values
        if cell_value is None:
            return False

        # Convert to string and check if it's empty or whitespace-only
        str_value = str(cell_value).strip()
        return len(str_value) > 0

    @staticmethod
    def create_cell_data_item(
        cell_value: CellValue, metadata: RelationalDatabaseMetadata
    ) -> StandardInputDataItemModel[RelationalDatabaseMetadata]:
        """Create a cell data item with metadata.

        Args:
            cell_value: The cell value to include
            metadata: RelationalDatabaseMetadata instance

        Returns:
            Properly typed StandardInputDataItemModel

        """
        return StandardInputDataItemModel[RelationalDatabaseMetadata](
            content=str(cell_value),
            metadata=metadata,
        )
