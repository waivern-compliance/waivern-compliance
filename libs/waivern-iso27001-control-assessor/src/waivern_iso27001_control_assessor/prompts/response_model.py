"""Structured LLM response model for ISO 27001 control assessment."""

from typing import Literal

from pydantic import BaseModel, Field


class ISO27001LLMResponse(BaseModel):
    """Structured response from the LLM for a single control assessment.

    The LLM produces exactly one verdict per control. The three status
    values map directly to ControlStatus (minus not_assessed, which is
    determined before the LLM is called).
    """

    status: Literal["compliant", "partial", "non_compliant"] = Field(
        description=(
            "Assessment verdict. 'compliant' = evidence demonstrates implementation. "
            "'partial' = evidence of intent but incomplete implementation. "
            "'non_compliant' = evidence shows the control is not implemented."
        ),
    )
    rationale: str = Field(
        description=(
            "Narrative explaining the verdict. Reference specific evidence items "
            "and document sections that informed the decision."
        ),
    )
    gap_description: str | None = Field(
        default=None,
        description=(
            "Actionable description of gaps when status is not 'compliant'. "
            "Must be None when status is 'compliant'."
        ),
    )
