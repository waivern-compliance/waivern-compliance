# waivern-community

Community-contributed connectors, analysers, and rulesets for the Waivern Compliance Framework.

## Overview

`waivern-community` provides a comprehensive collection of built-in components for the Waivern Compliance Framework, including:

- **Connectors**: Extract data from various sources (MySQL, SQLite, filesystem, source code)
- **Analysers**: Perform compliance analysis (personal data detection, processing purpose identification)
- **Rulesets**: YAML-based pattern definitions for compliance checks
- **Prompts**: LLM prompt templates for AI-powered analysis

## Installation

### Basic Installation

```bash
pip install waivern-community
```

### With Optional Dependencies

```bash
# MySQL connector support (pymysql, cryptography)
pip install waivern-community[mysql]

# Source code connector support (tree-sitter, tree-sitter-php)
pip install waivern-community[source-code]

# All optional dependencies
pip install waivern-community[all]
```

**Note:** WCT installs `waivern-community[all]` by default, so all connectors are available out of the box.

## Components

### Connectors

- **MySQL Connector** (`mysql`) - Extract data from MySQL databases
- **SQLite Connector** (`sqlite`) - Extract data from SQLite databases
- **Filesystem Connector** (`filesystem`) - Read files from filesystem
- **Source Code Connector** (`source_code`) - Parse and analyse source code files

### Analysers

- **Personal Data Analyser** (`personal_data`) - Detect and classify personal data
- **Processing Purpose Analyser** (`processing_purpose`) - Identify GDPR processing purposes

### Rulesets

Pre-configured pattern libraries for:
- Personal data detection
- GDPR processing purpose identification
- Custom compliance patterns

## Usage

```python
from waivern_community.connectors.mysql import MySQLConnector
from waivern_community.analysers.personal_data import PersonalDataAnalyser

# Use connectors and analysers in your WCT runbooks
```

## Requirements

- Python 3.12+
- waivern-core
- waivern-llm

## Optional Dependencies

- **MySQL support**: `pymysql`, `cryptography`
- **Source code parsing**: `tree-sitter`, `tree-sitter-php`

## Development

See the main [Waivern Compliance Framework](https://github.com/waivern-compliance/waivern-compliance) repository for development guidelines.

## License

[License information to be added]
