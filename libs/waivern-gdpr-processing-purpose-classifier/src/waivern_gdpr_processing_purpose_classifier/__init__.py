"""GDPR processing purpose classifier for Waivern Compliance Framework."""

from .classifier import GDPRProcessingPurposeClassifier
from .factory import GDPRProcessingPurposeClassifierFactory

__all__ = [
    "GDPRProcessingPurposeClassifier",
    "GDPRProcessingPurposeClassifierFactory",
]
