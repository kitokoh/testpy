import os
import sys
import sqlite3

# Get the project root directory (assuming db/connection.py is in db/ which is in project root)
# This allows importing config.py from the root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from app_setup import CONFIG
except ImportError:
    # Fallback if app_setup or CONFIG is not found, though this indicates a larger issue.
    # We'll rely on the existing config import as a final fallback.
    CONFIG = {} # Empty dict so .get doesn't fail
    print("WARNING: db/connection.py could not import CONFIG from app_setup.py. Database path may not be configurable via settings.")

try:
    import config
except ImportError:
    # This fallback is a safety net, but indicates a potential issue if reached.
    print("CRITICAL: config.py not found at project root by db/connection.py. Using fallback for DATABASE_PATH.")
    class config_fallback:
        DATABASE_PATH = os.path.join(project_root, "app_data_fallback_connection.db")
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
        configured_db_path = CONFIG.get('database_path')
        if configured_db_path: # Check if it's not None or empty
            path_to_connect = configured_db_path
        else:
            # Fallback to the DATABASE_PATH from the local config.py import
            # This also covers the case where CONFIG couldn't be imported.
            print("INFO: No 'database_path' in CONFIG or CONFIG not available, using default from config.py for DB connection.")
            path_to_connect = config.DATABASE_PATH
    conn = sqlite3.connect(path_to_connect)
    conn.row_factory = sqlite3.Row
    return conn

__all__ = ["get_db_connection"]
