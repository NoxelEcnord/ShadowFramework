import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/network_scan_cve_2024_36971',
        'description': 'Scans for CVE-2024-36971 (Kernel Use-After-Free in network route management).',
        'options': {
            'DEVICE_ID': 'Target device serial',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')

        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = [l.split('\t')[0] for l in r.stdout.strip().splitlines()[1:] if 'device' in l]
        if not devices:
            console.print("[red][!] No ADB devices found.[/red]")
            return
        dev = device_id if device_id in devices else devices[0]

        console.print(f"[*] Checking kernel/network info on: [cyan]{dev}[/cyan]")
        
        # Check kernel version via uname
        uname = subprocess.run(['adb', '-s', dev, 'shell', 'uname', '-a'], capture_output=True, text=True).stdout.strip()
        console.print(f"[*] Kernel: [cyan]{uname}[/cyan]")
        
        patch = subprocess.run(['adb', '-s', dev, 'shell', 'getprop', 'ro.build.version.security_patch'], capture_output=True, text=True).stdout.strip()
        console.print(f"[*] Patch Level: [cyan]{patch}[/cyan]")

        if patch < "2024-08-05":
            console.print("[bold red][CRITICAL] Kernel is likely VULNERABLE to CVE-2024-36971 (UAF in network stack).[/bold red]")
            log_action(f"Network UAF risk (CVE-2024-36971) on {dev}")
        else:
            console.print("[green][+] Kernel is patched against this UAF flaw.[/green]")
