"""
Timing and Performance Utilities Module

This module provides decorators and utilities for measuring function execution time
and monitoring application performance.

Functions:
    timing_decorator: Decorator to measure and log function execution time.

Example:
    >>> from backend.src.utils.timing import timing_decorator
    >>> @timing_decorator
    ... def slow_function():
    ...     time.sleep(1)
    >>> slow_function()  # Logs: "slow_function took 1.000s"
"""

import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def timing_decorator(f):
    """
    Decorator to measure and log the execution time of a function.
    
    This decorator wraps a function and logs the time it takes to execute,
    which is useful for performance monitoring and optimization.
    
    Args:
        f (callable): The function to be timed.
    
    Returns:
        callable: Wrapped function that logs its execution time.
        
    Example:
        >>> @timing_decorator
        ... def process_data(data):
        ...     # Process data
        ...     return result
        >>> result = process_data(my_data)
        # Logs: "process_data took 0.123s"
        
    Note:
        The timing includes the entire function execution, including any
        nested function calls.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"{f.__name__} took {duration:.3f}s")
        return result
    return wrapper
