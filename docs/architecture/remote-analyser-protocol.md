# Remote Analyser Protocol Specification

**Version:** 1.0.0 (Draft)
**Last Updated:** 2025-11-03
**Status:** Specification Draft

## Overview

The Remote Analyser Protocol defines how WCT communicates with analyser services hosted as HTTP endpoints. This enables analysers to run as microservices, supporting scalable deployments, third-party services, and hybrid local/remote workflows.

## Design Principles

1. **Async-First** - All analyses return asynchronously (compliance analysis is inherently long-running)
2. **Streaming by Default** - Server-Sent Events (SSE) for real-time progress feedback
3. **Schema-Driven** - All data exchange validated against JSON Schema
4. **Batch-Friendly** - Batch operations as first-class citizens (most analyses involve multiple items)
5. **Stateless** - Each request is independent
6. **RESTful** - Standard HTTP methods and status codes
7. **Versioned** - API and schema versioning for compatibility
8. **Layered Architecture** - Separation between transport and domain layers

## Architecture: Hybrid Envelope Pattern

The protocol uses a **hybrid envelope pattern** that separates transport concerns from domain data:

```json
{
  // HTTP Envelope (Transport Layer)
  "request_id": "uuid-1234-5678",        // Request tracking
  "status": "completed",                  // Execution status
  "execution_metadata": {...},            // HTTP metrics

  // WCF Message (Domain Layer)
  "message": {
    "id": "msg-5678-1234",               // Message ID
    "content": {...},                     // Analysis data
    "schema": {...},                      // Schema definition
    "context": {...}                      // Optional metadata
  }
}
```

**Benefits:**
- **Clean separation** - Transport vs. domain concerns
- **WCF alignment** - Message structure matches internal `Message` class
- **Protocol independence** - Same Message can be used over HTTP, gRPC, WebSocket, etc.
- **Minimal translation** - WCT easily converts between HTTP and internal Message
- **Industry standard** - Follows patterns from GitHub, AWS, Stripe APIs

## Base URL Structure

```
{protocol}://{host}:{port}/v{api_version}/analysers
```

Examples:
- `https://api.example.com/v1/analysers`
- `http://localhost:8080/v1/analysers`
- `https://analyser.internal.corp/v1/analysers`

## Authentication

### API Key (Bearer Token)

```http
Authorization: Bearer {api_key}
```

### Basic Authentication

```http
Authorization: Basic {base64(username:password)}
```

### Custom Headers

```http
X-API-Key: {api_key}
```

Implementation-specific. Services should document their authentication method.

## Core Endpoints

### 1. Discovery

Get list of available analysers from the service.

```http
GET /v1/analysers
Authorization: Bearer {api_key}
```

**Response:**
```json
{
  "api_version": "1.0.0",
  "analysers": [
    {
      "name": "gdpr_legal_basis_analyser",
      "type": "gdpr_legal_basis_analyser",
      "version": "2.1.0",
      "description": "Analyses legal basis for data processing under GDPR",
      "supported_input_schemas": [
        {
          "name": "standard_input",
          "version": "1.0.0"
        },
        {
          "name": "personal_data_finding",
          "version": "1.0.0"
        }
      ],
      "supported_output_schemas": [
        {
          "name": "legal_basis_finding",
          "version": "1.0.0"
        }
      ],
      "execution_url": "/v1/analysers/gdpr_legal_basis_analyser/execute",
      "batch_url": "/v1/analysers/gdpr_legal_basis_analyser/batch",
      "capabilities": {
        "streaming": true,
        "batch_processing": true,
        "polling": true,
        "max_batch_size": 100
      }
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Invalid credentials
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Service error

### 2. Execute Analyser

Execute analysis on provided data. All analyses are asynchronous. Clients can choose between streaming (SSE) or polling modes via the `Accept` header.

#### Option A: Streaming Mode (Recommended)

Real-time progress updates via Server-Sent Events. Ideal for analyses completing within minutes.

```http
POST /v1/analysers/{analyser_type}/execute
Content-Type: application/json
Accept: text/event-stream
Authorization: Bearer {api_key}

