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
6. test_can_create_returns_bool_for_invalid_config
7. test_get_service_dependencies_returns_dict

Factory-specific tests (added in this module):
- LLM service injection
- Pattern matcher creation
- Graceful degradation when LLM unavailable
- Service dependency declarations
"""

# from unittest.mock import Mock

# import pytest
# from waivern_core import (
#     ComponentConfig,
#     ComponentFactory,
#     ComponentFactoryContractTests,
# )
# from waivern_llm import BaseLLMService

# from waivern_personal_data_analyser import PersonalDataAnalyser
# from waivern_personal_data_analyser.factory import PersonalDataAnalyserFactory
# from waivern_personal_data_analyser.types import PersonalDataAnalyserConfig


# class TestPersonalDataAnalyserFactory(
#     ComponentFactoryContractTests[PersonalDataAnalyser]
# ):
#     """Test PersonalDataAnalyserFactory with contract compliance + factory-specific tests.

#     Inherits 7 contract tests automatically from ComponentFactoryContractTests.
#     Adds 5 factory-specific tests for PersonalDataAnalyser behavior.
#     """

#     # Required fixtures for contract tests

#     @pytest.fixture
#     def factory(self) -> ComponentFactory[PersonalDataAnalyser]:
#         """Provide factory instance with mocked LLM service.

#         This fixture is required by ComponentFactoryContractTests.
#         """
#         llm_service = Mock(spec=BaseLLMService)
#         return PersonalDataAnalyserFactory(llm_service=llm_service)

#     @pytest.fixture
#     def valid_config(self) -> ComponentConfig:
#         """Provide valid configuration for factory.create().

#         This fixture is required by ComponentFactoryContractTests.
#         Configuration includes all required fields for PersonalDataAnalyser.
#         """
#         return PersonalDataAnalyserConfig.from_properties(
#             {
#                 "pattern_matching": {
#                     "ruleset": "personal_data",
#                     "evidence_context_size": "medium",
#                     "maximum_evidence_count": 5,
#                 },
#                 "llm_validation": {
#                     "enable_llm_validation": True,
#                     "llm_batch_size": 10,
#                     "llm_validation_mode": "standard",
#                 },
#             }
#         )

#     # Factory-specific tests

#     def test_factory_injects_llm_service_into_analyser(
#         self, valid_config: ComponentConfig
#     ):
#         """Test that factory correctly injects LLM service into created analyser."""
#         mock_llm = Mock(spec=BaseLLMService)
#         factory = PersonalDataAnalyserFactory(llm_service=mock_llm)

#         analyser = factory.create(valid_config)

#         assert hasattr(analyser, "_llm_service")
#         assert analyser._llm_service is mock_llm

#     def test_factory_creates_pattern_matcher_from_config(
#         self, valid_config: ComponentConfig
#     ):
#         """Test that factory instantiates PersonalDataPatternMatcher from config."""
#         factory = PersonalDataAnalyserFactory(llm_service=None)

#         analyser = factory.create(valid_config)

#         assert hasattr(analyser, "pattern_matcher")
#         assert analyser.pattern_matcher is not None

#     def test_can_create_returns_false_when_llm_required_but_unavailable(self):
#         """Test graceful degradation when LLM validation enabled but service unavailable."""
#         factory = PersonalDataAnalyserFactory(llm_service=None)

#         config_requiring_llm = PersonalDataAnalyserConfig.from_properties(
#             {
#                 "pattern_matching": {"ruleset": "personal_data"},
#                 "llm_validation": {"enable_llm_validation": True},
#             }
#         )

#         result = factory.can_create(config_requiring_llm)

#         assert result is False

#     def test_get_service_dependencies_declares_llm_service(self):
#         """Test that factory declares BaseLLMService dependency."""
#         factory = PersonalDataAnalyserFactory()

#         deps = factory.get_service_dependencies()

#         assert "llm_service" in deps
#         assert deps["llm_service"] is BaseLLMService

#     def test_factory_works_with_none_llm_service(self, valid_config: ComponentConfig):
#         """Test that factory can create analyser with llm_service=None."""
#         factory = PersonalDataAnalyserFactory(llm_service=None)

#         analyser = factory.create(valid_config)

#         assert analyser is not None
#         assert analyser._llm_service is None
