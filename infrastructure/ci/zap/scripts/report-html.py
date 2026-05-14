#!/usr/bin/env python3
"""
ZAP HTML Report Generator
Generates an HTML report from ZAP scan results
"""

import json
import sys
from datetime import datetime

def generate_html_report(alerts_file, output_file='zap-report.html'):
    """Generate HTML report from ZAP alerts JSON"""

    try:
        with open(alerts_file, 'r') as f:
            data = json.load(f)

        alerts = data.get('alerts', [])

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ZAP Security Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #d32f2f; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .alert {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ff9800; }}
        .high {{ border-left-color: #f44336; }}
        .medium {{ border-left-color: #ff9800; }}
        .low {{ border-left-color: #4caf50; }}
        .risk {{ font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f44336; color: white; }}
    </style>
</head>
<body>
    <h1>🛡️ OWASP ZAP Security Report</h1>
    <div class="summary">
        <h2>Scan Summary</h2>
        <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Alerts:</strong> {len(alerts)}</p>
        <p><strong>High Risk:</strong> {len([a for a in alerts if a.get('risk') == 'High'])}</p>
        <p><strong>Medium Risk:</strong> {len([a for a in alerts if a.get('risk') == 'Medium'])}</p>
        <p><strong>Low Risk:</strong> {len([a for a in alerts if a.get('risk') == 'Low'])}</p>
    </div>

    <h2>Alerts</h2>
"""

        for alert in alerts:
            risk_class = alert.get('risk', '').lower()
            html += f"""
    <div class="alert {risk_class}">
        <h3>{alert.get('name', 'Unknown')}</h3>
        <p><span class="risk">Risk Level:</span> {alert.get('risk', 'Unknown')}</p>
        <p><strong>URL:</strong> {alert.get('url', 'N/A')}</p>
        <p><strong>Description:</strong> {alert.get('description', 'No description available')}</p>
        <p><strong>Solution:</strong> {alert.get('solution', 'No solution provided')}</p>
    </div>
"""

        html += """
</body>
</html>
"""

        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✅ HTML report generated: {output_file}")
        return 0

    except Exception as e:
        print(f"❌ Error generating report: {str(e)}")
        return 1

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python report-html.py <alerts.json> [output.html]")
        sys.exit(1)

    alerts_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'zap-report.html'

    sys.exit(generate_html_report(alerts_file, output_file))
