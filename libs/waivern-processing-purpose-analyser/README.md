# waivern-processing-purpose-analyser

Identifies processing purposes (why personal data is processed) using pattern matching and optional LLM validation.

Supports `standard_input` and `source_code` schemas.

## Architecture

**Dict-based schema handling:**
- Message validates data against JSON Schema contract
- Reader returns TypedDict for compile-time type safety
- Handler processes dict using key access
- No dependency on SourceCodeAnalyser package

**How it works:**
1. Message validates input against `source_code` JSON schema
2. Reader transforms to TypedDict (no Pydantic models)
3. Handler processes dict: `file_data["raw_content"]`
4. Findings returned as typed models

**Why:**
- True plugin architecture - no cross-package imports
- Schema-driven communication via contracts
- Independent evolution of components

## Usage

```python
from waivern_core.message import Message
from waivern_core.schemas import Schema
from waivern_processing_purpose_analyser import ProcessingPurposeAnalyserFactory

factory = ProcessingPurposeAnalyserFactory(service_container)
analyser = factory.create({
    "pattern_matching": {"ruleset": "processing_purposes"},
    "llm_validation": {"enable_llm_validation": True}
})

# Message validates data against source_code schema
message = Message(
    id="analysis",
    schema=Schema("source_code", "1.0.0"),
    content={
        "schemaVersion": "1.0.0",
        "name": "Payment analysis",
        "data": [{
            "file_path": "/app/PaymentController.php",
            "raw_content": "<?php class PaymentController { function processPayment() {} }",
            "language": "php",
            "imports": [],
            "functions": [{"name": "processPayment", "line_start": 1, "line_end": 1}],
            "classes": [{"name": "PaymentController", "line_start": 1, "line_end": 1}],
            "metadata": {"file_size": 100, "line_count": 1, "last_modified": "2024-01-01T00:00:00Z"}
        }],
        "metadata": {"total_files": 1, "total_lines": 1, "analysis_timestamp": "2024-01-01T00:00:00Z"}
    }
)

result = analyser.process(
    input_schema=Schema("source_code", "1.0.0"),
    output_schema=Schema("processing_purpose_finding", "1.0.0"),
    message=message
)
```

## Testing

Use plain dicts for test data - Message validates against schema:

```python
test_data = {
    "schemaVersion": "1.0.0",
    "name": "Test",
    "data": [{
        "file_path": "/test.php",
        "raw_content": "<?php class Test {}",
        "language": "php",
        "imports": [],
        "functions": [],
        "classes": [],
        "metadata": {"file_size": 10, "line_count": 1, "last_modified": "2024-01-01T00:00:00Z"}
    }],
    "metadata": {"total_files": 1, "total_lines": 1, "analysis_timestamp": "2024-01-01T00:00:00Z"}
}

message = Message(
    id="test",
    schema=Schema("source_code", "1.0.0"),
    content=test_data
)
```

**Do not:**
- Import models from waivern-source-code-analyser
- Use Pydantic models for test data

**Do:**
- Use dicts matching JSON schema
- Let Message validate schema compliance
