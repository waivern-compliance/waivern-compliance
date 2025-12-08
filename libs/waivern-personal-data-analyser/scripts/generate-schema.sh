#!/bin/bash

# Generate JSON schema from Pydantic model for personal_data_finding
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating personal_data_finding JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_personal_data_analyser.schemas import PersonalDataFindingOutput

output_path = Path('src/waivern_personal_data_analyser/schemas/json_schemas/personal_data_finding/1.0.0/personal_data_finding.json')
PersonalDataFindingOutput.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
