"""
API Module

This module contains all API-related functionality including routes,
dependencies, and middleware.

Modules:
    routes: API endpoint definitions.
    deps: Shared dependencies and decorators.
"""

from .routes import api_bp, init_routes
from .deps import error_handler, require_ready, set_system_state

__all__ = ['api_bp', 'init_routes', 'error_handler', 'require_ready', 'set_system_state']
