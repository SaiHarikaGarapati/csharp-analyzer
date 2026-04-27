"""
Reporter Module

Formats and outputs analysis findings in different formats:
- Console (colored table)
- JSON (for tool integration)
- HTML (for viewing)
- CSV (for importing to other tools)

Key Responsibility:
- Convert findings to human/machine-readable formats
- Handle different verbosity levels
- Summarize findings
"""

import json
from typing import List, Dict, Any
from pathlib import Path
from dataclasses import asdict
from tabulate import tabulate

from .rules import Finding, Severity


class Reporter:
    """
    Generates analysis reports in various formats
    """
    
    def __init__(self):
        """Initialize reporter"""
        self.findings: List[Finding] = []
    
    def add_findings(self, findings: List[Finding]):
        """
        Add findings to the report
        
        Args:
            findings: List of Finding objects
        """
        self.findings.extend(findings)
    
    def print_summary(self):
        """Print a summary of findings to console"""
        if not self.findings:
            print("✅ No issues found!")
            return
        
        # Count by severity
        severity_counts = {}
        for severity in Severity:
            count = sum(1 for f in self.findings if f.severity == severity)
            if count > 0:
                severity_counts[severity.value] = count
        
        print("\n" + "="*60)
        print("ANALYSIS SUMMARY")
        print("="*60)
        
        for severity_type, count in severity_counts.items():
            icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️", "suggestion": "💡"}.get(
                severity_type, "•"
            )
            print(f"{icon} {severity_type.upper()}: {count}")
        
        print(f"\nTotal Issues: {len(self.findings)}")
        print("="*60 + "\n")
    
    def print_detailed(self, max_issues: int = None):
        """
        Print detailed findings to console
        
        Args:
            max_issues: Maximum issues to display (None for all)
        """
        if not self.findings:
            print("✅ No issues found!")
            return
        
        print("\n" + "="*80)
        print("DETAILED FINDINGS")
        print("="*80)
        
        findings_to_show = self.findings[:max_issues] if max_issues else self.findings
        
        for i, finding in enumerate(findings_to_show, 1):
            severity_icon = {
                Severity.ERROR: "❌",
                Severity.WARNING: "⚠️",
                Severity.INFO: "ℹ️",
                Severity.SUGGESTION: "💡"
            }.get(finding.severity, "•")
            
            print(f"\n[{i}] {severity_icon} {finding.severity.value.upper()}")
            print(f"    Rule: {finding.rule_id}")
            print(f"    Message: {finding.message}")
            print(f"    Location: {finding.file}:{finding.line}")
            
            if finding.code_snippet:
                print(f"    Code: {finding.code_snippet}")
            
            if finding.suggestions:
                print(f"    Suggestions:")
                for suggestion in finding.suggestions:
                    print(f"      • {suggestion}")
        
        if max_issues and len(self.findings) > max_issues:
            print(f"\n... and {len(self.findings) - max_issues} more issues")
        
        print("\n" + "="*80 + "\n")
    
    def print_table(self, max_issues: int = 20):
        """
        Print findings as a formatted table
        
        Args:
            max_issues: Maximum issues to display in table
        """
        if not self.findings:
            print("✅ No issues found!")
            return
        
        findings_to_show = self.findings[:max_issues]
        
        # Prepare table data
        table_data = []
        for finding in findings_to_show:
            severity_icon = {
                Severity.ERROR: "❌",
                Severity.WARNING: "⚠️",
                Severity.INFO: "ℹ️",
                Severity.SUGGESTION: "💡"
            }.get(finding.severity, "•")
            
            table_data.append([
                severity_icon,
                finding.rule_id,
                f"{Path(finding.file).name}:{finding.line}",
                finding.message[:50] + ("..." if len(finding.message) > 50 else "")
            ])
        
        headers = ["Severity", "Rule", "Location", "Issue"]
        
        print("\n" + "="*100)
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print("="*100 + "\n")
    
    def to_json(self) -> str:
        """
        Convert findings to JSON format
        
        Returns:
            JSON string representation of findings
        """
        findings_data = []
        
        for finding in self.findings:
            data = {
                "rule_id": finding.rule_id,
                "severity": finding.severity.value,
                "message": finding.message,
                "file": finding.file,
                "line": finding.line,
                "column": finding.column,
                "code_snippet": finding.code_snippet,
                "suggestions": finding.suggestions,
                "metadata": finding.metadata
            }
            findings_data.append(data)
        
        report = {
            "summary": {
                "total_issues": len(self.findings),
                "by_severity": self._count_by_severity(),
                "by_rule": self._count_by_rule()
            },
            "findings": findings_data
        }
        
        return json.dumps(report, indent=2)
    
    def save_json(self, filepath: str):
        """
        Save findings to JSON file
        
        Args:
            filepath: Path to output JSON file
        """
        with open(filepath, 'w') as f:
            f.write(self.to_json())
        
        print(f"✅ Report saved to {filepath}")
    
    def to_csv(self) -> str:
        """
        Convert findings to CSV format
        
        Returns:
            CSV string representation
        """
        lines = ["Rule ID,Severity,File,Line,Message"]
        
        for finding in self.findings:
            # Escape quotes in message
            message = finding.message.replace('"', '""')
            line = f'{finding.rule_id},"{finding.severity.value}",{finding.file},{finding.line},"{message}"'
            lines.append(line)
        
        return '\n'.join(lines)
    
    def save_csv(self, filepath: str):
        """
        Save findings to CSV file
        
        Args:
            filepath: Path to output CSV file
        """
        with open(filepath, 'w') as f:
            f.write(self.to_csv())
        
        print(f"✅ Report saved to {filepath}")
    
    def to_html(self) -> str:
        """
        Convert findings to HTML report
        
        Returns:
            HTML string
        """
        severity_colors = {
            Severity.ERROR: "#ff4444",
            Severity.WARNING: "#ffaa00",
            Severity.INFO: "#4488ff",
            Severity.SUGGESTION: "#00aa44"
        }
        
        html_parts = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '<meta charset="UTF-8">',
            '<title>Code Analysis Report</title>',
            '<style>',
            'body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }',
            '.header { background-color: #333; color: white; padding: 20px; border-radius: 5px; }',
            '.summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }',
            '.summary-item { background-color: white; padding: 15px; border-radius: 5px; border-left: 4px solid; }',
            '.error { border-left-color: #ff4444; }',
            '.warning { border-left-color: #ffaa00; }',
            '.info { border-left-color: #4488ff; }',
            '.suggestion { border-left-color: #00aa44; }',
            '.summary-item h3 { margin: 0 0 10px 0; }',
            '.findings { background-color: white; padding: 20px; border-radius: 5px; }',
            '.finding { border-left: 4px solid; padding: 15px; margin: 10px 0; border-radius: 3px; }',
            '.finding.error { border-left-color: #ff4444; background-color: #fff5f5; }',
            '.finding.warning { border-left-color: #ffaa00; background-color: #fffbf0; }',
            '.finding.info { border-left-color: #4488ff; background-color: #f0f5ff; }',
            '.finding.suggestion { border-left-color: #00aa44; background-color: #f0fff5; }',
            '.finding-title { font-weight: bold; color: #333; margin-bottom: 5px; }',
            '.finding-location { color: #666; font-size: 0.9em; }',
            '.finding-message { margin: 10px 0; }',
            '.finding-suggestions { background-color: rgba(255,255,255,0.5); padding: 10px; border-radius: 3px; margin-top: 10px; }',
            '.finding-suggestions ul { margin: 5px 0; }',
            '.footer { text-align: center; color: #666; margin-top: 20px; font-size: 0.9em; }',
            '</style>',
            '</head>',
            '<body>',
            '<div class="header">',
            '<h1>Code Analysis Report</h1>',
            '</div>'
        ]
        
        # Add summary
        summary_counts = self._count_by_severity()
        html_parts.append('<div class="summary">')
        
        for severity in [Severity.ERROR, Severity.WARNING, Severity.INFO, Severity.SUGGESTION]:
            count = summary_counts.get(severity.value, 0)
            html_parts.append(f'<div class="summary-item {severity.value}">')
            html_parts.append(f'<h3>{severity.value.upper()}</h3>')
            html_parts.append(f'<p>{count}</p>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')
        
        # Add findings
        html_parts.append('<div class="findings">')
        
        for finding in self.findings:
            severity = finding.severity.value
            html_parts.append(f'<div class="finding {severity}">')
            html_parts.append(f'<div class="finding-title">{finding.rule_id}: {finding.message}</div>')
            html_parts.append(f'<div class="finding-location">{finding.file}:{finding.line}</div>')
            
            if finding.code_snippet:
                html_parts.append(f'<pre>{finding.code_snippet}</pre>')
            
            if finding.suggestions:
                html_parts.append('<div class="finding-suggestions">')
                html_parts.append('<strong>Suggestions:</strong>')
                html_parts.append('<ul>')
                for suggestion in finding.suggestions:
                    html_parts.append(f'<li>{suggestion}</li>')
                html_parts.append('</ul>')
                html_parts.append('</div>')
            
            html_parts.append('</div>')
        
        html_parts.extend([
            '</div>',
            '<div class="footer">',
            f'<p>Total Issues: {len(self.findings)}</p>',
            '</div>',
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    def save_html(self, filepath: str):
        """
        Save findings to HTML file
        
        Args:
            filepath: Path to output HTML file
        """
        with open(filepath, 'w') as f:
            f.write(self.to_html())
        
        print(f"✅ Report saved to {filepath}")
    
    def _count_by_severity(self) -> Dict[str, int]:
        """Count findings by severity level"""
        counts = {}
        for severity in Severity:
            count = sum(1 for f in self.findings if f.severity == severity)
            if count > 0:
                counts[severity.value] = count
        return counts
    
    def _count_by_rule(self) -> Dict[str, int]:
        """Count findings by rule"""
        counts = {}
        for finding in self.findings:
            counts[finding.rule_id] = counts.get(finding.rule_id, 0) + 1
        return counts
