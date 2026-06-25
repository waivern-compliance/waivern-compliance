"""Tests for the validate_or_raise configuration-translation helper."""

from typing import Any, override

import pytest
from pydantic import BaseModel


class _SampleConfig(BaseModel):
    """Minimal model standing in for a component configuration."""

    name: str
    count: int


class _RawValueErrorConfig(BaseModel):
    """Model whose validation raises a plain ValueError (not a ValidationError).

    Pydantic wraps validator-raised ``ValueError``s into ``ValidationError``, so a
    raw ``ValueError`` only escapes when ``model_validate`` itself raises one. This
    stub forces that path to exercise the helper's defensive branch.
    """

    @classmethod
    @override
    def model_validate(cls, *_args: Any, **_kwargs: Any) -> "_RawValueErrorConfig":
        raise ValueError("environment preprocessing failed")


class TestValidateOrRaise:
    """validate_or_raise validates a model and translates failures."""

    def test_returns_validated_instance_on_valid_data(self) -> None:
        """Valid data returns a populated instance of the model type."""
        from waivern_core.config_validation import validate_or_raise
        from waivern_core.errors import ConnectorConfigError

        result = validate_or_raise(
            _SampleConfig, {"name": "db", "count": 3}, ConnectorConfigError
        )

        assert isinstance(result, _SampleConfig)
        assert result.name == "db"
        assert result.count == 3

    def test_translates_validation_error_with_structured_errors(self) -> None:
        """ValidationError becomes error_cls carrying .errors() and chained cause."""
        from pydantic import ValidationError

        from waivern_core.config_validation import validate_or_raise
        from waivern_core.errors import ConnectorConfigError

        with pytest.raises(ConnectorConfigError) as exc_info:
            validate_or_raise(_SampleConfig, {"name": "db"}, ConnectorConfigError)

        error = exc_info.value
        assert "_SampleConfig" in str(error)
        assert error.validation_errors is not None
        assert any(detail["loc"] == ("count",) for detail in error.validation_errors)
        assert isinstance(error.__cause__, ValidationError)

    def test_translates_plain_value_error_without_structured_errors(self) -> None:
        """A plain ValueError becomes error_cls with no structured errors."""
        from pydantic import ValidationError

        from waivern_core.config_validation import validate_or_raise
        from waivern_core.errors import ConnectorConfigError

        with pytest.raises(ConnectorConfigError) as exc_info:
            validate_or_raise(_RawValueErrorConfig, {}, ConnectorConfigError)

        error = exc_info.value
        assert error.validation_errors is None
        assert isinstance(error.__cause__, ValueError)
        assert not isinstance(error.__cause__, ValidationError)
