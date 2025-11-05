"""Schema types for personal data analyser output.

To use the personal_data_finding schema:
    from waivern_core.schemas import Schema
    schema = Schema("personal_data_finding", "1.0.0")
"""

from .types import PersonalDataFindingModel

__all__ = [
    "PersonalDataFindingModel",
]
