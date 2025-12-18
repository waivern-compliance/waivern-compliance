"""Tests for standard_input v1.0.0 producer."""

from pathlib import Path

from waivern_connectors_database import (
    ColumnMetadata,
    RelationalExtractionMetadata,
    RelationalProducerConfig,
    TableMetadata,
)
from waivern_core.schemas import (
    RelationalDatabaseMetadata,
    StandardInputDataItemModel,
)


class TestStandardInputProducer:
    """Tests for standard_input schema v1.0.0 producer module."""

    def test_produce_formats_output_correctly(self) -> None:
        """Test producer formats standard_input output with correct structure."""
        from waivern_sqlite.schema_producers import (
            standard_input_1_0_0,
        )

        # Arrange
        schema_version = "1.0.0"
        database_path = "/path/to/test.db"

        metadata = RelationalExtractionMetadata(
            database_name="test",
            tables=[
                TableMetadata(
                    name="users",
                    table_type="BASE TABLE",
                    comment=None,
                    estimated_rows=10,
                    columns=[
                        ColumnMetadata(
                            name="email",
                            data_type="TEXT",
                            is_nullable=False,
                            default=None,
                            comment=None,
                            key=None,
                            extra=None,
                        )
                    ],
                )
            ],
            server_info=None,  # SQLite doesn't have server info
        )

        data_items = [
            StandardInputDataItemModel(
                content="test@example.com",
                metadata=RelationalDatabaseMetadata(
                    source="sqlite_database_(test)_table_(users)_column_(email)_row_(1)",
                    connector_type="sqlite_connector",
                    table_name="users",
                    column_name="email",
                    schema_name="test",
                ),
            )
        ]

        config_data = RelationalProducerConfig(
            database="test",
            max_rows_per_table=100,
            host=None,
            port=None,
            user=None,
        )

        # Act
        result = standard_input_1_0_0.produce(
            schema_version=schema_version,
            metadata=metadata,
            data_items=data_items,
            config_data=config_data,
            database_path=database_path,
        )

        # Assert
        assert result["schemaVersion"] == "1.0.0"
        assert result["name"] == "sqlite_text_from_test"
        assert result["source"] == str(Path(database_path).absolute())
        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["content"] == "test@example.com"
        assert result["metadata"]["connector_type"] == "sqlite_connector"
        assert result["metadata"]["total_data_items"] == 1
