import socket
import requests
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

# (port, service, banner_probe, banner_match -> cve_hints)
VULN_CHECKS = [
    {
        'port': 21, 'service': 'FTP',
        'checks': [
            {'banner_contains': 'vsftpd 2.3.4', 'cve': 'CVE-2011-2523', 'desc': 'vsftpd 2.3.4 backdoor'},
            {'banner_contains': 'ProFTPD 1.3.3', 'cve': 'CVE-2010-4221', 'desc': 'ProFTPD 1.3.3 RCE'},
        ]
    },
    {
        'port': 22, 'service': 'SSH',
        'checks': [
            {'banner_contains': 'OpenSSH_7.2p1', 'cve': 'CVE-2016-6210', 'desc': 'OpenSSH 7.2p1 user enum'},
            {'banner_contains': 'OpenSSH_5', 'cve': 'CVE-2010-4478', 'desc': 'OpenSSH <5.6 key-agreement DoS'},
        ]
    },
    {
        'port': 23, 'service': 'Telnet',
        'checks': [
            {'always': True, 'cve': 'INFO', 'desc': 'Telnet is plaintext — credentials sent in clear'},
        ]
    },
    {
        'port': 445, 'service': 'SMB',
        'checks': [
            {'always': True, 'cve': 'CVE-2017-0144', 'desc': 'Check for MS17-010 (EternalBlue) — use exploit/eternalblue'},
        ]
    },
    {
        'port': 3306, 'service': 'MySQL',
        'checks': [
            {'always': True, 'cve': 'INFO', 'desc': 'MySQL exposed — check for anonymous/root login'},
        ]
    },
    {
        'port': 6379, 'service': 'Redis',
        'checks': [
            {'always': True, 'cve': 'CVE-2022-0543', 'desc': 'Redis exposed — often no auth; check for RCE via Lua'},
        ]
    },
    {
        'port': 9200, 'service': 'Elasticsearch',
        'checks': [
            {'always': True, 'cve': 'CVE-2015-1427', 'desc': 'Elasticsearch may allow unauthenticated access'},
        ]
    },
    {
        'port': 27017, 'service': 'MongoDB',
        'checks': [
            {'always': True, 'cve': 'INFO', 'desc': 'MongoDB exposed — check for unauthenticated access'},
        ]
    },
]

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/vuln_scanner',
        'description': 'Banner-based vulnerability scanner with CVE hints for known vulnerable services.',
        'options': {
            'RHOST': 'Target IP address or hostname',
            'PORTS': 'Ports to check (comma-sep or range) [default: auto from known list]',
            'TIMEOUT': 'Connection timeout in seconds [default: 3]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _grab_banner(self, host, port, timeout):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            try:
                s.send(b'\r\n')
                banner = s.recv(512).decode(errors='ignore').strip()
            except Exception:
                banner = ''
            s.close()
            return banner
        except Exception:
            return None  # Port closed / filtered

    def run(self):
        rhost = self.framework.options.get('RHOST')
        timeout = float(self.framework.options.get('TIMEOUT', 3))

        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        try:
            target_ip = socket.gethostbyname(rhost)
        except socket.gaierror:
            console.print(f"[red][!] Cannot resolve: {rhost}[/red]")
            return

        console.print(f"[cyan][*] Vulnerability scan on {rhost} ({target_ip})...[/cyan]")
        log_action(f"Vuln scan started on {rhost}")

        findings = []
        for check in VULN_CHECKS:
            port = check['port']
            service = check['service']
            console.print(f"  [dim]→ Probing port {port} ({service})...[/dim]")
            banner = self._grab_banner(target_ip, port, timeout)

            if banner is None:
                continue  # Port closed

            console.print(f"  [green][+] Port {port} OPEN[/green] — banner: {repr(banner[:80])}")
            log_action(f"Open port {port} on {rhost}: {banner}")

            for rule in check['checks']:
                hit = False
                if rule.get('always'):
                    hit = True
                elif 'banner_contains' in rule and rule['banner_contains'].lower() in banner.lower():
                    hit = True

                if hit:
                    findings.append({
                        'port': port,
                        'service': service,
                        'cve': rule['cve'],
                        'desc': rule['desc']
                    })

        if not findings:
            console.print("[yellow][!] No known vulnerabilities detected.[/yellow]")
            return

        table = Table(title=f"Vulnerability Findings — {rhost}")
        table.add_column("Port", style="cyan", justify="right")
        table.add_column("Service", style="green")
        table.add_column("CVE", style="yellow")
        table.add_column("Description", style="white")
        for f in findings:
            table.add_row(str(f['port']), f['service'], f['cve'], f['desc'])
            log_action(f"VULN on {rhost}:{f['port']} — {f['cve']}: {f['desc']}")
        console.print(table)
        console.print(f"\n[bold red][!] {len(findings)} potential vulnerability/issue(s) found![/bold red]")
