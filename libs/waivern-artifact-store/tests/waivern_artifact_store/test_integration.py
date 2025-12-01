"""Integration tests for ArtifactStore ServiceContainer integration.

Tests the integration of ServiceContainer, ArtifactStoreFactory, and
ArtifactStoreConfiguration working together.
"""

from __future__ import annotations

from waivern_core.services import ServiceContainer, ServiceDescriptor

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.configuration import ArtifactStoreConfiguration
from waivern_artifact_store.factory import ArtifactStoreFactory
from waivern_artifact_store.in_memory import InMemoryArtifactStore


class TestArtifactStoreServiceContainerIntegration:
    """Integration tests for ArtifactStore with ServiceContainer."""

    def test_singleton_behavior_returns_same_instance(self) -> None:
        """Test singleton lifetime returns same instance across multiple get_service calls."""
        config = ArtifactStoreConfiguration(backend="memory")
        factory = ArtifactStoreFactory(config)

        container = ServiceContainer()
        container.register(ServiceDescriptor(ArtifactStore, factory, "singleton"))

        # Get service twice
        store_first = container.get_service(ArtifactStore)
        store_second = container.get_service(ArtifactStore)

        # Verify same instance returned
        assert store_first is not None
        assert store_second is not None
        assert store_first is store_second
        assert isinstance(store_first, InMemoryArtifactStore)

    def test_multiple_containers_have_independent_instances(self) -> None:
        """Test each ServiceContainer maintains its own ArtifactStore instance.

        Note: This tests ServiceContainer behavior (per-instance singleton isolation),
        not ArtifactStore-specific logic. Kept as integration smoke test.
        """
        config = ArtifactStoreConfiguration(backend="memory")

        # Create two separate containers
        container1 = ServiceContainer()
        container1.register(
            ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(config))
        )

        container2 = ServiceContainer()
        container2.register(
            ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(config))
        )

        # Get stores from each container
        store1 = container1.get_service(ArtifactStore)
        store2 = container2.get_service(ArtifactStore)

        # Verify independent instances
        assert store1 is not None
        assert store2 is not None
        assert store1 is not store2

    def test_environment_variable_configuration_respected(self, monkeypatch) -> None:
        """Test factory respects ARTIFACT_STORE_BACKEND environment variable."""
        # Test 1: Invalid env var -> should fail (proves env is read)
        monkeypatch.setenv("ARTIFACT_STORE_BACKEND", "redis")
        factory = ArtifactStoreFactory()
        assert factory.create() is None

        # Test 2: Valid env var -> should succeed
        monkeypatch.setenv("ARTIFACT_STORE_BACKEND", "memory")
        factory = ArtifactStoreFactory()

        container = ServiceContainer()
        container.register(ServiceDescriptor(ArtifactStore, factory, "singleton"))

        store = container.get_service(ArtifactStore)

        assert store is not None
        assert isinstance(store, InMemoryArtifactStore)

    def test_explicit_configuration_overrides_environment(self, monkeypatch) -> None:
        """Test explicit configuration takes precedence over environment variables."""
        # Set environment to invalid value
        monkeypatch.setenv("ARTIFACT_STORE_BACKEND", "invalid_backend")

        # Explicit config should override
        config = ArtifactStoreConfiguration(backend="memory")
        factory = ArtifactStoreFactory(config)

        container = ServiceContainer()
        container.register(ServiceDescriptor(ArtifactStore, factory, "singleton"))

        store = container.get_service(ArtifactStore)

        # Should succeed with explicit config despite invalid env var
        assert store is not None
        assert isinstance(store, InMemoryArtifactStore)
