# waivern-llm

Multi-provider LLM abstraction for Waivern Compliance Framework.

## Features

- **Multi-provider support**: Anthropic, OpenAI, Google
- **Local LLM support**: LM Studio, Ollama, vLLM via OpenAI-compatible API
- **Intelligent batching**: Three semantic batching modes (COUNT_BASED, EXTENDED_CONTEXT, INDEPENDENT)
- **Response caching**: Automatic caching via ArtifactStore
- **Dependency injection**: Factory pattern with lazy resolution

## Architecture

The LLM dispatcher handles batching and caching internally, allowing processors
to focus on domain logic. Processors declare their LLM needs as typed
`LLMRequest` objects; the executor routes them to the `LLMDispatcher` which
handles token estimation, batch planning, caching, and provider calls.

| Concern                 | Owner      | Rationale                             |
| ----------------------- | ---------- | ------------------------------------- |
| What to group by        | Processor  | Domain knowledge (source files, etc.) |
| What content to include | Processor  | Knows data relationships              |
| Batching mode selection | Processor  | Knows if context helps validation     |
| Prompt building         | Processor  | Domain-specific prompts               |
| Token estimation        | Dispatcher | Model-specific, implementation detail |
| Batch size calculation  | Dispatcher | Based on model context window         |
| Batch planning          | Dispatcher | Splitting, validation, optimisation   |
| Response caching        | Dispatcher | Cross-cutting concern                 |

## Usage

### Building an LLMRequest

Processors declare LLM needs by building an `LLMRequest` inside `prepare()`:

```python
from waivern_llm import LLMRequest, ItemGroup, BatchingMode

request = LLMRequest(
    groups=[ItemGroup(items=findings, content=None)],
    prompt_builder=MyPromptBuilder(),
    response_model=MyResponseModel,
    batching_mode=BatchingMode.COUNT_BASED,
    run_id=run_id,
)
```

The executor dispatches the request and hands the `LLMDispatchResult` to `finalise()`.

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
        findings_block = "\n".join(
            f"- [{f.id}] {f.category}: {f.evidence}" for f in items
        )
        if content:
            return f"Validate against source:\n\n{content}\n\n{findings_block}"
        return f"Validate these findings:\n\n{findings_block}"
```

### Batching Modes

Three modes representing distinct semantic contracts:

- **COUNT_BASED**: N items in → N decisions out, no shared context.
  Flattens all items, splits by count. Ignores `ItemGroup.content`.

- **EXTENDED_CONTEXT**: N items in → N decisions out, with shared context.
  One group per batch; items share context (e.g., source file content).
  Groups without content are skipped with `MISSING_CONTENT` reason.

- **INDEPENDENT**: N items in → 1 decision out, atomic verdict.
  One group per batch; items collectively inform a single verdict.
  Groups without content are skipped with `MISSING_CONTENT` reason.

### Handling Skipped Findings

```python
from waivern_llm import SkipReason

for skipped in result.skipped:
    match skipped.reason:
        case SkipReason.OVERSIZED:
            pass  # Group exceeded context window
        case SkipReason.MISSING_CONTENT:
            pass  # Extended context requested but content was None
        case SkipReason.BATCH_ERROR:
            pass  # LLM call failed for this batch
```

## Batch Mode

When enabled, the dispatcher submits prompts to the provider's asynchronous
Batch API instead of making synchronous calls. This allows large analysis runs
to submit prompts in bulk, pause, and resume once results are ready.

### How It Works

1. **Submission** (`wct run`): Cache misses are submitted as a batch via `BatchLLMProvider.submit_batch()`. Cache entries are written as `"pending"` and a `BatchJob` is saved. The dispatcher raises `PendingBatchError`, which the executor catches — leaving the artifact in `not_started` and marking the run `interrupted`.

2. **Polling** (`wct poll <run-id>`): The `BatchResultPoller` checks batch status with the provider. When complete, it updates cache entries from `"pending"` to `"completed"` with actual responses.

3. **Resume** (`wct run --resume <run-id>`): The artifact is re-attempted. All prompts now hit the cache (populated by the poller), so it completes immediately.

### Enabling Batch Mode

```bash
export WAIVERN_LLM_BATCH_MODE=true
```

The provider must implement the `BatchLLMProvider` protocol. If the provider only implements `LLMProvider`, the dispatcher falls back to synchronous calls automatically. Currently, `OpenAIProvider` implements `BatchLLMProvider`.

### BatchLLMProvider Protocol

Providers that support batch mode implement this protocol alongside `LLMProvider`:

```python
from waivern_llm import BatchLLMProvider

class MyBatchProvider(LLMProvider, BatchLLMProvider):
    async def submit_batch(self, requests: list[BatchRequest]) -> BatchSubmission: ...
    async def get_batch_status(self, batch_id: str) -> BatchStatus: ...
    async def get_batch_results(self, batch_id: str) -> list[BatchResult]: ...
    async def cancel_batch(self, batch_id: str) -> None: ...
```

### BatchResultPoller

Polls for batch completion and populates the LLM cache:

```python
from waivern_llm import BatchResultPoller, PollResult

poller = BatchResultPoller(
    store=artifact_store,
    provider=batch_provider,
    provider_name="anthropic",
    model_name="claude-sonnet-4-5-20250929",
)

result: PollResult = await poller.poll_run(run_id)
# result.completed, result.failed, result.pending, result.errors
```

## Environment Variables

| Variable                  | Description                                     | Required                                              |
| ------------------------- | ----------------------------------------------- | ----------------------------------------------------- |
| `LLM_PROVIDER`            | Provider (`anthropic`, `openai`, `google`)      | Yes                                                   |
| `WAIVERN_LLM_BATCH_MODE`  | Enable batch mode (`true`/`false`)              | No (default: `false`)                                 |
| `ANTHROPIC_API_KEY`       | Anthropic API key                               | If using Anthropic                                    |
| `ANTHROPIC_MODEL`         | Model name (e.g., `claude-sonnet-4-5-20250929`) | No                                                    |
| `OPENAI_API_KEY`          | OpenAI API key                                  | If using OpenAI (not required with `OPENAI_BASE_URL`) |
| `OPENAI_MODEL`            | Model name                                      | No                                                    |
| `OPENAI_BASE_URL`         | Base URL for OpenAI-compatible APIs             | For local LLMs                                        |
| `GOOGLE_API_KEY`          | Google API key                                  | If using Google                                       |
| `GOOGLE_MODEL`            | Model name                                      | No                                                    |

## Local LLM Support

Use local LLMs (LM Studio, Ollama, vLLM) via OpenAI-compatible API:

```bash
export LLM_PROVIDER=openai
export OPENAI_BASE_URL=http://localhost:1234/v1  # LM Studio default
export OPENAI_MODEL=your-local-model-name
# OPENAI_API_KEY is not required when OPENAI_BASE_URL is set
```
