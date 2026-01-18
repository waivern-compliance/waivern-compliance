"""Unit tests for StandardInputSchemaInputHandler."""

import pytest
from waivern_analysers_shared.types import PatternMatchingConfig

from waivern_data_subject_analyser.standard_input_schema_input_handler import (
    StandardInputSchemaInputHandler,
)


class TestStandardInputSchemaInputHandler:
    """Tests for StandardInputSchemaInputHandler."""

    def test_analyse_raises_type_error_for_invalid_input(self) -> None:
        """Test that analyse raises TypeError when given non-StandardInputDataModel."""
        # Arrange
        config = PatternMatchingConfig(ruleset="local/data_subject_indicator/1.0.0")
        handler = StandardInputSchemaInputHandler(config)
        invalid_data = {"not": "a StandardInputDataModel"}

        # Act & Assert
        with pytest.raises(TypeError, match="Expected StandardInputDataModel"):
            handler.analyse(invalid_data)
