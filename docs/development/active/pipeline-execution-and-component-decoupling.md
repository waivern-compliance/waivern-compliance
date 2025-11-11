# Task: Pipeline Execution Model and Component Decoupling

**Status:** Phase 1 Complete (Steps 1-2), Phase 2 In Progress
**Priority:** High
**Created:** 2025-11-10
**Last Updated:** 2025-11-11

## Executive Summary

Implement CI/CD-style pipeline execution in WCF to enable multi-step analyser chaining with schema-based routing. This solves two critical architectural violations where components have hardcoded dependencies, enabling true plugin architecture with independent, composable components.

## Problem Statement

### Critical Architectural Violations

After the monorepo refactoring, two components violate the plugin architecture by hardcoding dependencies on other components:

1. **SourceCodeConnector → FilesystemConnector** (CRITICAL)
   - Location: `libs/waivern-source-code/src/waivern_source_code/connector.py:20,54-62`
   - Issue: Direct import and instantiation of FilesystemConnector
   - Impact: Cannot substitute file collection mechanism, breaks component independence

2. **ProcessingPurposeAnalyser → SourceCodeConnector** (CRITICAL)
   - Location: `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/analyser.py:18`
   - Issue: Imports SourceCodeConnector schema models directly
   - Impact: Forces mandatory dependency chain, breaks analyser independence

### Root Cause

