import sqlite3
import uuid
from datetime import datetime, timezone
import logging
from typing import List, Dict, Optional, Any

# Ensure get_db_connection can be resolved.
# Assuming it's in ..utils relative to the cruds directory.
try:
    from ..utils import get_db_connection
except ImportError:
    logging.critical("Failed to import get_db_connection from ..utils. This is a critical error for client_order_money_transfer_agents_crud.")
    # Fallback or re-raise, depending on desired behavior when setup is incorrect.
    # For now, let it fail loudly if get_db_connection is not found.
    raise

# Assuming _manage_conn decorator is available from generic_crud or a similar utility module
# If not, connection management will be manual within each function.
# For this example, let's assume a _manage_conn is defined similarly to other CRUD files.
# If it's in generic_crud.py:
try:
    from .generic_crud import _manage_conn
except ImportError:
    logging.warning("generic_crud._manage_conn not found. Manual connection management will be used or this needs to be addressed.")
    # Define a dummy decorator if it's missing, to allow the code to be structured as intended,
    # but this would mean connections are not actually managed by it.
    def _manage_conn(func):
        def wrapper(*args, **kwargs):
            # This dummy version does not manage connections.
            # Replace with actual implementation or ensure generic_crud is correct.
            return func(*args, **kwargs)
        return wrapper

logger = logging.getLogger(__name__)

TABLE_NAME = "ClientOrder_MoneyTransferAgents"
PRIMARY_KEY = "assignment_id"

