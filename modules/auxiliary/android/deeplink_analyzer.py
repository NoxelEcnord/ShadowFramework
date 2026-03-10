import subprocess
import re
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/deeplink_analyzer',
        'description': 'Extracts custom URL schemes and deep link patterns from a target application\'s manifest.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'PACKAGE': 'Package to analyze',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        pkg = self.framework.options.get('PACKAGE', '')

        if not pkg:
            console.print("[red][!] PACKAGE is required.[/red]")
            return

        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = [l.split('\t')[0] for l in r.stdout.strip().splitlines()[1:] if 'device' in l]
        if not devices: return
        dev = device_id if device_id in devices else devices[0]

        console.print(f"[*] Extracting deep links from [cyan]{pkg}[/cyan]...")
        log_action(f"Deep link analysis on {pkg}")

        # Use dumpsys to find Intent Filters
        res = subprocess.run(['adb', '-s', dev, 'shell', 'dumpsys', 'package', pkg], capture_output=True, text=True)
        
        # Regex for schemes and hosts
        schemes = re.findall(r'scheme="([^"]+)"', res.stdout)
        hosts = re.findall(r'host="([^"]+)"', res.stdout)
        
        found = list(set(schemes))
        if found:
            console.print("[bold green][+] Found Custom URL Schemes:[/bold green]")
            for s in found:
                console.print(f"  [cyan]→ {s}://[/cyan]")
            
            if hosts:
                console.print("[bold yellow][+] Potential Deep Link Entry Points:[/bold yellow]")
                for h in set(hosts):
                    console.print(f"  [dim]→ https://{h}/[/dim]")
            
            log_action(f"Found {len(found)} schemes for {pkg}")
        else:
            console.print("[yellow][*] No custom schemes found. App may use standard Android App Links (Verified).[/yellow]")
