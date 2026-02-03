"""Tests for PersonalDataAnalyserFactory.

This test module uses the CONTRACT TESTING PATTERN by inheriting from
ComponentFactoryContractTests to ensure PersonalDataAnalyserFactory
correctly implements the ComponentFactory interface.

Contract tests (inherited automatically):
1. test_create_returns_component_instance
2. test_get_component_name_returns_non_empty_string
3. test_get_input_schemas_returns_list_of_schemas
4. test_get_output_schemas_returns_list_of_schemas
5. test_can_create_returns_bool_for_valid_config
6. test_get_service_dependencies_returns_dict

Factory-specific tests (added in this module):
- Graceful degradation when LLM unavailable
- Service dependency declarations
"""

from unittest.mock import Mock

import pytest
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_core.services import ServiceContainer, ServiceDescriptor
from waivern_core.services.protocols import ServiceFactory
from waivern_llm.v2 import LLMService

from waivern_personal_data_analyser import PersonalDataAnalyser
from waivern_personal_data_analyser.factory import PersonalDataAnalyserFactory


class TestPersonalDataAnalyserFactory(
    ComponentFactoryContractTests[PersonalDataAnalyser]
):
    """Test PersonalDataAnalyserFactory with contract compliance + factory-specific tests.

    Inherits 6 contract tests automatically from ComponentFactoryContractTests.
    Adds 2 factory-specific tests for PersonalDataAnalyser behavior.
    """

    # Required fixtures for contract tests

    @pytest.fixture
    def factory(self) -> ComponentFactory[PersonalDataAnalyser]:
        """Provide factory instance with mocked LLM service.

        This fixture is required by ComponentFactoryContractTests.
        """
        container = ServiceContainer()
        llm_service = Mock(spec=LLMService)
        llm_service_factory = Mock(spec=ServiceFactory)
        llm_service_factory.create.return_value = llm_service
        container.register(ServiceDescriptor(LLMService, llm_service_factory))
        return PersonalDataAnalyserFactory(container)

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide valid configuration for factory.create().

        This fixture is required by ComponentFactoryContractTests.
        Configuration includes all required fields for PersonalDataAnalyser.
        """
        return {
            "pattern_matching": {
                "ruleset": "local/personal_data_indicator/1.0.0",
                "evidence_context_size": "medium",
                "maximum_evidence_count": 5,
            },
            "llm_validation": {
                "enable_llm_validation": True,
                "llm_batch_size": 10,
                "llm_validation_mode": "standard",
            },
        }

    # Factory-specific tests

    def test_can_create_returns_false_when_llm_required_but_unavailable(self) -> None:
        """Test graceful degradation when LLM validation enabled but service unavailable."""
        container = ServiceContainer()  # No LLM service registered
        factory = PersonalDataAnalyserFactory(container)

        config_requiring_llm = {
            "pattern_matching": {"ruleset": "local/personal_data_indicator/1.0.0"},
            "llm_validation": {"enable_llm_validation": True},
        }

        result = factory.can_create(config_requiring_llm)

        assert result is False

    def test_get_service_dependencies_declares_llm_service(self) -> None:
        """Test that factory declares LLMService dependency."""
        container = ServiceContainer()
        factory = PersonalDataAnalyserFactory(container)

        deps = factory.get_service_dependencies()

        assert "llm_service" in deps
        assert deps["llm_service"] is LLMService

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        """Test that can_create returns False when ruleset doesn't exist."""
        container = ServiceContainer()
        factory = PersonalDataAnalyserFactory(container)

        # LLM validation disabled, so only ruleset matters
        config_with_nonexistent_ruleset = {
            "pattern_matching": {"ruleset": "local/nonexistent/1.0.0"},
            "llm_validation": {"enable_llm_validation": False},
        }

        result = factory.can_create(config_with_nonexistent_ruleset)

        assert result is False
