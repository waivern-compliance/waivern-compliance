# IDE Integration for WCT Runbooks

WCT runbooks support JSON Schema validation to provide enhanced developer experience with autocomplete, real-time validation, and documentation in your favourite IDE.

## Quick Start

1. **Generate schema** in your project:
   ```bash
   wct generate-schema
   ```

2. **Configure your IDE** (see specific instructions below)

3. **Start creating runbooks** with full IDE support!

## VS Code Setup

### Prerequisites

Install the required extension:
- [YAML Language Support](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) by Red Hat

### Configuration Options

#### Option 1: Project-Level Configuration (Recommended)

Create or update `.vscode/settings.json` in your project root:

```json
{
  "yaml.schemas": {
    "./runbook.schema.json": "apps/wct/runbooks/**/*.yaml",
    "./src/wct/schemas/json_schemas/runbook/1.0.0/runbook.json": "apps/wct/runbooks/**/*.yaml"
  },
  "yaml.format.enable": true,
  "yaml.validate": true,
  "files.associations": {
    "*.runbook.yaml": "yaml",
    "*.runbook.yml": "yaml"
  }
}
```

#### Option 2: Schema Comments in Files

Add this comment at the top of your runbook files:

```yaml
# yaml-language-server: $schema=./runbook.schema.json

name: "My Compliance Analysis"
description: "Personal data detection across filesystem and database"
# ... rest of your runbook
```

#### Option 3: User-Level Configuration

1. Open VS Code Settings (`Cmd/Ctrl + ,`)
2. Search for "yaml schemas"
3. Click "Edit in settings.json"
4. Add the schema mapping:

```json
{
  "yaml.schemas": {
    "/absolute/path/to/runbook.schema.json": "apps/wct/runbooks/**/*.yaml"
  }
}
```

### Verification

After configuration, you should see:
- ✅ **Autocomplete** when typing property names
- ✅ **Error highlighting** for invalid syntax
- ✅ **Documentation** on hover
- ✅ **Real-time validation** as you type

## PyCharm Setup

### Prerequisites

PyCharm Professional or Community Edition (2020.1 or later)

### Configuration Steps

1. **Open Settings**
   - Windows/Linux: `File` → `Settings`
   - macOS: `PyCharm` → `Preferences`

2. **Navigate to JSON Schema Mappings**
   - Go to `Languages & Frameworks` → `Schemas and DTDs` → `JSON Schema Mappings`

3. **Add New Mapping**
   - Click the `+` button to add a new mapping
   - Fill in the details:
     - **Name**: `WCT Runbook Schema`
     - **Schema file or URL**: Browse to your `runbook.schema.json` file
     - **Schema version**: `JSON Schema version 7`

4. **Set File Pattern**
   - In the file pattern section, add:
     - `runbooks/*.yaml`
     - `runbooks/*.yml`
     - `*.runbook.yaml`
     - `*.runbook.yml`

5. **Apply and Test**
   - Click `Apply` and `OK`
   - Open a runbook file to verify autocomplete works

## Other IDEs

### IntelliJ IDEA

Follow the same steps as PyCharm (both use the same underlying platform).

### Vim/Neovim

