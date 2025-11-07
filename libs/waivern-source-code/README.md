# waivern-source-code

Source code connector for WCF

## Overview

The Source Code connector parses source code files (currently PHP) using tree-sitter and extracts structured information about functions, classes, and code patterns for compliance analysis.

Key features:
- PHP source code parsing via tree-sitter
- Function and class extraction
- Code structure analysis
- Integrates with filesystem connector for file collection

## Installation

Basic installation:
```bash
pip install waivern-source-code
```

With tree-sitter support for PHP parsing:
```bash
pip install waivern-source-code[tree-sitter]
```

## Usage

```python
from waivern_source_code import SourceCodeConnector, SourceCodeConnectorConfig

# Parse PHP files in a directory
config = SourceCodeConnectorConfig(
    path="/path/to/source",
    language="php",
    pattern="*.php"
)
connector = SourceCodeConnector(config)
messages = connector.extract()
```
