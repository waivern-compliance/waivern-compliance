"""Core type definitions for Waivern Compliance Framework."""

from dataclasses import dataclass
from enum import StrEnum

# JSON type for type-safe JSON value representation
type JsonValue = (
    str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
)


class SecurityDomain(StrEnum):
    """Framework-agnostic security domain taxonomy.

    Bridges indicator findings to compliance framework controls
    (ISO 27001 Annex A, GDPR Art 32, etc.). Shared across all producers
    and consumers of security evidence — rulesets, normalisers, assessors.

    StrEnum serialises to plain strings in JSON — Pydantic handles this
    transparently, so no custom serialiser is needed.
    """

    AUTHENTICATION = "authentication"
    ENCRYPTION = "encryption"
    ACCESS_CONTROL = "access_control"
    LOGGING_MONITORING = "logging_monitoring"
    VULNERABILITY_MANAGEMENT = "vulnerability_management"
    DATA_PROTECTION = "data_protection"
    NETWORK_SECURITY = "network_security"
    PHYSICAL_SECURITY = "physical_security"
    PEOPLE_CONTROLS = "people_controls"
    SUPPLIER_MANAGEMENT = "supplier_management"
    INCIDENT_MANAGEMENT = "incident_management"
    BUSINESS_CONTINUITY = "business_continuity"


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
