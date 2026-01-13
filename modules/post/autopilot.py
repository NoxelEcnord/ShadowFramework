from rich.console import Console
from utils.logger import log_action

console = Console()

class Module:
    MODULE_INFO = {
        'name': 'post/autopilot',
        'description': 'Automatically run a sequence of modules for quick enumeration and post-exploitation.',
        'options': {
            'RHOST': 'Target IP address to use for all modules',
            'SEQUENCE': 'Comma-separated list of modules [default: auxiliary/scanner,auxiliary/smb_scan]'
        }
    }

    def __init__(self, framework):
        self.framework = framework

    def run(self):
        rhost = self.framework.options.get('RHOST')
        sequence = self.framework.options.get('SEQUENCE', 'auxiliary/scanner,auxiliary/smb_scan').split(',')

        if not rhost:
            console.print("[red][!] RHOST is required for autopilot.[/red]")
            return

        console.print(f"[bold magenta][*] Starting Autopilot SEQUENCE on {rhost}[/bold magenta]")
        log_action(f"Autopilot started on {rhost} with sequence: {sequence}")

        for module_name in sequence:
            module_name = module_name.strip()
            console.print(f"\n[bold yellow]>>> Running {module_name}...[/bold yellow]")
            
            if module_name in self.framework.module_loader.modules:
                # Setup options from framework for the sub-module
                # This assumes the framework instance passed to sub-modules uses self.framework.options
                try:
                    module_class = self.framework.module_loader.modules[module_name]
                    module_instance = module_class(self.framework)
                    module_instance.run()
                    log_action(f"Autopilot: Successfully ran {module_name}")
                except Exception as e:
                    console.print(f"[red][!] Module {module_name} failed: {e}[/red]")
                    log_action(f"Autopilot: Module {module_name} failed: {e}", level="ERROR")
            else:
                console.print(f"[red][!] Module {module_name} not found.[/red]")

        console.print("\n[bold green][+] Autopilot sequence complete.[/bold green]")
