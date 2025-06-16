import os
import sys
import sqlite3

import app_setup # Import app_setup directly

try:
    import config
except ImportError:
    # This fallback is a safety net, but indicates a potential issue if reached.
    print("CRITICAL: config.py not found at project root by db/connection.py. Using fallback for DATABASE_PATH.")
    class config_fallback:
        # Define project_root here for the fallback path
        project_root_for_fallback = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        DATABASE_PATH = os.path.join(project_root_for_fallback, "app_data_fallback_connection.db")
    config = config_fallback

def get_db_connection(db_path_override=None):
    """
    Returns a new database connection object.
    Uses DATABASE_PATH from config by default.
    An optional db_path_override can be provided (e.g., for tests).
    """
    if db_path_override:
        path_to_connect = db_path_override
    else:
        # Try to get database_path from app_setup.CONFIG
        app_config = app_setup.get_app_config()
        configured_db_path = app_config.get('database_path')

        if configured_db_path: # Check if it's not None or empty
            path_to_connect = configured_db_path
        else:
            # Fallback to the DATABASE_PATH from the local config.py import
            print("INFO: No 'database_path' found in loaded CONFIG via get_app_config(), attempting to use default from local config.py for DB connection.")
            path_to_connect = config.DATABASE_PATH
    conn = sqlite3.connect(path_to_connect)
    conn.row_factory = sqlite3.Row
    return conn

__all__ = ["get_db_connection"]
