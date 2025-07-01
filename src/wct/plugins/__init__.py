from wct.plugins.base import Plugin
from wct.plugins.wordpress import WordpressPlugin

__all__ = ("Plugin", "BUILTIN_PLUGINS")

BUILTIN_PLUGINS = (WordpressPlugin,)
