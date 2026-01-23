"""Handler for processing purpose detection in standard input data.

Encapsulates knowledge of StandardInputDataModel schema, keeping the
analyser schema-agnostic.
"""

from typing import cast

from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_core.schemas import BaseMetadata, StandardInputDataModel

from .pattern_matcher import ProcessingPurposePatternMatcher
from .schemas.types import ProcessingPurposeIndicatorModel


class StandardInputSchemaInputHandler:
    """Handler for processing purpose detection in standard input data.

    Encapsulates StandardInputDataModel schema knowledge, providing a
    schema-agnostic interface to the analyser.
    """

    def __init__(self, pattern_matching_config: PatternMatchingConfig) -> None:
        """Initialise the handler with configuration.

        Args:
            pattern_matching_config: Configuration for pattern matching.

        """
        self._pattern_matcher = ProcessingPurposePatternMatcher(pattern_matching_config)

    def analyse(self, data: object) -> list[ProcessingPurposeIndicatorModel]:
        """Analyse input data for processing purpose patterns.

        This is the public boundary - accepts object to keep analyser schema-agnostic.
        Type safety is maintained internally via StandardInputDataModel.

        Args:
            data: Standard input data (expected to be StandardInputDataModel from reader).

        Returns:
            List of processing purpose findings detected in the content.

        Raises:
            TypeError: If data is not a StandardInputDataModel instance.

        """
        # Validate at boundary - handler owns standard input schema knowledge
        if not isinstance(data, StandardInputDataModel):
            raise TypeError(
                f"Expected StandardInputDataModel, got {type(data).__name__}"
            )

        # Cast to concrete generic type after isinstance validation
        typed_data = cast(StandardInputDataModel[BaseMetadata], data)
        return self._analyse_validated_data(typed_data)

    def _analyse_validated_data(
        self, data: StandardInputDataModel[BaseMetadata]
    ) -> list[ProcessingPurposeIndicatorModel]:
        """Analyse validated standard input data (internal, type-safe).

        Args:
            data: Validated StandardInputDataModel instance.

        Returns:
            List of processing purpose findings detected in the content.

        """
        findings: list[ProcessingPurposeIndicatorModel] = []

        for data_item in data.data:
            content = data_item.content
            item_metadata = data_item.metadata

            item_findings = self._pattern_matcher.find_patterns(content, item_metadata)
            findings.extend(item_findings)

        return findings
