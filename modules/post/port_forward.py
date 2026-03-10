import socket
import threading
import select
import time
import os
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/port_forward',
        'description': 'Local-to-remote TCP port forwarding. Relay traffic from local port to remote host:port.',
        'options': {
            'LHOST': 'Local bind address [default: 0.0.0.0]',
            'LPORT': 'Local port to listen on',
            'RHOST': 'Remote host to forward traffic to',
            'RPORT': 'Remote port to forward traffic to',
            'DURATION': 'How long to run in seconds (0 = until Ctrl+C) [default: 0]',
            'BUFFER': 'Buffer size in bytes [default: 4096]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self._running = False

    def _forward(self, client_sock, rhost, rport, buffer_size):
        """Forward data between client and remote server."""
        try:
            remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_sock.connect((rhost, rport))
        except Exception as e:
            console.print(f"  [red][!] Cannot connect to {rhost}:{rport} — {e}[/red]")
            client_sock.close()
            return

        client_addr = client_sock.getpeername()
        console.print(f"  [green][+] Connection from {client_addr} → {rhost}:{rport}[/green]")
        log_action(f"PortForward: {client_addr} → {rhost}:{rport}")

        sockets = [client_sock, remote_sock]
        try:
            while True:
                r, _, _ = select.select(sockets, [], [], 5)
                if not r:
                    continue
                for s in r:
                    data = s.recv(buffer_size)
                    if not data:
                        return
                    target = remote_sock if s is client_sock else client_sock
                    target.sendall(data)
        except Exception:
            pass
        finally:
            client_sock.close()
            remote_sock.close()

    def run(self):
        lhost = self.framework.options.get('LHOST', '0.0.0.0')
        lport = self.framework.options.get('LPORT')
        rhost = self.framework.options.get('RHOST')
        rport = self.framework.options.get('RPORT')
        duration = float(self.framework.options.get('DURATION', 0))
        buffer_size = int(self.framework.options.get('BUFFER', 4096))

        if not lport or not rhost or not rport:
            console.print("[red][!] LPORT, RHOST, and RPORT are required.[/red]")
            return

        lport = int(lport)
        rport = int(rport)

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((lhost, lport))
            server.listen(10)
        except Exception as e:
            console.print(f"[red][!] Bind failed: {e}[/red]")
            return

        console.print(f"[bold green][+] Port forward: {lhost}:{lport} → {rhost}:{rport}[/bold green]")
        console.print("[dim]Press Ctrl+C to stop.[/dim]")
        log_action(f"Port forward started: {lhost}:{lport} → {rhost}:{rport}")

        self._running = True
        server.settimeout(1)
        start = time.time()

        try:
            while self._running:
                if duration > 0 and (time.time() - start) > duration:
                    break
                try:
                    client_sock, addr = server.accept()
                    t = threading.Thread(target=self._forward,
                                         args=(client_sock, rhost, rport, buffer_size),
                                         daemon=True)
                    t.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            console.print("\n[yellow][!] Port forward stopped.[/yellow]")
        finally:
            server.close()
