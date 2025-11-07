# waivern-filesystem

Filesystem connector for WCF

## Overview

The Filesystem connector reads file content from the local filesystem and transforms it into the standard_input schema format for analysis by WCF analysers.

Key features:
- Read single files or entire directories
- Automatic text encoding detection
- Support for various file types (txt, md, json, yaml, etc.)
- Recursive directory traversal
- File filtering by extension or pattern

## Installation

```bash
pip install waivern-filesystem
```

## Usage

```python
from waivern_filesystem import FilesystemConnector, FilesystemConnectorConfig

# Read a single file
config = FilesystemConnectorConfig(path="./sample_file.txt")
connector = FilesystemConnector(config)
messages = connector.extract()

# Read all files in a directory
config = FilesystemConnectorConfig(
    path="./documents/",
    recursive=True,
    file_extensions=[".txt", ".md"]
)
connector = FilesystemConnector(config)
messages = connector.extract()
```

## Runbook Configuration

```yaml
connectors:
  - name: "filesystem_reader"
    type: "filesystem"
    properties:
      path: "./sample_file.txt"
```

## Development

This package is part of the Waivern Compliance Framework monorepo. For development guidelines, testing, and contribution instructions, please refer to the main project documentation.
