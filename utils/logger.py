### utils/logger.py
import logging, os
from pathlib import Path
from colorama import Fore, Style

_LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

_LOG_COLORS = {
    'DEBUG': Fore.WHITE,
    'INFO': Fore.GREEN,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'CRITICAL': Fore.RED,
}

def setup_logger():
    log_dir = Path("~/.shadow/logs").expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "framework.log"

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.info("Logger initialized")

def log_action(message, level="INFO"):
    """
    Log an action to the framework log.

    Args:
        message: The message to log.
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    log_level = _LOG_LEVELS.get(level.upper(), logging.INFO)
    logging.log(log_level, message)

    color = _LOG_COLORS.get(level.upper(), Fore.GREEN)
    prefix = "[+]" if level.upper() == "INFO" else f"[{level.upper()}]"
    print(f"{color}{prefix} {message}{Style.RESET_ALL}")
