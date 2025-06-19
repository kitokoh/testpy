import os
import sys
import sqlite3
import logging # Added for error logging

import app_setup # Import app_setup directly

# Removed try-except block for config import
# Removed config_fallback class

def get_db_connection(db_path_override=None):
    """
    Returns a new database connection object.
    Uses 'database_path' from the centralized app_setup.CONFIG by default.
    An optional db_path_override can be provided (e.g., for tests).
    """
    if db_path_override:
        path_to_connect = db_path_override
    else:
        app_config = app_setup.get_app_config()
        path_to_connect = app_config.get('database_path')

        if not path_to_connect: # Check if it's None or empty
            # This is a critical error because utils.load_config should always provide a default.
            # If it's missing here, something is fundamentally wrong with config loading.
            logging.critical(
                "CRITICAL: 'database_path' is missing or empty in the application configuration (app_setup.CONFIG). "
                "This path is essential for database connectivity. "
                "Please check the configuration setup and ensure 'utils.load_config' provides a default."
            )
            raise ValueError("Database path not found in application configuration. Cannot establish connection.")

    conn = sqlite3.connect(path_to_connect)
    conn.row_factory = sqlite3.Row
    return conn

__all__ = ["get_db_connection"]
