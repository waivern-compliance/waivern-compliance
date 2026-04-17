"""Tests for GDPRDataSubjectClassifierFactory."""

import pytest
from waivern_core import (
    ComponentConfig,
    ComponentFactory,
    ComponentFactoryContractTests,
)
from waivern_core.services import ServiceContainer

from waivern_gdpr_data_subject_classifier import GDPRDataSubjectClassifier
from waivern_gdpr_data_subject_classifier.factory import (
    GDPRDataSubjectClassifierFactory,
)


class TestGDPRDataSubjectClassifierFactory(
    ComponentFactoryContractTests[GDPRDataSubjectClassifier]
):
    """Contract compliance plus factory-specific ruleset validation."""

    @pytest.fixture
    def factory(self) -> ComponentFactory[GDPRDataSubjectClassifier]:
        """Provide a factory wired with an empty ServiceContainer."""
        return GDPRDataSubjectClassifierFactory(ServiceContainer())

    @pytest.fixture
    def valid_config(self) -> ComponentConfig:
        """Provide a valid runbook configuration for create()/can_create()."""
        return {
            "ruleset": "local/gdpr_data_subject_classification/1.0.0",
            "llm_validation": {"enable_llm_validation": True},
        }

    def test_can_create_returns_false_for_nonexistent_ruleset(self) -> None:
        """A missing ruleset surfaces through can_create(), not create()."""
        factory = GDPRDataSubjectClassifierFactory(ServiceContainer())

        assert (
            factory.can_create({"ruleset": "local/nonexistent_ruleset/1.0.0"}) is False
        )
