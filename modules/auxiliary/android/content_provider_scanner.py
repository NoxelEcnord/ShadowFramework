import subprocess
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/content_provider_scanner',
        'description': 'Scans for exported content providers and potential information disclosure (CVE-2026-0024).',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'PACKAGE': 'Specific package to scan (optional)',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        pkg = self.framework.options.get('PACKAGE', '')

        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = [l.split('\t')[0] for l in r.stdout.strip().splitlines()[1:] if 'device' in l]
        if not devices:
            console.print("[red][!] No ADB devices found.[/red]")
            return
        dev = device_id if device_id in devices else devices[0]

        console.print(f"[*] Scanning providers on: [cyan]{dev}[/cyan]")
        
        # Get all providers
        cmd = ['adb', '-s', dev, 'shell', 'dumpsys', 'package', 'providers']
        if pkg:
            cmd += [pkg]
        
        res = subprocess.run(cmd, capture_output=True, text=True)
        
        table = Table(title="Exported Content Providers")
        table.add_column("Package", style="cyan")
        table.add_column("Authority", style="yellow")
        table.add_column("Permissions", style="red")

        found = 0
        current_pkg = ""
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.startswith("Package ["):
                current_pkg = line.split("[")[1].split("]")[0]
            if "authority=" in line:
                auth = line.split("authority=")[1].split()[0]
                if "readPermission=null" in line or "writePermission=null" in line:
                    table.add_row(current_pkg, auth, "NONE / INSECURE")
                    found += 1
        
        if found > 0:
            console.print(table)
            console.print(f"[bold red][!] Found {found} insecure/exported providers.[/bold red]")
            log_action(f"Content provider scan: {found} insecure providers on {dev}")
        else:
            console.print("[green][+] No insecure exported providers detected.[/green]")
