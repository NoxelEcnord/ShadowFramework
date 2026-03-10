import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/f2fs_checker',
        'description': 'Checks if the device uses Flash-Friendly File System (F2FS) which is vulnerable to CVE-2024-43859.',
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

        console.print(f"[*] Checking filesystem on: [cyan]{dev}[/cyan]")
        
        # Check mount points for f2fs
        mounts = subprocess.run(['adb', '-s', dev, 'shell', 'mount'], capture_output=True, text=True).stdout
        
        f2fs_mounts = [line for line in mounts.splitlines() if 'f2fs' in line]
        
        if f2fs_mounts:
            console.print("[bold yellow][!] F2FS filesystem detected on the following partitions:[/bold yellow]")
            for m in f2fs_mounts:
                console.print(f"  [cyan]→ {m}[/cyan]")
            
            patch = subprocess.run(['adb', '-s', dev, 'shell', 'getprop', 'ro.build.version.security_patch'], capture_output=True, text=True).stdout.strip()
            console.print(f"[*] Patch Level: [cyan]{patch}[/cyan]")
            
            if patch and patch < "2024-12-05":
                console.print("[bold red][CRITICAL] Device uses vulnerable F2FS (patch < 2024-12-05).[/bold red]")
                log_action(f"F2FS vulnerability risk (CVE-2024-43859) on {dev}")
            else:
                console.print("[green][+] Device is likely patched for F2FS flaws.[/green]")
        else:
            console.print("[green][+] F2FS not found on active mount points.[/green]")
