import socket
import concurrent.futures
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/port_scanner',
        'description': 'Fast TCP port scanner with banner grabbing (no nmap required).',
        'options': {
            'RHOST': 'Target IP address or hostname',
            'PORTS': 'Port range or list (e.g. 1-1024, 80,443,8080) [default: 1-1024]',
            'TIMEOUT': 'Connection timeout in seconds [default: 1]',
            'THREADS': 'Number of concurrent threads [default: 100]',
            'BANNER': 'Attempt banner grabbing [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _scan_port(self, host, port, timeout, grab_banner):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            banner = ''
            if result == 0 and grab_banner:
                try:
                    sock.send(b'HEAD / HTTP/1.0\r\n\r\n')
                    banner = sock.recv(256).decode(errors='ignore').split('\r\n')[0].strip()
                except Exception:
                    pass
            sock.close()
            return (port, result == 0, banner)
        except Exception:
            return (port, False, '')

    def _parse_ports(self, ports_str):
        ports = []
        for part in ports_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                ports.extend(range(int(start), int(end) + 1))
            else:
                ports.append(int(part))
        return ports

    def run(self):
        rhost = self.framework.options.get('RHOST')
        ports_str = self.framework.options.get('PORTS', '1-1024')
        timeout = float(self.framework.options.get('TIMEOUT', 1))
        threads = int(self.framework.options.get('THREADS', 100))
        grab_banner = self.framework.options.get('BANNER', 'true').lower() == 'true'

        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        try:
            target_ip = socket.gethostbyname(rhost)
        except socket.gaierror:
            console.print(f"[red][!] Cannot resolve host: {rhost}[/red]")
            return

        ports = self._parse_ports(ports_str)
        console.print(f"[cyan][*] Scanning {rhost} ({target_ip}) — {len(ports)} ports, {threads} threads...[/cyan]")
        log_action(f"Port scan started on {rhost} ports {ports_str}")

        open_ports = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self._scan_port, target_ip, p, timeout, grab_banner): p for p in ports}
            for future in concurrent.futures.as_completed(futures):
                port, is_open, banner = future.result()
                if is_open:
                    open_ports.append((port, banner))

        open_ports.sort(key=lambda x: x[0])

        if not open_ports:
            console.print("[yellow][!] No open ports found.[/yellow]")
            return

        table = Table(title=f"Open Ports — {rhost}")
        table.add_column("Port", style="cyan", justify="right")
        table.add_column("Service (guess)", style="green")
        table.add_column("Banner", style="white")

        common = {21:'ftp',22:'ssh',23:'telnet',25:'smtp',53:'dns',80:'http',
                  110:'pop3',143:'imap',443:'https',445:'smb',3306:'mysql',
                  3389:'rdp',5432:'postgres',6379:'redis',8080:'http-alt',8443:'https-alt'}

        for port, banner in open_ports:
            svc = common.get(port, 'unknown')
            table.add_row(str(port), svc, banner or '—')
            log_action(f"Open port {port}/{svc} on {rhost} | banner: {banner}")

        console.print(table)
        console.print(f"[green][+] Found {len(open_ports)} open port(s).[/green]")