{
  "request_id": "uuid-1234-5678",
  "message": {
    "id": "msg-5678-1234",
    "content": {
      "source": "mysql_database",
      "entities": [
        {
          "entity_type": "column",
          "entity_name": "users.email",
          "content": "user@example.com",
          "metadata": {}
        }
      ]
    },
    "schema": {
      "name": "standard_input",
      "version": "1.0.0"
    },
    "context": {
      "options": {
        "llm_validation": {
          "enable": true
        }
      }
    }
  }
}
```

**Response (SSE Stream):**
```http
HTTP/1.1 202 Accepted
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: started
data: {"request_id":"uuid-1234-5678","status":"processing","timestamp":"2025-11-03T10:00:00Z"}

event: progress
data: {"request_id":"uuid-1234-5678","progress":25,"message":"Analyzing entity users.email"}

event: progress
data: {"request_id":"uuid-1234-5678","progress":50,"message":"Running LLM validation"}

event: progress
data: {"request_id":"uuid-1234-5678","progress":75,"message":"Finalizing results"}

event: completed
data: {"request_id":"uuid-1234-5678","status":"completed","result_url":"/v1/analysers/results/uuid-1234-5678","result_size_bytes":1024,"execution_metadata":{"duration_ms":1250,"analyser_version":"2.1.0","timestamp":"2025-11-03T10:00:01Z"}}
```

**SSE Event Types:**
- `started` - Analysis has begun
- `progress` - Progress update (includes percentage and message)
- `completed` - Analysis finished successfully (includes result URL)
- `failed` - Analysis failed (includes error details)

#### Option B: Polling Mode

For long-running analyses or when SSE is not supported. Client polls for status updates.

```http
POST /v1/analysers/{analyser_type}/execute
Content-Type: application/json
Accept: application/json
Authorization: Bearer {api_key}

{
  "request_id": "uuid-1234-5678",
  "message": {...}
}
```

**Response (Polling):**
```json
HTTP/1.1 202 Accepted

{
  "request_id": "uuid-1234-5678",
  "status": "processing",
  "status_url": "/v1/analysers/status/uuid-1234-5678",
  "estimated_duration_seconds": 300,
  "poll_interval_seconds": 30
}
```

**Status Codes:**
- `202 Accepted` - Analysis started (always async)
- `400 Bad Request` - Invalid request format or schema validation failed
- `401 Unauthorized` - Invalid credentials
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Analyser type not found
- `422 Unprocessable Entity` - Data doesn't match input schema
- `429 Too Many Requests` - Rate limit exceeded
- `503 Service Unavailable` - Service overloaded

### 3. Check Execution Status

For polling mode, check status of long-running analyses.

```http
GET /v1/analysers/status/{request_id}
Authorization: Bearer {api_key}
```

**Response (In Progress):**
```json
{
  "request_id": "uuid-1234-5678",
  "status": "processing",
  "progress": 45,
  "message": "Running LLM validation",
  "estimated_completion": "2025-11-03T10:05:00Z",
  "poll_interval_seconds": 30
}
```

**Response (Completed):**
```json
{
  "request_id": "uuid-1234-5678",
  "status": "completed",
  "result_url": "/v1/analysers/results/uuid-1234-5678",
  "result_size_bytes": 2458,
  "execution_metadata": {
    "duration_ms": 45000,
    "analyser_version": "2.1.0",
    "timestamp": "2025-11-03T10:05:00Z"
  }
}
```

**Response (Failed):**
```json
{
  "request_id": "uuid-1234-5678",
  "status": "failed",
  "error": {
    "code": "EXECUTION_ERROR",
    "message": "Analysis failed: Invalid input data",
    "details": {
      "cause": "LLM service unavailable"
    }
  }
}
```

**Status Values:**
- `accepted` - Request received, queued
- `processing` - Execution in progress
- `completed` - Execution succeeded
- `failed` - Execution failed
- `cancelled` - Execution cancelled

**Status Codes:**
- `200 OK` - Status retrieved successfully
- `404 Not Found` - Request ID not found or expired
- `401 Unauthorized` - Invalid credentials

### 4. Fetch Analysis Results

Retrieve the completed analysis result. Results are retained for a limited time (typically 24-72 hours).

```http
GET /v1/analysers/results/{request_id}
Authorization: Bearer {api_key}
```

**Response:**
```json
{
  "request_id": "uuid-1234-5678",
  "message": {
    "id": "msg-5678-1234",
    "content": {
      "findings": [
        {
          "entity": "users.email",
          "legal_basis": "legitimate_interest",
          "confidence": 0.85,
          "evidence": "Email used for account management"
        }
      ]
    },
    "schema": {
      "name": "legal_basis_finding",
      "version": "1.0.0"
    },
    "context": null
  },
  "execution_metadata": {
    "duration_ms": 45000,
    "analyser_version": "2.1.0",
    "timestamp": "2025-11-03T10:05:00Z"
  }
}
```

**Status Codes:**
- `200 OK` - Result retrieved successfully
- `202 Accepted` - Result not ready yet (analysis still in progress)
- `404 Not Found` - Result expired or request ID not found
- `401 Unauthorized` - Invalid credentials
- `410 Gone` - Result expired and has been deleted

**Result Retention:**
- Services SHOULD retain results for at least 24 hours
- Services MAY delete results after retention period
- Clients SHOULD fetch results promptly after completion
- Services SHOULD document their retention policy

**Result Size Recommendations:**
- Services SHOULD use compression (gzip/brotli) for result responses
- Services SHOULD support results up to 50MB uncompressed
- Services SHOULD paginate results exceeding 50MB uncompressed (future enhancement)
- Most compliance analyses generate 1-20MB of findings (compresses to 100KB-2MB)
- Very large codebases (10,000+ files) may require pagination in future versions

### 5. Batch Execution

Execute multiple analyses in a single request. Particularly useful for analysing multiple database columns, files, or code entities.

```http
POST /v1/analysers/{analyser_type}/batch
Content-Type: application/json
Accept: text/event-stream
Authorization: Bearer {api_key}

