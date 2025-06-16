import sqlite3
from datetime import datetime
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

@_manage_conn
def get_next_invoice_number(conn: sqlite3.Connection = None) -> str:
    """
    Generates the next invoice number in the sequence for the current year.
    Format: INV-YYYY-NNNNN (e.g., INV-2024-00001)
    """
    current_year = datetime.now().year
    setting_key = f"last_invoice_sequence_{current_year}"
    prefix = f"INV-{current_year}-"

    last_sequence_str = get_setting(setting_key, conn=conn)

    last_sequence = 0
    if last_sequence_str:
        try:
            last_sequence = int(last_sequence_str)
        except ValueError:
            # Invalid value in DB, log an error or handle as first invoice
            # For now, treat as first invoice of the year if conversion fails
            print(f"Warning: Invalid invoice sequence number '{last_sequence_str}' in settings for key '{setting_key}'. Resetting to 0.")
            last_sequence = 0
            # Optionally, one might want to repair the setting here or raise a more critical error.

    next_sequence = last_sequence + 1

    # Store the new sequence number
    # The set_setting function is also decorated with _manage_conn,
    # it will use the connection provided by this function's decorator.
    success = set_setting(setting_key, str(next_sequence), conn=conn)

    if not success:
        # This would indicate a problem saving the new sequence, which is critical.
        # Depending on desired robustness, could raise an exception here.
        # For now, we'll proceed to format the number, but the next call might reuse it.
        print(f"CRITICAL: Failed to update invoice sequence number for key '{setting_key}' to '{next_sequence}'.")
        # Consider raising an exception: raise sqlite3.Error("Failed to update invoice sequence number.")

    invoice_number = f"{prefix}{next_sequence:05d}" # Zero-pads to 5 digits
    return invoice_number
