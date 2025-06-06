# Waivern Rulesets Core

Core framework for building compliance rulesets in the Waivern Analyser ecosystem. This package provides the base classes and interfaces that all rulesets must implement.

## Overview

Rulesets are responsible for analyzing data collected by connectors and determining compliance with various standards, regulations, or best practices such as:
- Security compliance (OWASP, NIST, etc.)
- Code quality standards
- Industry regulations (GDPR, HIPAA, SOX, etc.)
- Internal policies and guidelines
- Best practices and conventions

## Architecture

The core ruleset framework defines three main components:

### 1. RulesetInputSchema
A dataclass that defines the input data for a ruleset:

```python
from dataclasses import dataclass
from waivern_rulesets_core import RulesetInputSchema

@dataclass(frozen=True, slots=True)
class MyRulesetInputSchema(RulesetInputSchema):
    source_data: dict
    configuration: dict = None
    severity_threshold: str = "medium"
```

### 2. RulesetOutputSchema
A dataclass that defines the output format of a ruleset analysis:

```python
from dataclasses import dataclass
from waivern_rulesets_core import RulesetOutputSchema

@dataclass(frozen=True, slots=True)
class MyRulesetOutputSchema(RulesetOutputSchema):
    compliance_score: float
    violations: list[dict]
    recommendations: list[str]
    summary: dict
```

### 3. Ruleset
The abstract base class that all rulesets must inherit from:

```python
from waivern_rulesets_core import Ruleset

class MyRuleset(Ruleset):
    def run(self, input: MyRulesetInputSchema) -> MyRulesetOutputSchema:
        # Implement your compliance analysis logic here
        violations = self._analyze_violations(input.source_data)
        score = self._calculate_compliance_score(violations)
        
        return MyRulesetOutputSchema(
            compliance_score=score,
            violations=violations,
            recommendations=self._generate_recommendations(violations),
            summary={"total_rules": 10, "passed": 8, "failed": 2}
        )
```

## Creating a Custom Ruleset

### Step 1: Define Input Schema

```python
from dataclasses import dataclass
from waivern_rulesets_core import RulesetInputSchema

@dataclass(frozen=True, slots=True)
class SecurityRulesetInputSchema(RulesetInputSchema):
    source_files: list[dict]
    dependencies: list[dict]
    configuration_files: list[dict]
    scan_level: str = "standard"  # basic, standard, comprehensive
    exclude_rules: list[str] = None
```

### Step 2: Define Output Schema

```python
from dataclasses import dataclass
from waivern_rulesets_core import RulesetOutputSchema

@dataclass(frozen=True, slots=True)
class SecurityRulesetOutputSchema(RulesetOutputSchema):
    overall_score: float
    security_level: str  # low, medium, high, critical
    vulnerabilities: list[dict]
    recommendations: list[dict]
    compliance_status: dict
    scan_metadata: dict
```

### Step 3: Implement the Ruleset

```python
from waivern_rulesets_core import Ruleset

class SecurityRuleset(Ruleset):
    def run(self, input: SecurityRulesetInputSchema) -> SecurityRulesetOutputSchema:
        vulnerabilities = []
        
        # Analyze source files for security issues
        for file_data in input.source_files:
            file_vulns = self._scan_file_security(file_data)
            vulnerabilities.extend(file_vulns)
        
        # Analyze dependencies for known vulnerabilities
        for dep in input.dependencies:
            dep_vulns = self._check_dependency_security(dep)
            vulnerabilities.extend(dep_vulns)
        
        # Calculate overall security score
        score = self._calculate_security_score(vulnerabilities)
        level = self._determine_security_level(score)
        
        return SecurityRulesetOutputSchema(
            overall_score=score,
            security_level=level,
            vulnerabilities=vulnerabilities,
            recommendations=self._generate_security_recommendations(vulnerabilities),
            compliance_status=self._check_compliance_frameworks(vulnerabilities),
            scan_metadata={
                "scan_time": "2024-01-01T12:00:00Z",
                "rules_applied": 25,
                "files_scanned": len(input.source_files)
            }
        )
    
    def _scan_file_security(self, file_data: dict) -> list[dict]:
        # Implement file-level security scanning
        return []
    
    def _check_dependency_security(self, dependency: dict) -> list[dict]:
        # Implement dependency vulnerability checking
        return []
    
    def _calculate_security_score(self, vulnerabilities: list[dict]) -> float:
        # Implement scoring algorithm
        return 85.0
    
    def _determine_security_level(self, score: float) -> str:
        if score >= 90:
            return "high"
        elif score >= 70:
            return "medium"
        else:
            return "low"
```

### Step 4: Create a Plugin

To make your ruleset discoverable by the Waivern Analyser framework:

```python
from waivern_analyser.plugin import Plugin

class SecurityRulesetPlugin(Plugin):
    @classmethod
    def get_name(cls) -> str:
        return "security-ruleset"
    
    @classmethod
    def get_rulesets(cls):
        return (SecurityRuleset(),)
```

### Step 5: Register the Plugin