{
  "request_id": "batch-uuid-1234",
  "messages": [
    {
      "id": "msg-001",
      "content": {
        "source": "mysql_database",
        "entities": [
          {
            "entity_type": "column",
            "entity_name": "users.email",
            "content": "user@example.com"
          }
        ]
      },
      "schema": {
        "name": "standard_input",
        "version": "1.0.0"
      }
    },
    {
      "id": "msg-002",
      "content": {
        "source": "mysql_database",
        "entities": [
          {
            "entity_type": "column",
            "entity_name": "users.phone_number",
            "content": "+44 20 1234 5678"
          }
        ]
      },
      "schema": {
        "name": "standard_input",
        "version": "1.0.0"
      }
    }
  ],
  "options": {
    "parallel": true,
    "max_concurrency": 5,
    "stop_on_error": false
  }
}
```

**Response (SSE Stream):**
```http
HTTP/1.1 202 Accepted
Content-Type: text/event-stream

event: started
data: {"request_id":"batch-uuid-1234","total_items":2,"status":"processing"}

event: item_completed
data: {"request_id":"batch-uuid-1234","item_id":"msg-001","progress":50,"result_url":"/v1/analysers/results/msg-001"}

event: item_completed
data: {"request_id":"batch-uuid-1234","item_id":"msg-002","progress":100,"result_url":"/v1/analysers/results/msg-002"}

event: completed
data: {"request_id":"batch-uuid-1234","status":"completed","total_items":2,"successful":2,"failed":0,"result_urls":["/v1/analysers/results/msg-001","/v1/analysers/results/msg-002"],"execution_metadata":{"duration_ms":5400,"timestamp":"2025-11-03T10:00:05Z"}}
```

**Batch Options:**
- `parallel` - Process items in parallel (default: true)
- `max_concurrency` - Maximum parallel executions (default: 10)
- `stop_on_error` - Stop batch if one item fails (default: false)

**SSE Event Types:**
- `started` - Batch processing started
- `item_completed` - Individual item finished (includes result URL)
- `item_failed` - Individual item failed (includes error)
- `progress` - Overall batch progress update
- `completed` - All items processed (includes all result URLs)
- `failed` - Batch processing failed

**Polling Mode:**

For polling mode (`Accept: application/json`), response includes batch status URL:

```json
{
  "request_id": "batch-uuid-1234",
  "status": "processing",
  "total_items": 2,
  "completed_items": 1,
  "failed_items": 0,
  "progress": 50,
  "status_url": "/v1/analysers/batch/batch-uuid-1234",
  "poll_interval_seconds": 30
}
```

**Status Codes:**
- `202 Accepted` - Batch processing started
- `400 Bad Request` - Invalid batch request
- `413 Payload Too Large` - Batch size exceeds limit

### 6. Health Check

Service health status.

```http
GET /v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2025-11-03T10:00:00Z",
  "checks": {
    "database": "healthy",
    "llm_service": "healthy"
  }
}
```

**Status Codes:**
- `200 OK` - Service healthy
- `503 Service Unavailable` - Service unhealthy

## Request Schema

### Execute Request

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "request_id": {
      "type": "string",
      "description": "HTTP request ID for tracking (transport layer)"
    },
    "message": {
      "type": "object",
      "description": "WCF Message object (domain layer)",
      "properties": {
        "id": {
          "type": "string",
          "description": "Message ID"
        },
        "content": {
          "type": "object",
          "description": "Message content conforming to the schema"
        },
        "schema": {
          "type": "object",
          "description": "Schema definition",
          "properties": {
            "name": {"type": "string"},
            "version": {"type": "string"}
          },
          "required": ["name", "version"]
        },
        "context": {
          "type": "object",
          "description": "Optional context metadata",
          "nullable": true
        }
      },
      "required": ["id", "content", "schema"]
    }
  },
  "required": ["message"]
}
```

