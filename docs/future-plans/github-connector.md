# GitHub Connector Design

- **Version:** 1.0.0 (Draft)
- **Last Updated:** 2025-12-23
- **Status:** Design Draft

## Overview

Enable WCF to analyse source code directly from GitHub repositories by introducing a new `GitHubConnector` that outputs `standard_input` schema.

## Current Architecture (No Changes Needed)

The existing architecture is already well-designed for this extension:

```
FilesystemConnector → standard_input → SourceCodeAnalyser → source_code
                           ↓
                    (schema contract)
                           ↓
       SourceCodeAnalyser only knows about standard_input
```

**Key insight:** `SourceCodeAnalyser` is agnostic to data source. It consumes `standard_input` and produces `source_code`. This means we simply need a new connector that outputs `standard_input`.

## Proposed Architecture

```
┌──────────────────────┐     ┌─────────────────────┐
│  GitHubConnector     │     │ FilesystemConnector │
│  (new)               │     │ (existing)          │
│                      │     │                     │
│  Output:             │     │  Output:            │
│  standard_input      │     │  standard_input     │
└──────────┬───────────┘     └──────────┬──────────┘
           │                            │
           └────────────┬───────────────┘
                        │
                        ▼
              ┌────────────────────────┐
              │ SourceCodeAnalyser     │
              │ (unchanged)            │
              │                        │
              │ Input:  standard_input │
              │ Output: source_code    │
              └────────────────────────┘
```

## Package Structure

```
libs/waivern-github/
├── pyproject.toml
├── src/waivern_github/
│   ├── __init__.py
│   ├── connector.py              # GitHubConnector
│   ├── config.py                 # GitHubConnectorConfig
│   ├── auth.py                   # Authentication (PAT, GitHub App)
│   ├── clone.py                  # Clone strategies
│   ├── cache.py                  # Clone caching
│   └── schema_producers/
│       ├── __init__.py
│       └── standard_input_1_0_0.py
├── tests/
└── scripts/
```

## Configuration

```python
class GitHubConnectorConfig(BaseComponentConfiguration):
    """Configuration for GitHubConnector."""

    repository: str                                    # "owner/repo"
    ref: str = "HEAD"                                  # branch, tag, or commit SHA
    include_patterns: list[str] | None = None         # Sparse checkout patterns
    exclude_patterns: list[str] | None = None         # Patterns to exclude
    max_files: int = 1000                             # Safety limit

    # Authentication
    auth_method: Literal["pat", "app"] = "pat"
    # PAT: GITHUB_TOKEN env var
    # App: GITHUB_APP_ID, GITHUB_PRIVATE_KEY, GITHUB_INSTALLATION_ID env vars

    # Clone strategy
    clone_strategy: Literal["full", "shallow", "partial", "minimal"] = "minimal"
    # minimal: --depth 1 --filter=blob:none --sparse (recommended for analysis)
    # partial: --filter=blob:none + sparse checkout (keeps history)
    # shallow: --depth 1 (all files, no history)
    # full: Complete clone with history

    # Caching
    cache_dir: Path | None = None                     # None = temp directory
    cache_ttl_hours: int = 24                         # Cache expiry
```

## Runbook Usage

```yaml
artifacts:
  # GitHub source
  github_php_files:
    source:
      type: "github"
      properties:
        repository: "company/webapp"
        ref: "main"
        include_patterns: ["src/**/*.php", "lib/**/*.php"]
        max_files: 500

  # Parse to AST (unchanged - just wire the inputs)
  source_code:
    inputs: github_php_files
    process:
      type: "source_code_analyser"
      properties:
        language: "php"
    output: true

  # Further analysis
  processing_purposes:
    inputs: source_code
    process:
      type: "processing_purpose"
    output: true
```

## Authentication

### Personal Access Token (Default)

```bash
export GITHUB_TOKEN="ghp_xxxx"
```

Runbook:

```yaml
properties:
  repository: "owner/repo"
  auth_method: "pat" # default
```

