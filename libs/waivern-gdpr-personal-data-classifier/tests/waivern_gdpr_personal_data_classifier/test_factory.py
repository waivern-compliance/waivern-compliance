"""Unit tests for GDPRPersonalDataClassifierFactory."""

from waivern_core import Schema
from waivern_core.message import Message
from waivern_core.services.container import ServiceContainer

from waivern_gdpr_personal_data_classifier.factory import (
    GDPRPersonalDataClassifierFactory,
)


class TestGDPRPersonalDataClassifierFactory:
    """Test suite for GDPRPersonalDataClassifierFactory."""

    def test_factory_can_create_returns_true_for_empty_config(self) -> None:
        """Test that can_create returns True for empty config."""
        container = ServiceContainer()
        factory = GDPRPersonalDataClassifierFactory(container)

        assert factory.can_create({}) is True

    def test_factory_can_create_returns_false_for_invalid_config(self) -> None:
        """Test that can_create returns False for invalid configuration."""
        container = ServiceContainer()
        factory = GDPRPersonalDataClassifierFactory(container)

        # Invalid: ruleset should be a string, not an int
        invalid_config = {"ruleset": 123}

        assert factory.can_create(invalid_config) is False

    def test_factory_creates_classifier_with_configured_ruleset(self) -> None:
        """Test that factory creates classifier using ruleset from config."""
        container = ServiceContainer()
        factory = GDPRPersonalDataClassifierFactory(container)

        # Use the default ruleset URI (guaranteed to be registered)
        config = {"ruleset": "local/gdpr_personal_data_classification/1.0.0"}
        classifier = factory.create(config)

        # Create minimal input to verify the classifier uses the configured ruleset
        input_message = Message(
            id="test",
            content={
                "findings": [
                    {
                        "category": "email",
                        "evidence": [{"content": "test@example.com"}],
                        "matched_patterns": [
                            {"pattern": "email_pattern", "match_count": 1}
                        ],
                    }
                ]
            },
            schema=Schema("personal_data_indicator", "1.0.0"),
        )

        result = classifier.process(
            [input_message], Schema("gdpr_personal_data", "1.0.0")
        )

        # Verify the output metadata reflects the configured ruleset (version-agnostic)
        ruleset_used = result.content["analysis_metadata"]["ruleset_used"]
        assert isinstance(ruleset_used, str)
        assert ruleset_used.startswith("local/gdpr_personal_data_classification/")

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        """Test that can_create returns False when ruleset doesn't exist."""
        container = ServiceContainer()
        factory = GDPRPersonalDataClassifierFactory(container)

        config_with_nonexistent_ruleset = {"ruleset": "local/nonexistent/1.0.0"}

        result = factory.can_create(config_with_nonexistent_ruleset)

        assert result is False
