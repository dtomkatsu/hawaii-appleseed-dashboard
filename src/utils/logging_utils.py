"""Logging utilities for the Hawaii Appleseed Dashboard."""
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.config import LOG_DIR

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging():
    """Configure logging for the application."""
    # Main logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_DIR / 'app.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Debug logger
    debug_logger = logging.getLogger('debug')
    debug_logger.setLevel(logging.DEBUG)
    debug_file_handler = logging.FileHandler(LOG_DIR / 'debug.log')
    debug_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    debug_logger.addHandler(debug_file_handler)
    
    # Log system information
    debug_logger.info(f"Python version: {sys.version}")
    debug_logger.info(f"Starting application at {datetime.now()}")
    
    return logger

def log_error(message, exception=None):
    """Log error to debug file with traceback."""
    debug_logger = logging.getLogger('debug')
    debug_logger.error(message)
    if exception:
        import traceback
        debug_logger.error(traceback.format_exc())
        with open(LOG_DIR / 'debug.log', 'a') as f:
            f.write(f"\n{message}\n{traceback.format_exc()}\n")
