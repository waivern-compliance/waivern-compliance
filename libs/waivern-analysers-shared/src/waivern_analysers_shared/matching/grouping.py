"""Proximity-based grouping for pattern matches."""

import re
from collections.abc import Sequence

from waivern_analysers_shared.types import PatternMatch, PatternType


def group_matches_by_proximity(
    matches: Sequence[re.Match[str]],
    threshold: int,
    max_representatives: int,
    pattern_type: PatternType,
) -> tuple[PatternMatch, ...]:
    """Group matches by proximity and return one representative per group.

    Matches within the threshold distance are considered part of the same cluster.
    Returns one representative match from each cluster, limited to max_representatives.

    Args:
        matches: Sequence of regex matches to group
        threshold: Characters between matches to consider them distinct locations
        max_representatives: Maximum number of representative matches to return
        pattern_type: Type of pattern matching (word_boundary or regex)

    Returns:
        Tuple of representative PatternMatch objects, one per proximity cluster

    """
    if not matches:
        return ()

    representatives: list[PatternMatch] = []
    current_group_end = -1

    for match in matches:
        # Check if this match starts a new group (beyond threshold from previous group)
        if current_group_end == -1 or match.start() > current_group_end + threshold:
            representatives.append(
                PatternMatch(
                    pattern_type=pattern_type,
                    start=match.start(),
                    end=match.end(),
                )
            )
            if len(representatives) >= max_representatives:
                break

        # Update group boundary to include this match's end position
        current_group_end = max(current_group_end, match.end())

    return tuple(representatives)
