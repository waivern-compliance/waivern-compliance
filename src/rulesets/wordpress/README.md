# Waivern WordPress Ruleset

A specialized compliance ruleset for analyzing WordPress applications, themes, and plugins in the Waivern Analyser ecosystem. This ruleset implements WordPress-specific security, performance, and best practice rules.

## Overview

The WordPress Ruleset provides comprehensive analysis for WordPress-based applications, covering:

- **Security compliance**: WordPress security best practices and vulnerability detection
- **Performance optimization**: Code efficiency and WordPress performance guidelines
- **Coding standards**: WordPress Coding Standards (WPCS) compliance
- **Plugin/Theme guidelines**: WordPress.org submission requirements
- **Accessibility**: WCAG compliance for WordPress themes
- **SEO best practices**: WordPress SEO optimization rules

## Features

### Security Analysis
- SQL injection vulnerability detection
- Cross-site scripting (XSS) prevention
- CSRF protection validation
- File upload security checks
- Authentication and authorization validation
- WordPress nonce verification
- Capability and permission checks

### Performance Analysis
- Database query optimization
- Caching implementation checks
- Asset optimization validation
- WordPress hook usage efficiency
- Memory usage analysis

### Code Quality
- WordPress Coding Standards compliance
- Deprecated function usage detection
- Proper sanitization and validation
- Internationalization (i18n) compliance
- Documentation standards

### WordPress-Specific Rules
- Theme and plugin structure validation
- WordPress API usage compliance
- Hook and filter implementation
- Custom post type and field validation
- WordPress multisite compatibility

## Usage

### Basic Usage

```python
from waivern_rulesets_wordpress import (
    WordpressRuleset,
    WordpressRulesetInputSchema
)

# Create ruleset instance
ruleset = WordpressRuleset()

# Define input parameters
input_data = WordpressRulesetInputSchema(
    # Add input parameters here when implemented
)

# Run the analysis
result = ruleset.run(input_data)
```

### Input Schema

The `WordpressRulesetInputSchema` defines the parameters for WordPress analysis:

```python
@dataclass(frozen=True, slots=True)
class WordpressRulesetInputSchema(RulesetInputSchema):
    # TODO: Define input parameters such as:
    # wordpress_files: list[dict]
    # theme_files: list[dict] = None
    # plugin_files: list[dict] = None
    # config_files: list[dict] = None
    # database_schema: dict = None
    # wordpress_version: str = None
    # scan_level: str = "standard"  # basic, standard, comprehensive
    # include_performance: bool = True
    # include_security: bool = True
    # include_accessibility: bool = False
    pass
```

### Output Schema

The `WordpressRulesetOutputSchema` contains the analysis results:

```python
@dataclass(frozen=True, slots=True)
class WordpressRulesetOutputSchema(RulesetOutputSchema):
    # TODO: Define output structure such as:
    # overall_score: float
    # security_score: float
    # performance_score: float
    # code_quality_score: float
    # violations: list[dict]
    # recommendations: list[dict]
    # wordpress_specific_issues: list[dict]
    # compliance_status: dict
    pass
```

## WordPress-Specific Rules

### Security Rules

#### WP-SEC-001: SQL Injection Prevention
```python
# Detects unsafe database queries
# Bad:
$wpdb->query("SELECT * FROM table WHERE id = " . $_GET['id']);

# Good:
$wpdb->prepare("SELECT * FROM table WHERE id = %d", $_GET['id']);
```

#### WP-SEC-002: XSS Prevention
```python
# Detects unescaped output
# Bad:
echo $_POST['user_input'];

# Good:
echo esc_html($_POST['user_input']);
```

#### WP-SEC-003: CSRF Protection
```python
# Validates nonce usage in forms
# Bad:
if ($_POST['action'] == 'update') { /* process */ }

# Good:
if (wp_verify_nonce($_POST['nonce'], 'update_action')) { /* process */ }
```

### Performance Rules

#### WP-PERF-001: Database Query Optimization
```python
# Detects inefficient queries
# Bad:
for ($i = 0; $i < count($posts); $i++) {
    $meta = get_post_meta($posts[$i]->ID, 'key', true);
}

# Good:
$meta_values = get_post_meta($post_ids, 'key');
```

#### WP-PERF-002: Proper Hook Usage
```python
# Validates hook placement and efficiency
# Bad:
add_action('wp_head', 'expensive_function');

# Good:
add_action('wp_enqueue_scripts', 'enqueue_optimized_scripts');
```

### Code Quality Rules

#### WP-QUAL-001: Deprecated Function Usage
```python
# Detects usage of deprecated WordPress functions
# Bad:
wp_get_http('http://example.com');

# Good:
wp_remote_get('http://example.com');
```

#### WP-QUAL-002: Internationalization
```python
# Validates proper i18n implementation
# Bad:
echo 'Hello World';

# Good:
echo __('Hello World', 'textdomain');
```

## Configuration Examples

### Security-Focused Analysis

```python
input_data = WordpressRulesetInputSchema(
    wordpress_files=source_files,
    scan_level="comprehensive",
    include_security=True,
    include_performance=False,
    include_accessibility=False
)
```

### Theme Development Analysis

```python
input_data = WordpressRulesetInputSchema(
    theme_files=theme_source_files,
    scan_level="comprehensive",
    include_accessibility=True,
    include_performance=True,
    wordpress_version="6.0"
)
```

### Plugin Submission Analysis

```python
input_data = WordpressRulesetInputSchema(
    plugin_files=plugin_source_files,
    scan_level="comprehensive",
    include_security=True,
    include_performance=True,
    check_wordpress_org_guidelines=True
)
```

## Output Structure

### WordPress-Specific Violation

