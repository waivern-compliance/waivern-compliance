# waivern-http

Shared HTTP client service with authentication and resilience for the Waivern Compliance Framework.

## Overview

This package provides a single, pooled HTTP client service (`HttpClientService`) for
framework components that need to call external HTTP services. Concentrating connection
pooling, credential resolution, and resilience here keeps `waivern-core` dependency-light —
`httpx` enters the dependency tree in this package, not in core.

## Components

- **HttpClientService** — wraps a single pooled `httpx.AsyncClient`, enforces timeouts, and
  resolves an *auth reference* (a credential name) to a secret at call time.
- **HttpClientServiceConfiguration** — timeouts and circuit-breaker thresholds, with sensible
  defaults and environment-variable fallback.

## Authentication

Requests carry an *auth reference* — a credential name, never the secret itself. The service
resolves the reference to a secret from the environment at call time:

```
auth_ref = "acme_saas"  →  reads WAIVERN_HTTP_AUTH_ACME_SAAS  →  Authorization: Bearer <secret>
```

The secret is never persisted and never logged.

## License

See LICENSE file in the repository root.
