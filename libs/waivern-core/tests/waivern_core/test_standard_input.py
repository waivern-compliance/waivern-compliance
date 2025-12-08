"""Tests for standard_input schema models."""

import pytest
from pydantic import ValidationError

from waivern_core.schemas import BaseMetadata


class TestBaseMetadataContext:
    """Tests for BaseMetadata context field."""

    def test_context_defaults_to_empty_dict(self) -> None:
        """Context field defaults to empty dict when not provided."""
        metadata = BaseMetadata(source="test.txt", connector_type="filesystem")

        assert metadata.context == {}

    def test_context_accepts_valid_json_serialisable_dict(self) -> None:
        """Context accepts JSON-serialisable dictionary values."""
        metadata = BaseMetadata(
            source="test.txt",
            connector_type="filesystem",
            context={
                "artifact_id": "abc123",
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "null": None,
                "bool": True,
                "number": 42.5,
            },
        )

        assert metadata.context["artifact_id"] == "abc123"
        assert metadata.context["nested"]["key"] == "value"
        assert metadata.context["list"] == [1, 2, 3]

    def test_context_rejects_non_json_serialisable_values(self) -> None:
        """Context rejects values that cannot be JSON serialised."""
        with pytest.raises(ValidationError) as exc_info:
            BaseMetadata(
                source="test.txt",
                connector_type="filesystem",
                context={
                    "function": lambda x: x
                },  # Functions are not JSON serialisable
            )

        assert "context must be JSON-serialisable" in str(exc_info.value)

    def test_context_rejects_bytes(self) -> None:
        """Context rejects bytes which are not JSON serialisable."""
        with pytest.raises(ValidationError) as exc_info:
            BaseMetadata(
                source="test.txt",
                connector_type="filesystem",
                context={"binary": b"bytes data"},
            )

        assert "context must be JSON-serialisable" in str(exc_info.value)

    def test_context_rejects_sets(self) -> None:
        """Context rejects sets which are not JSON serialisable."""
        with pytest.raises(ValidationError) as exc_info:
            BaseMetadata(
                source="test.txt",
                connector_type="filesystem",
                context={"set_value": {1, 2, 3}},
            )

        assert "context must be JSON-serialisable" in str(exc_info.value)
