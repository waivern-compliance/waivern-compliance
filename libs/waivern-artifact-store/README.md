# waivern-artifact-store

Artifact storage service for the Waivern Compliance Framework.

## Overview

Provides abstract interface and concrete implementations for storing and retrieving pipeline artifacts during multi-step analysis workflows.

## Features

- **Abstract interface**: `ArtifactStore` async base class
- **In-memory storage**: `AsyncInMemoryStore` (default, for testing)
- **Filesystem storage**: `LocalFilesystemStore` (persistent, for local development)
- **Factory pattern**: Backend selection via configuration
- **Batch job tracking**: Storage for LLM batch job metadata

## Installation

```bash
uv add waivern-artifact-store
```

## Usage

### Basic Usage

```python
from waivern_artifact_store import ArtifactStoreFactory

# Create store (uses default "memory" backend)
factory = ArtifactStoreFactory()
store = factory.create()

# Save artifact (run-scoped, async)
await store.save_artifact(run_id, "extract", output_message)

# Retrieve artifact
message = await store.get_artifact(run_id, "extract")

# Check existence
if await store.artifact_exists(run_id, "extract"):
    # ...

# Cleanup artifacts (preserves system metadata)
await store.clear_artifacts(run_id)
```

### Configuration Options

The factory supports both explicit configuration and environment variable fallback:

```python
from waivern_artifact_store import (
    ArtifactStoreFactory,
    ArtifactStoreConfiguration
)

# Explicit configuration (highest priority)
config = ArtifactStoreConfiguration(backend="memory")
factory = ArtifactStoreFactory(config)
store = factory.create()

# Environment variable fallback
# Set ARTIFACT_STORE_BACKEND=memory in your environment
factory = ArtifactStoreFactory()  # Reads from environment
store = factory.create()

# Default configuration (if no config or env var)
factory = ArtifactStoreFactory()  # Defaults to "memory"
store = factory.create()
```

### Dependency Injection

Integration with ServiceContainer:

```python
from waivern_core.services import ServiceContainer
from waivern_artifact_store import (
    ArtifactStore,
    ArtifactStoreFactory,
    ArtifactStoreConfiguration
)

container = ServiceContainer()

# Zero-config (reads from environment)
container.register(
    ArtifactStore,
    ArtifactStoreFactory(),
    lifetime="singleton"
)

# Explicit configuration
config = ArtifactStoreConfiguration(backend="memory")
container.register(
    ArtifactStore,
    ArtifactStoreFactory(config),
    lifetime="singleton"
)

# Get singleton instance
store = container.get_service(ArtifactStore)
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run quality checks
./scripts/dev-checks.sh
```
