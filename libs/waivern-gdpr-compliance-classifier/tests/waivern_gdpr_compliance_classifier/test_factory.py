"""Unit tests for GDPRComplianceClassifierFactory."""

import pytest
from waivern_core.services.container import ServiceContainer

from waivern_gdpr_compliance_classifier import (
    GDPRComplianceClassifierFactory,
)


@pytest.fixture
def factory() -> GDPRComplianceClassifierFactory:
    """Create a factory instance."""
    container = ServiceContainer()
    return GDPRComplianceClassifierFactory(container)


class TestGDPRComplianceClassifierFactory:
    """Tests for GDPRComplianceClassifierFactory."""

    def test_can_create_returns_false_for_invalid_ruleset(
        self, factory: GDPRComplianceClassifierFactory
    ) -> None:
        """Test can_create returns False for non-existent ruleset."""
        config = {"ruleset": "local/nonexistent_ruleset/1.0.0"}
        assert factory.can_create(config) is False