With [`coc.nvim`](https://github.com/neoclide/coc.nvim) and [`coc-yaml`](https://github.com/neoclide/coc-yaml):

```json
// In coc-settings.json
{
  "yaml.schemas": {
    "/absolute/path/to/runbook.schema.json": "runbooks/*.{yaml,yml}"
  }
}
```

### Emacs

With [`lsp-mode`](https://github.com/emacs-lsp/lsp-mode) and [`yaml-language-server`](https://github.com/redhat-developer/yaml-language-server):

```elisp
;; In your Emacs configuration
(add-to-list 'lsp-yaml-schemas
  '("/absolute/path/to/runbook.schema.json" . ["apps/wct/runbooks/*.yaml" "apps/wct/runbooks/*.yml"]))
```

## Schema Management

### Updating Schema

When WCT is updated, regenerate your schema to get the latest features:

```bash
# Regenerate schema with latest WCT version
wct generate-schema --output runbook.schema.json

# Or use bundled schema (always current)
cp libs/waivern-orchestration/src/waivern_orchestration/schemas/json_schemas/runbook/1.0.0/runbook.json runbook.schema.json
```

### Version Management

Schema files are versioned alongside WCT releases:

- **Current version**: `1.0.0`
- **Location**: `libs/waivern-orchestration/src/waivern_orchestration/schemas/json_schemas/runbook/1.0.0/runbook.json`
- **Auto-update**: Regenerate schema after WCT updates

### Remote Schema (Future)

For future versions, you may be able to reference remote schemas:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/waivern-compliance/waivern-compliance/main/src/wct/schemas/json_schemas/runbook/1.0.0/runbook.json

name: "My Runbook"
# ... rest of runbook
```

## Features & Benefits

### Real-Time Validation
- **Syntax errors** highlighted immediately
- **Required fields** clearly indicated
- **Type validation** for all properties
- **Pattern matching** for names and values

### Intelligent Autocomplete
- **Property suggestions** based on context
- **Value completion** for enums and known values
- **Nested object** structure suggestions
- **Array item** templates

### Documentation Integration
- **Field descriptions** on hover
- **Examples** and usage patterns
- **Type information** for all properties
- **Constraint details** (min/max lengths, patterns)

### Schema-Aware Navigation
- **Go to definition** for referenced components
- **Find references** across runbook files
- **Symbol navigation** for large runbooks
- **Outline views** with structure

## Troubleshooting

### Schema Not Loading
1. **Check file path**: Ensure schema file exists at specified location
2. **Verify JSON**: Validate schema file is valid JSON
3. **Restart IDE**: Reload configuration after changes
4. **Check extension**: Ensure YAML language server is installed

### Autocomplete Not Working
1. **File extension**: Ensure file has `.yaml` or `.yml` extension
2. **Schema association**: Verify file pattern matches in configuration
3. **YAML syntax**: Ensure file has valid YAML syntax
4. **Schema validation**: Check schema file is valid JSON Schema

### Performance Issues
1. **Large files**: Schema validation may slow down very large runbooks
2. **Multiple schemas**: Avoid conflicting schema mappings
3. **Cache clearing**: Clear IDE cache if experiencing issues

### Common Error Messages

**"Schema validation failed"**
- Check runbook syntax against schema requirements
- Verify all required fields are present
- Ensure property names match schema exactly

**"Cannot resolve schema"**
- Verify schema file path is correct
- Check file permissions
- Ensure schema file is valid JSON

## Examples

### Basic Runbook with Schema

```yaml
# yaml-language-server: $schema=./runbook.schema.json

name: "Sample Personal Data Analysis"
description: "Detect PII in customer database"

artifacts:
  customer_data:
    source:
      type: mysql
      properties:
        host: "${MYSQL_HOST}"
        user: "${MYSQL_USER}"
        password: "${MYSQL_PASSWORD}"
        database: customers
        tables: ["users", "profiles"]

  pii_findings:
    inputs: customer_data
    process:
      type: personal_data
      properties:
        pattern_matching:
          ruleset: "local/personal_data/1.0.0"
        llm_validation:
          enable_llm_validation: true
    output: true
```

### Multi-Step Analysis

```yaml
# yaml-language-server: $schema=./runbook.schema.json

name: "Comprehensive Compliance Audit"
description: "Full compliance analysis including PII detection and processing purposes"

artifacts:
  # Data sources
  app_database:
    source:
      type: mysql
      properties:
        host: "${DB_HOST}"
        database: application
        tables: ["users", "orders", "logs"]

  source_files:
    source:
      type: source_code
      properties:
        root_path: "/app/src"
        include_patterns: ["*.php", "*.ts"]
        language: php

  # Personal data detection
  db_personal_data:
    inputs: app_database
    process:
      type: personal_data
      properties:
        pattern_matching:
          ruleset: "local/personal_data/1.0.0"
    output: true

  code_personal_data:
    inputs: source_files
    process:
      type: personal_data
      properties:
        pattern_matching:
          ruleset: "local/personal_data/1.0.0"
    output: true

  # Processing purpose analysis
  processing_purposes:
    inputs: app_database
    process:
      type: processing_purpose
      properties:
        pattern_matching:
          ruleset: "local/processing_purpose/1.0.0"
    output: true
```

## Next Steps

1. **Configure your IDE** following the instructions above
2. **Generate a schema** for your project
3. **Create your first runbook** with IDE assistance
4. **Explore templates** in `src/wct/schemas/json_schemas/runbook/1.0.0/runbook.template.yaml`
5. **Share configurations** with your team for consistent development experience

## Support

For issues with IDE integration:
1. Check the troubleshooting section above
2. Verify your IDE and extension versions
3. Report issues at [GitHub Issues](https://github.com/waivern-compliance/waivern-compliance/issues)
4. Include your IDE version, schema file, and error messages
