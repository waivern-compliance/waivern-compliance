"""WCT plugins package.

This package provides the core plugin system and built-in plugins
for the Waivern Compliance Tool (WCT).
"""

from wct.plugins.base import (
    Plugin,
    PluginConfig,
    PluginError,
    PluginInputError,
    PluginProcessingError,
)
from wct.plugins.file_content_analyser import FileContentAnalyser
from wct.plugins.personal_data_analyser import (
    PersonalDataAnalyser,
    PersonalDataFinding,
    PersonalDataPattern,
)
from wct.schema import WctSchema

__all__ = (
    "Plugin",
    "PluginConfig",
    "PluginError",
    "PluginInputError",
    "PluginProcessingError",
    "WctSchema",
    "FileContentAnalyser",
    "PersonalDataAnalyser",
    "PersonalDataFinding",
    "PersonalDataPattern",
    "BUILTIN_PLUGINS",
)

BUILTIN_PLUGINS = (FileContentAnalyser, PersonalDataAnalyser)
