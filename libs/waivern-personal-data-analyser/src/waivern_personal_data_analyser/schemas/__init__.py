"""Schema types for personal data analyser output.

To use the personal_data_indicator schema:
    from waivern_core.schemas import Schema
    schema = Schema("personal_data_indicator", "1.0.0")
"""

from .types import (
    PersonalDataIndicatorMetadata,
    PersonalDataIndicatorModel,
    PersonalDataIndicatorOutput,
    PersonalDataIndicatorSummary,
    PersonalDataValidationSummary,
)

__all__ = [
    "PersonalDataIndicatorMetadata",
    "PersonalDataIndicatorModel",
    "PersonalDataIndicatorOutput",
    "PersonalDataIndicatorSummary",
    "PersonalDataValidationSummary",
]
