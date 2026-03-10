"""
ShadowFramework Plugin — Advanced Nmap Scanner
Uses python-nmap if available, falls back to subprocess nmap.
"""
import subprocess
import os
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

try:
    import nmap
    HAS_NMAP = True
except ImportError:
    HAS_NMAP = False


class Module:
    MODULE_INFO = {
        'name': 'plugins/nmap_scanner',
        'description': 'Advanced Nmap scanner plugin (uses python-nmap or system nmap).',
        'options': {
            'RHOST': 'Target IP address',
            'RPORT': 'Target port or range [default: 1-1000]',
            'TIMEOUT': 'Scan timing template 1-5 [default: 4]',
            'SERVICE_SCAN': 'Enable service detection [default: true]',
            'OS_DETECTION': 'Enable OS detection (requires root) [default: false]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        rhost = self.framework.options.get('RHOST')
        rport = self.framework.options.get('RPORT', '1-1000')
        timing = self.framework.options.get('TIMEOUT', '4')
        svc = self.framework.options.get('SERVICE_SCAN', 'true').lower() == 'true'
        os_detect = self.framework.options.get('OS_DETECTION', 'false').lower() == 'true'

        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        if HAS_NMAP:
            self._run_python_nmap(rhost, rport, timing, svc, os_detect)
        else:
            self._run_system_nmap(rhost, rport, timing, svc, os_detect)

    def _run_python_nmap(self, rhost, rport, timing, svc, os_detect):
        """Scan using python-nmap library."""
        nm = nmap.PortScanner()
        args = f"-p {rport} --open -T{timing}"
        if svc:
            args += " -sV"
        if os_detect:
            args += " -O"

        console.print(f"[cyan][*] Scanning {rhost} (ports {rport}) via python-nmap...[/cyan]")
        log_action(f"Nmap scan on {rhost}:{rport} args: {args}")

        try:
            nm.scan(hosts=rhost, arguments=args)
        except nmap.PortScannerError as e:
            console.print(f"[red][!] Nmap error: {e}[/red]")
            return

        if not nm.all_hosts():
            console.print("[yellow][!] No hosts found.[/yellow]")
            return

        for host in nm.all_hosts():
            state = nm[host].state()
            console.print(f"[green][+] Host: {host} ({state})[/green]")

            if os_detect and 'osmatch' in nm[host]:
                for os_match in nm[host]['osmatch'][:3]:
                    console.print(f"    OS: {os_match['name']} ({os_match['accuracy']}%)")

            table = Table(title=f"Open Ports — {host}")
            table.add_column("Port", style="cyan")
            table.add_column("State", style="green")
            table.add_column("Service", style="white")
            table.add_column("Version", style="dim")

            for proto in nm[host].all_protocols():
                for port in nm[host][proto]:
                    info = nm[host][proto][port]
                    version = f"{info.get('product', '')} {info.get('version', '')}".strip()
                    table.add_row(f"{port}/{proto}", info['state'], info['name'], version)
                    log_action(f"Port {port}/{proto}: {info['state']} ({info['name']} {version})")

            console.print(table)

    def _run_system_nmap(self, rhost, rport, timing, svc, os_detect):
        """Fallback: run nmap as system command."""
        console.print("[yellow][!] python-nmap not installed. Using system nmap...[/yellow]")

        cmd = ['nmap', '-p', rport, '--open', f'-T{timing}']
        if svc:
            cmd.append('-sV')
        if os_detect:
            cmd.append('-O')
        cmd.append(rhost)

        console.print(f"[cyan][*] Running: {' '.join(cmd)}[/cyan]")
        log_action(f"System nmap: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                console.print(result.stdout)
            else:
                console.print(f"[red]{result.stderr}[/red]")
        except FileNotFoundError:
            console.print("[red][!] nmap not found. Install with: apt install nmap[/red]")
        except subprocess.TimeoutExpired:
            console.print("[red][!] Scan timed out (300s limit).[/red]")