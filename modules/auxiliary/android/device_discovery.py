"""
ShadowFramework - Android Device Discovery Module
===================================================
Multi-method network scanner for finding exposed Android devices.
Works with or without API keys (Shodan, Censys, ZoomEye, FOFA).
Falls back to raw async TCP port sweeps targeting ADB (5555).
"""

import socket
import subprocess
import threading
import time
import json
import re
import struct
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.live import Live
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import urllib.request
    import urllib.parse
    import ssl
    URLLIB_AVAILABLE = True
except ImportError:
    URLLIB_AVAILABLE = False

from utils.logger import log_action

console = Console() if RICH_AVAILABLE else None

# ─── ADB Banner Fingerprint ──────────────────────────────────────────────────
ADB_BANNER_PREFIX = b"CNXN"
ADB_CONNECT_MSG = b"CNXN\x00\x00\x00\x01\x00\x10\x00\x00"  # ADB protocol v1

# ─── Known phone-farm / cloud CIDR blocks (Asia-Pacific heavy) ───────────────
PHONE_FARM_CIDRS = [
    # China - Alibaba Cloud / Tencent / Huawei
    "47.104.0.0/16", "47.105.0.0/16", "47.106.0.0/16",
    "120.76.0.0/16", "120.77.0.0/16", "120.78.0.0/16",
    "139.196.0.0/16", "106.14.0.0/16", "106.15.0.0/16",
    # China - China Telecom / Unicom
    "114.55.0.0/16", "182.92.0.0/16", "123.56.0.0/16",
    "101.200.0.0/16", "101.201.0.0/16",
    # Southeast Asia - common VPS ranges
    "103.27.0.0/16", "103.28.0.0/16",
    "43.240.0.0/16", "43.241.0.0/16",
    # India
    "13.232.0.0/16", "13.233.0.0/16",
    # Russia / Eastern Europe
    "185.220.0.0/16", "5.188.0.0/16",
]

# ─── Smaller, faster local scan ranges ───────────────────────────────────────
LOCAL_RANGES = [
    "192.168.0.0/24", "192.168.1.0/24", "192.168.2.0/16",
    "10.0.0.0/16", "10.42.0.0/24",
    "172.16.0.0/12",
]


