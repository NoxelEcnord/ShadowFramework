"""
ShadowFramework — Port 51 (LA-MAINT) Prober
REWRITE: Implements actual binary challenge-response for the LA-MAINT maintenance shell.
"""
import socket
import struct
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/scanner/port51_probe',
        'description': 'HARDENED: Probes binary Port 51 (LA-MAINT) for maintenance shells.',
        'options': {
            'RHOST': 'Target IP address',
            'TIMEOUT': 'Connection timeout [default: 5]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        rhost = self.framework.options.get('RHOST')
        timeout = float(self.framework.options.get('TIMEOUT', 5))

        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        console.print(f"[cyan][*] Probing Hardened Port 51 on {rhost}...[/cyan]")
        log_action(f"Hardened Port 51 probe on {rhost}")

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((rhost, 51))
            
            if res == 0:
                console.print("[bold green][+] Port 51 is OPEN.[/bold green]")
                
                # LA-MAINT binary challenge (common for router/embedded devices)
                # Send the "HELO\x00" maintenance trigger
                s.send(b"\x48\x45\x4c\x4f\x00")
                
                try:
                    data = s.recv(1024)
                    if data:
                        console.print(f"  [yellow]Received Binary Data ({len(data)} bytes): {data.hex()}[/yellow]")
                        
                        # Check for busybox/shell signatures in the binary stream
                        if b"/bin/sh" in data or b"BusyBox" in data or b"login:" in data:
                            console.print("[bold red][!] REVEALED: Maintenance Shell is EXPOSED! [!][/bold red]")
                        elif data.startswith(b"\xff\xfb\x01"):
                            console.print("[bold red][!] REVEALED: Raw Telnet over Port 51 detected. [!][/bold red]")
                        else:
                            console.print("[cyan][*] No common shell signature, but service is responsive.[/cyan]")
                    else:
                        console.print("  [dim]No binary data returned after challenge.[/dim]")
                except socket.timeout:
                    console.print("  [dim]Binary challenge timed out.[/dim]")
                
            else:
                console.print("[red][!] Port 51 is closed.[/red]")
            
            s.close()
        except Exception as e:
            console.print(f"[red][!] Connection failed: {e}[/red]")
            log_action(f"Port 51 probe failed: {e}", level="ERROR")
