"""Tests for artifact store configuration classes."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from waivern_artifact_store.configuration import (
    ArtifactStoreConfiguration,
    FilesystemStoreConfig,
    MemoryStoreConfig,
    RemoteStoreConfig,
)
from waivern_artifact_store.filesystem import LocalFilesystemStore
from waivern_artifact_store.in_memory import AsyncInMemoryStore

# =============================================================================
# Discriminated Union Tests (type-based config selection)
# =============================================================================


class TestArtifactStoreConfigurationDiscriminatedUnion:
    """Test that discriminated union correctly selects config class based on type."""

    def test_memory_type_returns_memory_store_config(self) -> None:
        config = ArtifactStoreConfiguration.model_validate({"type": "memory"})

        assert isinstance(config.root, MemoryStoreConfig)

    def test_filesystem_type_returns_filesystem_store_config(self) -> None:
        config = ArtifactStoreConfiguration.model_validate({"type": "filesystem"})

        assert isinstance(config.root, FilesystemStoreConfig)

    def test_remote_type_returns_remote_store_config(self) -> None:
        config = ArtifactStoreConfiguration.model_validate(
            {"type": "remote", "endpoint_url": "https://example.com"}
        )

        assert isinstance(config.root, RemoteStoreConfig)

    def test_invalid_type_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ArtifactStoreConfiguration.model_validate({"type": "invalid"})

    def test_create_store_delegates_to_inner_config(self) -> None:
        config = ArtifactStoreConfiguration.model_validate({"type": "memory"})

        store = config.create_store()

        assert isinstance(store, AsyncInMemoryStore)


# =============================================================================
# from_properties() Tests (environment variable support)
# =============================================================================


ENV_VARS = [
    "WAIVERN_STORE_TYPE",
    "WAIVERN_STORE_PATH",
    "WAIVERN_STORE_URL",
    "WAIVERN_STORE_API_KEY",
]


class TestArtifactStoreConfigurationFromProperties:
    """Test from_properties() factory method with env var support."""

    @pytest.fixture(autouse=True)
    def clear_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clear all artifact store env vars before each test."""
        for var in ENV_VARS:
            monkeypatch.delenv(var, raising=False)

    def test_from_properties_returns_memory_config_by_default(self) -> None:
        """Default to memory store when no properties or env vars."""
        config = ArtifactStoreConfiguration.from_properties({})

        assert isinstance(config.root, MemoryStoreConfig)

    def test_from_properties_reads_store_type_from_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Read store type from WAIVERN_STORE_TYPE env var."""
        monkeypatch.setenv("WAIVERN_STORE_TYPE", "filesystem")

        config = ArtifactStoreConfiguration.from_properties({})

        assert isinstance(config.root, FilesystemStoreConfig)

    def test_from_properties_reads_store_path_from_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Read base_path from WAIVERN_STORE_PATH env var."""
        monkeypatch.setenv("WAIVERN_STORE_TYPE", "filesystem")
        monkeypatch.setenv("WAIVERN_STORE_PATH", "/custom/path")

        config = ArtifactStoreConfiguration.from_properties({})

        assert isinstance(config.root, FilesystemStoreConfig)
        assert config.root.base_path == Path("/custom/path")

    def test_from_properties_properties_override_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Properties take priority over environment variables."""
        monkeypatch.setenv("WAIVERN_STORE_TYPE", "filesystem")
        monkeypatch.setenv("WAIVERN_STORE_PATH", "/env/path")

        config = ArtifactStoreConfiguration.from_properties(
            {
                "type": "filesystem",
                "base_path": "/explicit/path",
            }
        )

        assert isinstance(config.root, FilesystemStoreConfig)
        assert config.root.base_path == Path("/explicit/path")

    def test_from_properties_raises_for_invalid_type_from_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raise ValidationError for invalid type from env var."""
        monkeypatch.setenv("WAIVERN_STORE_TYPE", "invalid_backend")

        with pytest.raises(ValidationError):
            ArtifactStoreConfiguration.from_properties({})


# =============================================================================
# MemoryStoreConfig Tests (in-memory store for testing)
# =============================================================================


class TestMemoryStoreConfig:
    """Test MemoryStoreConfig behaviour."""

    def test_create_store_returns_async_in_memory_store(self) -> None:
        config = MemoryStoreConfig()

        store = config.create_store()

        assert isinstance(store, AsyncInMemoryStore)


# =============================================================================
# FilesystemStoreConfig Tests (local filesystem store)
# =============================================================================


class TestFilesystemStoreConfig:
    """Test FilesystemStoreConfig behaviour."""

    def test_base_path_defaults_to_waivern(self) -> None:
        config = FilesystemStoreConfig()

        assert config.base_path == Path(".waivern")

    def test_create_store_returns_local_filesystem_store(self) -> None:
        config = FilesystemStoreConfig()

        store = config.create_store()

        assert isinstance(store, LocalFilesystemStore)
        assert store.base_path == Path(".waivern")


# =============================================================================
# RemoteStoreConfig Tests (remote HTTP store - not yet implemented)
# =============================================================================


class TestRemoteStoreConfig:
    """Test RemoteStoreConfig behaviour."""

    def test_endpoint_url_is_required(self) -> None:
        with pytest.raises(ValidationError, match="endpoint_url"):
            RemoteStoreConfig()  # type: ignore[call-arg]

    def test_create_store_raises_not_implemented(self) -> None:
        config = RemoteStoreConfig(endpoint_url="https://example.com")

        with pytest.raises(NotImplementedError, match="RemoteHttpArtifactStore"):
            config.create_store()
