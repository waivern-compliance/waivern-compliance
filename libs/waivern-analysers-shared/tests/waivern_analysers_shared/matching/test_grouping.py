"""Tests for proximity-based match grouping."""

import re

from waivern_analysers_shared.matching.grouping import group_matches_by_proximity
from waivern_analysers_shared.types import PatternType


class TestGroupMatchesByProximity:
    """Tests for the proximity grouping algorithm."""

    def test_empty_matches_returns_empty_tuple(self) -> None:
        """Empty list of matches returns empty tuple."""
        result = group_matches_by_proximity([], 200, 10, PatternType.REGEX)
        assert result == ()

    def test_single_match_single_representative(self) -> None:
        """Single match returns one representative."""
        matches = list(re.finditer(r"test", "test content"))
        result = group_matches_by_proximity(matches, 200, 10, PatternType.REGEX)

        assert len(result) == 1
        assert result[0].start == 0
        assert result[0].end == 4
        assert result[0].pattern_type == PatternType.REGEX

    def test_dense_matches_single_group(self) -> None:
        """Matches within threshold form single group, first match is representative."""
        content = "test1 test2 test3"
        matches = list(re.finditer(r"test\d", content))
        result = group_matches_by_proximity(matches, 200, 10, PatternType.REGEX)

        assert len(result) == 1  # All in one group
        assert result[0].start == 0  # First match is representative
        assert result[0].end == 5

    def test_spread_matches_multiple_groups(self) -> None:
        """Matches beyond threshold form separate groups."""
        # Create content with matches far apart
        content_parts = ["test", "x" * 300, "test", "x" * 300, "test"]
        content = "".join(content_parts)
        matches = list(re.finditer(r"test", content))
        result = group_matches_by_proximity(matches, 200, 10, PatternType.REGEX)

        assert len(result) == 3  # Three separate groups
        assert result[0].start == 0
        assert result[1].start == 304
        assert result[2].start == 608

    def test_boundary_threshold_exactly_met_same_group(self) -> None:
        """Matches exactly at threshold distance are in the SAME group."""
        # test1 ends at position 5, test2 starts at position 205 (exactly 200 apart)
        content = "test1" + "x" * 200 + "test2"
        matches = list(re.finditer(r"test\d", content))
        result = group_matches_by_proximity(matches, 200, 10, PatternType.REGEX)

        # With > (not >=), exactly at threshold = same group
        assert len(result) == 1

    def test_boundary_threshold_exceeded_separate_groups(self) -> None:
        """Matches beyond threshold distance are in SEPARATE groups."""
        # test1 ends at position 5, test2 starts at position 206 (201 apart, > threshold)
        content = "test1" + "x" * 201 + "test2"
        matches = list(re.finditer(r"test\d", content))
        result = group_matches_by_proximity(matches, 200, 10, PatternType.REGEX)

        # Beyond threshold = separate groups
        assert len(result) == 2

    def test_max_representatives_limit_respected(self) -> None:
        """Respects max_representatives limit even with more groups."""
        content_parts = [
            "test",
            "x" * 300,
            "test",
            "x" * 300,
            "test",
            "x" * 300,
            "test",
        ]
        content = "".join(content_parts)
        matches = list(re.finditer(r"test", content))
        result = group_matches_by_proximity(matches, 1, 3, PatternType.REGEX)

        assert len(result) == 3  # Limited by max_representatives
        assert result[0].start == 0
        assert result[1].start == 304
        assert result[2].start == 608

    def test_overlapping_matches_single_group(self) -> None:
        """Overlapping matches form single group."""
        content = "testtesttest"
        matches = list(re.finditer(r"test", content))
        result = group_matches_by_proximity(matches, 200, 10, PatternType.REGEX)

        assert len(result) == 1  # Single group (overlapping)
        assert result[0].start == 0  # First match is representative

    def test_adjoining_matches_single_group(self) -> None:
        """Matches that touch form single group."""
        content = "testtesttest"
        matches = list(re.finditer(r"test", content))
        result = group_matches_by_proximity(matches, 200, 10, PatternType.REGEX)

        assert len(result) == 1  # Single group (adjoining)
        assert result[0].start == 0  # First match is representative

    def test_pattern_type_preserved(self) -> None:
        """PatternType is preserved in representatives."""
        matches = list(re.finditer(r"test", "test"))

        result_regex = group_matches_by_proximity(matches, 200, 10, PatternType.REGEX)
        result_word = group_matches_by_proximity(
            matches, 200, 10, PatternType.WORD_BOUNDARY
        )

        assert result_regex[0].pattern_type == PatternType.REGEX
        assert result_word[0].pattern_type == PatternType.WORD_BOUNDARY

    def test_real_regex_matches(self) -> None:
        """Test with actual regex matches."""
        content = (
            "email: a@b.com ... email: c@d.com .................... email: e@f.com"
        )
        matches = list(re.finditer(r"\w+@\w+", content))
        result = group_matches_by_proximity(matches, 50, 10, PatternType.REGEX)

        # All matches are within 50 chars, so should be 1 group
        assert len(result) == 1
        assert result[0].start == 7  # First email position
