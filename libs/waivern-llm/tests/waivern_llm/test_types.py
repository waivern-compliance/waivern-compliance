"""Tests for waivern_llm.types — dispatch request/result types."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from waivern_llm.types import BatchingMode, ItemGroup, LLMRequest


class MockMetadata:
    """Minimal metadata for testing (satisfies FindingMetadata protocol)."""

    def __init__(self, source: str = "test.py") -> None:
        self._source = source

    @property
    def source(self) -> str:
        return self._source


class MockFinding:
    """Minimal finding for testing (satisfies Finding protocol)."""

    def __init__(self, finding_id: str, source: str = "test.py") -> None:
        self._id = finding_id
        self._metadata = MockMetadata(source)

    @property
    def id(self) -> str:
        return self._id

    @property
    def metadata(self) -> MockMetadata:
        return self._metadata


class MockResponse(BaseModel):
    """Minimal LLM response model for testing."""

    valid: bool


class MockPromptBuilder:
    """Minimal prompt builder for testing (satisfies PromptBuilder protocol)."""

    def build_prompt(self, groups: Sequence[ItemGroup[MockFinding]]) -> str:
        return "test prompt"


class TestLLMRequest:
    """Tests for LLMRequest serialisation contracts."""

    def test_prompt_builder_excluded_from_serialisation(self) -> None:
        """prompt_builder must be excluded from model_dump() for batch persistence."""
        request = LLMRequest(
            request_id="test-request",
            groups=[ItemGroup(items=[MockFinding("f1")])],
            prompt_builder=MockPromptBuilder(),
            response_model=MockResponse,
            batching_mode=BatchingMode.COUNT_BASED,
            run_id="test-run",
        )

        dumped = request.model_dump()

        assert "prompt_builder" not in dumped
        assert "response_model" not in dumped
        assert "groups" in dumped
        assert "batching_mode" in dumped
        assert "run_id" in dumped
        assert dumped["built_prompts"] is None
