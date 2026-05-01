"""Simple HTML report generator for PyShaft."""

from pathlib import Path
from typing import Any
import json


def render_html(report_data: Any, output_dir: Path) -> Path:
    """Generate a simple HTML report from test data."""
    
    html_path = output_dir / "index.html"
    
    # Get test results
    tests = getattr(report_data, 'tests', [])
    
    # Build test rows
    rows = []
    passed = 0
    failed = 0
    
    for test in tests:
        status = test.get('status', 'unknown')
        name = test.get('name', 'Unknown')
        error = test.get('error', '')
        
        if status == 'passed':
            passed += 1
            status_display = '<span style="color: green;">PASSED</span>'
        else:
            failed += 1
            status_display = '<span style="color: red;">FAILED</span>'
        
        rows.append(f"""
        <tr>
            <td>{name}</td>
            <td>{status_display}</td>
            <td>{error[:100] if error else '-'}</td>
        </tr>
        """)
    
    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>PyShaft Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .summary {{ margin: 20px 0; padding: 10px; background: #f0f0f0; }}
    </style>
</head>
<body>
    <h1>PyShaft Test Report</h1>
    <div class="summary">
        <strong>Results:</strong> {passed} passed, {failed} failed
    </div>
    <table>
        <tr>
            <th>Test Name</th>
            <th>Status</th>
            <th>Error</th>
        </tr>
        {''.join(rows)}
    </table>
</body>
</html>"""
    
    html_path.write_text(html, encoding='utf-8')
    return html_path


__all__ = ['render_html']