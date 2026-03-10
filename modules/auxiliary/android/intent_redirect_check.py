import subprocess
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/intent_redirect_check',
        'description': 'Audits exported activities/services for potential blind intent redirection vulnerabilities.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'PACKAGE': 'Package to audit',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        pkg = self.framework.options.get('PACKAGE', '')

        if not pkg: return

        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = [l.split('\t')[0] for l in r.stdout.strip().splitlines()[1:] if 'device' in l]
        if not devices: return
        dev = device_id if device_id in devices else devices[0]

        console.print(f"[*] Auditing components in [cyan]{pkg}[/cyan] for IPC flaws...")
        log_action(f"Intent redirect audit on {pkg}")

        res = subprocess.run(['adb', '-s', dev, 'shell', 'dumpsys', 'package', pkg], capture_output=True, text=True)
        
        table = Table(title=f"Exported Components: {pkg}")
        table.add_column("Component", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Exposed", style="red")

        found = 0
        for line in res.stdout.splitlines():
            if "Activity" in line or "Service" in line or "Receiver" in line:
                if "exported=true" in line or "filter [" in line:
                    comp_name = line.strip().split()[1] if len(line.strip().split()) > 1 else line.strip()
                    comp_type = "Activity" if "Activity" in line else "Service" if "Service" in line else "Receiver"
                    table.add_row(comp_name, comp_type, "YES")
                    found += 1
        
        if found:
            console.print(table)
            console.print(f"[bold red][!] Found {found} exported components.[/bold red]")
            console.print("[dim]Analyze these components for startActivity() or sendBroadcast() calls that forward untrusted Intents.[/dim]")
            log_action(f"Found {found} exported components in {pkg}")
        else:
            console.print("[green][+] No exported components found (secure by default).[/green]")
