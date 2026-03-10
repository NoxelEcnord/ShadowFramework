import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/qualcomm_gfx_check',
        'description': 'Check for vulnerable Qualcomm chipsets (CVE-2026-21385) targeting graphics/display components.',
        'options': {
            'DEVICE_ID': 'Target device serial',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        
        # Get devices
        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = [l.split('\t')[0] for l in r.stdout.strip().splitlines()[1:] if 'device' in l]
        if not devices:
            console.print("[red][!] No ADB devices found.[/red]")
            return
        
        dev = device_id if device_id in devices else devices[0]
        console.print(f"[*] Checking device: [cyan]{dev}[/cyan]")

        # Check Qualcomm hardware
        hw = subprocess.run(['adb', '-s', dev, 'shell', 'getprop', 'ro.board.platform'], capture_output=True, text=True).stdout.strip()
        console.print(f"[*] Hardware Platform: [yellow]{hw}[/yellow]")

        if any(q in hw.lower() for q in ['msm', 'sdm', 'sm', 'qcom']):
            console.print("[bold yellow][!] Device uses Qualcomm chipset. Potential risk for CVE-2026-21385.[/bold yellow]")
            
            # Check security patch level
            patch = subprocess.run(['adb', '-s', dev, 'shell', 'getprop', 'ro.build.version.security_patch'], capture_output=True, text=True).stdout.strip()
            console.print(f"[*] Security Patch Level: [cyan]{patch}[/cyan]")
            
            if patch and patch < "2026-03-05":
                console.print("[bold red][CRITICAL] Device is VULNERABLE to CVE-2026-21385 (Qualcomm GFX overflow).[/bold red]")
                log_action(f"CVE-2026-21385 vulnerability detected on {dev}")
            else:
                console.print("[green][+] Device is likely patched (requires 2026-03-05 or newer).[/green]")
        else:
            console.print("[green][+] Hardware is non-Qualcomm or not recognized as vulnerable.[/green]")
