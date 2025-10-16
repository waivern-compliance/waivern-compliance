"""Tests for LLMServiceManager utility class.

This module tests the public API of LLMServiceManager, focusing on:
- Service lifecycle management
- Availability checking
- Error handling scenarios
- Configuration-based behaviour ✔️
"""

from unittest.mock import Mock, patch

from waivern_llm import AnthropicLLMService, LLMServiceError

from waivern_community.analysers.utilities.llm_service_manager import LLMServiceManager


class TestLLMServiceManagerInitialisation:
    """Test LLMServiceManager initialisation behaviour."""

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_initialise_with_validation_enabled_by_default(self, mock_factory):
        """Test that LLMServiceManager initialises with validation enabled by default."""
        service_mock = Mock(spec=AnthropicLLMService)
        mock_factory.return_value = service_mock

        manager = LLMServiceManager()

        # Test behaviour: should attempt to create service when enabled
        result = manager.llm_service is not None
        assert result is True

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_initialise_with_validation_explicitly_enabled(self, mock_factory):
        """Test that LLMServiceManager initialises with validation explicitly enabled."""
        service_mock = Mock(spec=AnthropicLLMService)
        mock_factory.return_value = service_mock

        manager = LLMServiceManager(enable_llm_validation=True)

        # Test behaviour: should attempt to create service when enabled
        result = manager.llm_service is not None
        assert result is True

    def test_initialise_with_validation_disabled(self):
        """Test that LLMServiceManager initialises with validation disabled."""
        manager = LLMServiceManager(enable_llm_validation=False)

        # Test behaviour: should not attempt to create service when disabled
        result = manager.llm_service is not None
        assert result is False


class TestLLMServiceProperty:
    """Test the llm_service property behaviour."""

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_llm_service_creates_service_when_validation_enabled(self, mock_factory):
        """Test that llm_service property creates service when validation is enabled."""
        expected_service = Mock(spec=AnthropicLLMService)
        mock_factory.return_value = expected_service

        manager = LLMServiceManager(enable_llm_validation=True)

        result = manager.llm_service

        assert result is expected_service
        mock_factory.assert_called_once()

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_llm_service_returns_cached_service_on_subsequent_calls(self, mock_factory):
        """Test that llm_service property returns cached service on subsequent calls."""
        expected_service = Mock(spec=AnthropicLLMService)
        mock_factory.return_value = expected_service

        manager = LLMServiceManager(enable_llm_validation=True)

        first_result = manager.llm_service
        second_result = manager.llm_service

        assert first_result is expected_service
        assert second_result is expected_service
        assert first_result is second_result
        mock_factory.assert_called_once()

    def test_llm_service_returns_none_when_validation_disabled(self):
        """Test that llm_service property returns None when validation is disabled."""
        manager = LLMServiceManager(enable_llm_validation=False)

        result = manager.llm_service

        assert result is None

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_llm_service_handles_service_creation_failure(self, mock_factory):
        """Test that llm_service property handles service creation failures gracefully."""
        expected_error = LLMServiceError("Mock service creation failed")
        mock_factory.side_effect = expected_error

        manager = LLMServiceManager(enable_llm_validation=True)

        result = manager.llm_service

        assert result is None
        # Test behaviour: service should become unavailable after failure
        assert manager.llm_service is None
        mock_factory.assert_called_once()

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_llm_service_does_not_retry_after_failure(self, mock_factory):
        """Test that llm_service property does not retry service creation after failure."""
        expected_error = LLMServiceError("Mock service creation failed")
        mock_factory.side_effect = expected_error

        manager = LLMServiceManager(enable_llm_validation=True)

        first_result = manager.llm_service
        second_result = manager.llm_service

        assert first_result is None
        assert second_result is None
        # Test behaviour: service should remain unavailable after failure
        assert manager.llm_service is None
        mock_factory.assert_called_once()

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_llm_service_logs_successful_initialisation(self, mock_factory, caplog):
        """Test that llm_service property logs successful service initialisation."""
        expected_service = Mock(spec=AnthropicLLMService)
        mock_factory.return_value = expected_service

        manager = LLMServiceManager(enable_llm_validation=True)

        with caplog.at_level("INFO"):
            manager.llm_service

        assert "LLM service initialised for compliance analysis" in caplog.text

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_llm_service_logs_initialisation_failure(self, mock_factory, caplog):
        """Test that llm_service property logs service initialisation failures."""
        expected_error_message = "Mock service creation failed"
        expected_error = LLMServiceError(expected_error_message)
        mock_factory.side_effect = expected_error

        manager = LLMServiceManager(enable_llm_validation=True)

        with caplog.at_level("WARNING"):
            manager.llm_service

        assert "Failed to initialise LLM service" in caplog.text
        assert expected_error_message in caplog.text
        assert "Continuing without LLM validation" in caplog.text


class TestLLMServiceManagerEdgeCases:
    """Test edge cases and error scenarios."""

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_manager_state_after_service_failure_recovery_attempt(self, mock_factory):
        """Test manager state remains consistent after failed service creation."""
        expected_error = LLMServiceError("Mock service creation failed")
        mock_factory.side_effect = expected_error

        manager = LLMServiceManager(enable_llm_validation=True)

        # Trigger service creation failure
        first_service = manager.llm_service
        first_available = first_service is not None

        # Verify state is consistent
        second_service = manager.llm_service
        second_available = second_service is not None

        assert first_service is None
        assert first_available is False
        assert second_service is None
        assert second_available is False
        # Test behaviour consistency: both calls should give same result

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_multiple_managers_with_different_configurations(self, mock_factory):
        """Test multiple LLMServiceManager instances with different configurations."""
        service_mock = Mock(spec=AnthropicLLMService)
        mock_factory.return_value = service_mock

        enabled_manager = LLMServiceManager(enable_llm_validation=True)
        disabled_manager = LLMServiceManager(enable_llm_validation=False)

        enabled_result = enabled_manager.llm_service is not None
        disabled_result = disabled_manager.llm_service is not None

        assert enabled_result is True
        assert disabled_result is False
        assert enabled_manager.llm_service is service_mock
        assert disabled_manager.llm_service is None

    @patch(
        "waivern_community.analysers.utilities.llm_service_manager.LLMServiceFactory.create_anthropic_service"
    )
    def test_service_creation_called_only_when_needed(self, mock_factory):
        """Test that service creation is only called when actually needed."""
        service_mock = Mock(spec=AnthropicLLMService)
        mock_factory.return_value = service_mock

        # Manager with validation disabled should not call factory
        disabled_manager = LLMServiceManager(enable_llm_validation=False)
        disabled_manager.llm_service
        disabled_manager.llm_service is not None

        # Manager with validation enabled should call factory
        enabled_manager = LLMServiceManager(enable_llm_validation=True)
        enabled_manager.llm_service

        mock_factory.assert_called_once()