SourceCodeConnector has dual responsibility:
- **File discovery/collection** (should be FilesystemConnector's job)
- **Code parsing/analysis** (transformation of standard_input → source_code schema)

This violates single responsibility principle and creates cascading dependencies:
```
ProcessingPurposeAnalyser
    ↓ (hardcoded import)
SourceCodeConnector
    ↓ (hardcoded import)
FilesystemConnector
```

## Solution Overview

Implement pipeline execution to enable schema-based component chaining, then refactor SourceCodeConnector to be a pure transformer analyser.

### Architectural Vision

**Before (Current):**
```yaml
execution:
  - name: "Analyse source code"
    connector: "source_code"  # Hardcodes FilesystemConnector internally
    analyser: "purpose_analyser"
```

**After (Pipeline):**
```yaml
execution:
  - id: "read_files"
    connector: "filesystem"
    output_schema: "standard_input"
    save_output: true

  - id: "parse_code"
    analyser: "source_code_parser"  # SourceCode as transformer!
    input_from: "read_files"
    output_schema: "source_code"
    save_output: true

  - id: "analyse_purposes"
    analyser: "purpose_analyser"
    input_from: "parse_code"
    output_schema: "processing_purpose_finding"
```

### Key Benefits

✅ **Eliminates hardcoded dependencies** - Components become truly independent
✅ **Enables reusability** - SourceCodeAnalyser can accept input from any connector
✅ **Future-proof** - Foundation for parallel execution and complex DAGs
✅ **Schema-driven** - Executor validates compatibility automatically
✅ **Clean architecture** - Breaking change accepted for better long-term design (WCF is pre-1.0)

## Implementation Plan

### Phase 1: Extend Runbook Format (Pipeline-Only Design) ✅ COMPLETED

**Status:** ✅ Completed 2025-11-11
**Decision:** Breaking change - dropped backward compatibility for cleaner design (WCF is pre-1.0)

**File:** `apps/wct/src/wct/runbook.py`

#### Changes to `ExecutionStep` Model

Implemented pipeline-only model with required fields:

```python
class ExecutionStep(BaseModel):
    """Pipeline execution step with explicit data flow.

    Each step is either:
    - Connector-based: Reads from external source (connector + optional analyser)
    - Input-based: Transforms previous step output (input_from + analyser)

    Steps are mutually exclusive: connector XOR input_from.
    """

    # Step identification (REQUIRED)
    id: str = Field(
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Unique identifier for this step (required for pipeline chaining)",
    )

    name: str = Field(min_length=1, description="Human-readable name for this execution step")
    description: str = Field(description="Description of what this execution step does")
    contact: str | None = Field(default=None, description="Optional contact information")

    # Data source (connector OR input_from, mutually exclusive)
    connector: str | None = Field(
        default=None,
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Name of connector instance (for connector-based steps)",
    )
    input_from: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Step ID to read input from (for input-based steps)",
    )

    # Processing (analyser optional for connector-only steps)
    analyser: str | None = Field(
        default=None,
        min_length=1,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Name of analyser instance to use (optional for connector-only steps)",
    )

    # Schema definitions
    input_schema: str = Field(
        min_length=1,
        description="Schema name for connector output or previous step output validation"
    )
    output_schema: str = Field(
        min_length=1, description="Schema name for analyser output validation"
    )
    input_schema_version: str | None = Field(
        default=None,
        description="Optional specific version for input schema",
    )
    output_schema_version: str | None = Field(
        default=None,
        description="Optional specific version for output schema",
    )

    # Pipeline control
    save_output: bool = Field(
        default=False,
        description="Whether to save output for use by subsequent steps",
    )

    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional execution metadata and runtime configuration",
    )

    @model_validator(mode="after")
    def validate_connector_xor_input_from(self) -> "ExecutionStep":
        """Validate that connector and input_from are mutually exclusive."""
        if self.connector is not None and self.input_from is not None:
            msg = "Step cannot have both 'connector' and 'input_from' - choose one data source"
            raise ValueError(msg)

        if self.connector is None and self.input_from is None:
            msg = "Step must have either 'connector' or 'input_from' as data source"
            raise ValueError(msg)

        return self
```

**Breaking Changes:**
- Required `id` field for all execution steps
- Connector and input_from are mutually exclusive (XOR validation)
- Analyser field is now optional (connector-only steps supported)
- All sample runbooks updated with step IDs

#### Validation Updates ✅ COMPLETED

**Status:** ✅ Completed 2025-11-11 (Step 2)

Implemented cross-reference validation integrated into existing `validate_cross_references`:

```python
class Runbook(BaseModel):
    # ... existing fields ...

    @model_validator(mode="after")
    def validate_cross_references(self) -> Runbook:
        """Validate cross-references between execution steps and components.

        Validates:
        - Connector references point to defined connectors (if present)
        - Analyser references point to defined analysers (if present)
        - Pipeline step references (input_from) point to valid step IDs
        """
        connector_names = {conn.name for conn in self.connectors}
        analyser_names = {analyser.name for analyser in self.analysers}
        step_ids = {step.id for step in self.execution}

        for i, step in enumerate(self.execution):
            # Validate connector reference (if present)
            if step.connector is not None and step.connector not in connector_names:
                raise ValueError(
                    f"Execution step {i + 1} references unknown connector '{step.connector}'. "
                    f"Available connectors: {sorted(connector_names)}"
                )

            # Validate analyser reference (if present)
            if step.analyser is not None and step.analyser not in analyser_names:
                raise ValueError(
                    f"Execution step {i + 1} references unknown analyser '{step.analyser}'. "
                    f"Available analysers: {sorted(analyser_names)}"
                )

            # Validate pipeline reference (input_from)
            if step.input_from is not None and step.input_from not in step_ids:
                raise ValueError(
                    f"Step '{step.name}' references unknown step ID '{step.input_from}'. "
                    f"Available step IDs: {sorted(step_ids)}"
                )

        return self
```

**Files Modified:**
- `apps/wct/src/wct/runbook.py` (ExecutionStep model + Runbook validation)
- `apps/wct/tests/test_runbook.py` (9 new pipeline validation tests)
- `apps/wct/runbooks/samples/*.yaml` (3 sample runbooks updated with step IDs)
- `apps/wct/tests/*.py` (29 test execution steps updated with IDs)
- Documentation (Steps 1-2 marked complete)

**Tests:** 890 passed, 7 skipped, 14 deselected

---

### Phase 2: Implement Sequential Pipeline Execution

**File:** `apps/wct/src/wct/executor.py`

#### New Artifact Management

Add artifact storage for passing data between steps:

```python
class Executor:
    # ... existing fields ...

    def execute_runbook(self, runbook_path: Path) -> list[AnalysisResult]:
        """Execute runbook with pipeline support."""
        try:
            runbook = RunbookLoader.load(runbook_path)
        except Exception as e:
            raise ExecutorError(f"Failed to load runbook {runbook_path}: {e}") from e

        # NEW: Build execution graph and validate dependencies
        execution_order = self._build_execution_order(runbook.execution)

        # NEW: Artifact storage for passing data between steps
        artifacts: dict[str, Message] = {}

        results: list[AnalysisResult] = []
        for step in execution_order:
            result = self._execute_step(step, runbook, artifacts)
            results.append(result)

            # Save output if requested
            if step.save_output and step.id:
                # Result contains the Message data
                artifacts[step.id] = result.message  # Need to add message to AnalysisResult

        return results
```

#### Execution Order Resolution

Implement topological sort for dependency ordering:

```python
def _build_execution_order(self, steps: list[ExecutionStep]) -> list[ExecutionStep]:
    """Build execution order respecting dependencies.

    For Phase 1 (sequential only), this simply validates there are no cycles
    and returns steps in declaration order.

    Args:
        steps: Execution steps from runbook

    Returns:
        Steps in valid execution order

    Raises:
        ExecutorError: If circular dependencies detected
    """
    # Build dependency graph
    dependencies: dict[str, set[str]] = {}
    for step in steps:
        step_id = step.id or step.name
        dependencies[step_id] = set()
        if step.input_from:
            dependencies[step_id].add(step.input_from)

    # Validate no cycles (simple check for Phase 1)
    visited = set()
    for step_id in dependencies:
        if self._has_cycle(step_id, dependencies, visited, set()):
            raise ExecutorError(
                f"Circular dependency detected in execution steps involving '{step_id}'"
            )

    # For sequential execution, return in declaration order
    # (Proper topological sort can be added in Phase 2 for parallel execution)
    return steps

def _has_cycle(
    self,
    step_id: str,
    dependencies: dict[str, set[str]],
    visited: set[str],
    rec_stack: set[str]
) -> bool:
    """Check for cycles in dependency graph using DFS."""
    visited.add(step_id)
    rec_stack.add(step_id)

    for dep in dependencies.get(step_id, set()):
        if dep not in visited:
            if self._has_cycle(dep, dependencies, visited, rec_stack):
                return True
        elif dep in rec_stack:
            return True

    rec_stack.remove(step_id)
    return False
```

#### Updated Step Execution

Modify `_execute_step` to handle both modes:

```python
def _execute_step(
    self,
    step: ExecutionStep,
    runbook: Runbook,
    artifacts: dict[str, Message]
) -> AnalysisResult:
    """Execute a single step in either single-step or pipeline mode."""
    logger.info("Executing step: %s", step.name)

    try:
        analyser_config, connector_config = self._get_step_configs(step, runbook)
        analyser_type = self._validate_analyser_type(step, analyser_config)

        # Instantiate analyser
        analyser = self._instantiate_analyser(analyser_type, analyser_config)

        # Get input message (from connector OR previous step)
        if step.connector:
            # Single-step mode: extract from connector
            connector_type = self._validate_connector_type(step, connector_config)
            connector = self._instantiate_connector(connector_type, connector_config)
            input_schema, output_schema = self._resolve_step_schemas(
                step, connector, analyser
            )
            input_message = connector.extract(input_schema)
        else:
            # Pipeline mode: read from previous step
            if step.input_from not in artifacts:
                raise ExecutorError(
                    f"Step '{step.name}' depends on '{step.input_from}' "
                    f"but no artifact found"
                )
            input_message = artifacts[step.input_from]

            # Resolve schemas (no connector, just analyser)
            input_schema, output_schema = self._resolve_pipeline_schemas(
                step, input_message, analyser
            )

        # Execute analyser
        result_message = analyser.process(input_schema, output_schema, input_message)

        return AnalysisResult(
            analysis_name=step.name,
            analysis_description=step.description,
            input_schema=input_schema.name,
            output_schema=output_schema.name,
            data=result_message.content,
            metadata=analyser_config.metadata,
            contact=step.contact,
            success=True,
            message=result_message,  # NEW: Store for artifacts
        )

    except (ConnectorError, AnalyserError, ExecutorError, Exception) as e:
        return self._handle_step_error(step, e)
```

#### Schema Resolution for Pipeline

Add schema resolution for analyser-only steps:

```python
def _resolve_pipeline_schemas(
    self,
    step: ExecutionStep,
    input_message: Message,
    analyser: Analyser
) -> tuple[Schema, Schema]:
    """Resolve schemas for pipeline step (analyser-only).

    Args:
        step: Execution step
        input_message: Message from previous step
        analyser: Analyser instance

    Returns:
        Tuple of (input_schema, output_schema)

    Raises:
        ExecutorError: If schemas incompatible
    """
    # Input schema comes from previous step's message
    input_schema = input_message.schema

    # Validate analyser supports this input schema
    analyser_inputs = analyser.get_supported_input_schemas()
    if not any(s.name == input_schema.name and s.version == input_schema.version
               for s in analyser_inputs):
        raise ExecutorError(
            f"Analyser '{step.analyser}' does not support input schema "
            f"'{input_schema.name}' v{input_schema.version}. "
            f"Supported: {[f'{s.name} v{s.version}' for s in analyser_inputs]}"
        )

    # Resolve output schema
    analyser_outputs = analyser.get_supported_output_schemas()
    output_schema = self._find_compatible_schema(
        schema_name=step.output_schema,
        requested_version=step.output_schema_version,
        producer_schemas=analyser_outputs,
        consumer_schemas=[],
    )

    return input_schema, output_schema
```

**Files Modified:** 2 (`apps/wct/src/wct/executor.py`, `apps/wct/src/wct/analysis.py`)

---

### Phase 3: Refactor SourceCodeConnector → SourceCodeAnalyser

**Location:** `libs/waivern-source-code/`

#### Step 3.1: Create SourceCodeAnalyser Class

**File:** `libs/waivern-source-code/src/waivern_source_code/analyser.py` (NEW)

```python
"""Source code analyser for transforming file content to structured code data."""

import importlib
import logging
from pathlib import Path
from types import ModuleType
from typing import Any, override

from waivern_core.base_analyser import Analyser
from waivern_core.errors import AnalyserError
from waivern_core.message import Message
from waivern_core.schemas.base import Schema

from waivern_source_code.config import SourceCodeAnalyserConfig
from waivern_source_code.extractors import ClassExtractor, FunctionExtractor
from waivern_source_code.parser import SourceCodeParser

logger = logging.getLogger(__name__)

_SUPPORTED_INPUT_SCHEMAS: list[Schema] = [Schema("standard_input", "1.0.0")]
_SUPPORTED_OUTPUT_SCHEMAS: list[Schema] = [Schema("source_code", "1.0.0")]


class SourceCodeAnalyser(Analyser):
    """Analyser that parses source code files into structured data.

    Accepts standard_input schema (file content) and transforms to source_code schema
    containing parsed functions, classes, and metadata.
    """

    def __init__(self, config: SourceCodeAnalyserConfig) -> None:
        """Initialise the source code analyser.

        Args:
            config: Validated configuration
        """
        self._config = config
        self.parser = SourceCodeParser(config.language) if config.language else None

    @classmethod
    @override
    def get_name(cls) -> str:
        """Return the name of the analyser."""
        return "source_code_analyser"

    @classmethod
    @override
    def get_supported_input_schemas(cls) -> list[Schema]:
        """Return the input schemas supported by this analyser."""
        return _SUPPORTED_INPUT_SCHEMAS

    @classmethod
    @override
    def get_supported_output_schemas(cls) -> list[Schema]:
        """Return the output schemas supported by this analyser."""
        return _SUPPORTED_OUTPUT_SCHEMAS

    def _load_producer(self, schema: Schema) -> ModuleType:
        """Dynamically import producer module."""
        module_name = f"{schema.name}_{schema.version.replace('.', '_')}"
        return importlib.import_module(
            f"waivern_source_code.schema_producers.{module_name}"
        )

    @override
    def process_data(self, message: Message) -> Message:
        """Transform file content to structured source code data.

        Args:
            message: Input message with standard_input schema

        Returns:
            Output message with source_code schema

        Raises:
            AnalyserError: If processing fails
        """
        try:
            # Extract file data from standard_input
            input_data = message.content
            files = input_data.get("files", [])

            # Process each file
            files_data = []
            total_files = 0
            total_lines = 0

            for file_info in files:
                file_path = Path(file_info["file_path"])
                content = file_info["content"]

                # Apply file filtering
                if not self._should_process_file(file_path):
                    continue

                # Parse file
                file_data, line_count = self._parse_file(file_path, content)
                if file_data:
                    files_data.append(file_data)
                    total_files += 1
                    total_lines += line_count

            # Transform to output schema
            output_schema = _SUPPORTED_OUTPUT_SCHEMAS[0]
            producer = self._load_producer(output_schema)

            analysis_data = producer.produce(
                schema_version=output_schema.version,
                source_config={
                    "path_name": "input_files",
                    "path_str": "standard_input",
                    "language": self._config.language or "auto-detected",
                },
                analysis_summary={
                    "total_files": total_files,
                    "total_lines": total_lines,
                },
                files_data=files_data,
            )

            return Message(
                id=f"Source code analysis",
                content=analysis_data,
                schema=output_schema,
            )

        except Exception as e:
            logger.error(f"Failed to process source code: {e}")
            raise AnalyserError(f"Source code parsing failed: {e}") from e

    def _should_process_file(self, file_path: Path) -> bool:
        """Determine if file should be processed."""
        parser = self.parser or SourceCodeParser()

        # Check language support
        if not parser.is_supported_file(file_path):
            return False

        # Apply file patterns
        if self._config.file_patterns != ["**/*"]:
            return any(
                file_path.match(pattern) or file_path.name.endswith(pattern.replace("*", ""))
                for pattern in self._config.file_patterns
            )

        return True

    def _parse_file(self, file_path: Path, content: str) -> tuple[dict[str, Any] | None, int]:
        """Parse a single source code file."""
        try:
            # Check size limit
            if len(content) > self._config.max_file_size:
                logger.warning(f"Skipping large file: {file_path}")
                return None, 0

            # Detect language if needed
            if not self.parser:
                language = SourceCodeParser().detect_language_from_file(file_path)
                self.parser = SourceCodeParser(language)

            # Parse content
            root_node = self.parser.parse_string(content)
            line_count = content.count("\n") + 1

            # Extract structured data
            language = self.parser.language
            function_extractor = FunctionExtractor(language)
            class_extractor = ClassExtractor(language)

            file_data = {
                "file_path": str(file_path),
                "language": language,
                "raw_content": content,
                "functions": function_extractor.extract(root_node, content),
                "classes": class_extractor.extract(root_node, content),
                "imports": [],
                "metadata": {
                    "file_size": len(content),
                    "line_count": line_count,
                },
            }

            return file_data, line_count

        except Exception as e:
            logger.error(f"Failed to parse file {file_path}: {e}")
            return None, 0
```

#### Step 3.2: Update Configuration

**File:** `libs/waivern-source-code/src/waivern_source_code/config.py`

Remove path-related fields (now handled by FilesystemConnector):

```python
class SourceCodeAnalyserConfig(BaseComponentConfiguration):
    """Configuration for SourceCodeAnalyser."""

    language: str | None = Field(
        default=None,
        description="Programming language (auto-detected if None)",
    )
    file_patterns: list[str] = Field(
        default_factory=lambda: ["**/*"],
        description="Glob patterns for file inclusion",
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Skip files larger than this size in bytes",
        gt=0,
    )
    # REMOVED: path, max_files, exclude_patterns (handled by FilesystemConnector)
```

#### Step 3.3: Create Factory

**File:** `libs/waivern-source-code/src/waivern_source_code/analyser_factory.py` (NEW)

```python
"""Factory for creating SourceCodeAnalyser instances."""

from typing import override

from waivern_core import ComponentConfig, ComponentFactory, Schema
from waivern_core.services.container import ServiceContainer

from .analyser import SourceCodeAnalyser
from .config import SourceCodeAnalyserConfig


class SourceCodeAnalyserFactory(ComponentFactory[SourceCodeAnalyser]):
    """Factory for creating SourceCodeAnalyser instances."""

    def __init__(self, container: ServiceContainer) -> None:
        """Initialise factory with dependency injection container."""
        self._container = container

    @override
    def create(self, config: ComponentConfig) -> SourceCodeAnalyser:
        """Create a SourceCodeAnalyser instance from configuration."""
        analyser_config = SourceCodeAnalyserConfig.from_properties(config)
        return SourceCodeAnalyser(analyser_config)

    @override
    def can_create(self, config: ComponentConfig) -> bool:
        """Check if this factory can create an analyser with the given config."""
        try:
            SourceCodeAnalyserConfig.from_properties(config)
            return True
        except Exception:
            return False

    @override
    def get_component_name(self) -> str:
        """Get the component type name for analyser registration."""
        return "source_code_analyser"

    @override
    def get_input_schemas(self) -> list[Schema]:
        """Get the input schemas this analyser accepts."""
        return [Schema("standard_input", "1.0.0")]

    @override
    def get_output_schemas(self) -> list[Schema]:
        """Get the output schemas this analyser produces."""
        return [Schema("source_code", "1.0.0")]

    @override
    def get_service_dependencies(self) -> dict[str, type]:
        """Get the service dependencies required by this factory."""
        return {}  # No service dependencies
```

#### Step 3.4: Update Entry Points

**File:** `libs/waivern-source-code/pyproject.toml`

```toml
[project.entry-points."waivern.analysers"]
source_code_analyser = "waivern_source_code.analyser_factory:SourceCodeAnalyserFactory"

# NOTE: Old source_code_connector removed - breaking change accepted for Phase 3
```

#### Step 3.5: Remove FilesystemConnector Dependency

**File:** `libs/waivern-source-code/pyproject.toml`

```toml
dependencies = [
    "waivern-core",
    "tree-sitter>=0.23.2",
    "tree-sitter-php>=0.23.10",
    # REMOVED: "waivern-filesystem"
]
```

**Files Modified:** 7 files, Created: 2 new files
**Packages Modified:** `waivern-source-code`

---

### Phase 4: Fix ProcessingPurposeAnalyser Schema Coupling

**Location:** `libs/waivern-processing-purpose-analyser/`

#### Problem

ProcessingPurposeAnalyser currently imports schema models from `waivern-source-code`:

```python
from waivern_source_code.schemas import SourceCodeDataModel
```

This creates hardcoded dependency. Instead, it should work generically with the `source_code` schema through the Message object.

#### Solution

Refactor to use dictionary-based schema handling instead of typed models.

**File:** `libs/waivern-processing-purpose-analyser/src/waivern_processing_purpose_analyser/source_code_schema_input_handler.py`

**Before:**
```python
from waivern_source_code.schemas import (
    SourceCodeDataModel,
    SourceCodeFileDataModel,
)

def extract_from_source_code(data: SourceCodeDataModel) -> list[dict[str, Any]]:
    """Extract from typed model."""
    files = data.files
    # ...
```

**After:**
```python
# NO imports from waivern-source-code

def extract_from_source_code(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract from source_code schema (generic dictionary).

    Args:
        data: Validated source_code schema data (as dict)

    Returns:
        List of evidence items
    """
    # Work with dictionary directly (already validated by Message)
    files = data.get("files", [])

    evidence_items = []
    for file_data in files:
        file_path = file_data.get("file_path", "unknown")
        raw_content = file_data.get("raw_content", "")
        functions = file_data.get("functions", [])
        classes = file_data.get("classes", [])

        # Extract evidence from functions
        for func in functions:
            evidence_items.append({
                "text": func.get("body", ""),
                "location": f"{file_path}:{func.get('name', 'unknown')}",
                "metadata": {
                    "file_path": file_path,
                    "function_name": func.get("name"),
                    "line_number": func.get("start_line"),
                },
            })

        # Extract evidence from classes
        for cls in classes:
            for method in cls.get("methods", []):
                evidence_items.append({
                    "text": method.get("body", ""),
                    "location": f"{file_path}:{cls.get('name')}.{method.get('name')}",
                    "metadata": {
                        "file_path": file_path,
                        "class_name": cls.get("name"),
                        "method_name": method.get("name"),
                        "line_number": method.get("start_line"),
                    },
                })

    return evidence_items
```

#### Remove Dependency

**File:** `libs/waivern-processing-purpose-analyser/pyproject.toml`

```toml
dependencies = [
    "waivern-core",
    "waivern-analysers-shared",
    "waivern-rulesets",
    # REMOVED: "waivern-source-code"
]
```

**Files Modified:** 4 files
**Packages Modified:** `waivern-processing-purpose-analyser`

---

### Phase 5: Update Tests

#### Test Categories

1. **Runbook validation tests** - Test new pipeline format validation (✅ Phase 1 complete - 9 tests added)
2. **Executor tests** - Test artifact passing and schema resolution (Phase 2 pending)
3. **SourceCodeAnalyser tests** - Test transformation from standard_input (Phase 3 pending)
4. **Integration tests** - Test full pipeline execution (Phase 2+ pending)
5. **Migration validation tests** - Ensure updated runbooks work with new format (✅ Phase 1 complete)

#### Key Test Files

**File:** `apps/wct/tests/unit/test_runbook_validation.py` (NEW)

```python
"""Test runbook validation for pipeline execution."""

import pytest
from wct.runbook import ExecutionStep, RunbookValidationError


def test_pipeline_step_requires_id_when_save_output():
    """Step must have id when save_output is true."""
    with pytest.raises(RunbookValidationError):
        ExecutionStep(
            name="Parse code",
            description="",
            analyser="source_code",
            input_from="read_files",
            input_schema="standard_input",
            output_schema="source_code",
            save_output=True,  # Requires id
            # Missing: id field
        )


def test_pipeline_step_cannot_have_both_connector_and_input_from():
    """Step cannot specify both connector and input_from."""
    with pytest.raises(RunbookValidationError):
        ExecutionStep(
            name="Invalid step",
            description="",
            connector="filesystem",
            input_from="previous_step",  # Conflict!
            analyser="personal_data",
            input_schema="standard_input",
            output_schema="personal_data_finding",
        )


def test_pipeline_step_must_have_connector_or_input_from():
    """Step must have either connector or input_from."""
    with pytest.raises(RunbookValidationError):
        ExecutionStep(
            name="Invalid step",
            description="",
            # Missing both connector and input_from
            analyser="personal_data",
            input_schema="standard_input",
            output_schema="personal_data_finding",
        )


def test_pipeline_validates_step_references():
    """Runbook must validate input_from references exist."""
    # Test that referencing non-existent step ID raises error
    # (Implementation in Runbook.validate_pipeline_references)
```

**File:** `apps/wct/tests/integration/test_pipeline_execution.py` (NEW)

```python
"""Integration tests for pipeline execution."""

import pytest
from pathlib import Path

from wct.executor import Executor
from wct.runbook import RunbookLoader


@pytest.fixture
def pipeline_runbook(tmp_path):
    """Create a test runbook with pipeline execution."""
    runbook_content = """
name: "Pipeline Test"
description: "Test multi-step pipeline execution"

connectors:
  - name: "file_reader"
    type: "filesystem_connector"
    properties:
      path: "./test_data"

analysers:
  - name: "code_parser"
    type: "source_code_analyser"
    properties:
      language: "python"

  - name: "purpose_detector"
    type: "processing_purpose_analyser"
    properties:
      pattern_matching:
        ruleset: "processing_purposes"

execution:
  - id: "read_files"
    name: "Read source files"
    description: ""
    connector: "file_reader"
    analyser: "passthrough"  # Hypothetical passthrough analyser
    input_schema: "standard_input"
    output_schema: "standard_input"
    save_output: true

  - id: "parse_code"
    name: "Parse source code"
    description: ""
    input_from: "read_files"
    analyser: "code_parser"
    input_schema: "standard_input"
    output_schema: "source_code"
    save_output: true

  - id: "analyse_purposes"
    name: "Detect processing purposes"
    description: ""
    input_from: "parse_code"
    analyser: "purpose_detector"
    input_schema: "source_code"
    output_schema: "processing_purpose_finding"
"""
    runbook_path = tmp_path / "pipeline_test.yaml"
    runbook_path.write_text(runbook_content)
    return runbook_path


def test_pipeline_execution_with_artifacts(pipeline_runbook):
    """Test that artifacts pass between steps correctly."""
    executor = Executor.create_with_built_ins()
    results = executor.execute_runbook(pipeline_runbook)

    assert len(results) == 3
    assert results[0].success
    assert results[1].success
    assert results[2].success

    # Verify schemas match
    assert results[0].output_schema == "standard_input"
    assert results[1].output_schema == "source_code"
    assert results[2].output_schema == "processing_purpose_finding"
```

**File:** `libs/waivern-source-code/tests/test_source_code_analyser.py` (NEW)

```python
"""Tests for SourceCodeAnalyser."""

import pytest
from waivern_core.message import Message
from waivern_core.schemas.base import Schema

from waivern_source_code.analyser import SourceCodeAnalyser
from waivern_source_code.config import SourceCodeAnalyserConfig


def test_source_code_analyser_accepts_standard_input():
    """Test that analyser accepts standard_input schema."""
    config = SourceCodeAnalyserConfig.from_properties({
        "language": "python",
    })
    analyser = SourceCodeAnalyser(config)

    # Create input message with standard_input schema
    input_data = {
        "files": [
            {
                "file_path": "test.py",
                "content": "def hello():\n    print('world')\n",
            }
        ]
    }

    input_message = Message(
        id="test_input",
        content=input_data,
        schema=Schema("standard_input", "1.0.0"),
    )

    # Process
    output_message = analyser.process_data(input_message)

    # Verify output
    assert output_message.schema.name == "source_code"
    assert "files" in output_message.content
    assert len(output_message.content["files"]) == 1

    file_data = output_message.content["files"][0]
    assert file_data["file_path"] == "test.py"
    assert "functions" in file_data
    assert len(file_data["functions"]) == 1
    assert file_data["functions"][0]["name"] == "hello"
```

**Files Created:** 5-7 new test files
**Files Modified:** 10-15 existing test files

---

### Phase 6: Update Documentation and Examples

#### Runbook Examples

Create new example runbooks demonstrating pipeline execution:

**File:** `apps/wct/runbooks/samples/source_code_pipeline.yaml` (NEW)

```yaml
name: "Source Code Analysis Pipeline"
description: >
  Demonstrates multi-step pipeline for source code analysis.
  Shows: FilesystemConnector → SourceCodeAnalyser → ProcessingPurposeAnalyser

connectors:
  - name: "file_reader"
    type: "filesystem_connector"
    properties:
      path: "./src"
      exclude_patterns: ["*.pyc", "__pycache__", "*.log"]
      max_files: 1000

analysers:
  - name: "code_parser"
    type: "source_code_analyser"
    properties:
      language: "php"
      file_patterns: ["**/*.php"]
      max_file_size: 10485760  # 10MB

  - name: "purpose_detector"
    type: "processing_purpose_analyser"
    properties:
      pattern_matching:
        ruleset: "processing_purposes"
        evidence_context_size: "medium"
      llm_validation:
        enable_llm_validation: false

execution:
  - id: "read_files"
    name: "Read PHP source files"
    description: "Collect all PHP files from source directory"
    connector: "file_reader"
    # Note: Need a passthrough analyser or extend executor to support connector-only steps
    analyser: "passthrough"
    input_schema: "standard_input"
    output_schema: "standard_input"
    save_output: true

  - id: "parse_code"
    name: "Parse PHP code structure"
    description: "Extract functions, classes, and code structure"
    input_from: "read_files"
    analyser: "code_parser"
    input_schema: "standard_input"
    output_schema: "source_code"
    save_output: true

  - id: "detect_purposes"
    name: "Detect processing purposes"
    description: "Identify GDPR/CCPA processing purposes from code"
    input_from: "parse_code"
    analyser: "purpose_detector"
    input_schema: "source_code"
    output_schema: "processing_purpose_finding"
```

#### Update Migration Guide

**File:** `docs/migration/pipeline-execution-migration.md` (NEW)

```markdown
# Migration Guide: Pipeline Execution

## Overview

WCF now supports multi-step pipeline execution, enabling analyser chaining
with schema-based routing. This guide explains how to migrate from single-step
runbooks to pipeline-based execution.

## What Changed

### SourceCodeConnector → SourceCodeAnalyser

The `source_code_connector` has been refactored to `source_code_analyser`:

**Before (Old):**
```yaml
connectors:
  - name: "php_code"
    type: "source_code_connector"  # OLD: Was a connector
    properties:
      path: "./src"                 # Path was here
      language: "php"

execution:
  - connector: "php_code"
    analyser: "purpose_analyser"
    input_schema: "source_code"    # Connector produced this
```

**After (New - Pipeline):**
```yaml
connectors:
  - name: "file_reader"
    type: "filesystem_connector"
    properties:
      path: "./src"                 # Path moved to filesystem

analysers:
  - name: "code_parser"
    type: "source_code_analyser"   # NEW: Now an analyser
    properties:
      language: "php"

  - name: "purpose_detector"
    type: "processing_purpose_analyser"

execution:
  - id: "read_files"
    connector: "file_reader"
    analyser: "passthrough"
    output_schema: "standard_input"
    save_output: true

  - id: "parse_code"
    input_from: "read_files"        # Chain from previous step
    analyser: "code_parser"
    output_schema: "source_code"
    save_output: true

  - id: "detect_purposes"
    input_from: "parse_code"        # Chain again
    analyser: "purpose_detector"
    output_schema: "processing_purpose_finding"
```

## Breaking Changes (Phase 1 Complete)

**Decision (2025-11-11):** Breaking change accepted for cleaner architecture (WCF is pre-1.0)

**What Changed:**
- All execution steps now require `id` field
- Old runbooks without `id` will fail validation
- Migration required: add `id` to all execution steps

**Migration Example:**
```yaml
# Old (no longer valid):
execution:
  - name: "Analyse data"
    connector: "filesystem"
    ...

# New (required):
execution:
  - id: "analyse_data"
    name: "Analyse data"
    connector: "filesystem"
    ...
```

**Affected:**
- All existing runbooks (updated in Phase 1)
- Sample runbooks (3 files updated)
- Test runbooks (29 execution steps updated)

## Pipeline Execution Use Cases

**When to use pipeline mode:**
- Chaining multiple analysers
- Transforming data between schemas (e.g., standard_input → source_code → findings)
- Reusing intermediate results
- Building complex analysis workflows

**Single-step mode still works:**
- All current runbooks use single-step pattern (one connector → one analyser)
- Each step is independent (no `input_from` references)
```

**Files Created:** 3 documentation files, 2 example runbooks
**Files Modified:** 2 existing docs (README.md, runbooks/README.md)

---

### Phase 7: Validation and Quality Checks

#### Final Checklist

**Phase 1 Complete (2025-11-11):**
- [x] All tests pass - 890 passed, 7 skipped
- [x] Type checking passes (strict mode)
- [x] Linting passes
- [x] Formatting correct
- [x] Dev checks pass
- [x] All runbooks updated with required `id` field
- [x] Documentation updated (Steps 1-2 marked complete)

**Pending (Phases 2-7):**
- [ ] Integration tests pass (require API keys)
- [ ] Pipeline execution implemented (artifact storage, schema resolution)
- [ ] SourceCode refactoring complete (analyser instead of connector)
- [ ] ProcessingPurpose dependency removed
- [ ] Example pipeline runbooks created
- [ ] No hardcoded dependencies remain

---

## Success Criteria

### Functional Requirements (Phase 1 Status)

- ✅ **Runbook format extended** - ExecutionStep model supports pipeline fields
- ✅ **Validation implemented** - XOR and cross-reference validation working
- ⏳ Pipeline execution supports multi-step analyser chaining (Phase 2 pending)
- ⏳ Schema-based routing validates compatibility automatically (Phase 2 pending)
- ⏳ Artifact passing works between steps (Phase 2 pending)
- ⏳ SourceCodeAnalyser accepts `standard_input` schema (Phase 3 pending)
- ⏳ ProcessingPurposeAnalyser has no hardcoded imports (Phase 4 pending)
- ✅ **Breaking changes accepted** - Clean architecture over backward compatibility

### Non-Functional Requirements (Phase 1 Status)

- ✅ All components are independently installable
- ✅ Code quality standards maintained (type checking, linting, 890 tests passing)
- ⏳ No hardcoded cross-component dependencies (Phase 3-4 pending)
- ⏳ Components depend only on waivern-core and shared utilities (Phase 3-4 pending)
- ⏳ True plugin architecture achieved (Phase 3-4 pending)

### Architecture Validation (Future)

- ⏳ FilesystemConnector is standalone (already achieved, no changes needed)
- ⏳ SourceCodeAnalyser depends only on waivern-core (Phase 3 pending)
- ⏳ ProcessingPurposeAnalyser depends only on waivern-core + shared utilities (Phase 4 pending)
- ✅ No circular dependencies (maintained)
- ⏳ Dependency graph is clean (Phase 3-4 will complete this)

---

## Risks and Mitigation

### Risk 1: Breaking Changes to Existing Users ✅ RESOLVED

**Decision:** Breaking change accepted (2025-11-11) - WCF is pre-1.0
**Impact:** Medium
**Status:** ✅ Completed in Phase 1
**Resolution:**
- All existing runbooks updated with required `id` field (3 samples, 29 test steps)
- Migration is straightforward (add `id` to each execution step)
- Clear migration guide provided in documentation
- Pre-1.0 status makes breaking changes acceptable

### Risk 2: Increased Complexity for Simple Use Cases

**Impact:** Low
**Likelihood:** Medium
**Mitigation:**
- Keep single-step format for simple cases
- Provide clear examples for both patterns
- Document when to use each approach

### Risk 3: Testing Coverage Gaps

**Impact:** High
**Likelihood:** Low
**Mitigation:**
- Comprehensive test plan (Phase 5)
- Integration tests for full pipelines
- Backward compatibility test suite
- Manual testing of example runbooks

### Risk 4: Performance Overhead from Artifact Storage

**Impact:** Low
**Likelihood:** Low
**Mitigation:**
- Artifacts stored only when `save_output: true`
- In-memory storage (no serialization overhead)
- Future optimization: streaming for large datasets

---

## Future Enhancements (Out of Scope)

The following are explicitly out of scope for this task but can be added later:

- **Parallel execution** - DAG-based parallel step execution
- **Conditional execution** - If/then branching in pipelines
- **Loop execution** - Iterate over datasets
- **Artifact persistence** - Save artifacts to disk for resumability
- **Artifact visualization** - UI for viewing pipeline flow
- **Advanced schema routing** - Automatic schema conversion
- **Connector-only steps** - Steps that just extract (no analyser)

These can be implemented incrementally without changing the core architecture.

---

## Implementation Notes

### Development Workflow

1. Create feature branch: `feature/pipeline-execution-model`
2. Implement phases sequentially (each phase should be committable)
3. Run `./scripts/dev-checks.sh` after each phase
4. Commit with conventional commit messages
5. Create PR when complete

### Testing Strategy

- **Unit tests first** - Test each component in isolation
- **Integration tests** - Test full pipeline execution
- **Migration validation** - Verify updated runbooks work
- **Manual testing** - Run example runbooks
- **Performance testing** - Benchmark artifact passing overhead

### Code Review Focus Areas

- Schema validation logic correctness
- Artifact lifecycle management
- Error handling in pipeline execution
- Breaking change migration completeness
- Documentation completeness

---

## References

- **WCF Core Concepts:** `docs/core-concepts/wcf-core-components.md`
- **Schema Architecture:** `docs/core-concepts/schema-architecture.md`
- **Current Executor:** `apps/wct/src/wct/executor.py`
- **Runbook Format:** `apps/wct/src/wct/runbook.py`
- **Dependency Analysis Report:** (See conversation context)

---

**Document Version:** 2.0 (Phase 1 Complete)
**Last Updated:** 2025-11-11
