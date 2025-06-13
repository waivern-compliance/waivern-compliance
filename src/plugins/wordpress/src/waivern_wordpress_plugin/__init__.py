"""Wordpress plugin."""

from plugins.wordpress.src.waivern_wordpress_plugin.connectors import (
    WordpressProjectConnector,
)
from waivern_analyser.connectors import Connector
from waivern_analyser.plugins import Plugin
from waivern_analyser.rulesets import Finding, ReportItem, Ruleset
from waivern_analyser.sources import Source


class WordpressRulesetInputSchema(Finding):
    pass


class WordpressRulesetOutputSchema(ReportItem):
    pass


class WordpressRuleset(Ruleset):
    def run(self, input: Finding) -> ReportItem:
        return ReportItem()


class WordpressPlugin(Plugin):
    @classmethod
    def get_name(cls) -> str:
        return "wordpress"

    @classmethod
    def get_source_types(cls) -> tuple[type[Source], ...]:
        return ()

    @classmethod
    def get_connector_types(cls) -> tuple[type[Connector], ...]:
        return (WordpressProjectConnector,)

    @classmethod
    def get_ruleset_types(cls) -> tuple[type[Ruleset], ...]:
        return (WordpressRuleset,)
