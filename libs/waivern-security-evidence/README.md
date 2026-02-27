# waivern-security-evidence

Shared security evidence schema for the Waivern Compliance Framework.

Defines the `security_evidence/1.0.0` schema — the framework-agnostic hub that normalises
findings from code analysis, configuration inspection, and document extraction into a
uniform structure for downstream compliance assessors.

Produced by `SecurityEvidenceNormaliser` (deterministic, no LLM) and
`DocumentEvidenceExtractor` (LLM-based). Both packages declare this package as a
dependency rather than owning the schema themselves.
