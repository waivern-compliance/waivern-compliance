# waivern-processing-purpose-analyser

Processing purpose analyser for WCF

## Overview

The Processing Purpose analyser identifies processing purposes (the reasons why personal data is being processed) in content using pattern matching and optional LLM validation. It supports both standard text input and structured source code analysis.

Key features:
- Pattern-based processing purpose identification using rulesets
- LLM validation for improved accuracy
- Source code analysis support (PHP)
- Confidence scoring
- Evidence extraction with context

## Installation

```bash
pip install waivern-processing-purpose-analyser
```

## Usage

```python
from waivern_processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeAnalyserConfig,
)

# Create analyser with LLM validation
config = ProcessingPurposeAnalyserConfig(
    pattern_matching={"ruleset": "processing_purposes"},
    llm_validation={"enable_llm_validation": True}
)
analyser = ProcessingPurposeAnalyser(config)

# Process standard input
messages = analyser.process_data(input_message)

# Or process source code
source_code_messages = analyser.process_data(source_code_message)
```
