import sqlite3
import os

# Import db_config from the parent directory (app level)
try:
    from . import db_config # Attempt relative import if part of 'db' package execution
except ImportError: # Fallback for direct execution or different context
    import sys
    # Navigate up two levels from db/connection.py to reach app root
    app_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if app_root_dir not in sys.path:
        sys.path.append(app_root_dir)
    try:
        import db_config # Assumes db_config.py is at app_root_dir
    except ImportError:
        print("CRITICAL: db_config.py not found by db/connection.py. Using fallback.")
        class db_config_fallback: # Minimal fallback
            DATABASE_PATH = os.path.join(app_root_dir if 'app_root_dir' in locals() else '.', "app_data_fallback_connection.db")
        db_config = db_config_fallback

def get_db_connection(db_path_override=None):
    """
    Returns a new database connection object.
    Uses DATABASE_PATH from db_config by default.
    An optional db_path_override can be provided (e.g., for tests).
    """
    path_to_connect = db_path_override if db_path_override else db_config.DATABASE_PATH
    conn = sqlite3.connect(path_to_connect)
    conn.row_factory = sqlite3.Row
    return conn

__all__ = ["get_db_connection"]
