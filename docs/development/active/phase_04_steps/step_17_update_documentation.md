# Task: Update Documentation and Examples

- **Phase:** 4 - Fix ProcessingPurposeAnalyser Schema Coupling
- **Status:** TODO
- **Prerequisites:** Steps 13-16 complete (Dict-based schema handling implemented, dependency removed)
- **Step:** 17 of 17

## Context

This is the final step in removing hardcoded dependencies on SourceCodeAnalyser's typed Pydantic models. Steps 13-16 implemented dict-based schema handling. Now we need to update documentation to reflect the architectural changes.

**See:** the parent implementation plan (`docs/development/active/phase_04_fix_processing_purpose_analyser_schema_coupling.md`) for full context.

## Purpose

Update README, docstrings, and inline documentation to explain dict-based schema handling approach, reliance on Message validation, and independence from SourceCodeAnalyser package. Ensure users understand the architectural principles and how to work with the analyser.

## Problem

Current documentation reflects old typed model approach:

**Location:** `libs/waivern-processing-purpose-analyser/README.md`

**Issues:**
1. May reference SourceCodeAnalyser dependency
2. May show examples using typed models
3. May not explain dict-based schema handling
4. May not document schema contract reliance
5. May not explain Message validation role

## Solution

Update documentation to reflect new architecture:

**Changes needed:**
1. Update README.md with dict-based approach
2. Add section on schema handling and validation
3. Document independence from SourceCodeAnalyser
4. Update docstrings in key files
5. Add examples showing dict-based usage
6. Document architectural principles

## Implementation

### Files to Modify

**1. Package README:**
`libs/waivern-processing-purpose-analyser/README.md`

**2. Handler docstrings:**
`libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/source_code_schema_input_handler.py`

**3. Reader docstrings:**
`libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/schema_readers/source_code_1_0_0.py`

**4. Analyser docstrings:**
`libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/analyser.py`

### Documentation Changes Required

#### 1. Update README.md

**Section to add: Schema Handling**

```markdown
## Schema Handling

### Dict-Based Schema Processing

ProcessingPurposeAnalyser uses dictionary-based schema handling for all input data. This approach:

- **Relies on JSON schema contracts** - Components communicate through JSON schemas, not typed models
- **Trusts Message validation** - Message objects validate data against schemas before analysis
- **Enables independence** - No direct dependencies on other analyser packages
- **Supports schema evolution** - Dict-based access adapts to schema changes

### How It Works

1. **Message Validation:**
   ```python
   # Message validates data against JSON schema
   message = Message(
       schema=Schema(name="source_code", version="1.0.0"),
       data={
           "data": [
               {
                   "file_path": "/app/Controller.php",
                   "raw_content": "<?php ...",
                   "imports": [],
                   "functions": [],
                   "classes": []
               }
           ],
           "analysis_metadata": {...}
       }
   )
   ```

2. **Schema Reader:**
   ```python
   # Reader wraps validated dict data
   reader = SourceCode_1_0_0_Reader()
   schema_data = reader.read(message)
   # schema_data.data is the dict from message.data
   ```

3. **Handler Processing:**
   ```python
   # Handler processes dict using key access
   def analyse_source_code_data(self, data: dict[str, Any]) -> list[Finding]:
       for file_data in data["data"]:
           file_path = file_data["file_path"]
           raw_content = file_data["raw_content"]
           imports = file_data.get("imports", [])
           # ... pattern matching on dict data
   ```

### No Direct Dependencies

ProcessingPurposeAnalyser does **not** depend on `waivern-source-code-analyser` package. It communicates with SourceCodeAnalyser only through the `source_code` JSON schema contract.

**Dependencies:**
- `waivern-core` - Base abstractions (Message, Schema, Analyser, etc.)
- `waivern-rulesets` - Shared pattern rulesets
- `waivern-analysers-shared` - Shared analyser utilities
- `waivern-llm` - LLM validation integration

This enables:
- ✅ Independent installation and versioning
- ✅ True plugin architecture
- ✅ No circular dependencies
- ✅ Schema-driven communication
```

