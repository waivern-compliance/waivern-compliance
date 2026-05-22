# Documentation

User- and contributor-facing documentation for the Waivern Compliance Framework. Internal package documentation lives next to each package under `libs/<package>/docs/`.

## Core Concepts

Start here if you are new to WCF.

- [WCF Core Components](core-concepts/wcf-core-components.md) — Connectors, analysers, schemas, runbooks
- [Regulatory Framework Architecture](core-concepts/regulatory-framework-architecture.md) — How WCF separates technical analysis from regulatory interpretation

## How-Tos

Task-oriented guides.

- [Configuration](how-tos/configuration.md) — Environment variables, `.env` file, LLM providers, MySQL credentials
- [IDE Integration](how-tos/ide-integration.md) — JSON Schema autocomplete for runbooks in VS Code, PyCharm, Vim, Emacs
- [Extending WCF](how-tos/extending-wcf.md) — Build custom connectors, analysers, rulesets, and language plugins

## Architecture Decisions

- [ADR Index](adr/) — Architecture Decision Records

## Package-Level Documentation

Implementation-detail docs live with their code:

- [Orchestration & DAG execution](../libs/waivern-orchestration/docs/) — Runbook format, planner/executor, child runbook composition, artifact-centric orchestration
- [Artifact Store](../libs/waivern-artifact-store/docs/) — Storage architecture, caching, external sources
- [Core abstractions](../libs/waivern-core/docs/) — Processor input requirements, DI factory patterns
- [Source code analyser](../libs/waivern-source-code-analyser/docs/) — Language plugin architecture
- [Analyser-shared utilities](../libs/waivern-analysers-shared/docs/) — Ruleset management
- Each component package's `README.md`

## Runbooks

- [Runbook Reference](../apps/wct/runbooks/README.md) — Runbook format, fields, examples
- [Sample Runbooks](../apps/wct/runbooks/samples/)

## Contributing

Project conventions, development workflow, test isolation patterns, and commit standards live in [`CLAUDE.md`](../CLAUDE.md) at the workspace root.
