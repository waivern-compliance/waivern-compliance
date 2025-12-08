#!/bin/bash

# Generate JSON schema from Pydantic model for processing_purpose_finding
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating processing_purpose_finding JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_processing_purpose_analyser.schemas import ProcessingPurposeFindingOutput

output_path = Path('src/waivern_processing_purpose_analyser/schemas/json_schemas/processing_purpose_finding/1.0.0/processing_purpose_finding.json')
ProcessingPurposeFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
