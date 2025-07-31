"""Unit tests for PersonalDataRuleset class."""

from wct.rulesets.personal_data import (
    PERSONAL_DATA_PATTERNS,
    PersonalDataRuleset,
)


class TestPersonalDataRuleset:
    """Test suite for PersonalDataRuleset class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.ruleset = PersonalDataRuleset()

    def test_init_default_name(self):
        """Test initialization with default ruleset name."""
        ruleset = PersonalDataRuleset()
        assert hasattr(ruleset, "logger")

    def test_get_patterns_returns_all_patterns(self):
        """Test that get_patterns returns all personal data patterns."""
        patterns = self.ruleset.get_patterns()

        # Verify we get the same number of patterns as in PERSONAL_DATA_PATTERNS
        assert len(patterns) == len(PERSONAL_DATA_PATTERNS)

        # Verify all expected pattern names are present
        expected_names = set(PERSONAL_DATA_PATTERNS.keys())
        actual_names = set(patterns.keys())
        assert actual_names == expected_names

    def test_get_high_risk_patterns(self):
        """Test filtering for high-risk patterns."""
        high_risk_patterns = self.ruleset.get_high_risk_patterns()

        # Verify all returned patterns have high risk level
        for pattern_data in high_risk_patterns.values():
            assert pattern_data["risk_level"] == "high"

    def test_get_special_category_patterns(self):
        """Test filtering for special category patterns."""
        special_patterns = self.ruleset.get_special_category_patterns()

        # Verify all returned patterns are marked as special category
        for pattern_data in special_patterns.values():
            assert pattern_data["special_category"] == "Y"

    def test_validate_pattern_structure_success(self):
        """Test pattern structure validation with valid data."""
        result = self.ruleset.validate_pattern_structure()
        assert result is True

    # TODO: Add more comprehensive tests following the pattern from test_processing_purposes.py
