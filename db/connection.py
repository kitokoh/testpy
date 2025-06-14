import os
import sys
import sqlite3

# Get the project root directory (assuming db/connection.py is in db/ which is in project root)
# This allows importing config.py from the root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
    path_to_connect = db_path_override if db_path_override else config.DATABASE_PATH
    conn = sqlite3.connect(path_to_connect)
    conn.row_factory = sqlite3.Row
    return conn

__all__ = ["get_db_connection"]
