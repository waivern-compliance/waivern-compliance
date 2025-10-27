"""Tests for base service configuration."""

from __future__ import annotations

from waivern_core.services import BaseServiceConfiguration


class TestBaseServiceConfiguration:
    """Test BaseServiceConfiguration base class."""

    def test_base_configuration_can_be_instantiated_directly_for_testing(self) -> None:
        """Test that BaseServiceConfiguration can be used directly."""
        # BaseServiceConfiguration should be instantiable with no fields
        config = BaseServiceConfiguration()

        # Verify it's the correct type
        assert isinstance(config, BaseServiceConfiguration)

    def test_configuration_is_immutable_frozen(self) -> None:
        """Test that configuration fields cannot be modified after creation."""
        from pydantic import ValidationError

        # Create a test subclass with a field to modify
        class TestServiceConfig(BaseServiceConfiguration):
            name: str

        # Create instance
        config = TestServiceConfig(name="original")
        assert config.name == "original"

        # Attempt to modify the field - should raise ValidationError (frozen instance)
        try:
            config.name = "modified"  # type: ignore[misc]
            assert False, "Should have raised ValidationError for frozen instance"
        except ValidationError as e:
            # Pydantic raises ValidationError with frozen/immutable message
            assert "frozen" in str(e).lower() or "immutable" in str(e).lower()

    def test_from_properties_creates_configuration_from_valid_dictionary(self) -> None:
        """Test from_properties() factory method with valid dictionary."""

        # Create a test subclass with fields
        class TestServiceConfig(BaseServiceConfiguration):
            name: str
            port: int

        # Create configuration from properties dictionary
        properties = {"name": "test-service", "port": 8080}
        config = TestServiceConfig.from_properties(properties)

        # Verify configuration was created correctly
        assert isinstance(config, TestServiceConfig)
        assert config.name == "test-service"
        assert config.port == 8080

    def test_from_properties_rejects_extra_fields_not_in_model(self) -> None:
        """Test from_properties() rejects unknown/extra fields."""
        from pydantic import ValidationError

        # Create a test subclass with specific fields
        class TestServiceConfig(BaseServiceConfiguration):
            name: str
            port: int

        # Attempt to create configuration with extra/unknown field
        properties = {"name": "test-service", "port": 8080, "unknown_field": "value"}

        try:
            TestServiceConfig.from_properties(properties)
            assert False, "Should have raised ValidationError for extra field"
        except ValidationError as e:
            # Pydantic raises ValidationError with extra fields forbidden message
            error_msg = str(e).lower()
            assert (
                "extra" in error_msg
                or "forbidden" in error_msg
                or "unexpected" in error_msg
            )
