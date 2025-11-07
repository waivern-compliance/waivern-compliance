"""Data export analyser (work in progress)."""

import logging
from typing import override

from waivern_core import Analyser
from waivern_core.message import Message
from waivern_core.schemas import Schema

from .types import DataExportAnalyserConfig

logger = logging.getLogger(__name__)


class DataExportAnalyser(Analyser):
    """Analyser for data export compliance analysis (work in progress).

    This analyser is currently under development. It will use the TCF vendor
    database to analyse data export practices and compliance.

    The vendor database tooling is available in the vendor_database/ directory.
    """

    def __init__(self, config: DataExportAnalyserConfig) -> None:
        """Initialise the analyser with dependency injection.

        Args:
            config: Validated configuration object

        """
        self._config = config
        logger.warning(
            "DataExportAnalyser is a work in progress and not yet functional"
        )

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "data_export_analyser"

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Return list of supported input schemas.

        Returns:
            Empty list - analyser not yet implemented

        """
        return []

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return list of supported output schemas.

        Returns:
            Empty list - analyser not yet implemented

        """
        return []

    @override
    def process(
        self,
        input_schema: Schema,
        output_schema: Schema,
        message: Message,
    ) -> Message:
        """Process data and return findings.

        Args:
            input_schema: Input schema for data validation
            output_schema: Output schema for result validation
            message: Input data message

        Returns:
            Empty message - analyser not yet implemented

        Raises:
            NotImplementedError: This analyser is not yet functional

        """
        msg = (
            "DataExportAnalyser is a work in progress. "
            "The vendor database tooling is available in the vendor_database/ directory, "
            "but the analyser integration is not yet implemented."
        )
        raise NotImplementedError(msg)
