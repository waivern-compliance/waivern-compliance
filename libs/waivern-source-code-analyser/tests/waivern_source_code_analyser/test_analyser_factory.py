"""Tests for SourceCodeAnalyserFactory.

This test module uses the CONTRACT TESTING PATTERN by inheriting from
ComponentFactoryContractTests to ensure SourceCodeAnalyserFactory
correctly implements the ComponentFactory interface.

Contract tests (inherited automatically):
1. test_create_returns_component_instance
2. test_get_component_name_returns_non_empty_string
3. test_get_input_schemas_returns_list_of_schemas
4. test_get_output_schemas_returns_list_of_schemas
5. test_can_create_returns_bool_for_valid_config
6. test_get_service_dependencies_returns_dict
"""

import pytest
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_core.services.container import ServiceContainer

from waivern_source_code_analyser.analyser import SourceCodeAnalyser
from waivern_source_code_analyser.analyser_factory import SourceCodeAnalyserFactory


class TestSourceCodeAnalyserFactory(ComponentFactoryContractTests[SourceCodeAnalyser]):
    """Test SourceCodeAnalyserFactory with contract compliance.

    Inherits 6 contract tests automatically from ComponentFactoryContractTests.
    SourceCodeAnalyser has no service dependencies, so no additional tests needed.
    """

    # Required fixtures for contract tests

    @pytest.fixture
    def factory(self) -> ComponentFactory[SourceCodeAnalyser]:
        """Provide factory instance.

        This fixture is required by ComponentFactoryContractTests.
        """
        container = ServiceContainer()
        return SourceCodeAnalyserFactory(container)

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide valid configuration for factory.create().

        This fixture is required by ComponentFactoryContractTests.
        Configuration includes all required fields for SourceCodeAnalyser.
        """
        return {
            "language": "php",
            "max_file_size": 5242880,  # 5MB
        }
