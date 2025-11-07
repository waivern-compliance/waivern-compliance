"""Producer for source_code schema version 1.0.0."""

from datetime import datetime
from typing import Any


def produce(
    schema_version: str,
    source_config: dict[str, str],
    analysis_summary: dict[str, int],
    files_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Transform source code data to source_code v1.0.0 schema format.

    Args:
        schema_version: The schema version ("1.0.0")
        source_config: Source configuration (path_name, path_str, language)
        analysis_summary: Analysis summary (total_files, total_lines)
        files_data: List of file data dictionaries

    Returns:
        Dictionary conforming to source_code v1.0.0 schema structure

    """
    path_name = source_config["path_name"]
    path_str = source_config["path_str"]
    language = source_config["language"]
    total_files = analysis_summary["total_files"]
    total_lines = analysis_summary["total_lines"]

    return {
        "schemaVersion": schema_version,
        "name": f"source_code_analysis_{path_name}",
        "description": f"Source code analysis of {path_str}",
        "language": language,
        "source": path_str,
        "metadata": {
            "total_files": total_files,
            "total_lines": total_lines,
            "analysis_timestamp": datetime.now().isoformat(),
        },
        "data": files_data,
    }
