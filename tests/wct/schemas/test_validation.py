"""Tests for data model parsing utilities."""

import unittest.mock

import pytest
from pydantic import BaseModel

from wct.schemas.validation import DataParsingError, parse_data_model


class SimpleTestModel(BaseModel):
    """Simple test model for validation testing."""

    name: str
    value: int


class TestParseDataModel:
    """Light testing for parse_data_model utility function."""

    def test_parse_data_model_success(self) -> None:
        """Test successful parsing with valid data."""
        data = {"name": "test", "value": 42}

        result = parse_data_model(data, SimpleTestModel)

        assert isinstance(result, SimpleTestModel)
        assert result.name == "test"
        assert result.value == 42

    def test_parse_data_model_validation_error(self) -> None:
        """Test that Pydantic ValidationError becomes DataParsingError."""
        invalid_data = {"name": "test", "value": "not_an_int"}  # Invalid type

        with pytest.raises(DataParsingError) as exc_info:
            parse_data_model(invalid_data, SimpleTestModel)

        error_message = str(exc_info.value)
        assert "Data parsing failed for SimpleTestModel" in error_message
        assert "validation error" in error_message

    def test_parse_data_model_missing_field_error(self) -> None:
        """Test validation error with missing required field."""
        incomplete_data = {"name": "test"}  # Missing 'value' field

        with pytest.raises(DataParsingError) as exc_info:
            parse_data_model(incomplete_data, SimpleTestModel)

        assert "Data parsing failed for SimpleTestModel" in str(exc_info.value)

    def test_parse_data_model_unexpected_error(self) -> None:
        """Test that other exceptions become DataParsingError."""
        # This is hard to trigger with Pydantic, but we test the code path
        # by mocking model_validate to raise an unexpected error
        with unittest.mock.patch.object(
            SimpleTestModel,
            "model_validate",
            side_effect=RuntimeError("Unexpected error"),
        ):
            with pytest.raises(DataParsingError) as exc_info:
                parse_data_model({"name": "test", "value": 42}, SimpleTestModel)

        error_message = str(exc_info.value)
        assert "Unexpected error during data parsing" in error_message
        assert isinstance(exc_info.value.__cause__, RuntimeError)
