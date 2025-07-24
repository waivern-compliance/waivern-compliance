from wct.plugins.base import (
    Plugin,
    PluginConfig,
    PluginError,
    PluginInputError,
    PluginOutputError,
    PluginProcessingError,
)
from wct.schema import WctSchema
from wct.plugins.file_content_analyser import FileContentAnalyser
from wct.plugins.personal_data_analyser import (
    PersonalDataAnalyser,
    PersonalDataFinding,
    PersonalDataPattern,
)

__all__ = (
    "Plugin",
    "PluginConfig",
    "PluginError",
    "PluginInputError",
    "PluginOutputError",
    "PluginProcessingError",
    "WctSchema",
    "FileContentAnalyser",
    "PersonalDataAnalyser",
    "PersonalDataFinding",
    "PersonalDataPattern",
    "BUILTIN_PLUGINS",
)

BUILTIN_PLUGINS = (FileContentAnalyser, PersonalDataAnalyser)
