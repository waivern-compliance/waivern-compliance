from __future__ import annotations

from typing import Any

from typing_extensions import Self

from waivern_analyser.rulesets import ReportItem, Ruleset
from waivern_wordpress_plugin.connectors import WordpressFinding


class WordpressRuleset(Ruleset):
    @classmethod
    def get_name(cls) -> str:
        return "wordpress"

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> Self:
        return cls()

    def run(self, finding: WordpressFinding) -> WordpressReportItem:
        return WordpressReportItem()


class WordpressReportItem(ReportItem):
    pass
