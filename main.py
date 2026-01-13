#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from colorama import Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.logging import RichHandler
import logging

console = Console()
# Custom imports
from utils.logger import setup_logger, log_action
from utils.banner import display_banner
from shell import ShadowShell
from utils.db_manager import DBManager
from utils.module_loader import ModuleLoader
from utils.plugin_loader import PluginLoader
from utils.session_manager import SessionManager

# Constants
SHADOW_HOME = Path("./").expanduser()#Path("~/.shadow").expanduser()
CONFIG_FILE = SHADOW_HOME / "config" / "config.ini"
LOG_DIR = SHADOW_HOME / "logs"
DB_FILE = SHADOW_HOME / "db" / "shadow.db"

def initialize_framework():
    """
    Initialize the framework by setting up directories, logging, and configurations.
    """
    try:
        # Create necessary directories
        SHADOW_HOME.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (SHADOW_HOME / "db").mkdir(parents=True, exist_ok=True)
        (SHADOW_HOME / "loot").mkdir(parents=True, exist_ok=True)
        (SHADOW_HOME / "modules").mkdir(parents=True, exist_ok=True)
        (SHADOW_HOME / "plugins").mkdir(parents=True, exist_ok=True)
        (SHADOW_HOME / "wordlists").mkdir(parents=True, exist_ok=True)
        (SHADOW_HOME / "payloads").mkdir(parents=True, exist_ok=True)

        # Set up logging
        setup_logger()

        # Display banner
        display_banner()

        # Initialize database
        db_manager = DBManager(DB_FILE)
        log_action("Database initialized")

        # Load core modules
        module_loader = ModuleLoader(SHADOW_HOME / "modules")
        core_modules = module_loader.load_modules()
        log_action(f"Loaded {len(core_modules)} core modules")

        # Load user-made plugins
        plugin_loader = PluginLoader(SHADOW_HOME / "plugins")
        user_modules = plugin_loader.load_plugins()
        log_action(f"Loaded {len(user_modules)} user modules")

        # Initialize session manager
        session_manager = SessionManager(db_manager)
        log_action("Session manager initialized")

        # Return initialized components
        return db_manager, module_loader, plugin_loader, session_manager

    except Exception as e:
        console.print(f"[bold red][!] Error during framework initialization: {e}[/bold red]")
        sys.exit(1)

def main():
    """
    Main function to start the ShadowFramework.
    """
    try:
        # Initialize the framework
        db_manager, module_loader, plugin_loader, session_manager = initialize_framework()

        # Start the interactive shell
        shell = ShadowShell(
            db_manager=db_manager,
            module_loader=module_loader,
            plugin_loader=plugin_loader,
            session_manager=session_manager
        )
        shell.start()

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Exiting ShadowFramework...{Style.RESET_ALL}")
        sys.exit(0)

    except Exception as e:
        print(f"{Fore.RED}[!] Fatal error: {e}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()
