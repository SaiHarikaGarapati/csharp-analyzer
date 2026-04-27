"""
Rules Engine Module

This module defines and executes analysis rules.

Key Concepts:
1. Rules: Declarative patterns that detect code issues
2. Rule Types:
   - Metric-based: Triggered when metrics exceed thresholds
   - Pattern-based: Triggered when specific code patterns found
   - Semantic: Triggered by code behavior analysis

3. Rule Configuration: YAML files define rules, engine executes them

4. Findings: Issues detected by rules (with severity, message, location)

The engine:
- Loads rules from YAML files
- Applies rules to code
- Returns findings (issues) sorted by severity
- Can be extended with custom rule types
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import yaml
from pathlib import Path

from .metrics import FileMetrics, MetricsCalculator, MethodMetrics, ClassMetrics


class Severity(Enum):
    """Issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


class RuleType(Enum):
    """Types of rules"""
    METRIC = "metric"  # Rule based on metrics thresholds
    PATTERN = "pattern"  # Rule based on code patterns
    SEMANTIC = "semantic"  # Rule based on code semantics


@dataclass
class Finding:
    """
    Represents a single code issue found
    
    Attributes:
        rule_id: Unique identifier for the rule
        severity: Severity level of the issue
        message: Human-readable description
        location: File location of the issue
        code_snippet: The problematic code (optional)
        suggestions: List of improvement suggestions
    """
    rule_id: str
    severity: Severity
    message: str
    file: str
    line: int
    column: int = 0
    code_snippet: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    """
    Configuration for a single rule
    
    Attributes:
        id: Unique rule identifier
        name: Human-readable rule name
        type: Rule type (metric, pattern, semantic)
        severity: Issue severity
        description: What the rule detects
        enabled: Whether rule is active
        config: Rule-specific configuration
    """
    id: str
    name: str
    type: RuleType
    severity: Severity
    description: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class RulesEngine:
    """
    Executes rules against code metrics and findings
    """
    
    def __init__(self, rules_dir: Optional[str] = None):
        """
        Initialize rules engine
        
        Args:
            rules_dir: Directory containing YAML rule definitions
        """
        self.rules: List[Rule] = []
        self.custom_rules: Dict[str, Callable] = {}
        
        if rules_dir:
            self.load_rules_from_directory(rules_dir)
        else:
            self._register_built_in_rules()
    
    def _register_built_in_rules(self):
        """Register default built-in rules"""
        # These rules are applied even without YAML files
        self.rules = [
            Rule(
                id="high-complexity",
                name="High Cyclomatic Complexity",
                type=RuleType.METRIC,
                severity=Severity.WARNING,
                description="Method has very high cyclomatic complexity",
                config={"threshold": 10}
            ),
            Rule(
                id="long-method",
                name="Long Method",
                type=RuleType.METRIC,
                severity=Severity.WARNING,
                description="Method is too long (exceeds LOC threshold)",
                config={"threshold": 50}
            ),
            Rule(
                id="god-class",
                name="God Class",
                type=RuleType.METRIC,
                severity=Severity.ERROR,
                description="Class is too large (possible God Class anti-pattern)",
                config={"threshold": 300}
            ),
            Rule(
                id="deep-nesting",
                name="Deep Nesting",
                type=RuleType.METRIC,
                severity=Severity.WARNING,
                description="Code has excessive nesting depth",
                config={"threshold": 4}
            ),
            Rule(
                id="empty-catch-block",
                name="Empty Catch Block",
                type=RuleType.PATTERN,
                severity=Severity.ERROR,
                description="Catch block has no exception handling",
                config={}
            ),
            Rule(
                id="magic-numbers",
                name="Magic Numbers",
                type=RuleType.PATTERN,
                severity=Severity.WARNING,
                description="Code contains hard-coded magic numbers",
                config={}
            ),
        ]
    
    def load_rules_from_directory(self, rules_dir: str):
        """
        Load rules from YAML files in a directory
        
        Args:
            rules_dir: Path to directory containing rule YAML files
        """
        path = Path(rules_dir)
        
        if not path.exists():
            # Fall back to built-in rules
            self._register_built_in_rules()
            return
        
        self.rules = []
        
        # Load all YAML files
        for yaml_file in path.glob("*.yaml"):
            self._load_yaml_rules(yaml_file)
    
    def _load_yaml_rules(self, yaml_file: Path):
        """
        Load rules from a single YAML file
        
        Args:
            yaml_file: Path to YAML file
        """
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data or 'rules' not in data:
                return
            
            for rule_data in data['rules']:
                rule = Rule(
                    id=rule_data['id'],
                    name=rule_data['name'],
                    type=RuleType[rule_data.get('type', 'METRIC').upper()],
                    severity=Severity[rule_data.get('severity', 'WARNING').upper()],
                    description=rule_data.get('description', ''),
                    enabled=rule_data.get('enabled', True),
                    config=rule_data.get('config', {})
                )
                self.rules.append(rule)
        
        except Exception as e:
            print(f"Error loading rules from {yaml_file}: {e}")
    
    def analyze(self, code: str, filename: str) -> List[Finding]:
        """
        Analyze code and return findings
        
        Args:
            code: C# source code to analyze
            filename: Name of the file being analyzed
            
        Returns:
            List of Finding objects (issues detected)
        """
        findings: List[Finding] = []
        
        # Calculate metrics
        metrics = MetricsCalculator(code, filename).calculate()
        
        # Apply each enabled rule
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if rule.type == RuleType.METRIC:
                findings.extend(self._apply_metric_rule(rule, metrics, code))
            elif rule.type == RuleType.PATTERN:
                findings.extend(self._apply_pattern_rule(rule, code, metrics))
        
        # Sort by severity and line number
        severity_order = {
            Severity.ERROR: 0,
            Severity.WARNING: 1,
            Severity.INFO: 2,
            Severity.SUGGESTION: 3
        }
        findings.sort(key=lambda f: (severity_order[f.severity], f.line))
        
        return findings
    
    def _apply_metric_rule(
        self, rule: Rule, metrics: FileMetrics, code: str
    ) -> List[Finding]:
        """Apply a metric-based rule"""
        findings: List[Finding] = []
        threshold = rule.config.get('threshold', 0)
        
        if rule.id == "high-complexity":
            for class_m in metrics.classes:
                for method_m in class_m.methods:
                    if method_m.cyclomatic_complexity > threshold:
                        findings.append(Finding(
                            rule_id=rule.id,
                            severity=rule.severity,
                            message=f"{rule.name}: Method '{method_m.name}' has complexity "
                                   f"{method_m.cyclomatic_complexity}",
                            file=metrics.filename,
                            line=method_m.start_line,
                            suggestions=[
                                "Break method into smaller functions",
                                "Extract conditional logic into helper methods",
                                "Use polymorphism instead of complex conditionals"
                            ],
                            metadata={
                                "complexity": method_m.cyclomatic_complexity,
                                "threshold": threshold,
                                "method": method_m.name
                            }
                        ))
        
        elif rule.id == "long-method":
            for class_m in metrics.classes:
                for method_m in class_m.methods:
                    if method_m.loc > threshold:
                        findings.append(Finding(
                            rule_id=rule.id,
                            severity=rule.severity,
                            message=f"{rule.name}: Method '{method_m.name}' is {method_m.loc} "
                                   f"LOC (threshold: {threshold})",
                            file=metrics.filename,
                            line=method_m.start_line,
                            suggestions=[
                                "Extract methods for specific responsibilities",
                                "Use helper methods to reduce size",
                                "Consider using lambdas or LINQ where appropriate"
                            ],
                            metadata={
                                "loc": method_m.loc,
                                "threshold": threshold,
                                "method": method_m.name
                            }
                        ))
        
        elif rule.id == "god-class":
            for class_m in metrics.classes:
                if class_m.loc > threshold:
                    findings.append(Finding(
                        rule_id=rule.id,
                        severity=rule.severity,
                        message=f"{rule.name}: Class '{class_m.name}' is {class_m.loc} LOC "
                               f"(threshold: {threshold})",
                        file=metrics.filename,
                        line=class_m.start_line,
                        suggestions=[
                            "Break class into smaller, focused classes",
                            "Apply Single Responsibility Principle",
                            "Consider using composition over inheritance"
                        ],
                        metadata={
                            "loc": class_m.loc,
                            "threshold": threshold,
                            "class": class_m.name,
                            "method_count": class_m.method_count
                        }
                    ))
        
        elif rule.id == "deep-nesting":
            for class_m in metrics.classes:
                for method_m in class_m.methods:
                    if method_m.nesting_depth > threshold:
                        findings.append(Finding(
                            rule_id=rule.id,
                            severity=rule.severity,
                            message=f"{rule.name}: Method '{method_m.name}' has nesting depth "
                                   f"{method_m.nesting_depth}",
                            file=metrics.filename,
                            line=method_m.start_line,
                            suggestions=[
                                "Extract nested blocks into separate methods",
                                "Use guard clauses to reduce nesting",
                                "Consider using early returns"
                            ],
                            metadata={
                                "nesting_depth": method_m.nesting_depth,
                                "threshold": threshold,
                                "method": method_m.name
                            }
                        ))
        
        return findings
    
    def _apply_pattern_rule(
        self, rule: Rule, code: str, metrics: FileMetrics
    ) -> List[Finding]:
        """Apply a pattern-based rule"""
        findings: List[Finding] = []
        
        if rule.id == "empty-catch-block":
            lines = code.split('\n')
            for i, line in enumerate(lines):
                # Look for pattern: catch (...) { }
                if 'catch' in line and '{' in line:
                    # Simple check: next non-empty line should not be }
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    
                    if j < len(lines) and lines[j].strip() == '}':
                        findings.append(Finding(
                            rule_id=rule.id,
                            severity=rule.severity,
                            message="Empty catch block - exception is silently ignored",
                            file=metrics.filename,
                            line=i + 1,
                            suggestions=[
                                "Add exception logging or handling",
                                "Rethrow the exception if not handling it",
                                "Add meaningful comments if intentionally empty"
                            ]
                        ))
        
        elif rule.id == "magic-numbers":
            lines = code.split('\n')
            for i, line in enumerate(lines):
                # Simple pattern: look for numbers in assignments/comparisons
                # Skip: 0, 1, 2 (common), decimal points, dates
                import re
                # Match numbers that aren't 0, 1, 2 and aren't in strings
                matches = re.findall(r'(?<!["\'])(?<!\d)([3-9]\d*|100+)(?!["\'])', line)
                
                if matches and 'const' not in line and '0x' not in line:
                    findings.append(Finding(
                        rule_id=rule.id,
                        severity=rule.severity,
                        message="Magic number detected - consider defining as named constant",
                        file=metrics.filename,
                        line=i + 1,
                        code_snippet=line.strip(),
                        suggestions=[
                            "Define a const for this magic number",
                            "Use enum if representing discrete values",
                            "Extract to a configuration constant"
                        ]
                    ))
        
        return findings
    
    def register_custom_rule(self, rule_id: str, checker: Callable):
        """
        Register a custom rule checker function
        
        Args:
            rule_id: Unique identifier for the rule
            checker: Function that takes (code, metrics) and returns List[Finding]
        """
        self.custom_rules[rule_id] = checker
