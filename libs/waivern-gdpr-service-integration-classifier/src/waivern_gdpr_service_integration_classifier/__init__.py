"""GDPR service integration classifier for Waivern Compliance Framework."""

from .classifier import GDPRServiceIntegrationClassifier
from .factory import GDPRServiceIntegrationClassifierFactory

__all__ = [
    "GDPRServiceIntegrationClassifier",
    "GDPRServiceIntegrationClassifierFactory",
]
