"""Security domain taxonomy types."""

from enum import StrEnum


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
    GOVERNANCE = "governance"
    ASSET_MANAGEMENT = "asset_management"
    LEGAL_COMPLIANCE = "legal_compliance"