**Section to add: Working with Source Code Schema**

```markdown
## Working with Source Code Schema

### Input Schema: source_code v1.0.0

ProcessingPurposeAnalyser can process `source_code` schema data:

**Schema structure:**
```json
{
  "data": [
    {
      "file_path": "/app/PaymentController.php",
      "raw_content": "<?php class PaymentController { ... }",
      "imports": [
        {"module": "Stripe\\StripeClient"}
      ],
      "functions": [
        {"name": "processPayment"}
      ],
      "classes": [
        {"name": "PaymentController"}
      ],
      "file_metadata": {
        "size_bytes": 1024,
        "last_modified": "2024-01-01T00:00:00Z"
      }
    }
  ],
  "analysis_metadata": {
    "total_files_analysed": 1,
    "analysis_timestamp": "2024-01-01T00:00:00Z"
  }
}
```

**Usage example:**
```python
from waivern_core import Message, Schema
from waivern_processing_purpose_analyser import (
    ProcessingPurposeAnalyser,
    ProcessingPurposeAnalyserConfig,
)

# Create message with source code data
message = Message(
    schema=Schema(name="source_code", version="1.0.0"),
    data={
        "data": [
            {
                "file_path": "/app/PaymentController.php",
                "raw_content": "<?php\nclass PaymentController {\n    public function processPayment() {}\n}",
                "imports": [{"module": "Stripe\\\\StripeClient"}],
                "functions": [{"name": "processPayment"}],
                "classes": [{"name": "PaymentController"}]
            }
        ],
        "analysis_metadata": {
            "total_files_analysed": 1,
            "analysis_timestamp": "2024-01-01T00:00:00Z"
        }
    }
)

# Process data
analyser = ProcessingPurposeAnalyser(
    config=ProcessingPurposeAnalyserConfig()
)
result = analyser.process_data(message)

# Result contains processing purpose findings
print(result.data["findings"])
```

### Pipeline Usage

In WCF pipelines, use SourceCodeAnalyser to produce source_code data:

```yaml
execution:
  - id: "read_files"
    connector: "filesystem"
    output_schema: "standard_input"
    save_output: true

  - id: "parse_code"
    analyser: "source_code_analyser"
    input_from: "read_files"
    output_schema: "source_code"
    save_output: true

  - id: "analyse_purposes"
    analyser: "processing_purpose_analyser"
    input_from: "parse_code"
    output_schema: "processing_purpose_finding"
```
```

**Section to update: Installation/Dependencies**

```markdown
## Dependencies

ProcessingPurposeAnalyser depends on:
- **waivern-core** - Base WCF abstractions
- **waivern-rulesets** - Shared pattern rulesets
- **waivern-analysers-shared** - Shared analyser utilities
- **waivern-llm** - LLM validation (optional providers)

**No dependency on other analysers.** Communication with SourceCodeAnalyser (or any other component) happens through JSON schema contracts only.
```

#### 2. Update Handler Docstrings

**File:** `source_code_schema_input_handler.py`

**Class docstring:**
```python
class SourceCodeSchemaInputHandler:
    """Handles processing purpose analysis for source code schema data.

    This handler processes source code schema data using dict-based access.
    It relies on Message object validation against the source_code JSON schema
    contract, eliminating the need for typed Pydantic models.

    The handler analyzes:
    - Raw source code content for pattern matching
    - Import statements for service integrations
    - Function/class names for purpose indicators

    All data is processed as dictionaries that have been validated by the
    Message object against the source_code v1.0.0 JSON schema.
    """
```

