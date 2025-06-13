import sqlite3
import uuid
from datetime import datetime
from ..utils import get_db_connection

# --- CRUD functions for Transporters ---
def add_transporter(data: dict) -> str | None:
    """Adds a new transporter. Returns transporter_id (UUID) or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        new_transporter_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
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
        conn.commit()
        return new_transporter_id
    except sqlite3.Error as e:
        print(f"Database error in add_transporter: {e}")
        return None
    finally:
        if conn: conn.close()

def get_transporter_by_id(transporter_id: str) -> dict | None:
    """Retrieves a transporter by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Transporters WHERE transporter_id = ?", (transporter_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_transporter_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_transporters() -> list[dict]:
    """Retrieves all transporters."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Transporters ORDER BY name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_transporters: {e}")
        return []
    finally:
        if conn: conn.close()

def update_transporter(transporter_id: str, data: dict) -> bool:
    """Updates a transporter. Returns True on success."""
    conn = None
    if not data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        data['updated_at'] = datetime.utcnow().isoformat() + "Z"
        set_clauses = [f"{key} = ?" for key in data.keys() if key != 'transporter_id']
        params = [value for key, value in data.items() if key != 'transporter_id']
        if not set_clauses: return False
        params.append(transporter_id)
        sql = f"UPDATE Transporters SET {', '.join(set_clauses)} WHERE transporter_id = ?"
        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_transporter: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_transporter(transporter_id: str) -> bool:
    """Deletes a transporter. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Consider ON DELETE SET NULL or RESTRICT for Client_Transporters if direct deletion is too destructive
        cursor.execute("DELETE FROM Transporters WHERE transporter_id = ?", (transporter_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_transporter: {e}")
        return False
    finally:
        if conn: conn.close()
