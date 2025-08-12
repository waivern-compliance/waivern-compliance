# WCT Configuration

This directory contains configuration files for the Waivern Compliance Tool.

## Logging Configuration

WCT uses Python's standard `logging.config.dictConfig()` with YAML configuration files:

- **`logging.yaml`** - Default logging configuration for production
- **`logging-dev.yaml`** - Development configuration with debug logging and Rich formatting
- **`logging-test.yaml`** - Minimal logging for test environments

### Environment Selection

The logging system automatically selects configuration based on:

1. **`WCT_ENV` environment variable**: Set to `dev`, `test`, or `prod`
2. **Explicit config**: Pass config path to `setup_logging()`
3. **Default fallback**: Uses `logging.yaml` if no environment specified

### Configuration Structure

Each logging config follows Python's standard logging configuration format:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard

loggers:
  wct:
    level: INFO
    handlers: [console]
    propagate: false

root:
  level: WARNING
  handlers: [console]
```

### Adding New Configurations

To add environment-specific logging:

1. Create `config/logging-{environment}.yaml`
2. Set `WCT_ENV={environment}` in your environment
3. The logging system will automatically use your configuration

### Rich Console Output

Development and default configurations use Rich formatting for enhanced console output with:
- Syntax highlighting
- Progress bars
- Better tracebacks
- Timestamps and paths
