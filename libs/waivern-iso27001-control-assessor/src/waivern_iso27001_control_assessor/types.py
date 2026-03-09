"""Configuration types for ISO 27001 control assessor."""

from pydantic import Field
from waivern_core import BaseComponentConfiguration


class ISO27001AssessorConfig(BaseComponentConfiguration):
    """Configuration for ISO27001Assessor.

    Each assessor instance assesses exactly one ISO 27001 control.
    The control_ref identifies which rule to load from the domain ruleset.

    Inherits from BaseComponentConfiguration to support:
    - Pydantic validation for type safety
    - Immutability (frozen dataclass)
    - from_properties() factory method (inherited)
    - Strict validation (no extra fields)
    """

    domain_ruleset: str = Field(
        default="local/iso27001_domains/1.0.0",
        description="Ruleset URI for ISO 27001 domain rules",
    )
    control_ref: str = Field(
        min_length=1,
        description="ISO 27001:2022 Annex A control reference (e.g. 'A.5.1')",
    )
