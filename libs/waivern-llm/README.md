# waivern-llm

Multi-provider LLM abstraction for Waivern Compliance Framework.

## Features

- **Multi-provider support**: Anthropic, OpenAI, Google
- **Local LLM support**: LM Studio, Ollama, vLLM via OpenAI-compatible API
- **Unified interface**: Single API across all providers
- **Factory pattern**: Easy provider selection
- **Lazy imports**: Optional dependencies for non-default providers

## Installation

```bash
# Core with Anthropic (default)
uv add waivern-llm

# With OpenAI support
uv add "waivern-llm[openai]"

# With Google support
uv add "waivern-llm[google]"

# With all providers
uv add "waivern-llm[all]"
```

## Usage

```python
from waivern_llm import LLMServiceFactory

# Use factory to create service (auto-detects from LLM_PROVIDER env var)
llm = LLMServiceFactory.create_service()

# Or specify provider explicitly
from waivern_llm import AnthropicLLMService
llm = AnthropicLLMService(model_name="claude-sonnet-4-5-20250929")

# Invoke the LLM
result = llm.invoke(prompt="...")
```

## Environment Variables

- `LLM_PROVIDER`: Provider to use (`anthropic`, `openai`, `google`)
- `ANTHROPIC_API_KEY`: Anthropic API key
- `ANTHROPIC_MODEL`: Anthropic model name (optional)
- `OPENAI_API_KEY`: OpenAI API key (not required when `OPENAI_BASE_URL` is set)
- `OPENAI_MODEL`: OpenAI model name (optional)
- `OPENAI_BASE_URL`: Base URL for OpenAI-compatible APIs (for local LLMs)
- `GOOGLE_API_KEY`: Google API key
- `GOOGLE_MODEL`: Google model name (optional)

## Local LLM Support

Use local LLMs (LM Studio, Ollama, vLLM) via OpenAI-compatible API:

```bash
# Set provider to openai and configure base URL
export LLM_PROVIDER=openai
export OPENAI_BASE_URL=http://localhost:1234/v1  # LM Studio default
export OPENAI_MODEL=your-local-model-name
# OPENAI_API_KEY is not required when OPENAI_BASE_URL is set
```

```python
from waivern_llm import OpenAILLMService

# Using environment variables
llm = OpenAILLMService()

# Or explicitly
llm = OpenAILLMService(
    model_name="llama-3.2-3b",
    base_url="http://localhost:1234/v1",
)
```
