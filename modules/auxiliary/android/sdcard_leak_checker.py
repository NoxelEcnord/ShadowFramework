import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/sdcard_leak_checker',
        'description': 'Scans for CVE-2024-43093 (ExternalStorageProvider path filter bypass) allowing access to sensitive directories.',
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

        # Check Android Version
        ver = subprocess.run(['adb', '-s', dev, 'shell', 'getprop', 'ro.build.version.release'], capture_output=True, text=True).stdout.strip()
        console.print(f"[*] Android Version: [cyan]{ver}[/cyan]")

        affected_versions = ['12', '12L', '13', '14', '15']
        if ver in affected_versions or any(v in ver for v in affected_versions):
            console.print("[yellow][!] Version is in the affected range (12-15).[/yellow]")
            
            patch = subprocess.run(['adb', '-s', dev, 'shell', 'getprop', 'ro.build.version.security_patch'], capture_output=True, text=True).stdout.strip()
            console.print(f"[*] Patch Level: [cyan]{patch}[/cyan]")
            
            if patch and patch < "2024-11-05":
                console.print("[bold red][CRITICAL] Device is likely VULNERABLE to CVE-2024-43093.[/bold red]")
                console.print("[dim]Use exploit/android/cve_2024_43093_path_bypass to test.[/dim]")
                log_action(f"CVE-2024-43093 risk detected on {dev}")
            else:
                console.print("[green][+] Device is patched (requires 2024-11-05 or newer).[/green]")
        else:
            console.print("[green][+] Device version not known to be affected.[/green]")
