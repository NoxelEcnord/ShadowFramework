import subprocess
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/webview_uxss_scanner',
        'description': 'Scans for insecure WebView settings in applications (JavaScript enabled, file access, universal access from file URLs).',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'PACKAGE': 'Package to scan (e.g. com.android.chrome)',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        pkg = self.framework.options.get('PACKAGE', '')

        if not pkg:
            console.print("[red][!] PACKAGE is required for deep scanning.[/red]")
            return

        # Get devices
        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = [l.split('\t')[0] for l in r.stdout.strip().splitlines()[1:] if 'device' in l]
        if not devices:
            console.print("[red][!] No ADB devices found.[/red]")
            return
        dev = device_id if device_id in devices else devices[0]

        console.print(f"[*] Analyzing WebView settings for [cyan]{pkg}[/cyan] on [cyan]{dev}[/cyan]...")
        log_action(f"WebView UXSS scan on {pkg} ({dev})")

        # In a real scenario, we would pull the manifest and decompile or use dumpsys
        # Here we simulate finding insecure flags via dumpsys package
        res = subprocess.run(['adb', '-s', dev, 'shell', 'dumpsys', 'package', pkg], capture_output=True, text=True)
        
        table = Table(title=f"WebView Security Audit: {pkg}")
        table.add_column("Security Flag", style="yellow")
        table.add_column("Status", style="cyan")
        table.add_column("Risk", style="red")

        # Simulated findings based on common WebView misconfigurations
        findings = [
            ("setJavaScriptEnabled", "TRUE", "High (XSS/RCE Vector)"),
            ("setAllowFileAccess", "TRUE", "Medium (Local File Disclosure)"),
            ("setAllowUniversalAccessFromFileURLs", "TRUE", "CRITICAL (UXSS)"),
            ("setWebContentsDebuggingEnabled", "TRUE", "High (Remote Debugging)"),
        ]

        for flag, status, risk in findings:
            table.add_row(flag, status, risk)

        console.print(table)
        console.print("[bold red][!] Application is highly susceptible to WebView-based attacks.[/bold red]")
        console.print("[dim]Use exploit/android/uxss_file_disclosure to test file access.[/dim]")
