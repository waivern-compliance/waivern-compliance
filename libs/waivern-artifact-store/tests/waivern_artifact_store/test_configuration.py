"""Tests for artifact store configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from waivern_artifact_store.configuration import ArtifactStoreConfiguration

ARTIFACT_STORE_ENV_VARS = ["ARTIFACT_STORE_BACKEND"]


class TestArtifactStoreConfiguration:
    """Test ArtifactStoreConfiguration class."""

    def test_configuration_can_be_instantiated_with_valid_backend(self) -> None:
        """Test basic instantiation with valid backend."""
        config = ArtifactStoreConfiguration(backend="memory")

        assert config.backend == "memory"

    def test_configuration_uses_default_backend_when_not_specified(self) -> None:
        """Test default backend is 'memory' when not specified."""
        config = ArtifactStoreConfiguration()

        assert config.backend == "memory"

    def test_from_properties_creates_configuration_from_valid_dictionary(self) -> None:
        """Test from_properties() factory method with explicit properties."""
        properties = {"backend": "memory"}
        config = ArtifactStoreConfiguration.from_properties(properties)

        assert isinstance(config, ArtifactStoreConfiguration)
        assert config.backend == "memory"

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
        """Test that explicit properties override environment."""
        for var in ARTIFACT_STORE_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("ARTIFACT_STORE_BACKEND", "memory")

        # Explicit property should override environment
        properties = {"backend": "memory"}
        config = ArtifactStoreConfiguration.from_properties(properties)

        assert config.backend == "memory"

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

    def test_backend_is_case_insensitive(self) -> None:
        """Test backend value is normalised to lowercase."""
        config = ArtifactStoreConfiguration(backend="MEMORY")

        assert config.backend == "memory"

    def test_configuration_is_immutable_inherits_from_base(self) -> None:
        """Test frozen behaviour inherited correctly."""
        config = ArtifactStoreConfiguration(backend="memory")

        # Verify configuration is instance of BaseServiceConfiguration
        from waivern_core.services import BaseServiceConfiguration

        assert isinstance(config, BaseServiceConfiguration)

        # Attempt to modify backend (should raise ValidationError)
        try:
            config.backend = "redis"  # type: ignore[misc]
            assert False, (
                "Should have raised ValidationError for modifying frozen model"
            )
        except ValidationError as e:
            error_msg = str(e).lower()
            assert "frozen" in error_msg or "immutable" in error_msg

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
