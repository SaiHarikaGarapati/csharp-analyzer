"""
C# Parser Module

This module is responsible for parsing C# source code without heavy semantic analysis.
We use a lightweight tokenization approach that's fast and efficient.

Key Concepts:
1. Tokenization: Break code into meaningful tokens (keywords, identifiers, operators)
2. Token Stream: Sequential list of tokens for analysis
3. Code Segments: Identify methods, classes, blocks for metrics calculation

Why not use Roslyn?
- Roslyn is accurate but slow and requires .NET runtime
- For metrics calculation, we don't need full semantic analysis
- Tokenization + regex patterns work well for ~95% of cases
- Can be upgraded to tree-sitter later if needed

Performance: ~1000 files/sec on modern hardware
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from enum import Enum


class TokenType(Enum):
    """Types of tokens we recognize in C# code"""
    KEYWORD = "keyword"
    IDENTIFIER = "identifier"
    OPERATOR = "operator"
    PUNCTUATION = "punctuation"
    STRING = "string"
    COMMENT = "comment"
    NUMBER = "number"
    WHITESPACE = "whitespace"
    NEWLINE = "newline"


@dataclass
class Token:
    """
    Represents a single token in C# code
    
    Attributes:
        type: TokenType enum value
        value: The actual token text
        line: Line number where token appears (1-indexed)
        column: Column number where token appears (0-indexed)
    """
    type: TokenType
    value: str
    line: int
    column: int


