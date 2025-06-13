import sqlite3
from datetime import datetime
from ..utils import get_db_connection

# --- CRUD functions for Client_Transporters ---
def assign_transporter_to_client(client_id: str, transporter_id: str, transport_details: str = None, cost_estimate: float = None) -> int | None:
    """Assigns a transporter to a client. Returns client_transporter_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO Client_Transporters (client_id, transporter_id, transport_details, cost_estimate, assigned_at, email_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (client_id, transporter_id, transport_details, cost_estimate, now, 'Pending') # Added email_status
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Handles UNIQUE constraint violation
        print(f"Transporter {transporter_id} already assigned to client {client_id}.")
        return None
    except sqlite3.Error as e:
        print(f"Database error in assign_transporter_to_client: {e}")
        return None
    finally:
        if conn: conn.close()

def get_assigned_transporters_for_client(client_id: str) -> list[dict]:
    """Retrieves assigned transporters for a client.
       Joins with Transporters table to get transporter details."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT ct.*, t.name as transporter_name, t.contact_person, t.phone, t.email, ct.email_status
            FROM Client_Transporters ct
            JOIN Transporters t ON ct.transporter_id = t.transporter_id
            WHERE ct.client_id = ?
            ORDER BY t.name
        """
        cursor.execute(sql, (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_assigned_transporters_for_client: {e}")
        return []
    finally:
        if conn: conn.close()

def unassign_transporter_from_client(client_transporter_id: int) -> bool:
    """Unassigns a transporter from a client by client_transporter_id. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Client_Transporters WHERE client_transporter_id = ?", (client_transporter_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in unassign_transporter_from_client: {e}")
        return False
    finally:
        if conn: conn.close()

def update_client_transporter_email_status(client_transporter_id: int, status: str) -> bool:
    """Updates the email_status for a specific client-transporter assignment."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "UPDATE Client_Transporters SET email_status = ? WHERE client_transporter_id = ?"
        cursor.execute(sql, (status, client_transporter_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_client_transporter_email_status: {e}")
        return False
    finally:
        if conn: conn.close()
