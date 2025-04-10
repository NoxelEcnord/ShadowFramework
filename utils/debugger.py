"""
Debugger Utility
This module provides debugging functionality for the Shadow Framework.
"""

import sys
import traceback
import logging
from functools import wraps
from typing import Callable, Any

class Debugger:
    def __init__(self, logger=None):
        """
        Initialize the debugger.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def debug(self, func: Callable) -> Callable:
        """
        Decorator to add debugging functionality to a function.
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                self.logger.debug(f"Entering {func.__name__}")
                result = func(*args, **kwargs)
                self.logger.debug(f"Exiting {func.__name__}")
                return result
            except Exception as e:
                self.logger.error(f"Error in {func.__name__}: {str(e)}")
                self.logger.error(traceback.format_exc())
                raise
        return wrapper

    def log_exception(self, exc_info=None):
        """
        Log an exception with full traceback.
        
        Args:
            exc_info: Exception info tuple (type, value, traceback)
        """
        if exc_info is None:
            exc_info = sys.exc_info()
        
        self.logger.error("Exception occurred:")
        self.logger.error(f"Type: {exc_info[0].__name__}")
        self.logger.error(f"Value: {str(exc_info[1])}")
        self.logger.error("Traceback:")
        for line in traceback.format_tb(exc_info[2]):
            self.logger.error(line.strip())

    def enable_debug_mode(self):
        """
        Enable debug mode for the framework.
        """
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("Debug mode enabled")

    def disable_debug_mode(self):
        """
        Disable debug mode for the framework.
        """
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger.setLevel(logging.INFO)
        self.logger.info("Debug mode disabled")
