import sqlite3
import uuid
from datetime import datetime
import logging
from ..utils import get_db_connection # Assuming get_db_connection is in db/utils.py
from ..decorators import _manage_conn # Assuming _manage_conn is in db/decorators.py

# Setup logger
logger = logging.getLogger(__name__)

@_manage_conn
def add_transporter(data: dict, conn: sqlite3.Connection = None) -> str | None:
    """Adds a new transporter. Returns transporter_id (UUID) or None."""
    cursor = conn.cursor()
    new_transporter_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    try:
        sql = """
            INSERT INTO Transporters (
                transporter_id, name, contact_person, phone, email, address,
                service_area, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_transporter_id, data.get('name'), data.get('contact_person'),
            data.get('phone'), data.get('email'), data.get('address'),
            data.get('service_area'), data.get('notes'), now, now
        )
        cursor.execute(sql, params)
        logger.info(f"Transporter '{data.get('name')}' added with ID: {new_transporter_id}")
        return new_transporter_id
    except sqlite3.Error as e:
        logger.error(f"Database error in add_transporter for '{data.get('name')}': {e}", exc_info=True)
        return None

@_manage_conn
def get_transporter_by_id(transporter_id: str, conn: sqlite3.Connection = None) -> dict | None:
    """Retrieves a transporter by its ID."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Transporters WHERE transporter_id = ?", (transporter_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Database error in get_transporter_by_id for ID {transporter_id}: {e}", exc_info=True)
        return None

@_manage_conn
def get_all_transporters(conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves all transporters."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Transporters ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error in get_all_transporters: {e}", exc_info=True)
        return []

@_manage_conn
def update_transporter(transporter_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    """Updates a transporter. Returns True on success."""
    cursor = conn.cursor()
    if not data:
        logger.warning("update_transporter called with no data.")
        return False
    try:
        data['updated_at'] = datetime.utcnow().isoformat() + "Z"

        # Filter out transporter_id from data to prevent it from being in SET clause
        update_data_filtered = {k: v for k, v in data.items() if k != 'transporter_id'}

        set_clauses = [f"{key} = ?" for key in update_data_filtered.keys()]
        params = list(update_data_filtered.values())

        if not set_clauses:
            logger.warning(f"No valid fields to update for transporter ID: {transporter_id}")
            return False # No valid fields to update

        params.append(transporter_id) # Add transporter_id for the WHERE clause
        sql = f"UPDATE Transporters SET {', '.join(set_clauses)} WHERE transporter_id = ?"

        cursor.execute(sql, tuple(params))
        updated = cursor.rowcount > 0
        if updated:
            logger.info(f"Transporter ID {transporter_id} updated.")
        else:
            logger.warning(f"Transporter ID {transporter_id} not found for update or data unchanged.")
        return updated
    except sqlite3.Error as e:
        logger.error(f"Database error in update_transporter for ID {transporter_id}: {e}", exc_info=True)
        return False

@_manage_conn
def delete_transporter(transporter_id: str, conn: sqlite3.Connection = None) -> bool:
    """Deletes a transporter. Returns True on success."""
    cursor = conn.cursor()
    try:
        # Consider ON DELETE SET NULL or RESTRICT for Client_Transporters if direct deletion is too destructive
        cursor.execute("DELETE FROM Transporters WHERE transporter_id = ?", (transporter_id,))
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Transporter ID {transporter_id} deleted.")
        else:
            logger.warning(f"Transporter ID {transporter_id} not found for deletion.")
        return deleted
    except sqlite3.Error as e:
        logger.error(f"Database error in delete_transporter for ID {transporter_id}: {e}", exc_info=True)
        return False
