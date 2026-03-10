import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/app_cloning_check',
        'description': 'Check for insecure app cloning/migration configurations (e.g. data transfer vulnerabilities).',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'PACKAGE': 'Package to check [default: com.google.android.apps.restore]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        pkg = self.framework.options.get('PACKAGE', 'com.google.android.apps.restore')

        r = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        devices = [l.split('\t')[0] for l in r.stdout.strip().splitlines()[1:] if 'device' in l]
        if not devices:
            console.print("[red][!] No ADB devices found.[/red]")
            return
        dev = device_id if device_id in devices else devices[0]

        console.print(f"[*] Checking cloning/restore configuration on: [cyan]{dev}[/cyan]")
        
        # Check permissions and manifest flags for the restore app
        res = subprocess.run(['adb', '-s', dev, 'shell', 'dumpsys', 'package', pkg], capture_output=True, text=True)
        
        if "ALLOW_BACKUP" in res.stdout or "allowBackup=true" in res.stdout:
            console.print("[yellow][!] App allows backup/restore. Potential for data cloning/seed theft.[/yellow]")
            log_action(f"App cloning risk (allowBackup) on {dev} for {pkg}")
        else:
            console.print("[green][+] App does not explicitly allow backup (modern secure default).[/green]")

        # Check for secure migration services
        if "com.android.backupconfirm" in res.stdout:
            console.print("[green][+] Confirmation service detected.[/green]")
        else:
            console.print("[bold red][!] Migration confirmation service missing or obscured.[/bold red]")
