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
from waivern_llm import BaseLLMService

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
        llm_service = Mock(spec=BaseLLMService)
        return PersonalDataAnalyserFactory(llm_service=llm_service)

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide valid configuration for factory.create().

        This fixture is required by ComponentFactoryContractTests.
        Configuration includes all required fields for PersonalDataAnalyser.
        """
        return {
            "pattern_matching": {
                "ruleset": "personal_data",
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
        factory = PersonalDataAnalyserFactory(llm_service=None)

        config_requiring_llm = {
            "pattern_matching": {"ruleset": "personal_data"},
            "llm_validation": {"enable_llm_validation": True},
        }

        result = factory.can_create(config_requiring_llm)

        assert result is False

    def test_get_service_dependencies_declares_llm_service(self) -> None:
        """Test that factory declares BaseLLMService dependency."""
        factory = PersonalDataAnalyserFactory()

        deps = factory.get_service_dependencies()

        assert "llm_service" in deps
        assert deps["llm_service"] is BaseLLMService
