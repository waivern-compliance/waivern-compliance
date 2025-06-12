"""Wordpress plugin."""

from waivern_analyser.connectors import Connector
from waivern_analyser.plugins import Plugin
from waivern_analyser.rulesets import Ruleset, RulesetInputSchema, RulesetOutputSchema
from waivern_analyser.sources import Source


class WordpressRulesetInputSchema(RulesetInputSchema):
    pass


class WordpressRulesetOutputSchema(RulesetOutputSchema):
    pass


class WordpressRuleset(Ruleset):
    def run(self, input: RulesetInputSchema) -> RulesetOutputSchema:
        return RulesetOutputSchema()


class WordpressPlugin(Plugin):
    @classmethod
    def get_name(cls) -> str:
        return "wordpress"

    @classmethod
    def get_sources(cls) -> tuple[type[Source], ...]:
        return ()

    @classmethod
    def get_connectors(cls) -> tuple[type[Connector], ...]:
        return ()

    @classmethod
    def get_rulesets(cls) -> tuple[type[Ruleset], ...]:
        # TODO: Add rulesets here
        return (WordpressRuleset,)
