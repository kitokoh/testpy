import sqlite3
import logging # Added import
from .generic_crud import _manage_conn, get_db_connection

# --- ApplicationSettings CRUD ---
@_manage_conn
def get_setting(key: str, default: any = None, conn: sqlite3.Connection = None) -> any: # Signature modified
    cursor = conn.cursor()
    value_to_return = default # Initialize with default
    try:
        cursor.execute("SELECT setting_value FROM ApplicationSettings WHERE setting_key = ?", (key,))
        row = cursor.fetchone()
        if row:
            value_to_return = row['setting_value']
        # If row is None, value_to_return remains default
        logging.info(f"Retrieved setting: {key} = {value_to_return}")
        return value_to_return
    except sqlite3.Error as e:
        logging.error(f"Failed to get setting for key {key}: {e}")
        logging.info(f"Returning default value for key {key} due to error: {default}")
        return default

@_manage_conn
def set_setting(key: str, value: str, conn: sqlite3.Connection = None, **kwargs) -> bool:
    cursor = conn.cursor()
    sql = "INSERT OR REPLACE INTO ApplicationSettings (setting_key, setting_value) VALUES (?, ?)"
    try:
        logging.info(f"Setting value for key {key} = {value}") # Added logging
        cursor.execute(sql, (key, value))
        # conn.commit() is handled by _manage_conn
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to set setting for key {key}, value {value}: {e}") # Added logging
        return False
