"""Type definitions for data export analyser."""

from pydantic import BaseModel
from waivern_core import ComponentConfig


class DataExportAnalyserConfig(BaseModel):
    """Configuration for DataExportAnalyser.

    Work in progress - configuration will be expanded as analyser is implemented.
    """

    @classmethod
    def from_properties(cls, _config: ComponentConfig) -> "DataExportAnalyserConfig":
        """Create config from properties dict.

        Args:
            _config: Configuration dict from runbook (currently unused)

        Returns:
            Validated configuration object

        """
        # Currently no properties to validate, return empty config
        return cls()