```python
{
    "rule_id": "WP-SEC-001",
    "rule_name": "SQL Injection Prevention",
    "category": "security",
    "severity": "high",
    "message": "Unsafe database query detected",
    "file": "includes/admin.php",
    "line": 45,
    "function": "get_user_data",
    "evidence": "$wpdb->query(\"SELECT * FROM users WHERE id = \" . $_GET['id'])",
    "wordpress_context": {
        "hook": "admin_init",
        "capability_required": "manage_options",
        "affected_versions": "all"
    },
    "remediation": {
        "description": "Use $wpdb->prepare() for parameterized queries",
        "example": "$wpdb->prepare(\"SELECT * FROM users WHERE id = %d\", $_GET['id'])",
        "references": [
            "https://developer.wordpress.org/reference/classes/wpdb/prepare/"
        ]
    }
}
```

### Performance Analysis

```python
{
    "category": "performance",
    "issues": [
        {
            "type": "database_queries",
            "count": 45,
            "threshold": 20,
            "impact": "high",
            "recommendations": [
                "Implement query caching",
                "Use WP_Query with proper parameters",
                "Consider using transients for expensive operations"
            ]
        }
    ],
    "scores": {
        "query_efficiency": 65.0,
        "caching_implementation": 80.0,
        "asset_optimization": 90.0
    }
}
```

### Compliance Status

```python
{
    "wordpress_coding_standards": {
        "compliance_percentage": 85.0,
        "passed_rules": ["spacing", "naming", "documentation"],
        "failed_rules": ["indentation", "line_length"],
        "score": 85.0
    },
    "wordpress_org_guidelines": {
        "plugin_ready": True,
        "theme_ready": False,
        "issues": ["Missing sanitization in theme options"]
    },
    "accessibility": {
        "wcag_level": "AA",
        "compliance_percentage": 92.0,
        "issues": ["Missing alt text for images"]
    }
}
```

## Integration with WordPress Ecosystem

### Plugin Development Workflow

```python
def analyze_wordpress_plugin(plugin_path):
    # Use source code connector to gather plugin files
    connector = SourceCodeConnector()
    source_data = connector.run(SourceCodeConnectorInputSchema(
        repository_path=plugin_path,
        include_patterns=["*.php", "*.js", "*.css"],
        exclude_patterns=["*/vendor/*", "*/node_modules/*"]
    ))
    
    # Analyze with WordPress ruleset
    ruleset = WordpressRuleset()
    analysis = ruleset.run(WordpressRulesetInputSchema(
        plugin_files=source_data.files,
        scan_level="comprehensive",
        check_wordpress_org_guidelines=True
    ))
    
    return analysis
```

### Theme Development Workflow

```python
def analyze_wordpress_theme(theme_path):
    # Gather theme files and assets
    source_data = gather_theme_files(theme_path)
    
    # Comprehensive theme analysis
    analysis = WordpressRuleset().run(WordpressRulesetInputSchema(
        theme_files=source_data.files,
        include_accessibility=True,
        include_performance=True,
        wordpress_version="latest"
    ))
    
    return analysis
```

## WordPress Plugin Integration

This ruleset can be integrated as a WordPress plugin for real-time analysis:

```php
<?php
/**
 * Plugin Name: Waivern WordPress Analyzer
 * Description: Real-time WordPress compliance analysis
 */

class WaivernWordPressAnalyzer {
    public function __construct() {
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('wp_ajax_run_analysis', [$this, 'run_analysis']);
    }
    
    public function run_analysis() {
        // Call Python analysis via subprocess or API
        $result = $this->call_waivern_analyzer();
        wp_send_json($result);
    }
}
```

## Development Status

⚠️ **Note**: This ruleset is currently in early development. The implementation contains placeholder code and TODOs. The actual WordPress-specific rules are being developed.

### Current Status
- ✅ Basic structure and plugin registration implemented
- ⚠️ Input/output schemas need implementation
- ⚠️ WordPress-specific rules need implementation
- ⚠️ Security analysis logic needs implementation
- ⚠️ Performance analysis logic needs implementation
- ⚠️ Code quality checks need implementation

### Planned Features
- Complete WordPress security rule set
- Performance optimization analysis
- WordPress Coding Standards validation
- Accessibility compliance checking
- WordPress.org submission readiness
- Integration with WordPress hooks and filters
- Real-time analysis WordPress plugin

## Contributing

To contribute to the WordPress Ruleset:

1. **Implement WordPress rules**: Add specific security, performance, and quality rules
2. **Add WordPress context**: Implement WordPress-specific analysis logic
3. **Extend compatibility**: Support different WordPress versions and configurations
4. **Improve accuracy**: Reduce false positives and enhance detection
5. **Add documentation**: Document WordPress-specific rules and remediation

### Development Setup

```bash
# Navigate to the WordPress ruleset directory
cd src/rulesets/wordpress

# Install in development mode
uv pip install -e .

# Run tests
uv run pytest tests/

# Test with WordPress codebase
python -c "
from waivern_rulesets_wordpress import WordpressRuleset
ruleset = WordpressRuleset()
# Add test code here
"
```

## WordPress Resources

- [WordPress Developer Documentation](https://developer.wordpress.org/)
- [WordPress Coding Standards](https://developer.wordpress.org/coding-standards/)
- [WordPress Security Guidelines](https://developer.wordpress.org/plugins/security/)
- [WordPress Performance Best Practices](https://developer.wordpress.org/advanced-administration/performance/)
- [WordPress Accessibility Guidelines](https://developer.wordpress.org/themes/accessibility/)

## Dependencies

- `waivern-rulesets-core`: Base ruleset framework
- `waivern-analyser`: Plugin system integration
- Additional WordPress-specific dependencies will be added as features are implemented

## License

This package is part of the Waivern Analyser project and follows the same license terms.