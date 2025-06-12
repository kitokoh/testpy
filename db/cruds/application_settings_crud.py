import sqlite3
from .generic_crud import _manage_conn, get_db_connection

# --- ApplicationSettings CRUD ---
@_manage_conn
def get_setting(key: str, conn: sqlite3.Connection = None) -> str | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT setting_value FROM ApplicationSettings WHERE setting_key = ?", (key,))
        row=cursor.fetchone()
        return row['setting_value'] if row else None
    except sqlite3.Error:
        # logging.error(f"Failed to get setting for key {key}: {e}") # Consider logging
        return None

@_manage_conn
def set_setting(key: str, value: str, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor()
    sql="INSERT OR REPLACE INTO ApplicationSettings (setting_key, setting_value) VALUES (?, ?)"
    try:
        cursor.execute(sql, (key,value))
        return cursor.rowcount > 0
    except sqlite3.Error:
        # logging.error(f"Failed to set setting for key {key}: {e}") # Consider logging
        return False
