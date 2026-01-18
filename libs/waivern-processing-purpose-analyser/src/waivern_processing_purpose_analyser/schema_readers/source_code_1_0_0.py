"""Reader for source_code schema version 1.0.0."""

from typing import Any

from waivern_analysers_shared import SchemaInputHandler
from waivern_source_code_analyser import SourceCodeDataModel

from ..schemas.types import ProcessingPurposeFindingModel
from ..source_code_schema_input_handler import SourceCodeSchemaInputHandler
from ..types import ProcessingPurposeAnalyserConfig


def read(content: dict[str, Any]) -> SourceCodeDataModel:
    """Transform source_code v1.0.0 dict to Pydantic model.

    Message has already validated content against JSON schema.
    Converts to authoritative SourceCodeDataModel for type-safe processing.

    Args:
        content: Validated source_code v1.0.0 data

    Returns:
        SourceCodeDataModel instance

    """
    return SourceCodeDataModel.model_validate(content)


def create_handler(
    config: ProcessingPurposeAnalyserConfig,
) -> SchemaInputHandler[ProcessingPurposeFindingModel]:
    """Create handler for source_code schema.

    Args:
        config: Analyser configuration.

    Returns:
        Handler implementing SchemaInputHandler protocol.

    """
    return SourceCodeSchemaInputHandler(
        context_window=config.source_code_context_window
    )
