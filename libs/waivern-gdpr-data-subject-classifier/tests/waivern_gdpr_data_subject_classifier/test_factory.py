"""Unit tests for GDPRDataSubjectClassifierFactory."""

from waivern_core.services.container import ServiceContainer

from waivern_gdpr_data_subject_classifier.factory import (
    GDPRDataSubjectClassifierFactory,
)


class TestGDPRDataSubjectClassifierFactory:
    """Test suite for GDPRDataSubjectClassifierFactory."""

    def test_can_create_returns_false_for_invalid_config(self) -> None:
        """Test that can_create returns False for invalid configuration."""
        container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(container)

        # Invalid: ruleset should be a string, not an int
        invalid_config = {"ruleset": 123}

        assert factory.can_create(invalid_config) is False

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        """Test that can_create returns False when ruleset doesn't exist."""
        container = ServiceContainer()
        factory = GDPRDataSubjectClassifierFactory(container)

        config_with_nonexistent_ruleset = {"ruleset": "local/nonexistent/1.0.0"}

        result = factory.can_create(config_with_nonexistent_ruleset)

        assert result is False
