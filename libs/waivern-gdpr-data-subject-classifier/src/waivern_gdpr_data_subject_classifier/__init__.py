"""GDPR data subject classifier for Waivern Compliance Framework."""

from .classifier import GDPRDataSubjectClassifier
from .factory import GDPRDataSubjectClassifierFactory

__all__ = [
    "GDPRDataSubjectClassifier",
    "GDPRDataSubjectClassifierFactory",
]
