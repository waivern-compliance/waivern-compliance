from waivern_rulesets_core import Ruleset, RulesetInputSchema, RulesetOutputSchema

from waivern_analyser.plugin import Plugin


class WordpressRulesetInputSchema(RulesetInputSchema):
    pass


class WordpressRulesetOutputSchema(RulesetOutputSchema):
    pass


class WordpressRuleset(Ruleset):
    def run(self, input: RulesetInputSchema) -> RulesetOutputSchema:
        return RulesetOutputSchema()


class WordpressRulesetPlugin(Plugin):
    @classmethod
    def get_name(cls) -> str:
        return "wordpress"

    @classmethod
    def get_connectors(cls):
        return ()

    @classmethod
    def get_rulesets(cls):
        return (WordpressRuleset(),)
