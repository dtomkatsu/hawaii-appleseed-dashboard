"""Debug utilities for the Hawaii Appleseed Dashboard."""
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

def setup_debug_logging():
    """Set up debug logging to a dedicated file."""
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Set up debug logger
    debug_logger = logging.getLogger('debug')
    debug_logger.setLevel(logging.DEBUG)
    
    # Create file handler for debug.log
    debug_file = logs_dir / "debug.log"
    debug_handler = logging.FileHandler(debug_file)
    debug_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    debug_logger.addHandler(debug_handler)
    
    # Log system information
    debug_logger.info(f"Application started at {datetime.now()}")
    debug_logger.info(f"Python version: {sys.version}")
    debug_logger.info(f"Working directory: {os.getcwd()}")
    
    return debug_logger

def log_debug(message, obj=None):
    """Log a debug message with optional object inspection."""
    logger = logging.getLogger('debug')
    logger.debug(message)
    
    if obj is not None:
        try:
            # Log object type and representation
            logger.debug(f"Object type: {type(obj)}")
            logger.debug(f"Object repr: {repr(obj)}")
            
            # If it's a dictionary, log its keys
            if isinstance(obj, dict):
                logger.debug(f"Dict keys: {list(obj.keys())}")
            
            # If it has attributes, log some common ones
            for attr in ['shape', 'columns', 'bounds', '_children', 'layers']:
                if hasattr(obj, attr):
                    logger.debug(f"Object.{attr}: {getattr(obj, attr)}")
        except Exception as e:
            logger.debug(f"Error inspecting object: {e}")

def log_error(message, exception=None):
    """Log an error with traceback."""
    logger = logging.getLogger('debug')
    logger.error(message)
    
    if exception:
        logger.error(traceback.format_exc())
        
    # Always write to the debug log file directly too
    with open(Path(__file__).parent.parent.parent / "logs" / "debug.log", 'a') as f:
        f.write(f"\n{datetime.now()} - ERROR - {message}\n")
        if exception:
            f.write(traceback.format_exc())
            f.write("\n")