### Execute Response (Async - Polling Mode)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "request_id": {
      "type": "string",
      "description": "HTTP request ID (transport layer)"
    },
    "status": {
      "enum": ["accepted", "processing"],
      "description": "Execution status (always async)"
    },
    "status_url": {
      "type": "string",
      "description": "URL to poll for status updates"
    },
    "estimated_duration_seconds": {
      "type": "integer",
      "description": "Estimated time to completion"
    },
    "poll_interval_seconds": {
      "type": "integer",
      "description": "Recommended polling interval"
    }
  },
  "required": ["request_id", "status", "status_url"]
}
```

### Status Response

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "request_id": {
      "type": "string",
      "description": "HTTP request ID"
    },
    "status": {
      "enum": ["accepted", "processing", "completed", "failed", "cancelled"],
      "description": "Current execution status"
    },
    "progress": {
      "type": "integer",
      "description": "Progress percentage (0-100, when status=processing)"
    },
    "message": {
      "type": "string",
      "description": "Status message (when status=processing)"
    },
    "result_url": {
      "type": "string",
      "description": "URL to fetch results (when status=completed)"
    },
    "result_size_bytes": {
      "type": "integer",
      "description": "Size of result payload (when status=completed)"
    },
    "execution_metadata": {
      "type": "object",
      "description": "Execution metrics (when status=completed)",
      "properties": {
        "duration_ms": {"type": "integer"},
        "analyser_version": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"}
      }
    },
    "error": {
      "type": "object",
      "description": "Error details (when status=failed)",
      "properties": {
        "code": {"type": "string"},
        "message": {"type": "string"},
        "details": {"type": "object"}
      }
    }
  },
  "required": ["request_id", "status"]
}
```

### Result Response

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "request_id": {
      "type": "string",
      "description": "HTTP request ID"
    },
    "message": {
      "type": "object",
      "description": "WCF Message object (domain layer)",
      "properties": {
        "id": {
          "type": "string",
          "description": "Message ID"
        },
        "content": {
          "type": "object",
          "description": "Analysis results conforming to output schema"
        },
        "schema": {
          "type": "object",
          "description": "Output schema definition",
          "properties": {
            "name": {"type": "string"},
            "version": {"type": "string"}
          },
          "required": ["name", "version"]
        },
        "context": {
          "type": "object",
          "description": "Optional context metadata",
          "nullable": true
        }
      },
      "required": ["id", "content", "schema"]
    },
    "execution_metadata": {
      "type": "object",
      "description": "Execution metrics",
      "properties": {
        "duration_ms": {"type": "integer"},
        "analyser_version": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"}
      }
    }
  },
  "required": ["request_id", "message"]
}
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional context"
    },
    "request_id": "uuid-1234-5678"
  }
}
```

### Standard Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request |
| `SCHEMA_VALIDATION_FAILED` | 422 | Data doesn't match schema |
| `ANALYSER_NOT_FOUND` | 404 | Analyser type not found |
| `UNAUTHORIZED` | 401 | Invalid credentials |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `EXECUTION_ERROR` | 500 | Analysis failed |
| `SERVICE_UNAVAILABLE` | 503 | Service overloaded |
| `TIMEOUT` | 504 | Execution timed out |

## Schema Validation

### Input Validation

1. Service MUST validate input against declared input schema
2. Return `422 Unprocessable Entity` if validation fails
3. Include validation errors in response:

```json
{
  "error": {
    "code": "SCHEMA_VALIDATION_FAILED",
    "message": "Input data does not match schema",
    "details": {
      "schema": "standard_input",
      "version": "1.0.0",
      "errors": [
        {
          "path": "$.entities[0].entity_type",
          "message": "Required field missing"
        }
      ]
    }
  }
}
```

### Output Validation

1. Service MUST produce output matching declared output schema
2. WCT validates response against schema
3. Invalid responses treated as execution errors

## Rate Limiting

Services SHOULD implement rate limiting:

**Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699000000
```

