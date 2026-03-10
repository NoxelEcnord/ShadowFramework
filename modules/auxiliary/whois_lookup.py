import socket
import requests
from rich.console import Console
from rich.panel import Panel
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/whois_lookup',
        'description': 'Perform WHOIS, ASN, and geolocation lookup for a target IP or domain.',
        'options': {
            'TARGET': 'Target IP address or domain name',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _whois_raw(self, host):
        """Query whois.iana.org to find authoritative whois server, then query it."""
        try:
            # Step 1: ask IANA
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect(('whois.iana.org', 43))
            s.send(f"{host}\r\n".encode())
            response = b''
            while True:
                data = s.recv(4096)
                if not data:
                    break
                response += data
            s.close()
            text = response.decode(errors='ignore')

            # Extract refer: line for actual whois server
            refer = None
            for line in text.splitlines():
                if line.lower().startswith('refer:'):
                    refer = line.split(':', 1)[1].strip()
                    break

            if refer:
                s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s2.settimeout(5)
                s2.connect((refer, 43))
                s2.send(f"{host}\r\n".encode())
                resp2 = b''
                while True:
                    d = s2.recv(4096)
                    if not d:
                        break
                    resp2 += d
                s2.close()
                return resp2.decode(errors='ignore')
            return text
        except Exception as e:
            return f"WHOIS query failed: {e}"

    def _ip_info(self, ip):
        """Use ip-api.com to get ASN, org, geo."""
        try:
            r = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,org,as,query", timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {}

    def run(self):
        target = self.framework.options.get('TARGET')
        if not target:
            console.print("[red][!] TARGET is required.[/red]")
            return

        console.print(f"[cyan][*] Resolving {target}...[/cyan]")
        log_action(f"WHOIS lookup for {target}")

        try:
            ip = socket.gethostbyname(target)
            console.print(f"[green][+] Resolved: {ip}[/green]")
        except socket.gaierror:
            ip = target
            console.print(f"[yellow][!] Could not resolve, treating as IP: {ip}[/yellow]")

        # IP geolocation / ASN
        info = self._ip_info(ip)
        if info and info.get('status') == 'success':
            geo_text = (
                f"IP:       {info.get('query')}\n"
                f"Country:  {info.get('country')}\n"
                f"Region:   {info.get('regionName')}\n"
                f"City:     {info.get('city')}\n"
                f"ISP:      {info.get('isp')}\n"
                f"Org:      {info.get('org')}\n"
                f"ASN:      {info.get('as')}"
            )
            console.print(Panel(geo_text, title="IP / ASN Info", border_style="cyan"))
            log_action(f"ASN info for {ip}: {info}")

        # WHOIS
        console.print(f"\n[cyan][*] Fetching WHOIS for {target}...[/cyan]")
        whois_data = self._whois_raw(target)
        # Filter blank lines for cleaner output
        cleaned = '\n'.join(line for line in whois_data.splitlines() if line.strip())
        console.print(Panel(cleaned[:3000], title="WHOIS Data", border_style="green"))
        log_action(f"WHOIS data retrieved for {target}")
