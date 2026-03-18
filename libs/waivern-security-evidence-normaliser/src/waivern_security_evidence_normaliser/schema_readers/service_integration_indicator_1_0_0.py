"""Reader for service_integration_indicator schema version 1.0.0."""

from typing import Any

from waivern_service_integration_analyser.schemas.types import (
    ServiceIntegrationIndicatorOutput,
)


def read(content: dict[str, Any]) -> ServiceIntegrationIndicatorOutput:
    """Parse service_integration_indicator v1.0.0 message content.

    Args:
        content: Dict conforming to service_integration_indicator v1.0.0 schema.

    Returns:
        Validated ServiceIntegrationIndicatorOutput instance.

    Raises:
        ValidationError: If content does not match the expected structure.

    """
    return ServiceIntegrationIndicatorOutput.model_validate(content)
