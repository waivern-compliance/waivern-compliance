"""Contract and ruleset-integrity tests for GDPRDataSubjectClassifier.

Behavioural coverage of the prepare/finalise distributed-processor contract
lives in ``test_distributed.py``. The ruleset-integrity tests here catch
drift between the indicator ruleset and the GDPR classification ruleset,
which would otherwise surface as silent 'unclassified' outputs.
"""

import pytest
from waivern_core import ClassifierContractTests
from waivern_rulesets import (
    DataSubjectIndicatorRuleset,
    GDPRDataSubjectClassificationRuleset,
)

from waivern_gdpr_data_subject_classifier.classifier import GDPRDataSubjectClassifier


class TestGDPRDataSubjectClassifierContract(
    ClassifierContractTests[GDPRDataSubjectClassifier]
):
    """Contract tests inherited from ClassifierContractTests."""

    @pytest.fixture
    def processor_class(self) -> type[GDPRDataSubjectClassifier]:
        """Provide the classifier class for inherited contract tests."""
        return GDPRDataSubjectClassifier


class TestRulesetContractValidation:
    """Ensures indicator categories and GDPR classifications stay aligned.

    Drift in either direction causes silent classification failures, so
    these tests catch mapping gaps and stale references before they reach
    production.
    """

    def test_all_indicator_categories_have_gdpr_mapping(self) -> None:
        """Every indicator category must be mapped in the GDPR classification ruleset."""
        indicator_ruleset = DataSubjectIndicatorRuleset()
        indicator_categories = {
            rule.subject_category for rule in indicator_ruleset.get_rules()
        }

        gdpr_ruleset = GDPRDataSubjectClassificationRuleset()
        mapped_categories: set[str] = set()
        for rule in gdpr_ruleset.get_rules():
            mapped_categories.update(rule.indicator_categories)

        unmapped = indicator_categories - mapped_categories

        assert unmapped == set(), (
            f"Indicator categories missing GDPR mapping: {unmapped}\n"
            f"Add mappings to gdpr_data_subject_classification.yaml"
        )

    def test_gdpr_mappings_reference_valid_indicator_categories(self) -> None:
        """GDPR mappings must only reference existing indicator categories."""
        indicator_ruleset = DataSubjectIndicatorRuleset()
        indicator_categories = {
            rule.subject_category for rule in indicator_ruleset.get_rules()
        }

        gdpr_ruleset = GDPRDataSubjectClassificationRuleset()
        referenced_categories: set[str] = set()
        for rule in gdpr_ruleset.get_rules():
            referenced_categories.update(rule.indicator_categories)

        invalid = referenced_categories - indicator_categories

        assert invalid == set(), (
            f"GDPR mappings reference non-existent indicator categories: {invalid}\n"
            f"These may be typos or stale references after renaming."
        )
