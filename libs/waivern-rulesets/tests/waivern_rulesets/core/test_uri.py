"""Unit tests for RulesetURI parsing."""

import pytest

from waivern_rulesets.core.exceptions import RulesetURIParseError
from waivern_rulesets.core.uri import RulesetURI


class TestRulesetURIParsing:
    """Test suite for ruleset URI parsing."""

    def test_parse_valid_uri(self) -> None:
        """Test parsing a valid URI format."""
        uri = RulesetURI.parse("local/personal_data/1.0.0")

        assert uri.provider == "local"
        assert uri.name == "personal_data"
        assert uri.version == "1.0.0"

    def test_parse_uri_with_different_versions(self) -> None:
        """Test parsing URIs with various version formats."""
        uri = RulesetURI.parse("local/processing_purposes/2.1.0")

        assert uri.provider == "local"
        assert uri.name == "processing_purposes"
        assert uri.version == "2.1.0"

    def test_parse_uri_rejects_missing_components(self) -> None:
        """Test that URIs with missing components are rejected."""
        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("personal_data")

        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("local/personal_data")

    def test_parse_uri_rejects_empty_components(self) -> None:
        """Test that URIs with empty components are rejected."""
        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("//1.0.0")

        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("local//1.0.0")

    def test_parse_uri_rejects_extra_components(self) -> None:
        """Test that URIs with extra components are rejected."""
        with pytest.raises(RulesetURIParseError, match="Invalid ruleset URI format"):
            RulesetURI.parse("local/personal_data/1.0.0/extra")

    def test_uri_str_representation(self) -> None:
        """Test string representation of RulesetURI."""
        uri = RulesetURI.parse("local/personal_data/1.0.0")
        assert str(uri) == "local/personal_data/1.0.0"
