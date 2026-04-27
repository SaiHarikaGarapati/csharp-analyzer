"""
Metrics Module

Calculates various code metrics from parsed C# code:
1. Complexity Metrics
   - Cyclomatic Complexity (CC): How many paths through code
   - Cognitive Complexity: How hard is code to understand
   
2. Size Metrics
   - Lines of Code (LOC)
   - Physical Lines (including blanks and comments)
   - Method count
   - Class count
   
3. Quality Indicators
   - Average method length
   - Average class size
   - Nesting depth

Key Concept:
Cyclomatic Complexity = 1 + (number of decision points)
Decision points: if, else, switch, case, for, foreach, while, catch, &&, ||, ?:

These metrics help identify:
- Overly complex methods (high CC)
- Large classes (God Class pattern)
- Deep nesting (hard to understand)

Performance: ~100,000 LOC/sec
"""

from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum
from .parser import CSharpParser, Token, TokenType


@dataclass
class MethodMetrics:
    """Metrics for a single method"""
    name: str
    start_line: int
    end_line: int
    loc: int = 0  # Lines of Code
    cyclomatic_complexity: int = 1  # CC = 1 + decision points
    cognitive_complexity: int = 0  # CC weighted by nesting
    nesting_depth: int = 0  # Max nesting level
    decision_points: int = 0  # Count of if/switch/loop statements


@dataclass
class ClassMetrics:
    """Metrics for a single class"""
    name: str
    start_line: int
    end_line: int
    loc: int = 0  # Lines in class
    is_abstract: bool = False
    method_count: int = 0
    public_method_count: int = 0
    property_count: int = 0
    avg_method_complexity: float = 0.0
    max_method_complexity: int = 0
    methods: List[MethodMetrics] = field(default_factory=list)


@dataclass
class FileMetrics:
    """Metrics for entire file"""
    filename: str
    total_loc: int = 0
    physical_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    class_count: int = 0
    method_count: int = 0
    avg_class_size: float = 0.0
    avg_method_size: float = 0.0
    avg_complexity: float = 0.0
    classes: List[ClassMetrics] = field(default_factory=list)


