"""Reader for processing_purpose_indicator schema version 1.0.0."""

from typing import Any

from waivern_schemas.processing_purpose_indicator import (
    ProcessingPurposeIndicatorOutput,
)


def read(content: dict[str, Any]) -> ProcessingPurposeIndicatorOutput:
    """Parse processing_purpose_indicator v1.0.0 message content.

    Args:
        content: Dict conforming to processing_purpose_indicator v1.0.0 schema.

    Returns:
        Validated ProcessingPurposeIndicatorOutput instance.

    Raises:
        ValidationError: If content does not match the expected structure.

    """
    return ProcessingPurposeIndicatorOutput.model_validate(content)
