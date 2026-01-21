"""Tests for ExtendedContextLLMValidationStrategy.

Business behaviour: Provides LLM validation with full source content,
batching findings by their source (file, table, etc.) for richer context.
Uses token-aware batching to fit within model context limits.
"""

from typing import override
from unittest.mock import Mock

from pydantic import Field
from waivern_core.schemas import (
    BaseFindingEvidence,
    BaseFindingModel,
    PatternMatchDetail,
)
from waivern_llm import BaseLLMService

from waivern_analysers_shared.llm_validation.extended_context_strategy import (
    ExtendedContextLLMValidationStrategy,
    SourceBatch,
)
from waivern_analysers_shared.llm_validation.models import (
    LLMValidationResponseModel,
    LLMValidationResultModel,
)
from waivern_analysers_shared.llm_validation.protocols import SourceProvider
from waivern_analysers_shared.types import BatchingConfig, LLMValidationConfig


class MockFinding(BaseFindingModel):
    """Mock finding for testing."""

    source_id: str = Field(description="Source identifier for testing")
    purpose: str = Field(description="Purpose for testing")

    @override
    def __str__(self) -> str:
        """Human-readable representation for logging."""
        return f"{self.purpose} - {', '.join(p.pattern for p in self.matched_patterns)}"


def _create_finding(purpose: str, source_id: str) -> MockFinding:
    """Create a mock finding with required base fields."""
    return MockFinding(
        source_id=source_id,
        purpose=purpose,
        evidence=[BaseFindingEvidence(content=f"Evidence for {purpose}")],
        matched_patterns=[PatternMatchDetail(pattern=purpose.lower(), match_count=1)],
    )


class MockSourceProvider:
    """Mock source provider for testing."""

    def __init__(self, sources: dict[str, str | None]) -> None:
        """Initialise with source content mapping.

        Args:
            sources: Mapping of source ID to content (None = no content available).

        """
        self._sources = sources

    def get_source_id(self, finding: MockFinding) -> str:
        """Get source ID from finding."""
        return finding.source_id

    def get_source_content(self, source_id: str) -> str | None:
        """Get content for a source."""
        return self._sources.get(source_id)


# Type assertion to verify MockSourceProvider satisfies the protocol
_: SourceProvider[MockFinding] = MockSourceProvider({})


class MockExtendedContextStrategy(ExtendedContextLLMValidationStrategy[MockFinding]):
    """Concrete implementation for testing abstract base class."""

    @override
    def get_batch_validation_prompt(
        self,
        batch: SourceBatch,
        findings_by_source: dict[str, list[MockFinding]],
        source_contents: dict[str, str],
        config: LLMValidationConfig,
    ) -> str:
        """Generate mock validation prompt."""
        source_count = len(batch.sources)
        finding_count = sum(len(findings_by_source[s]) for s in batch.sources)
        return f"Validate {finding_count} findings across {source_count} sources"


def _create_config() -> LLMValidationConfig:
    """Create a default test config."""
    return LLMValidationConfig(
        enable_llm_validation=True,
        llm_batch_size=50,
        llm_validation_mode="standard",
        batching=BatchingConfig(model_context_window=100000),
    )


