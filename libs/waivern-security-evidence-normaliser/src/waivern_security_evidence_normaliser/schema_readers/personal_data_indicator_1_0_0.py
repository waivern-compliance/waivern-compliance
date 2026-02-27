"""Reader for personal_data_indicator schema version 1.0.0."""

from typing import Any

from waivern_personal_data_analyser.schemas.types import PersonalDataIndicatorOutput


def read(content: dict[str, Any]) -> PersonalDataIndicatorOutput:
    """Parse personal_data_indicator v1.0.0 message content.

    Args:
        content: Dict conforming to personal_data_indicator v1.0.0 schema.

    Returns:
        Validated PersonalDataIndicatorOutput instance.

    Raises:
        ValidationError: If content does not match the expected structure.

    """
    return PersonalDataIndicatorOutput.model_validate(content)
