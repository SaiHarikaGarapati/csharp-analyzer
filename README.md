# C# Codebase Analyzer

A Python-based tool for analyzing C# codebases to detect anti-patterns, complexity metrics, code duplication, and suggest improvements.

## Features

### Phase 1: Core Analysis
- **C# Code Parsing**: Tokenize and extract metrics from C# code
- **Complexity Metrics**: Calculate cyclomatic complexity, cognitive complexity, LOC
- **Pattern Detection**: Identify anti-patterns (God Classes, Long Methods, etc.)
- **Duplication Detection**: Find duplicate code segments using fingerprinting

### Phase 2: Git Integration & Performance
- **Incremental Analysis**: Only analyze changed files
- **Git Blame Integration**: Track when anti-patterns were introduced
- **Caching Layer**: Store results for faster subsequent runs

### Phase 3: AI Enhancement (Optional)
- **LLM Integration**: Get AI-powered improvement suggestions
- **Context-Aware**: Understand semantic meaning of issues

## Installation

```bash
pip install -e .

# With AI support
pip install -e ".[ai]"
```

## Usage

```bash
# Analyze C# directory
csharp-analyzer analyze ./src

# With output report
csharp-analyzer analyze ./src --output report.json

# Incremental (Git-based)
csharp-analyzer analyze ./src --incremental

# With AI suggestions
csharp-analyzer analyze ./src --ai
```

## Project Structure

```
csharp-analyzer/
├── src/csharp_analyzer/
│   ├── __init__.py
│   ├── parser.py          # C# tokenization and parsing
│   ├── metrics.py         # Complexity and metrics calculation
│   ├── rules.py           # Pattern matching engine
│   ├── git_utils.py       # Git integration (Phase 2)
│   ├── incremental.py     # Incremental analysis (Phase 2)
│   ├── cache.py           # Caching layer (Phase 2)
│   ├── ai_module.py       # LLM integration (Phase 3)
│   ├── reporter.py        # Output formatting
│   └── cli.py             # Command-line interface
├── rules/
│   ├── anti_patterns.yaml
│   ├── metrics.yaml
│   └── duplication.yaml
├── tests/
├── pyproject.toml
└── README.md
```

## Development Roadmap

- [ ] Phase 1: Core Analysis Engine
- [ ] Phase 2: Git Integration & Caching
- [ ] Phase 3: AI Module

## License

MIT
