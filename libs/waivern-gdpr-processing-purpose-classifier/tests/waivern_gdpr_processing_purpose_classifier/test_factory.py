"""Unit tests for GDPRProcessingPurposeClassifierFactory."""

import pytest
from waivern_core.services.container import ServiceContainer

from waivern_gdpr_processing_purpose_classifier import (
    GDPRProcessingPurposeClassifierFactory,
)


@pytest.fixture
def factory() -> GDPRProcessingPurposeClassifierFactory:
    """Create a factory instance."""
    container = ServiceContainer()
    return GDPRProcessingPurposeClassifierFactory(container)


class TestGDPRProcessingPurposeClassifierFactory:
    """Tests for GDPRProcessingPurposeClassifierFactory."""

    def test_can_create_returns_false_for_invalid_ruleset(
        self, factory: GDPRProcessingPurposeClassifierFactory
    ) -> None:
        """Test can_create returns False for non-existent ruleset."""
        config = {"ruleset": "local/nonexistent_ruleset/1.0.0"}
        assert factory.can_create(config) is False