class Module:
    MODULE_INFO = {
        'name': 'auxiliary/android/device_discovery',
        'description': (
            'Multi-method Android device discovery. Scans for exposed ADB (port 5555) '
            'using Shodan/Censys/ZoomEye/FOFA APIs and raw TCP sweeps. '
            'Automatically adds discovered devices to the framework scope.'
        ),
        'options': {
            'MODE':         'Scan mode: ALL, LOCAL, API, SWEEP [default: ALL]',
            'SHODAN_KEY':   'Shodan API key (optional)',
            'CENSYS_ID':    'Censys API ID (optional)',
            'CENSYS_SECRET':'Censys API secret (optional)',
            'ZOOMEYE_KEY':  'ZoomEye API key (optional)',
            'FOFA_EMAIL':   'FOFA email (optional)',
            'FOFA_KEY':     'FOFA API key (optional)',
            'THREADS':      'Number of scan threads [default: 200]',
            'TIMEOUT':      'Connection timeout in seconds [default: 1.5]',
            'MAX_DEVICES':  'Stop after finding N devices [default: 20]',
            'PORT':         'Target port [default: 5555]',
            'CIDR':         'Custom CIDR range to sweep (optional)',
            'AUTO_SCOPE':   'Automatically add to scope [default: true]',
            'VERIFY_ADB':   'Verify ADB banner before adding [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self.found_devices = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

    # ═══════════════════════════════════════════════════════════════════════════
    #  MAIN ENTRY
    # ═══════════════════════════════════════════════════════════════════════════
    def run(self):
        mode      = self.framework.options.get('MODE', 'ALL').upper()
        threads   = int(self.framework.options.get('THREADS', '200'))
        timeout   = float(self.framework.options.get('TIMEOUT', '1.5'))
        max_dev   = int(self.framework.options.get('MAX_DEVICES', '20'))
        port      = int(self.framework.options.get('PORT', '5555'))
        custom    = self.framework.options.get('CIDR', '')
        auto_scope= self.framework.options.get('AUTO_SCOPE', 'true').lower() == 'true'
        verify    = self.framework.options.get('VERIFY_ADB', 'true').lower() == 'true'

        console.print(f"\n[bold cyan]╔══════════════════════════════════════════════════╗[/bold cyan]")
        console.print(f"[bold cyan]║   SHADOW Android Device Discovery Engine         ║[/bold cyan]")
        console.print(f"[bold cyan]╚══════════════════════════════════════════════════╝[/bold cyan]")
        console.print(f"  [dim]Mode: {mode} | Threads: {threads} | Port: {port} | Max: {max_dev}[/dim]\n")
        log_action(f"Device discovery started (mode={mode}, port={port})")

        start_time = time.time()

        # ── Phase 1: API-based discovery (fast, global reach) ─────────────
        if mode in ('ALL', 'API'):
            self._run_api_scans(max_dev, port)

        # ── Phase 2: Local network sweep ──────────────────────────────────
        if mode in ('ALL', 'LOCAL') and len(self.found_devices) < max_dev:
            console.print("\n[bold yellow]⬤ Phase: Local Network Sweep[/bold yellow]")
            local_targets = self._get_local_cidrs()
            self._sweep_cidrs(local_targets, threads, timeout, port, max_dev, verify)

        # ── Phase 3: Wide internet sweep (phone farms) ────────────────────
        if mode in ('ALL', 'SWEEP') and len(self.found_devices) < max_dev:
            console.print("\n[bold yellow]⬤ Phase: Internet Sweep (Phone Farm Ranges)[/bold yellow]")
            cidrs = [custom] if custom else PHONE_FARM_CIDRS
            self._sweep_cidrs(cidrs, threads, timeout, port, max_dev, verify)

        elapsed = time.time() - start_time

        # ── Results ───────────────────────────────────────────────────────
        self._display_results(elapsed)

        # ── Auto-add to scope ─────────────────────────────────────────────
        if auto_scope and self.found_devices:
            self._add_to_scope()

    # ═══════════════════════════════════════════════════════════════════════════
    #  API SCANNERS
    # ═══════════════════════════════════════════════════════════════════════════
    def _run_api_scans(self, max_dev, port):
        console.print("[bold yellow]⬤ Phase: API Search Engines[/bold yellow]")

        # Shodan
        key = self.framework.options.get('SHODAN_KEY', '')
        if key:
            self._query_shodan(key, max_dev, port)
        else:
            console.print("  [dim]Shodan: No API key, skipping.[/dim]")

        # Censys
        c_id = self.framework.options.get('CENSYS_ID', '')
        c_sec = self.framework.options.get('CENSYS_SECRET', '')
        if c_id and c_sec:
            self._query_censys(c_id, c_sec, max_dev, port)
        else:
            console.print("  [dim]Censys: No credentials, skipping.[/dim]")

        # ZoomEye
        zkey = self.framework.options.get('ZOOMEYE_KEY', '')
        if zkey:
            self._query_zoomeye(zkey, max_dev, port)
        else:
            console.print("  [dim]ZoomEye: No API key, skipping.[/dim]")

        # FOFA
        f_email = self.framework.options.get('FOFA_EMAIL', '')
        f_key = self.framework.options.get('FOFA_KEY', '')
        if f_email and f_key:
            self._query_fofa(f_email, f_key, max_dev, port)
        else:
            console.print("  [dim]FOFA: No credentials, skipping.[/dim]")

    def _http_get(self, url, headers=None, auth=None):
        """Zero-dependency HTTP GET using urllib."""
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=headers or {})
            if auth:
                import base64
                credentials = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
                req.add_header('Authorization', f'Basic {credentials}')
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            console.print(f"  [red][!] HTTP error: {e}[/red]")
            return None

    def _query_shodan(self, api_key, max_dev, port):
        console.print("  [cyan]→ Querying Shodan...[/cyan]")
        query = urllib.parse.quote(f'"Android Debug Bridge" port:{port}')
        url = f"https://api.shodan.io/shodan/host/search?key={api_key}&query={query}&facets=org"
        data = self._http_get(url)
        if data and 'matches' in data:
            count = 0
            for match in data['matches']:
                if count >= max_dev or self.stop_event.is_set():
                    break
                ip = match.get('ip_str', '')
                p = match.get('port', port)
                org = match.get('org', 'Unknown')
                country = match.get('location', {}).get('country_name', '?')
                self._register_device(ip, p, f"Shodan/{org}", country)
                count += 1
            console.print(f"  [green][+] Shodan: Found {count} devices.[/green]")
        else:
            console.print("  [yellow][!] Shodan: No results or error.[/yellow]")

    def _query_censys(self, api_id, api_secret, max_dev, port):
        console.print("  [cyan]→ Querying Censys...[/cyan]")
        query = urllib.parse.quote(f'services.port: {port} and services.banner: "Android"')
        url = f"https://search.censys.io/api/v2/hosts/search?q={query}&per_page=25"
        data = self._http_get(url, auth=(api_id, api_secret))
        if data and 'result' in data:
            count = 0
            for hit in data['result'].get('hits', []):
                if count >= max_dev:
                    break
                ip = hit.get('ip', '')
                country = hit.get('location', {}).get('country', '?')
                self._register_device(ip, port, "Censys", country)
                count += 1
            console.print(f"  [green][+] Censys: Found {count} devices.[/green]")
        else:
            console.print("  [yellow][!] Censys: No results or error.[/yellow]")

    def _query_zoomeye(self, api_key, max_dev, port):
        console.print("  [cyan]→ Querying ZoomEye...[/cyan]")
        query = urllib.parse.quote(f'port:{port} +os:"Android"')
        url = f"https://api.zoomeye.ai/host/search?query={query}&page=1"
        headers = {"API-KEY": api_key}
        data = self._http_get(url, headers=headers)
        if data and 'matches' in data:
            count = 0
            for match in data['matches']:
                if count >= max_dev:
                    break
                ip = match.get('ip', '')
                country = match.get('geoinfo', {}).get('country', {}).get('names', {}).get('en', '?')
                self._register_device(ip, port, "ZoomEye", country)
                count += 1
            console.print(f"  [green][+] ZoomEye: Found {count} devices.[/green]")
        else:
            console.print("  [yellow][!] ZoomEye: No results or error.[/yellow]")

    def _query_fofa(self, email, key, max_dev, port):
        console.print("  [cyan]→ Querying FOFA...[/cyan]")
        import base64
        query = base64.b64encode(f'port="{port}" && banner="Android Debug Bridge"'.encode()).decode()
        url = f"https://fofa.info/api/v1/search/all?email={email}&key={key}&qbase64={query}&size=25&fields=ip,port,country_name"
        data = self._http_get(url)
        if data and 'results' in data:
            count = 0
            for entry in data['results']:
                if count >= max_dev:
                    break
                ip = entry[0] if len(entry) > 0 else ''
                p = entry[1] if len(entry) > 1 else port
                country = entry[2] if len(entry) > 2 else '?'
                self._register_device(ip, int(p) if str(p).isdigit() else port, "FOFA", country)
                count += 1
            console.print(f"  [green][+] FOFA: Found {count} devices.[/green]")
        else:
            console.print("  [yellow][!] FOFA: No results or error.[/yellow]")

    # ═══════════════════════════════════════════════════════════════════════════
    #  RAW TCP PORT SWEEP
    # ═══════════════════════════════════════════════════════════════════════════
    def _get_local_cidrs(self):
        """Detect local subnets from OS interfaces."""
        subnets = LOCAL_RANGES[:]
        try:
            # Parse ip addr
            out = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=5).stdout
            matches = re.findall(r'inet\s+(\d+\.\d+\.\d+\.\d+/\d+)', out)
            for m in matches:
                if not m.startswith('127.'):
                    subnets.insert(0, m)
        except Exception:
            pass
        return list(dict.fromkeys(subnets)) # Unique

    def _sweep_cidrs(self, cidrs, threads, timeout, port, max_dev, verify):
        all_ips = set()
        
        # Fast ARP/Cache discovery first for LOCAL mode
        if any(c.startswith(('192.', '10.', '172.')) for c in cidrs):
            console.print("  [cyan]→ Checking ARP cache and local neighbors...[/cyan]")
            try:
                # Check /proc/net/arp
                if os.path.exists('/proc/net/arp'):
                    with open('/proc/net/arp', 'r') as f:
                        for line in f.readlines()[1:]:
                            parts = line.split()
                            if len(parts) >= 4 and parts[3] != '00:00:00:00:00:00':
                                all_ips.add(parts[0])
                
                # Try nmap discovery if available
                cidr_str = ' '.join(cidrs[:3]) # Limit to first 3 subnets for speed
                n_out = subprocess.run(['nmap', '-sn', '--host-timeout', '10s', cidr_str], capture_output=True, text=True, timeout=20).stdout
                ips = re.findall(r'(\d+\.\d+\.\d+\.\d+)', n_out)
                all_ips.update(ips)
            except Exception:
                pass

        # Fill in the rest from CIDR
        for cidr in cidrs:
            if len(all_ips) >= 1000 or self.stop_event.is_set(): break
            try:
                for ip in self._cidr_to_ips(cidr):
                    all_ips.add(ip)
                    if len(all_ips) >= 1000: break
            except Exception: continue

        total = len(all_ips)
        if total == 0:
            console.print("  [yellow][!] No IPs to scan.[/yellow]")
            return

        console.print(f"  [dim]Probing {total} candidate hosts...[/dim]")

        scanned = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
            TextColumn("[green]{task.fields[found]}[/green]"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("Discovering...", total=total, found="Found: 0")

            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {}
                for ip in all_ips:
                    if self.stop_event.is_set() or len(self.found_devices) >= max_dev:
                        break
                    futures[executor.submit(self._probe_host, ip, port, timeout, verify)] = ip

                for future in as_completed(futures):
                    scanned += 1
                    progress.update(task, advance=1, found=f"Found: {len(self.found_devices)}")
                    if len(self.found_devices) >= max_dev:
                        # Don't set stop_event globally here, just break this phase
                        break

    def _probe_host(self, ip, port, timeout, verify):
        """Probe a single host for open ADB port."""
        if self.stop_event.is_set():
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            if result == 0:
                if verify:
                    # Send ADB protocol handshake to verify
                    try:
                        sock.send(ADB_CONNECT_MSG)
                        response = sock.recv(24)
                        if response and (ADB_BANNER_PREFIX in response or b"device" in response.lower()):
                            self._register_device(ip, port, "TCP/Verified", "Unknown")
                        else:
                            # Port open but not ADB - still interesting
                            self._register_device(ip, port, "TCP/Open(Unverified)", "Unknown")
                    except socket.timeout:
                        self._register_device(ip, port, "TCP/Open(Timeout)", "Unknown")
                else:
                    self._register_device(ip, port, "TCP/Open", "Unknown")
            sock.close()
        except (socket.error, OSError):
            pass

    # ═══════════════════════════════════════════════════════════════════════════
    #  UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════
    def _register_device(self, ip, port, source, country):
        """Thread-safe device registration."""
        if not ip:
            return
        with self.lock:
            # Scope stores IP only — port is metadata
            for d in self.found_devices:
                if d['ip'] == ip:
                    return  # Don't add duplicate IPs
            self.found_devices.append({
                'device_id': ip,
                'ip': ip,
                'port': port,
                'source': source,
                'country': country,
                'timestamp': time.strftime('%H:%M:%S'),
            })
            console.print(f"  [bold green][+] FOUND: {ip}:{port} ({source}) [{country}][/bold green]")
            log_action(f"Discovered Android device: {ip}:{port} via {source}")

    def _cidr_to_ips(self, cidr):
        """Convert CIDR notation to list of IPs (stdlib only)."""
        if '/' not in cidr:
            return [cidr]
        network, prefix_len = cidr.split('/')
        prefix_len = int(prefix_len)
        
        # Convert IP to integer
        parts = network.split('.')
        network_int = (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])
        
        # Calculate host range
        host_bits = 32 - prefix_len
        num_hosts = (1 << host_bits) - 2  # Exclude network and broadcast
        if num_hosts <= 0:
            return [network]
        
        # Cap at 65534 to prevent memory issues on large ranges
        num_hosts = min(num_hosts, 65534)
        
        ips = []
        for i in range(1, num_hosts + 1):
            ip_int = network_int + i
            ip = f"{(ip_int >> 24) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 8) & 0xFF}.{ip_int & 0xFF}"
            ips.append(ip)
        return ips

    def _display_results(self, elapsed):
        """Display scan results in a formatted table."""
        console.print(f"\n[bold cyan]{'═' * 55}[/bold cyan]")
        console.print(f"[bold]  Scan Complete | {len(self.found_devices)} devices found | {elapsed:.1f}s elapsed[/bold]")
        console.print(f"[bold cyan]{'═' * 55}[/bold cyan]\n")

        if not self.found_devices:
            console.print("[yellow][!] No devices found. Try a wider CIDR range or add API keys.[/yellow]")
            return

        table = Table(title="Discovered Android Devices")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Device ID", style="white")
        table.add_column("Source", style="yellow")
        table.add_column("Country", style="green")
        table.add_column("Time", style="dim")

        for idx, dev in enumerate(self.found_devices, 1):
            table.add_row(str(idx), dev['device_id'], dev['source'], dev['country'], dev['timestamp'])

        console.print(table)

    def _add_to_scope(self):
        """Add all discovered devices to the framework scope."""
        added = 0
        for dev in self.found_devices:
            try:
                nick = self.framework.db_manager.add_to_scope(dev['device_id'])
                if nick:
                    console.print(f"  [dim]{dev['device_id']} → [bold cyan]{nick}[/bold cyan][/dim]")
                    added += 1
            except Exception:
                break

        if added:
            console.print(f"\n[bold green][+] Auto-added {added} devices to scope.[/bold green]")
            console.print(f"[dim]  Use 'scopeList' to view. Use '${{ALL}}' to target all.[/dim]")
        log_action(f"Auto-added {added} devices to scope from discovery scan.")
