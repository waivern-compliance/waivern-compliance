"""GDPR data collection classifier for Waivern Compliance Framework."""

from .classifier import GDPRDataCollectionClassifier
from .factory import GDPRDataCollectionClassifierFactory

__all__ = [
    "GDPRDataCollectionClassifier",
    "GDPRDataCollectionClassifierFactory",
]
