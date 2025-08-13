# WCT Development Roadmap

This document outlines the development status and planned roadmap for the Waivern Compliance Tool (WCT). It serves as a guide for contributors and users to understand the current state of the project and upcoming features.

## Feature Status Overview

| Feature                    | PoC | WCT | Refactor* | Description                                                                                  |
| -------------------------- | --- | --- | -------- | -------------------------------------------------------------------------------------------- |
| Rulesets                   | N/A | ✅   | ✅        | Pattern rules for static analysis                                                            |
| Input/Output Schema        | N/A | ✅   | ✅        | JSON Schema-based validation system with data flow schemas                |
| Runbook                    | N/A | ✅   | ✅        | JSON Schema-based runbook configuration spec with validation utility                |
| MySQL Connector            | ✅   | ✅   | ✅        | Database connectivity and data extraction with enhanced error handling and comprehensive tests |
| Source Code Connector      | ✅   | ✅   | ✅        | PHP source code analysis with compliance-focused extraction and comprehensive test coverage  |
| Personal Data (MySQL)      | ✅   | ✅   | ⏳        | Personal data collection analysis in MySQL databases                                         |
| Personal Data (PHP)        | ✅   | ✅   | ⏳        | Personal data collection in PHP source code                                                  |
| Processing Purpose (MySQL) | ✅   | ✅   | ⏳        | GDPR processing purpose analysis for MySQL                                                   |
| Processing Purpose (PHP)   | ✅   | ✅   | ⏳        | GDPR processing purpose analysis for PHP code                                                |
| Log Analysis               | ✅   | ✅   | ⏳        | Analysis of application and server logs for personal data collection and processing purposes |
| Security Measures          | ✅   | ✅   | ⏳        | Security measures analysis                                                                   |
| Generate SBODPA            | ✅   | ⏳   | ⏳        | Draft Service-Based Online Data Processing Agreement generation                              |
| Generate Privacy Policy    | ✅   | ⏳   | ⏳        | Automated Privacy Policy draft generation                                                    |
| Generate RoPA              | ✅   | ⏳   | ⏳        | Draft Record of Processing Activities generation                                             |
| Data Export Analysis       | ✅   | ⏳   | ⏳        | Analysis of data export capabilities and compliance                                          |

_*Test coverage, code quality review to produce production-ready code_

### Legend

- ✅ **Complete**: Feature is implemented
- ⏳ **In Progress/Planned**: Feature is being worked on
- ☐ **Not Started**: Feature has not been started yet
- N/A: Not applicable (feature was implemented directly in WCT)

## Current State (v0.0.1)

We are in the process of transforming from proof-of-concept to a production-ready framework with the following:

### Features Implemented & Planned

**Core Architecture**
- **JSON Schema-based validation**: Comprehensive validation system with data flow schemas (runtime) and configuration schemas (setup)
- **Declarative configuration**: YAML runbooks with structural validation and cross-reference checking
- **Modular connector/analyser architecture**: Hot-swappable components with clear schema contracts
- **Rulesets system**: Comprehensive rule definitions for personal data and processing purposes
- **Message-based validation**: Automatic input/output validation with detailed error reporting

**Data Analysis Capabilities**
- **Personal data detection**: Multi-source personal data identification (MySQL, PHP, files)
- **Processing purpose analysis**: GDPR-compliant processing purpose detection
- **Log analysis**: Application and server log compliance analysis
- **Security measures**: Security control identification and assessment

**Technical Infrastructure**
- **Optional dependency groups**: Modular installation with connector-specific dependencies
- **Comprehensive testing**: Full test coverage with type checking and linting
- **CLI interface**: User-friendly command-line tools with detailed logging
- **Sample runbooks**: Ready-to-use examples for common compliance scenarios

## Current Phase: Document Generation & Advanced Features (v0.0.1)

### ✅ Priority 1: Schema-Based Validation System (COMPLETED)

Complete migration from manual validation to a comprehensive JSON Schema-based validation architecture:

**Completed Goals:**
- ✅ **JSON Schema validation**: Replace ~150+ lines of scattered manual validation with declarative schema definitions
- ✅ **Two-tier schema architecture**: Separate data flow schemas (runtime) from configuration schemas (setup validation)
- ✅ **RunbookSchema implementation**: YAML runbook validation with structural requirements and cross-reference checking
- ✅ **Strongly typed interfaces**: RunbookSummary dataclass and mandatory schema specifications
- ✅ **Enhanced error reporting**: Field path reporting with clear validation failure details
- ✅ **Comprehensive testing**: 119 total tests with 23 new tests for schema validation and runbook implementation

**Completed:** January 2025 - Full JSON Schema-based validation system with declarative configuration validation

### ✅ Priority 2: Connector Refactoring (COMPLETED)

Enhanced connector implementations leveraging the JSON Schema-based validation system:

**Completed Goals:**
- ✅ **FilesystemConnector refactoring**: Extracted constants, improved encapsulation, comprehensive test coverage
- ✅ **MySQLConnector refactoring**: Enhanced error handling, proper validation consolidation, full test suite
- ✅ **SourceCodeConnector refactoring**: Compliance-focused data extraction, simplified extractors, comprehensive testing
- ✅ **Comprehensive test coverage**: 35 extractor tests following industrial best practices with public API focus
- ✅ **Code quality improvements**: Fixed all linting issues, improved type safety, eliminated dead code
- ✅ **Performance optimisation**: Streamlined connector architecture with ~98 lines of code reduction

