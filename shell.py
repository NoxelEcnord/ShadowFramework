import os
import subprocess
import readline
from colorama import Fore, Style
from utils.adb_manager import ADBManager

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
        self.current_plugin = None
        self.running = True
        self.adb_manager = ADBManager()
        self.connected_device = None

        # Set up autocomplete
        self.commands = {
            'help': self.show_help,
            'exit': self.exit,
            'use': self.use_module,
            'search': self.search_modules,
            'devices': self.list_devices,
            'connect': self.connect_device,
            'disconnect': self.disconnect_device,
            'shell': self.execute_adb_shell,
            'push': self.push_file,
            'pull': self.pull_file,
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
        Display the available options for the current module or plugin.
        """
        if self.current_module:
            module = self.module_loader.modules[self.current_module]
            if hasattr(module, 'MODULE_INFO') and 'options' in module.MODULE_INFO:
                print(f"\n{Fore.CYAN}Module Options for {self.current_module}{Style.RESET_ALL}")
                print("========================")
                print(f"  {'Name':<15} {'Description':<40} {'Required':<10} {'Value'}")
                print(f"  {'-'*15} {'-'*40} {'-'*10} {'-'*20}")
                for name, option in module.MODULE_INFO['options'].items():
                    print(f"  {name:<15} {option['description']:<40} {str(option['required']):<10} {option['value']}")
                print()
            else:
                print(f"{Fore.YELLOW}[!] No options defined for this module.{Style.RESET_ALL}")
        elif self.current_plugin:
            self.current_plugin.show_options()
        else:
            print(f"{Fore.RED}[!] No module or plugin loaded.{Style.RESET_ALL}")

    def set_option(self, *args):
        """
        Set a module or plugin option.
        """
        if len(args) < 2:
            print(f"{Fore.RED}[!] Usage: set <option> <value>{Style.RESET_ALL}")
            return

        option, value = args

        # Check if the value is a search result number
        if value.isdigit() and self.last_search_results:
            index = int(value) - 1
            if 0 <= index < len(self.last_search_results):
                value = self.last_search_results[index][0]
            else:
                print(f"{Fore.RED}[!] Invalid search result number.{Style.RESET_ALL}")
                return

        if self.current_module:
            module = self.module_loader.modules[self.current_module]
            if hasattr(module, 'MODULE_INFO') and 'options' in module.MODULE_INFO:
                if option.upper() in module.MODULE_INFO['options']:
                    if not hasattr(module, 'options'):
                        module.options = {}
                    module.options[option.upper()] = value
                    print(f"{Fore.GREEN}[+] {option.upper()} => {value}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}[!] Invalid option: {option}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[!] No options defined for this module.{Style.RESET_ALL}")
        elif self.current_plugin:
            self.current_plugin.set_option(option.upper(), value)
        else:
            print(f"{Fore.RED}[!] No module or plugin loaded.{Style.RESET_ALL}")

    def show_info(self, *args):
        """
        Display information about the current module or plugin.
        """
        if self.current_module:
            module = self.module_loader.modules[self.current_module]
            if hasattr(module, 'MODULE_INFO'):
                print(f"\n{Fore.CYAN}Module Information{Style.RESET_ALL}")
                print("==================")
                print(f"  Name:        {module.MODULE_INFO['name']}")
                print(f"  Description: {module.MODULE_INFO['description']}")
                print(f"  Author:      {module.MODULE_INFO['author']}")
                print()
            else:
                print(f"{Fore.YELLOW}[!] No information available for this module.{Style.RESET_ALL}")
        elif self.current_plugin:
            print(f"\n{Fore.CYAN}Plugin Information{Style.RESET_ALL}")
            print("==================")
            print(f"  Name:        {self.current_plugin.name}")
            print(f"  Description: {self.current_plugin.description}")
            print(f"  Author:      {self.current_plugin.author}")
            print()
        else:
            print(f"{Fore.RED}[!] No module or plugin loaded.{Style.RESET_ALL}")

    def run_module(self, *args):
        """
        Execute the current module or plugin.
        """
        if self.current_module:
            module_class = self.module_loader.modules[self.current_module]
            module_instance = module_class(self)
            if hasattr(module_instance, 'run'):
                module_instance.run()
            else:
                print(f"{Fore.RED}[!] Module does not have a run method.{Style.RESET_ALL}")
        elif self.current_plugin:
            self.current_plugin.run()
        else:
            print(f"{Fore.RED}[!] No module or plugin loaded.{Style.RESET_ALL}")

    def _autocomplete(self, text, state):
        """
        Autocomplete function for the shell.
        """
        line = readline.get_line_buffer().split()
        if not line:
            options = list(self.commands.keys())
        else:
            command = line[0]
            if command == 'use':
                options = [m for m in self.module_loader.modules if m.startswith(text)] + \
                          [p for p in self.plugin_loader.plugins if p.startswith(text)]
            elif command == 'set':
                if self.current_module:
                    module = self.module_loader.modules[self.current_module]
                    if hasattr(module, 'MODULE_INFO') and 'options' in module.MODULE_INFO:
                        options = [o for o in module.MODULE_INFO['options'] if o.startswith(text.upper())]
                    else:
                        options = []
                else:
                    options = []
            else:
                options = [cmd for cmd in self.commands.keys() if cmd.startswith(text)]

        if state < len(options):
            return options[state]
        return None

    def _prompt(self):
        """
        Display the shell prompt.
        """
        if self.connected_device:
            device_prompt = f"{Fore.RED}{self.connected_device}{Style.RESET_ALL}"
        else:
            device_prompt = f"{Fore.YELLOW}no-device{Style.RESET_ALL}"

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
            return input(f"{color}shadow({self.current_module}) [{device_prompt}]>{Style.RESET_ALL} ")
        elif self.current_plugin:
            return input(f"{Fore.YELLOW}shadow(plugin:{self.current_plugin.name}) [{device_prompt}]>{Style.RESET_ALL} ")
        return input(f"{Fore.MAGENTA}shadow [{device_prompt}]>{Style.RESET_ALL} ")

    def start(self):
        """
        Start the interactive shell.
        """
        history_file = os.path.expanduser('~/.shadow_history')
        if os.path.exists(history_file):
            readline.read_history_file(history_file)

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
        print(f"\n{Fore.CYAN}Core Commands{Style.RESET_ALL}")
        print("=============")
        print(f"  {'Command':<15} {'Description'}")
        print(f"  {'-'*15} {'-'*30}")
        for command, func in self.commands.items():
            if func.__doc__:
                print(f"  {command:<15} {func.__doc__.strip().splitlines()[0]}")
        print()

    def exit(self, *args):
        """
        Exit the framework.
        """
        history_file = os.path.expanduser('~/.shadow_history')
        readline.write_history_file(history_file)
        print(f"{Fore.YELLOW}[!] Exiting ShadowFramework...{Style.RESET_ALL}")
        self.running = False

    def use_module(self, *args):
        """
        Load a module or plugin.
        """
        if not args:
            print(f"{Fore.RED}[!] Usage: use <module|plugin>{Style.RESET_ALL}")
            return

        name = args[0]
        if name in self.module_loader.modules:
            self.current_module = name
            self.current_plugin = None
            print(f"{Fore.GREEN}[+] Loaded module: {name}{Style.RESET_ALL}")
        elif name in self.plugin_loader.plugins:
            plugin_class = self.plugin_loader.plugins[name]
            self.current_plugin = plugin_class(self)
            self.current_module = None
            print(f"{Fore.GREEN}[+] Loaded plugin: {name}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[!] Module or plugin not found: {name}{Style.RESET_ALL}")

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
                results.append((name, module.MODULE_INFO.get('description', '')))

        # Search user-made plugins
        for name, module in self.plugin_loader.plugins.items():
            if (term in name.lower() or
                term in module.MODULE_INFO.get('description', '').lower()):
                results.append((name, module.MODULE_INFO.get('description', '')))

        if results:
            print(f"\n{Fore.CYAN}Matching Modules{Style.RESET_ALL}")
            print("================")
            print(f"  {'Module':<50} {'Description'}")
            print(f"  {'-'*50} {'-'*30}")
            for name, description in results:
                print(f"  {name:<50} {description}")
            print()
        else:
            print(f"{Fore.YELLOW}[!] No modules found for: {term}{Style.RESET_ALL}")

    def list_devices(self, *args):
        """
        List connected devices.
        """
        devices = self.adb_manager.get_devices()
        if devices:
            print(f"\n{Fore.CYAN}Connected Devices{Style.RESET_ALL}")
            print("=================")
            print(f"  {'ID':<5} {'Device'}")
            print(f"  {'-'*5} {'-'*20}")
            for idx, device in enumerate(devices, 1):
                print(f"  {idx:<5} {device}")
            print()
        else:
            print(f"{Fore.YELLOW}[!] No devices connected.{Style.RESET_ALL}")

    def connect_device(self, *args):
        """
        Connect to a device.
        """
        if not args:
            print(f"{Fore.RED}[!] Usage: connect <device_id>{Style.RESET_ALL}")
            return

        device_id = args[0]
        devices = self.adb_manager.get_devices()
        if device_id in devices:
            self.connected_device = device_id
            self.adb_manager.device_id = device_id
            print(f"{Fore.GREEN}[+] Connected to device: {device_id}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[!] Device not found: {device_id}{Style.RESET_ALL}")

    def disconnect_device(self, *args):
        """
        Disconnect from the current device.
        """
        if not self.connected_device:
            print(f"{Fore.YELLOW}[!] Not connected to any device.{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}[+] Disconnected from device: {self.connected_device}{Style.RESET_ALL}")
        self.connected_device = None
        self.adb_manager.device_id = None

    def execute_adb_shell(self, *args):
        """
        Execute a shell command on the connected device.
        """
        if not self.connected_device:
            print(f"{Fore.RED}[!] No device connected.{Style.RESET_ALL}")
            return

        command = " ".join(args)
        output = self.adb_manager.execute_shell_command(command)
        if output:
            print(output)

    def push_file(self, *args):
        """
        Push a file to the connected device.
        """
        if not self.connected_device:
            print(f"{Fore.RED}[!] No device connected.{Style.RESET_ALL}")
            return

        if len(args) < 2:
            print(f"{Fore.RED}[!] Usage: push <local_path> <remote_path>{Style.RESET_ALL}")
            return

        local_path, remote_path = args
        self.adb_manager.push_file(local_path, remote_path)

    def pull_file(self, *args):
        """
        Pull a file from the connected device.
        """
        if not self.connected_device:
            print(f"{Fore.RED}[!] No device connected.{Style.RESET_ALL}")
            return

        if len(args) < 2:
            print(f"{Fore.RED}[!] Usage: pull <remote_path> <local_path>{Style.RESET_ALL}")
            return

        remote_path, local_path = args
        self.adb_manager.pull_file(remote_path, local_path)

    def list_sessions(self, *args):
        """
        List active sessions.
        """
        sessions = self.session_manager.get_sessions()
        if sessions:
            print(f"\n{Fore.CYAN}Active Sessions{Style.RESET_ALL}")
            print("===============")
            print(f"  {'ID':<5} {'Session'}")
            print(f"  {'-'*5} {'-'*20}")
            for idx, session in enumerate(sessions, 1):
                print(f"  {idx:<5} {session}")
            print()
        else:
            print(f"{Fore.YELLOW}[!] No active sessions.{Style.RESET_ALL}")

    def show_history(self, *args):
        """
        Show command history.
        """
        lines = int(args[0]) if args else None
        with open("~/.shadow/history.txt", "r") as f:
            history = f.readlines()
            if lines:
                history = history[-lines:]
            print(f"{Fore.CYAN}[+] Command history:{Style.RESET_ALL}")
            for line in history:
                print(f"  {line.strip()}")

    def clear_screen(self, *args):
        """
        Clear the screen.
        """
        print("\033[H\033[J", end="")
