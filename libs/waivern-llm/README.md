# waivern-llm

Multi-provider LLM abstraction for Waivern Compliance Framework.

## Features

- **Multi-provider support**: Anthropic, OpenAI, Google
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
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: OpenAI model name (optional)
- `GOOGLE_API_KEY`: Google API key
- `GOOGLE_MODEL`: Google model name (optional)
