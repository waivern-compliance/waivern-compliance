"""Unit tests for DataCollectionRuleset class."""

from wct.rulesets.data_collection import DataCollectionRuleset
from wct.rulesets.types import Rule, RuleComplianceData


class TestDataCollectionRuleset:
    """Test cases for the DataCollectionRuleset class."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.ruleset = DataCollectionRuleset()

    def test_name_property_returns_canonical_name(self):
        """Test DataCollectionRuleset returns canonical name."""
        ruleset = DataCollectionRuleset()

        assert ruleset.name == "data_collection"

    def test_version_property_returns_correct_string_format(self):
        """Test that version property returns a non-empty string."""
        version = self.ruleset.version

        assert isinstance(version, str)
        assert len(version) > 0
        # Version should follow semantic versioning pattern (x.y.z)
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_get_rules_returns_tuple_of_rules_with_at_least_one_rule(self):
        """Test that get_rules returns an immutable tuple of Rule objects."""
        rules = self.ruleset.get_rules()

        assert isinstance(rules, tuple)
        assert len(rules) > 0
        assert all(isinstance(rule, Rule) for rule in rules)

    def test_get_rules_returns_consistent_count(self):
        """Test that get_rules returns a consistent number of rules."""
        rules1 = self.ruleset.get_rules()
        rules2 = self.ruleset.get_rules()

        assert len(rules1) == len(rules2)

    def test_rule_names_are_unique(self):
        """Test that all rule names are unique."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name for rule in rules]

        assert len(rule_names) == len(set(rule_names))

    def test_rules_have_correct_structure(self):
        """Test that each rule has the correct structure and required fields."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert hasattr(rule, "name")
            assert hasattr(rule, "description")
            assert hasattr(rule, "patterns")
            assert hasattr(rule, "risk_level")
            assert hasattr(rule, "metadata")

            assert isinstance(rule.name, str)
            assert isinstance(rule.description, str)
            assert isinstance(rule.patterns, tuple)
            assert isinstance(rule.risk_level, str)
            assert isinstance(rule.metadata, dict)

    def test_rules_have_valid_risk_levels(self):
        """Test that all rules have valid risk levels."""
        rules = self.ruleset.get_rules()
        valid_risk_levels = {"low", "medium", "high"}

        for rule in rules:
            assert rule.risk_level in valid_risk_levels

    def test_rules_have_non_empty_patterns(self):
        """Test that all rules have non-empty pattern tuples."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert len(rule.patterns) > 0
            assert all(isinstance(pattern, str) for pattern in rule.patterns)
            assert all(len(pattern) > 0 for pattern in rule.patterns)

    def test_rules_have_non_empty_names_and_descriptions(self):
        """Test that all rules have non-empty names and descriptions."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert len(rule.name) > 0
            assert len(rule.description) > 0

    def test_rules_have_collection_type_metadata(self):
        """Test that rules have collection_type in metadata."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert "collection_type" in rule.metadata
            assert isinstance(rule.metadata["collection_type"], str)
            assert len(rule.metadata["collection_type"]) > 0

    def test_rules_have_data_source_metadata(self):
        """Test that rules have data_source in metadata."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert "data_source" in rule.metadata
            assert isinstance(rule.metadata["data_source"], str)
            assert len(rule.metadata["data_source"]) > 0

    def test_rules_have_structured_compliance_data(self):
        """Test that rules have structured compliance data."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert hasattr(rule, "compliance")
            assert isinstance(rule.compliance, list)
            assert len(rule.compliance) > 0

            # Verify each compliance entry is a ComplianceData instance
            for compliance_entry in rule.compliance:
                assert isinstance(compliance_entry, RuleComplianceData)
                assert hasattr(compliance_entry, "regulation")
                assert hasattr(compliance_entry, "relevance")
                assert isinstance(compliance_entry.regulation, str)
                assert isinstance(compliance_entry.relevance, str)
                assert len(compliance_entry.regulation) > 0
                assert len(compliance_entry.relevance) > 0

    def test_patterns_are_tuples_not_lists(self):
        """Test that all patterns are stored as tuples, not lists."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.patterns, tuple)
            assert not isinstance(rule.patterns, list)

    def test_collection_types_are_valid(self):
        """Test that collection_type metadata contains valid categories."""
        rules = self.ruleset.get_rules()
        expected_collection_types = {
            "form_data",
            "url_parameters",
            "cookies",
            "session_data",
            "html_forms",
            "client_storage",
            "api",
            "file_upload",
        }

        found_collection_types: set[str] = set()
        for rule in rules:
            found_collection_types.add(rule.metadata["collection_type"])

        # Should have some overlap with expected types
        assert len(found_collection_types.intersection(expected_collection_types)) > 0
