"""Exception classes for waivern-rulesets package."""

from waivern_core import RulesetError


class RulesetURIParseError(RulesetError):
    """Raised when a ruleset URI cannot be parsed."""

    pass


class UnsupportedProviderError(RulesetError):
    """Raised when a ruleset provider is not supported."""

    pass


class RulesetNotFoundError(RulesetError):
    """Raised when a requested ruleset cannot be found."""

    pass
