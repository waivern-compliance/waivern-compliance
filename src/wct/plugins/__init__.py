from wct.plugins.base import Plugin, PluginConfig
from wct.plugins.file_content_analyser import FileContentAnalyser
from wct.plugins.personal_data_analyser import PersonalDataAnalyser

__all__ = ("Plugin", "PluginConfig", "BUILTIN_PLUGINS")

BUILTIN_PLUGINS = (FileContentAnalyser, PersonalDataAnalyser)
