#!/bin/bash

# Generate JSON schema from Pydantic model for iso27001_assessment
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating iso27001_assessment JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_iso27001_control_assessor.schemas import ISO27001AssessmentOutput

output_path = Path('src/waivern_iso27001_control_assessor/schemas/json_schemas/iso27001_assessment/1.0.0/iso27001_assessment.json')
ISO27001AssessmentOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
