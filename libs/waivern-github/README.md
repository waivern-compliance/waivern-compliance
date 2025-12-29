# waivern-github

GitHub connector for Waivern Compliance Framework (WCF).

Clones GitHub repositories and outputs `standard_input` schema for analysis by downstream processors.

## Installation

```bash
uv sync --all-packages
```

## Usage

```yaml
artifacts:
  github_files:
    source:
      type: "github"
      properties:
        repository: "owner/repo"
        ref: "main"
        include_patterns: ["src/**/*.php"]
```

## Configuration Options

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `repository` | string | *required* | Repository in `owner/repo` format |
| `ref` | string | `HEAD` | Branch, tag, or commit SHA |
| `clone_strategy` | string | `minimal` | Clone strategy (see below) |
| `include_patterns` | list | `null` | Glob patterns to include |
| `exclude_patterns` | list | `null` | Glob patterns to exclude |
| `max_files` | int | `1000` | Maximum files to process |
| `clone_timeout` | int | `300` | Clone timeout in seconds |
| `auth_method` | string | `pat` | Authentication method (`pat` or `app`) |

> **Note:** `include_patterns` and `exclude_patterns` are mutually exclusive.

## Authentication

### Personal Access Token (Default)

```bash
export GITHUB_TOKEN="ghp_xxxx"
```

### GitHub App

```bash
export GITHUB_APP_ID="12345"
export GITHUB_APP_PRIVATE_KEY_PATH="/path/to/private-key.pem"
export GITHUB_APP_INSTALLATION_ID="67890"
```

Then set `auth_method: "app"` in your runbook properties.

## Clone Strategies

| Strategy  | Description                             | Use Case               |
| --------- | --------------------------------------- | ---------------------- |
| `minimal` | --depth 1 --filter=blob:none --sparse   | Analysis (default)     |
| `partial` | --filter=blob:none --sparse             | Need history           |
| `shallow` | --depth 1                               | Quick full checkout    |
| `full`    | Complete clone                          | Complete repo          |

## Development

This package is part of the Waivern Compliance Framework monorepo.

### Running Tests

```bash
# Unit tests
uv run pytest libs/waivern-github

# Integration tests (requires network access)
uv run pytest libs/waivern-github -m integration
```
