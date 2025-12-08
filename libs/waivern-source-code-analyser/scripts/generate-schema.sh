#!/bin/bash

# Generate JSON schema from Pydantic model for source_code
# Usage: bash scripts/generate-schema.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PACKAGE_DIR"

echo "Generating source_code JSON schema..."

uv run python -c "
from pathlib import Path
from waivern_source_code_analyser.schemas import SourceCodeDataModel

output_path = Path('src/waivern_source_code_analyser/schemas/json_schemas/source_code/1.0.0/source_code.json')
SourceCodeDataModel.generate_json_schema(output_path)
print(f'Generated: {output_path}')
"

echo "Done!"
