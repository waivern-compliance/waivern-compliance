"""Tests for standard_input v1.0.0 reader."""

from waivern_core.schemas import StandardInputDataModel


class TestStandardInputReader:
    """Tests for standard_input schema v1.0.0 reader module."""

    def test_read_validates_and_returns_typed_model(self) -> None:
        """Test reader validates input and returns StandardInputDataModel."""
        from waivern_community.analysers.data_subject_analyser.schema_readers import (
            standard_input_1_0_0,
        )

        # Arrange: Valid standard_input data
        input_data = {
            "schemaVersion": "1.0.0",
            "name": "Test data",
            "description": "Test description",
            "source": "test_source",
            "metadata": {},
            "data": [
                {
                    "content": "Test content",
                    "metadata": {
                        "source": "test",
                        "connector_type": "test_connector",
                    },
                }
            ],
        }

        # Act
        result = standard_input_1_0_0.read(input_data)

        # Assert
        assert isinstance(result, StandardInputDataModel)
        assert result.schemaVersion == "1.0.0"
        assert result.name == "Test data"
        assert len(result.data) == 1
        assert result.data[0].content == "Test content"
        assert result.data[0].metadata.source == "test"
