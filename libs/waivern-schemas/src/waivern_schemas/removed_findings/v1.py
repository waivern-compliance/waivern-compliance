"""Schema data models for the removed-findings audit trail.

Persisted as a sidecar Message alongside the primary analyser output when LLM
validation removes findings. Each entry pairs the original finding's
serialised form with a human-readable reason for its removal.
"""

from datetime import UTC, datetime
from typing import Annotated, ClassVar

from pydantic import BaseModel, Field, PlainSerializer
from waivern_core.schemas import BaseSchemaOutput
from waivern_core.types import JsonValue


class RemovedFinding(BaseModel):
    """Single finding removed by LLM validation, paired with its removal reason.

    ``original_finding`` is stored as a JSON-serialised dict so that the
    audit-trail schema is decoupled from the producer analyser's specific
    finding type. Migration across analyser-side schema versions is handled
    by pure forward-migration functions at read time.
    """

    original_finding: dict[str, JsonValue] = Field(
        description="Serialised form of the analyser's finding at the time of removal",
    )
    reason: str = Field(
        description=(
            "Human-readable removal reason. For LLM-direct removals this is the "
            "LLM's verdict reasoning verbatim; for group cascade removals it is "
            "a synthesised 'Inferred — …' string explaining the cascade."
        ),
    )
    removal_timestamp: Annotated[
        datetime,
        PlainSerializer(lambda v: v.isoformat(), return_type=str, when_used="json"),
    ] = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this finding was removed",
    )


class RemovedFindingsOutput(BaseSchemaOutput):
    """Sidecar audit-trail payload listing findings removed by LLM validation.

    Carries enough context (analyser identity, run ID, ruleset reference) to
    be interpreted on its own without reference to the primary output, which
    is required for downstream tooling that aggregates audit data across
    runs.
    """

    __schema_version__: ClassVar[str] = "1.0.0"

    analyser_name: str = Field(
        description="Name of the analyser that produced this audit trail",
    )
    run_id: str = Field(
        description="Run ID for cross-artifact correlation",
    )
    ruleset_name: str | None = Field(
        default=None,
        description=(
            "Ruleset URI used for pattern matching. ``None`` when the producing "
            "analyser is not ruleset-driven."
        ),
    )
    ruleset_version: str | None = Field(
        default=None,
        description="Version of the ruleset referenced by ``ruleset_name``",
    )
    removed_findings: list[RemovedFinding] = Field(
        description="Findings removed during LLM validation, each paired with its removal reason",
    )


__all__ = [
    "RemovedFinding",
    "RemovedFindingsOutput",
]
