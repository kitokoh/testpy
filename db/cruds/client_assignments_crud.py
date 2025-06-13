import sqlite3
import uuid # Though not used by these specific functions, good for consistency if other IDs were UUIDs
from datetime import datetime
import logging
from .generic_crud import _manage_conn, get_db_connection # Adjust relative import if needed

# Setup logger
logger = logging.getLogger(__name__)

# --- Client_AssignedPersonnel ---
@_manage_conn
def assign_personnel_to_client(client_id: str, personnel_id: int, role_in_project: str, conn: sqlite3.Connection = None) -> int | None:
    """Assigns a personnel to a client with a specific role. Returns assignment_id or None."""
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    sql = """
        INSERT INTO Client_AssignedPersonnel (client_id, personnel_id, role_in_project, assigned_at)
        VALUES (?, ?, ?, ?)
    """
    params = (client_id, personnel_id, role_in_project, now)
    try:
        cursor.execute(sql, params)
        logger.info(f"Assigned personnel {personnel_id} to client {client_id} with role '{role_in_project}'.")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"Personnel {personnel_id} already assigned to client {client_id} with role '{role_in_project}'.")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error assigning personnel to client: {e}", exc_info=True)
        return None

@_manage_conn
def get_assigned_personnel_for_client(client_id: str, role_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves assigned personnel for a client, optionally filtered by role."""
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
    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error getting assigned personnel for client {client_id}: {e}", exc_info=True)
        return []

@_manage_conn
def unassign_personnel_from_client(assignment_id: int, conn: sqlite3.Connection = None) -> bool:
    """Unassigns a personnel from a client by assignment_id. Returns True on success."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Client_AssignedPersonnel WHERE assignment_id = ?", (assignment_id,))
        logger.info(f"Unassigned personnel with assignment ID {assignment_id}.")
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error unassigning personnel (assignment ID {assignment_id}): {e}", exc_info=True)
        return False

# --- Client_Transporters ---
@_manage_conn
def assign_transporter_to_client(client_id: str, transporter_id: str, transport_details: str = None, cost_estimate: float = None, conn: sqlite3.Connection = None) -> int | None:
    """Assigns a transporter to a client. Returns client_transporter_id or None."""
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    sql = """
        INSERT INTO Client_Transporters (client_id, transporter_id, transport_details, cost_estimate, assigned_at, email_status)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    params = (client_id, transporter_id, transport_details, cost_estimate, now, 'Pending')
    try:
        cursor.execute(sql, params)
        logger.info(f"Assigned transporter {transporter_id} to client {client_id}.")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"Transporter {transporter_id} already assigned to client {client_id}.")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error assigning transporter to client: {e}", exc_info=True)
        return None

@_manage_conn
def get_assigned_transporters_for_client(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves assigned transporters for a client."""
    cursor = conn.cursor()
    sql = """
        SELECT ct.*, t.name as transporter_name, t.contact_person, t.phone, t.email, ct.email_status
        FROM Client_Transporters ct
        JOIN Transporters t ON ct.transporter_id = t.transporter_id
        WHERE ct.client_id = ?
        ORDER BY t.name
    """
    try:
        cursor.execute(sql, (client_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error getting assigned transporters for client {client_id}: {e}", exc_info=True)
        return []

@_manage_conn
def unassign_transporter_from_client(client_transporter_id: int, conn: sqlite3.Connection = None) -> bool:
    """Unassigns a transporter from a client by client_transporter_id. Returns True on success."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Client_Transporters WHERE client_transporter_id = ?", (client_transporter_id,))
        logger.info(f"Unassigned transporter with client_transporter_id {client_transporter_id}.")
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error unassigning transporter (ID {client_transporter_id}): {e}", exc_info=True)
        return False

@_manage_conn
def update_client_transporter_email_status(client_transporter_id: int, status: str, conn: sqlite3.Connection = None) -> bool:
    """Updates the email_status for a specific client-transporter assignment."""
    cursor = conn.cursor()
    sql = "UPDATE Client_Transporters SET email_status = ? WHERE client_transporter_id = ?"
    try:
        cursor.execute(sql, (status, client_transporter_id))
        logger.info(f"Updated email status for client_transporter_id {client_transporter_id} to {status}.")
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error updating email status for client_transporter_id {client_transporter_id}: {e}", exc_info=True)
        return False

# --- Client_FreightForwarders ---
@_manage_conn
def assign_forwarder_to_client(client_id: str, forwarder_id: str, task_description: str = None, cost_estimate: float = None, conn: sqlite3.Connection = None) -> int | None:
    """Assigns a freight forwarder to a client. Returns client_forwarder_id or None."""
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    sql = """
        INSERT INTO Client_FreightForwarders (client_id, forwarder_id, task_description, cost_estimate, assigned_at)
        VALUES (?, ?, ?, ?, ?)
    """
    params = (client_id, forwarder_id, task_description, cost_estimate, now)
    try:
        cursor.execute(sql, params)
        logger.info(f"Assigned forwarder {forwarder_id} to client {client_id}.")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"Freight forwarder {forwarder_id} already assigned to client {client_id}.")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error assigning forwarder to client: {e}", exc_info=True)
        return None

@_manage_conn
def get_assigned_forwarders_for_client(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves assigned freight forwarders for a client."""
    cursor = conn.cursor()
    sql = """
        SELECT cff.*, ff.name as forwarder_name, ff.contact_person, ff.phone, ff.email
        FROM Client_FreightForwarders cff
        JOIN FreightForwarders ff ON cff.forwarder_id = ff.forwarder_id
        WHERE cff.client_id = ?
        ORDER BY ff.name
    """
    try:
        cursor.execute(sql, (client_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error getting assigned forwarders for client {client_id}: {e}", exc_info=True)
        return []

@_manage_conn
def unassign_forwarder_from_client(client_forwarder_id: int, conn: sqlite3.Connection = None) -> bool:
    """Unassigns a freight forwarder from a client by client_forwarder_id. Returns True on success."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Client_FreightForwarders WHERE client_forwarder_id = ?", (client_forwarder_id,))
        logger.info(f"Unassigned forwarder with client_forwarder_id {client_forwarder_id}.")
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error unassigning forwarder (ID {client_forwarder_id}): {e}", exc_info=True)
        return False
