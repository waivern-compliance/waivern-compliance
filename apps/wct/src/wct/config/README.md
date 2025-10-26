# WCT Configuration

This directory contains configuration files for the Waivern Compliance Tool.

## Logging Configuration

WCT uses Python's standard `logging.config.dictConfig()` with a single YAML configuration file for console-only logging.

### Configuration File

- **`logging.yaml`** - Console-only logging configuration using Rich formatting

### Log Level Control

Control logging verbosity using CLI flags:

```bash
# Default (INFO level)
wct run runbook.yaml

# Debug output (DEBUG level)
wct run runbook.yaml -v

# Custom log level
wct run runbook.yaml --log-level WARNING
```

### Configuration Structure

The logging config follows Python's standard logging configuration format:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

handlers:
  rich_console:
    class: rich.logging.RichHandler
    level: INFO
    formatter: standard
    markup: true
    rich_tracebacks: true

loggers:
  wct:
    level: INFO
    handlers: [rich_console]
    propagate: false

root:
  level: WARNING
  handlers: [rich_console]
```

### Cloud-Native Logging

WCT follows cloud-native principles:
- Logs to **stdout/stderr** (not files)
- Execution environment handles persistence (CI captures output, AWS CloudWatch auto-collects, etc.)
- Users can redirect if needed: `wct run ... 2>&1 | tee output.log`

### Rich Console Output

The configuration uses Rich formatting for enhanced console output with:
- Syntax highlighting
- Auto-detection of terminal vs pipe (plain text when piped)
- Pretty tracebacks with context
- Formatted timestamps
