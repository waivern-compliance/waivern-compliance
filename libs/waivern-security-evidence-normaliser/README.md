# waivern-security-evidence-normaliser

Normalises indicator findings into framework-agnostic security evidence items.

Consumes one indicator schema per invocation (personal data, processing purpose,
or crypto quality) and maps each finding to a security domain via the
`security_evidence_domain_mapping` ruleset. No LLM required — mapping is fully
deterministic and the output is cacheable.
