"""Reader for standard_input schema version 1.0.0."""

from typing import Any

from waivern_analysers_shared import SchemaInputHandler
from waivern_rulesets.data_subject_indicator import DataSubjectIndicatorRule
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.data_subject_indicator import DataSubjectIndicatorModel
from waivern_schemas.standard_input import StandardInputDataModel

from ..standard_input_schema_input_handler import StandardInputSchemaInputHandler
from ..types import DataSubjectAnalyserConfig


def read(content: dict[str, Any]) -> StandardInputDataModel[BaseMetadata]:
    """Transform standard_input v1.0.0 to canonical format.

    This version matches the canonical model structure, so we use
    direct Pydantic validation without transformation.

    Args:
        content: Data conforming to standard_input v1.0.0 schema

    Returns:
        Validated StandardInputDataModel instance

    Raises:
        ValidationError: If content doesn't match schema structure

    """
    return StandardInputDataModel[BaseMetadata].model_validate(content)


def create_handler(
    config: DataSubjectAnalyserConfig,
    rules: tuple[DataSubjectIndicatorRule, ...],
) -> SchemaInputHandler[DataSubjectIndicatorModel]:
    """Create handler for standard_input schema.

    Args:
        config: Analyser configuration.
        rules: Pre-loaded data subject indicator rules.

    Returns:
        Handler implementing SchemaInputHandler protocol.

    """
    return StandardInputSchemaInputHandler(rules, config.pattern_matching)
