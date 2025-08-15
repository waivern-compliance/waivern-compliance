"""Unit tests for ThirdPartyServicesRuleset class."""

from wct.rulesets.third_party_services import ThirdPartyServicesRuleset
from wct.rulesets.types import Rule


class TestThirdPartyServicesRuleset:
    """Test cases for the ThirdPartyServicesRuleset class."""

    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.ruleset = ThirdPartyServicesRuleset()

    def test_name_property_returns_canonical_name(self):
        """Test ThirdPartyServicesRuleset returns canonical name."""
        ruleset = ThirdPartyServicesRuleset()

        assert ruleset.name == "third_party_services"

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

    def test_rules_have_service_category_metadata(self):
        """Test that rules have service_category in metadata."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert "service_category" in rule.metadata
            assert isinstance(rule.metadata["service_category"], str)
            assert len(rule.metadata["service_category"]) > 0

    def test_rules_have_data_types_metadata(self):
        """Test that rules have data_types in metadata with valid personal_data categories."""
        rules = self.ruleset.get_rules()

        # Expected personal data categories from personal_data ruleset
        expected_data_types = {
            "basic_profile",
            "account_data",
            "payment_data",
            "financial_data",
            "behavioral_event_data",
            "technical_device_and_network_data",
            "location_data",
            "user_generated_content",
            "inferred_profile_data",
            "accurate_location",
            "health_data",
            "political_data",
            "racial_ethnic_data",
            "religious_philosophical_data",
            "genetic_data",
            "biometric_data",
            "sexual_orientation_data",
            "date_of_birth",
        }

        for rule in rules:
            assert "data_types" in rule.metadata
            assert isinstance(rule.metadata["data_types"], list)
            assert len(rule.metadata["data_types"]) > 0

            # Each data type should be a valid personal_data category
            for data_type in rule.metadata["data_types"]:
                assert isinstance(data_type, str)
                assert data_type in expected_data_types, (
                    f"Invalid data_type: {data_type}"
                )

    def test_rules_have_compliance_relevance_metadata(self):
        """Test that rules have compliance_relevance in metadata."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert "compliance_relevance" in rule.metadata
            assert isinstance(rule.metadata["compliance_relevance"], str)
            assert len(rule.metadata["compliance_relevance"]) > 0

    def test_rules_have_regulatory_impact_metadata(self):
        """Test that rules have regulatory_impact in metadata."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert "regulatory_impact" in rule.metadata
            assert isinstance(rule.metadata["regulatory_impact"], str)
            assert len(rule.metadata["regulatory_impact"]) > 0

    def test_payment_processor_patterns_exist(self):
        """Test that payment processor patterns exist."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name.lower() for rule in rules]

        # Should have payment processor patterns
        payment_patterns = [name for name in rule_names if "payment" in name]
        assert len(payment_patterns) > 0

        # Check for specific payment services
        payment_rules = [rule for rule in rules if "payment" in rule.name.lower()]
        all_payment_patterns = []
        for rule in payment_rules:
            all_payment_patterns.extend(rule.patterns)

        # Should include common payment processors
        payment_patterns_str = " ".join(all_payment_patterns).lower()
        assert "stripe" in payment_patterns_str or "paypal" in payment_patterns_str

    def test_analytics_tracking_patterns_exist(self):
        """Test that analytics and tracking patterns exist."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name.lower() for rule in rules]

        # Should have analytics patterns
        analytics_patterns = [
            name for name in rule_names if "analytics" in name or "tracking" in name
        ]
        assert len(analytics_patterns) > 0

    def test_social_media_patterns_exist(self):
        """Test that social media platform patterns exist."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name.lower() for rule in rules]

        # Should have social media patterns
        social_patterns = [name for name in rule_names if "social" in name]
        assert len(social_patterns) > 0

    def test_communication_service_patterns_exist(self):
        """Test that communication service patterns exist."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name.lower() for rule in rules]

        # Should have communication patterns
        comm_patterns = [name for name in rule_names if "communication" in name]
        assert len(comm_patterns) > 0

    def test_cloud_storage_patterns_exist(self):
        """Test that cloud storage patterns exist."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name.lower() for rule in rules]

        # Should have cloud storage patterns
        cloud_patterns = [
            name for name in rule_names if "cloud" in name or "storage" in name
        ]
        assert len(cloud_patterns) > 0

    def test_authentication_service_patterns_exist(self):
        """Test that authentication service patterns exist."""
        rules = self.ruleset.get_rules()
        rule_names = [rule.name.lower() for rule in rules]

        # Should have authentication patterns
        auth_patterns = [
            name
            for name in rule_names
            if "authentication" in name or "identity" in name
        ]
        assert len(auth_patterns) > 0

    def test_patterns_are_tuples_not_lists(self):
        """Test that all patterns are stored as tuples, not lists."""
        rules = self.ruleset.get_rules()

        for rule in rules:
            assert isinstance(rule.patterns, tuple)
            assert not isinstance(rule.patterns, list)

    def test_risk_level_distribution(self):
        """Test that we have a reasonable distribution of risk levels."""
        rules = self.ruleset.get_rules()
        risk_counts = {"low": 0, "medium": 0, "high": 0}

        for rule in rules:
            risk_counts[rule.risk_level] += 1

        # We should have rules at multiple risk levels
        assert risk_counts["medium"] > 0
        # Payment and auth services should be high risk
        assert risk_counts["high"] > 0

    def test_service_categories_are_valid(self):
        """Test that service_category metadata contains valid categories."""
        rules = self.ruleset.get_rules()
        expected_categories = {
            "payment_processing",
            "user_analytics",
            "social_media",
            "communication",
            "cloud_infrastructure",
            "identity_management",
        }

        found_categories = set()
        for rule in rules:
            found_categories.add(rule.metadata["service_category"])

        # Should have some overlap with expected categories
        assert len(found_categories.intersection(expected_categories)) > 0

    def test_high_risk_services_include_payment_and_auth(self):
        """Test that payment and authentication services are marked as high risk."""
        rules = self.ruleset.get_rules()

        high_risk_rules = [rule for rule in rules if rule.risk_level == "high"]
        high_risk_categories = [
            rule.metadata["service_category"] for rule in high_risk_rules
        ]

        # Payment processing and identity management should be high risk
        assert "payment_processing" in high_risk_categories
        assert "identity_management" in high_risk_categories

    def test_rules_reference_valid_personal_data_categories(self):
        """Test that data_types reference valid categories from personal_data ruleset."""
        rules = self.ruleset.get_rules()

        # Common personal data categories that should be referenced
        common_categories = {"basic_profile", "account_data", "payment_data"}

        all_referenced_types = set()
        for rule in rules:
            all_referenced_types.update(rule.metadata["data_types"])

        # Should reference some common personal data categories
        assert len(all_referenced_types.intersection(common_categories)) > 0

    def test_rules_have_expected_count(self):
        """Test that we have the expected number of third-party service rules."""
        rules = self.ruleset.get_rules()

        # Should have at least 5 rules covering different service types
        assert len(rules) >= 5

        # Should not have too many rules (keeping it manageable)
        assert len(rules) <= 15

    def test_gdpr_compliance_mentioned_in_metadata(self):
        """Test that GDPR compliance is mentioned in rule metadata."""
        rules = self.ruleset.get_rules()

        gdpr_mentions = 0
        for rule in rules:
            compliance_text = rule.metadata.get("compliance_relevance", "")
            regulatory_text = rule.metadata.get("regulatory_impact", "")

            if "GDPR" in compliance_text or "GDPR" in regulatory_text:
                gdpr_mentions += 1

        # Most third-party services should mention GDPR compliance
        assert gdpr_mentions > 0
