import sqlite3
from datetime import datetime
from ..utils import get_db_connection

# --- CRUD functions for Client_AssignedPersonnel ---
def assign_personnel_to_client(client_id: str, personnel_id: int, role_in_project: str) -> int | None:
    """Assigns a personnel to a client with a specific role. Returns assignment_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO Client_AssignedPersonnel (client_id, personnel_id, role_in_project, assigned_at)
            VALUES (?, ?, ?, ?)
        """
        params = (client_id, personnel_id, role_in_project, now)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Handles UNIQUE constraint violation
        print(f"Personnel {personnel_id} already assigned to client {client_id} with role '{role_in_project}'.")
        return None
    except sqlite3.Error as e:
        print(f"Database error in assign_personnel_to_client: {e}")
        return None
    finally:
        if conn: conn.close()

def get_assigned_personnel_for_client(client_id: str, role_filter: str = None) -> list[dict]:
    """Retrieves assigned personnel for a client, optionally filtered by role.
       Joins with CompanyPersonnel to get personnel details."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT cap.*, cp.name as personnel_name, cp.role as personnel_role, cp.email as personnel_email, cp.phone as personnel_phone
            FROM Client_AssignedPersonnel cap
            JOIN CompanyPersonnel cp ON cap.personnel_id = cp.personnel_id
            WHERE cap.client_id = ?
        """
        params = [client_id]
        if role_filter:
            sql += " AND cap.role_in_project = ?"
            params.append(role_filter)
        sql += " ORDER BY cp.name"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_assigned_personnel_for_client: {e}")
        return []
    finally:
        if conn: conn.close()

def unassign_personnel_from_client(assignment_id: int) -> bool:
    """Unassigns a personnel from a client by assignment_id. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Client_AssignedPersonnel WHERE assignment_id = ?", (assignment_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in unassign_personnel_from_client: {e}")
        return False
    finally:
        if conn: conn.close()
