import sqlite3
from datetime import datetime, timezone
import logging
from .generic_crud import _manage_conn, get_db_connection

logger = logging.getLogger(__name__)

@_manage_conn
def add_task(task_data: dict, conn: sqlite3.Connection = None) -> int | None:
    """
    Adds a new task to the Tasks table.
    Expected task_data keys: project_id, task_name.
    Optional keys: description, status_id, assignee_team_member_id,
                   reporter_team_member_id, due_date, priority,
                   estimated_hours, actual_hours_spent, parent_task_id, completed_at.
    """
    cursor = conn.cursor()
    now_utc = datetime.now(timezone.utc).isoformat()

    required_fields = ['project_id', 'task_name']
    for field in required_fields:
        if field not in task_data or task_data[field] is None:
            logger.error(f"Field '{field}' is required to add a task.")
            return None

    # completed_at should only be set if the task is actually completed.
    # If status_id corresponds to a completion status, completed_at might be set here or in update_task.
    # For add_task, it's usually None unless specified.
    completed_at_val = task_data.get('completed_at')

    sql = """
        INSERT INTO Tasks (
            project_id, task_name, description, status_id,
            assignee_team_member_id, reporter_team_member_id, due_date,
            priority, estimated_hours, actual_hours_spent, parent_task_id,
            created_at, updated_at, completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        task_data['project_id'],
        task_data['task_name'],
        task_data.get('description'),
        task_data.get('status_id'), # Ensure this ID exists in StatusSettings
        task_data.get('assignee_team_member_id'), # Ensure this ID exists in TeamMembers
        task_data.get('reporter_team_member_id'), # Ensure this ID exists in TeamMembers
        task_data.get('due_date'), # ISO date string or None
        task_data.get('priority', 0), # Default priority
        task_data.get('estimated_hours'), # REAL
        task_data.get('actual_hours_spent', 0.0), # REAL, default 0
        task_data.get('parent_task_id'), # INTEGER, Ensure this ID exists in Tasks
        now_utc,
        now_utc,
        completed_at_val
    )
    try:
        cursor.execute(sql, params)
        task_id = cursor.lastrowid
        logger.info(f"Task '{task_data['task_name']}' added with ID: {task_id} for project {task_data['project_id']}.")
        return task_id
    except sqlite3.Error as e:
        logger.error(f"Database error in add_task for '{task_data.get('task_name')}': {e}", exc_info=True)
        return None

@_manage_conn
def get_task_by_id(task_id: int, conn: sqlite3.Connection = None) -> dict | None:
    """Retrieves a task by its ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_tasks_by_project_id(project_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves all tasks for a given project_id, ordered by creation date."""
    cursor = conn.cursor()
    # Consider ordering by priority or due_date as well/instead if more useful
    cursor.execute("SELECT * FROM Tasks WHERE project_id = ? ORDER BY created_at ASC", (project_id,))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_tasks_by_project_id_ordered_by_sequence(project_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    logger.debug(f"Fetching tasks for project_id {project_id}, ordered by sequence.")
    cursor = conn.cursor()
    # Assuming 'sequence_order' is a column in the Tasks table
    # If the column name is different (e.g., 'sequence_number', 'order_index'), adjust it here.
    sql = "SELECT * FROM Tasks WHERE project_id = ? ORDER BY sequence_order ASC"
    try:
        cursor.execute(sql, (project_id,))
        tasks = [dict(row) for row in cursor.fetchall()]
        logger.debug(f"Found {len(tasks)} tasks for project_id {project_id} ordered by sequence.")
        return tasks
    except sqlite3.Error as e:
        logger.error(f"Database error in get_tasks_by_project_id_ordered_by_sequence for project {project_id}: {e}", exc_info=True)
        return [] # Return empty list on error

@_manage_conn
def update_task(task_id: int, task_data: dict, conn: sqlite3.Connection = None) -> bool:
    """
    Updates an existing task.
    Valid fields in task_data: task_name, description, status_id,
    assignee_team_member_id, reporter_team_member_id, due_date, priority,
    estimated_hours, actual_hours_spent, parent_task_id, completed_at.
    """
    cursor = conn.cursor()
    now_utc = datetime.now(timezone.utc).isoformat()

    valid_fields = [
        'task_name', 'description', 'status_id', 'assignee_team_member_id',
        'reporter_team_member_id', 'due_date', 'priority', 'estimated_hours',
        'actual_hours_spent', 'parent_task_id', 'completed_at', 'project_id' # Allow moving task to another project
    ]

    fields_to_update = {k: v for k, v in task_data.items() if k in valid_fields}

    if not fields_to_update:
        logger.info(f"No valid fields provided for updating task {task_id}.")
        return False

    fields_to_update['updated_at'] = now_utc

    set_clauses = [f"{field} = ?" for field in fields_to_update.keys()]
    params = list(fields_to_update.values())
    params.append(task_id)

    sql = f"UPDATE Tasks SET {', '.join(set_clauses)} WHERE task_id = ?"

    try:
        cursor.execute(sql, tuple(params))
        if cursor.rowcount > 0:
            logger.info(f"Task {task_id} updated successfully.")
            return True
        logger.warning(f"No task found with ID {task_id} to update, or data was the same.")
        return False
    except sqlite3.Error as e:
        logger.error(f"Database error updating task {task_id}: {e}", exc_info=True)
        return False

@_manage_conn
def delete_task(task_id: int, conn: sqlite3.Connection = None) -> bool:
    """Deletes a task by its ID (hard delete)."""
    cursor = conn.cursor()
    try:
        # Check for sub-tasks that might need to be re-parented or deleted (cascade not set in schema)
        # For simplicity, this example does not handle orphaned sub-tasks automatically here.
        # A more robust solution might involve setting parent_task_id to NULL for children,
        # or preventing deletion if sub-tasks exist, depending on requirements.
        cursor.execute("DELETE FROM Tasks WHERE task_id = ?", (task_id,))
        if cursor.rowcount > 0:
            logger.info(f"Task {task_id} deleted successfully.")
            return True
        logger.warning(f"No task found with ID {task_id} to delete.")
        return False
    except sqlite3.Error as e:
        # Handle foreign key constraints if other tables reference Tasks without ON DELETE CASCADE
        logger.error(f"Database error deleting task {task_id}: {e}", exc_info=True)
        return False

@_manage_conn
def get_all_tasks(conn: sqlite3.Connection = None, skip: int = 0, limit: int = 100) -> list[dict]:
    """Retrieves all tasks with pagination, ordered by creation date."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, skip))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_tasks_by_assignee_id(assignee_team_member_id: int, conn: sqlite3.Connection = None, skip: int = 0, limit: int = 100) -> list[dict]:
    """Retrieves tasks assigned to a specific team member, with pagination."""
    cursor = conn.cursor()
    # Consider also filtering by non-completed statuses
    cursor.execute("""
        SELECT * FROM Tasks
        WHERE assignee_team_member_id = ?
        ORDER BY due_date ASC, priority DESC, created_at ASC
        LIMIT ? OFFSET ?
    """, (assignee_team_member_id, limit, skip))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def add_task_dependency(task_id: int, depends_on_task_id: int, conn: sqlite3.Connection = None) -> bool:
    logger.info(f"Attempting to add dependency: task {task_id} depends on {depends_on_task_id}")
    return True

@_manage_conn
def get_predecessor_tasks(task_id: int, conn: sqlite3.Connection = None) -> list[dict]:
    logger.info(f"Fetching predecessor tasks for task_id: {task_id}")
    return []

# def remove_task_dependency(task_id: int, depends_on_task_id: int, conn: sqlite3.Connection = None) -> bool:
#     pass

# def get_task_dependencies(task_id: int, conn: sqlite3.Connection = None) -> list[dict]:
#     pass

# def get_tasks_blocking_task(task_id: int, conn: sqlite3.Connection = None) -> list[dict]:
#     pass


__all__ = [
    "add_task",
    "get_task_by_id",
    "get_tasks_by_project_id",
    "get_tasks_by_project_id_ordered_by_sequence",
    "update_task",
    "delete_task",
    "get_all_tasks",
    "get_tasks_by_assignee_id",
    "add_task_dependency",
    "get_predecessor_tasks",
]
