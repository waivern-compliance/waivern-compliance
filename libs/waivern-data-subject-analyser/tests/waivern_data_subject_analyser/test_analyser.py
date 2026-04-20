"""Metadata and construction tests for DataSubjectAnalyser.

Behavioural coverage of the prepare/finalise distributed-processor contract
lives in ``test_distributed.py``. Pattern-matching behaviour lives in
``test_pattern_matcher.py`` and schema-specific reading behaviour lives in
the schema-reader test modules.

Uses monkeypatched RulesetManager to decouple from production ruleset data.
"""

import pytest
from waivern_analysers_shared.utilities import RulesetManager
from waivern_core import InputRequirement
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule

from waivern_data_subject_analyser.analyser import DataSubjectAnalyser
from waivern_data_subject_analyser.types import DataSubjectAnalyserConfig

SYNTHETIC_RULES = (
    DataSubjectIndicatorRule(
        name="Test Rule",
        description="Test",
        subject_category="test_cat",
        indicator_type="primary",
        confidence_weight=45,
        patterns=("test_kw",),
    ),
)


def _mock_get_rules(
    uri: str, rule_type: type[DataSubjectIndicatorRule]
) -> tuple[DataSubjectIndicatorRule, ...]:
    return SYNTHETIC_RULES


class TestDataSubjectAnalyserConstruction:
    """Tests that require analyser instantiation (and therefore rule loading)."""

    @pytest.fixture(autouse=True)
    def _mock_ruleset_manager(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Inject synthetic rules so the analyser doesn't need real rulesets."""
        monkeypatch.setattr(RulesetManager, "get_rules", _mock_get_rules)

    def test_from_properties_creates_instance_with_defaults(self) -> None:
        config = DataSubjectAnalyserConfig.from_properties({})

        analyser = DataSubjectAnalyser(config)

        assert analyser is not None


class TestDataSubjectAnalyserSchemaSupport:
    """Static schema declarations (no analyser instantiation needed)."""

    def test_get_name_returns_correct_identifier(self) -> None:
        assert DataSubjectAnalyser.get_name() == "data_subject_analyser"

    def test_get_input_requirements_includes_standard_input(self) -> None:
        input_requirements = DataSubjectAnalyser.get_input_requirements()
        all_schema_names = {
            req.schema_name for req_set in input_requirements for req in req_set
        }

        assert "standard_input" in all_schema_names
        first_req = input_requirements[0][0]
        assert isinstance(first_req, InputRequirement)
        assert first_req.schema_name == "standard_input"
        assert first_req.version == "1.0.0"

    def test_get_input_requirements_includes_source_code(self) -> None:
        input_requirements = DataSubjectAnalyser.get_input_requirements()
        all_schema_names = {
            req.schema_name for req_set in input_requirements for req in req_set
        }

        assert "source_code" in all_schema_names
        source_code_req_set = next(
            req_set
            for req_set in input_requirements
            if any(req.schema_name == "source_code" for req in req_set)
        )
        assert len(source_code_req_set) == 1
        assert source_code_req_set[0].version == "1.0.0"

    def test_get_supported_output_schemas_returns_data_subject_indicator(self) -> None:
        output_schemas = DataSubjectAnalyser.get_supported_output_schemas()

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "data_subject_indicator"
