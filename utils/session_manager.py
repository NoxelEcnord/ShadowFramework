"""
ShadowFramework — Session Manager
Manages device connections and active exploitation sessions.
"""
import time
from rich.console import Console
from rich.table import Table

console = Console()


class SessionManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.devices = {}
        self.sessions = []
        self._next_session_id = 1

    def add_device(self, ip_address, serial, rooted=False, info=None):
        """Add a new device."""
        device_id = f"#{len(self.devices) + 1}"
        self.devices[device_id] = {
            'ip': ip_address,
            'serial': serial,
            'rooted': rooted,
            'info': info or {},
            'added': time.strftime('%H:%M:%S'),
        }
        console.print(f"[green][+] Added device: {device_id} ({ip_address})[/green]")
        return device_id

    def get_devices(self):
        return self.devices

    def add_session(self, device_id, module_name, output, session_type='exploit'):
        """Add a new session."""
        if device_id not in self.devices and device_id != 'local':
            console.print(f"[red][!] Device not found: {device_id}[/red]")
            return None

        session_id = self._next_session_id
        self._next_session_id += 1
        session = {
            'id': session_id,
            'device_id': device_id,
            'module_name': module_name,
            'output': output,
            'type': session_type,
            'opened': time.strftime('%H:%M:%S'),
        }
        self.sessions.append(session)
        console.print(f"[green][+] Session #{session_id} opened ({module_name})[/green]")
        return session_id

    def get_sessions(self):
        return self.sessions

    def get_device_info(self, device_id):
        return self.devices.get(device_id)

    def list_devices(self):
        if not self.devices:
            console.print("[yellow][!] No devices connected.[/yellow]")
            return

        table = Table(title="Connected Devices")
        table.add_column("ID", style="cyan")
        table.add_column("IP", style="white")
        table.add_column("Serial", style="dim")
        table.add_column("Rooted", style="green")
        table.add_column("Added", style="dim")

        for device_id, info in self.devices.items():
            rooted = "✓" if info['rooted'] else "✗"
            table.add_row(device_id, info['ip'], info['serial'], rooted, info.get('added', ''))

        console.print(table)

    def list_sessions(self):
        if not self.sessions:
            console.print("[yellow][!] No active sessions.[/yellow]")
            return

        table = Table(title="Active Sessions")
        table.add_column("ID", style="cyan")
        table.add_column("Device", style="white")
        table.add_column("Module", style="green")
        table.add_column("Type", style="dim")
        table.add_column("Opened", style="dim")

        for session in self.sessions:
            table.add_row(
                str(session['id']),
                session['device_id'],
                session['module_name'],
                session.get('type', 'exploit'),
                session.get('opened', ''),
            )

        console.print(table)

    def close_session(self, session_id):
        for session in self.sessions:
            if session['id'] == session_id:
                self.sessions.remove(session)
                console.print(f"[green][+] Closed session #{session_id}[/green]")
                return True
        console.print(f"[red][!] Session not found: {session_id}[/red]")
        return False

    def remove_device(self, device_id):
        if device_id in self.devices:
            del self.devices[device_id]
            console.print(f"[green][+] Removed device: {device_id}[/green]")
            return True
        console.print(f"[red][!] Device not found: {device_id}[/red]")
        return False