**Completed:** August 2025 - All three core connectors refactored with production-ready quality

### 🎯 Priority 3: Analyser Refactoring

Enhanced analyser implementations leveraging the JSON Schema-based validation system:

**Goals:**
- Comprehensive integration testing for all analysers with schema validation
- Analyser improvements with Message-based validation
- Performance optimisation for large-scale data processing

**Timeline:** TBC

### 🎯 Priority 4: End-to-End Testing & CI/CD Infrastructure

**End-to-End Testing Framework**
- Comprehensive testing framework with realistic datasets for analyser output validation
- LLM validation testing with standardised compliance scenarios
- Performance benchmarking with large-scale data processing
- Integration testing across multiple connector and analyser combinations

**CI/CD Pipeline Enhancement**
- Migration from GitHub Actions to CircleCI for enhanced testing capabilities
- Automated testing pipeline for end-to-end validation workflows
- Performance regression testing and reporting
- Automated compliance validation against known datasets

**Community Collaboration Needed:**
These initiatives require architectural decisions and community input on testing strategies, dataset creation, and CI/CD infrastructure choices. Contributors interested in testing infrastructure and DevOps are encouraged to start discussions.

**Timeline:** Community-driven - requires discussion and planning

### 🎯 Priority 5: Advanced Analysis Features

**Data Export Analysis**
- Subject access request compliance verification
- Data portability assessment
- Export format validation and standardisation

**Timeline:** TBC

### 🎯 Priority 6: Document Generation Suite

Implementation of automated compliance document generation:

**SBODPA Generation**
- Template-driven draft Service-Based Online Data Processing Agreement creation
- Automated data flow mapping and compliance requirement identification
- Integration with existing personal data and processing purpose analysers

**Privacy Policy Generation**
- Dynamic draft privacy policy creation based on detected processing activities
- Multi-jurisdiction support
- Customisable templates and legal language adaptation

**RoPA Generation**
- Automated draft Record of Processing Activities documentation
- Cross-reference with detected personal data and processing purposes

**Timeline:** TBC

## Technical Roadmap

### Architecture Evolution

**Phase 1: Document Generation Framework**
- Design template engine for compliance documents
- Create document schema definitions
- Implement PDF/Word export capabilities
- Add multi-language support infrastructure

**Phase 2: Advanced Analytics**
- Implement data lineage tracking
- Add compliance scoring and risk assessment

### Quality Assurance

**Testing Strategy**
- Maintain 95%+ test coverage across all components
- Implement integration testing for document generation
- Add performance benchmarking for large datasets
- Create compliance validation test suites

**Security & Compliance**
- Regular security audits and vulnerability assessments
- GDPR compliance verification for WCT itself
- Data minimisation and privacy-by-design implementation
- Secure credential management and storage

## Community & Contribution

### Open Source Transition

**Phase 1: Core Release** (Current)
- Open source core WCT framework
- Community contribution guidelines
- Documentation and tutorial creation
- Discord community establishment

**Phase 2: Ecosystem Growth**
- Third-party connector development support
- Plugin architecture for custom analysers
- Community-contributed rulesets
- Integration with popular compliance tools

### Contribution Opportunities

**For Developers**
- **Connector Development**: MongoDB, PostgreSQL, Redis, Elasticsearch connectors for diverse data sources
- **Source Code Analysis**: JavaScript, Python, Java, Go language support for SourceCodeConnector
- **Testing Infrastructure**: End-to-end testing frameworks, CI/CD pipeline improvements
- **Performance Optimisation**: Schema refactoring, large-scale data processing improvements
- **Core Features**: Test coverage enhancement, bug fixes, code quality improvements

**For DevOps & Infrastructure**
- **CI/CD Enhancement**: CircleCI pipeline design and implementation
- **Testing Frameworks**: End-to-end testing infrastructure with realistic datasets
- **Performance Testing**: Benchmarking and regression testing systems
- **Deployment**: Docker improvements, cloud deployment automation

**For Compliance Experts**
- **Ruleset Development**: Industry-specific compliance patterns and validation rules
- **Document Generation**: Template creation for GDPR, CCPA, and other frameworks
- **Compliance Validation**: Legal requirement specification and testing scenarios
- **Framework Mapping**: Cross-jurisdiction compliance requirement analysis

**For Documentation & Community**
- **Tutorial Creation**: Getting started guides, use case documentation
- **Best Practices**: Contributor guidelines, coding standards documentation
- **Integration Examples**: Sample runbooks for different technology stacks
- **Translation**: Localisation support for international compliance frameworks

## Getting Involved

### Current Focus Areas

1. **Connector & Analyser Enhancement**: Leverage the new JSON Schema-based validation system for improved performance and usability
2. **Document Generation**: Contribute to the implementation of automated compliance document generation
3. **Testing & Quality**: Expand integration tests for schema validation and add performance benchmarks
4. **Community Building**: Help establish best practices and contribution guidelines

### How to Contribute

1. **Join our Discord**: [Discord Server](https://discord.gg/hPkvTQdS) for real-time discussion
2. **Check GitHub Issues**: Look for "good first issue" and "help wanted" labels
3. **Review Documentation**: Help improve and expand our documentation
4. **Test Early Features**: Provide feedback on pre-release features and improvements

### Contact & Support

- **GitHub Issues**: Bug reports and feature requests
- **Discord Community**: Real-time support and discussion
- **Email**: Contact Waivern for commercial licensing and enterprise support

---

*This roadmap is updated regularly based on community feedback and development progress. Last updated: August 2025*
