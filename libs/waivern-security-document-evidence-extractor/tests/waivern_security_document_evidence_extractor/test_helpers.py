"""Shared test helpers for waivern-security-document-evidence-extractor tests."""

from typing import Any

from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_schemas.connector_types import BaseMetadata
from waivern_schemas.security_document_context import SecurityDocumentContextOutput
from waivern_schemas.standard_input import (
    StandardInputDataItemModel,
    StandardInputDataModel,
)

RUN_ID = "test-run-001"
OUTPUT_SCHEMA = Schema("security_document_context", "1.0.0")


def make_input_message(
    items: list[dict[str, Any]],
    *,
    message_id: str = "test_input",
) -> Message:
    """Build a standard_input/1.0.0 Message from content/source pairs."""
    data = StandardInputDataModel(
        schemaVersion="1.0.0",
        name="test_data",
        source="test",
        metadata={},
        data=[
            StandardInputDataItemModel(
                content=item["content"],
                metadata=BaseMetadata(
                    source=item["source"],
                    connector_type="filesystem",
                ),
            )
            for item in items
        ],
    )
    return Message(
        id=message_id,
        content=data.model_dump(exclude_none=True),
        schema=Schema("standard_input", "1.0.0"),
        run_id=RUN_ID,
    )


def parse_output(result: Message) -> SecurityDocumentContextOutput:
    """Parse an extractor output Message into the typed model."""
    return SecurityDocumentContextOutput.model_validate(result.content)
