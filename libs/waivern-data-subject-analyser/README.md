# waivern-data-subject-analyser

Data subject analyser for WCF

## Overview

The Data Subject analyser identifies data subjects (individuals or groups whose personal data is being processed) in content using pattern matching and optional LLM validation.

Key features:
- Pattern-based data subject identification using rulesets
- LLM validation for improved accuracy
- Confidence scoring
- Evidence extraction with context

## Installation

```bash
pip install waivern-data-subject-analyser
```

## Usage

```python
from waivern_data_subject_analyser import (
    DataSubjectAnalyser,
    DataSubjectAnalyserConfig,
)

# Create analyser with LLM validation
config = DataSubjectAnalyserConfig(
    pattern_matching={"ruleset": "local/data_subjects/1.0.0"},
    llm_validation={"enable_llm_validation": True}
)
analyser = DataSubjectAnalyser(config)

# Process data
messages = analyser.process_data(input_message)
```
