# Dependency Management Strategy

## Problem Statement

WCT currently includes all dependencies in the core package. As the project grows to support multiple LLM providers, database connectors, and other optional features, this approach shows limitations:

- ❌ Bloated installation (unnecessary dependencies)
- ❌ Slow installation times
- ❌ Unnecessary security surface area
- ❌ Difficult to maintain compatibility across many providers

## Options Considered

### Option A: All-Inclusive (Current Approach)
```toml
dependencies = [
    "langchain-anthropic>=0.2.0",
    "langchain-openai>=0.2.0",
    "langchain-google-genai>=2.0.0",
    "pymysql>=1.1.1",
    "psycopg2-binary>=2.9.0",
    "pymongo>=4.0.0",
    # ... everything
]
```

**Pros:**
- ✅ Simple for users (one command installs everything)
- ✅ No import errors

**Cons:**
- ❌ Bloated installation
- ❌ Slow installation
- ❌ Unnecessary security surface
- ❌ Conflicting dependencies across providers
- ❌ Doesn't scale as features grow

### Option B: Optional Dependency Groups
```toml
dependencies = [
    "langchain>=0.3.0",
    "langchain-anthropic>=0.2.0",  # Default only
]

[dependency-groups]
llm-openai = ["langchain-openai>=0.2.0"]
llm-google = ["langchain-google-genai>=2.0.0"]
llm-all = ["langchain-openai>=0.2.0", "langchain-google-genai>=2.0.0", ...]
```

Installation: `uv sync --group llm-openai`

**Pros:**
- ✅ Users install only what they need
- ✅ Faster installation
- ✅ Smaller security surface
- ✅ Clear separation of concerns
- ✅ Standard Python packaging approach

**Cons:**
- ❌ Users need to know which groups to install
- ❌ Import errors if dependencies missing (mitigated with lazy imports)

### Option C: Separate Plugin Packages
```
waivern-compliance-tool (core)
waivern-compliance-openai (separate package)
waivern-compliance-google (separate package)
```

**Pros:**
- ✅ Complete separation
- ✅ Independent versioning
- ✅ Clean plugin architecture

**Cons:**
- ❌ Overkill for current scale
- ❌ Much more maintenance overhead
- ❌ Complex publishing/release process
- ❌ Harder for users to discover features

### Option D: Hybrid - Optional Groups + Lazy Imports (RECOMMENDED)
Combines Option B with runtime checks and helpful error messages.

```toml
[project]
dependencies = [
    "langchain>=0.3.0",
    "langchain-anthropic>=0.2.0",  # Default provider
]

[dependency-groups]
# LLM providers
llm-openai = ["langchain-openai>=0.2.0"]
llm-google = ["langchain-google-genai>=2.0.0"]
llm-cohere = ["langchain-cohere>=0.3.0"]
llm-all = ["langchain-openai>=0.2.0", "langchain-google-genai>=2.0.0", "langchain-cohere>=0.3.0"]

# Database connectors
connector-postgres = ["psycopg2-binary>=2.9.0"]
connector-mongodb = ["pymongo>=4.0.0"]
connector-all = ["psycopg2-binary>=2.9.0", "pymongo>=4.0.0"]

# Convenience groups
all = [...]  # Everything
dev = [...]  # Development tools
```

```python
# Lazy import with helpful errors
class OpenAILLMService:
    def __init__(self):
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise LLMConfigurationError(
                "OpenAI provider is not installed.\n"
                "Install it with: uv sync --group llm-openai\n"
                "Or install all providers: uv sync --group llm-all"
            ) from e

        self._chat_openai = ChatOpenAI
```

**Pros:**
- ✅ Minimal default installation
- ✅ Clear user guidance via error messages
- ✅ Scales to many optional features
- ✅ Standard Python approach
- ✅ Easy to add new features without bloating core

**Cons:**
- ❌ Slightly more complex implementation (lazy imports)
- ❌ Users need to read error messages

## Recommended Solution: Option D

### Rationale

1. **Right size for current scale**: Not too simple (Option A), not too complex (Option C)
2. **Future-proof**: Easy to add new providers/connectors without core bloat
3. **User-friendly**: Helpful error messages guide installation
4. **Standard approach**: Uses established Python packaging patterns
5. **Performance**: Faster installation, smaller footprint
6. **Security**: Reduced attack surface (only install what you need)

