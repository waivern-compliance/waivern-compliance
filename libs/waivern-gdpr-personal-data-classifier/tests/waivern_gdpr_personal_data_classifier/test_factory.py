"""Unit tests for GDPRPersonalDataClassifierFactory."""

from waivern_core.services.container import ServiceContainer

from waivern_gdpr_personal_data_classifier.classifier import GDPRPersonalDataClassifier
from waivern_gdpr_personal_data_classifier.factory import (
    GDPRPersonalDataClassifierFactory,
)


class TestGDPRPersonalDataClassifierFactory:
    """Test suite for GDPRPersonalDataClassifierFactory."""

    def test_factory_creates_classifier_instance(self) -> None:
        """Test that factory creates a GDPRPersonalDataClassifier instance."""
        container = ServiceContainer()
        factory = GDPRPersonalDataClassifierFactory(container)

        classifier = factory.create({})

        assert isinstance(classifier, GDPRPersonalDataClassifier)

    def test_factory_component_class_returns_classifier_type(self) -> None:
        """Test that component_class property returns GDPRPersonalDataClassifier."""
        container = ServiceContainer()
        factory = GDPRPersonalDataClassifierFactory(container)

        assert factory.component_class is GDPRPersonalDataClassifier

    def test_factory_can_create_returns_true_for_empty_config(self) -> None:
        """Test that can_create returns True for empty config."""
        container = ServiceContainer()
        factory = GDPRPersonalDataClassifierFactory(container)

        assert factory.can_create({}) is True

    def test_factory_can_create_returns_true_for_any_valid_config(self) -> None:
        """Test that can_create returns True for any valid configuration."""
        container = ServiceContainer()
        factory = GDPRPersonalDataClassifierFactory(container)

        # Classifier ignores config, so any dict should work
        assert factory.can_create({"some_key": "some_value"}) is True

    def test_factory_get_service_dependencies_returns_empty_dict(self) -> None:
        """Test that get_service_dependencies returns empty dict (no dependencies)."""
        container = ServiceContainer()
        factory = GDPRPersonalDataClassifierFactory(container)

        assert factory.get_service_dependencies() == {}
