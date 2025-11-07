"""Producer for standard_input schema version 1.0.0."""

from pathlib import Path
from typing import Any

from waivern_core.schemas import FilesystemMetadata

# Connector name constant
_CONNECTOR_NAME = "filesystem_connector"


def produce(
    schema_version: str,
    all_file_data: list[dict[str, Any]],
    config_data: dict[str, Any],
) -> dict[str, Any]:
    """Transform file data to standard_input v1.0.0 schema format.

    Args:
        schema_version: The schema version ("1.0.0")
        all_file_data: List of file data dictionaries with 'path', 'content', 'stat' keys
        config_data: Configuration data with 'path', 'encoding', 'exclude_patterns', 'is_file' keys

    Returns:
        Dictionary conforming to standard_input v1.0.0 schema structure

    """
    # Extract config values
    source_path: Path = config_data["path"]
    encoding: str = config_data["encoding"]
    exclude_patterns: list[str] = config_data["exclude_patterns"]
    is_file: bool = config_data["is_file"]

    # Calculate aggregate metadata
    total_size = sum(file_data["stat"].st_size for file_data in all_file_data)
    file_count = len(all_file_data)

    # Build data array with one entry per file
    data_entries: list[dict[str, Any]] = []
    for file_data in all_file_data:
        file_path = file_data["path"]
        content = file_data["content"]

        # Create FilesystemMetadata instance
        metadata = FilesystemMetadata(
            source=str(file_path),
            connector_type=_CONNECTOR_NAME,
            file_path=str(file_path),
        )

        data_entries.append(
            {
                "content": content,
                "metadata": metadata.model_dump(),
            }
        )

    # Determine source description
    if is_file:
        source_desc = f"Content from file {source_path.name}"
        name_suffix = source_path.name
    else:
        source_desc = f"Content from directory {source_path.name} ({file_count} files)"
        name_suffix = f"{source_path.name}_directory"

    return {
        "schemaVersion": schema_version,
        "name": f"standard_input_from_{name_suffix}",
        "description": source_desc,
        "contentEncoding": encoding,
        "source": str(source_path),
        "metadata": {
            "file_count": file_count,
            "total_size_bytes": total_size,
            "exclude_patterns": exclude_patterns,
            "source_type": "file" if is_file else "directory",
        },
        "data": data_entries,
    }
