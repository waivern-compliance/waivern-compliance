# WCT Development Roadmap

This document outlines the development status and planned roadmap for the Waivern Compliance Tool (WCT). It serves as a guide for contributors and users to understand the current state of the project and upcoming features.

## Feature Status Overview

| Feature                    | PoC | WCT | Refactor* | Description                                                                                  |
| -------------------------- | --- | --- | -------- | -------------------------------------------------------------------------------------------- |
| Rulesets                   | N/A | ✅   | ✅        | Pattern rules for static analysis                                                            |
| Input/Output Schema        | N/A | ✅   | ✅        | Strongly typed schemas with unified interface and runtime validation                         |
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
- **Schema-driven design**: Strongly typed schema system with unified interface, dependency injection, and runtime validation
- **Modular connector/analyser architecture**: Hot-swappable components with clear interfaces
- **Rulesets system**: Comprehensive rule definitions for personal data and processing purposes
- **Message-based validation**: Automatic input/output validation using JSON schemas

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

## Current Phase: Document Generation & Advanced Features (v0.1.0)

### ✅ Priority 1: Schema System Enhancement (COMPLETED)

The schema refactoring phase focused on optimising the current unified schema system:

**Completed Goals:**
- ✅ Streamlined schema definitions and validation processes with strongly typed Schema base class
- ✅ Improved performance for large-scale data processing through schema caching and dependency injection
- ✅ Enhanced error reporting and debugging capabilities with detailed validation messages
- ✅ Standardised schema contracts across all components (connectors, analysers, executor)

**Completed:** December 2024 - Fully implemented strongly typed schema system with unified interface

### 🎯 Priority 2: Connector & Analyser Refactoring

Enhanced connector and analyser implementations leveraging the new typed schema system.

**Testing & Quality**
- Comprehensive integration testing for all connectors and analysers

**Timeline:** TBC

### 🎯 Priority 3: Advanced Analysis Features

**Data Export Analysis**
- Subject access request compliance verification
- Data portability assessment
- Export format validation and standardisation

**Timeline:** TBC

### 🎯 Priority 4: Document Generation Suite

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

**Phase 1: Schema Optimisation**
- Refactor existing analysers to use optimised schema contracts
- Implement lazy loading for large datasets
- Add schema versioning and migration capabilities
- Enhance performance monitoring and profiling

**Phase 2: Document Generation Framework**
- Design template engine for compliance documents
- Create document schema definitions
- Implement PDF/Word export capabilities
- Add multi-language support infrastructure

**Phase 3: Advanced Analytics**
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
- Connector development for new data sources (databases, APIs, cloud services)
- Analyser implementation for additional compliance frameworks
- Performance optimisation and schema refactoring
- Test coverage improvement and bug fixes

**For Compliance Experts**
- Ruleset definitions for specific industries or regulations
- Document template creation and localisation
- Compliance framework mapping and validation
- Legal requirement specification and testing

**For Documentation**
- Tutorial and guide creation
- Use case documentation and examples
- API reference and technical documentation
- Translation and localisation support

## Getting Involved

### Current Focus Areas

1. **Schema System Refactoring**: Help optimise the current schema system for better performance and usability
2. **Document Generation**: Contribute to the implementation of automated compliance document generation
3. **Testing & Quality**: Improve test coverage and add integration tests for new features
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
