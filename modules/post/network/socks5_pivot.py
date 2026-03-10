"""
ShadowFramework — SOCKS5 Pivot Module
Turns a compromised host (Android/Linux) into a SOCKS5 proxy server.
This allows the operator to route all their local tools (Nmap, Browser, etc.) 
through the target device's network.
"""
import socket
import threading
import select
import struct
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/network/socks5_pivot',
        'description': 'Starts a SOCKS5 proxy server on the local machine that routes traffic through the target.',
        'options': {
            'LHOST': 'Local bind address [default: 0.0.0.0]',
            'LPORT': 'Local SOCKS5 port [default: 1080]',
            'DEVICE_ID': 'Target device (if using ADB pivot)',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self.running = False

    def _handle_client(self, client):
        """Handle SOCKS5 negotiation."""
        try:
            # 1. Version and Auth
            version, nmethods = struct.unpack('!BB', client.recv(2))
            methods = client.recv(nmethods)
            client.sendall(struct.pack('!BB', 0x05, 0x00)) # No auth

            # 2. Request
            version, cmd, _, address_type = struct.unpack('!BBBB', client.recv(4))
            
            if address_type == 1: # IPv4
                address = socket.inet_ntoa(client.recv(4))
            elif address_type == 3: # Domain
                domain_length = client.recv(1)[0]
                address = client.recv(domain_length).decode()
            
            port = struct.unpack('!H', client.recv(2))[0]

            # 3. Connection
            if cmd == 1: # CONNECT
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.connect((address, port))
                bind_address = remote.getsockname()
                
                # Send success response
                addr = struct.unpack("!I", socket.inet_aton(bind_address[0]))[0]
                client.sendall(struct.pack('!BBBBIH', 0x05, 0x00, 0x00, 0x01, addr, bind_address[1]))

                # 4. Data Transfer
                self._proxy_data(client, remote)
            else:
                client.close()
        except Exception:
            client.close()

    def _proxy_data(self, client, remote):
        """Relay traffic between client and remote."""
        sockets = [client, remote]
        while True:
            r, w, e = select.select(sockets, [], [])
            if client in r:
                data = client.recv(4096)
                if remote.send(data) <= 0: break
            if remote in r:
                data = remote.recv(4096)
                if client.send(data) <= 0: break

    def run(self):
        lhost = self.framework.options.get('LHOST', '0.0.0.0')
        lport = int(self.framework.options.get('LPORT', '1080'))
        
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((lhost, lport))
            server.listen(100)
            console.print(f"[bold green][+] SOCKS5 Pivot active on {lhost}:{lport}[/bold green]")
            console.print(f"[cyan][*] Configure your browser/tools to use SOCKS5 proxy at {lhost}:{lport}[/cyan]")
            log_action(f"SOCKS5 Pivot started on {lhost}:{lport}")
            
            self.running = True
            while self.running:
                client, addr = server.accept()
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
        except KeyboardInterrupt:
            console.print("\n[yellow][!] SOCKS5 Pivot stopped.[/yellow]")
        except Exception as e:
            console.print(f"[red][!] Error: {e}[/red]")
        finally:
            server.close()