Add to your package's `pyproject.toml`:

```toml
[project.entry-points."waivern-plugins"]
security-ruleset = "your_package:SecurityRulesetPlugin"
```

## Ruleset Design Patterns

### 1. Rule-Based Analysis

```python
class RuleBasedRuleset(Ruleset):
    def __init__(self):
        self.rules = [
            self._rule_no_hardcoded_secrets,
            self._rule_secure_dependencies,
            self._rule_proper_authentication,
        ]
    
    def run(self, input: RulesetInputSchema) -> RulesetOutputSchema:
        violations = []
        for rule in self.rules:
            rule_violations = rule(input)
            violations.extend(rule_violations)
        return self._format_output(violations)
    
    def _rule_no_hardcoded_secrets(self, input: RulesetInputSchema) -> list[dict]:
        # Implement specific rule logic
        return []
```

### 2. Scoring-Based Analysis

```python
class ScoringRuleset(Ruleset):
    def run(self, input: RulesetInputSchema) -> RulesetOutputSchema:
        scores = {
            "security": self._calculate_security_score(input),
            "maintainability": self._calculate_maintainability_score(input),
            "performance": self._calculate_performance_score(input),
        }
        
        overall_score = sum(scores.values()) / len(scores)
        return self._format_scored_output(scores, overall_score)
```

### 3. Threshold-Based Analysis

```python
class ThresholdRuleset(Ruleset):
    def __init__(self):
        self.thresholds = {
            "complexity": 10,
            "file_size": 1000,
            "test_coverage": 80,
        }
    
    def run(self, input: RulesetInputSchema) -> RulesetOutputSchema:
        violations = []
        for metric, threshold in self.thresholds.items():
            if self._check_threshold_violation(input, metric, threshold):
                violations.append({
                    "rule": f"{metric}_threshold",
                    "threshold": threshold,
                    "actual": self._get_metric_value(input, metric)
                })
        return self._format_threshold_output(violations)
```

## Common Output Structures

### Violation Format

```python
{
    "rule_id": "SEC001",
    "rule_name": "No Hardcoded Secrets",
    "severity": "high",
    "message": "Potential API key found in source code",
    "file": "src/config.py",
    "line": 15,
    "column": 20,
    "evidence": "api_key = 'sk-1234567890abcdef'",
    "remediation": "Move API key to environment variable"
}
```

### Recommendation Format

```python
{
    "id": "REC001",
    "title": "Implement Secret Management",
    "description": "Use a secret management system for API keys",
    "priority": "high",
    "effort": "medium",
    "resources": ["https://example.com/secret-management-guide"]
}
```

### Compliance Status Format

```python
{
    "framework": "OWASP Top 10",
    "version": "2021",
    "compliance_percentage": 85.0,
    "passed_controls": ["A01", "A02", "A04"],
    "failed_controls": ["A03", "A06"],
    "not_applicable": ["A10"]
}
```

## Testing Rulesets

Example test for a ruleset:

```python
from waivern_rulesets_core import RulesetInputSchema, RulesetOutputSchema

def test_security_ruleset():
    ruleset = SecurityRuleset()
    
    input_data = SecurityRulesetInputSchema(
        source_files=[
            {"path": "test.py", "content": "api_key = 'secret'"}
        ],
        dependencies=[],
        configuration_files=[]
    )
    
    result = ruleset.run(input_data)
    
    assert isinstance(result, SecurityRulesetOutputSchema)
    assert result.overall_score >= 0.0
    assert result.overall_score <= 100.0
    assert isinstance(result.vulnerabilities, list)
```

## Best Practices

### 1. Rule Organization
- Group related rules into logical categories
- Use consistent naming conventions for rules
- Provide clear rule descriptions and remediation guidance

### 2. Performance Optimization
- Cache expensive computations
- Use efficient algorithms for large datasets
- Implement early termination for critical violations

### 3. Configuration Management
- Make rules configurable through input schemas
- Support different severity levels and thresholds
- Allow rule inclusion/exclusion

### 4. Error Handling
- Gracefully handle malformed input data
- Provide meaningful error messages
- Continue analysis even if individual rules fail

### 5. Documentation
- Document each rule's purpose and logic
- Provide examples of violations and fixes
- Include references to relevant standards

## Integration with Connectors

Rulesets are designed to work with data from various connectors:

```python
# Example: Using source code connector data
def analyze_source_code(connector_output, ruleset_config):
    ruleset = SecurityRuleset()
    
    input_data = SecurityRulesetInputSchema(
        source_files=connector_output.files,
        dependencies=connector_output.dependencies,
        configuration_files=connector_output.config_files,
        scan_level=ruleset_config.get("scan_level", "standard")
    )
    
    return ruleset.run(input_data)
```

## Dependencies

This package has no external dependencies and only requires Python 3.9+.

## Contributing

When contributing to the rulesets core framework:

1. Maintain backward compatibility
2. Add comprehensive tests for any changes
3. Update documentation for new features
4. Follow the existing code style and patterns
5. Consider performance implications for large datasets