import sqlite3
import uuid
from datetime import datetime
from ..utils import get_db_connection

# --- CRUD functions for FreightForwarders ---
def add_freight_forwarder(data: dict) -> str | None:
    """Adds a new freight forwarder. Returns forwarder_id (UUID) or None."""
    conn = None
    try:
        conn = get_db_connection()
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
        cursor.execute(sql, params)
        conn.commit()
        return new_forwarder_id
    except sqlite3.Error as e:
        print(f"Database error in add_freight_forwarder: {e}")
        return None
    finally:
        if conn: conn.close()

def get_freight_forwarder_by_id(forwarder_id: str) -> dict | None:
    """Retrieves a freight forwarder by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM FreightForwarders WHERE forwarder_id = ?", (forwarder_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_freight_forwarder_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_freight_forwarders() -> list[dict]:
    """Retrieves all freight forwarders."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM FreightForwarders ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_freight_forwarders: {e}")
        return []
    finally:
        if conn: conn.close()

def update_freight_forwarder(forwarder_id: str, data: dict) -> bool:
    """Updates a freight forwarder. Returns True on success."""
    conn = None
    if not data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        data['updated_at'] = datetime.utcnow().isoformat() + "Z"
        set_clauses = [f"{key} = ?" for key in data.keys() if key != 'forwarder_id']
        params = [value for key, value in data.items() if key != 'forwarder_id']
        if not set_clauses: return False
        params.append(forwarder_id)
        sql = f"UPDATE FreightForwarders SET {', '.join(set_clauses)} WHERE forwarder_id = ?"
        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_freight_forwarder: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_freight_forwarder(forwarder_id: str) -> bool:
    """Deletes a freight forwarder. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Consider ON DELETE SET NULL or RESTRICT for Client_FreightForwarders
        cursor.execute("DELETE FROM FreightForwarders WHERE forwarder_id = ?", (forwarder_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_freight_forwarder: {e}")
        return False
    finally:
        if conn: conn.close()
