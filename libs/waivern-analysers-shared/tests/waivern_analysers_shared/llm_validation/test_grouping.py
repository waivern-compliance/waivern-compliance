"""Tests for grouping strategies."""

from waivern_core.schemas.finding_types import BaseFindingEvidence, BaseFindingModel

from waivern_analysers_shared.llm_validation.grouping import (
    ConcernGroupingStrategy,
    SourceGroupingStrategy,
)


class MockFinding(BaseFindingModel):
    """Simple finding for testing with purpose and source fields."""

    purpose: str
    source: str


def make_finding(finding_id: str, purpose: str, source: str) -> MockFinding:
    """Create a mock finding with required fields."""
    return MockFinding(
        id=finding_id,
        purpose=purpose,
        source=source,
        evidence=[BaseFindingEvidence(content="test evidence")],
        matched_patterns=["test_pattern"],
    )


class MockConcernProvider:
    """Mock ConcernProvider that groups by purpose."""

    @property
    def concern_key(self) -> str:
        return "purpose"

    def get_concern(self, finding: MockFinding) -> str:
        return finding.purpose


class MockSourceProvider:
    """Mock SourceProvider that groups by source."""

    def get_source_id(self, finding: MockFinding) -> str:
        return finding.source

    def get_source_content(self, source_id: str) -> str | None:
        return None  # Not needed for grouping tests


class TestConcernGroupingStrategy:
    """Tests for ConcernGroupingStrategy."""

    def test_concern_grouping_groups_findings_by_concern_value(self) -> None:
        """Should group findings by the value returned from ConcernProvider.get_concern()."""
        # Arrange
        provider = MockConcernProvider()
        strategy = ConcernGroupingStrategy(provider)
        findings = [
            make_finding("1", purpose="Payment", source="file1.py"),
            make_finding("2", purpose="Analytics", source="file2.py"),
            make_finding("3", purpose="Payment", source="file3.py"),
        ]

        # Act
        groups = strategy.group(findings)

        # Assert
        assert len(groups) == 2
        assert len(groups["Payment"]) == 2
        assert len(groups["Analytics"]) == 1
        assert groups["Payment"][0].id == "1"
        assert groups["Payment"][1].id == "3"
        assert groups["Analytics"][0].id == "2"

    def test_concern_grouping_preserves_all_findings(self) -> None:
        """Should not lose any findings during grouping."""
        # Arrange
        provider = MockConcernProvider()
        strategy = ConcernGroupingStrategy(provider)
        findings = [
            make_finding("1", purpose="Payment", source="file1.py"),
            make_finding("2", purpose="Analytics", source="file2.py"),
            make_finding("3", purpose="Payment", source="file3.py"),
            make_finding("4", purpose="Logging", source="file4.py"),
        ]

        # Act
        groups = strategy.group(findings)

        # Assert
        all_grouped_findings = [f for group in groups.values() for f in group]
        assert len(all_grouped_findings) == len(findings)
        assert set(f.id for f in all_grouped_findings) == set(f.id for f in findings)


class TestSourceGroupingStrategy:
    """Tests for SourceGroupingStrategy."""

    def test_source_grouping_groups_findings_by_source_id(self) -> None:
        """Should group findings by the value returned from SourceProvider.get_source_id()."""
        # Arrange
        provider = MockSourceProvider()
        strategy = SourceGroupingStrategy(provider)
        findings = [
            make_finding("1", purpose="Payment", source="file1.py"),
            make_finding("2", purpose="Analytics", source="file2.py"),
            make_finding("3", purpose="Logging", source="file1.py"),
        ]

        # Act
        groups = strategy.group(findings)

        # Assert
        assert len(groups) == 2
        assert len(groups["file1.py"]) == 2
        assert len(groups["file2.py"]) == 1
        assert groups["file1.py"][0].id == "1"
        assert groups["file1.py"][1].id == "3"
        assert groups["file2.py"][0].id == "2"

    def test_source_grouping_preserves_all_findings(self) -> None:
        """Should not lose any findings during grouping."""
        # Arrange
        provider = MockSourceProvider()
        strategy = SourceGroupingStrategy(provider)
        findings = [
            make_finding("1", purpose="Payment", source="file1.py"),
            make_finding("2", purpose="Analytics", source="file2.py"),
            make_finding("3", purpose="Logging", source="file1.py"),
            make_finding("4", purpose="Metrics", source="file3.py"),
        ]

        # Act
        groups = strategy.group(findings)

        # Assert
        all_grouped_findings = [f for group in groups.values() for f in group]
        assert len(all_grouped_findings) == len(findings)
        assert set(f.id for f in all_grouped_findings) == set(f.id for f in findings)
