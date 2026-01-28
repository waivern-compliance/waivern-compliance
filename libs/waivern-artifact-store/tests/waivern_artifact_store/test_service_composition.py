"""Service composition tests for ArtifactStore with ServiceContainer.

Tests internal component composition: ServiceContainer, ArtifactStoreFactory, and
ArtifactStoreConfiguration working together. These are NOT external integration tests
(no @pytest.mark.integration) as they don't require external services - they test
internal DI flow and should run with regular unit tests.
"""

from __future__ import annotations

from waivern_core.services import ServiceContainer, ServiceDescriptor

from waivern_artifact_store.base import ArtifactStore
from waivern_artifact_store.configuration import ArtifactStoreConfiguration
from waivern_artifact_store.factory import ArtifactStoreFactory
from waivern_artifact_store.in_memory import InMemoryArtifactStore

# =============================================================================
# Service Composition Tests (singleton behaviour)
# =============================================================================


class TestArtifactStoreServiceComposition:
    """Service composition tests for ArtifactStore with ServiceContainer."""

    # -------------------------------------------------------------------------
    # Singleton Behaviour
    # -------------------------------------------------------------------------

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
