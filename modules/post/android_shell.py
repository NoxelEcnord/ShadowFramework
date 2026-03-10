import subprocess
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
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
        'name': 'post/android_shell',
        'description': 'Interactive ADB shell, remote command runner, and file push/pull manager.',
        'options': {
            'DEVICE_ID': 'Target device serial',
            'ACTION': 'Action: shell, exec, push, pull, root_check, app_kill [default: shell]',
            'COMMAND': 'Command to run for exec action',
            'LOCAL_PATH': 'Local file path for push/pull',
            'REMOTE_PATH': 'Remote device path for push/pull',
            'APP_PACKAGE': 'Package name to kill for app_kill action',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _interactive_shell(self, dev):
        console.print(f"[green][+] Dropping into interactive ADB shell on {dev}...[/green]")
        console.print("[dim]Type 'exit' to return to Shadow.[/dim]")
        log_action(f"Interactive ADB shell on {dev}")
        os.system(f"adb -s {dev} shell")

    def _exec(self, dev, command):
        console.print(f"[cyan][*] Executing: {command}[/cyan]")
        out = _shell(dev, command)
        console.print(out)
        log_action(f"ADB exec on {dev}: {command}")
        return out

    def _root_check(self, dev):
        console.print(f"[cyan][*] Checking root status on {dev}...[/cyan]")
        uid_out = _shell(dev, 'id')
        su_out, su_err = _adb(dev, 'shell', 'su -c id')
        magisk = _shell(dev, 'which magisk')
        supersu = _shell(dev, 'ls /system/xbin/su 2>/dev/null')

        table = Table(title="Root Status")
        table.add_column("Check", style="cyan")
        table.add_column("Result", style="green")
        table.add_row("Current UID", uid_out)
        table.add_row("su -c id", su_out or f"[red]{su_err}[/red]")
        table.add_row("magisk", magisk or "not found")
        table.add_row("/system/xbin/su", supersu or "not found")
        console.print(table)

        is_rooted = (uid_out and 'uid=0' in su_out) or bool(magisk) or bool(supersu)
        if is_rooted:
            console.print("[bold green][+] Device is ROOTED.[/bold green]")
        else:
            console.print("[yellow][!] Device does not appear rooted.[/yellow]")
        log_action(f"Root check on {dev}: rooted={is_rooted}")

    def _push(self, dev, local, remote):
        if not os.path.exists(local):
            console.print(f"[red][!] Local file not found: {local}[/red]")
            return
        console.print(f"[cyan][*] Pushing {local} → {dev}:{remote}...[/cyan]")
        out, err = _adb(dev, 'push', local, remote)
        console.print(out or err)
        log_action(f"ADB push: {local} → {dev}:{remote}")

    def _pull(self, dev, remote, local):
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        console.print(f"[cyan][*] Pulling {dev}:{remote} → {local}...[/cyan]")
        out, err = _adb(dev, 'pull', remote, local)
        console.print(out or err)
        log_action(f"ADB pull: {dev}:{remote} → {local}")

    def _app_kill(self, dev, package):
        console.print(f"[cyan][*] Force-stopping {package}...[/cyan]")
        out = _shell(dev, f'am force-stop {package}')
        console.print(f"[green][+] {package} force-stopped.[/green]")
        log_action(f"app_kill: {package} on {dev}")

    def run(self):
        device_id = self.framework.options.get('DEVICE_ID', '')
        action = self.framework.options.get('ACTION', 'shell').lower()
        command = self.framework.options.get('COMMAND', '')
        local_path = self.framework.options.get('LOCAL_PATH', '')
        remote_path = self.framework.options.get('REMOTE_PATH', '/sdcard/')
        package = self.framework.options.get('APP_PACKAGE', '')

        if not device_id:
            console.print("[red][!] DEVICE_ID is required.[/red]")
            return

        if action == 'shell':
            self._interactive_shell(device_id)
        elif action == 'exec':
            if not command:
                console.print("[red][!] COMMAND is required for exec action.[/red]")
                return
            self._exec(device_id, command)
        elif action == 'root_check':
            self._root_check(device_id)
        elif action == 'push':
            self._push(device_id, local_path, remote_path)
        elif action == 'pull':
            self._pull(device_id, remote_path, local_path or f'loot/{os.path.basename(remote_path)}')
        elif action == 'app_kill':
            if not package:
                console.print("[red][!] APP_PACKAGE is required.[/red]")
                return
            self._app_kill(device_id, package)
        else:
            console.print(f"[red][!] Unknown action: {action}. Use: shell, exec, push, pull, root_check, app_kill[/red]")
