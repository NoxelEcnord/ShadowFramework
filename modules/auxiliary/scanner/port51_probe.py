"""
ShadowFramework — Port 51 (LA-MAINT) Prober
Investigates the mysterious Port 51 often found on local network devices.
Attempts to identify if it is a legacy maintenance port or a modern service.
"""
import socket
import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/scanner/port51_probe',
        'description': 'Probes Port 51 (LA-MAINT) to identify the underlying service/vulnerability.',
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

        console.print(f"[cyan][*] Probing Port 51 on {rhost}...[/cyan]")
        log_action(f"Port 51 probe on {rhost}")

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            res = s.connect_ex((rhost, 51))
            
            if res == 0:
                console.print("[bold green][+] Port 51 is OPEN.[/bold green]")
                
                # Try grabbing banner
                s.send(b"\r\nHELP\r\n")
                try:
                    banner = s.recv(1024).strip()
                    if banner:
                        console.print(f"  [yellow]Banner: {banner.decode(errors='ignore')}[/yellow]")
                    else:
                        console.print("  [dim]No immediate banner received.[/dim]")
                except socket.timeout:
                    console.print("  [dim]Banner grab timed out.[/dim]")
                
                # Check for LA-MAINT characteristics
                # Often uses UDP 51 as well, but TCP 51 can be a legacy management shell
                console.print("\n[cyan][*] Identifying service type...[/cyan]")
                if b"busybox" in banner.lower() or b"login:" in banner.lower():
                    console.print("  [bold red][!] Possible exposed BusyBox/Telnet shell detected on Port 51![/bold red]")
                elif b"dns" in banner.lower():
                    console.print("  [yellow][!] Unusual DNS service on Port 51 detected.[/yellow]")
                else:
                    console.print("  [dim]Service signature unknown. Might be a proprietary vendor protocol.[/dim]")
                    
            else:
                console.print("[red][!] Port 51 is closed or filtered.[/red]")
            
            s.close()
        except Exception as e:
            console.print(f"[red][!] Connection failed: {e}[/red]")
