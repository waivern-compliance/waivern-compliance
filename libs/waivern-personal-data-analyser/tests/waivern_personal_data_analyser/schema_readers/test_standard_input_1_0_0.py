"""Tests for standard_input v1.0.0 reader."""

from typing import Any

from waivern_core.schemas import StandardInputDataModel

from waivern_personal_data_analyser.schema_readers import standard_input_1_0_0


class TestStandardInputReader:
    """Tests for standard_input schema v1.0.0 reader module."""

    def test_read_transforms_all_required_fields(self) -> None:
        """Test reader transforms all required standard_input fields correctly."""
        input_data = {
            "schemaVersion": "1.0.0",
            "name": "test_dataset",
            "data": [
                {
                    "content": "test@email.com",
                    "metadata": {"source": "test_db", "connector_type": "mysql"},
                },
                {
                    "content": "john@example.com",
                    "metadata": {"source": "test_db", "connector_type": "mysql"},
                },
            ],
        }

        result = standard_input_1_0_0.read(input_data)

        # Assert returns Pydantic model, not dict
        assert isinstance(result, StandardInputDataModel)
        assert result.schemaVersion == "1.0.0"
        assert result.name == "test_dataset"
        assert len(result.data) == 2
        assert result.data[0].content == "test@email.com"
        assert result.data[1].content == "john@example.com"

    def test_read_handles_optional_fields_when_present(self) -> None:
        """Test reader includes optional fields when they are present."""
        input_data = {
            "schemaVersion": "1.0.0",
            "name": "test_dataset",
            "data": [
                {
                    "content": "test",
                    "metadata": {"source": "test_db", "connector_type": "mysql"},
                }
            ],
            "description": "Test description",
            "contentEncoding": "utf-8",
            "source": "test_source",
            "metadata": {"custom_key": "custom_value"},
        }

        result = standard_input_1_0_0.read(input_data)

        assert result.description == "Test description"
        assert result.contentEncoding == "utf-8"
        assert result.source == "test_source"
        assert result.metadata["custom_key"] == "custom_value"

    def test_read_handles_missing_optional_fields(self) -> None:
        """Test reader handles gracefully when optional fields are absent."""
        input_data = {
            "schemaVersion": "1.0.0",
            "name": "minimal_dataset",
            "data": [
                {
                    "content": "test",
                    "metadata": {"source": "test_db", "connector_type": "mysql"},
                }
            ],
            # description, contentEncoding, source, metadata are optional - omitted
        }

        result = standard_input_1_0_0.read(input_data)

        assert result.schemaVersion == "1.0.0"
        assert result.name == "minimal_dataset"
        assert len(result.data) == 1
        # Optional fields should have None or default values
        assert result.description is None
        assert result.contentEncoding is None
        assert result.source is None
        assert result.metadata == {}  # default empty dict

    def test_read_preserves_data_array_structure(self) -> None:
        """Test reader preserves data items with content and metadata structure."""
        input_data = {
            "schemaVersion": "1.0.0",
            "name": "multi_item_dataset",
            "data": [
                {
                    "content": "first item",
                    "metadata": {
                        "source": "db1",
                        "connector_type": "mysql",
                        "extra": "data",
                    },
                },
                {
                    "content": "second item",
                    "metadata": {"source": "db2", "connector_type": "postgresql"},
                },
                {
                    "content": "third item",
                    "metadata": {"source": "db3", "connector_type": "sqlite"},
                },
            ],
        }

        result = standard_input_1_0_0.read(input_data)

        assert len(result.data) == 3
        # Verify structure is preserved
        assert result.data[0].content == "first item"
        assert result.data[0].metadata.source == "db1"
        assert result.data[1].content == "second item"
        assert result.data[1].metadata.source == "db2"
        assert result.data[2].content == "third item"
        assert result.data[2].metadata.source == "db3"

    def test_read_handles_empty_data_array(self) -> None:
        """Test reader handles empty data array gracefully."""
        input_data: dict[str, Any] = {
            "schemaVersion": "1.0.0",
            "name": "empty_dataset",
            "data": [],  # Empty array
        }

        result = standard_input_1_0_0.read(input_data)

        assert result.schemaVersion == "1.0.0"
        assert result.name == "empty_dataset"
        assert result.data == []
        assert len(result.data) == 0
