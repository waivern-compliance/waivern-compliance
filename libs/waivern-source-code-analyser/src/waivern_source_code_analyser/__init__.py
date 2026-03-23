"""Source code analyser for WCF.

This package provides SourceCodeAnalyser, which transforms file content
from standard_input schema to source_code schema with language detection.

Use in pipeline: FilesystemConnector → SourceCodeAnalyser → ProcessingPurposeAnalyser

Note: Structural extraction (functions, classes) has been intentionally removed.
LLMs understand code structure natively from raw content. This analyser focuses
on language detection and can be extended with compliance-relevant metadata
(dependencies, frameworks, security patterns) in the future.
"""

from .analyser import SourceCodeAnalyser
from .analyser_config import SourceCodeAnalyserConfig
from .analyser_factory import SourceCodeAnalyserFactory
from .file_content_provider import SourceCodeFileContentProvider

__all__ = [
    "SourceCodeAnalyser",
    "SourceCodeAnalyserConfig",
    "SourceCodeAnalyserFactory",
    "SourceCodeFileContentProvider",
]
