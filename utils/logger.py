### utils/logger.py
import logging,os
from pathlib import Path
from colorama import Fore, Style

def setup_logger():
    log_dir = Path("~/.shadow/logs").expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "framework.log"

       # Configure logging
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
       )
    logging.info("Logger initialized")

def log_action(message):
    """
       Log an action to the framework log.

       Args:
           message: The message to log.
    """
    logging.info(message)
    print(f"{Fore.GREEN}[+] {message}{Style.RESET_ALL}")
