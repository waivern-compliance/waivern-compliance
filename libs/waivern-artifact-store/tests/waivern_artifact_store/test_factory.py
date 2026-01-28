"""Tests for artifact store factory."""

from __future__ import annotations

from waivern_artifact_store.configuration import ArtifactStoreConfiguration
from waivern_artifact_store.factory import ArtifactStoreFactory
from waivern_artifact_store.in_memory import InMemoryArtifactStore

# =============================================================================
# Factory Tests (creation, configuration priority)
# =============================================================================


class TestArtifactStoreFactory:
    """Test ArtifactStoreFactory."""

    # -------------------------------------------------------------------------
    # Store Creation
    # -------------------------------------------------------------------------

    def test_factory_creates_in_memory_store_with_explicit_config(self) -> None:
        """Test factory creates InMemoryArtifactStore with explicit configuration."""
        config = ArtifactStoreConfiguration(backend="memory")
        factory = ArtifactStoreFactory(config)

        assert factory.can_create() is True
        store = factory.create()

        assert store is not None
        assert isinstance(store, InMemoryArtifactStore)

    def test_factory_creates_in_memory_store_with_default(self, monkeypatch) -> None:
        """Test factory creates InMemoryArtifactStore with default backend."""
        # Ensure no env var is set
        monkeypatch.delenv("ARTIFACT_STORE_BACKEND", raising=False)
        factory = ArtifactStoreFactory()

        assert factory.can_create() is True
        store = factory.create()

        assert store is not None
        assert isinstance(store, InMemoryArtifactStore)

    def test_factory_returns_none_for_unsupported_backend(self, monkeypatch) -> None:
        """Test factory returns None for unsupported backend.

        This also proves env vars are read - if they weren't, this wouldn't fail.
        """
        monkeypatch.setenv("ARTIFACT_STORE_BACKEND", "invalid_backend")
        factory = ArtifactStoreFactory()

        assert factory.can_create() is False
        assert factory.create() is None

    # -------------------------------------------------------------------------
    # Configuration Priority
    # -------------------------------------------------------------------------

    def test_explicit_config_overrides_environment(self, monkeypatch) -> None:
        """Test explicit configuration takes precedence over environment variables."""
        monkeypatch.setenv("ARTIFACT_STORE_BACKEND", "invalid_backend")

        # Explicit config should override invalid env var
        config = ArtifactStoreConfiguration(backend="memory")
        factory = ArtifactStoreFactory(config)

        assert factory.can_create() is True
        store = factory.create()

        assert store is not None
        assert isinstance(store, InMemoryArtifactStore)
