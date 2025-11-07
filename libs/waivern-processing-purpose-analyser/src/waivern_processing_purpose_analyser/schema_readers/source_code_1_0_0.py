"""Reader for source_code schema version 1.0.0."""

from typing import Any

from waivern_core.schemas import parse_data_model
from waivern_source_code.schemas import SourceCodeDataModel


def read(content: dict[str, Any]) -> SourceCodeDataModel:
    """Transform source_code v1.0.0 to canonical format.

    Uses parse_data_model for generic Pydantic model validation
    with support for generic types.

    Args:
        content: Data conforming to source_code v1.0.0 schema

    Returns:
        Validated SourceCodeDataModel instance

    Raises:
        ValidationError: If content doesn't match schema structure

    """
    return parse_data_model(content, SourceCodeDataModel)
