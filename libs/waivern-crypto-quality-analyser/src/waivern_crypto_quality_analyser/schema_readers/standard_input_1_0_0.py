"""Reader for standard_input schema version 1.0.0."""

from typing import Any

from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.standard_input import StandardInputDataModel


def read(content: dict[str, Any]) -> StandardInputDataModel[BaseMetadata]:
    """Transform standard_input v1.0.0 to canonical format.

    This version matches the canonical model structure, so we use
    direct Pydantic validation without transformation.

    Args:
        content: Data conforming to standard_input v1.0.0 schema

    Returns:
        Validated StandardInputDataModel instance

    Raises:
        ValidationError: If content doesn't match schema structure

    """
    return StandardInputDataModel[BaseMetadata].model_validate(content)
