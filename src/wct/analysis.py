"""Analysis result data classes for WCT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Result from a plugin analysis."""

    plugin_name: str
    input_schema: str
    output_schema: str
    data: dict[str, Any]
    metadata: dict[str, Any]
    success: bool
    error_message: str | None = None
