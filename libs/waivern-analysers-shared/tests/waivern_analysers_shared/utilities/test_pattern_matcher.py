"""Tests for PatternMatcher utility class.

This module tests the word boundary-aware pattern matching functionality.
"""

from waivern_analysers_shared.utilities import PatternMatcher


class TestPatternMatcherMatches:
    """Test the matches() method for word boundary detection."""

    def test_matches_pattern_surrounded_by_spaces(self) -> None:
        """Test that pattern matches when surrounded by spaces."""
        matcher = PatternMatcher()

        assert matcher.matches("user dna sample", "dna") is True
        assert matcher.matches("the email address is here", "email") is True

    def test_matches_pattern_with_underscore_boundaries(self) -> None:
        """Test that pattern matches when surrounded by underscores."""
        matcher = PatternMatcher()

        assert matcher.matches("user_dna_sample", "dna") is True
        assert matcher.matches("field_email_address", "email") is True

    def test_matches_pattern_with_punctuation_boundaries(self) -> None:
        """Test that pattern matches when surrounded by punctuation."""
        matcher = PatternMatcher()

        assert matcher.matches('"dna": "value"', "dna") is True
        assert matcher.matches("field-email-address", "email") is True
        assert matcher.matches("data.dna.sequence", "dna") is True

    def test_matches_pattern_at_start_of_string(self) -> None:
        """Test that pattern matches at the start of string."""
        matcher = PatternMatcher()

        assert matcher.matches("dna sequence here", "dna") is True
        assert matcher.matches("email: test@example.com", "email") is True

    def test_matches_pattern_at_end_of_string(self) -> None:
        """Test that pattern matches at the end of string."""
        matcher = PatternMatcher()

        assert matcher.matches("contains some dna", "dna") is True
        assert matcher.matches("user provides email", "email") is True

    def test_no_match_when_embedded_in_alphanumeric(self) -> None:
        """Test that pattern does NOT match when embedded in alphanumeric sequence."""
        matcher = PatternMatcher()

        # These should NOT match - pattern embedded in larger word
        assert matcher.matches("package", "age") is False
        assert matcher.matches("relationship", "ip") is False
        assert matcher.matches("message", "age") is False
        assert matcher.matches("storage", "age") is False

    def test_matches_is_case_insensitive(self) -> None:
        """Test that matching is case insensitive."""
        matcher = PatternMatcher()

        assert matcher.matches("user DNA sample", "dna") is True
        assert matcher.matches("user dna sample", "DNA") is True
        assert matcher.matches("USER EMAIL ADDRESS", "email") is True

    def test_matches_returns_false_for_empty_content(self) -> None:
        """Test that empty content returns False."""
        matcher = PatternMatcher()

        assert matcher.matches("", "dna") is False
        assert matcher.matches("   ", "dna") is False

    def test_matches_returns_false_for_empty_pattern(self) -> None:
        """Test that empty pattern returns False."""
        matcher = PatternMatcher()

        assert matcher.matches("some content", "") is False
        assert matcher.matches("some content", "   ") is False

    def test_no_match_in_base64_encoded_string(self) -> None:
        """Test that pattern does NOT match inside base64-like encoded strings."""
        matcher = PatternMatcher()

        # Real base64-like content where "dna" appears embedded
        base64_content = "EDYvj90wmildna5h31gzvsWw30apC1s"
        assert matcher.matches(base64_content, "dna") is False

        # JWT-like token
        jwt_content = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.agedna123"
        assert matcher.matches(jwt_content, "age") is False


class TestPatternMatcherFindAll:
    """Test the find_all() method for finding match positions."""

    def test_find_all_returns_single_match_position(self) -> None:
        """Test finding a single match returns correct position."""
        matcher = PatternMatcher()

        matches = matcher.find_all("user dna sample", "dna")
        assert len(matches) == 1
        assert matches[0] == (5, 8)  # "dna" starts at index 5, ends at 8

    def test_find_all_returns_multiple_match_positions(self) -> None:
        """Test finding multiple matches returns all positions."""
        matcher = PatternMatcher()

        matches = matcher.find_all("dna sample dna test dna", "dna")
        assert len(matches) == 3

    def test_find_all_returns_empty_list_when_no_matches(self) -> None:
        """Test that no matches returns empty list."""
        matcher = PatternMatcher()

        assert matcher.find_all("some content", "dna") == []
        assert matcher.find_all("", "dna") == []

    def test_find_all_returns_empty_list_for_embedded_pattern(self) -> None:
        """Test that embedded patterns return empty list."""
        matcher = PatternMatcher()

        # "age" embedded in "package" - should not match
        assert matcher.find_all("package", "age") == []
        assert matcher.find_all("storage message package", "age") == []

    def test_find_all_positions_are_correct(self) -> None:
        """Test that returned positions accurately reflect match locations."""
        matcher = PatternMatcher()

        content = "the email is here and another email there"
        matches = matcher.find_all(content, "email")

        # Verify we can use positions to extract the actual matched text
        for start, end in matches:
            assert content[start:end].lower() == "email"


