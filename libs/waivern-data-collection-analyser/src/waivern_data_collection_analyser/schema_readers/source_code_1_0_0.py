"""Reader for source_code schema version 1.0.0."""

from typing import Any

from waivern_source_code_analyser.schemas.source_code import SourceCodeDataModel


def read(content: dict[str, Any]) -> SourceCodeDataModel:
    """Transform source_code v1.0.0 dict to SourceCodeDataModel.

    Args:
        content: Validated source_code v1.0.0 data.

    Returns:
        Validated SourceCodeDataModel instance.

    """
    return SourceCodeDataModel.model_validate(content)
