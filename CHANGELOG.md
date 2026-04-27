# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 2: Git integration for incremental analysis
- Phase 3: AI-powered suggestions

## [0.1.0] - 2024-04-27

### Added
- Initial release (Phase 1: Core Analysis)
- C# code parser with tokenization
- Complexity metrics calculation (cyclomatic, cognitive)
- Rule engine with YAML-based rules
- Built-in detection of anti-patterns
- Multiple output formats (table, JSON, CSV, HTML)
- Command-line interface
- Comprehensive documentation

### Features
- **Parser**: Lightweight tokenization of C# code
- **Metrics**: LOC, cyclomatic complexity, cognitive complexity, nesting depth
- **Rules**: God Class, Long Method, High Complexity, Deep Nesting, Empty Catch Blocks, Magic Numbers
- **Reporter**: Console, JSON, CSV, HTML output formats
- **CLI**: analyze, inspect, init commands

### Known Limitations
- No semantic analysis (uses tokenization)
- Pattern-based rules are basic
- AI suggestions not yet implemented