class MetricsCalculator:
    """
    Calculates code metrics from parsed C# code
    """
    
    # Keywords that increase cyclomatic complexity
    COMPLEXITY_KEYWORDS = {
        'if', 'else', 'switch', 'case', 'for', 'foreach', 'while', 'do',
        'catch', 'finally', 'default'
    }
    
    # Operators that increase cyclomatic complexity
    COMPLEXITY_OPERATORS = {'&&', '||', '?', ':'}
    
    def __init__(self, code: str, filename: str = ""):
        """
        Initialize calculator with code
        
        Args:
            code: C# source code
            filename: Name of the file being analyzed
        """
        self.code = code
        self.filename = filename
        self.parser = CSharpParser(code)
        self.metrics = FileMetrics(filename=filename)
    
    def calculate(self) -> FileMetrics:
        """
        Calculate all metrics for the code
        
        Returns:
            FileMetrics object with all calculated metrics
        """
        self._calculate_basic_metrics()
        self._calculate_class_metrics()
        self._calculate_aggregate_metrics()
        return self.metrics
    
    def _calculate_basic_metrics(self):
        """
        Calculate basic line metrics:
        - Total LOC
        - Physical lines
        - Blank lines
        - Comment lines
        """
        lines = self.code.split('\n')
        self.metrics.physical_lines = len(lines)
        
        blank_count = 0
        comment_count = 0
        loc = 0
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                blank_count += 1
            elif stripped.startswith('//'):
                comment_count += 1
            else:
                loc += 1
        
        self.metrics.total_loc = loc
        self.metrics.blank_lines = blank_count
        self.metrics.comment_lines = comment_count
    
    def _calculate_class_metrics(self):
        """
        Calculate metrics for each class in the code
        """
        classes = self.parser.find_classes()
        methods = self.parser.find_methods()
        
        for class_info in classes:
            class_metrics = ClassMetrics(
                name=class_info['name'],
                start_line=class_info['start_line'],
                end_line=class_info['end_line'],
                loc=class_info['line_count'],
                is_abstract=class_info['is_abstract']
            )
            
            # Find methods in this class
            class_methods = [
                m for m in methods 
                if class_info['start_line'] <= m['start_line'] <= class_info['end_line']
            ]
            
            for method_info in class_methods:
                method_metrics = self._calculate_method_metrics(method_info)
                class_metrics.methods.append(method_metrics)
                class_metrics.method_count += 1
            
            # Calculate class-level metrics
            if class_metrics.methods:
                complexities = [m.cyclomatic_complexity for m in class_metrics.methods]
                class_metrics.avg_method_complexity = sum(complexities) / len(complexities)
                class_metrics.max_method_complexity = max(complexities)
            
            self.metrics.classes.append(class_metrics)
    
    def _calculate_method_metrics(self, method_info: Dict) -> MethodMetrics:
        """
        Calculate metrics for a single method
        
        Args:
            method_info: Dictionary with method name, start_line, end_line
            
        Returns:
            MethodMetrics object
        """
        metrics = MethodMetrics(
            name=method_info['name'],
            start_line=method_info['start_line'],
            end_line=method_info['end_line'],
            loc=method_info['line_count']
        )
        
        # Get code segment for this method
        lines = self.code.split('\n')
        method_lines = lines[method_info['start_line']-1:method_info['end_line']]
        method_code = '\n'.join(method_lines)
        
        # Calculate complexity
        metrics.cyclomatic_complexity = self._calculate_cyclomatic_complexity(method_code)
        metrics.cognitive_complexity = self._calculate_cognitive_complexity(method_code)
        metrics.nesting_depth = self._calculate_nesting_depth(method_code)
        
        return metrics
    
    def _calculate_cyclomatic_complexity(self, code: str) -> int:
        """
        Calculate cyclomatic complexity
        CC = 1 + (number of decision points)
        
        Decision points: if, else, switch, case, for, foreach, while, catch, &&, ||, ?:
        """
        complexity = 1  # Base complexity
        decision_points = 0
        
        # Tokenize the code
        parser = CSharpParser(code)
        tokens = parser.get_non_comment_tokens()
        
        for i, token in enumerate(tokens):
            # Count keyword decision points
            if token.type == TokenType.KEYWORD and token.value in self.COMPLEXITY_KEYWORDS:
                if token.value == 'else':
                    # else doesn't add complexity by itself (already counted with if)
                    continue
                if token.value in ('case', 'default'):
                    # Each case/default adds 1
                    decision_points += 1
                else:
                    decision_points += 1
            
            # Count operator decision points
            elif token.type == TokenType.OPERATOR:
                if token.value == '&&' or token.value == '||':
                    decision_points += 1
                elif token.value == '?':
                    # Ternary operator adds 1
                    decision_points += 1
        
        return complexity + decision_points
    
    def _calculate_cognitive_complexity(self, code: str) -> int:
        """
        Calculate cognitive complexity
        
        Unlike cyclomatic complexity, cognitive complexity:
        - Doesn't count first level of nesting
        - Increments by nesting depth
        - Ignores some operators
        
        Formula: For each decision point, add (1 + nesting level)
        """
        complexity = 0
        nesting_level = 0
        
        parser = CSharpParser(code)
        tokens = parser.get_non_comment_tokens()
        
        for token in tokens:
            # Track brace depth for nesting
            if token.value == '{':
                nesting_level += 1
            elif token.value == '}':
                nesting_level = max(0, nesting_level - 1)
            
            # Count decision points with nesting weight
            elif token.type == TokenType.KEYWORD and token.value in self.COMPLEXITY_KEYWORDS:
                if token.value not in ('else', 'default'):
                    complexity += 1 + max(0, nesting_level - 1)
                elif token.value in ('case', 'default'):
                    complexity += 1
        
        return complexity
    
    def _calculate_nesting_depth(self, code: str) -> int:
        """
        Find maximum nesting depth in the code
        """
        max_depth = 0
        current_depth = 0
        
        parser = CSharpParser(code)
        tokens = parser.get_non_comment_tokens()
        
        for token in tokens:
            if token.value == '{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif token.value == '}':
                current_depth = max(0, current_depth - 1)
        
        return max_depth
    
    def _calculate_aggregate_metrics(self):
        """
        Calculate aggregate metrics from class metrics
        """
        if self.metrics.classes:
            class_sizes = [c.loc for c in self.metrics.classes]
            self.metrics.avg_class_size = sum(class_sizes) / len(class_sizes)
            
            all_methods = [m for c in self.metrics.classes for m in c.methods]
            if all_methods:
                method_sizes = [m.loc for m in all_methods]
                method_complexities = [m.cyclomatic_complexity for m in all_methods]
                
                self.metrics.avg_method_size = sum(method_sizes) / len(method_sizes)
                self.metrics.avg_complexity = sum(method_complexities) / len(method_complexities)
            
            self.metrics.class_count = len(self.metrics.classes)
            self.metrics.method_count = sum(c.method_count for c in self.metrics.classes)
    
    def get_high_complexity_methods(self, threshold: int = 10) -> List[MethodMetrics]:
        """
        Get methods with complexity above threshold
        
        Args:
            threshold: Complexity threshold (default 10)
            
        Returns:
            List of high-complexity methods
        """
        high_complexity = []
        for class_metrics in self.metrics.classes:
            for method in class_metrics.methods:
                if method.cyclomatic_complexity > threshold:
                    high_complexity.append(method)
        
        return high_complexity
    
    def get_large_methods(self, threshold: int = 50) -> List[MethodMetrics]:
        """
        Get methods larger than threshold LOC
        
        Args:
            threshold: LOC threshold (default 50)
            
        Returns:
            List of large methods
        """
        large_methods = []
        for class_metrics in self.metrics.classes:
            for method in class_metrics.methods:
                if method.loc > threshold:
                    large_methods.append(method)
        
        return large_methods
    
    def get_large_classes(self, threshold: int = 300) -> List[ClassMetrics]:
        """
        Get classes larger than threshold LOC (God Class pattern)
        
        Args:
            threshold: LOC threshold (default 300)
            
        Returns:
            List of large classes
        """
        return [c for c in self.metrics.classes if c.loc > threshold]
    
    def get_deeply_nested_methods(self, threshold: int = 4) -> List[MethodMetrics]:
        """
        Get methods with nesting depth above threshold
        
        Args:
            threshold: Nesting depth threshold (default 4)
            
        Returns:
            List of deeply nested methods
        """
        deep_methods = []
        for class_metrics in self.metrics.classes:
            for method in class_metrics.methods:
                if method.nesting_depth > threshold:
                    deep_methods.append(method)
        
        return deep_methods
