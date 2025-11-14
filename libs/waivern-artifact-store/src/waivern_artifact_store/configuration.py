"""Configuration for artifact store with dependency injection support.

This module provides configuration classes for artifact stores that integrate
with the waivern-core DI system. Configuration supports both explicit
instantiation and environment variable fallback.
"""

from __future__ import annotations

import os
from typing import Any, Self, override

from pydantic import Field, field_validator
from waivern_core.services import BaseServiceConfiguration


class ArtifactStoreConfiguration(BaseServiceConfiguration):
    """Configuration for artifact store with environment fallback.

    This configuration class supports dual-mode operation:
    1. Explicit configuration with typed fields
    2. Environment variable fallback for zero-config scenarios

    The configuration validates backend names at creation time,
    ensuring invalid configurations are caught early.

    Attributes:
        backend: Artifact store backend type (currently only "memory" supported)

    Example:
        ```python
        # Explicit configuration
        config = ArtifactStoreConfiguration(backend="memory")

        # From properties dict with env fallback
        config = ArtifactStoreConfiguration.from_properties({
            "backend": "memory"
        })

        # Zero-config (reads from environment)
        config = ArtifactStoreConfiguration.from_properties({})
        ```

    """

    backend: str = Field(
        default="memory", description="Backend type: currently only 'memory' supported"
    )

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, v: str) -> str:
        """Validate that backend is one of the supported options.

        Args:
            v: Backend name to validate

        Returns:
            Lowercase backend name

        Raises:
            ValueError: If backend is not supported

        """
        allowed = {"memory"}
        backend_lower = v.lower()
        if backend_lower not in allowed:
            raise ValueError(
                f"Backend must be one of {allowed}, got: {v}. "
                f"Currently only in-memory storage is supported."
            )
        return backend_lower

    @classmethod
    @override
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        """Create configuration from properties with environment fallback.

        This method implements a layered configuration system:
        1. Explicit properties (highest priority)
        2. Environment variables (fallback)
        3. Defaults (lowest priority)

        Environment variables used:
        - ARTIFACT_STORE_BACKEND: Backend type (default: "memory")

        Args:
            properties: Configuration properties dictionary

        Returns:
            Validated configuration instance

        Raises:
            ValidationError: If configuration is invalid

        Example:
            ```python
            # Explicit properties override environment
            config = ArtifactStoreConfiguration.from_properties({
                "backend": "memory"
            })

            # Environment fallback
            os.environ["ARTIFACT_STORE_BACKEND"] = "memory"
            config = ArtifactStoreConfiguration.from_properties({})
            ```

        """
        config_data = properties.copy()

        # Backend (env fallback with default)
        if "backend" not in config_data:
            config_data["backend"] = os.getenv("ARTIFACT_STORE_BACKEND", "memory")

        return cls.model_validate(config_data)
