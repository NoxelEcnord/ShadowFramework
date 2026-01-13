from impacket.smbconnection import SMBConnection
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'auxiliary/smb_scan',
        'description': 'Enumerate SMB shares and versions on a target.',
        'options': {
            'RHOST': 'Target IP address',
            'RPORT': 'Target port [default: 445]',
            'TIMEOUT': 'Connection timeout [default: 5]'
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        rhost = self.framework.options.get('RHOST')
        rport = int(self.framework.options.get('RPORT', 445))
        timeout = int(self.framework.options.get('TIMEOUT', 5))

        if not rhost:
            console.print("[red][!] RHOST is required.[/red]")
            return

        console.print(f"[*] Connecting to [cyan]{rhost}:{rport}[/cyan]...")
        try:
            smb = SMBConnection(rhost, rhost, sess_port=rport, timeout=timeout)
            # Try anonymous or guest login
            try:
                smb.login('', '')
                console.print("[green][+] Anonymous login successful![/green]")
            except:
                console.print("[yellow][*] Anonymous login failed. Attempting to list shares without login...[/yellow]")

            shares = smb.listShares()
            console.print(f"[bold green][+] Found {len(shares)} shares on {rhost}:[/bold green]")
            for share in shares:
                share_name = share['shi1_netname'][:-1]
                console.print(f"  - {share_name}")
            
            log_action(f"SMB Scan on {rhost} completed. Found {len(shares)} shares.")

        except Exception as e:
            console.print(f"[red][!] SMB Connection failed: {e}[/red]")
            log_action(f"SMB Scan on {rhost} failed: {e}", level="ERROR")