class TestValidateFindings:
    """Tests for the main validate_findings method."""

    def test_filters_false_positives_from_validation_response(self) -> None:
        """Should filter out findings marked as FALSE_POSITIVE by LLM."""
        source_provider = MockSourceProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        strategy = MockExtendedContextStrategy(source_provider)
        findings = [
            _create_finding("Payment", "src/app.py"),
            _create_finding("Documentation", "src/app.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Real payment processing",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[1].id,
                        validation_result="FALSE_POSITIVE",
                        confidence=0.85,
                        reasoning="Just documentation",
                        recommended_action="discard",
                    ),
                ]
            )
        )

        outcome = strategy.validate_findings(
            findings=findings,
            config=_create_config(),
            llm_service=mock_llm,
        )

        assert outcome.validation_succeeded is True
        assert len(outcome.kept_findings) == 1
        assert outcome.kept_findings[0].purpose == "Payment"
        # Check detailed breakdown
        assert len(outcome.llm_validated_kept) == 1
        assert len(outcome.llm_validated_removed) == 1

    def test_returns_all_findings_when_all_true_positives(self) -> None:
        """Should keep all findings when LLM marks all as TRUE_POSITIVE."""
        source_provider = MockSourceProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        strategy = MockExtendedContextStrategy(source_provider)
        findings = [
            _create_finding("Payment", "src/app.py"),
            _create_finding("Analytics", "src/app.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Real processing",
                        recommended_action="keep",
                    ),
                    LLMValidationResultModel(
                        finding_id=findings[1].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.85,
                        reasoning="Real analytics",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        outcome = strategy.validate_findings(
            findings=findings,
            config=_create_config(),
            llm_service=mock_llm,
        )

        assert outcome.validation_succeeded is True
        assert len(outcome.kept_findings) == 2

    def test_returns_original_findings_on_llm_error(self) -> None:
        """Should return original findings as skipped when LLM call fails entirely."""
        source_provider = MockSourceProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        strategy = MockExtendedContextStrategy(source_provider)
        findings = [_create_finding("Payment", "src/app.py")]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.invoke_with_structured_output.side_effect = Exception(
            "LLM unavailable"
        )

        outcome = strategy.validate_findings(
            findings=findings,
            config=_create_config(),
            llm_service=mock_llm,
        )

        # Fail-safe: batch error keeps findings as skipped
        assert outcome.validation_succeeded is False
        assert len(outcome.kept_findings) == 1
        assert outcome.kept_findings[0].purpose == "Payment"
        assert len(outcome.skipped) == 1

    def test_empty_findings_returns_empty_outcome(self) -> None:
        """Should return empty outcome for empty findings."""
        source_provider = MockSourceProvider({})
        strategy = MockExtendedContextStrategy(source_provider)
        mock_llm = Mock(spec=BaseLLMService)

        outcome = strategy.validate_findings(
            findings=[],
            config=_create_config(),
            llm_service=mock_llm,
        )

        assert outcome.validation_succeeded is True
        assert outcome.kept_findings == []
        mock_llm.invoke_with_structured_output.assert_not_called()

    def test_includes_findings_omitted_by_llm(self) -> None:
        """Should include findings not mentioned in LLM response (fail-safe)."""
        source_provider = MockSourceProvider(
            {"src/app.py": "def process_payment(): pass"}
        )
        strategy = MockExtendedContextStrategy(source_provider)
        findings = [
            _create_finding("Payment", "src/app.py"),
            _create_finding("Analytics", "src/app.py"),
            _create_finding("Logging", "src/app.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        # LLM only returns result for finding 0, omits 1 and 2
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Real payment",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        outcome = strategy.validate_findings(
            findings=findings,
            config=_create_config(),
            llm_service=mock_llm,
        )

        # All 3 findings should be kept (1 explicit + 2 via fail-safe)
        assert outcome.validation_succeeded is True
        assert len(outcome.kept_findings) == 3
        result_purposes = {f.purpose for f in outcome.kept_findings}
        assert result_purposes == {"Payment", "Analytics", "Logging"}
        # Check detailed breakdown: 1 kept, 2 not_flagged
        assert len(outcome.llm_validated_kept) == 1
        assert len(outcome.llm_not_flagged) == 2


class TestSourceGrouping:
    """Tests for source-based grouping behaviour."""

    def test_groups_findings_by_source(self) -> None:
        """Should group findings by their source and batch together."""
        source_provider = MockSourceProvider(
            {
                "src/payments.py": "payment code",
                "src/analytics.py": "analytics code",
            }
        )
        strategy = MockExtendedContextStrategy(source_provider)
        findings = [
            _create_finding("Payment1", "src/payments.py"),
            _create_finding("Payment2", "src/payments.py"),
            _create_finding("Analytics1", "src/analytics.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(results=[])
        )

        outcome = strategy.validate_findings(
            findings=findings,
            config=_create_config(),
            llm_service=mock_llm,
        )

        # All findings kept (not flagged = valid)
        assert outcome.validation_succeeded is True
        assert len(outcome.kept_findings) == 3

    def test_sources_without_content_kept_but_marked_incomplete(self) -> None:
        """Should keep findings from sources without content but mark as incomplete.

        Since this strategy requires source content for context, findings
        from sources without content cannot be validated. They are kept
        (not discarded) but succeeded=False indicates not all findings
        were validated - the caller may use fallback validation.
        """
        source_provider = MockSourceProvider(
            {
                "src/available.py": "available code",
                "src/missing.py": None,  # Content not available
            }
        )
        strategy = MockExtendedContextStrategy(source_provider)
        findings = [
            _create_finding("FromAvailable", "src/available.py"),
            _create_finding("FromMissing", "src/missing.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        # LLM only validates the finding from available source
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[0].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        outcome = strategy.validate_findings(
            findings=findings,
            config=_create_config(),
            llm_service=mock_llm,
        )

        # Both findings kept but validation_succeeded=False (not all were validated)
        assert (
            outcome.validation_succeeded is False
        )  # Some findings couldn't be validated
        assert len(outcome.kept_findings) == 2
        result_purposes = {f.purpose for f in outcome.kept_findings}
        assert result_purposes == {"FromAvailable", "FromMissing"}
        # Check skipped has the missing content finding
        assert len(outcome.skipped) == 1
        assert outcome.skipped[0].reason == "missing_content"


class TestTokenAwareBatching:
    """Tests for token-aware batching behaviour."""

    def test_oversized_sources_kept_but_marked_incomplete(self) -> None:
        """Should keep findings from oversized sources but mark as incomplete."""
        # Create a source that will exceed token limits
        huge_content = "a" * 400000  # ~100K tokens
        source_provider = MockSourceProvider(
            {
                "src/huge.py": huge_content,
                "src/small.py": "small code",
            }
        )
        strategy = MockExtendedContextStrategy(source_provider)
        findings = [
            _create_finding("FromHuge", "src/huge.py"),
            _create_finding("FromSmall", "src/small.py"),
        ]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(
                results=[
                    LLMValidationResultModel(
                        finding_id=findings[1].id,
                        validation_result="TRUE_POSITIVE",
                        confidence=0.9,
                        reasoning="Valid",
                        recommended_action="keep",
                    ),
                ]
            )
        )

        # Use small context window to force huge source to be oversized
        config = LLMValidationConfig(
            enable_llm_validation=True,
            batching=BatchingConfig(model_context_window=10000),
        )

        outcome = strategy.validate_findings(
            findings=findings,
            config=config,
            llm_service=mock_llm,
        )

        # Both kept but validation_succeeded=False (oversized source wasn't validated)
        assert (
            outcome.validation_succeeded is False
        )  # Some findings couldn't be validated
        assert len(outcome.kept_findings) == 2
        result_purposes = {f.purpose for f in outcome.kept_findings}
        assert result_purposes == {"FromHuge", "FromSmall"}
        # Check skipped has the oversized finding
        assert len(outcome.skipped) == 1
        assert outcome.skipped[0].reason == "oversized_source"


class TestPromptGeneration:
    """Tests for prompt generation."""

    def test_prompt_receives_source_contents(self) -> None:
        """Should pass source contents to prompt generation."""
        source_provider = MockSourceProvider({"src/app.py": "def process(): pass"})

        # Track what's passed to get_batch_validation_prompt
        captured_contents: dict[str, str] = {}

        class CapturingStrategy(ExtendedContextLLMValidationStrategy[MockFinding]):
            @override
            def get_batch_validation_prompt(
                self,
                batch: SourceBatch,
                findings_by_source: dict[str, list[MockFinding]],
                source_contents: dict[str, str],
                config: LLMValidationConfig,
            ) -> str:
                captured_contents.update(source_contents)
                return "test prompt"

        strategy = CapturingStrategy(source_provider)
        findings = [_create_finding("Payment", "src/app.py")]
        mock_llm = Mock(spec=BaseLLMService)
        mock_llm.invoke_with_structured_output.return_value = (
            LLMValidationResponseModel(results=[])
        )

        strategy.validate_findings(
            findings=findings,
            config=_create_config(),
            llm_service=mock_llm,
        )

        # Source content should have been passed to prompt generator
        assert "src/app.py" in captured_contents
        assert captured_contents["src/app.py"] == "def process(): pass"
