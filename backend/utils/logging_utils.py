import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_logging(log_level=None):
    """
    Configure logging for the application
    
    Args:
        log_level (str, optional): Log level to set. If None, uses LOG_LEVEL from env
    
    Returns:
        logger: Configured logger instance
    """
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Application started with log level: {log_level}")
    return logger

def get_logger(name):
    """
    Get a logger instance for a specific module
    
    Args:
        name (str): Name of the module/logger
    
    Returns:
        logger: Logger instance
    """
    return logging.getLogger(name)

def set_log_level(level):
    """
    Set log level dynamically for all loggers
    
    Args:
        level (str): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        str: The level that was set
    
    Raises:
        ValueError: If invalid log level provided
    """
    level = level.upper()
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    if level not in valid_levels:
        raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
    
    # Set the log level for the root logger and all existing loggers
    logging.getLogger().setLevel(getattr(logging, level))
    for name in logging.Logger.manager.loggerDict:
        logging.getLogger(name).setLevel(getattr(logging, level))
    
    return level

def get_current_log_level():
    """
    Get the current log level
    
    Returns:
        dict: Dictionary with log level name and numeric value
    """
    current_level = logging.getLogger().getEffectiveLevel()
    level_name = logging.getLevelName(current_level)
    return {"log_level": level_name, "numeric_level": current_level}
