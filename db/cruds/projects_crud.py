import sqlite3
import uuid
from datetime import datetime
import logging
from .generic_crud import get_db_connection, _manage_conn # Relative import

# Setup logger
logger = logging.getLogger(__name__)

@_manage_conn
def add_project(project_data: dict, conn: sqlite3.Connection = None) -> str | None:
    """
    Adds a new project to the database.
    Generates a UUID for project_id.
    Sets created_at and updated_at timestamps.
    """
    cursor = conn.cursor()
    project_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    try:
        cursor.execute("""
            INSERT INTO Projects (
                project_id, client_id, project_name, description, start_date,
                deadline_date, budget, status_id, progress_percentage,
                manager_team_member_id, priority, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            project_data.get('client_id'),
            project_data.get('project_name'),
            project_data.get('description'),
            project_data.get('start_date'),
            project_data.get('deadline_date'),
            project_data.get('budget'),
            project_data.get('status_id'),
            project_data.get('progress_percentage', 0),
            project_data.get('manager_team_member_id'),
            project_data.get('priority', 0),
            now,
            now
        ))
        logger.info(f"Project '{project_data.get('project_name')}' added with ID: {project_id}")
        return project_id
    except sqlite3.Error as e:
        logger.error(f"Error adding project '{project_data.get('project_name')}': {e}", exc_info=True)
        return None

@_manage_conn
def get_project_by_id(project_id: str, conn: sqlite3.Connection = None) -> dict | None:
    """Retrieves a project by its ID."""
    cursor = conn.cursor()
    # Fetching related names for better display if needed directly
    cursor.execute("""
        SELECT
            p.*,
            c.client_name,
            s.status_name as project_status_name,
            u.full_name as manager_full_name
        FROM Projects p
        LEFT JOIN Clients c ON p.client_id = c.client_id
        LEFT JOIN StatusSettings s ON p.status_id = s.status_id
        LEFT JOIN Users u ON p.manager_team_member_id = u.user_id
        WHERE p.project_id = ?
    """, (project_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_projects_by_client_id(client_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves all projects for a given client_id."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            p.*,
            s.status_name as project_status_name,
            u.full_name as manager_full_name
        FROM Projects p
        LEFT JOIN StatusSettings s ON p.status_id = s.status_id
        LEFT JOIN Users u ON p.manager_team_member_id = u.user_id
        WHERE p.client_id = ?
        ORDER BY p.project_name
    """, (client_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@_manage_conn
def get_all_projects(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    """
    Retrieves all projects, optionally filtered.
    Filters can include 'client_id', 'status_id', 'manager_team_member_id', 'priority'.
    """
    cursor = conn.cursor()
    query = """
        SELECT
            p.*,
            c.client_name,
            s.status_name as project_status_name,
            u.full_name as manager_full_name
        FROM Projects p
        LEFT JOIN Clients c ON p.client_id = c.client_id
        LEFT JOIN StatusSettings s ON p.status_id = s.status_id
        LEFT JOIN Users u ON p.manager_team_member_id = u.user_id
    """
    params = []
    conditions = []

    if filters:
        if filters.get('client_id'):
            conditions.append("p.client_id = ?")
            params.append(filters['client_id'])
        if filters.get('status_id'):
            conditions.append("p.status_id = ?")
            params.append(filters['status_id'])
        if filters.get('manager_team_member_id'): # Assuming manager_team_member_id in Projects table is user_id
            conditions.append("p.manager_team_member_id = ?")
            params.append(filters['manager_team_member_id'])
        if filters.get('priority') is not None: # Priority can be 0
            conditions.append("p.priority = ?")
            params.append(filters['priority'])
        # Add more filters as needed, e.g., for date ranges, name search etc.

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY p.deadline_date DESC, p.project_name ASC" # Example ordering

    cursor.execute(query, params)
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

@_manage_conn
def update_project(project_id: str, project_data: dict, conn: sqlite3.Connection = None) -> bool:
    """
    Updates an existing project.
    Updates the updated_at timestamp.
    """
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    # Construct SET clause dynamically for fields present in project_data
    set_clauses = []
    params = []

    allowed_fields = [
        'client_id', 'project_name', 'description', 'start_date', 'deadline_date',
        'budget', 'status_id', 'progress_percentage', 'manager_team_member_id', 'priority'
    ]

    for field in allowed_fields:
        if field in project_data:
            set_clauses.append(f"{field} = ?")
            params.append(project_data[field])

    if not set_clauses:
        logger.warning(f"No valid fields provided for updating project ID: {project_id}")
        return False

    set_clauses.append("updated_at = ?")
    params.append(now)
    params.append(project_id) # For the WHERE clause

    sql = f"UPDATE Projects SET {', '.join(set_clauses)} WHERE project_id = ?"

    try:
        cursor.execute(sql, tuple(params))
        updated = cursor.rowcount > 0
        if updated:
            logger.info(f"Project ID {project_id} updated.")
        else:
            logger.warning(f"Project ID {project_id} not found for update or data unchanged.")
        return updated
    except sqlite3.Error as e:
        logger.error(f"Error updating project ID {project_id}: {e}", exc_info=True)
        return False

@_manage_conn
def delete_project(project_id: str, conn: sqlite3.Connection = None) -> bool:
    """
    Deletes a project by its ID.
    Note: Associated tasks, KPIs, etc., might need to be handled separately or via CASCADE if set in schema.
    The schema for Tasks and KPIs has ON DELETE CASCADE for project_id.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Projects WHERE project_id = ?", (project_id,))
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Project ID {project_id} deleted.")
        else:
            logger.warning(f"Project ID {project_id} not found for deletion.")
        return deleted
    except sqlite3.Error as e:
        logger.error(f"Error deleting project ID {project_id}: {e}", exc_info=True)
        return False

@_manage_conn
def get_total_projects_count(conn: sqlite3.Connection = None) -> int:
    """Retrieves the total number of projects."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(project_id) as total_count FROM Projects")
        row = cursor.fetchone()
        return row['total_count'] if row else 0
    except sqlite3.Error as e:
        logger.error(f"Database error in get_total_projects_count: {e}", exc_info=True)
        return 0

@_manage_conn
def get_active_projects_count(conn: sqlite3.Connection = None) -> int:
    """
    Retrieves the count of active projects.
    Active projects are those not linked to a status marked as completion or archival,
    or projects with no status_id (considered active by default).
    """
    cursor = conn.cursor()
    try:
        # Select projects whose status_id is not in the set of completion or archival statuses,
        # or projects who have no status_id (considered active by default).
        sql = """
            SELECT COUNT(p.project_id) as active_count
            FROM Projects p
            LEFT JOIN StatusSettings ss ON p.status_id = ss.status_id
            WHERE (ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE) OR p.status_id IS NULL
        """
        cursor.execute(sql)
        row = cursor.fetchone()
        return row['active_count'] if row else 0
    except sqlite3.Error as e:
        logger.error(f"Database error in get_active_projects_count: {e}", exc_info=True)
        return 0
