"""Contract and metadata tests for PersonalDataAnalyser.

Behavioural coverage of the prepare/finalise distributed-processor contract
lives in ``test_distributed.py``. Pattern-matching behaviour lives in
``test_pattern_matcher.py`` and schema-specific reading behaviour lives in
``test_source_code_schema_input_handler.py``.
"""

import pytest
from waivern_core import AnalyserContractTests

from waivern_personal_data_analyser.analyser import PersonalDataAnalyser


class TestPersonalDataAnalyserMetadata:
    """Static metadata declared by the analyser class."""

    def test_get_name_returns_correct_analyser_name(self) -> None:
        """The registered name is the stable identifier used by runbooks."""
        assert PersonalDataAnalyser.get_name() == "personal_data_analyser"

    def test_get_input_requirements_covers_standard_input_and_source_code(self) -> None:
        """Both standard_input and source_code are advertised as valid inputs."""
        requirements = PersonalDataAnalyser.get_input_requirements()
        schema_names = {req[0].schema_name for req in requirements}

        assert "standard_input" in schema_names
        assert "source_code" in schema_names

    def test_get_supported_output_schemas_returns_personal_data_indicator(self) -> None:
        """The analyser only emits personal_data_indicator/1.0.0."""
        output_schemas = PersonalDataAnalyser.get_supported_output_schemas()

        assert len(output_schemas) == 1
        assert output_schemas[0].name == "personal_data_indicator"
        assert output_schemas[0].version == "1.0.0"


class TestPersonalDataAnalyserContract(AnalyserContractTests[PersonalDataAnalyser]):
    """Contract tests inherited from AnalyserContractTests."""

    @pytest.fixture
    def processor_class(self) -> type[PersonalDataAnalyser]:
        """Provide the analyser class for inherited contract tests."""
        return PersonalDataAnalyser
