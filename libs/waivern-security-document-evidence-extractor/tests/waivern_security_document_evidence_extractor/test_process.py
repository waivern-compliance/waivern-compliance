"""Contract tests for SecurityDocumentEvidenceExtractor.

Behavioural coverage of the prepare/finalise distributed-processor contract
lives in ``test_distributed.py``. Schema-level tests live in
``test_schemas.py``.
"""

import pytest
from waivern_core.testing import ProcessorContractTests

from waivern_security_document_evidence_extractor import (
    SecurityDocumentEvidenceExtractor,
)


class TestSecurityDocumentEvidenceExtractorContract(
    ProcessorContractTests[SecurityDocumentEvidenceExtractor],
):
    """Contract tests for SecurityDocumentEvidenceExtractor."""

    @pytest.fixture
    def processor_class(self) -> type[SecurityDocumentEvidenceExtractor]:
        return SecurityDocumentEvidenceExtractor
