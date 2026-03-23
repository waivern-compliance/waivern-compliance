"""Reader for crypto_quality_indicator schema version 1.0.0."""

from typing import Any

from waivern_schemas.crypto_quality_indicator import CryptoQualityIndicatorOutput


def read(content: dict[str, Any]) -> CryptoQualityIndicatorOutput:
    """Parse crypto_quality_indicator v1.0.0 message content.

    Args:
        content: Dict conforming to crypto_quality_indicator v1.0.0 schema.

    Returns:
        Validated CryptoQualityIndicatorOutput instance.

    Raises:
        ValidationError: If content does not match the expected structure.

    """
    return CryptoQualityIndicatorOutput.model_validate(content)
