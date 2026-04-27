"""Tests for the parser module"""

import pytest
from csharp_analyzer.parser import CSharpParser, TokenType


class TestCSharpParser:
    """Test cases for CSharpParser"""
    
    def test_tokenize_simple_code(self):
        """Test tokenization of simple code"""
        code = "public class Test { }"
        parser = CSharpParser(code)
        tokens = parser.get_tokens()
        
        assert len(tokens) > 0
        assert tokens[0].value == "public"
        assert tokens[0].type == TokenType.KEYWORD
    
    def test_find_classes(self):
        """Test finding class definitions"""
        code = """
        public class MyClass {
            public void Method() { }
        }
        """
        parser = CSharpParser(code)
        classes = parser.find_classes()
        
        assert len(classes) == 1
        assert classes[0]['name'] == 'MyClass'
    
    def test_find_methods(self):
        """Test finding method definitions"""
        code = """
        public class MyClass {
            public void FirstMethod() { }
            public int SecondMethod() { return 0; }
        }
        """
        parser = CSharpParser(code)
        methods = parser.find_methods()
        
        assert len(methods) >= 2
    
    def test_skip_comments(self):
        """Test that comments are tokenized but can be filtered"""
        code = """
        // This is a comment
        public class Test { }
        """
        parser = CSharpParser(code)
        non_comment_tokens = parser.get_non_comment_tokens()
        
        # Should not have comment in non-comment tokens
        comment_tokens = [t for t in non_comment_tokens if t.type == TokenType.COMMENT]
        assert len(comment_tokens) == 0
    
    def test_string_parsing(self):
        """Test that strings are properly tokenized"""
        code = 'string text = "Hello World";'
        parser = CSharpParser(code)
        tokens = parser.get_tokens()
        
        string_tokens = [t for t in tokens if t.type == TokenType.STRING]
        assert len(string_tokens) > 0
        assert '"Hello World"' in [t.value for t in string_tokens]