**Method docstring:**
```python
def analyse_source_code_data(self, data: dict[str, Any]) -> list[Finding]:
    """Analyse source code data for processing purposes.

    Args:
        data: Dict containing source code schema data that has been
              validated by Message against source_code JSON schema.
              Expected structure:
              {
                  "data": [
                      {
                          "file_path": str,
                          "raw_content": str,
                          "imports": list[dict] (optional),
                          "functions": list[dict] (optional),
                          "classes": list[dict] (optional)
                      }
                  ],
                  "analysis_metadata": dict
              }

    Returns:
        List of Finding objects representing detected processing purposes

    Notes:
        - Dict data has already been validated by Message object
        - No additional validation performed in this handler
        - Optional fields accessed with .get() to handle missing keys
        - Required fields accessed with [] to raise KeyError if missing
    """
```

#### 3. Update Reader Docstrings

**File:** `schema_readers/source_code_1_0_0.py`

**Class docstring:**
```python
class SourceCode_1_0_0_Reader(SchemaReader[dict[str, Any]]):
    """Schema reader for source_code schema version 1.0.0.

    Returns dict-based data that has been validated by Message object
    against the source_code JSON schema contract. No additional validation
    is performed - the reader trusts Message's schema validation.

    This approach eliminates dependency on waivern-source-code-analyser's
    typed Pydantic models and enables true schema-contract communication.
    """
```

#### 4. Update Analyser Docstrings

**File:** `analyser.py`

**Add note to class docstring:**
```python
class ProcessingPurposeAnalyser(Analyser):
    """Analyser for detecting data processing purposes.

    Supports two input schemas:
    - standard_input v1.0.0: Generic text content
    - source_code v1.0.0: Parsed source code structures

    Uses dict-based schema handling for all input data. This eliminates
    hardcoded dependencies on other analyser packages and relies on JSON
    schema contracts validated by Message objects.

    Pattern matching is performed using ProcessingPurposesRuleset for
    efficient detection of common processing purposes (payment, support,
    marketing, etc.). Optional LLM validation provides additional verification.
    """
```

**Add note to _process_source_code_data method:**
```python
def _process_source_code_data(self, message: Message) -> list[Finding]:
    """Process source code schema data.

    Args:
        message: Message containing source_code schema data (dict-based)

    Returns:
        List of findings from source code analysis

    Notes:
        - Message has validated data against source_code JSON schema
        - Reader returns dict (not typed model)
        - Handler processes dict using key access
        - No dependency on waivern-source-code-analyser package
    """
```

#### 5. Add Architectural Notes

**Create new section in README.md:**

```markdown
## Architecture

### Schema-Driven Design

ProcessingPurposeAnalyser follows WCF's schema-driven architecture:

1. **Schema Contracts**: Components communicate through JSON schema definitions
2. **Message Validation**: Message objects validate data against schemas
3. **Dict-Based Processing**: Handlers process validated dict data
4. **No Code Coupling**: No imports of other analysers' internal models

### Validation Responsibilities

**Message Object:**
- Validates data against JSON schema (wire format)
- Ensures data conforms to schema contract
- Catches schema violations early

**Schema Reader:**
- Wraps validated dict data
- No additional validation performed
- Trusts Message's schema validation

**Handler:**
- Processes dict data using key access
- Trusts schema contract enforced by Message
- Uses .get() for optional fields, [] for required fields

### Benefits

- ✅ **Independent evolution** - Components can change independently
- ✅ **True plugin architecture** - No hardcoded cross-component dependencies
- ✅ **Schema versioning** - Easy to support multiple schema versions
- ✅ **Performance** - No redundant Pydantic validation
- ✅ **Flexibility** - Dict-based access adapts to schema changes
```

### Testing Documentation

**Add section on testing with schemas:**

```markdown
## Testing

### Creating Test Fixtures

When testing with source_code schema:

```python
from waivern_core import Message, Schema

# Create dict-based test data
test_data = {
    "data": [
        {
            "file_path": "/test/TestController.php",
            "raw_content": "<?php class TestController {}",
            "imports": [],
            "functions": [],
            "classes": [{"name": "TestController"}]
        }
    ],
    "analysis_metadata": {
        "total_files_analysed": 1,
        "analysis_timestamp": "2024-01-01T00:00:00Z"
    }
}

