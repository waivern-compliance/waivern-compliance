"""GDPR personal data classifier for Waivern Compliance Framework."""

from .classifier import GDPRPersonalDataClassifier
from .factory import GDPRPersonalDataClassifierFactory

__all__ = [
    "GDPRPersonalDataClassifier",
    "GDPRPersonalDataClassifierFactory",
]
