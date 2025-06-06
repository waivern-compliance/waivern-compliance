# Waivern Source Code Connector

A connector for analyzing source code repositories in the Waivern Analyser ecosystem. This connector extracts information from source code files, directories, and repository structures.

## Overview

The Source Code Connector is designed to:
- Scan source code repositories
- Extract file metadata and content
- Analyze code structure and patterns
- Provide data for compliance analysis

## Features

- **Multi-language support**: Analyze various programming languages
- **File filtering**: Include/exclude files based on patterns
- **Metadata extraction**: File sizes, modification dates, permissions
- **Content analysis**: Extract code metrics and structure information
- **Repository analysis**: Git history, branch information, and commit data

## Usage

### Basic Usage

```python
from waivern_connectors_source_code import (
    SourceCodeConnector,
    SourceCodeConnectorInputSchema
)

# Create connector instance
connector = SourceCodeConnector()

# Define input parameters
input_data = SourceCodeConnectorInputSchema(
    # Add input parameters here when implemented
)

# Run the connector
result = connector.run(input_data)
```

### Input Schema

The `SourceCodeConnectorInputSchema` defines the parameters for source code analysis:

```python
@dataclass(frozen=True, slots=True)
class SourceCodeConnectorInputSchema(ConnectorInputSchema):
    # TODO: Define input parameters such as:
    # repository_path: str
    # include_patterns: list[str] = None
    # exclude_patterns: list[str] = None
    # max_file_size: int = 1024 * 1024  # 1MB
    # follow_symlinks: bool = False
    # analyze_git_history: bool = True
    pass
```

### Output Schema

The `SourceCodeConnectorOutputSchema` contains the analysis results:

```python
@dataclass(frozen=True, slots=True)
class SourceCodeConnectorOutputSchema(ConnectorOutputSchema):
    # TODO: Define output structure such as:
    # files_analyzed: int
    # total_lines_of_code: int
    # languages_detected: list[str]
    # file_metadata: list[dict]
    # code_metrics: dict
    # repository_info: dict
    pass
```

## Configuration Examples

### Analyze a Local Repository

```python
input_data = SourceCodeConnectorInputSchema(
    repository_path="/path/to/your/repo",
    include_patterns=["*.py", "*.js", "*.java"],
    exclude_patterns=["*/node_modules/*", "*/venv/*", "*.pyc"],
    analyze_git_history=True
)
```

### Analyze with Size Limits

```python
input_data = SourceCodeConnectorInputSchema(
    repository_path="/path/to/your/repo",
    max_file_size=512 * 1024,  # 512KB limit
    follow_symlinks=False
)
```

## Supported File Types

The connector can analyze various file types:

### Programming Languages
- Python (`.py`)
- JavaScript/TypeScript (`.js`, `.ts`)
- Java (`.java`)
- C/C++ (`.c`, `.cpp`, `.h`)
- C# (`.cs`)
- Go (`.go`)
- Rust (`.rs`)
- PHP (`.php`)
- Ruby (`.rb`)

### Configuration Files
- JSON (`.json`)
- YAML (`.yml`, `.yaml`)
- TOML (`.toml`)
- XML (`.xml`)
- INI (`.ini`)

### Documentation
- Markdown (`.md`)
- reStructuredText (`.rst`)
- Plain text (`.txt`)

## Output Structure

The connector provides structured output containing:

### File Metadata
```python
{
    "path": "src/main.py",
    "size": 1024,
    "modified": "2024-01-01T12:00:00Z",
    "language": "python",
    "lines_of_code": 45,
    "complexity": 3
}
```

### Repository Information
```python
{
    "total_files": 150,
    "total_size": 2048576,
    "languages": ["python", "javascript", "yaml"],
    "git_info": {
        "branch": "main",
        "last_commit": "abc123",
        "commit_count": 245
    }
}
```

### Code Metrics
```python
{
    "total_lines": 5000,
    "code_lines": 3500,
    "comment_lines": 800,
    "blank_lines": 700,
    "cyclomatic_complexity": 125,
    "maintainability_index": 85
}
```

## Integration with Rulesets

The Source Code Connector output is designed to work with various rulesets:

- **Security rulesets**: Analyze for security vulnerabilities
- **Quality rulesets**: Check code quality metrics
- **Compliance rulesets**: Ensure coding standards compliance
- **License rulesets**: Verify license compatibility

## Performance Considerations

- **Large repositories**: The connector handles large codebases efficiently
- **Memory usage**: Streaming analysis for memory-efficient processing
- **Parallel processing**: Multi-threaded file analysis when possible
- **Caching**: Results can be cached for repeated analysis

## Error Handling

The connector handles various error conditions:

- **Permission errors**: Graceful handling of inaccessible files
- **Encoding issues**: Automatic encoding detection and fallback
- **Corrupted files**: Skip and report problematic files
- **Network issues**: Timeout and retry for remote repositories

## Development Status

⚠️ **Note**: This connector is currently in early development. The implementation contains placeholder code and TODOs. The actual functionality is being developed.

### Current Status
- ✅ Basic structure and interfaces defined
- ⚠️ Input/output schemas need implementation
- ⚠️ Core analysis logic needs implementation
- ⚠️ File type detection needs implementation
- ⚠️ Git integration needs implementation

### Planned Features
- File content analysis
- Code metrics calculation
- Git history analysis
- Language detection
- Dependency analysis
- Security scanning integration

## Contributing

To contribute to the Source Code Connector:

1. **Implement missing schemas**: Define proper input/output structures
2. **Add file analysis logic**: Implement code parsing and metrics
3. **Add language support**: Extend support for more programming languages
4. **Improve performance**: Optimize for large repositories
5. **Add tests**: Comprehensive test coverage for all features

### Development Setup

```bash
# Navigate to the connector directory
cd src/connectors/source_code

# Install in development mode
uv pip install -e .

# Run tests
uv run pytest tests/
```

## Dependencies

- `waivern-connectors-core`: Base connector framework
- Additional dependencies will be added as features are implemented

## License

This package is part of the Waivern Analyser project and follows the same license terms.