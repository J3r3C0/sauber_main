"""
Custom Uvicorn logging configuration to use better colors.
Green for INFO, Yellow for WARNING, Red for ERROR, Cyan for startup.
"""

import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter with better color scheme."""
    
    # ANSI color codes
    RESET = "\033[0m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    
    COLORS = {
        logging.DEBUG: CYAN,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: RED + BOLD,
    }
    
    def format(self, record):
        # Use green for INFO instead of red
        color = self.COLORS.get(record.levelno, self.RESET)
        
        # Format the message
        message = super().format(record)
        
        # Color the entire line for INFO messages
        if record.levelno == logging.INFO:
            return f"{color}{message}{self.RESET}"
        else:
            return message


def setup_logging():
    """Setup colored logging for Uvicorn."""
    
    # Override uvicorn's default formatter
    formatter = ColoredFormatter(
        fmt="%(levelprefix)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configure uvicorn loggers
    for logger_name in ["uvicorn", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.addHandler(handler)
        logger.propagate = False
    
    return handler


def print_startup(message: str):
    """Print startup message in cyan."""
    CYAN = "\033[36m"
    RESET = "\033[0m"
    print(f"{CYAN}{message}{RESET}")
