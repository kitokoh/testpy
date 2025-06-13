import sqlite3
from datetime import datetime
import logging

from .generic_crud import _manage_conn

logger = logging.getLogger(__name__)

@_manage_conn
def add_task(task_data: dict, conn: sqlite3.Connection = None) -> int | None:
    """Adds a new task to the Tasks table."""
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    sql = """
        INSERT INTO Tasks (
            project_id, task_name, description, status_id,
            assignee_team_member_id, reporter_team_member_id,
            due_date, priority, estimated_hours, actual_hours_spent,
            parent_task_id, created_at, updated_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        task_data.get('project_id'),
        task_data.get('task_name'),
        task_data.get('description'),
        task_data.get('status_id'),
        task_data.get('assignee_team_member_id'),
        task_data.get('reporter_team_member_id'),
        task_data.get('due_date'),
        task_data.get('priority', 0),
        task_data.get('estimated_hours'),
        task_data.get('actual_hours_spent'),
        task_data.get('parent_task_id'),
        now,
        now,
        task_data.get('completed_at')
    )
    try:
        cursor.execute(sql, params)
        # conn.commit() # Handled by _manage_conn
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Database error in add_task: {e}", exc_info=True)
        # conn.rollback() # Handled by _manage_conn
        return None

@_manage_conn
def get_task_by_id(task_id: int, conn: sqlite3.Connection = None) -> dict | None:
    """Retrieves a specific task by its ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_tasks_by_project_id(project_id: str, filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves all tasks for a given project_id, optionally filtered."""
    cursor = conn.cursor()
    sql = "SELECT * FROM Tasks WHERE project_id = ?"
    params = [project_id]
    if filters:
        clauses = []
        valid_filters = ['assignee_team_member_id', 'status_id', 'priority'] # Add more as needed
        for key, value in filters.items():
            if key in valid_filters:
                clauses.append(f"{key} = ?")
                params.append(value)
        if clauses:
            sql += " AND " + " AND ".join(clauses)

    sql += " ORDER BY created_at DESC" # Default ordering
    cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def update_task(task_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    """Updates an existing task."""
    if not data:
        return False

    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    data['updated_at'] = now

    valid_cols = [
        'project_id', 'task_name', 'description', 'status_id',
        'assignee_team_member_id', 'reporter_team_member_id',
        'due_date', 'priority', 'estimated_hours', 'actual_hours_spent',
        'parent_task_id', 'updated_at', 'completed_at'
    ]

    fields_to_update = {k: v for k, v in data.items() if k in valid_cols}

    if not fields_to_update:
        logger.info(f"No valid fields provided for updating task_id {task_id}")
        return False

    set_clauses = [f"{key} = ?" for key in fields_to_update.keys()]
    params_list = list(fields_to_update.values())
    params_list.append(task_id)

    sql = f"UPDATE Tasks SET {', '.join(set_clauses)} WHERE task_id = ?"

    try:
        cursor.execute(sql, tuple(params_list))
        # conn.commit() # Handled by _manage_conn
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error in update_task for task_id {task_id}: {e}", exc_info=True)
        # conn.rollback() # Handled by _manage_conn
        return False

@_manage_conn
def delete_task(task_id: int, conn: sqlite3.Connection = None) -> bool:
    """Deletes a task by its ID."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Tasks WHERE task_id = ?", (task_id,))
        # conn.commit() # Handled by _manage_conn
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error in delete_task for task_id {task_id}: {e}", exc_info=True)
        # conn.rollback() # Handled by _manage_conn
        return False

@_manage_conn
def get_all_tasks(active_only: bool = False, project_id_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves all tasks, optionally filtered for active tasks or by project_id."""
    cursor = conn.cursor()
    sql = "SELECT t.* FROM Tasks t"
    params = []
    conditions = []

    if active_only:
        # Assuming StatusSettings table and relevant columns (is_completion_status, is_archival_status) exist
        # This might require joining with StatusSettings if status_id itself doesn't denote active/inactive
        # For simplicity, if 'status_id' is directly used to mark completion (e.g. a specific ID means completed),
        # adjust this logic. If 'active' is a direct column in Tasks, use that.
        # The version from db/crud.py did:
        # sql += " LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id";
        # conditions.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")
        # This requires StatusSettings table to be defined and populated correctly.
        # For now, let's assume a simplified status check if StatusSettings is complex to join here without full context
        # If a specific status_id means "completed" or "archived", filter it out.
        # This is a placeholder: actual active logic might depend on StatusSettings table.
        # For now, if 'status_id' for 'completed' is known, e.g. 5: conditions.append("t.status_id != 5")
        # The original code from db/crud.py had a join, let's replicate that structure.
        sql += " LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"
        conditions.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE OR t.status_id IS NULL)")


    if project_id_filter:
        conditions.append("t.project_id = ?")
        params.append(project_id_filter)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY t.created_at DESC"
    cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_tasks_by_assignee_id(assignee_id: int, active_only: bool = False, conn: sqlite3.Connection = None) -> list[dict]:
    """Retrieves tasks assigned to a specific team member, optionally filtered for active tasks."""
    cursor = conn.cursor()
    sql = "SELECT t.* FROM Tasks t"
    params = []
    conditions = ["t.assignee_team_member_id = ?"]
    params.append(assignee_id)

    if active_only:
        # Similar to get_all_tasks, assuming StatusSettings join for active status
        sql += " LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"
        conditions.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE OR t.status_id IS NULL)")

    sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY t.due_date ASC, t.priority DESC" # Tasks nearing deadline and higher priority first

    cursor.execute(sql, tuple(params))
    return [dict(row) for row in cursor.fetchall()]

__all__ = [
    "add_task",
    "get_task_by_id",
    "get_tasks_by_project_id",
    "update_task",
    "delete_task",
    "get_all_tasks",
    "get_tasks_by_assignee_id"
]
