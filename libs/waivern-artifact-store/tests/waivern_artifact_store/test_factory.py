"""Tests for artifact store factory."""

from __future__ import annotations

from pathlib import Path

import pytest

from waivern_artifact_store.configuration import ArtifactStoreConfiguration
from waivern_artifact_store.factory import ArtifactStoreFactory
from waivern_artifact_store.persistent.filesystem import LocalFilesystemStore
from waivern_artifact_store.persistent.in_memory import AsyncInMemoryStore

ENV_VARS = [
    "WAIVERN_STORE_TYPE",
    "WAIVERN_STORE_PATH",
    "WAIVERN_STORE_URL",
    "WAIVERN_STORE_API_KEY",
]

# =============================================================================
# Factory Tests (creation, configuration priority)
# =============================================================================


class TestArtifactStoreFactory:
    """Test ArtifactStoreFactory."""

    @pytest.fixture(autouse=True)
    def clear_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clear all artifact store env vars before each test."""
        for var in ENV_VARS:
            monkeypatch.delenv(var, raising=False)

    # -------------------------------------------------------------------------
    # Store Creation (explicit config)
    # -------------------------------------------------------------------------

    def test_factory_creates_memory_store_with_explicit_config(self) -> None:
        """Factory creates AsyncInMemoryStore with explicit memory config."""
        config = ArtifactStoreConfiguration.model_validate({"type": "memory"})
        factory = ArtifactStoreFactory(config)

        assert factory.can_create() is True
        store = factory.create()

        assert store is not None
        assert isinstance(store, AsyncInMemoryStore)

    def test_factory_creates_filesystem_store_with_explicit_config(
        self, tmp_path: Path
    ) -> None:
        """Factory creates LocalFilesystemStore with explicit filesystem config."""
        config = ArtifactStoreConfiguration.model_validate(
            {
                "type": "filesystem",
                "base_path": str(tmp_path),
            }
        )
        factory = ArtifactStoreFactory(config)

        assert factory.can_create() is True
        store = factory.create()

        assert store is not None
        assert isinstance(store, LocalFilesystemStore)
        assert store.base_path == tmp_path

    # -------------------------------------------------------------------------
    # Store Creation (environment / defaults)
    # -------------------------------------------------------------------------

    def test_factory_creates_memory_store_with_default(self) -> None:
        """Factory creates AsyncInMemoryStore when no config or env vars."""
        factory = ArtifactStoreFactory()

        assert factory.can_create() is True
        store = factory.create()

        assert store is not None
        assert isinstance(store, AsyncInMemoryStore)

    def test_factory_creates_filesystem_store_from_environment(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Factory creates LocalFilesystemStore from environment variables."""
        monkeypatch.setenv("WAIVERN_STORE_TYPE", "filesystem")
        monkeypatch.setenv("WAIVERN_STORE_PATH", str(tmp_path))

        factory = ArtifactStoreFactory()

        assert factory.can_create() is True
        store = factory.create()

        assert store is not None
        assert isinstance(store, LocalFilesystemStore)
        assert store.base_path == tmp_path

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    def test_factory_returns_none_for_invalid_type(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Factory returns None for invalid store type in env vars."""
        monkeypatch.setenv("WAIVERN_STORE_TYPE", "invalid_backend")
        factory = ArtifactStoreFactory()

        assert factory.can_create() is False
        assert factory.create() is None

    # -------------------------------------------------------------------------
    # Configuration Priority
    # -------------------------------------------------------------------------

    def test_explicit_config_overrides_environment(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Explicit config takes precedence over environment variables."""
        # Set env to filesystem
        monkeypatch.setenv("WAIVERN_STORE_TYPE", "filesystem")
        monkeypatch.setenv("WAIVERN_STORE_PATH", str(tmp_path))

        # But provide explicit memory config
        config = ArtifactStoreConfiguration.model_validate({"type": "memory"})
        factory = ArtifactStoreFactory(config)

        assert factory.can_create() is True
        store = factory.create()

        # Should use explicit config (memory), not env (filesystem)
        assert isinstance(store, AsyncInMemoryStore)
