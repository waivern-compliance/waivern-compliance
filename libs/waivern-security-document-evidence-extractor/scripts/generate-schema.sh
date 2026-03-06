#!/bin/bash

# Generate JSON schema from Pydantic model for security_document_context
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating security_document_context JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_security_document_evidence_extractor.schemas import SecurityDocumentContextOutput

output_path = Path('src/waivern_security_document_evidence_extractor/schemas/json_schemas/security_document_context/1.0.0/security_document_context.json')
SecurityDocumentContextOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
