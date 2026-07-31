"""Tests for HttpClientServiceConfiguration."""

import pytest

from waivern_http.configuration import HttpClientServiceConfiguration
from waivern_http.errors import HttpConfigError

_ENV_VARS = (
    "WAIVERN_HTTP_CONNECT_TIMEOUT",
    "WAIVERN_HTTP_READ_TIMEOUT",
    "WAIVERN_HTTP_CB_FAILURE_THRESHOLD",
    "WAIVERN_HTTP_CB_RESET_TIMEOUT",
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all HTTP configuration environment variables."""
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


class TestConfigurationDefaultsAndEnvironment:
    """Configuration assembly from defaults, environment, and properties."""

    def test_uses_defaults_when_no_properties_or_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no properties and no env vars, sensible defaults are used."""
        _clear_env(monkeypatch)

        config = HttpClientServiceConfiguration.from_properties({})

        assert config.connect_timeout_seconds == 30.0
        assert config.read_timeout_seconds == 30.0
        assert config.circuit_breaker_failure_threshold == 5
        assert config.circuit_breaker_reset_timeout_seconds == 60.0

    def test_env_vars_override_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WAIVERN_HTTP_* environment variables override the defaults."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("WAIVERN_HTTP_CONNECT_TIMEOUT", "5")
        monkeypatch.setenv("WAIVERN_HTTP_READ_TIMEOUT", "10")
        monkeypatch.setenv("WAIVERN_HTTP_CB_FAILURE_THRESHOLD", "3")
        monkeypatch.setenv("WAIVERN_HTTP_CB_RESET_TIMEOUT", "15")

        config = HttpClientServiceConfiguration.from_properties({})

        assert config.connect_timeout_seconds == 5.0
        assert config.read_timeout_seconds == 10.0
        assert config.circuit_breaker_failure_threshold == 3
        assert config.circuit_breaker_reset_timeout_seconds == 15.0

    def test_properties_override_env_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit properties take precedence over environment variables."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("WAIVERN_HTTP_CONNECT_TIMEOUT", "5")

        config = HttpClientServiceConfiguration.from_properties(
            {"connect_timeout_seconds": 2.5}
        )

        assert config.connect_timeout_seconds == 2.5

    def test_invalid_value_raises_http_config_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An invalid configuration value is surfaced as HttpConfigError."""
        _clear_env(monkeypatch)
        monkeypatch.setenv("WAIVERN_HTTP_CONNECT_TIMEOUT", "not-a-number")

        with pytest.raises(HttpConfigError):
            HttpClientServiceConfiguration.from_properties({})
