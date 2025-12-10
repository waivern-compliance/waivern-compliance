"""Framework-level Analyser base class.

Analyser is a Processor specialised for compliance analysis.
It adds compliance framework declaration to the base Processor contract.
"""

from __future__ import annotations

from waivern_core.base_processor import Processor


class Analyser(Processor):
    """Processor that analyses data for compliance findings.

    Analysers are processors specialised for compliance analysis. They accept
    input data in defined schema(s), run analysis logic, and produce compliance
    findings in defined result schemas.

    In addition to the base Processor contract, Analysers declare which
    compliance frameworks (GDPR, CCPA, etc.) their output supports. This
    enables automatic exporter selection based on the frameworks used in
    a runbook.

    Example:
        class PersonalDataAnalyser(Analyser):
            @classmethod
            def get_compliance_frameworks(cls) -> list[str]:
                return []  # Generic analyser, usable across any framework

        class GdprArticle30Analyser(Analyser):
            @classmethod
            def get_compliance_frameworks(cls) -> list[str]:
                return ["GDPR", "UK_GDPR"]  # GDPR-specific analyser

    """

    @classmethod
    def get_compliance_frameworks(cls) -> list[str]:
        """Declare compliance frameworks this analyser's output supports.

        This is used by the export infrastructure to auto-detect which
        exporter to use based on the analysers in a runbook.

        Returns:
            List of framework identifiers (e.g., ["GDPR", "UK_GDPR"]),
            or empty list for generic/framework-agnostic analysers.

        """
        return []
