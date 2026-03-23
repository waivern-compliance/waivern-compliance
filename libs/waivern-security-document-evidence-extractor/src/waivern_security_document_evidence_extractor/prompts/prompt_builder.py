"""PromptBuilder for domain classification of policy documents.

Implements the PromptBuilder protocol for classifying documents
by SecurityDomain using LLM analysis.
"""

from collections.abc import Sequence
from typing import override

from waivern_llm import ItemGroup, PromptBuilder
from waivern_schemas.security_domain import SecurityDomain

from waivern_security_document_evidence_extractor.types import DocumentItem

_DOMAIN_DESCRIPTIONS: dict[SecurityDomain, str] = {
    SecurityDomain.AUTHENTICATION: "User identity verification, MFA, password policies",
    SecurityDomain.ENCRYPTION: "Data encryption at rest and in transit, key management, TLS",
    SecurityDomain.ACCESS_CONTROL: "Authorisation, RBAC, least privilege, access reviews",
    SecurityDomain.LOGGING_MONITORING: "Audit logs, SIEM, alerting, log retention",
    SecurityDomain.VULNERABILITY_MANAGEMENT: "Patching, scanning, penetration testing",
    SecurityDomain.DATA_PROTECTION: "Data classification, DLP, backup, retention policies",
    SecurityDomain.NETWORK_SECURITY: "Firewalls, segmentation, IDS/IPS, VPN",
    SecurityDomain.PHYSICAL_SECURITY: "Physical access controls, CCTV, secure areas",
    SecurityDomain.PEOPLE_CONTROLS: "Security awareness, training, screening, HR policies",
    SecurityDomain.SUPPLIER_MANAGEMENT: "Third-party risk, vendor assessments, SLAs",
    SecurityDomain.INCIDENT_MANAGEMENT: "Incident response, breach notification, forensics",
    SecurityDomain.BUSINESS_CONTINUITY: "DR planning, BCP, resilience testing, RTO/RPO",
    SecurityDomain.GOVERNANCE: "Information security policies, roles, management commitment, independent review",
    SecurityDomain.ASSET_MANAGEMENT: "Asset inventory, acceptable use, classification, return of assets",
    SecurityDomain.LEGAL_COMPLIANCE: "Legal/regulatory requirements, intellectual property, compliance reviews",
}


class DomainClassificationPromptBuilder(PromptBuilder[DocumentItem]):
    """Builds prompts for classifying documents by security domain.

    Uses INDEPENDENT batching mode — receives a single group per batch
    where group.content carries the document text and group.items carries
    the document item.
    """

    @override
    def build_prompt(
        self,
        groups: Sequence[ItemGroup[DocumentItem]],
    ) -> str:
        """Build classification prompt for the given document.

        Args:
            groups: Groups of findings. INDEPENDENT mode provides a single
                group where content is the full document text and items
                contains the document item.

        Returns:
            Complete prompt string for LLM domain classification.

        """
        items = groups[0].items
        content = groups[0].content

        domain_list = "\n".join(
            f"- {domain.value}: {desc}" for domain, desc in _DOMAIN_DESCRIPTIONS.items()
        )

        filename = items[0].metadata.source if items else "unknown"

        return f"""You are an information security domain classifier. Your task is to read a policy document and determine which security domains it addresses.

**DOCUMENT:** {filename}

**CONTENT:**
{content or "(empty)"}

**SECURITY DOMAINS:**
{domain_list}

**TASK:**
Analyse the document and:
1. Determine which security domains it addresses
2. Produce a compliance-focused summary

**Domain classification rules:**
- A document may address multiple domains (e.g. an access control policy might cover both authentication and access_control)
- Return an empty list [] ONLY if the document is purely organisational context (applies to ALL domains equally), such as:
  - Organisational context documents (industry, tech stack, team size, regulatory jurisdiction)
  - Company overview or general background documents
  Note: ISMS policy documents should be classified as 'governance', not []
- Only include domains the document meaningfully addresses, not domains it merely mentions in passing

**Summary rules:**
- Preserve all compliance-relevant substance: controls, procedures, responsibilities, metrics, review cycles, specific requirements
- Discard boilerplate: headers, formatting, table of contents, repeated definitions, generic preamble
- Keep specific details (e.g. "passwords must be 12+ characters", "reviews every 6 months") rather than vague statements
- The summary will be used by downstream compliance assessors — ensure no actionable detail is lost

**RESPONSE FORMAT:**
Return valid JSON only:
{{"security_domains": ["domain1", "domain2"], "summary": "Compliance-focused summary..."}}
or for cross-cutting documents:
{{"security_domains": [], "summary": "Compliance-focused summary..."}}"""
