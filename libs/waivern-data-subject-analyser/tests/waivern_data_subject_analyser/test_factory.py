"""Tests for DataSubjectAnalyserFactory."""

from unittest.mock import Mock

import pytest
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_core.services import ServiceContainer, ServiceDescriptor
from waivern_core.services.protocols import ServiceFactory
from waivern_llm import BaseLLMService

from waivern_data_subject_analyser import DataSubjectAnalyser
from waivern_data_subject_analyser.factory import (
    DataSubjectAnalyserFactory,
)


class TestDataSubjectAnalyserFactory(
    ComponentFactoryContractTests[DataSubjectAnalyser]
):
    """Contract tests for DataSubjectAnalyserFactory."""

    # Fixtures required by ComponentFactoryContractTests
    @pytest.fixture
    def factory(self) -> ComponentFactory[DataSubjectAnalyser]:
        """Create factory instance for testing."""
        container = ServiceContainer()
        llm_service = Mock(spec=BaseLLMService)
        llm_service_factory = Mock(spec=ServiceFactory)
        llm_service_factory.create.return_value = llm_service
        container.register(ServiceDescriptor(BaseLLMService, llm_service_factory))
        return DataSubjectAnalyserFactory(container)

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Create valid configuration for testing."""
        return {
            "pattern_matching": {"ruleset": "data_subjects"},
            "llm_validation": {"enable_llm_validation": False},
        }

    # Factory-specific tests
    def test_can_create_returns_false_when_llm_required_but_unavailable(self) -> None:
        """Test graceful degradation when LLM validation enabled but service unavailable."""
        container = ServiceContainer()  # No LLM service registered
        factory = DataSubjectAnalyserFactory(container)

        config_requiring_llm = {
            "pattern_matching": {"ruleset": "data_subjects"},
            "llm_validation": {"enable_llm_validation": True},
        }

        result = factory.can_create(config_requiring_llm)

        assert result is False

    def test_get_service_dependencies_declares_llm_service(self) -> None:
        """Test that factory declares BaseLLMService as dependency."""
        container = ServiceContainer()
        factory = DataSubjectAnalyserFactory(container)

        deps = factory.get_service_dependencies()

        assert "llm_service" in deps
        assert deps["llm_service"] is BaseLLMService
