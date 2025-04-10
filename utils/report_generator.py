import os
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style
import pdfkit  # For PDF generation (install with `pip install pdfkit`)

class ReportGenerator:
    def __init__(self):
        """
        Initialize the report generator.
        """
        self.reports_dir = Path("~/.shadow/reports").expanduser()
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(self, title, content, output_file=None):
        """
        Generate an HTML report.

        Args:
            title: The title of the report.
            content: The content of the report (HTML format).
            output_file: Path to the output HTML file. If None, a random name will be generated.

        Returns:
            Path to the generated HTML file.
        """
        try:
            if not output_file:
                output_file = self.reports_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

            # Create the HTML report
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{title}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    h1 {{ color: #333; }}
                    pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>{title}</h1>
                <div>{content}</div>
            </body>
            </html>
            """

            with open(output_file, "w") as f:
                f.write(html)

            print(f"{Fore.GREEN}[+] HTML report generated: {output_file}{Style.RESET_ALL}")
            return output_file

        except Exception as e:
            print(f"{Fore.RED}[!] Error generating HTML report: {e}{Style.RESET_ALL}")
            return None

    def generate_pdf_report(self, title, content, output_file=None):
        """
        Generate a PDF report.

        Args:
            title: The title of the report.
            content: The content of the report (HTML format).
            output_file: Path to the output PDF file. If None, a random name will be generated.

        Returns:
            Path to the generated PDF file.
        """
        try:
            if not output_file:
                output_file = self.reports_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            # Generate HTML content
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{title}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    h1 {{ color: #333; }}
                    pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>{title}</h1>
                <div>{content}</div>
            </body>
            </html>
            """

            # Convert HTML to PDF
            pdfkit.from_string(html, str(output_file))

            print(f"{Fore.GREEN}[+] PDF report generated: {output_file}{Style.RESET_ALL}")
            return output_file

        except Exception as e:
            print(f"{Fore.RED}[!] Error generating PDF report: {e}{Style.RESET_ALL}")
            return None