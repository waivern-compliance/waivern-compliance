# Processor Input Requirements

This document describes how processors declare and handle input schemas in the Waivern Compliance Framework, including support for multi-schema fan-in.

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [InputRequirement](#inputrequirement)
4. [Declaring Input Requirements](#declaring-input-requirements)
   - [Single-Schema Input](#single-schema-input)
   - [Schema Version Alternatives](#schema-version-alternatives)
   - [Multi-Schema Fan-In](#multi-schema-fan-in)
5. [The process() Method](#the-process-method)
   - [Signature](#signature)
   - [Same-Schema Fan-In](#same-schema-fan-in)
   - [Multi-Schema Routing](#multi-schema-routing)
6. [Schema Readers](#schema-readers)
7. [Validation](#validation)
8. [Model Reference](#model-reference)
9. [Examples](#examples)

---

## Overview

### Problem

Compliance analysis often requires synthesising data from multiple sources with different schemas. For example, a GDPR Article 30 report requires:

- Personal data findings
- Processing purpose findings
- Data subject findings

A single-input processor interface cannot express these requirements.

### Solution

Processors declare **input requirements**—lists of valid input schema combinations. The Planner validates that runbook inputs match a declared combination, and the Executor passes all matched inputs to a unified `process()` method.

### Key Insight

Schema-driven validation at **plan time** catches mismatches before expensive execution. Processors remain pure functions—they don't know about runbooks or orchestration, only about schemas and data transformation.

---

## Design Principles

### 1. Processors Are Pure Functions

Processors accept schema-compliant inputs and produce schema-compliant outputs. They don't know about runbooks, file paths, or orchestration.

### 2. Schema as Contract

Input requirements use schemas as the contract between components. This enables:

- **Type safety**—Compile-time-like checks at plan time
- **Version compatibility**—Explicit schema versions in requirements
- **Self-documentation**—Requirements declare the interface

### 3. Exact Set Matching

The Planner uses **exact set matching** on unique schemas. This eliminates ambiguity:

- Provided schemas must match exactly one requirement combination
- No partial matching or implicit optional schemas
- Clear error messages when mismatched

### 4. Merge-First Pattern

When multiple inputs have the same schema, processors merge them before analysis. This enables:

- **Cross-source correlation**—Detect patterns across sources
- **Holistic analysis**—Complete view of all data
- **Provenance preservation**—Each item retains its source metadata

---

## InputRequirement

`InputRequirement` is a frozen dataclass declaring a required input schema:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class InputRequirement:
    """Declares a required input schema for a processor."""
    schema_name: str   # e.g., "personal_data_finding"
    version: str       # e.g., "1.0.0"
```

### Usage

```python
from waivern_core import InputRequirement

# Declare a single requirement
req = InputRequirement("standard_input", "1.0.0")

# Access fields
print(req.schema_name)  # "standard_input"
print(req.version)      # "1.0.0"
```

### Immutability

`frozen=True` ensures requirements are hashable and can be used in sets for matching logic.

---

## Declaring Input Requirements

### Single-Schema Input

Most processors accept a single schema type:

```python
class PersonalDataAnalyser(Analyser):
    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [
            [InputRequirement("standard_input", "1.0.0")],
        ]
```

This processor accepts any number of `standard_input/1.0.0` messages.

### Schema Version Alternatives

Support multiple schema versions by listing alternatives:

```python
class FlexibleAnalyser(Analyser):
    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [
            [InputRequirement("standard_input", "1.0.0")],
            [InputRequirement("standard_input", "1.1.0")],
            [InputRequirement("standard_input", "2.0.0")],
        ]
```

Each inner list is a valid combination. The Planner selects the first matching combination.

### Multi-Schema Fan-In

For processors that synthesise multiple schema types:

```python
class GdprArticle30Analyser(Analyser):
    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [
            # Full combination: all three schemas
            [
                InputRequirement("personal_data_finding", "1.0.0"),
                InputRequirement("processing_purpose_finding", "1.0.0"),
                InputRequirement("data_subject_finding", "1.0.0"),
            ],
            # Partial combination: without data subjects
            [
                InputRequirement("personal_data_finding", "1.0.0"),
                InputRequirement("processing_purpose_finding", "1.0.0"),
            ],
        ]
```

The runbook must provide **exactly** the schemas in one combination (no more, no less).

---

## The process() Method

### Signature

```python
@abstractmethod
def process(
    self,
    inputs: list[Message],
    output_schema: Schema,
) -> Message:
    """Process input data and produce output.

    Args:
        inputs: List of input messages. May contain multiple messages
               of the same schema (same-schema fan-in) or different
               schemas (multi-schema fan-in).
        output_schema: Expected output schema for validation.

    Returns:
        Output message conforming to output_schema.
    """
```

### Same-Schema Fan-In

When multiple artifacts provide the same schema, all messages are passed to `process()`:

```yaml
# Runbook
artifacts:
  mysql_data:
    source:
      type: mysql
  postgres_data:
    source:
      type: postgres
  combined_analysis:
    inputs:
      - mysql_data
      - postgres_data
    process:
      type: personal_data
```

The processor receives both messages and should merge them:

```python
def process(self, inputs: list[Message], output_schema: Schema) -> Message:
    # Merge all items from all inputs
    all_items = []
    for message in inputs:
        reader = self._load_reader(message.schema)
        typed_data = reader.read(message.content)
        all_items.extend(typed_data.data)

    # Process the combined dataset
    findings = self._analyse(all_items)
    return self._create_output(findings, output_schema)
```

### Multi-Schema Routing

When inputs have different schemas, route to appropriate handlers:

```python
def process(self, inputs: list[Message], output_schema: Schema) -> Message:
    # Determine which schema combination we received
    schemas = frozenset((msg.schema.name, msg.schema.version) for msg in inputs)

    if schemas == {
        ("personal_data_finding", "1.0.0"),
        ("processing_purpose_finding", "1.0.0"),
        ("data_subject_finding", "1.0.0"),
    }:
        return self._process_full(inputs, output_schema)

    elif schemas == {
        ("personal_data_finding", "1.0.0"),
        ("processing_purpose_finding", "1.0.0"),
    }:
        return self._process_without_subjects(inputs, output_schema)

    else:
        # Should never happen if Planner validated correctly
        raise ValueError(f"Unexpected schema combination: {schemas}")
```

---

## Schema Readers

Readers transform wire format (JSON dict) into typed internal models.

### Location

```
{package}/schema_readers/{schema_name}_{version}.py
```

Example: `waivern_personal_data_analyser/schema_readers/standard_input_1_0_0.py`

### Structure

```python
# schema_readers/standard_input_1_0_0.py
from waivern_core.schemas import StandardInputDataModel

def read(content: dict) -> StandardInputDataModel:
    """Transform wire format to typed model."""
    return StandardInputDataModel.model_validate(content)
```

### Loading Readers Dynamically

```python
import importlib
from types import ModuleType

def _load_reader(self, schema: Schema) -> ModuleType:
    """Load reader module for a schema."""
    module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
    package = self.__class__.__module__.rsplit('.', 1)[0]
    return importlib.import_module(f"{package}.schema_readers.{module_name}")
```

### Usage in process()

```python
def process(self, inputs: list[Message], output_schema: Schema) -> Message:
    all_items = []
    for message in inputs:
        reader = self._load_reader(message.schema)
        typed_data = reader.read(message.content)  # dict → Pydantic model
        all_items.extend(typed_data.data)

    # Now work with strongly-typed models
    findings = []
    for item in all_items:
        # item.content, item.metadata are typed
        result = self._analyse_item(item)
        findings.append(result)

    return self._create_output(findings, output_schema)
```

---

## Validation

### Plan-Time Validation

The Planner validates input compatibility before execution:

1. **Collect provided schemas** from upstream artifacts
2. **Match against requirements** using exact set matching
3. **Validate reader availability** for all matched schemas
4. **Report clear errors** if no match found

```
Artifact 'gdpr_report': no matching input requirement.
Provided: {(personal_data_finding, 1.0.0)}
Available: [
  {(personal_data_finding, 1.0.0), (processing_purpose_finding, 1.0.0), (data_subject_finding, 1.0.0)},
  {(personal_data_finding, 1.0.0), (processing_purpose_finding, 1.0.0)}
]
```

### Matching Rules

1. **Exact set match**—Provided schemas must exactly match one requirement
2. **Multiple messages OK**—Same schema can appear multiple times
3. **Order irrelevant**—Only the set of unique schemas matters

```python
# Requirement: [InputRequirement("personal_data_finding", "1.0.0")]
# Provided: 1 personal_data_finding → ✓ matches
# Provided: 3 personal_data_findings → ✓ matches (same schema set)
# Provided: 1 personal_data + 1 processing_purpose → ✗ unexpected schema
```

---

## Model Reference

### InputRequirement

```python
@dataclass(frozen=True)
class InputRequirement:
    schema_name: str
    version: str
```

### Processor (Base Class)

```python
class Processor(ABC):
    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Processor identifier."""

    @classmethod
    @abstractmethod
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        """Valid input schema combinations."""

    @classmethod
    @abstractmethod
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Output schemas this processor can produce."""

    @abstractmethod
    def process(
        self,
        inputs: list[Message],
        output_schema: Schema,
    ) -> Message:
        """Process inputs and produce output."""
```

### Analyser (Subclass)

```python
class Analyser(Processor):
    """Base class for compliance analysers.

    Analysers detect compliance-relevant patterns in data and produce
    structured findings. They are the primary processing component in WCF.
    """
```

---

## Examples

### Example 1: Single-Schema Analyser

```python
from typing import override
from waivern_core import Analyser, InputRequirement, Message
from waivern_core.schemas import Schema

class PersonalDataAnalyser(Analyser):
    @classmethod
    @override
    def get_name(cls) -> str:
        return "personal_data"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [[InputRequirement("standard_input", "1.0.0")]]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("personal_data_finding", "1.0.0")]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        # Merge all inputs (same-schema fan-in)
        all_items = []
        for message in inputs:
            reader = self._load_reader(message.schema)
            all_items.extend(reader.read(message.content).data)

        # Analyse each item
        findings = []
        for item in all_items:
            findings.extend(self._find_personal_data(item))

        return self._create_output(findings, output_schema)
```

### Example 2: Multi-Schema Synthesiser

```python
class GdprArticle30Analyser(Analyser):
    @classmethod
    @override
    def get_name(cls) -> str:
        return "gdpr_article_30"

    @classmethod
    @override
    def get_input_requirements(cls) -> list[list[InputRequirement]]:
        return [
            # Full: personal data + purposes + subjects
            [
                InputRequirement("personal_data_finding", "1.0.0"),
                InputRequirement("processing_purpose_finding", "1.0.0"),
                InputRequirement("data_subject_finding", "1.0.0"),
            ],
            # Partial: personal data + purposes only
            [
                InputRequirement("personal_data_finding", "1.0.0"),
                InputRequirement("processing_purpose_finding", "1.0.0"),
            ],
        ]

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        return [Schema("gdpr_article_30_finding", "1.0.0")]

    @override
    def process(self, inputs: list[Message], output_schema: Schema) -> Message:
        schemas = frozenset((m.schema.name, m.schema.version) for m in inputs)

        if len(schemas) == 3:
            return self._process_full(inputs, output_schema)
        else:
            return self._process_partial(inputs, output_schema)

    def _process_full(self, inputs: list[Message], output_schema: Schema) -> Message:
        personal_data = self._extract_by_schema(inputs, "personal_data_finding")
        purposes = self._extract_by_schema(inputs, "processing_purpose_finding")
        subjects = self._extract_by_schema(inputs, "data_subject_finding")

        activities = self._build_processing_activities(personal_data, purposes, subjects)
        return self._create_output(activities, output_schema)

    def _extract_by_schema(self, inputs: list[Message], schema_name: str) -> list:
        """Extract all items from messages matching schema name."""
        results = []
        for msg in inputs:
            if msg.schema.name == schema_name:
                reader = self._load_reader(msg.schema)
                results.extend(reader.read(msg.content).findings)
        return results
```

### Example 3: Corresponding Runbook

```yaml
name: "GDPR Article 30 Analysis"
description: "Generate GDPR Records of Processing Activities"

artifacts:
  db_schema:
    source:
      type: mysql
      properties:
        database: production

  personal_data:
    inputs: db_schema
    process:
      type: personal_data

  processing_purposes:
    inputs: db_schema
    process:
      type: processing_purpose

  data_subjects:
    inputs: db_schema
    process:
      type: data_subject

  gdpr_ropa:
    inputs:
      - personal_data
      - processing_purposes
      - data_subjects
    process:
      type: gdpr_article_30
    output: true
```

---

## Related Documentation

- [Runbook Format](../../waivern-orchestration/docs/runbook-format.md) - Artifact-centric runbook structure
- [Child Runbook Composition](../../waivern-orchestration/docs/child-runbook-composition.md) - Modular runbook design