**Response when exceeded:**
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Retry after 60 seconds."
  }
}
```

## Timeout Handling

### Request Timeouts

Services SHOULD document expected execution times:

```json
{
  "analysers": [{
    "name": "slow_analyser",
    "expected_duration_ms": 30000,
    "timeout_ms": 60000
  }]
}
```

### Client Timeout Behaviour

WCT implements timeouts:
1. Connection timeout: 30 seconds
2. SSE stream timeout: 5 minutes (configurable, for fast analyses)
3. Polling timeout: 1 hour (configurable, for long-running analyses)
4. Individual poll read timeout: 30 seconds

## Security Considerations

### Transport Security

- MUST use HTTPS in production
- MAY use HTTP for localhost/development

### Authentication

- Services MUST implement authentication
- API keys SHOULD be rotatable
- SHOULD support multiple authentication methods

### Input Sanitisation

- Services MUST validate and sanitise all inputs
- Prevent injection attacks (SQL, command, etc.)
- Validate schema references

### Rate Limiting

- SHOULD implement per-client rate limits
- SHOULD implement global rate limits
- SHOULD provide clear error messages

### Audit Logging

- SHOULD log all requests (excluding sensitive data)
- SHOULD log authentication attempts
- SHOULD log errors and failures

### Data Privacy and Security Policies

Detailed security policies including data retention, encryption at rest, zero-knowledge architecture, and customer-controlled encryption keys should be defined by service providers according to their legal and compliance requirements.

**Technical capabilities provided by this protocol:**
- Encrypted transport (HTTPS/TLS)
- Multiple authentication methods
- Input validation and sanitisation
- Audit logging
- Regional data residency (via endpoint configuration)
- On-premises deployment option (zero external data transfer)

**Policy documentation:** For detailed security policies, data handling practices, and compliance certifications, refer to Waivern's legal documentation and customer agreements.

## Versioning

### API Versioning

Version in URL path: `/v1/analysers`

Breaking changes require new major version: `/v2/analysers`

### Schema Versioning

Schemas use semantic versioning: `"schema_version": "1.2.3"`

- Major version: Breaking changes
- Minor version: Backward-compatible additions
- Patch version: Bug fixes

### Version Compatibility

**Component-Level Validation:**

Each analyser declares which schema versions it supports via the discovery endpoint. When a request arrives, the analyser validates whether it can process the input schema version and produce the requested output schema version.

**Discovery Response:**
```json
{
  "analysers": [{
    "name": "gdpr_legal_basis_analyser",
    "supported_input_schemas": [
      {
        "name": "standard_input",
        "versions": ["1.0.0", "1.1.0", "1.2.0"]
      },
      {
        "name": "personal_data_finding",
        "versions": ["1.0.0", "1.1.0"]
      }
    ],
    "supported_output_schemas": [
      {
        "name": "legal_basis_finding",
        "versions": ["1.0.0", "1.1.0"]
      }
    ]
  }]
}
```

**Version Rejection:**

If the analyser cannot process the requested schema version, it returns `422 Unprocessable Entity`:

```json
{
  "error": {
    "code": "UNSUPPORTED_SCHEMA_VERSION",
    "message": "Analyser does not support standard_input version 2.0.0",
    "details": {
      "requested_schema": "standard_input",
      "requested_version": "2.0.0",
      "supported_versions": ["1.0.0", "1.1.0", "1.2.0"]
    }
  }
}
```

**Compatibility Strategy:**
- No centralized compatibility matrix required
- Each analyser independently declares supported versions
- Client (WCT) can query discovery endpoint before execution
- Clear error messages guide users to compatible versions

### Deprecation

Services SHOULD:
- Support multiple schema versions during transition periods
- Document deprecation timelines (minimum 6 months notice)
- Provide migration guides for breaking changes

## Implementation Examples

### Python (FastAPI) - Streaming Mode

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import json

app = FastAPI()

class Message(BaseModel):
    id: str
    content: dict
    schema: dict
    context: dict | None = None

class ExecuteRequest(BaseModel):
    request_id: str | None = None
    message: Message

@app.get("/v1/analysers")
async def list_analysers():
    return {
        "api_version": "1.0.0",
        "analysers": [{
            "name": "gdpr_legal_basis_analyser",
            "type": "gdpr_legal_basis_analyser",
            "capabilities": {
                "streaming": True,
                "batch_processing": True,
                "polling": True
            }
        }]
    }

@app.post("/v1/analysers/{analyser_type}/execute")
async def execute_analyser(
    analyser_type: str,
    request: ExecuteRequest,
    req: Request
):
    # Check if client accepts SSE
    if req.headers.get("accept") == "text/event-stream":
        return StreamingResponse(
            stream_analysis(request),
            media_type="text/event-stream"
        )

    # Polling mode - return 202 with status URL
    task_id = start_async_analysis(request)
    return {
        "request_id": request.request_id,
        "status": "processing",
        "status_url": f"/v1/analysers/status/{task_id}",
        "poll_interval_seconds": 30
    }

async def stream_analysis(request: ExecuteRequest):
    """Stream analysis progress via SSE"""
    # Send started event
    yield f"event: started\n"
    yield f"data: {json.dumps({'request_id': request.request_id, 'status': 'processing'})}\n\n"

    # Simulate analysis progress
    for progress in [25, 50, 75]:
        await asyncio.sleep(1)
        yield f"event: progress\n"
        yield f"data: {json.dumps({'request_id': request.request_id, 'progress': progress})}\n\n"

    # Execute actual analysis
    result = await run_analysis(request.message)

    # Store result for later retrieval
    await store_result(request.request_id, result)

    # Send completed event with result URL
    yield f"event: completed\n"
    yield f"data: {json.dumps({'request_id': request.request_id, 'status': 'completed', 'result_url': f'/v1/analysers/results/{request.request_id}', 'result_size_bytes': len(json.dumps(result))})}\n\n"

async def run_analysis(message: Message) -> dict:
    """Execute the actual analysis"""
    # Validate input schema
    # Run analysis logic
    # Return WCF Message object
    return {
        "id": message.id,
        "content": {"findings": [...]},
        "schema": {"name": "output_schema", "version": "1.0.0"},
        "context": None
    }

@app.get("/v1/analysers/results/{request_id}")
async def get_result(request_id: str):
    """Fetch analysis result"""
    result = await fetch_result(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found or expired")

    return {
        "request_id": request_id,
        "message": result["message"],
        "execution_metadata": result["execution_metadata"]
    }
```

