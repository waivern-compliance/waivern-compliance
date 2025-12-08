"""Core type definitions for Waivern Compliance Framework."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InputRequirement:
    """Declares a required input schema for an analyser.

    This dataclass is used by analysers to declare which input schemas they
    support. The frozen=True ensures immutability after creation.

    Attributes:
        schema_name: Name of the required schema (e.g., "personal_data_finding")
        version: Version of the required schema (e.g., "1.0.0")

    """

    schema_name: str
    version: str