### Implementation Strategy

#### 1. Dependency Group Structure
```toml
[dependency-groups]
# LLM providers (start with these)
llm-openai = ["langchain-openai>=0.2.0"]
llm-google = ["langchain-google-genai>=2.0.0"]
llm-cohere = ["langchain-cohere>=0.3.0"]
llm-all = ["langchain-openai>=0.2.0", "langchain-google-genai>=2.0.0", "langchain-cohere>=0.3.0"]

# Future: Database connectors
connector-postgres = ["psycopg2-binary>=2.9.0"]
connector-mongodb = ["pymongo>=4.0.0"]
connector-all = [...]

# Future: Source code analysers
analyser-javascript = ["tree-sitter-javascript>=0.21.0"]
analyser-python = ["tree-sitter-python>=0.21.0"]
analyser-all = [...]

# Convenience
all = [...]  # All optional features
```

#### 2. Lazy Import Pattern
```python
def _lazy_import_provider(provider: str):
    """Lazy import provider with helpful error message."""
    imports = {
        "openai": ("langchain_openai", "ChatOpenAI", "llm-openai"),
        "google": ("langchain_google_genai", "ChatGoogleGenerativeAI", "llm-google"),
        "cohere": ("langchain_cohere", "ChatCohere", "llm-cohere"),
    }

    if provider not in imports:
        raise ValueError(f"Unknown provider: {provider}")

    module_name, class_name, group_name = imports[provider]

    try:
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)
    except ImportError as e:
        raise LLMConfigurationError(
            f"{provider.title()} provider is not installed.\n"
            f"Install it with: uv sync --group {group_name}\n"
            f"Or install all providers: uv sync --group llm-all"
        ) from e
```

#### 3. User Experience
```bash
# Default installation (Anthropic only)
$ uv sync
# Works immediately with Anthropic

# Try to use OpenAI without installing
$ uv run wct run runbook.yaml
Error: OpenAI provider is not installed.
Install it with: uv sync --group llm-openai
Or install all providers: uv sync --group llm-all

# Install OpenAI support
$ uv sync --group llm-openai
# Now works with both Anthropic and OpenAI

# Install everything
$ uv sync --group all
# All features available
```

#### 4. Documentation Updates
- Update `CLAUDE.md` with dependency group documentation
- Add troubleshooting section for import errors
- Document recommended groups for different use cases
- Add examples for common scenarios

### Migration Path

1. **Phase 1**: Implement for LLM providers (current feature)
   - Move optional LLM providers to dependency groups
   - Keep `langchain-anthropic` in core (default)
   - Implement lazy imports with helpful errors

2. **Phase 2**: Apply to existing connectors
   - Move MySQL connector dependencies to optional group
   - Keep in core for now (backward compatibility)
   - Plan migration for next major version

3. **Phase 3**: Future connectors use pattern by default
   - All new connectors go in dependency groups
   - Core remains lean
   - Users install what they need

### Benefits for WCT

1. **Development velocity**: Add new features without worrying about core bloat
2. **User choice**: Advanced users install only what they need
3. **Easier testing**: Test optional features in isolation
4. **Better compatibility**: Fewer dependency conflicts
5. **Clearer architecture**: Optional vs. core features explicit

### Compatibility Considerations

- Existing installations continue working (Anthropic in core)
- No breaking changes to current users
- Optional features are opt-in
- Clear migration path for future versions

## Examples

### Use Case 1: Simple Deployment (Anthropic only)
```bash
uv sync
uv run wct run runbook.yaml
```

### Use Case 2: Multi-Provider Setup
```bash
uv sync --group llm-openai --group llm-google
uv run wct run runbook.yaml
```

### Use Case 3: Development Environment
```bash
uv sync --group all --group dev
```

### Use Case 4: CI/CD (Minimal)
```bash
# Only install what's needed for tests
uv sync --group llm-openai
uv run pytest tests/llm/test_openai.py
```

## Future Extensions

This pattern enables clean separation for:
- Database connectors (postgres, mongodb, redis, etc.)
- Cloud integrations (AWS, GCP, Azure)
- Source code parsers (tree-sitter for different languages)
- Export formats (PDF, Excel, DOCX)
- Specialized analysers

Each can be independently versioned and maintained without affecting core stability.
