import sqlite3
from .generic_crud import _manage_conn, get_db_connection
import logging

# --- StatusSettings CRUD ---
@_manage_conn
def get_status_setting_by_name(name: str, type: str, conn: sqlite3.Connection = None) -> dict | None:
    original_name_param = name # Keep a copy for logging or fallback
    if isinstance(name, dict) and type == 'Client':
        logging.warning(
            f"WARNING: get_status_setting_by_name called with a dictionary for 'name' when type is 'Client'. "
            f"Attempting to recover using name.get('status'). problematic_dict: {name}"
        )
        status_from_dict = name.get('status')
        if isinstance(status_from_dict, str):
            name = status_from_dict
            logging.info(f"Recovered status_name '{name}' from dictionary for type 'Client'.")
        else:
            logging.error(
                f"Failed to recover a string status from dict['status'] for type 'Client'. "
                f"Dict['status'] was: {status_from_dict}. Proceeding with original dict, which will likely fail."
            )
            # name remains original_name_param (the dict) to reproduce original error if recovery fails
            name = original_name_param # Explicitly set to original problematic dict

    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM StatusSettings WHERE status_name = ? AND status_type = ?",(name,type))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        # Log the 'name' that was actually used in the query, which might be the recovered string or the original dict
        logging.error(f"Error getting status setting by name '{name}' (original_param_type: {type(original_name_param).__name__}) and type '{type}': {e}")
        return None

@_manage_conn
def get_status_setting_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM StatusSettings WHERE status_id = ?",(id,))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting status setting by id {id}: {e}")
        return None

@_manage_conn
def get_all_status_settings(type_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all status settings, optionally filtered by type.
    STUB FUNCTION - Original was a stub, providing a basic implementation.
    """
    logging.warning(f"Called stub function get_all_status_settings (filter: {type_filter}). Basic implementation provided.")
    cursor = conn.cursor()
    sql = "SELECT * FROM StatusSettings"
    params = []
    if type_filter:
        sql += " WHERE status_type = ?"
        params.append(type_filter)
    sql += " ORDER BY status_type, sort_order, status_name"

    try:
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Database error in get_all_status_settings (filter: {type_filter}): {e}")
        return []
