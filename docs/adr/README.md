# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the Waivern Compliance Framework.

## What is an ADR?

An Architecture Decision Record (ADR) captures a single architectural decision and its rationale. ADRs help us:

- Understand the context and reasoning behind important decisions
- Document trade-offs and alternatives considered
- Provide historical context for future contributors
- Enable informed decisions about changing or extending the architecture

## ADR Format

We use Michael Nygard's template, which includes:

- **Title**: Short, descriptive name for the decision
- **Status**: Current state (Proposed, Accepted, Deprecated, Superseded)
- **Context**: The issue motivating this decision
- **Decision**: The change we're proposing/implementing
- **Consequences**: What becomes easier or more difficult

## ADR Numbering

ADRs are numbered sequentially with a 4-digit prefix:
- `0001-first-decision.md`
- `0002-second-decision.md`
- etc.

## When to Create an ADR

Create an ADR when making decisions about:

- Framework architecture and design patterns
- Technology choices (libraries, tools, languages)
- API design and interfaces
- Data structures and schemas
- Performance vs. maintainability trade-offs
- Security and compliance approaches

## ADR Lifecycle

1. **Proposed**: Draft ADR for discussion
2. **Accepted**: Decision approved and implemented
3. **Deprecated**: Decision no longer recommended but still in use
4. **Superseded**: Replaced by a newer decision (reference the new ADR)

## Index

- [ADR-0001](0001-explicit-schema-loading-over-autodiscovery.md) - Use Explicit Configuration for Schema Loading
- [ADR-0002](0002-dependency-injection-for-service-management.md) - Dependency Injection Container for Service Management
