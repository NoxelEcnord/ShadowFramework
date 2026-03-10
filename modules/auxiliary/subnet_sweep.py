import socket
import ipaddress
import concurrent.futures
import struct
import os
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/subnet_sweep',
        'description': 'ICMP ping sweep to discover live hosts across a CIDR range.',
        'options': {
            'CIDR': 'Target subnet in CIDR notation (e.g. 192.168.1.0/24)',
            'TIMEOUT': 'Ping timeout in seconds [default: 1]',
            'THREADS': 'Concurrent threads [default: 100]',
            'RESOLVE': 'Attempt reverse DNS resolution on live hosts [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _ping(self, ip_str, timeout):
        """Send a raw ICMP echo request. Falls back to TCP connect if no root."""
        # Try ICMP first (needs root)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            sock.settimeout(timeout)
            # Build ICMP echo packet
            icmp_type, icmp_code, checksum, identifier, sequence = 8, 0, 0, os.getpid() & 0xFFFF, 1
            header = struct.pack('bbHHh', icmp_type, icmp_code, checksum, identifier, sequence)
            payload = b'shadowfwk'
            checksum = self._checksum(header + payload)
            header = struct.pack('bbHHh', icmp_type, icmp_code, socket.htons(checksum), identifier, sequence)
            packet = header + payload
            sock.sendto(packet, (ip_str, 0))
            data, _ = sock.recvfrom(1024)
            sock.close()
            return True
        except PermissionError:
            # Fall back to TCP port 80 connect
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                result = s.connect_ex((ip_str, 80))
                s.close()
                return result == 0
            except Exception:
                return False
        except Exception:
            return False

    def _checksum(self, data):
        s = 0
        for i in range(0, len(data), 2):
            w = (data[i] << 8) + (data[i+1] if i+1 < len(data) else 0)
            s += w
        s = (s >> 16) + (s & 0xFFFF)
        s += (s >> 16)
        return ~s & 0xFFFF

    def _discover_arp(self, cidr):
        """Use arp-scan for fast, low-level discovery."""
        console.print("  [cyan]→ Probing with arp-scan...[/cyan]")
        try:
            # Need sudo for raw sockets, but we check if it's available
            cmd = ['arp-scan', '--localnet'] if not cidr else ['arp-scan', cidr]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            # 192.168.1.1	00:11:22:33:44:55	Vendor
            matches = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-f:]{17})', r.stdout, re.I)
            return [(ip, f"ARP ({mac})") for ip, mac in matches]
        except Exception:
            return []

    def _discover_nmap(self, cidr):
        """Use nmap host discovery (-sn)."""
        console.print("  [cyan]→ Probing with nmap...[/cyan]")
        try:
            r = subprocess.run(['nmap', '-sn', cidr], capture_output=True, text=True, timeout=30)
            # Nmap scan report for 192.168.1.1
            matches = re.findall(r'Nmap scan report for (?:[^\s(]+\s\()?(\d+\.\d+\.\d+\.\d+)\)?', r.stdout)
            return [(ip, "Nmap Discovery") for ip in matches]
        except Exception:
            return []

    def _discover_proc_arp(self):
        """Parse local ARP cache from /proc/net/arp."""
        console.print("  [cyan]→ Checking local ARP cache...[/cyan]")
        hosts = []
        try:
            if os.path.exists('/proc/net/arp'):
                with open('/proc/net/arp', 'r') as f:
                    for line in f.readlines()[1:]: # Skip header
                        parts = line.split()
                        if len(parts) >= 4 and parts[3] != '00:00:00:00:00:00':
                            hosts.append((parts[0], "Local ARP Cache"))
        except Exception:
            pass
        return hosts

    def _ping(self, ip_str, timeout):
        """Probe host via multiple ports."""
        # Common ports that are likely to be open on active devices
        ports = [80, 443, 22, 5555, 8080, 139, 445]
        for port in ports:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                result = s.connect_ex((ip_str, port))
                s.close()
                if result == 0:
                    return True
            except Exception:
                continue
        return False

    def run(self):
        cidr = self.framework.options.get('CIDR')
        timeout = float(self.framework.options.get('TIMEOUT', 1))
        threads = int(self.framework.options.get('THREADS', 100))
        resolve = self.framework.options.get('RESOLVE', 'true').lower() == 'true'

        if not cidr:
            # Try to auto-detect local network
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                cidr = '.'.join(local_ip.split('.')[:-1]) + '.0/24'
                console.print(f"[dim][*] Auto-detected local CIDR: {cidr}[/dim]")
            except Exception:
                console.print("[red][!] CIDR is required (e.g. 192.168.1.0/24).[/red]")
                return

        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError as e:
            console.print(f"[red][!] Invalid CIDR: {e}[/red]")
            return

        console.print(f"[cyan][*] Robust Discovery on {cidr}...[/cyan]")
        log_action(f"Subnet sweep on {cidr}")

        found_map = {} # IP -> Source

        # Fast initial discovery
        for ip, src in self._discover_proc_arp():
            found_map[ip] = src

        for ip, src in self._discover_arp(cidr):
            found_map[ip] = src

        for ip, src in self._discover_nmap(cidr):
            if ip not in found_map:
                found_map[ip] = src

        # Sweep remaining if needed
        hosts = [str(h) for h in network.hosts() if str(h) not in found_map]
        if hosts:
            console.print(f"  [cyan]→ Sweeping {len(hosts)} remaining hosts with TCP probes...[/cyan]")
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {executor.submit(self._probe, h, timeout, resolve): h for h in hosts}
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        ip, hn = result
                        found_map[ip] = f"TCP Probe ({hn})" if hn else "TCP Probe"

        # Results table
        table = Table(title=f"Discovered Hosts — {cidr}")
        table.add_column("IP Address", style="cyan")
        table.add_column("Source / Method", style="yellow")
        table.add_column("Hostname", style="green")

        live_count = 0
        for ip in sorted(found_map.keys(), key=lambda x: ipaddress.ip_address(x)):
            hn = ''
            if resolve:
                try:
                    hn = socket.gethostbyaddr(ip)[0]
                except Exception:
                    pass
            table.add_row(ip, found_map[ip], hn or '—')
            live_count += 1
            log_action(f"Live host: {ip} via {found_map[ip]}")

        console.print(table)
        console.print(f"[bold green][+] {live_count} live host(s) discovered.[/bold green]")
