"""
ShadowFramework — Report Generator
Generates HTML and optional PDF reports from scan/exploit results.
PDF requires pdfkit + wkhtmltopdf, gracefully falls back to HTML-only.
"""
import os
import json
from pathlib import Path
from datetime import datetime
from rich.console import Console

console = Console()

# Optional PDF support
try:
    import pdfkit
    HAS_PDFKIT = True
except ImportError:
    HAS_PDFKIT = False


class ReportGenerator:
    def __init__(self, output_dir=None):
        self.reports_dir = Path(output_dir) if output_dir else Path("~/.shadow/reports").expanduser()
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def _build_html(self, title, content, sections=None):
        """Build a styled HTML report."""
        section_html = ""
        if sections:
            for heading, body in sections:
                section_html += f"<h2>{heading}</h2><pre>{body}</pre>\n"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0d1117; color: #c9d1d9; padding: 20px; }}
        h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        h2 {{ color: #79c0ff; margin-top: 20px; }}
        pre {{ background: #161b22; padding: 12px; border-radius: 6px; overflow-x: auto;
               border: 1px solid #30363d; font-size: 13px; line-height: 1.5; }}
        .meta {{ color: #8b949e; font-size: 12px; margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #30363d; padding: 8px 12px; text-align: left; }}
        th {{ background: #161b22; color: #58a6ff; }}
        .success {{ color: #3fb950; }} .warning {{ color: #d29922; }} .danger {{ color: #f85149; }}
    </style>
</head>
<body>
    <h1>🛡️ {title}</h1>
    <div class="meta">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ShadowFramework</div>
    <div>{content}</div>
    {section_html}
</body>
</html>"""

    def generate_html_report(self, title, content, sections=None, output_file=None):
        """Generate a styled HTML report.
        
        Args:
            title: Report title
            content: Main HTML content  
            sections: Optional list of (heading, body) tuples
            output_file: Output path (auto-generated if None)
        Returns:
            Path to generated file
        """
        try:
            if not output_file:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = self.reports_dir / f"report_{ts}.html"
            
            html = self._build_html(title, content, sections)
            
            with open(output_file, 'w') as f:
                f.write(html)
            
            console.print(f"[green][+] HTML report generated: {output_file}[/green]")
            return output_file
        except Exception as e:
            console.print(f"[red][!] Error generating HTML report: {e}[/red]")
            return None

    def generate_pdf_report(self, title, content, sections=None, output_file=None):
        """Generate a PDF report (requires pdfkit + wkhtmltopdf)."""
        if not HAS_PDFKIT:
            console.print("[yellow][!] pdfkit not installed. Install with: pip install pdfkit[/yellow]")
            console.print("[yellow]    Also requires wkhtmltopdf: apt install wkhtmltopdf[/yellow]")
            console.print("[*] Falling back to HTML report...")
            return self.generate_html_report(title, content, sections, 
                                             output_file=str(output_file).replace('.pdf', '.html') if output_file else None)
        try:
            if not output_file:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = self.reports_dir / f"report_{ts}.pdf"
            
            html = self._build_html(title, content, sections)
            pdfkit.from_string(html, str(output_file))
            
            console.print(f"[green][+] PDF report generated: {output_file}[/green]")
            return output_file
        except Exception as e:
            console.print(f"[red][!] PDF generation failed: {e}[/red]")
            console.print("[*] Falling back to HTML report...")
            return self.generate_html_report(title, content, sections)

    def generate_json_report(self, title, data, output_file=None):
        """Export structured data as JSON."""
        try:
            if not output_file:
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = self.reports_dir / f"report_{ts}.json"
            
            report = {
                'title': title,
                'generated': datetime.now().isoformat(),
                'framework': 'ShadowFramework',
                'data': data,
            }
            
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            console.print(f"[green][+] JSON report generated: {output_file}[/green]")
            return output_file
        except Exception as e:
            console.print(f"[red][!] Error generating JSON report: {e}[/red]")
            return None