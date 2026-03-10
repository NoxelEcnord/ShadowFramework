import socket
import concurrent.futures
import dns.resolver
import dns.zone
import dns.query
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

RECORD_TYPES = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME', 'SOA', 'SRV']

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/dns_enum',
        'description': 'DNS enumeration: records, subdomains brute-force, and zone transfer attempt.',
        'options': {
            'DOMAIN': 'Target domain (e.g. example.com)',
            'WORDLIST': 'Subdomain wordlist path [default: wordlists/subdomains.txt]',
            'THREADS': 'Threads for subdomain brute force [default: 50]',
            'ZONE_TRANSFER': 'Attempt DNS zone transfer [default: true]',
            'BRUTE': 'Brute-force subdomains [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 2
        self.resolver.lifetime = 2

    def _query(self, domain, rtype):
        try:
            answers = self.resolver.resolve(domain, rtype)
            return [r.to_text() for r in answers]
        except Exception:
            return []

    def _zone_transfer(self, domain):
        console.print(f"[cyan][*] Attempting zone transfer for {domain}...[/cyan]")
        ns_records = self._query(domain, 'NS')
        for ns in ns_records:
            ns = ns.rstrip('.')
            try:
                ns_ip = socket.gethostbyname(ns)
                zone = dns.zone.from_xfr(dns.query.xfr(ns_ip, domain, timeout=5))
                console.print(f"[bold green][+] Zone transfer SUCCESS from {ns}![/bold green]")
                for name, node in zone.nodes.items():
                    console.print(f"  {name}.{domain}")
                log_action(f"Zone transfer success from {ns} for {domain}")
                return
            except Exception:
                pass
        console.print("[yellow][!] Zone transfer failed (normal if server is configured correctly).[/yellow]")

    def _brute_sub(self, domain, sub):
        target = f"{sub}.{domain}"
        addrs = self._query(target, 'A')
        if addrs:
            return (target, addrs)
        return None

    def run(self):
        domain = self.framework.options.get('DOMAIN')
        wordlist = self.framework.options.get('WORDLIST', 'wordlists/subdomains.txt')
        threads = int(self.framework.options.get('THREADS', 50))
        do_zone = self.framework.options.get('ZONE_TRANSFER', 'true').lower() == 'true'
        do_brute = self.framework.options.get('BRUTE', 'true').lower() == 'true'

        if not domain:
            console.print("[red][!] DOMAIN is required.[/red]")
            return

        console.print(f"[cyan][*] Enumerating DNS for: {domain}[/cyan]\n")
        log_action(f"DNS enum started for {domain}")

        # Standard record lookup
        table = Table(title=f"DNS Records — {domain}")
        table.add_column("Type", style="cyan")
        table.add_column("Value", style="green")
        for rtype in RECORD_TYPES:
            results = self._query(domain, rtype)
            for r in results:
                table.add_row(rtype, r)
                log_action(f"{domain} {rtype}: {r}")
        console.print(table)

        # Zone transfer
        if do_zone:
            self._zone_transfer(domain)

        # Subdomain brute force
        if do_brute:
            try:
                with open(wordlist, 'r') as f:
                    subs = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                console.print(f"[yellow][!] Wordlist not found: {wordlist}. Skipping brute force.[/yellow]")
                return

            console.print(f"\n[cyan][*] Brute-forcing {len(subs)} subdomains with {threads} threads...[/cyan]")
            found = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {executor.submit(self._brute_sub, domain, s): s for s in subs}
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        sub, addrs = result
                        found.append((sub, ', '.join(addrs)))
                        console.print(f"  [green][+] {sub}[/green] → {', '.join(addrs)}")
                        log_action(f"Subdomain found: {sub} → {addrs}")

            console.print(f"\n[green][+] Found {len(found)} subdomain(s).[/green]")
