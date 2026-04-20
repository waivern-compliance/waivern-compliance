"""Unit tests for StandardInputSchemaInputHandler.

Uses synthetic rules injected via constructor to decouple from
production ruleset data.
"""

import pytest
from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule

from waivern_data_subject_analyser.standard_input_schema_input_handler import (
    StandardInputSchemaInputHandler,
)

RULE_EMPLOYEE = DataSubjectIndicatorRule(
    name="Test Employee",
    description="Employee indicator",
    subject_category="test_employee",
    indicator_type="primary",
    confidence_weight=45,
    patterns=("test_employee_kw",),
)

SYNTHETIC_RULES = (RULE_EMPLOYEE,)

_UNUSED_RULESET_URI = "unused/test/1.0.0"


class TestStandardInputSchemaInputHandler:
    """Tests for StandardInputSchemaInputHandler."""

    def test_analyse_raises_type_error_for_invalid_input(self) -> None:
        """Test that analyse raises TypeError when given non-StandardInputDataModel."""
        config = PatternMatchingConfig(ruleset=_UNUSED_RULESET_URI)
        handler = StandardInputSchemaInputHandler(SYNTHETIC_RULES, config)
        invalid_data = {"not": "a StandardInputDataModel"}

        with pytest.raises(TypeError, match="Expected StandardInputDataModel"):
            handler.analyse(invalid_data)
