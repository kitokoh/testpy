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
    """
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


@_manage_conn
def add_status_setting(status_name: str, status_type: str, color_hex: str = None, sort_order: int = 0, conn: sqlite3.Connection = None) -> int | bool:
    """
    Adds a new status setting to the StatusSettings table.

    Args:
        status_name: The name of the status.
        status_type: The type of the status (e.g., 'Client', 'Project', 'Task').
        color_hex: The hex color code for the status (optional).
        sort_order: The sort order for the status (optional, default 0).
        conn: The database connection (managed by _manage_conn decorator if not provided).

    Returns:
        The ID of the newly inserted status if successful, False otherwise.
    """
    # If conn is not provided, get_db_connection will be called by the decorator @_manage_conn
    # However, if we want to use this function without the decorator in some specific cases,
    # or if the decorator is not applied, we might need manual connection handling.
    # For now, assuming @_manage_conn will handle the connection.
    # If direct call (without decorator) is needed, conn must be passed.

    # The @_manage_conn decorator handles the connection and cursor creation,
    # and also commit/rollback and closing the connection.
    # So, we just need to get the cursor from the conn and execute the query.

    if conn is None:
        # This case should ideally be handled by @_manage_conn
        # or the calling function should ensure conn is provided if not using the decorator.
        logging.error("Database connection not provided to add_status_setting.")
        # Attempt to establish a connection if none is provided and not managed by decorator
        # This is a fallback, ideally connection is managed by decorator or passed explicitly
        try:
            conn = get_db_connection()
            if conn is None:
                logging.error("Failed to establish a fallback database connection.")
                return False
            # We are not in a managed context here, so manual commit/close would be needed.
            # This path is getting complex and indicates a potential design issue
            # if the decorator is not consistently used.
            # For simplicity, let's rely on the decorator or explicit passing of 'conn'.
            # If decorator is not used, the caller MUST pass an active connection.
        except Exception as e:
            logging.error(f"Error establishing fallback connection: {e}")
            return False

        # If we manually created a connection, we need to manually manage it.
        # This is not ideal. The decorator @_manage_conn is preferred.
        manual_connection_management = True
    else:
        manual_connection_management = False

    try:
        cur = conn.cursor()
        sql = """INSERT INTO StatusSettings (status_name, status_type, color_hex, sort_order)
                 VALUES (?, ?, ?, ?)"""
        cur.execute(sql, (status_name, status_type, color_hex, sort_order))

        if manual_connection_management:
            conn.commit()

        last_id = cur.lastrowid
        cur.close() # Close cursor
        return last_id if last_id is not None else True # lastrowid is None if no row was inserted or backend doesn't support it well, but True indicates it likely worked if no error
    except sqlite3.Error as e:
        logging.error(f"Database error in add_status_setting for '{status_name}'/'{status_type}': {e}")
        if manual_connection_management and conn:
            conn.rollback()
        return False
    finally:
        if manual_connection_management and conn:
            conn.close()


@_manage_conn
def update_status_setting(status_id: int, status_name: str, status_type: str, color_hex: str = None, sort_order: int = None, conn: sqlite3.Connection = None) -> bool:
    """
    Updates an existing status setting in the StatusSettings table.

    Args:
        status_id: The ID of the status to update.
        status_name: The new name of the status.
        status_type: The new type of the status.
        color_hex: The new hex color code (optional, None to leave unchanged if not provided, or pass existing value).
                   Consider how to handle clearing a value if that's a use case (e.g. pass empty string or specific sentinel).
                   For now, if None, it implies no change to color_hex in the SET clause.
        sort_order: The new sort order (optional, None to leave unchanged).
        conn: The database connection (managed by _manage_conn decorator).

    Returns:
        True if successful, False otherwise.
    """
    sql = """UPDATE StatusSettings SET
             status_name = ?,
             status_type = ?"""
    params = [status_name, status_type]

    if color_hex is not None: # Assuming None means "do not update this field"
        sql += ", color_hex = ?"
        params.append(color_hex)

    if sort_order is not None: # Assuming None means "do not update this field"
        sql += ", sort_order = ?"
        params.append(sort_order)

    sql += " WHERE status_id = ?"
    params.append(status_id)

    try:
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        conn.commit()
        return cur.rowcount > 0  # True if at least one row was updated
    except sqlite3.Error as e:
        logging.error(f"Database error in update_status_setting for ID {status_id}: {e}")
        # conn.rollback() # Handled by _manage_conn
        return False
    # finally: # Cursor and connection closing handled by _manage_conn
        # if cur:
        #     cur.close()


@_manage_conn
def is_status_in_use(status_id: int, conn: sqlite3.Connection = None) -> bool:
    """
    Checks if a status_id is currently in use in the Clients table.

    Args:
        status_id: The ID of the status to check.
        conn: The database connection (managed by _manage_conn decorator).

    Returns:
        True if the status_id is found in Clients, False otherwise.
    """
    sql = "SELECT 1 FROM Clients WHERE status_id = ? LIMIT 1"
    try:
        cur = conn.cursor()
        cur.execute(sql, (status_id,))
        return cur.fetchone() is not None  # True if a row is found
    except sqlite3.Error as e:
        logging.error(f"Database error in is_status_in_use for status_id {status_id}: {e}")
        # Returning True on error prevents deletion if the check fails, which is safer.
        return True # Safer: assume in use if check fails


@_manage_conn
def delete_status_setting(status_id: int, conn: sqlite3.Connection = None) -> bool:
    """
    Deletes a status setting from the StatusSettings table.

    Args:
        status_id: The ID of the status to delete.
        conn: The database connection (managed by _manage_conn decorator).

    Returns:
        True if successful (row was deleted), False otherwise.
    """
    sql = "DELETE FROM StatusSettings WHERE status_id = ?"
    try:
        cur = conn.cursor()
        cur.execute(sql, (status_id,))
        conn.commit()
        return cur.rowcount > 0  # True if at least one row was deleted
    except sqlite3.Error as e:
        logging.error(f"Database error in delete_status_setting for ID {status_id}: {e}")
        # conn.rollback() # Handled by _manage_conn
        return False
