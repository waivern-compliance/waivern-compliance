"""Framework-level Classifier base class.

Classifier is a Processor specialised for regulatory classification.
It applies framework-specific interpretation to generic technical findings.
"""

from __future__ import annotations

import abc

from waivern_core.base_processor import Processor


class Classifier(Processor):
    """Processor that classifies findings according to a regulatory framework.

    Classifiers are processors that apply framework-specific interpretation
    to generic technical findings. Unlike Analysers which detect technical facts,
    Classifiers enrich findings with regulatory context.

    Each Classifier targets a specific regulatory framework (GDPR, CCPA, etc.)
    and understands that framework's concepts, categories, and requirements.

    Example:
        class GDPRClassifier(Classifier):
            @classmethod
            def get_framework(cls) -> str:
                return "GDPR"

            # Understands GDPR-specific concepts:
            # - Special category data (Article 9)
            # - Legal basis requirements (Article 6)
            # - Cross-border transfer rules (Chapter V)

    """

    @classmethod
    @abc.abstractmethod
    def get_framework(cls) -> str:
        """Declare the regulatory framework this classifier targets.

        Each classifier targets exactly one framework. Different frameworks
        have fundamentally different concepts that cannot be generalised
        (e.g., GDPR Article 9 vs CCPA "sensitive personal information").

        Returns:
            Framework identifier (e.g., "GDPR", "CCPA", "LGPD").

        """
