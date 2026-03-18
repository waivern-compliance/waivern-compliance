"""Unit tests for GDPRServiceIntegrationClassifierFactory."""

import pytest
from waivern_core.services.container import ServiceContainer

from waivern_gdpr_service_integration_classifier import (
    GDPRServiceIntegrationClassifierFactory,
)


@pytest.fixture
def factory() -> GDPRServiceIntegrationClassifierFactory:
    """Create a factory instance."""
    container = ServiceContainer()
    return GDPRServiceIntegrationClassifierFactory(container)


class TestGDPRServiceIntegrationClassifierFactory:
    """Tests for GDPRServiceIntegrationClassifierFactory."""

    def test_can_create_returns_false_for_invalid_ruleset(
        self, factory: GDPRServiceIntegrationClassifierFactory
    ) -> None:
        """Test can_create returns False for non-existent ruleset."""
        config = {"ruleset": "local/nonexistent_ruleset/1.0.0"}
        assert factory.can_create(config) is False
