"""Data model validation utilities for WCT schemas.

This module provides utilities for validating data against strongly typed models,
abstracting the implementation details from the calling code.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError


class DataParsingError(Exception):
    """Raised when data model parsing fails."""

    pass


def parse_data_model[T: BaseModel](data: dict[str, Any], model_class: type[T]) -> T:
    """Parse dictionary data into a strongly typed data model.

    This function converts dictionary data to a strongly typed data model
    with runtime validation. The implementation uses Pydantic for parsing
    and validation but this is an implementation detail.

    Args:
        data: Dictionary data to parse
        model_class: The data model class to parse into

    Returns:
        An instance of the data model with validated data

    Raises:
        DataParsingError: If parsing fails with detailed error information

    """
    try:
        # Use Pydantic to parse and validate the data
        parsed_model = model_class.model_validate(data)
        return parsed_model

    except ValidationError as e:
        raise DataParsingError(
            f"Data parsing failed for {model_class.__name__}: {e}"
        ) from e
    except Exception as e:
        raise DataParsingError(f"Unexpected error during data parsing: {e}") from e
