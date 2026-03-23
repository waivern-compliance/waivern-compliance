"""Reader for data_collection_indicator schema version 1.0.0."""

from typing import Any

from waivern_schemas.data_collection_indicator import (
    DataCollectionIndicatorOutput,
)


def read(content: dict[str, Any]) -> DataCollectionIndicatorOutput:
    """Parse data_collection_indicator v1.0.0 message content.

    Args:
        content: Dict conforming to data_collection_indicator v1.0.0 schema.

    Returns:
        Validated DataCollectionIndicatorOutput instance.

    Raises:
        ValidationError: If content does not match the expected structure.

    """
    return DataCollectionIndicatorOutput.model_validate(content)
