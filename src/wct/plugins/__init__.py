from wct.plugins.base import (
    Plugin,
    PluginConfig,
    PluginError,
    PluginInputError,
    PluginProcessingError,
)
from wct.plugins.file_content_analyser import FileContentAnalyser
from wct.plugins.personal_data_analyser import PersonalDataAnalyser

__all__ = (
    "Plugin",
    "PluginConfig",
    "PluginError",
    "PluginInputError",
    "PluginProcessingError",
    "BUILTIN_PLUGINS",
)

BUILTIN_PLUGINS = (FileContentAnalyser, PersonalDataAnalyser)
