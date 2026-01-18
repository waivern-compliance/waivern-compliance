"""Handler for data subject detection in standard input.

Wraps the existing DataSubjectPatternMatcher for schema-handler consistency.
"""

from typing import cast

from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core.schemas import BaseMetadata, StandardInputDataModel

from .pattern_matcher import DataSubjectPatternMatcher
from .schemas.types import DataSubjectIndicatorModel


class StandardInputSchemaInputHandler:
    """Handler for data subject detection in standard input.

    Wraps DataSubjectPatternMatcher to implement the SchemaInputHandler protocol.
    """

    def __init__(self, config: PatternMatchingConfig) -> None:
        """Initialise the handler with pattern matching configuration.

        Args:
            config: Pattern matching configuration.

        """
        self._pattern_matcher = DataSubjectPatternMatcher(config)

    def analyse(self, data: object) -> list[DataSubjectIndicatorModel]:
        """Analyse input data for data subject patterns.

        This is the public boundary - accepts object to keep analyser schema-agnostic.
        Type safety is maintained internally via StandardInputDataModel.

        Args:
            data: Standard input data (expected to be StandardInputDataModel from reader).

        Returns:
            List of data subject indicators.

        Raises:
            TypeError: If data is not a StandardInputDataModel instance.

        """
        if not isinstance(data, StandardInputDataModel):
            raise TypeError(
                f"Expected StandardInputDataModel, got {type(data).__name__}"
            )

        # Cast to concrete generic type after isinstance validation
        typed_data = cast(StandardInputDataModel[BaseMetadata], data)
        return self._analyse_validated_data(typed_data)

    def _analyse_validated_data(
        self, data: StandardInputDataModel[BaseMetadata]
    ) -> list[DataSubjectIndicatorModel]:
        """Analyse validated standard input data (internal, type-safe).

        Args:
            data: Validated StandardInputDataModel instance.

        Returns:
            List of data subject indicators.

        """
        indicators: list[DataSubjectIndicatorModel] = []

        for data_item in data.data:
            content = data_item.content
            metadata = data_item.metadata
            item_indicators = self._pattern_matcher.find_patterns(content, metadata)
            indicators.extend(item_indicators)

        return indicators