# Create Message (validates against schema)
message = Message(
    schema=Schema(name="source_code", version="1.0.0"),
    data=test_data
)

# Process with analyser
result = analyser.process_data(message)
```

**Do not:**
- Import typed models from waivern-source-code-analyser
- Construct Pydantic models for test data
- Manually validate dict structure (Message does this)

**Do:**
- Use plain dicts for test data
- Let Message validate against schema
- Focus tests on analyser behavior, not schema validation
```

## Testing

### Testing Strategy

**Documentation validation:**
1. Review all documentation changes for accuracy
2. Verify examples work with current implementation
3. Check that architectural principles are clearly explained
4. Ensure no references to old typed model approach

### Documentation Sections to Verify

#### 1. README.md is accurate

**Check:**
- Schema handling explanation correct
- Dict-based approach clearly documented
- Examples work with current code
- Dependencies list accurate
- No references to SourceCodeAnalyser dependency

#### 2. Docstrings are complete

**Check:**
- Handler docstrings explain dict-based approach
- Reader docstrings explain Message validation reliance
- Analyser docstrings updated
- No references to typed models in docstrings

#### 3. Examples are functional

**Check:**
- Code examples can be run
- Dict structure matches schema
- Examples demonstrate proper usage
- Pipeline example is accurate

#### 4. Architecture is clearly explained

**Check:**
- Schema-driven design principles clear
- Validation responsibilities documented
- Benefits of approach explained
- No confusing or contradictory information

### Quality Checks

**Must pass before marking step complete:**
- [ ] README.md updated with dict-based schema handling
- [ ] Handler docstrings updated
- [ ] Reader docstrings updated
- [ ] Analyser docstrings updated
- [ ] Examples added and verified
- [ ] Architecture section added
- [ ] No references to typed models in docs
- [ ] No references to SourceCodeAnalyser dependency
- [ ] Documentation is clear and accurate

## Success Criteria

**Functional:**
- [x] README.md explains dict-based schema handling
- [x] Schema handling section added
- [x] Working with source_code schema section added
- [x] Pipeline usage example added
- [x] Architecture section added
- [x] Dependencies section updated

**Docstrings:**
- [x] Handler docstrings updated
- [x] Reader docstrings updated
- [x] Analyser docstrings updated
- [x] Method docstrings explain dict-based approach

**Quality:**
- [x] Documentation accurate
- [x] Examples functional
- [x] No outdated information
- [x] Clear and understandable

## Implementation Notes

### Documentation Principles

**Focus on:**
1. **How it works** - Explain dict-based schema handling
2. **Why this way** - Document architectural decisions
3. **How to use** - Provide clear examples
4. **What's different** - Explain change from typed models

**Avoid:**
1. Implementation details that may change
2. References to internal code structure
3. Assumptions about user's knowledge
4. Outdated examples or patterns

### Key Messages to Communicate

**To users:**
- Use dicts for schema data, not typed models
- Message validation handles schema compliance
- No need to import from SourceCodeAnalyser
- Communication via schema contracts only

**To developers:**
- Architecture follows schema-driven design
- Validation at Message level, not handler level
- Dict-based approach enables independence
- No hardcoded cross-component dependencies

### Refactoring Opportunities

**Future documentation enhancements:**
1. Add troubleshooting section for common issues
2. Add migration guide from old typed model approach (if needed)
3. Add advanced usage examples (custom schemas, etc.)
4. Consider adding diagrams for architecture explanation

## Next Steps

After this step is complete:
- **Phase 4 is complete!**
- All hardcoded dependencies removed
- True plugin architecture achieved
- ProcessingPurposeAnalyser is truly independent

**Final verification:**
- Run full test suite (882+ tests)
- Run `./scripts/dev-checks.sh`
- Verify integration tests pass
- Create PR for Phase 4
- Update parent task document with completion notes
