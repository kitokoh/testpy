import sqlite3
import uuid
from datetime import datetime
import logging
from .generic_crud import _manage_conn, get_db_connection # Adjust relative import if needed

# Setup logger
logger = logging.getLogger(__name__)

# --- CRUD functions for FreightForwarders ---
@_manage_conn
def add_freight_forwarder(data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor = conn.cursor()
    new_forwarder_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    sql = """
        INSERT INTO FreightForwarders (
            forwarder_id, name, contact_person, phone, email, address,
            services_offered, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        new_forwarder_id, data.get('name'), data.get('contact_person'),
        data.get('phone'), data.get('email'), data.get('address'),
        data.get('services_offered'), data.get('notes'), now, now
    )
    try:
        cursor.execute(sql, params)
        logger.info(f"Freight Forwarder '{data.get('name')}' added with ID: {new_forwarder_id}")
        return new_forwarder_id
    except sqlite3.Error as e:
        logger.error(f"Database error in add_freight_forwarder for '{data.get('name')}': {e}", exc_info=True)
        return None

@_manage_conn
def get_freight_forwarder_by_id(forwarder_id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM FreightForwarders WHERE forwarder_id = ?", (forwarder_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Database error in get_freight_forwarder_by_id for ID {forwarder_id}: {e}", exc_info=True)
        return None

@_manage_conn
def get_all_freight_forwarders(conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM FreightForwarders ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error in get_all_freight_forwarders: {e}", exc_info=True)
        return []

@_manage_conn
def update_freight_forwarder(forwarder_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data:
        logger.warning("update_freight_forwarder called with no data.")
        return False
    cursor = conn.cursor()
    data['updated_at'] = datetime.utcnow().isoformat() + "Z"

    update_data_filtered = {k: v for k, v in data.items() if k != 'forwarder_id'}

    set_clauses = [f"{key} = ?" for key in update_data_filtered.keys()]
    params = list(update_data_filtered.values())

    if not set_clauses:
        logger.warning(f"No valid fields to update for freight forwarder ID: {forwarder_id}")
        return False

    params.append(forwarder_id)
    sql = f"UPDATE FreightForwarders SET {', '.join(set_clauses)} WHERE forwarder_id = ?"
    try:
        cursor.execute(sql, tuple(params))
        updated = cursor.rowcount > 0
        if updated:
            logger.info(f"Freight Forwarder ID {forwarder_id} updated.")
        else:
            logger.warning(f"Freight Forwarder ID {forwarder_id} not found or data unchanged.")
        return updated
    except sqlite3.Error as e:
        logger.error(f"Database error in update_freight_forwarder for ID {forwarder_id}: {e}", exc_info=True)
        return False

@_manage_conn
def delete_freight_forwarder(forwarder_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    try:
        # Consider ON DELETE SET NULL or RESTRICT for Client_FreightForwarders if direct deletion is too destructive
        cursor.execute("DELETE FROM FreightForwarders WHERE forwarder_id = ?", (forwarder_id,))
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Freight Forwarder ID {forwarder_id} deleted.")
        else:
            logger.warning(f"Freight Forwarder ID {forwarder_id} not found for deletion.")
        return deleted
    except sqlite3.Error as e:
        logger.error(f"Database error in delete_freight_forwarder for ID {forwarder_id}: {e}", exc_info=True)
        return False
