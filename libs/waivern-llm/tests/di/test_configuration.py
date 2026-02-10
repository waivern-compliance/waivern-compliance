"""Tests for LLM service configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

from pydantic import ValidationError

from waivern_llm.di.configuration import LLMServiceConfiguration


class TestLLMServiceConfiguration:
    """Test LLMServiceConfiguration class."""

    def test_configuration_can_be_instantiated_with_valid_provider_and_api_key(
        self,
    ) -> None:
        """Test basic instantiation with required fields."""
        # Create configuration with required fields
        config = LLMServiceConfiguration(provider="anthropic", api_key="sk-test-key")

        # Verify fields are set correctly
        assert config.provider == "anthropic"
        assert config.api_key == "sk-test-key"
        assert config.model is None  # Optional field defaults to None

    def test_from_properties_creates_configuration_from_valid_dictionary(self) -> None:
        """Test from_properties() factory method with explicit properties."""
        # Create configuration from properties dictionary
        properties = {
            "provider": "openai",
            "api_key": "sk-openai-test",
            "model": "gpt-4-turbo",
        }
        config = LLMServiceConfiguration.from_properties(properties)

        # Verify configuration was created correctly
        assert isinstance(config, LLMServiceConfiguration)
        assert config.provider == "openai"
        assert config.api_key == "sk-openai-test"
        assert config.model == "gpt-4-turbo"

    def test_from_properties_falls_back_to_environment_variables_when_properties_empty(
        self,
    ) -> None:
        """Test environment fallback when no properties provided."""
        # Mock environment variables
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "google",
                "GOOGLE_API_KEY": "google-test-key",
                "GOOGLE_MODEL": "gemini-pro-vision",
            },
            clear=True,
        ):
            # Create configuration from empty properties (should read from env)
            config = LLMServiceConfiguration.from_properties({})

            # Verify environment variables were used
            assert config.provider == "google"
            assert config.api_key == "google-test-key"
            assert config.model == "gemini-pro-vision"

    def test_from_properties_prioritises_properties_over_environment_variables(
        self,
    ) -> None:
        """Test that explicit properties override environment."""
        # Mock environment variables
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "env-openai-key",
                "OPENAI_MODEL": "gpt-3.5-turbo",
            },
            clear=True,
        ):
            # Create configuration with explicit properties (should override env)
            properties = {
                "provider": "anthropic",
                "api_key": "explicit-anthropic-key",
                "model": "claude-3-opus",
            }
            config = LLMServiceConfiguration.from_properties(properties)

            # Verify explicit properties took precedence over environment
            assert config.provider == "anthropic"
            assert config.api_key == "explicit-anthropic-key"
            assert config.model == "claude-3-opus"

    def test_validation_rejects_unsupported_provider(self) -> None:
        """Test only anthropic/openai/google accepted."""
        # Attempt to create configuration with unsupported provider
        try:
            LLMServiceConfiguration(provider="invalid_provider", api_key="test-key")
            assert False, "Should have raised ValidationError for unsupported provider"
        except ValidationError as e:
            # Verify error message mentions the invalid provider
            error_msg = str(e).lower()
            assert (
                "provider" in error_msg
                or "invalid" in error_msg
                or "anthropic" in error_msg
            )

    def test_validation_rejects_empty_api_key(self) -> None:
        """Test API key cannot be empty/whitespace."""
        # Test with empty string
        try:
            LLMServiceConfiguration(provider="anthropic", api_key="")
            assert False, "Should have raised ValidationError for empty API key"
        except ValidationError as e:
            error_msg = str(e).lower()
            assert "api_key" in error_msg or "empty" in error_msg

        # Test with whitespace only
        try:
            LLMServiceConfiguration(provider="anthropic", api_key="   ")
            assert False, "Should have raised ValidationError for whitespace API key"
        except ValidationError as e:
            error_msg = str(e).lower()
            assert "api_key" in error_msg or "empty" in error_msg

    def test_model_field_is_optional_with_provider_specific_defaults(self) -> None:
        """Test model has sensible defaults per provider."""
        # Test Anthropic default
        config_anthropic = LLMServiceConfiguration(
            provider="anthropic", api_key="test-key"
        )
        assert config_anthropic.model is None
        assert config_anthropic.get_default_model() == "claude-sonnet-4-5-20250929"

        # Test OpenAI default
        config_openai = LLMServiceConfiguration(provider="openai", api_key="test-key")
        assert config_openai.model is None
        assert config_openai.get_default_model() == "gpt-4"

        # Test Google default
        config_google = LLMServiceConfiguration(provider="google", api_key="test-key")
        assert config_google.model is None
        assert config_google.get_default_model() == "gemini-pro"

    def test_model_field_can_be_explicitly_overridden(self) -> None:
        """Test explicit model overrides default."""
        # Test Anthropic with explicit model
        config_anthropic = LLMServiceConfiguration(
            provider="anthropic",
            api_key="test-key",
            model="claude-3-opus",
        )
        assert config_anthropic.model == "claude-3-opus"
        assert config_anthropic.get_default_model() == "claude-3-opus"

        # Test OpenAI with explicit model
        config_openai = LLMServiceConfiguration(
            provider="openai",
            api_key="test-key",
            model="gpt-4-turbo",
        )
        assert config_openai.model == "gpt-4-turbo"
        assert config_openai.get_default_model() == "gpt-4-turbo"

        # Test Google with explicit model
        config_google = LLMServiceConfiguration(
            provider="google",
            api_key="test-key",
            model="gemini-pro-vision",
        )
        assert config_google.model == "gemini-pro-vision"
        assert config_google.get_default_model() == "gemini-pro-vision"

    def test_configuration_is_immutable_inherits_from_base(self) -> None:
        """Test frozen behavior inherited correctly."""
        # Create configuration
        config = LLMServiceConfiguration(
            provider="anthropic",
            api_key="test-key",
            model="claude-3-opus",
        )

        # Verify configuration is instance of BaseServiceConfiguration
        from waivern_core.services import BaseServiceConfiguration

        assert isinstance(config, BaseServiceConfiguration)

        # Attempt to modify provider (should raise ValidationError)
        try:
            config.provider = "openai"  # type: ignore[misc]
            assert False, (
                "Should have raised ValidationError for modifying frozen model"
            )
        except ValidationError as e:
            error_msg = str(e).lower()
            assert "frozen" in error_msg or "immutable" in error_msg

        # Attempt to modify api_key (should raise ValidationError)
        try:
            config.api_key = "new-key"  # type: ignore[misc]
            assert False, (
                "Should have raised ValidationError for modifying frozen model"
            )
        except ValidationError as e:
            error_msg = str(e).lower()
            assert "frozen" in error_msg or "immutable" in error_msg

        # Attempt to modify model (should raise ValidationError)
        try:
            config.model = "new-model"  # type: ignore[misc]
            assert False, (
                "Should have raised ValidationError for modifying frozen model"
            )
        except ValidationError as e:
            error_msg = str(e).lower()
            assert "frozen" in error_msg or "immutable" in error_msg

    def test_from_properties_reads_provider_specific_api_key_from_environment(
        self,
    ) -> None:
        """Test correct env var mapping (ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY)."""
        # Test Anthropic API key mapping
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "anthropic-key-123"},
            clear=True,
        ):
            config = LLMServiceConfiguration.from_properties({})
            assert config.provider == "anthropic"
            assert config.api_key == "anthropic-key-123"

        # Test OpenAI API key mapping
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "openai-key-456"},
            clear=True,
        ):
            config = LLMServiceConfiguration.from_properties({})
            assert config.provider == "openai"
            assert config.api_key == "openai-key-456"

        # Test Google API key mapping
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "google", "GOOGLE_API_KEY": "google-key-789"},
            clear=True,
        ):
            config = LLMServiceConfiguration.from_properties({})
            assert config.provider == "google"
            assert config.api_key == "google-key-789"

        # Test that wrong env var is NOT used (e.g., OPENAI_API_KEY when provider is anthropic)
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "OPENAI_API_KEY": "wrong-key",  # Wrong provider's key
                "ANTHROPIC_API_KEY": "correct-key",
            },
            clear=True,
        ):
            config = LLMServiceConfiguration.from_properties({})
            assert config.provider == "anthropic"
            assert config.api_key == "correct-key"  # Should use correct provider key

    def test_from_properties_reads_base_url_from_environment_only_for_openai_provider(
        self,
    ) -> None:
        """Test OPENAI_BASE_URL is read for openai provider but ignored for others."""
        # When provider is openai, OPENAI_BASE_URL should be read
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "test-key",
                "OPENAI_BASE_URL": "http://localhost:1234/v1",
            },
            clear=True,
        ):
            config = LLMServiceConfiguration.from_properties({})
            assert config.provider == "openai"
            assert config.base_url == "http://localhost:1234/v1"

        # When provider is anthropic, OPENAI_BASE_URL should be ignored
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-key",
                "OPENAI_BASE_URL": "http://localhost:1234/v1",  # Should be ignored
            },
            clear=True,
        ):
            config = LLMServiceConfiguration.from_properties({})
            assert config.provider == "anthropic"
            assert config.base_url is None

    def test_batch_mode_defaults_to_false(self) -> None:
        """Test batch_mode field defaults to False when not specified."""
        config = LLMServiceConfiguration(provider="anthropic", api_key="test-key")

        assert config.batch_mode is False

    def test_from_properties_reads_batch_mode_from_environment_with_truthy_string_parsing(
        self,
    ) -> None:
        """Test WAIVERN_LLM_BATCH_MODE env var parsed as truthy string."""
        # Truthy values should activate batch mode
        for truthy_value in ("true", "1", "yes", "TRUE", "Yes"):
            with patch.dict(
                os.environ,
                {
                    "LLM_PROVIDER": "anthropic",
                    "ANTHROPIC_API_KEY": "test-key",
                    "WAIVERN_LLM_BATCH_MODE": truthy_value,
                },
                clear=True,
            ):
                config = LLMServiceConfiguration.from_properties({})
                assert config.batch_mode is True, (
                    f"Expected batch_mode=True for env value {truthy_value!r}"
                )

        # Non-truthy values should not activate batch mode
        for falsy_value in ("false", "0", "no", "random"):
            with patch.dict(
                os.environ,
                {
                    "LLM_PROVIDER": "anthropic",
                    "ANTHROPIC_API_KEY": "test-key",
                    "WAIVERN_LLM_BATCH_MODE": falsy_value,
                },
                clear=True,
            ):
                config = LLMServiceConfiguration.from_properties({})
                assert config.batch_mode is False, (
                    f"Expected batch_mode=False for env value {falsy_value!r}"
                )

        # Absent env var should default to False
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "test-key",
            },
            clear=True,
        ):
            config = LLMServiceConfiguration.from_properties({})
            assert config.batch_mode is False
