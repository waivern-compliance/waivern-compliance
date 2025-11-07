"""Tests for standard_input v1.0.0 producer."""

from pathlib import Path


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

        metadata = {
            "database_name": "test",
            "tables": [
                {
                    "name": "users",
                    "type": "BASE TABLE",
                    "columns": [
                        {
                            "COLUMN_NAME": "email",
                            "DATA_TYPE": "TEXT",
                            "IS_NULLABLE": "NO",
                        }
                    ],
                    "estimated_rows": 10,
                }
            ],
            "server_info": {"version": "SQLite 3.39.0"},
        }

        data_items = [
            {
                "content": "test@example.com",
                "metadata": {
                    "source": "sqlite_database_(test)_table_(users)_column_(email)_row_(1)",
                    "connector_type": "sqlite_connector",
                    "table_name": "users",
                    "column_name": "email",
                    "schema_name": "test",
                },
            }
        ]

        config_data = {
            "database_path": database_path,
            "max_rows_per_table": 100,
        }

        # Act
        result = standard_input_1_0_0.produce(
            schema_version=schema_version,
            metadata=metadata,
            data_items=data_items,
            config_data=config_data,
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
