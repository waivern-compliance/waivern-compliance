# waivern-llm

Multi-provider LLM abstraction for Waivern Compliance Framework.

## Features

- **Multi-provider support**: Anthropic, OpenAI, Google
- **Local LLM support**: LM Studio, Ollama, vLLM via OpenAI-compatible API
- **Intelligent batching**: Token-aware bin-packing or count-based splitting
- **Response caching**: Automatic caching via ArtifactStore
- **Dependency injection**: Factory pattern with lazy resolution

## Architecture

The LLM service handles batching and caching internally, allowing processors
to focus on domain logic. Key separation of concerns:

| Concern                 | Owner       | Rationale                             |
| ----------------------- | ----------- | ------------------------------------- |
| What to group by        | Processor   | Domain knowledge (source files, etc.) |
| What content to include | Processor   | Knows data relationships              |
| Batching mode selection | Processor   | Knows if context helps validation     |
| Prompt building         | Processor   | Domain-specific prompts               |
| Token estimation        | LLM Service | Model-specific, implementation detail |
| Batch size calculation  | LLM Service | Based on model context window         |
| Bin-packing algorithm   | LLM Service | Optimisation detail                   |
| Response caching        | LLM Service | Cross-cutting concern                 |

## Usage

### Basic Usage (with DI Container)

```python
from waivern_core.services import ServiceContainer, ServiceDescriptor
from waivern_artifact_store import ArtifactStore, ArtifactStoreFactory
from waivern_llm import LLMService, LLMServiceFactory

# Create container and register services
container = ServiceContainer()
container.register(
    ServiceDescriptor(ArtifactStore, ArtifactStoreFactory(), "singleton")
)
container.register(
    ServiceDescriptor(LLMService, LLMServiceFactory(container), "singleton")
)

# Resolve service (created lazily on first request)
llm_service = container.get_service(LLMService)
```

### Implementing a PromptBuilder

Processors provide prompts via the `PromptBuilder` protocol:

```python
from collections.abc import Sequence
from typing import override
from waivern_llm import PromptBuilder
from my_analyser.schemas import MyFindingModel

class MyPromptBuilder(PromptBuilder[MyFindingModel]):
    """Builds validation prompts for my findings."""

    @override
    def build_prompt(
        self,
        items: Sequence[MyFindingModel],
        content: str | None = None,
    ) -> str:
        """Build prompt for the given findings.

        Args:
            items: Findings to include in the prompt.
            content: Optional source content (for EXTENDED_CONTEXT mode).

        Returns:
            Complete prompt string.
        """
        findings_block = self._format_findings(items)

        if content:
            # EXTENDED_CONTEXT mode - include source file content
            return f"Validate these findings against the source:\n\n{content}\n\n{findings_block}"
        else:
            # COUNT_BASED mode - findings only
            return f"Validate these findings:\n\n{findings_block}"

    def _format_findings(self, items: Sequence[MyFindingModel]) -> str:
        return "\n".join(f"- [{f.id}] {f.category}: {f.evidence}" for f in items)
```

### Calling LLMService.complete()

```python
import asyncio
from waivern_llm import LLMService, ItemGroup, BatchingMode, LLMCompletionResult
from my_analyser.prompts import MyPromptBuilder
from my_analyser.schemas import MyFindingModel, LLMResponseModel

async def validate_findings(
    findings: list[MyFindingModel],
    llm_service: LLMService,
    run_id: str,
) -> LLMCompletionResult[MyFindingModel, LLMResponseModel]:
    # Group findings (processor decides grouping logic)
    groups = [ItemGroup(items=tuple(findings), content=None)]

    # Call LLM service
    return await llm_service.complete(
        groups,
        prompt_builder=MyPromptBuilder(),
        response_model=LLMResponseModel,
        batching_mode=BatchingMode.COUNT_BASED,
        run_id=run_id,
    )

# Sync wrapper if needed
result = asyncio.run(validate_findings(findings, llm_service, "run-123"))
```

### Batching Modes

Choose based on whether shared context helps validation:

- **COUNT_BASED**: Flatten all findings, split by count (default)
  - Use for evidence-only validation
  - Ignores `ItemGroup.content`

- **EXTENDED_CONTEXT**: Keep groups intact, bin-pack by tokens
  - Use when source file content helps validation
  - Requires `ItemGroup.content` to be set
  - Groups without content are skipped with `MISSING_CONTENT` reason

### Handling Skipped Findings

```python
from waivern_llm import SkipReason

result = await llm_service.complete(...)

# Check for skipped findings
for skipped in result.skipped:
    match skipped.reason:
        case SkipReason.OVERSIZED:
            # Group exceeded context window - implement fallback
            pass
        case SkipReason.MISSING_CONTENT:
            # Extended context requested but content was None
            pass
        case SkipReason.BATCH_ERROR:
            # LLM call failed for this batch
            pass
```

## Environment Variables

| Variable            | Description                                     | Required                                              |
| ------------------- | ----------------------------------------------- | ----------------------------------------------------- |
| `LLM_PROVIDER`      | Provider (`anthropic`, `openai`, `google`)      | Yes                                                   |
| `ANTHROPIC_API_KEY` | Anthropic API key                               | If using Anthropic                                    |
| `ANTHROPIC_MODEL`   | Model name (e.g., `claude-sonnet-4-5-20250929`) | No                                                    |
| `OPENAI_API_KEY`    | OpenAI API key                                  | If using OpenAI (not required with `OPENAI_BASE_URL`) |
| `OPENAI_MODEL`      | Model name                                      | No                                                    |
| `OPENAI_BASE_URL`   | Base URL for OpenAI-compatible APIs             | For local LLMs                                        |
| `GOOGLE_API_KEY`    | Google API key                                  | If using Google                                       |
| `GOOGLE_MODEL`      | Model name                                      | No                                                    |

## Local LLM Support

Use local LLMs (LM Studio, Ollama, vLLM) via OpenAI-compatible API:

```bash
export LLM_PROVIDER=openai
export OPENAI_BASE_URL=http://localhost:1234/v1  # LM Studio default
export OPENAI_MODEL=your-local-model-name
# OPENAI_API_KEY is not required when OPENAI_BASE_URL is set
```
