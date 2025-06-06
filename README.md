# Waivern Analyser

Waivern Analyser is a tool designed to [TODO: Add a brief, high-level description of what the analyser does. e.g., 'analyze code for vulnerabilities', 'scan websites for broken links', etc.].

## Architecture

The analyser features a plugin-based architecture, allowing for easy extension and customization. Key components include:

*   **Connectors**: These plugins are responsible for fetching data from various sources (e.g., websites, source code repositories, databases).
*   **Rulesets**: These plugins define the specific rules and logic used to analyse the data provided by the connectors.

The core application loads these plugins at runtime to perform its analysis tasks.
