from typing import Any

from waivern_analyser.config.base import Config


class SourceConfig(Config):
    """Configuration for a source of data."""

    type: str
    properties: dict[str, Any]
