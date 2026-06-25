"""Tests for WaivernError carrying structured validation errors."""

from typing import cast

from pydantic_core import ErrorDetails


def _error_detail() -> ErrorDetails:
    """A representative Pydantic ErrorDetails entry."""
    return cast(
        ErrorDetails,
        {"type": "missing", "loc": ("path",), "msg": "Field required", "input": {}},
    )


class TestWaivernErrorValidationErrors:
    """WaivernError can carry Pydantic structured error data."""

    def test_defaults_to_none_and_preserves_message(self) -> None:
        """WaivernError("msg") stores no validation errors and keeps its message."""
        from waivern_core.errors import WaivernError

        error = WaivernError("something went wrong")

        assert error.validation_errors is None
        assert str(error) == "something went wrong"

    def test_stores_provided_validation_errors(self) -> None:
        """WaivernError stores a provided list of validation errors."""
        from waivern_core.errors import WaivernError

        details = [_error_detail()]
        error = WaivernError("invalid config", validation_errors=details)

        assert error.validation_errors == details

    def test_subclass_inherits_validation_errors_parameter(self) -> None:
        """Category subclasses inherit the validation_errors parameter."""
        from waivern_core.errors import ConnectorConfigError

        details = [_error_detail()]
        error = ConnectorConfigError(
            "invalid connector config", validation_errors=details
        )

        assert error.validation_errors == details