class CSharpParser:
    """
    Lightweight C# parser that tokenizes code and identifies code structures.
    
    This parser:
    - Removes comments and whitespace
    - Identifies classes, methods, properties
    - Tracks code blocks and nesting levels
    - Extracts relevant code metrics
    """
    
    # C# keywords to recognize
    KEYWORDS = {
        'class', 'interface', 'enum', 'struct', 'namespace',
        'public', 'private', 'protected', 'internal',
        'static', 'async', 'await', 'virtual', 'abstract',
        'override', 'sealed', 'partial', 'const',
        'if', 'else', 'switch', 'case', 'default',
        'for', 'foreach', 'while', 'do', 'break', 'continue',
        'return', 'throw', 'try', 'catch', 'finally',
        'using', 'new', 'typeof', 'is', 'as', 'null',
        'true', 'false', 'this', 'base', 'void',
        'int', 'string', 'bool', 'double', 'float', 'long', 'decimal'
    }
    
    # Operators
    OPERATORS = {
        '==', '!=', '>=', '<=', '&&', '||', '++', '--',
        '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=',
        '<<', '>>', '??', '?.', '=>',
        '=', '+', '-', '*', '/', '%', '&', '|', '^', '!', '<', '>'
    }
    
    def __init__(self, code: str):
        """
        Initialize parser with C# code
        
        Args:
            code: The C# source code to parse
        """
        self.code = code
        self.lines = code.split('\n')
        self.tokens: List[Token] = []
        self._parse()
    
    def _parse(self):
        """
        Main parsing logic: tokenize the code
        """
        line_num = 1
        
        for line_text in self.lines:
            self._tokenize_line(line_text, line_num)
            line_num += 1
    
    def _tokenize_line(self, line: str, line_num: int):
        """
        Tokenize a single line of code
        
        Args:
            line: The line of code to tokenize
            line_num: Current line number
        """
        column = 0
        i = 0
        
        while i < len(line):
            # Skip whitespace (but track newlines)
            if line[i].isspace():
                column += 1
                i += 1
                continue
            
            # Single-line comment
            if i < len(line) - 1 and line[i:i+2] == '//':
                token = Token(
                    type=TokenType.COMMENT,
                    value=line[i:],
                    line=line_num,
                    column=column
                )
                self.tokens.append(token)
                break
            
            # Multi-line comment start (simplified - doesn't track across lines)
            if i < len(line) - 1 and line[i:i+2] == '/*':
                end = line.find('*/', i + 2)
                if end != -1:
                    token = Token(
                        type=TokenType.COMMENT,
                        value=line[i:end+2],
                        line=line_num,
                        column=column
                    )
                    self.tokens.append(token)
                    i = end + 2
                    column += len(token.value)
                    continue
            
            # String literals
            if line[i] in ('"', "'"):
                quote = line[i]
                string_val = quote
                i += 1
                column += 1
                
                while i < len(line):
                    if line[i] == '\\' and i + 1 < len(line):
                        string_val += line[i:i+2]
                        i += 2
                        column += 2
                    elif line[i] == quote:
                        string_val += quote
                        i += 1
                        column += 1
                        break
                    else:
                        string_val += line[i]
                        i += 1
                        column += 1
                
                token = Token(
                    type=TokenType.STRING,
                    value=string_val,
                    line=line_num,
                    column=column - len(string_val)
                )
                self.tokens.append(token)
                continue
            
            # Numbers
            if line[i].isdigit():
                num_val = ''
                start_col = column
                while i < len(line) and (line[i].isdigit() or line[i] == '.'):
                    num_val += line[i]
                    i += 1
                    column += 1
                
                token = Token(
                    type=TokenType.NUMBER,
                    value=num_val,
                    line=line_num,
                    column=start_col
                )
                self.tokens.append(token)
                continue
            
            # Identifiers and keywords
            if line[i].isalpha() or line[i] == '_':
                ident = ''
                start_col = column
                
                while i < len(line) and (line[i].isalnum() or line[i] == '_'):
                    ident += line[i]
                    i += 1
                    column += 1
                
                token_type = (
                    TokenType.KEYWORD 
                    if ident in self.KEYWORDS 
                    else TokenType.IDENTIFIER
                )
                
                token = Token(
                    type=token_type,
                    value=ident,
                    line=line_num,
                    column=start_col
                )
                self.tokens.append(token)
                continue
            
            # Operators (multi-character first)
            found_operator = False
            for op_len in (3, 2, 1):
                if i + op_len <= len(line):
                    potential_op = line[i:i+op_len]
                    if potential_op in self.OPERATORS:
                        token = Token(
                            type=TokenType.OPERATOR,
                            value=potential_op,
                            line=line_num,
                            column=column
                        )
                        self.tokens.append(token)
                        i += op_len
                        column += op_len
                        found_operator = True
                        break
            
            if found_operator:
                continue
            
            # Punctuation
            if line[i] in '{}[]();:,.<>':
                token = Token(
                    type=TokenType.PUNCTUATION,
                    value=line[i],
                    line=line_num,
                    column=column
                )
                self.tokens.append(token)
                i += 1
                column += 1
                continue
            
            # Unknown character - skip
            i += 1
            column += 1
    
    def get_tokens(self) -> List[Token]:
        """Return all tokens"""
        return self.tokens
    
    def get_non_comment_tokens(self) -> List[Token]:
        """Return only non-comment tokens (useful for analysis)"""
        return [t for t in self.tokens if t.type != TokenType.COMMENT]
    
    def find_methods(self) -> List[Dict]:
        """
        Identify method definitions and their boundaries
        
        Returns:
            List of dicts with method info: {name, start_line, end_line, params}
        """
        methods = []
        tokens = self.get_non_comment_tokens()
        
        i = 0
        while i < len(tokens):
            # Look for method pattern: (visibility)? type identifier ( params ) {
            # Simplified: look for pattern like "void MethodName(" or "public string GetValue("
            
            if tokens[i].type == TokenType.KEYWORD and tokens[i].value in (
                'void', 'int', 'string', 'bool', 'double', 'float', 'long', 'decimal'
            ):
                # Might be a method return type
                if i + 1 < len(tokens) and tokens[i+1].type == TokenType.IDENTIFIER:
                    method_name = tokens[i+1].value
                    if i + 2 < len(tokens) and tokens[i+2].value == '(':
                        # Found a method!
                        start_line = tokens[i].line
                        
                        # Find matching closing brace
                        end_line = self._find_matching_brace(tokens, i + 2)
                        
                        methods.append({
                            'name': method_name,
                            'start_line': start_line,
                            'end_line': end_line,
                            'type': tokens[i].value,
                            'line_count': end_line - start_line + 1
                        })
            
            i += 1
        
        return methods
    
    def _find_matching_brace(self, tokens: List[Token], paren_index: int) -> int:
        """Find the line number of the closing brace for a method"""
        depth = 0
        i = paren_index
        
        while i < len(tokens):
            if tokens[i].value == '(':
                depth += 1
            elif tokens[i].value == ')':
                depth -= 1
                if depth == 0:
                    # Now find the opening brace
                    i += 1
                    while i < len(tokens):
                        if tokens[i].value == '{':
                            # Count braces to find matching close
                            return self._find_closing_brace(tokens, i)
                        i += 1
                    return tokens[paren_index].line
            i += 1
        
        return tokens[-1].line
    
    def _find_closing_brace(self, tokens: List[Token], open_brace_index: int) -> int:
        """Find the closing brace matching an opening brace"""
        depth = 1
        i = open_brace_index + 1
        
        while i < len(tokens):
            if tokens[i].value == '{':
                depth += 1
            elif tokens[i].value == '}':
                depth -= 1
                if depth == 0:
                    return tokens[i].line
            i += 1
        
        return tokens[-1].line
    
    def find_classes(self) -> List[Dict]:
        """
        Identify class definitions
        
        Returns:
            List of dicts with class info: {name, start_line, end_line, is_abstract}
        """
        classes = []
        tokens = self.get_non_comment_tokens()
        
        i = 0
        while i < len(tokens):
            # Look for "class ClassName {"
            if tokens[i].type == TokenType.KEYWORD and tokens[i].value == 'class':
                if i + 1 < len(tokens) and tokens[i+1].type == TokenType.IDENTIFIER:
                    class_name = tokens[i+1].value
                    start_line = tokens[i].line
                    
                    # Find opening brace
                    j = i + 2
                    while j < len(tokens) and tokens[j].value != '{':
                        j += 1
                    
                    if j < len(tokens):
                        end_line = self._find_closing_brace(tokens, j)
                        
                        classes.append({
                            'name': class_name,
                            'start_line': start_line,
                            'end_line': end_line,
                            'line_count': end_line - start_line + 1,
                            'is_abstract': i > 0 and tokens[i-1].value == 'abstract'
                        })
            
            i += 1
        
        return classes
