"""Unit tests for GDPRDataCollectionClassifierFactory."""

import pytest
from waivern_core.services.container import ServiceContainer

from waivern_gdpr_data_collection_classifier import (
    GDPRDataCollectionClassifierFactory,
)


@pytest.fixture
def factory() -> GDPRDataCollectionClassifierFactory:
    """Create a factory instance."""
    container = ServiceContainer()
    return GDPRDataCollectionClassifierFactory(container)


class TestGDPRDataCollectionClassifierFactory:
    """Tests for GDPRDataCollectionClassifierFactory."""

    def test_can_create_returns_false_for_invalid_ruleset(
        self, factory: GDPRDataCollectionClassifierFactory
    ) -> None:
        """Test can_create returns False for non-existent ruleset."""
        config = {"ruleset": "local/nonexistent_ruleset/1.0.0"}
        assert factory.can_create(config) is False
