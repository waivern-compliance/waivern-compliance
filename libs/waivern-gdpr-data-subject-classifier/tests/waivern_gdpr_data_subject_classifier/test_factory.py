"""Unit tests for GDPRDataSubjectClassifierFactory."""

from waivern_core.services.container import ServiceContainer

from waivern_gdpr_data_subject_classifier.classifier import GDPRDataSubjectClassifier
from waivern_gdpr_data_subject_classifier.factory import (
    GDPRDataSubjectClassifierFactory,
)


class TestGDPRDataSubjectClassifierFactory:
    """Test suite for GDPRDataSubjectClassifierFactory."""

    def test_factory_creates_classifier_instance(self) -> None:
        """Test that factory creates a GDPRDataSubjectClassifier instance."""
        container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(container)

        classifier = factory.create({})

        assert isinstance(classifier, GDPRDataSubjectClassifier)

    def test_factory_component_class_returns_classifier_type(self) -> None:
        """Test that component_class property returns GDPRDataSubjectClassifier."""
        container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(container)

        assert factory.component_class is GDPRDataSubjectClassifier

    def test_factory_can_create_returns_true_for_empty_config(self) -> None:
        """Test that can_create returns True for empty config."""
        container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(container)

        assert factory.can_create({}) is True

    def test_factory_can_create_returns_true_for_any_valid_config(self) -> None:
        """Test that can_create returns True for any valid configuration."""
        container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(container)

        # Classifier ignores config, so any dict should work
        assert factory.can_create({"some_key": "some_value"}) is True

    def test_factory_get_service_dependencies_returns_empty_dict(self) -> None:
        """Test that get_service_dependencies returns empty dict (no dependencies)."""
        container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(container)

        assert factory.get_service_dependencies() == {}
