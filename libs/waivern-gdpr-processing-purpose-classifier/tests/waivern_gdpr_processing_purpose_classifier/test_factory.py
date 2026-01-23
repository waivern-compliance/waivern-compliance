"""Unit tests for GDPRProcessingPurposeClassifierFactory."""

import pytest
from waivern_core.services.container import ServiceContainer

from waivern_gdpr_processing_purpose_classifier import (
    GDPRProcessingPurposeClassifier,
    GDPRProcessingPurposeClassifierFactory,
)


@pytest.fixture
def container() -> ServiceContainer:
    """Create a service container for tests."""
    return ServiceContainer()


@pytest.fixture
def factory(container: ServiceContainer) -> GDPRProcessingPurposeClassifierFactory:
    """Create a factory instance."""
    return GDPRProcessingPurposeClassifierFactory(container)


class TestGDPRProcessingPurposeClassifierFactory:
    """Tests for GDPRProcessingPurposeClassifierFactory."""

    def test_create_with_default_config(
        self, factory: GDPRProcessingPurposeClassifierFactory
    ) -> None:
        """Test factory creates classifier with default config."""
        classifier = factory.create({})

        assert isinstance(classifier, GDPRProcessingPurposeClassifier)

    def test_create_with_custom_ruleset(
        self, factory: GDPRProcessingPurposeClassifierFactory
    ) -> None:
        """Test factory creates classifier with custom ruleset."""
        config = {"ruleset": "local/gdpr_processing_purpose_classification/1.0.0"}
        classifier = factory.create(config)

        assert isinstance(classifier, GDPRProcessingPurposeClassifier)

    def test_can_create_returns_true_for_valid_config(
        self, factory: GDPRProcessingPurposeClassifierFactory
    ) -> None:
        """Test can_create returns True for valid configuration."""
        assert factory.can_create({}) is True

    def test_can_create_returns_false_for_invalid_ruleset(
        self, factory: GDPRProcessingPurposeClassifierFactory
    ) -> None:
        """Test can_create returns False for non-existent ruleset."""
        config = {"ruleset": "local/nonexistent_ruleset/1.0.0"}
        assert factory.can_create(config) is False

    def test_component_class_returns_classifier_type(
        self, factory: GDPRProcessingPurposeClassifierFactory
    ) -> None:
        """Test component_class property returns correct type."""
        assert factory.component_class is GDPRProcessingPurposeClassifier

    def test_get_service_dependencies_returns_empty_dict(
        self, factory: GDPRProcessingPurposeClassifierFactory
    ) -> None:
        """Test that classifier has no service dependencies."""
        assert factory.get_service_dependencies() == {}
