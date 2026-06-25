"""Mechanical helper for translating configuration validation failures.

``validate_or_raise`` performs only the ``model_validate``-and-translate step. It
holds no policy and never reaches into the environment: each component owns its own
``from_properties`` assembly (env-var merging, secret resolution, field dispatch) and
names the category error class to translate into.
"""

from typing import Any

from pydantic import BaseModel, ValidationError

from waivern_core.errors import WaivernError


def validate_or_raise[T: BaseModel](
    model: type[T], data: dict[str, Any], error_cls: type[WaivernError]
) -> T:
    """Validate ``data`` against ``model``, translating failures to ``error_cls``.

    Args:
        model: The Pydantic model to validate against.
        data: The assembled configuration data to validate.
        error_cls: The framework error class to raise on failure.

    Returns:
        The validated model instance.

    Raises:
        WaivernError: An instance of ``error_cls`` if validation fails. For a
            ``ValidationError`` source the structured ``.errors()`` data is carried
            on ``error.validation_errors``; for a plain ``ValueError`` it stays
            ``None``. The original exception is always chained via ``__cause__``.

    """
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise error_cls(
            f"Invalid {model.__name__}: {e}", validation_errors=e.errors()
        ) from e
    except ValueError as e:  # env-preprocessing raise; no structured .errors()
        raise error_cls(f"Invalid {model.__name__}: {e}") from e
