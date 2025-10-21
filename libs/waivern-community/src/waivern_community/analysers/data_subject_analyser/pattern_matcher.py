"""Pattern matcher for data subject classification.

CONTEXT-AWARE PATTERN MATCHING EXPLAINED
========================================

The data subject pattern matcher applies different rules based on the data source
context to improve classification accuracy and reduce false positives.

CONTEXT MAPPING SYSTEM:
The system maps connector types to standardized context names:
- mysql → "database" context
- filesystem → "filesystem" context
- source_code → "source_code" context

RULE FILTERING BY CONTEXT:
Each rule declares which contexts it applies to via applicable_contexts field.
Only rules matching the current context are considered during pattern matching.

EXAMPLE RULE CONTEXTS:
- employee_direct_role_fields: ["database", "source_code"]
  → Applies to database tables and source code, NOT filesystem files
- employee_hr_system_indicators: ["database", "filesystem"]
  → Applies to databases and files, NOT source code comments

CONTEXT FILTERING LOGIC:
1. Determine current context from metadata.connector_type
2. Load all rules from ruleset
3. Filter rules: only include those with current context in applicable_contexts
4. Apply pattern matching on filtered rule set
5. Calculate confidence from matched rules only

WHY CONTEXT MATTERS:
- "employee" in database table = strong indicator (employee record)
- "employee" in source code = weak indicator (variable name, comment)
- "patient" in medical database = strong indicator (patient record)
- "patient" in general filesystem = weak indicator (could be documentation)

BENEFITS:
- Reduces false positives from generic terms in wrong contexts
- Allows context-specific confidence weights
- Enables domain-specific pattern sets
- Improves classification precision

Note: Context filtering happens before pattern matching, ensuring only
relevant rules are evaluated for each data source type.
"""

from waivern_analysers_shared.types import PatternMatchingConfig
from waivern_analysers_shared.utilities import EvidenceExtractor, RulesetManager
from waivern_core.schemas import BaseFindingCompliance, BaseMetadata
from waivern_rulesets.data_subjects import DataSubjectRule

from .confidence_scorer import DataSubjectConfidenceScorer
from .types import DataSubjectFindingMetadata, DataSubjectFindingModel


class DataSubjectPatternMatcher:
    """Pattern matcher for data subject classification.

    This class provides pattern matching functionality specifically for data subject
    detection, creating structured findings with confidence scoring.
    """

    def __init__(self, config: PatternMatchingConfig) -> None:
        """Initialise the pattern matcher with configuration.

        Args:
            config: Pattern matching configuration

        """
        self._config = config
        self._evidence_extractor = EvidenceExtractor()
        self._ruleset_manager = RulesetManager()
        self._confidence_scorer = DataSubjectConfidenceScorer()

    def find_patterns(
        self, content: str, metadata: BaseMetadata
    ) -> list[DataSubjectFindingModel]:
        """Find data subject patterns in content with confidence scoring.

        Args:
            content: Text content to analyze
            metadata: Content metadata for context filtering

        Returns:
            List of data subject findings with confidence scores

        """
        # Check if content is empty
        if not content.strip():
            return []

        rules = self._ruleset_manager.get_rules(self._config.ruleset, DataSubjectRule)
        findings: list[DataSubjectFindingModel] = []
        content_lower = content.lower()

        # Group matched rules and patterns by subject category for confidence calculation
        category_matched_data: dict[str, list[tuple[DataSubjectRule, list[str]]]] = {}

        # Find all matching rules and track which patterns matched
        for rule in rules:
            # Check if rule applies to this context
            if not self._rule_applies_to_context(rule, metadata):
                continue

            # Check each pattern in the rule and collect all matches
            matched_patterns_for_rule: list[str] = []
            for pattern in rule.patterns:
                if pattern.lower() in content_lower:
                    matched_patterns_for_rule.append(pattern)

            # If any patterns matched, add the rule and its matched patterns
            if matched_patterns_for_rule:
                category = rule.subject_category
                if category not in category_matched_data:
                    category_matched_data[category] = []
                category_matched_data[category].append(
                    (rule, matched_patterns_for_rule)
                )

        # Create findings for each category with matched data
        for category, matched_data in category_matched_data.items():
            # Extract rules and patterns from matched data
            matched_rules = [rule for rule, _ in matched_data]
            matched_patterns: list[str] = []
            for _, patterns in matched_data:
                matched_patterns.extend(patterns)

            # Calculate confidence for this category
            confidence_score = self._confidence_scorer.calculate_confidence(
                matched_rules
            )

            # Extract evidence for the first matched pattern (representative)
            evidence = self._evidence_extractor.extract_evidence(
                content,
                matched_patterns[0],  # Use first actually matched pattern for evidence
                self._config.maximum_evidence_count,
                self._config.evidence_context_size,
            )

            if evidence:  # Only create finding if we have evidence
                # Create metadata for the finding
                finding_metadata = DataSubjectFindingMetadata(source=metadata.source)

                # Create the finding
                finding = DataSubjectFindingModel(
                    primary_category=category,
                    confidence_score=confidence_score,
                    risk_level="medium",  # TODO: Implement proper risk assessment logic for data subjects
                    compliance=[
                        BaseFindingCompliance(
                            regulation="GDPR",
                            relevance="Article 30(1)(c) data subject categories",
                        )
                    ],  # TODO: Add proper compliance framework mappings for data subject categories
                    evidence=evidence,
                    modifiers=[],  # TODO: Implement modifier detection logic using ruleset.risk_increasing_modifiers and ruleset.risk_decreasing_modifiers with LLM validation
                    matched_patterns=matched_patterns,
                    metadata=finding_metadata,
                )
                findings.append(finding)

        return findings

    def _rule_applies_to_context(
        self, rule: DataSubjectRule, metadata: BaseMetadata
    ) -> bool:
        """Check if rule applies to the given context.

        Args:
            rule: Data subject rule to check
            metadata: Content metadata

        Returns:
            True if rule applies to this context

        """
        # Map connector types to context names
        context_mapping = {
            "mysql": "database",
            "filesystem": "filesystem",
            "source_code": "source_code",
        }

        current_context = context_mapping.get(
            metadata.connector_type, metadata.connector_type
        )
        return current_context in rule.applicable_contexts
