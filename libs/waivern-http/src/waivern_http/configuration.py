"""Configuration for the shared HTTP client service."""

from __future__ import annotations

import os
from typing import Any, Self, override

from pydantic import Field
from waivern_core.config_validation import validate_or_raise
from waivern_core.services import BaseServiceConfiguration

from waivern_http.errors import HttpConfigError


class HttpClientServiceConfiguration(BaseServiceConfiguration):
    """Configuration for the HTTP client service.

    Holds transport timeouts and circuit-breaker thresholds. The circuit-breaker
    fields are defined here but consumed by the breaker state machine (a later
    step); every field has a sensible default so the service is usable with no
    explicit configuration.

    Attributes:
        connect_timeout_seconds: Maximum time to establish a connection.
        read_timeout_seconds: Maximum time to wait for a response.
        circuit_breaker_failure_threshold: Consecutive failures that open the breaker.
        circuit_breaker_reset_timeout_seconds: Cooldown before the breaker probes recovery.

    """

    connect_timeout_seconds: float = Field(
        default=30.0, gt=0, description="Maximum time to establish a connection"
    )
    read_timeout_seconds: float = Field(
        default=30.0, gt=0, description="Maximum time to wait for a response"
    )
    circuit_breaker_failure_threshold: int = Field(
        default=5, ge=1, description="Consecutive failures that open the breaker"
    )
    circuit_breaker_reset_timeout_seconds: float = Field(
        default=60.0, gt=0, description="Cooldown before the breaker probes recovery"
    )

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from properties with environment fallback.

        Precedence is properties > environment > defaults. Environment values are
        passed through as-is and coerced/validated by Pydantic, so an invalid value
        (e.g. a non-numeric timeout) raises HttpConfigError rather than being ignored.

        Environment variables used:
        - WAIVERN_HTTP_CONNECT_TIMEOUT: Connection timeout in seconds
        - WAIVERN_HTTP_READ_TIMEOUT: Read timeout in seconds
        - WAIVERN_HTTP_CB_FAILURE_THRESHOLD: Consecutive failures that open the breaker
        - WAIVERN_HTTP_CB_RESET_TIMEOUT: Breaker recovery cooldown in seconds

        Raises:
            HttpConfigError: If the assembled configuration is invalid.

        """
        # Env values are passed through as-is and coerced/validated by Pydantic,
        # so a malformed value surfaces as HttpConfigError rather than being
        # silently dropped (unlike a try/except int() fallback).
        env_overrides = {
            "connect_timeout_seconds": "WAIVERN_HTTP_CONNECT_TIMEOUT",
            "read_timeout_seconds": "WAIVERN_HTTP_READ_TIMEOUT",
            "circuit_breaker_failure_threshold": "WAIVERN_HTTP_CB_FAILURE_THRESHOLD",
            "circuit_breaker_reset_timeout_seconds": "WAIVERN_HTTP_CB_RESET_TIMEOUT",
        }
        config_data = properties.copy()
        for field, env_var in env_overrides.items():
            if field not in config_data:
                value = os.getenv(env_var)
                if value is not None:
                    config_data[field] = value

        return validate_or_raise(cls, config_data, HttpConfigError)
