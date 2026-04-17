"""Tests for ISO27001AssessorFactory and ISO27001Assessor contract compliance."""

import pytest
from waivern_core import ComponentConfig, ComponentFactory
from waivern_core.services import ServiceContainer
from waivern_core.testing import AnalyserContractTests, ComponentFactoryContractTests

from waivern_iso27001_control_assessor import (
    ISO27001Assessor,
    ISO27001AssessorFactory,
)


class TestISO27001AssessorContract(AnalyserContractTests[ISO27001Assessor]):
    """Contract tests for ISO27001Assessor class-level declarations."""

    @pytest.fixture
    def processor_class(self) -> type[ISO27001Assessor]:
        return ISO27001Assessor


class TestISO27001AssessorFactoryContract(
    ComponentFactoryContractTests[ISO27001Assessor],
):
    """Contract tests for ISO27001AssessorFactory."""

    @pytest.fixture
    def factory(self) -> ComponentFactory[ISO27001Assessor]:
        return ISO27001AssessorFactory(ServiceContainer())

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        return {
            "domain_ruleset": "local/iso27001_domains/1.0.0",
            "control_ref": "A.5.1",
        }


class TestISO27001AssessorFactory:
    """Factory-specific behaviour tests."""

    def test_can_create_returns_false_for_missing_control_ref(self) -> None:
        factory = ISO27001AssessorFactory(ServiceContainer())

        result = factory.can_create({"domain_ruleset": "local/iso27001_domains/1.0.0"})

        assert result is False
