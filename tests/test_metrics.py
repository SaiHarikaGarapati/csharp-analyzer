"""Tests for the metrics module"""

import pytest
from csharp_analyzer.metrics import MetricsCalculator


class TestMetricsCalculator:
    """Test cases for MetricsCalculator"""
    
    def test_basic_metrics(self):
        """Test calculation of basic metrics"""
        code = """
        public class Calculator {
            public int Add(int a, int b) {
                return a + b;
            }
        }
        """
        calculator = MetricsCalculator(code, "test.cs")
        metrics = calculator.calculate()
        
        assert metrics.filename == "test.cs"
        assert metrics.total_loc > 0
        assert metrics.class_count == 1
    
    def test_cyclomatic_complexity(self):
        """Test cyclomatic complexity calculation"""
        code = """
        public void Method(int x) {
            if (x > 0) {
                return;
            }
        }
        """
        calculator = MetricsCalculator(code, "test.cs")
        metrics = calculator.calculate()
        
        # Should have complexity > 1 due to if statement
        assert any(m.cyclomatic_complexity > 1 for c in metrics.classes for m in c.methods)
    
    def test_high_complexity_methods(self):
        """Test identifying high complexity methods"""
        code = """
        public void ComplexMethod(int x) {
            if (x == 1) { }
            else if (x == 2) { }
            else if (x == 3) { }
            else if (x == 4) { }
            else if (x == 5) { }
        }
        """
        calculator = MetricsCalculator(code, "test.cs")
        calculator.calculate()
        
        high_cc = calculator.get_high_complexity_methods(threshold=3)
        assert len(high_cc) > 0
    
    def test_nesting_depth(self):
        """Test nesting depth calculation"""
        code = """
        public void Nested() {
            if (true) {
                if (true) {
                    if (true) {
                        Console.WriteLine("Deep");
                    }
                }
            }
        }
        """
        calculator = MetricsCalculator(code, "test.cs")
        metrics = calculator.calculate()
        
        # Should have nesting depth >= 3
        has_deep_nesting = any(
            m.nesting_depth >= 3 
            for c in metrics.classes 
            for m in c.methods
        )
        assert has_deep_nesting