### Node.js (Express) - Streaming Mode

```javascript
const express = require('express');
const app = express();

app.get('/v1/analysers', (req, res) => {
  res.json({
    api_version: '1.0.0',
    analysers: [{
      name: 'gdpr_legal_basis_analyser',
      type: 'gdpr_legal_basis_analyser',
      capabilities: {
        streaming: true,
        batch_processing: true,
        polling: true
      }
    }]
  });
});

app.post('/v1/analysers/:type/execute', async (req, res) => {
  const { request_id, message } = req.body;

  // Check if client accepts SSE
  if (req.headers.accept === 'text/event-stream') {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    // Send started event
    res.write(`event: started\ndata: ${JSON.stringify({
      request_id, status: 'processing'
    })}\n\n`);

    // Simulate progress
    const progress = [25, 50, 75];
    for (const p of progress) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      res.write(`event: progress\ndata: ${JSON.stringify({
        request_id, progress: p
      })}\n\n`);
    }

    // Execute analysis
    const result = await runAnalysis(message);

    // Store result
    await storeResult(request_id, result);

    // Send completed event with result URL
    res.write(`event: completed\ndata: ${JSON.stringify({
      request_id,
      status: 'completed',
      result_url: `/v1/analysers/results/${request_id}`,
      result_size_bytes: JSON.stringify(result).length
    })}\n\n`);

    res.end();
  } else {
    // Polling mode
    const taskId = await startAsyncAnalysis(req.body);
    res.status(202).json({
      request_id,
      status: 'processing',
      status_url: `/v1/analysers/status/${taskId}`,
      poll_interval_seconds: 30
    });
  }
});

app.get('/v1/analysers/results/:request_id', async (req, res) => {
  const result = await fetchResult(req.params.request_id);

  if (!result) {
    return res.status(404).json({
      error: {
        code: 'NOT_FOUND',
        message: 'Result not found or expired'
      }
    });
  }

  res.json({
    request_id: req.params.request_id,
    message: result.message,
    execution_metadata: result.execution_metadata
  });
});

async function runAnalysis(message) {
  // Validate and execute analysis
  return {
    id: message.id,
    content: { findings: [...] },
    schema: { name: 'output_schema', version: '1.0.0' },
    context: null
  };
}
```