### GitHub App (Enterprise)

```bash
export GITHUB_APP_ID="12345"
export GITHUB_PRIVATE_KEY_PATH="/path/to/private-key.pem"
export GITHUB_INSTALLATION_ID="67890"
```

Runbook:

```yaml
properties:
  repository: "owner/repo"
  auth_method: "app"
```

**GitHub App advantages:**

- Fine-grained permissions
- Higher rate limits (5,000+ requests/hour)
- Installation-scoped tokens with automatic expiration

## Clone Strategies

| Strategy  | Command                                 | History | Files                | Use Case               |
| --------- | --------------------------------------- | ------- | -------------------- | ---------------------- |
| `minimal` | `--depth 1 --filter=blob:none --sparse` | No      | Specified paths only | **Analysis (default)** |
| `partial` | `--filter=blob:none --sparse`           | Yes     | Specified paths only | Need history           |
| `shallow` | `--depth 1`                             | No      | All files            | Quick full checkout    |
| `full`    | `git clone`                             | Yes     | All files            | Complete repo          |

**Recommended:** `minimal` for compliance analysis (no history needed):

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/owner/repo.git
cd repo
git sparse-checkout set --cone src/php lib/php
```

This achieves the smallest possible download - only the latest commit's directory structure, with file contents fetched on-demand for specified paths only.

## Caching

### Session Cache (Default)

Clone persists for the duration of the runbook execution, then cleaned up.

### Persistent Cache

```yaml
properties:
  cache_dir: "/var/cache/waivern/github"
  cache_ttl_hours: 24
```

Cache key: `{repository}:{ref}:{include_patterns_hash}`

On subsequent runs:

1. Check if cached clone exists and is fresh
2. If fresh: `git fetch origin {ref}` + `git checkout`
3. If stale or missing: Fresh clone

## Metadata

Reuse existing `FilesystemMetadata` (file_path is the only file-specific field needed):

```python
# In schema producer
metadata = FilesystemMetadata(
    source=str(relative_path),           # "src/controllers/UserController.php"
    connector_type="github_connector",
    file_path=str(relative_path),
)
```

The `standard_input` schema remains unchanged. Downstream analysers see the same structure regardless of source.

## Error Handling

| Error          | Behaviour                                         |
| -------------- | ------------------------------------------------- |
| Auth failure   | `ConnectorConfigError` with clear message         |
| Repo not found | `ConnectorConfigError`                            |
| Ref not found  | `ConnectorConfigError`                            |
| Clone timeout  | `ConnectorExtractionError` (configurable timeout) |
| Rate limited   | Retry with exponential backoff, then fail         |
| Network error  | `ConnectorExtractionError`                        |

## Dependencies

```toml
[project]
dependencies = [
    "waivern-core",
    "pydantic>=2.0",
]

[project.optional-dependencies]
github-app = ["PyJWT>=2.0", "cryptography>=3.0"]
```

Git operations via subprocess (no GitPython dependency - more reliable).

## Entry Point

```toml
[project.entry-points."waivern.connectors"]
github = "waivern_github:GitHubConnector"
```

## Test Strategy

| Test Type          | Scope                                                         |
| ------------------ | ------------------------------------------------------------- |
| Unit               | Config validation, metadata generation, cache key computation |
| Integration        | Clone public repos (e.g., `octocat/Hello-World`)              |
| Integration (auth) | Marked `pytest.mark.integration`, requires credentials        |

## Future Considerations

- **GitLab/Bitbucket:** Same pattern, different auth. Could share base `GitConnector` class.
- **Webhook triggers:** For CI/CD integration, trigger analysis on push events.
- **Incremental analysis:** Cache previous analysis results, only re-analyse changed files.

## Non-Goals

- Direct GitHub API file fetching (clone is more efficient for multi-file analysis)
- GitHub Actions integration (out of scope for connector)
- Issue/PR analysis (different data type, would need separate connector)
