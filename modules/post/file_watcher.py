"""
ShadowFramework — File Watcher
Real-time filesystem monitoring using inotify (Linux) or polling fallback.
"""
import os
import time
import threading
import hashlib
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()


class Module:
    MODULE_INFO = {
        'name': 'post/file_watcher',
        'description': 'Monitor directories for file changes in real-time using inotify or polling.',
        'options': {
            'WATCH_PATH': 'Directory to monitor [default: /tmp]',
            'RECURSIVE':  'Watch subdirectories [default: true]',
            'DURATION':   'Monitor duration in seconds (0=until Ctrl-C) [default: 60]',
            'PATTERN':    'Filename pattern to watch [default: *]',
            'EXFIL':      'Auto-exfil new/modified files to loot/ [default: false]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self._stop = False

    def _get_file_hash(self, path):
        try:
            return hashlib.md5(open(path, 'rb').read()).hexdigest()[:12]
        except Exception:
            return '?'

    def _snapshot(self, watch_path, recursive):
        """Take a snapshot of files and their metadata."""
        snap = {}
        root = Path(watch_path)
        try:
            iterator = root.rglob('*') if recursive else root.glob('*')
            for p in iterator:
                try:
                    stat = p.stat()
                    snap[str(p)] = (stat.st_mtime, stat.st_size)
                except (PermissionError, OSError):
                    continue
        except Exception:
            pass
        return snap

    def _try_inotify(self, watch_path, recursive, duration, pattern):
        """Use inotifywait for real-time monitoring (much more efficient)."""
        import subprocess
        
        cmd = ['inotifywait', '-m', '-e', 'create,modify,delete,moved_to,moved_from']
        if recursive:
            cmd.append('-r')
        cmd.append(watch_path)
        
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            start = time.time()
            events = 0
            
            for line in iter(proc.stdout.readline, ''):
                if self._stop or (duration > 0 and time.time() - start > duration):
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    path, event_type, filename = parts[0], parts[1], parts[2] if len(parts) > 2 else ''
                    
                    # Pattern filter
                    if pattern != '*':
                        import fnmatch
                        if not fnmatch.fnmatch(filename, pattern):
                            continue

                    events += 1
                    color = 'green' if 'CREATE' in event_type else 'yellow' if 'MODIFY' in event_type else 'red'
                    console.print(f"  [{color}]{event_type}[/{color}] {path}{filename}")
                    log_action(f"File event: {event_type} {path}{filename}")
                    
            proc.kill()
            return events
        except FileNotFoundError:
            return -1  # inotifywait not installed

    def _poll_monitor(self, watch_path, recursive, duration, pattern):
        """Polling-based file monitoring fallback."""
        console.print("[dim]  (using polling mode — install inotify-tools for real-time)[/dim]")
        
        import fnmatch
        prev_snap = self._snapshot(watch_path, recursive)
        start = time.time()
        events = 0

        while not self._stop:
            if duration > 0 and (time.time() - start) > duration:
                break
            
            time.sleep(1)
            curr_snap = self._snapshot(watch_path, recursive)

            # New files
            for path in set(curr_snap) - set(prev_snap):
                if pattern != '*' and not fnmatch.fnmatch(Path(path).name, pattern):
                    continue
                console.print(f"  [green]CREATE[/green] {path}")
                events += 1
                log_action(f"File created: {path}")

            # Deleted files
            for path in set(prev_snap) - set(curr_snap):
                if pattern != '*' and not fnmatch.fnmatch(Path(path).name, pattern):
                    continue
                console.print(f"  [red]DELETE[/red] {path}")
                events += 1

            # Modified files
            for path in set(curr_snap) & set(prev_snap):
                if curr_snap[path] != prev_snap[path]:
                    if pattern != '*' and not fnmatch.fnmatch(Path(path).name, pattern):
                        continue
                    console.print(f"  [yellow]MODIFY[/yellow] {path} (size: {curr_snap[path][1]})")
                    events += 1

            prev_snap = curr_snap

        return events

    def run(self):
        watch_path = self.framework.options.get('WATCH_PATH', '/tmp')
        recursive = self.framework.options.get('RECURSIVE', 'true').lower() == 'true'
        duration = int(self.framework.options.get('DURATION', '60'))
        pattern = self.framework.options.get('PATTERN', '*')
        exfil = self.framework.options.get('EXFIL', 'false').lower() == 'true'

        if not os.path.isdir(watch_path):
            console.print(f"[red][!] Directory not found: {watch_path}[/red]")
            return

        console.print(f"[cyan][*] Watching: {watch_path} (recursive={recursive}, pattern={pattern})[/cyan]")
        log_action(f"File watcher started: {watch_path}")

        # Try inotify first
        result = self._try_inotify(watch_path, recursive, duration, pattern)
        
        if result == -1:
            # Fallback to polling
            try:
                result = self._poll_monitor(watch_path, recursive, duration, pattern)
            except KeyboardInterrupt:
                self._stop = True

        console.print(f"\n[bold green][+] Monitoring complete. {result} events captured.[/bold green]")