## Testing

### Health Check

```bash
curl https://api.example.com/v1/health
```

### Discovery

```bash
curl -H "Authorization: Bearer API_KEY" \
  https://api.example.com/v1/analysers
```

### Execute (Streaming Mode)

```bash
curl -X POST \
  -H "Authorization: Bearer API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "request_id": "test-123",
    "message": {
      "id": "msg-123",
      "content": {...},
      "schema": {"name": "standard_input", "version": "1.0.0"}
    }
  }' \
  https://api.example.com/v1/analysers/my_analyser/execute
```

### Execute (Polling Mode)

```bash
# Start analysis
curl -X POST \
  -H "Authorization: Bearer API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "request_id": "test-123",
    "message": {...}
  }' \
  https://api.example.com/v1/analysers/my_analyser/execute

# Poll for status
curl -H "Authorization: Bearer API_KEY" \
  https://api.example.com/v1/analysers/status/test-123

# Fetch results when completed
curl -H "Authorization: Bearer API_KEY" \
  https://api.example.com/v1/analysers/results/test-123
```

### Batch Execute

```bash
curl -X POST \
  -H "Authorization: Bearer API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "request_id": "batch-123",
    "messages": [
      {"id": "msg-001", "content": {...}, "schema": {...}},
      {"id": "msg-002", "content": {...}, "schema": {...}}
    ]
  }' \
  https://api.example.com/v1/analysers/my_analyser/batch
```

## WCT Integration

WCT automatically uses remote analysers when configured:

```yaml
# runbook.yaml
analysers:
  - name: "remote_analyser"
    type: "gdpr_legal_basis_analyser"
    execution:
      mode: "remote"
      endpoint: "https://api.example.com/v1"
      authentication:
        api_key: "${MY_API_KEY}"
      streaming: true  # Use SSE streaming (default)
      timeout: 300000  # 5 minutes (polling mode)
```

WCT handles:
- Message serialisation/deserialisation
- Schema validation (input and output)
- Error handling with circuit breaker
- Timeout management
- Authentication
- SSE stream consumption
- Automatic fallback from streaming to polling
- Progress reporting to user
- Result fetching from result URLs

**Execution Flow:**
1. WCT sends analysis request (SSE or polling mode)
2. Service streams progress updates (SSE) or WCT polls status endpoint
3. On completion, service provides `result_url`
4. WCT fetches full result from result URL
5. WCT validates result against output schema
6. WCT writes findings to output file

**Network Resilience:**

WCT implements a **circuit breaker pattern** to prevent cascading failures when remote services are unavailable:

- **Closed state:** Normal operation, requests sent to remote service
- **Open state:** After threshold failures (e.g., 5 consecutive), circuit opens and requests fail fast
- **Half-open state:** After timeout period, allow test request to check if service recovered

This is sufficient for managed service deployments where:
- Services have reasonable SLAs
- Analyses are not mission-critical
- Fast failure is preferable to hanging requests

**Configuration:**
```yaml
# .waivern/config.yaml
deployment:
  saas:
    circuit_breaker:
      failure_threshold: 5
      timeout_seconds: 60
      half_open_max_requests: 1
```

## Related Documentation

- [Extending WCF](../development/extending-wcf.md) - Overview of extension mechanisms
- [Building Custom Components](../development/building-custom-components.md) - Component development guide
- [WCF Core Components](../core-concepts/wcf-core-components.md) - Framework architecture

## Future Enhancements

Potential future additions:
- WebSocket support as alternative to SSE
- GraphQL API variant for complex query patterns
- gRPC protocol option for high-performance scenarios
- Analysis cancellation endpoint
- Priority queuing for batch requests
- Partial result streaming (results as they become available)

## Feedback

This specification is in draft status. Feedback welcome:
- GitHub Discussions: https://github.com/waivern-compliance/waivern-compliance/discussions
- Issues: https://github.com/waivern-compliance/waivern-compliance/issues
