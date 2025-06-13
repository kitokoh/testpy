import sqlite3
from datetime import datetime
from ..utils import get_db_connection

# --- CRUD functions for Client_FreightForwarders ---
def assign_forwarder_to_client(client_id: str, forwarder_id: str, task_description: str = None, cost_estimate: float = None) -> int | None:
    """Assigns a freight forwarder to a client. Returns client_forwarder_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO Client_FreightForwarders (client_id, forwarder_id, task_description, cost_estimate, assigned_at)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (client_id, forwarder_id, task_description, cost_estimate, now)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Handles UNIQUE constraint violation
        print(f"Freight forwarder {forwarder_id} already assigned to client {client_id}.")
        return None
    except sqlite3.Error as e:
        print(f"Database error in assign_forwarder_to_client: {e}")
        return None
    finally:
        if conn: conn.close()

def get_assigned_forwarders_for_client(client_id: str) -> list[dict]:
    """Retrieves assigned freight forwarders for a client.
       Joins with FreightForwarders table to get forwarder details."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT cff.*, ff.name as forwarder_name, ff.contact_person, ff.phone, ff.email
            FROM Client_FreightForwarders cff
            JOIN FreightForwarders ff ON cff.forwarder_id = ff.forwarder_id
            WHERE cff.client_id = ?
            ORDER BY ff.name
        """
        cursor.execute(sql, (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_assigned_forwarders_for_client: {e}")
        return []
    finally:
        if conn: conn.close()

def unassign_forwarder_from_client(client_forwarder_id: int) -> bool:
    """Unassigns a freight forwarder from a client by client_forwarder_id. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Client_FreightForwarders WHERE client_forwarder_id = ?", (client_forwarder_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in unassign_forwarder_from_client: {e}")
        return False
    finally:
        if conn: conn.close()