@_manage_conn
def assign_agent_to_client_order(
    client_id: str,
    order_id: str,
    agent_id: str,
    assignment_details: Optional[str] = None,
    fee_estimate: Optional[float] = None,
    # user_id: Optional[str] = None, # Not used in insert query per current schema
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """
    Assigns a money transfer agent to a client's order/project.
    """
    if not all([client_id, order_id, agent_id]):
        return {'success': False, 'error': "Client ID, Order ID, and Agent ID are required."}

    assignment_id = str(uuid.uuid4())
    now_utc = datetime.now(timezone.utc).isoformat()

    # Check if an active assignment already exists for this combination (optional, for business logic)
    # query_check = f"SELECT {PRIMARY_KEY} FROM {TABLE_NAME} WHERE client_id = ? AND order_id = ? AND agent_id = ? AND (is_deleted = 0 OR is_deleted IS NULL)"
    # cursor_check = conn.cursor()
    # cursor_check.execute(query_check, (client_id, order_id, agent_id))
    # if cursor_check.fetchone():
    #     return {'success': False, 'error': "This agent is already actively assigned to this client order."}

    sql = f"""
        INSERT INTO {TABLE_NAME} (
            {PRIMARY_KEY}, client_id, order_id, agent_id, assignment_details,
            fee_estimate, assigned_at, updated_at, email_status, is_deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        assignment_id, client_id, order_id, agent_id, assignment_details,
        fee_estimate, now_utc, now_utc, 'Pending', 0
    )
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return {'success': True, 'assignment_id': assignment_id}
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error assigning agent to client order ({client_id}, {order_id}, {agent_id}): {e}")
        # This could be due to non-existent client_id, order_id, or agent_id if FKs are enforced.
        return {'success': False, 'error': f"Database integrity error: {e}. Ensure Client, Order/Project, and Agent exist."}
    except sqlite3.Error as e:
        logger.error(f"Database error assigning agent to client order ({client_id}, {order_id}, {agent_id}): {e}")
        return {'success': False, 'error': str(e)}

@_manage_conn
def get_assigned_agents_for_client_order(
    client_id: str,
    order_id: str,
    conn: Optional[sqlite3.Connection] = None,
    include_deleted: bool = False
) -> List[Dict[str, Any]]:
    """
    Retrieves agents assigned to a specific client and order, with agent and project details.
    """
    if not client_id or not order_id:
        logger.warning("Client ID and Order ID are required for get_assigned_agents_for_client_order.")
        return []

    # Base query
    sql = f"""
        SELECT
            coma.{PRIMARY_KEY}, coma.client_id, coma.order_id, coma.agent_id,
            coma.assignment_details, coma.fee_estimate, coma.assigned_at,
            coma.updated_at, coma.email_status, coma.is_deleted, coma.deleted_at,
            mta.name AS agent_name, mta.email AS agent_email, mta.phone_number AS agent_phone, mta.agent_type,
            p.project_name
        FROM {TABLE_NAME} coma
        JOIN MoneyTransferAgents mta ON coma.agent_id = mta.agent_id
        LEFT JOIN Projects p ON coma.order_id = p.project_id
        WHERE coma.client_id = ? AND coma.order_id = ?
    """
    params = [client_id, order_id]

    if not include_deleted:
        sql += " AND (coma.is_deleted = 0 OR coma.is_deleted IS NULL)"

    sql += " ORDER BY mta.name ASC"

    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching assigned agents for client order ({client_id}, {order_id}): {e}")
        return []

@_manage_conn
def get_assigned_agents_for_client(
    client_id: str,
    conn: Optional[sqlite3.Connection] = None,
    include_deleted: bool = False
) -> List[Dict[str, Any]]:
    """
    Retrieves all agents assigned to a specific client across all orders, with agent and project details.
    """
    if not client_id:
        logger.warning("Client ID is required for get_assigned_agents_for_client.")
        return []

    sql = f"""
        SELECT
            coma.{PRIMARY_KEY}, coma.client_id, coma.order_id, coma.agent_id,
            coma.assignment_details, coma.fee_estimate, coma.assigned_at,
            coma.updated_at, coma.email_status, coma.is_deleted, coma.deleted_at,
            mta.name AS agent_name, mta.email AS agent_email, mta.phone_number AS agent_phone, mta.agent_type,
            p.project_name
        FROM {TABLE_NAME} coma
        JOIN MoneyTransferAgents mta ON coma.agent_id = mta.agent_id
        LEFT JOIN Projects p ON coma.order_id = p.project_id
        WHERE coma.client_id = ?
    """
    params = [client_id]

    if not include_deleted:
        sql += " AND (coma.is_deleted = 0 OR coma.is_deleted IS NULL)"

    sql += " ORDER BY p.project_name ASC, mta.name ASC"

    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching assigned agents for client '{client_id}': {e}")
        return []

@_manage_conn
def update_assignment_details(
    assignment_id: str,
    details: Optional[str] = None,
    fee: Optional[float] = None,
    email_status: Optional[str] = None,
    # user_id: Optional[str] = None, # Not used for audit trail in this version
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """
    Updates details of an agent assignment.
    """
    if not assignment_id:
        return {'success': False, 'error': "Assignment ID is required."}

    fields_to_update = {}
    if details is not None:
        fields_to_update['assignment_details'] = details
    if fee is not None:
        fields_to_update['fee_estimate'] = fee
    if email_status is not None:
        if email_status not in ('Pending', 'Sent', 'Failed', 'Not Applicable'):
            return {'success': False, 'error': "Invalid email_status value."}
        fields_to_update['email_status'] = email_status

    if not fields_to_update:
        return {'success': False, 'error': "No details provided for update."}

    fields_to_update['updated_at'] = datetime.now(timezone.utc).isoformat()

    set_clauses = [f"{key} = ?" for key in fields_to_update.keys()]
    params = list(fields_to_update.values())
    params.append(assignment_id)

    sql = f"UPDATE {TABLE_NAME} SET {', '.join(set_clauses)} WHERE {PRIMARY_KEY} = ?"

    try:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        if cursor.rowcount == 0:
            return {'success': False, 'error': "Assignment not found or no changes made."}
        return {'success': True, 'updated_count': cursor.rowcount}
    except sqlite3.Error as e:
        logger.error(f"Database error updating assignment {assignment_id}: {e}")
        return {'success': False, 'error': str(e)}

@_manage_conn
def unassign_agent_from_client_order(
    assignment_id: str,
    # user_id: Optional[str] = None, # Not used for audit trail in this version
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """
    Soft deletes an agent assignment.
    """
    if not assignment_id:
        return {'success': False, 'error': "Assignment ID is required."}

    now_utc = datetime.now(timezone.utc).isoformat()
    sql = f"UPDATE {TABLE_NAME} SET is_deleted = 1, deleted_at = ?, updated_at = ? WHERE {PRIMARY_KEY} = ? AND (is_deleted = 0 OR is_deleted IS NULL)"
    params = (now_utc, now_utc, assignment_id)

    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if cursor.rowcount == 0:
            return {'success': False, 'error': "Assignment not found or already deleted."}
        return {'success': True, 'message': "Assignment soft deleted."}
    except sqlite3.Error as e:
        logger.error(f"Database error unassigning agent (soft delete) for assignment {assignment_id}: {e}")
        return {'success': False, 'error': str(e)}

# For potential direct import if preferred over module.function access
__all__ = [
    "assign_agent_to_client_order",
    "get_assigned_agents_for_client_order",
    "get_assigned_agents_for_client",
    "update_assignment_details",
    "unassign_agent_from_client_order"
]
