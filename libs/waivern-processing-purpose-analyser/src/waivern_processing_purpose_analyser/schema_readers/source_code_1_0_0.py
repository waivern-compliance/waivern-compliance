"""Reader for source_code schema version 1.0.0."""

from typing import Any, cast

from waivern_processing_purpose_analyser.source_code_schema_input_handler import (
    SourceCodeSchemaDict,
)


def read(content: dict[str, Any]) -> SourceCodeSchemaDict:
    """Transform source_code v1.0.0 to TypedDict.

    Message has already validated content against JSON schema.
    Returns dict with TypedDict type hint for compile-time safety.

    Args:
        content: Validated source_code v1.0.0 data

    Returns:
        TypedDict-annotated dict

    """
    return cast(SourceCodeSchemaDict, content)
