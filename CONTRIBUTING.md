# Contributing to C# Analyzer

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/csharp-analyzer.git
cd csharp-analyzer
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install in development mode
```bash
pip install -e ".[dev]"
```

## Making Changes

### 1. Create a feature branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make your changes
- Follow PEP 8 style guide
- Add docstrings to all functions and classes
- Write unit tests for new functionality
- Update relevant documentation

### 3. Run tests
```bash
pytest tests/ -v
```

### 4. Check code style
```bash
black src/ tests/
flake8 src/ tests/
```

## Submitting Changes

### 1. Commit your changes
```bash
git add .
git commit -m "Description of changes"
```

### 2. Push to your fork
```bash
git push origin feature/your-feature-name
```

### 3. Create a Pull Request
- Provide a clear description of the changes
- Reference any related issues
- Ensure all tests pass

## Code Style

- Use Black for formatting: `black src/`
- Use Flake8 for linting: `flake8 src/`
- Follow PEP 8 guidelines
- Write descriptive docstrings

## Writing Tests

Tests go in the `tests/` directory with the same structure as `src/`.

Example:
```python
import pytest
from csharp_analyzer.parser import CSharpParser

def test_parse_simple_class():
    code = """
    public class Example {
        public void Method() { }
    }
    """
    parser = CSharpParser(code)
    classes = parser.find_classes()
    
    assert len(classes) == 1
    assert classes[0]['name'] == 'Example'
```

## Reporting Issues

- Use GitHub Issues to report bugs
- Provide a clear description
- Include reproduction steps
- Attach relevant code samples

## Questions?

- Check the [documentation](PHASE_1_GUIDE.md)
- Open a discussion on GitHub
- Email: your-email@example.com

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
