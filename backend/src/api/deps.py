"""
API Dependencies Module

This module contains shared dependencies, decorators, and middleware
used across API routes.

Functions:
    timing_decorator: Decorator to measure endpoint execution time.
    error_handler: Decorator for consistent error handling.
    require_ready: Decorator to check system initialization status.

Example:
    >>> from backend.src.api.deps import require_ready, error_handler
    >>> @require_ready
    ... @error_handler
    ... def my_endpoint():
    ...     return {"status": "ok"}
"""

import logging
from functools import wraps
from flask import jsonify, request
from typing import Callable, Any

from ..core.config import config

logger = logging.getLogger(__name__)

# Global state (will be set by main.py)
system_ready = False
initialization_error = None


def error_handler(f: Callable) -> Callable:
    """
    Decorator for consistent error handling across API endpoints.
    
    This decorator wraps endpoint functions to catch and handle exceptions,
    returning appropriate HTTP error responses with consistent formatting.
    
    Args:
        f (Callable): The endpoint function to wrap.
    
    Returns:
        Callable: Wrapped function with error handling.
        
    Example:
        >>> @error_handler
        ... def my_endpoint():
        ...     raise ValueError("Invalid input")
        # Returns: ({"error": "Invalid input", "type": "validation"}, 400)
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.error(f"ValueError: {e}")
            return jsonify({"error": str(e), "type": "validation"}), 400
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return jsonify({"error": "Internal server error", "details": str(e)}), 500
    return wrapper


def require_ready(f: Callable) -> Callable:
    """
    Decorator to ensure system is initialized before processing requests.
    
    This decorator checks if the system has completed initialization before
    allowing the endpoint to execute. Returns 503 Service Unavailable if
    the system is still initializing or if initialization failed.
    
    Args:
        f (Callable): The endpoint function to wrap.
    
    Returns:
        Callable: Wrapped function with readiness check.
        
    Example:
        >>> @require_ready
        ... def search_endpoint():
        ...     return {"results": [...]}
        # Returns 503 if system not ready, otherwise executes normally
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not system_ready:
            msg = "System initializing. Please retry in a few seconds."
            if initialization_error:
                msg = f"System initialization failed: {initialization_error}"
            return jsonify({"error": msg}), 503
        return f(*args, **kwargs)
    return wrapper


def require_admin(f: Callable) -> Callable:
    """
    Decorator to require an admin API key for sensitive endpoints.

    Uses header: X-Admin-API-Key
    Configured via env var: ADMIN_API_KEY
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not config.ADMIN_API_KEY:
            return jsonify({"error": "Admin endpoints are disabled"}), 401

        provided = request.headers.get('X-Admin-API-Key', '')
        if provided != config.ADMIN_API_KEY:
            return jsonify({"error": "Unauthorized"}), 401

        return f(*args, **kwargs)

    return wrapper


def set_system_state(ready: bool, error: str = None) -> None:
    """
    Set the global system state.
    
    This function is called by the main application to update the system
    readiness status and any initialization errors.
    
    Args:
        ready (bool): Whether the system is ready to serve requests.
        error (str, optional): Error message if initialization failed.
    """
    global system_ready, initialization_error
    system_ready = ready
    initialization_error = error
