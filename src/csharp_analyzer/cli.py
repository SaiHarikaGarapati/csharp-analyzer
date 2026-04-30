"""
CLI Module

Command-line interface for the C# codebase analyzer.

This module provides the main entry point for the tool with commands like:
- analyze: Scan a directory or file
- report: Generate reports from analysis results
- config: Manage configuration

The CLI uses Click framework for clean command definition.
"""

import click
from pathlib import Path
from typing import Optional
import sys

from .parser import CSharpParser
from .metrics import MetricsCalculator
from .rules import RulesEngine
from .reporter import Reporter


def find_csharp_files(directory: Path) -> list:
    """
    Find all C# files in a directory recursively
    
    Args:
        directory: Root directory to search
        
    Returns:
        List of Path objects for .cs files
    """
    return list(directory.rglob("*.cs"))


@click.group() #defines group of commands, creates main CLI entry point, Used on the cli() function
@click.version_option(version="0.1.0")
def cli():
    """
    C# Codebase Analyzer
    
    Analyze C# code for anti-patterns, complexity, and code duplication.
    """
    pass


@cli.command() #Registers a function as a CLI command, used on analyze(), inspect() and init()
@click.argument('path', type=click.Path(exists=True)) #this argument decorator defines the required positional argument, path - validates file/directory path
@click.option(
    '--output',
    type=click.Path(), #type is basically parameter. It's purpose is data type validation
    help='Output file for report (supports .json, .csv, .html)' #help text shown to users
) #defines an optional flag or parameter, users can choose to provide it or not
@click.option(
    '--format',
    type=click.Choice(['summary', 'detailed', 'table', 'json', 'csv', 'html']), #choice - restricts input to specific options
    default='table', #default value 
    help='Output format for console display'
)
@click.option(
    '--rules-dir',
    type=click.Path(exists=True),
    help='Directory containing rule definitions' /*Load custom rule definitions*/
)
@click.option(
    '--max-issues',
    type=int,
    default=50,
    help='Maximum issues to display'
)
@click.option(
    '--severity',
    type=click.Choice(['error', 'warning', 'info', 'suggestion']),
    multiple=True, #allow multiple values
    help='Filter findings by severity (can specify multiple)'
)
def analyze(
    path: str,
    output: Optional[str],
    format: str,
    rules_dir: Optional[str],
    max_issues: int,
    severity: tuple
):
    """
    Analyze C# code in a directory or file
    
    Examples:
        # Analyze a directory
        csharp-analyzer analyze ./src
        
        # Analyze and save JSON report
        csharp-analyzer analyze ./src --output report.json
        
        # Show only errors and warnings
        csharp-analyzer analyze ./src --severity error --severity warning
    """
    
    target_path = Path(path)
    
    # Find all C# files
    if target_path.is_file():
        csharp_files = [target_path]
    else:
        csharp_files = find_csharp_files(target_path)
    
    if not csharp_files:
        click.echo(click.style("❌ No C# files found", fg='red')) # echo-prints text to the console, style-formats text with colors, echo and style should be used together
        sys.exit(1)
    
    click.echo(click.style(f"📁 Found {len(csharp_files)} C# files", fg='cyan'))
    
    # Initialize engine
    rules_directory = rules_dir or str(Path(__file__).parent.parent.parent / "rules")
    engine = RulesEngine(rules_directory if Path(rules_directory).exists() else None)
    reporter = Reporter()
    
    # Analyze each file - progressbar - shows a progress bar while iterating through items
    with click.progressbar(
        csharp_files,
        label="Analyzing files",
        show_pos=True
    ) as progress_files:
        for csharp_file in progress_files:
            try:
                with open(csharp_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Analyze
                findings = engine.analyze(code, str(csharp_file))
                
                # Filter by severity if specified
                if severity:
                    findings = [f for f in findings if f.severity.value in severity]
                
                reporter.add_findings(findings)
            
            except Exception as e:
                click.echo(
                    click.style(f"⚠️  Error analyzing {csharp_file}: {e}", fg='yellow'),
                    err=True
                )
    
    # Display results
    if format == 'summary':
        reporter.print_summary()
    elif format == 'detailed':
        reporter.print_detailed(max_issues)
    elif format == 'table':
        reporter.print_summary()
        reporter.print_table(max_issues)
    elif format == 'json':
        click.echo(reporter.to_json())
    elif format == 'csv':
        click.echo(reporter.to_csv())
    elif format == 'html':
        click.echo(reporter.to_html())
    
    # Save file report if requested
    if output:
        output_path = Path(output)
        
        if output.endswith('.json'):
            reporter.save_json(output)
        elif output.endswith('.csv'):
            reporter.save_csv(output)
        elif output.endswith('.html'):
            reporter.save_html(output)
        else:
            click.echo(
                click.style(
                    "⚠️  Unknown output format. Supported: .json, .csv, .html",
                    fg='yellow'
                ),
                err=True
            )


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option(
    '--metrics',
    is_flag=True, #boolean flag
    help='Show detailed metrics'
)
def inspect(file: str, metrics: bool):
    """
    Inspect a single C# file in detail
    
    Examples:
        # Show parsing details
        csharp-analyzer inspect ./src/MyClass.cs
        
        # Show detailed metrics
        csharp-analyzer inspect ./src/MyClass.cs --metrics
    """
    
    with open(file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Parse
    parser = CSharpParser(code)
    
    # Show basic info
    click.echo(click.style(f"File: {file}", fg='cyan', bold=True))
    click.echo(f"Lines: {len(code.split(chr(10)))}")
    click.echo(f"Tokens: {len(parser.get_tokens())}")
    click.echo()
    
    # Show classes
    classes = parser.find_classes()
    if classes:
        click.echo(click.style("Classes:", fg='cyan', bold=True))
        for cls in classes:
            click.echo(f"  • {cls['name']} (lines {cls['start_line']}-{cls['end_line']})")
    
    # Show methods
    methods = parser.find_methods()
    if methods:
        click.echo(click.style("\nMethods:", fg='cyan', bold=True))
        for method in methods:
            click.echo(f"  • {method['name']} (lines {method['start_line']}-{method['end_line']})")
    
    # Show metrics if requested
    if metrics:
        click.echo()
        calc = MetricsCalculator(code, file)
        file_metrics = calc.calculate()
        
        click.echo(click.style("Metrics:", fg='cyan', bold=True))
        click.echo(f"  Total LOC: {file_metrics.total_loc}")
        click.echo(f"  Blank lines: {file_metrics.blank_lines}")
        click.echo(f"  Comment lines: {file_metrics.comment_lines}")
        click.echo(f"  Classes: {file_metrics.class_count}")
        click.echo(f"  Methods: {file_metrics.method_count}")
        
        if file_metrics.classes:
            click.echo(f"  Avg class size: {file_metrics.avg_class_size:.1f} LOC")
            click.echo(f"  Avg method size: {file_metrics.avg_method_size:.1f} LOC")
            click.echo(f"  Avg complexity: {file_metrics.avg_complexity:.1f} CC")
        
        # Show high complexity methods
        high_complexity = calc.get_high_complexity_methods(threshold=10)
        if high_complexity:
            click.echo(click.style("\nHigh Complexity Methods:", fg='yellow'))
            for method in high_complexity:
                click.echo(f"  • {method.name}: CC={method.cyclomatic_complexity}")
        
        # Show large methods
        large_methods = calc.get_large_methods(threshold=50)
        if large_methods:
            click.echo(click.style("\nLarge Methods:", fg='yellow'))
            for method in large_methods:
                click.echo(f"  • {method.name}: {method.loc} LOC")


@cli.command()
def init():
    """
    Initialize analyzer configuration in current directory
    
    Creates:
    - .csharp-analyzer.yaml: Main configuration
    - rules/: Custom rule definitions
    """
    
    config_file = Path('.csharp-analyzer.yaml')
    rules_dir = Path('rules')
    
    # Create rules directory
    rules_dir.mkdir(exist_ok=True)
    click.echo(f"✅ Created {rules_dir}/")
    
    # Create config file
    if not config_file.exists():
        config_content = """# C# Analyzer Configuration

# Severity levels to report (error, warning, info, suggestion)
severity_levels:
  - error
  - warning
  - info

# Rules directories to load
rules_directories:
  - ./rules

# Output settings
output:
  format: table
  max_issues: 50

# Custom rule settings
rules:
  high-complexity:
    threshold: 10
  long-method:
    threshold: 50
  god-class:
    threshold: 300
"""
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        click.echo(f"✅ Created {config_file}")
    else:
        click.echo(f"ℹ️  {config_file} already exists")
    
    click.echo("\n✅ Analyzer initialized!")


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main()
