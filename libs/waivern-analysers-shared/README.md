# waivern-analysers-shared

Shared utilities for analysers in the Waivern Compliance Framework.

## Overview

This package provides common utilities used by all analysers in the framework:

- **LLM Validation**: Unified LLM-based validation engine with prompt management
- **Analyser Utilities**: Common helper functions for pattern matching and evidence collection
- **Shared Types**: Common type definitions used across analysers

## Components

### LLM Validation (`llm_validation/`)

- `validation_engine.py`: Core LLM validation engine
- `prompt_manager.py`: Prompt template management
- `types.py`: LLM validation type definitions

### Analyser Utilities (`utilities/`)

- `evidence_utils.py`: Evidence collection and context extraction utilities
- `ruleset_manager.py`: Ruleset loading and caching utilities

### Types (`types.py`)

Common type definitions and enums used across multiple analysers.

## Dependencies

- `waivern-core`: Core framework abstractions
- `waivern-llm`: Multi-provider LLM abstraction
- `waivern-rulesets`: Ruleset loading and management

## Usage

This package is intended to be used as a dependency by specific analyser packages:

```python
from waivern_analysers_shared.llm_validation import LLMValidationEngine
from waivern_analysers_shared.utilities import RulesetManager
from waivern_analysers_shared.types import EvidenceContextSize
```

## Development

```bash
# Run tests
uv run pytest

# Type checking
bash scripts/type-check.sh

# Linting
bash scripts/lint.sh

# Formatting
bash scripts/format.sh
```

## License

MIT License - see the main repository LICENSE file for details.
