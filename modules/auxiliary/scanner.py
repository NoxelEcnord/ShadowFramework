"""
ShadowFramework — Nmap Scanner Module
Comprehensive port/service/OS scanning with python-nmap or system nmap fallback.
"""
import subprocess
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
        'name': 'auxiliary/scanner',
        'description': 'Comprehensive Nmap scanner — ports, services, and OS detection.',
        'options': {
            'RHOST': 'Target IP address',
            'RPORT': 'Target port or port range (e.g., 80 or 1-1000) [default: 1-1000]',
            'TIMEOUT': 'Scan timing template 1-5 [default: 4]',
            'SERVICE_SCAN': 'Perform service detection [default: true]',
            'OS_DETECTION': 'Perform OS detection (may require root) [default: false]',
            'EXTRA_ARGS': 'Additional nmap arguments (e.g., -Pn, -A, --script=vuln) [default: ]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        rhost = self.framework.options.get('RHOST')
        rport = self.framework.options.get('RPORT', '1-1000')
        timing = self.framework.options.get('TIMEOUT', '4')
        service_scan = self.framework.options.get('SERVICE_SCAN', 'true').lower() == 'true'
        os_detection = self.framework.options.get('OS_DETECTION', 'false').lower() == 'true'
        extra_args = self.framework.options.get('EXTRA_ARGS', '')

        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        # Strip any port suffix that might leak in
        if ':' in rhost:
            rhost = rhost.split(':')[0]

        # Safety check for large scans
        if '/' in rhost and rport == '1-65535':
            console.print("[bold yellow][!] WARNING: Scanning /24 subnet on ALL ports (65535) is EXTREMELY slow.[/bold yellow]")
            console.print("[dim]    Tip: Use 'set RPORT 1-1000' for a 100x speed boost.[/dim]")

        # Optimized scan args: added --host-timeout to prevent getting stuck on dead/shielded hosts
        scan_args = f"-p {rport} --open -T{timing} --host-timeout 30s"
        if service_scan:
            scan_args += " -sV"
        if os_detection:
            scan_args += " -O"
        if extra_args:
            scan_args += f" {extra_args}"

        console.print(f"[cyan][*] Scanning {rhost} (ports {rport})...[/cyan]")
        if extra_args:
            console.print(f"[dim]    Extra Arguments: {extra_args}[/dim]")
        log_action(f"Nmap scan: {rhost} ports={rport} args={scan_args}")

        if HAS_NMAP:
            self._run_python_nmap(rhost, rport, scan_args)
        else:
            self._run_system_nmap(rhost, scan_args)

    def _run_python_nmap(self, rhost, rport, scan_args):
        """Scan using python-nmap library."""
        try:
            nm = nmap.PortScanner()
            nm.scan(hosts=rhost, arguments=scan_args)

            if not nm.all_hosts():
                console.print("[yellow][!] No hosts found (host may be down or filtered).[/yellow]")
                log_action(f"Nmap: no hosts found for {rhost}", level="WARNING")
                return

            for host in nm.all_hosts():
                state = nm[host].state()
                console.print(f"[green][+] Host: {host} ({state})[/green]")

                # OS detection
                if 'osmatch' in nm[host]:
                    for os_match in nm[host]['osmatch'][:3]:
                        console.print(f"    OS: {os_match['name']} ({os_match['accuracy']}%)")

                # Port table
                table = Table(title=f"Open Ports — {host}")
                table.add_column("Port", style="cyan")
                table.add_column("State", style="green")
                table.add_column("Service", style="white")
                table.add_column("Version", style="dim")

                for proto in nm[host].all_protocols():
                    for port in sorted(nm[host][proto]):
                        info = nm[host][proto][port]
                        version = f"{info.get('product', '')} {info.get('version', '')}".strip()
                        table.add_row(f"{port}/{proto}", info['state'], info['name'], version)
                        log_action(f"  {port}/{proto}: {info['state']} ({info['name']} {version})")

                console.print(table)

        except nmap.PortScannerError as e:
            console.print(f"[red][!] Nmap error: {e}[/red]")
            log_action(f"Nmap error: {e}", level="ERROR")
        except Exception as e:
            console.print(f"[red][!] Scan error: {e}[/red]")
            log_action(f"Scan error: {e}", level="ERROR")

    def _run_system_nmap(self, rhost, scan_args):
        """Fallback: run nmap as a system command."""
        console.print("[yellow][!] python-nmap not installed. Using system nmap...[/yellow]")

        cmd = f"nmap {scan_args} {rhost}"
        console.print(f"[dim]  $ {cmd}[/dim]")

        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                console.print(result.stdout)
            else:
                console.print(f"[red]{result.stderr}[/red]")
        except FileNotFoundError:
            console.print("[red][!] nmap not found. Install with: apt install nmap[/red]")
            console.print("[dim]  For python-nmap: pip install python-nmap[/dim]")
        except subprocess.TimeoutExpired:
            console.print("[red][!] Scan timed out (300s limit).[/red]")
