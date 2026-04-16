"""Tests for create_validation_orchestrator factory.

The factory was originally documented as having no dedicated tests because
it was pure wiring. Step 13 introduces non-trivial logic — strategy_state
unpacking for multi-round reconstruction — which this module covers.

Tests verify the factory's observable behaviour via the orchestrator it
produces: calling ``orchestrator.prepare()`` reveals the primary strategy's
batching mode and the content available to its prompt builder, which is
sufficient to assert the factory wired the right strategies.
"""

from unittest.mock import Mock

from waivern_analysers_shared.types import LLMValidationConfig
from waivern_core.schemas import BaseFindingEvidence, PatternMatchDetail
from waivern_core.types import JsonValue
from waivern_llm import BatchingMode, LLMService
from waivern_schemas.processing_purpose_indicator import (
    ProcessingPurposeIndicatorMetadata,
    ProcessingPurposeIndicatorModel,
)

from waivern_processing_purpose_analyser.validation.orchestration import (
    create_validation_orchestrator,
)

RUN_ID = "test-run-id"


def _make_config() -> LLMValidationConfig:
    return LLMValidationConfig(enable_llm_validation=True)


def _make_finding(source: str = "src/File.py") -> ProcessingPurposeIndicatorModel:
    return ProcessingPurposeIndicatorModel(
        purpose="Payment Processing",
        matched_patterns=[PatternMatchDetail(pattern="payment", match_count=1)],
        evidence=[BaseFindingEvidence(content="process payment")],
        metadata=ProcessingPurposeIndicatorMetadata(source=source),
    )


def _source_code_strategy_state(
    contents: dict[str, str],
) -> dict[str, JsonValue]:
    """Build a strategy_state dict matching SourceCodeStrategyState's shape."""
    return {"source_contents": dict(contents)}


class TestFactoryReconstruction:
    """Tests for strategy_state unpacking during round-2 / resume reconstruction."""

    def test_factory_reconstructs_source_contents_from_strategy_state_on_source_code(
        self,
    ) -> None:
        """strategy_state populated -> prepare() yields an EXTENDED_CONTEXT request.

        The round-trip proof: start from an orchestrator built with explicit
        source_contents, capture its ``strategy_state``, build a fresh
        orchestrator using only that state, and confirm it exposes the same
        primary strategy identity (batching mode + captured strategy_state).
        """
        contents = {"src/File.py": "original content"}

        original = create_validation_orchestrator(
            config=_make_config(),
            input_schema_name="source_code",
            source_contents=contents,
            llm_service=Mock(spec=LLMService),
        )
        original_state, original_request = original.prepare(
            [_make_finding()], _make_config(), RUN_ID
        )
        assert original_request is not None
        assert original_request.batching_mode == BatchingMode.EXTENDED_CONTEXT

        # Reconstruct from strategy_state only (the round-2 / resume path).
        reconstructed = create_validation_orchestrator(
            config=_make_config(),
            input_schema_name="source_code",
            source_contents=None,
            strategy_state=original_state.strategy_state,
            llm_service=Mock(spec=LLMService),
        )
        reconstructed_state, reconstructed_request = reconstructed.prepare(
            [_make_finding()], _make_config(), RUN_ID
        )
        assert reconstructed_request is not None
        assert reconstructed_request.batching_mode == BatchingMode.EXTENDED_CONTEXT
        # Round-tripped strategy_state matches the original → same provider shape.
        assert reconstructed_state.strategy_state == original_state.strategy_state

    def test_factory_prefers_explicit_source_contents_over_strategy_state(self) -> None:
        """When both are provided, explicit source_contents wins (round-1 path is authoritative)."""
        explicit = {"explicit.py": "from_round_1"}
        persisted = {"persisted.py": "from_state"}

        orchestrator = create_validation_orchestrator(
            config=_make_config(),
            input_schema_name="source_code",
            source_contents=explicit,
            strategy_state=_source_code_strategy_state(persisted),
            llm_service=Mock(spec=LLMService),
        )
        state, _ = orchestrator.prepare([_make_finding()], _make_config(), RUN_ID)

        assert state.strategy_state == {"source_contents": explicit}

    def test_factory_standard_input_ignores_strategy_state(self) -> None:
        """standard_input schema -> prepare() yields COUNT_BASED and no strategy_state."""
        orchestrator = create_validation_orchestrator(
            config=_make_config(),
            input_schema_name="standard_input",
            source_contents=None,
            strategy_state=_source_code_strategy_state({"a.py": "x"}),
            llm_service=Mock(spec=LLMService),
        )
        state, request = orchestrator.prepare([_make_finding()], _make_config(), RUN_ID)

        assert request is not None
        assert request.batching_mode == BatchingMode.COUNT_BASED
        # ProcessingPurposeValidationStrategy does not override
        # export_persistence_state(), so strategy_state stays None regardless
        # of what the caller passed in.
        assert state.strategy_state is None
