#!/bin/bash

# Generate JSON schema from Pydantic model for security_evidence
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating security_evidence JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_security_evidence.schemas import SecurityEvidenceOutput

output_path = Path('src/waivern_security_evidence/schemas/json_schemas/security_evidence/1.0.0/security_evidence.json')
SecurityEvidenceOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
