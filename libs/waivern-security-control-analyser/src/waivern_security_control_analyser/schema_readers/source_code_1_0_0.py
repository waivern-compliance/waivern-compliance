"""Reader for source_code schema version 1.0.0."""

from typing import Any

from waivern_core.schemas import (
    BaseMetadata,
    StandardInputDataItemModel,
    StandardInputDataModel,
)
from waivern_source_code_analyser import SourceCodeDataModel


def read(content: dict[str, Any]) -> StandardInputDataModel[BaseMetadata]:
    """Transform source_code v1.0.0 dict to StandardInputDataModel.

    Converts each source code file to a StandardInputDataItemModel,
    mapping raw_content → content and file_path → metadata.source.

    SourceCodeDataModel requires these fields (all mandatory):
      - name: str
      - description: str
      - source: str (repository name)
      - metadata: {total_files, total_lines, analysis_timestamp}
      - data[]: {file_path, language, raw_content,
                 metadata: {file_size, line_count, last_modified}}

    Args:
        content: Validated source_code v1.0.0 data

    Returns:
        StandardInputDataModel with one item per source code file

    """
    source_code_data = SourceCodeDataModel.model_validate(content)
    data_items = [
        StandardInputDataItemModel[BaseMetadata](
            content=file_data.raw_content,
            metadata=BaseMetadata(
                source=file_data.file_path,
                connector_type="source_code_analyser",
            ),
        )
        for file_data in source_code_data.data
    ]
    return StandardInputDataModel[BaseMetadata](
        schemaVersion="1.0.0",
        name=source_code_data.name,
        data=data_items,
    )
