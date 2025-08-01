"""Unit tests for ProcessingPurposesRuleset class."""

import re
from unittest.mock import patch

from wct.rulesets.processing_purposes import (
    PROCESSING_PURPOSES,
    ProcessingPurposesRuleset,
)


class TestProcessingPurposesRuleset:
    """Test suite for ProcessingPurposesRuleset class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.ruleset = ProcessingPurposesRuleset()

    def test_init_default_name(self):
        """Test initialization with default ruleset name."""
        ruleset = ProcessingPurposesRuleset()
        assert hasattr(ruleset, "logger")

    def test_init_custom_name(self):
        """Test initialization with custom ruleset name."""
        custom_name = "custom_processing_purposes"
        ruleset = ProcessingPurposesRuleset(custom_name)
        assert hasattr(ruleset, "logger")

    def test_get_patterns_returns_all_patterns(self):
        """Test that get_patterns returns all processing purpose patterns."""
        patterns = self.ruleset.get_patterns()

        # Verify we get the same number of patterns as in PROCESSING_PURPOSES
        assert len(patterns) == len(PROCESSING_PURPOSES)

        # Verify all expected pattern names are present
        expected_names = set(PROCESSING_PURPOSES.keys())
        actual_names = set(patterns.keys())
        assert actual_names == expected_names

    def test_get_patterns_structure(self):
        """Test that get_patterns returns correctly structured patterns."""
        patterns = self.ruleset.get_patterns()

        for pattern_data in patterns.values():
            # Verify required fields are present
            required_fields = {
                "patterns",
                "purpose_category",
                "risk_level",
                "compliance_relevance",
                "keywords",
            }
            assert all(field in pattern_data for field in required_fields)

            # Verify patterns field is a list of regex patterns
            assert isinstance(pattern_data["patterns"], list)
            assert len(pattern_data["patterns"]) > 0

            # Verify each pattern is a valid regex
            for regex_pattern in pattern_data["patterns"]:
                assert isinstance(regex_pattern, str)
                # Test that the regex compiles without errors
                re.compile(regex_pattern, re.IGNORECASE)

            # Verify other field types
            assert isinstance(pattern_data["purpose_category"], str)
            assert isinstance(pattern_data["risk_level"], str)
            assert isinstance(pattern_data["compliance_relevance"], list)
            assert isinstance(pattern_data["keywords"], list)

    def test_transform_to_pattern_format(self):
        """Test the _transform_to_pattern_format method."""
        # Test with a subset of data
        test_data = {
            "Test Purpose": {
                "keywords": ["test keyword", "another test"],
                "category": "TEST_CATEGORY",
                "risk_level": "medium",
                "compliance_frameworks": ["GDPR", "CCPA"],
            }
        }

        # Access protected method for testing purposes
        result = self.ruleset._transform_to_pattern_format(test_data)  # pyright: ignore[reportPrivateUsage]

        assert "Test Purpose" in result
        pattern_data = result["Test Purpose"]

        # Verify transformation
        expected_pattern_count = 2
        assert len(pattern_data["patterns"]) == expected_pattern_count
        assert pattern_data["purpose_category"] == "TEST_CATEGORY"
        assert pattern_data["risk_level"] == "medium"
        assert pattern_data["compliance_relevance"] == ["GDPR", "CCPA"]
        assert pattern_data["keywords"] == ["test keyword", "another test"]

        # Verify regex patterns are properly escaped and have word boundaries
        # re.escape() will escape spaces as "\ ", so we need to account for that
        expected_patterns = [r"\btest\ keyword\b", r"\banother\ test\b"]
        assert pattern_data["patterns"] == expected_patterns

    def test_get_patterns_by_risk_level_high(self):
        """Test filtering patterns by high risk level."""
        high_risk_patterns = self.ruleset.get_patterns_by_risk_level("high")

        # Verify all returned patterns have high risk level
        for pattern_data in high_risk_patterns.values():
            assert pattern_data["risk_level"] == "high"

        # Verify we get some results (based on PROCESSING_PURPOSES data)
        assert len(high_risk_patterns) > 0

    def test_get_patterns_by_risk_level_medium(self):
        """Test filtering patterns by medium risk level."""
        medium_risk_patterns = self.ruleset.get_patterns_by_risk_level("medium")

        # Verify all returned patterns have medium risk level
        for pattern_data in medium_risk_patterns.values():
            assert pattern_data["risk_level"] == "medium"

    def test_get_patterns_by_risk_level_low(self):
        """Test filtering patterns by low risk level."""
        low_risk_patterns = self.ruleset.get_patterns_by_risk_level("low")

        # Verify all returned patterns have low risk level
        for pattern_data in low_risk_patterns.values():
            assert pattern_data["risk_level"] == "low"

    def test_get_patterns_by_risk_level_case_insensitive(self):
        """Test that risk level filtering is case insensitive."""
        high_risk_upper = self.ruleset.get_patterns_by_risk_level("HIGH")
        high_risk_mixed = self.ruleset.get_patterns_by_risk_level("High")
        high_risk_lower = self.ruleset.get_patterns_by_risk_level("high")

        # All should return the same results
        assert len(high_risk_upper) == len(high_risk_mixed) == len(high_risk_lower)

    def test_get_patterns_by_risk_level_nonexistent(self):
        """Test filtering by non-existent risk level."""
        result = self.ruleset.get_patterns_by_risk_level("nonexistent")
        assert len(result) == 0

    def test_get_patterns_by_category_ai_and_ml(self):
        """Test filtering patterns by AI_AND_ML category."""
        ai_patterns = self.ruleset.get_patterns_by_category("AI_AND_ML")

        # Verify all returned patterns have AI_AND_ML category
        for pattern_data in ai_patterns.values():
            assert pattern_data["purpose_category"] == "AI_AND_ML"

        # Verify we get expected AI-related patterns
        assert len(ai_patterns) > 0

    def test_get_patterns_by_category_case_insensitive(self):
        """Test that category filtering is case insensitive."""
        ai_upper = self.ruleset.get_patterns_by_category("AI_AND_ML")
        ai_lower = self.ruleset.get_patterns_by_category("ai_and_ml")
        ai_mixed = self.ruleset.get_patterns_by_category("Ai_And_Ml")

        # All should return the same results
        assert len(ai_upper) == len(ai_lower) == len(ai_mixed)

    def test_get_patterns_by_category_all_categories(self):
        """Test filtering by all expected categories."""
        expected_categories = {
            "AI_AND_ML",
            "OPERATIONAL",
            "ANALYTICS",
            "MARKETING_AND_ADVERTISING",
            "SECURITY",
        }

        for category in expected_categories:
            patterns = self.ruleset.get_patterns_by_category(category)
            # Should have at least some patterns for each category
            assert len(patterns) > 0

            # Verify all patterns have the correct category
            for pattern_data in patterns.values():
                assert pattern_data["purpose_category"] == category

    def test_get_patterns_by_framework_gdpr(self):
        """Test filtering patterns by GDPR compliance framework."""
        gdpr_patterns = self.ruleset.get_patterns_by_framework("GDPR")

        # Verify all returned patterns include GDPR in compliance_relevance
        for pattern_data in gdpr_patterns.values():
            assert "GDPR" in pattern_data["compliance_relevance"]

        # Should have many GDPR-relevant patterns
        assert len(gdpr_patterns) > 0

    def test_get_patterns_by_framework_case_insensitive(self):
        """Test that framework filtering is case insensitive."""
        gdpr_upper = self.ruleset.get_patterns_by_framework("GDPR")
        gdpr_lower = self.ruleset.get_patterns_by_framework("gdpr")
        gdpr_mixed = self.ruleset.get_patterns_by_framework("Gdpr")

        # All should return the same results
        assert len(gdpr_upper) == len(gdpr_lower) == len(gdpr_mixed)

    def test_get_patterns_by_framework_multiple_frameworks(self):
        """Test filtering by various compliance frameworks."""
        frameworks_to_test = ["GDPR", "EU_AI_ACT", "NIST_AI_RMF", "CCPA", "CPRA"]

        for framework in frameworks_to_test:
            patterns = self.ruleset.get_patterns_by_framework(framework)

            # Verify all patterns include the framework
            for pattern_data in patterns.values():
                assert framework in pattern_data["compliance_relevance"]

    def test_validate_patterns_success(self):
        """Test validate_patterns with valid patterns."""
        result = self.ruleset.validate_patterns()
        assert result is True

    def test_validate_patterns_with_mock_invalid_data(self):
        """Test validate_patterns with mocked invalid data."""
        # Mock get_patterns to return invalid data
        invalid_patterns = {
            "Invalid Pattern": {
                "patterns": [],  # Empty patterns list
                "purpose_category": "TEST",
                "risk_level": "invalid_risk",  # Invalid risk level
                "compliance_relevance": "not_a_list",  # Should be list
                "keywords": ["test"],
            }
        }

        with patch.object(self.ruleset, "get_patterns", return_value=invalid_patterns):
            result = self.ruleset.validate_patterns()
            assert result is False

    def test_get_statistics_structure(self):
        """Test that get_statistics returns properly structured statistics."""
        stats = self.ruleset.get_statistics()

        # Verify required fields
        required_fields = {
            "total_purposes",
            "total_keywords",
            "categories",
            "risk_levels",
            "compliance_frameworks",
            "average_keywords_per_purpose",
        }
        assert all(field in stats for field in required_fields)

        # Verify data types
        assert isinstance(stats["total_purposes"], int)
        assert isinstance(stats["total_keywords"], int)
        assert isinstance(stats["categories"], dict)
        assert isinstance(stats["risk_levels"], dict)
        assert isinstance(stats["compliance_frameworks"], dict)
        assert isinstance(stats["average_keywords_per_purpose"], int | float)

    def test_get_statistics_accuracy(self):
        """Test that get_statistics returns accurate counts."""
        stats = self.ruleset.get_statistics()

        # Verify total purposes matches PROCESSING_PURPOSES
        assert stats["total_purposes"] == len(PROCESSING_PURPOSES)

        # Verify total keywords by manual calculation
        expected_total_keywords = sum(
            len(purpose_data["keywords"])
            for purpose_data in PROCESSING_PURPOSES.values()
        )
        assert stats["total_keywords"] == expected_total_keywords

        # Verify average calculation
        expected_average = expected_total_keywords / len(PROCESSING_PURPOSES)
        tolerance = 0.01
        assert abs(stats["average_keywords_per_purpose"] - expected_average) < tolerance

    def test_get_statistics_risk_levels(self):
        """Test that get_statistics correctly counts risk levels."""
        stats = self.ruleset.get_statistics()

        # Manually count risk levels from PROCESSING_PURPOSES
        expected_risk_counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for purpose_data in PROCESSING_PURPOSES.values():
            risk_level: str = purpose_data["risk_level"]  # type: ignore[assignment]
            expected_risk_counts[risk_level] += 1

        assert stats["risk_levels"] == expected_risk_counts

    def test_get_statistics_categories(self):
        """Test that get_statistics correctly counts categories."""
        stats = self.ruleset.get_statistics()

        # Manually count categories from PROCESSING_PURPOSES
        expected_category_counts: dict[str, int] = {}
        for purpose_data in PROCESSING_PURPOSES.values():
            category: str = purpose_data["category"]  # type: ignore[assignment]
            expected_category_counts[category] = (
                expected_category_counts.get(category, 0) + 1
            )

        assert stats["categories"] == expected_category_counts

    def test_get_statistics_compliance_frameworks(self):
        """Test that get_statistics correctly counts compliance frameworks."""
        stats = self.ruleset.get_statistics()

        # Manually count frameworks from PROCESSING_PURPOSES
        expected_framework_counts: dict[str, int] = {}
        for purpose_data in PROCESSING_PURPOSES.values():
            frameworks: list[str] = purpose_data["compliance_frameworks"]  # type: ignore[assignment]
            for framework in frameworks:
                expected_framework_counts[framework] = (
                    expected_framework_counts.get(framework, 0) + 1
                )

        assert stats["compliance_frameworks"] == expected_framework_counts

    @patch("wct.rulesets.processing_purposes.PROCESSING_PURPOSES", {})
    def test_get_statistics_empty_data(self):
        """Test get_statistics with empty PROCESSING_PURPOSES data."""
        stats = self.ruleset.get_statistics()

        assert stats["total_purposes"] == 0
        assert stats["total_keywords"] == 0
        assert stats["average_keywords_per_purpose"] == 0
        assert stats["categories"] == {}
        assert stats["risk_levels"] == {"high": 0, "medium": 0, "low": 0}
        assert stats["compliance_frameworks"] == {}

    def test_regex_pattern_compilation(self):
        """Test that all generated regex patterns can be compiled and used."""
        patterns = self.ruleset.get_patterns()

        for pattern_data in patterns.values():
            for regex_pattern in pattern_data["patterns"]:
                # Should compile without errors
                compiled_pattern = re.compile(regex_pattern, re.IGNORECASE)

                # Find the corresponding original keyword for this pattern
                # The pattern format is \b<escaped_keyword>\b
                escaped_content = regex_pattern[2:-2]  # Remove \b from start and end

                # Find matching keyword by comparing escaped versions
                original_keyword = None
                for keyword in pattern_data["keywords"]:
                    if re.escape(keyword.lower()) == escaped_content:
                        original_keyword = keyword
                        break

                if original_keyword:
                    test_string = f"This contains {original_keyword} in the text"
                    match = compiled_pattern.search(test_string.lower())
                    assert match is not None, (
                        f"Pattern {regex_pattern} should match keyword {original_keyword}"
                    )

    def test_word_boundary_patterns(self):
        """Test that patterns use word boundaries to avoid false positives."""
        patterns = self.ruleset.get_patterns()

        # Find a pattern that specifically uses "ai training" keyword
        ai_training_pattern = None
        for pattern_data in patterns.values():
            for pattern in pattern_data["patterns"]:
                if "ai\\ training" in pattern:  # Escaped version of "ai training"
                    ai_training_pattern = pattern
                    break
            if ai_training_pattern:
                break

        if ai_training_pattern:
            # Test that word boundaries work correctly
            compiled_pattern = re.compile(ai_training_pattern, re.IGNORECASE)

            # Should match "ai training" but not "maintain training"
            assert compiled_pattern.search("ai training") is not None
            assert compiled_pattern.search("maintain training") is None

        # Test with a simpler pattern - look for any single word pattern
        simple_patterns = [
            (pattern, keyword)
            for pattern_data in patterns.values()
            for pattern, keyword in zip(
                pattern_data["patterns"], pattern_data["keywords"]
            )
            if " " not in keyword  # Single word keywords
        ]

        if simple_patterns:
            test_pattern, original_keyword = simple_patterns[0]
            compiled_pattern = re.compile(test_pattern, re.IGNORECASE)

            # Should match the keyword but not when it's part of another word
            assert compiled_pattern.search(original_keyword.lower()) is not None
            assert (
                compiled_pattern.search(f"prefix{original_keyword.lower()}suffix")
                is None
            )

    def test_filtering_methods_consistency(self):
        """Test that filtering methods are consistent in their behavior."""
        # Test that different filtering methods work together correctly
        all_patterns = self.ruleset.get_patterns()

        # Get high-risk AI patterns using both methods
        high_risk_patterns = self.ruleset.get_patterns_by_risk_level("high")
        ai_patterns = self.ruleset.get_patterns_by_category("AI_AND_ML")

        # Find intersection manually
        high_risk_ai_manual = {
            name: pattern
            for name, pattern in all_patterns.items()
            if pattern["risk_level"] == "high"
            and pattern["purpose_category"] == "AI_AND_ML"
        }

        # Find intersection using filtering methods
        high_risk_ai_filtered = {
            name: pattern
            for name, pattern in high_risk_patterns.items()
            if name in ai_patterns
        }

        assert high_risk_ai_manual == high_risk_ai_filtered

    def test_logging_integration(self):
        """Test that the ruleset integrates properly with logging."""
        # This test verifies that logger is properly initialized
        assert hasattr(self.ruleset, "logger")
        assert self.ruleset.logger is not None

        # Test that methods don't raise errors when logging
        # (logger calls are already in the methods, so this tests integration)
        self.ruleset.get_patterns()
        self.ruleset.get_patterns_by_risk_level("high")
        self.ruleset.get_patterns_by_category("AI_AND_ML")
        self.ruleset.get_patterns_by_framework("GDPR")
        self.ruleset.validate_patterns()
        self.ruleset.get_statistics()
