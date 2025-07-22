from wct.plugins.base import Plugin
from wct.plugins.file_content_analyser import FileContentAnalyser
from wct.plugins.personal_data_analyser import PersonalDataAnalyser

__all__ = ("Plugin", "BUILTIN_PLUGINS")

BUILTIN_PLUGINS = (FileContentAnalyser, PersonalDataAnalyser)
