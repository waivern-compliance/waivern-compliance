"""Tests for artifact store configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from waivern_artifact_store.configuration import ArtifactStoreConfiguration

ARTIFACT_STORE_ENV_VARS = ["ARTIFACT_STORE_BACKEND"]


# =============================================================================
# Configuration Tests (defaults, validation, environment)
# =============================================================================


class TestArtifactStoreConfiguration:
    """Test ArtifactStoreConfiguration class."""

    # -------------------------------------------------------------------------
    # Default Values
    # -------------------------------------------------------------------------

    def test_configuration_uses_default_backend_when_not_specified(self) -> None:
        """Test default backend is 'memory' when not specified."""
        config = ArtifactStoreConfiguration()

        assert config.backend == "memory"

    def test_backend_is_case_insensitive(self) -> None:
        """Test backend value is normalised to lowercase."""
        config = ArtifactStoreConfiguration(backend="MEMORY")

        assert config.backend == "memory"

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def test_validation_rejects_unsupported_backend(self) -> None:
        """Test only 'memory' backend is accepted."""
        try:
            ArtifactStoreConfiguration(backend="redis")
            assert False, "Should have raised ValidationError for unsupported backend"
        except ValidationError as e:
            error_msg = str(e).lower()
            assert "backend" in error_msg or "memory" in error_msg

    def test_validation_rejects_empty_backend(self) -> None:
        """Test backend cannot be empty string."""
        try:
            ArtifactStoreConfiguration(backend="")
            assert False, "Should have raised ValidationError for empty backend"
        except ValidationError as e:
            error_msg = str(e).lower()
            assert "backend" in error_msg or "memory" in error_msg

    # -------------------------------------------------------------------------
    # Factory Method (from_properties)
    # -------------------------------------------------------------------------

    def test_from_properties_falls_back_to_environment_variables_when_properties_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment fallback when no properties provided."""
        for var in ARTIFACT_STORE_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("ARTIFACT_STORE_BACKEND", "memory")

        config = ArtifactStoreConfiguration.from_properties({})

        assert config.backend == "memory"

    def test_from_properties_uses_default_when_no_properties_or_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test default backend used when no properties or environment variables."""
        for var in ARTIFACT_STORE_ENV_VARS:
            monkeypatch.delenv(var, raising=False)

        config = ArtifactStoreConfiguration.from_properties({})

        assert config.backend == "memory"

    def test_from_properties_prioritises_properties_over_environment_variables(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that explicit properties override environment variables.

        Sets env to an invalid value and property to valid value.
        If properties didn't take priority, this would raise ValidationError.
        """
        for var in ARTIFACT_STORE_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("ARTIFACT_STORE_BACKEND", "redis")  # Invalid backend

        # Explicit property should override invalid env var
        config = ArtifactStoreConfiguration.from_properties({"backend": "memory"})

        assert config.backend == "memory"

    def test_from_properties_handles_invalid_backend_from_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test validation error when environment variable has invalid backend."""
        for var in ARTIFACT_STORE_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("ARTIFACT_STORE_BACKEND", "invalid_backend")

        try:
            ArtifactStoreConfiguration.from_properties({})
            assert False, (
                "Should have raised ValidationError for invalid backend from env"
            )
        except ValidationError as e:
            error_msg = str(e).lower()
            assert "backend" in error_msg or "memory" in error_msg
