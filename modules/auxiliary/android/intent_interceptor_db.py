import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/intent_interceptor_db',
        'description': 'Scans for broadcast receivers that might leak sensitive intents or accept unvalidated data.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'FILTER': 'Filter by keyword (e.g. "auth", "sync")',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        flt = self.framework.options.get('FILTER', '')

        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = [l.split('\t')[0] for l in r.stdout.strip().splitlines()[1:] if 'device' in l]
        if not devices:
            console.print("[red][!] No ADB devices found.[/red]")
            return
        dev = device_id if device_id in devices else devices[0]

        console.print(f"[*] Scanning receivers on: [cyan]{dev}[/cyan]")
        
        # Get all receivers
        res = subprocess.run(['adb', '-s', dev, 'shell', 'dumpsys', 'package', 'receivers'], capture_output=True, text=True)
        
        lines = res.stdout.splitlines()
        found = 0
        for i, line in enumerate(lines):
            line = line.strip()
            if "Receiver #" in line:
                # Look for 'exported=true' or missing permissions
                block = lines[i:i+10]
                content = " ".join(block)
                if "filter [" in content and (flt in content):
                    console.print(f"[yellow][!] Potential Interceptor Target:[/yellow] {line}")
                    for b_line in block[:5]:
                        console.print(f"  [dim]{b_line.strip()}[/dim]")
                    found += 1
        
        if found:
            console.print(f"\n[bold red][+] Found {found} potential intent targets.[/bold red]")
            log_action(f"Intent interception scan: {found} targets on {dev}")
        else:
            console.print("[green][+] No suspicious receivers found with current filter.[/green]")
