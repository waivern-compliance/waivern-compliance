"""Tests for standard_input v1.0.0 producer."""

from waivern_mysql.schema_producers import standard_input_1_0_0


class TestStandardInputProducer:
    """Tests for standard_input schema v1.0.0 producer module."""

    def test_produce_formats_output_correctly(self) -> None:
        """Test producer formats standard_input output with correct structure."""
        # Arrange
        schema_version = "1.0.0"

        metadata = {
            "database_name": "test_db",
            "tables": [
                {
                    "name": "users",
                    "type": "BASE TABLE",
                    "comment": "",
                    "estimated_rows": 10,
                    "columns": [
                        {
                            "COLUMN_NAME": "email",
                            "DATA_TYPE": "varchar",
                            "IS_NULLABLE": "NO",
                        }
                    ],
                }
            ],
            "server_info": {"version": "8.0.32", "host": "localhost", "port": 3306},
        }

        data_items = [
            {
                "content": "test@example.com",
                "metadata": {
                    "source": "mysql_database_(test_db)_table_(users)_column_(email)_row_(1)",
                    "connector_type": "mysql_connector",
                    "table_name": "users",
                    "column_name": "email",
                    "schema_name": "test_db",
                },
            }
        ]

        config_data = {
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "user": "test_user",
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
        assert result["name"] == "mysql_text_from_test_db"
        assert result["source"] == "localhost:3306/test_db"
        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["content"] == "test@example.com"
        assert result["metadata"]["connector_type"] == "mysql"
        assert result["metadata"]["total_data_items"] == 1
        assert result["metadata"]["connection_info"]["host"] == "localhost"
