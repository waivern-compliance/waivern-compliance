"""Framework-level Analyser base class.

Analyser is a Processor specialised for compliance analysis.
"""

from __future__ import annotations

from waivern_core.base_processor import Processor


class Analyser(Processor):
    """Processor that analyses data for compliance findings.

    Analysers are processors specialised for compliance analysis. They accept
    input data in defined schema(s), run analysis logic, and produce compliance
    findings in defined result schemas.

    The regulatory framework context is declared at the runbook level via the
    `framework` field, not on individual analysers.

    Example:
        class PersonalDataAnalyser(Analyser):
            @classmethod
            def get_name(cls) -> str:
                return "personal_data"

            @classmethod
            def get_input_requirements(cls) -> list[list[InputRequirement]]:
                return [[InputRequirement("standard_input", "1.0.0")]]

            def process(self, inputs: list[Message], output_schema: Schema) -> Message:
                # Analysis logic here
                ...

    """
