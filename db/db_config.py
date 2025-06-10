import os
import sqlite3

# Global variable for the database name
DATABASE_NAME = "app_data.db"

# Constants for document context paths
# APP_ROOT_DIR_CONTEXT should point to the parent directory of the project root.
# If db_config.py is in /app/db/, then os.path.dirname(__file__) is /app/db.
# To get to / (parent of /app), we need to go up two levels.
APP_ROOT_DIR_CONTEXT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOGO_SUBDIR_CONTEXT = "company_logos" # This assumes company_logos is at /company_logos

def get_db_connection():
    """
    Returns a new database connection object.
    The connection is configured to return rows as dictionary-like objects.
    """
    # DATABASE_NAME is now defined in this file.
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn
