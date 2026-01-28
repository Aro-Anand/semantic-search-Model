"""
Logging Utilities Module

This module provides centralized logging configuration for the application.

Functions:
    setup_logging: Configure application-wide logging.
    get_logger: Get a logger instance for a specific module.

Example:
    >>> from backend.src.utils.logging import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Application started")
"""

import logging
import sys


def setup_logging(level=logging.INFO, format_string=None):
    """
    Configure application-wide logging settings.
    
    Args:
        level (int, optional): Logging level. Defaults to logging.INFO.
        format_string (str, optional): Custom format string for log messages.
            If None, uses a default format with timestamp, name, level, and message.
    
    Returns:
        logging.Logger: Root logger instance.
        
    Example:
        >>> setup_logging(level=logging.DEBUG)
        >>> logger = logging.getLogger(__name__)
        >>> logger.debug("Debug message")
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    return logging.getLogger()


def get_logger(name):
    """
    Get a logger instance for a specific module.
    
    Args:
        name (str): Name of the logger, typically __name__ of the calling module.
    
    Returns:
        logging.Logger: Logger instance configured for the specified name.
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Module initialized")
    """
    return logging.getLogger(name)
