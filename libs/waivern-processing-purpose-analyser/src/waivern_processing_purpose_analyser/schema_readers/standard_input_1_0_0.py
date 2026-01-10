"""Reader for standard_input schema version 1.0.0."""

from typing import Any

from waivern_core.schemas import BaseMetadata, StandardInputDataModel

from ..protocols import SchemaInputHandler
from ..standard_input_schema_input_handler import StandardInputSchemaInputHandler
from ..types import ProcessingPurposeAnalyserConfig


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


def create_handler(config: ProcessingPurposeAnalyserConfig) -> SchemaInputHandler:
    """Create handler for standard_input schema.

    Args:
        config: Analyser configuration.

    Returns:
        Handler implementing SchemaInputHandler protocol.

    """
    return StandardInputSchemaInputHandler(config.pattern_matching)
