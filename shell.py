import os
import subprocess
import readline
from colorama import Fore, Style
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class ShadowShell:
    def __init__(self, db_manager, module_loader, plugin_loader, session_manager):
        """
        Initialize the ShadowShell.

        Args:
            db_manager: Database manager instance.
            module_loader: Module loader instance.
            plugin_loader: Plugin loader instance.
            session_manager: Session manager instance.
        """
        self.db_manager = db_manager
        self.module_loader = module_loader
        self.plugin_loader = plugin_loader
        self.session_manager = session_manager
        self.current_module = None
        self.options = {}
        self.running = True

        # Set up autocomplete
        self.commands = {
            'help': self.show_help,
            'exit': self.exit,
            'use': self.use_module,
            'search': self.search_modules,
            'devices': self.list_devices,
            'sessions': self.list_sessions,
            'history': self.show_history,
            'clear': self.clear_screen,
            'sh': self.local_shell,
        }
        readline.set_completer(self._autocomplete)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(" \t\n")
        # Existing initialization code...
        self.commands.update({
            'options': self.show_options,
            'set': self.set_option,
            'info': self.show_info,
            'run': self.run_module,
        })

    def show_options(self, *args):
        """
        Display the available options for the current module.
        """
        if not self.current_module:
            print(f"{Fore.RED}[!] No module loaded.{Style.RESET_ALL}")
            return

        module = self.module_loader.modules[self.current_module]
        if hasattr(module, 'MODULE_INFO') and 'options' in module.MODULE_INFO:
            table = Table(title=f"Options for {self.current_module}")
            table.add_column("Option", style="cyan")
            table.add_column("Description", style="white")
            
            for option, description in module.MODULE_INFO['options'].items():
                table.add_row(option, description)
            
            console.print(table)
        else:
            console.print(f"[yellow][!] No options defined for this module.[/yellow]")

    def set_option(self, *args):
        """
        Set a module option.
        """
        if not self.current_module:
            print(f"{Fore.RED}[!] No module loaded.{Style.RESET_ALL}")
            return

        if len(args) < 2:
            print(f"{Fore.RED}[!] Usage: set <option> <value>{Style.RESET_ALL}")
            return

        option = args[0].upper()
        value = args[1]

        module = self.module_loader.modules[self.current_module]
        if hasattr(module, 'MODULE_INFO') and 'options' in module.MODULE_INFO:
            if option in module.MODULE_INFO['options']:
                self.options[option] = value
                console.print(f"[green][+] {option} => {value}[/green]")
            else:
                console.print(f"[red][!] Invalid option: {option}[/red]")
        else:
            console.print(f"[yellow][!] No options defined for this module.[/yellow]")

    def show_info(self, *args):
        """
        Display information about the current module.
        """
        if not self.current_module:
            print(f"{Fore.RED}[!] No module loaded.{Style.RESET_ALL}")
            return

        module = self.module_loader.modules[self.current_module]
        if hasattr(module, 'MODULE_INFO'):
            print(f"{Fore.CYAN}[+] Module: {module.MODULE_INFO['name']}{Style.RESET_ALL}")
            print(f"  Description: {module.MODULE_INFO['description']}")
            if 'options' in module.MODULE_INFO:
                print("  Options:")
                for option, description in module.MODULE_INFO['options'].items():
                    print(f"    {option}: {description}")
        else:
            print(f"{Fore.YELLOW}[!] No information available for this module.{Style.RESET_ALL}")

    def run_module(self, *args):
        """
        Execute the current module.
        """
        if not self.current_module:
            print(f"{Fore.RED}[!] No module loaded.{Style.RESET_ALL}")
            return

        module_class = self.module_loader.modules[self.current_module]
        module_instance = module_class(self)  # Pass the framework instance to the module
        if hasattr(module_instance, 'run'):
            module_instance.run()
        else:
            print(f"{Fore.RED}[!] Module does not have a run method.{Style.RESET_ALL}")

    def _autocomplete(self, text, state):
        """
        Autocomplete function for the shell.
        """
        options = [cmd for cmd in self.commands.keys() if cmd.startswith(text)]
        if state < len(options):
            return options[state]
        return None

    def _prompt(self):
        """
        Display the shell prompt.
        """
        if self.current_module:
            module_type = self.current_module.split('/')[0]
            if module_type == 'auxiliary':
                color = Fore.YELLOW
            elif module_type == 'exploit':
                color = Fore.BLUE
            elif module_type == 'post':
                color = Fore.GREEN
            else:
                color = Fore.WHITE
            return input(f"{color}shadow({self.current_module})>{Style.RESET_ALL} ")
        return input(f"{Fore.MAGENTA}shadow>{Style.RESET_ALL} ")

    def start(self):
        """
        Start the interactive shell.
        """
        while self.running:
            try:
                cmd = self._prompt().strip()
                if not cmd:
                    continue

                # Handle local shell commands
                if cmd.startswith('/'):
                    self.execute_local_command(cmd[1:])
                    continue

                # Handle framework commands
                parts = cmd.split()
                command = parts[0].lower()
                if command in self.commands:
                    self.commands[command](*parts[1:])
                else:
                    print(f"{Fore.RED}[!] Unknown command: {command}{Style.RESET_ALL}")

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}[!] Type 'exit' to quit.{Style.RESET_ALL}")

            except Exception as e:
                print(f"{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")

    def execute_local_command(self, cmd):
        """
        Execute a command on the local machine.

        Args:
            cmd: The command to execute.
        """
        try:
            print(f"{Fore.CYAN}[*] Executing local command: {cmd}{Style.RESET_ALL}")
            subprocess.run(cmd, shell=True)
        except Exception as e:
            print(f"{Fore.RED}[!] Error executing local command: {e}{Style.RESET_ALL}")

    def local_shell(self, *args):
        """
        Drop into a local shell.
        """
        print(f"{Fore.CYAN}[*] Starting local shell. Type 'exit' to return to ShadowFramework.{Style.RESET_ALL}")
        while True:
            try:
                cmd = input(f"{Fore.MAGENTA}local>{Style.RESET_ALL} ").strip()
                if cmd.lower() == 'exit':
                    break
                self.execute_local_command(cmd)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}[!] Type 'exit' to return to ShadowFramework.{Style.RESET_ALL}")

    def show_help(self, *args):
        """
        Display the help menu.
        """
        help_text = """
        [bold cyan]Core Commands:[/bold cyan]
        help              Show this help menu
        exit              Exit the framework
        use <module>      Load a module
        search <term>     Search for modules
        devices           List connected devices
        sessions          List active sessions
        history [lines]   Show command history
        clear             Clear the screen
        sh                Drop into a local shell
        /<command>        Execute a command on the local machine
        """
        console.print(Panel(help_text, title="ShadowFramework Help", expand=False))

    def exit(self, *args):
        """
        Exit the framework.
        """
        print(f"{Fore.YELLOW}[!] Exiting ShadowFramework...{Style.RESET_ALL}")
        self.running = False

    def use_module(self, *args):
        """
        Load a module.
        """
        if not args:
            print(f"{Fore.RED}[!] Usage: use <module>{Style.RESET_ALL}")
            return

        module_name = args[0]
        if module_name in self.module_loader.modules:
            self.current_module = module_name
            self.options = {} # Clear options for new module
            console.print(f"[green][+] Loaded module: {module_name}[/green]")
        else:
            console.print(f"[red][!] Module not found: {module_name}[/red]")

    def search_modules(self, *args):
        """
        Search for modules by name, path, or description.
        """
        if not args:
            print(f"{Fore.RED}[!] Usage: search <term>{Style.RESET_ALL}")
            return

        term = args[0].lower()
        results = []

        # Search core modules
        for name, module in self.module_loader.modules.items():
            if (term in name.lower() or
                term in module.MODULE_INFO.get('description', '').lower()):
                results.append(name)

        # Search user-made plugins
        for name, module in self.plugin_loader.plugins.items():
            if (term in name.lower() or
                term in module.MODULE_INFO.get('description', '').lower()):
                results.append(name)

        if results:
            print(f"{Fore.CYAN}[+] Found {len(results)} modules:{Style.RESET_ALL}")
            for result in results:
                print(f"  {result}")
        else:
            print(f"{Fore.YELLOW}[!] No modules found for: {term}{Style.RESET_ALL}")

    def list_devices(self, *args):
        """
        List connected devices.
        """
        devices = self.session_manager.get_devices()
        if devices:
            print(f"{Fore.CYAN}[+] Connected devices:{Style.RESET_ALL}")
            for idx, device in enumerate(devices, 1):
                print(f"  #{idx}: {device}")
        else:
            print(f"{Fore.YELLOW}[!] No devices connected.{Style.RESET_ALL}")

    def list_sessions(self, *args):
        """
        List active sessions.
        """
        sessions = self.session_manager.get_sessions()
        if sessions:
            print(f"{Fore.CYAN}[+] Active sessions:{Style.RESET_ALL}")
            for session in sessions:
                print(f"  {session}")
        else:
            print(f"{Fore.YELLOW}[!] No active sessions.{Style.RESET_ALL}")

    def show_history(self, *args):
        """
        Show command history.
        """
        lines = int(args[0]) if args else None
        history_file = os.path.join(os.path.expanduser("~"), ".shadow", "history.txt")
        if not os.path.exists(history_file):
            console.print(f"[yellow][!] No history file found.[/yellow]")
            return

        with open(history_file, "r") as f:
            history = f.readlines()
            if lines:
                history = history[-lines:]
            console.print(f"[cyan][+] Command history:[/cyan]")
            for line in history:
                console.print(f"  {line.strip()}")

    def clear_screen(self, *args):
        """
        Clear the screen.
        """
        print("\033[H\033[J", end="")