class TestPatternMatcherMatchesValue:
    """Test the matches_value() method for regex pattern matching."""

    def test_matches_value_with_email_pattern(self) -> None:
        """Test matching an email address pattern in content."""
        matcher = PatternMatcher()
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

        assert matcher.matches_value("contact: john@example.com", email_pattern) is True
        assert (
            matcher.matches_value(
                "notes: email is test.user@company.co.uk", email_pattern
            )
            is True
        )

    def test_matches_value_with_phone_pattern(self) -> None:
        """Test matching a phone number pattern in content."""
        matcher = PatternMatcher()
        uk_phone_pattern = r"(?:\+44|0)\s?[1-9]\d{8,9}"

        assert matcher.matches_value("call: +44 7911123456", uk_phone_pattern) is True
        assert matcher.matches_value("phone: 07911123456", uk_phone_pattern) is True

    def test_matches_value_returns_false_when_no_match(self) -> None:
        """Test that non-matching content returns False."""
        matcher = PatternMatcher()
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

        assert matcher.matches_value("no email address here", email_pattern) is False
        assert matcher.matches_value("just some random text", email_pattern) is False

    def test_matches_value_is_case_insensitive(self) -> None:
        """Test that regex matching is case insensitive."""
        matcher = PatternMatcher()

        # Pattern in lowercase, content in uppercase
        assert (
            matcher.matches_value("EMAIL: JOHN@EXAMPLE.COM", r"john@example\.com")
            is True
        )
        # Pattern specifies case, content differs
        assert matcher.matches_value("Test Value Here", r"test value") is True

    def test_matches_value_returns_false_for_empty_content(self) -> None:
        """Test that empty content returns False."""
        matcher = PatternMatcher()

        assert matcher.matches_value("", r"pattern") is False
        assert matcher.matches_value("   ", r"pattern") is False

    def test_matches_value_returns_false_for_empty_pattern(self) -> None:
        """Test that empty pattern returns False."""
        matcher = PatternMatcher()

        assert matcher.matches_value("some content", "") is False


class TestPatternMatcherFindAllValues:
    """Test the find_all_values() method for finding regex match positions."""

    def test_find_all_values_returns_single_match_position(self) -> None:
        """Test finding a single regex match returns correct position."""
        matcher = PatternMatcher()
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

        matches = matcher.find_all_values("contact: john@example.com", email_pattern)
        assert len(matches) == 1

    def test_find_all_values_returns_multiple_match_positions(self) -> None:
        """Test finding multiple regex matches returns all positions."""
        matcher = PatternMatcher()
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

        content = "emails: john@example.com and jane@test.org"
        matches = matcher.find_all_values(content, email_pattern)
        assert len(matches) == 2

    def test_find_all_values_returns_empty_list_when_no_matches(self) -> None:
        """Test that no matches returns empty list."""
        matcher = PatternMatcher()
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

        assert matcher.find_all_values("no email here", email_pattern) == []
        assert matcher.find_all_values("just text", email_pattern) == []

    def test_find_all_values_positions_allow_text_extraction(self) -> None:
        """Test that returned positions can extract the matched text."""
        matcher = PatternMatcher()
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

        content = "contact: john@example.com for info"
        matches = matcher.find_all_values(content, email_pattern)

        # Verify we can use positions to extract the actual matched text
        assert len(matches) == 1
        start, end = matches[0]
        assert content[start:end] == "john@example.com"

    def test_find_all_values_returns_empty_list_for_empty_content(self) -> None:
        """Test that empty content returns empty list."""
        matcher = PatternMatcher()

        assert matcher.find_all_values("", r"pattern") == []

    def test_find_all_values_returns_empty_list_for_empty_pattern(self) -> None:
        """Test that empty pattern returns empty list."""
        matcher = PatternMatcher()

        assert matcher.find_all_values("some content", "") == []
