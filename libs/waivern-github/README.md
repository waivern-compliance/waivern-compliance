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

## Authentication

### Personal Access Token (Default)

```bash
export GITHUB_TOKEN="ghp_xxxx"
```

### GitHub App

```bash
export GITHUB_APP_ID="12345"
export GITHUB_PRIVATE_KEY_PATH="/path/to/private-key.pem"
export GITHUB_INSTALLATION_ID="67890"
```

Then set `auth_method: "app"` in your runbook properties.

## Clone Strategies

| Strategy  | Description                             | Use Case               |
| --------- | --------------------------------------- | ---------------------- |
| `minimal` | --depth 1 --filter=blob:none --sparse   | Analysis (default)     |
| `partial` | --filter=blob:none --sparse             | Need history           |
| `shallow` | --depth 1                               | Quick full checkout    |
| `full`    | Complete clone                          | Complete repo          |
