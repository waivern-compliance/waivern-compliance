# Configuration Guide

This guide explains how to configure the Waivern Compliance Tool and its dependencies.

## Quick Start (Development)

1. Copy the example configuration:
   ```bash
   cp apps/wct/.env.example apps/wct/.env
   ```

2. Edit `apps/wct/.env` with your credentials:
   ```bash
   # Add your Anthropic API key (required for LLM analysis)
   ANTHROPIC_API_KEY=your_actual_api_key_here

   # Add database credentials if using MySQL connector
   MYSQL_HOST=localhost
   MYSQL_USER=your_username
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=your_database
   ```

3. Run WCT:
   ```bash
   uv run wct run apps/wct/runbooks/samples/file_content_analysis.yaml
   ```

## Configuration Architecture

The Waivern framework uses a **layered configuration approach**, following [12-factor app principles](https://12factor.net/config):

### Configuration Layers (Highest to Lowest Priority)

1. **System environment variables** - Set by deployment environment (production)
2. **Application `.env` file** - Local development configuration (`apps/wct/.env`)
3. **Runbook properties** - Connector/analyser-specific config in YAML
4. **Code defaults** - Fallback values in source code

This means environment variables always override runbook properties, allowing flexible deployment without changing runbooks.

## Environment Variables

### LLM Configuration

**Required for AI-powered compliance analysis:**

- `ANTHROPIC_API_KEY` - Your Anthropic API key for Claude models
- `ANTHROPIC_MODEL` - Model name (optional, defaults to `claude-sonnet-4-5-20250929`)

**Optional providers (require additional dependencies):**

```bash
# OpenAI (install with: uv sync --group llm-openai)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o  # optional

# Google (install with: uv sync --group llm-google)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_MODEL=gemini-2.5-flash  # optional

# Provider selection (defaults to anthropic)
LLM_PROVIDER=anthropic  # Options: anthropic, openai, google
```

### Database Connectors

**MySQL Connector:**

These environment variables provide defaults for MySQL connections and can be overridden in runbooks:

- `MYSQL_HOST` - Database hostname (default: required in runbook)
- `MYSQL_PORT` - Database port (default: 3306)
- `MYSQL_USER` - Database username (default: required in runbook)
- `MYSQL_PASSWORD` - Database password (default: empty)
- `MYSQL_DATABASE` - Database name (default: empty)

**Usage pattern:**
```yaml
# Runbook connector configuration
connectors:
  - name: "production_db"
    type: "mysql"
    properties:
      host: "${MYSQL_HOST}"  # Uses env var
      user: "${MYSQL_USER}"  # Uses env var
      password: "${MYSQL_PASSWORD}"  # Uses env var
      database: "production"  # Explicit override
```

## Configuration by Package

### Applications (wct)

**Configuration location:** `apps/wct/.env`

Applications are responsible for loading configuration. WCT loads `.env` from its application directory on startup.

**What to configure:**
- API keys (LLM providers)
- Development database credentials
- Local development settings

### Framework Libraries (waivern-core, waivern-llm, component packages)

**Configuration location:** None (libraries have no `.env` files)

Framework libraries read configuration from the environment using `os.getenv()`. This allows:
- Multiple applications to use the same library differently
- Flexible deployment patterns
- Clear separation of concerns

**Component packages** (connectors, analysers) are discovered via entry points and configured through runbooks. Each package documents required environment variables in its README.

**Libraries document required environment variables in their READMEs.**

## Development vs Production

### Development Setup

Use `.env` file for convenience:

```bash
# apps/wct/.env (gitignored)
ANTHROPIC_API_KEY=sk-ant-...
MYSQL_HOST=localhost
MYSQL_USER=dev_user
MYSQL_PASSWORD=dev_password
```

**Advantages:**
- Easy local setup
- No system environment pollution
- Quick credential switching

### Production Deployment

Use system environment variables (no `.env` file):

**Docker:**
```dockerfile
FROM python:3.12
# ...
ENV ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
# Or use --env-file docker run option
```

**Kubernetes:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: wct-secrets
type: Opaque
data:
  anthropic-api-key: <base64-encoded-key>
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: wct
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: wct-secrets
              key: anthropic-api-key
```

**CI/CD:**
```yaml
# GitHub Actions example
- name: Run WCT
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    MYSQL_HOST: ${{ secrets.MYSQL_HOST }}
  run: |
    uv run wct run runbook.yaml
```

## Security Best Practices

### ✅ Do

- **Keep `.env` files out of version control** (already gitignored)
- **Use different API keys per environment** (dev/staging/prod)
- **Rotate credentials regularly**
- **Use secret management tools in production** (AWS Secrets Manager, HashiCorp Vault, etc.)
- **Limit API key permissions** to minimum required
- **Document required environment variables** in runbooks and README

### ❌ Don't

- **Never commit `.env` files** to git
- **Never put secrets in runbook files** committed to version control
- **Never share API keys** between developers (use separate keys)
- **Never log or print** environment variables containing secrets
- **Never use production credentials** in development

## Runbook Configuration

Runbooks can specify connector and analyser configuration:

```yaml
name: "Database Analysis"
connectors:
  - name: "prod_db"
    type: "mysql"
    properties:
      # Can use environment variables
      host: "prod.mysql.example.com"
      user: "readonly_user"
      password: "${MYSQL_PASSWORD}"  # From environment
      database: "customer_data"
      max_rows_per_table: 100

analysers:
  - name: "personal_data"
    type: "personal_data"
    properties:
      enable_llm_validation: true  # Uses ANTHROPIC_API_KEY from env
```

**Configuration precedence:**
1. Environment variable (if connector checks env)
2. Runbook property value
3. Connector default value

## Troubleshooting

### "API key is required" Error

**Problem:** LLM service can't find API key

**Solutions:**
1. Check `.env` file exists: `ls apps/wct/.env`
2. Verify API key is set: `ANTHROPIC_API_KEY=sk-ant-...`
3. Check file is in correct location: `apps/wct/.env` (not workspace root)
4. Verify no typos in variable name

### "Connection failed" for MySQL

**Problem:** Can't connect to database

**Solutions:**
1. Verify database is running
2. Check credentials in `.env` or runbook
3. Verify network access (firewall, VPN, etc.)
4. Check `MYSQL_HOST` and `MYSQL_PORT` are correct
5. Test connection manually: `mysql -h $MYSQL_HOST -u $MYSQL_USER -p`

### Environment Variables Not Loading

**Problem:** WCT doesn't see environment variables

**Solutions:**
1. Verify `.env` file location: `apps/wct/.env`
2. Check file format (no quotes around values usually)
3. Restart terminal/shell after setting system env vars
4. Check for typos in variable names
5. Use `--verbose` flag to see detailed logging

## Package-Specific Configuration

### waivern-llm

**Required environment variables:**
- `ANTHROPIC_API_KEY` (default provider)

**Optional environment variables:**
- `LLM_PROVIDER` - Select provider (anthropic, openai, google)
- `ANTHROPIC_MODEL` - Override default model
- `OPENAI_API_KEY` - For OpenAI provider
- `OPENAI_MODEL` - Override default model
- `GOOGLE_API_KEY` - For Google provider
- `GOOGLE_MODEL` - Override default model

**See:** `libs/waivern-llm/README.md` for detailed configuration

### waivern-core

No configuration required (base abstractions only).

### Component Packages (Connectors and Analysers)

All components are now standalone packages discovered via Python entry points:
- **Connectors:** mysql, sqlite, filesystem, source-code
- **Analysers:** personal-data, data-subject, processing-purpose, data-export

Each component package:
- Registers via `pyproject.toml` entry points
- Documents configuration in its README
- Configurable through runbook properties

See individual package READMEs in `libs/waivern-*/` for component-specific configuration.

## Migration Notes

**Completed Migrations:**
- **Phase 2:** `.env` moved from workspace root to `apps/wct/.env` for app-specific configuration
- **Phase 3:** All components extracted to standalone packages with entry point discovery
- **Phase 4-5:** waivern-community removed, true plugin architecture established

## Additional Resources

- **Runbooks:** See `apps/wct/runbooks/README.md` for runbook configuration
- **LLM Providers:** See `libs/waivern-llm/README.md` for provider setup
- **Component Packages:** See individual package READMEs in `libs/waivern-*/`
- **12-Factor App:** https://12factor.net/config
