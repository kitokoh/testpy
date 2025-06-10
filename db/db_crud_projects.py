import sqlite3
import uuid
from datetime import datetime

from .db_config import get_db_connection

# CRUD functions for Projects
def add_project(project_data: dict) -> str | None:
    """
    Adds a new project to the database.
    Returns the new project_id if successful, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        new_project_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"

        sql = """
            INSERT INTO Projects (
                project_id, client_id, project_name, description, start_date,
                deadline_date, budget, status_id, progress_percentage,
                manager_team_member_id, priority, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_project_id,
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
            now,  # created_at
            now   # updated_at
        )

        cursor.execute(sql, params)
        conn.commit()
        return new_project_id
    except sqlite3.Error as e:
        print(f"Database error in add_project: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_project_by_id(project_id: str) -> dict | None:
    """Retrieves a project by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Projects WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_project_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_projects_by_client_id(client_id: str) -> list[dict]:
    """Retrieves all projects for a given client_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Projects WHERE client_id = ?", (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_projects_by_client_id: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_projects(filters: dict = None) -> list[dict]:
    """
    Retrieves all projects, optionally applying filters.
    Allowed filters: client_id, status_id, manager_team_member_id, priority.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "SELECT * FROM Projects"
        params = []

        if filters:
            where_clauses = []
            allowed_filters = ['client_id', 'status_id', 'manager_team_member_id', 'priority']
            for key, value in filters.items():
                if key in allowed_filters:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_projects: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_project(project_id: str, project_data: dict) -> bool:
    """
    Updates an existing project. Sets updated_at.
    Returns True if update was successful, False otherwise.
    """
    conn = None
    if not project_data:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat() + "Z"
        project_data['updated_at'] = now

        set_clauses = []
        params = []

        valid_columns = [
            'client_id', 'project_name', 'description', 'start_date', 'deadline_date',
            'budget', 'status_id', 'progress_percentage', 'manager_team_member_id',
            'priority', 'updated_at'
        ]
        for key, value in project_data.items():
            if key in valid_columns:
                 set_clauses.append(f"{key} = ?")
                 params.append(value)

        if not set_clauses:
            return False

        sql = f"UPDATE Projects SET {', '.join(set_clauses)} WHERE project_id = ?"
        params.append(project_id)

        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_project: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_project(project_id: str) -> bool:
    """Deletes a project. Returns True if deletion was successful."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Projects WHERE project_id = ?", (project_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_project: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for Tasks
def add_task(task_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO Tasks (
                project_id, task_name, description, status_id, assignee_team_member_id,
                reporter_team_member_id, due_date, priority, estimated_hours,
                actual_hours_spent, parent_task_id, created_at, updated_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            task_data.get('project_id'), task_data.get('task_name'),
            task_data.get('description'), task_data.get('status_id'),
            task_data.get('assignee_team_member_id'), task_data.get('reporter_team_member_id'),
            task_data.get('due_date'), task_data.get('priority', 0),
            task_data.get('estimated_hours'), task_data.get('actual_hours_spent'),
            task_data.get('parent_task_id'), now, now, task_data.get('completed_at')
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_task: {e}")
        return None
    finally:
        if conn: conn.close()

def get_task_by_id(task_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_task_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_tasks_by_project_id(project_id: str, filters: dict = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Tasks WHERE project_id = ?"
        params = [project_id]
        if filters:
            where_clauses = []
            allowed_filters = ['assignee_team_member_id', 'status_id', 'priority']
            for key, value in filters.items():
                if key in allowed_filters:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
            if where_clauses:
                sql += " AND " + " AND ".join(where_clauses)
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_tasks_by_project_id: {e}")
        return []
    finally:
        if conn: conn.close()

def update_task(task_id: int, task_data: dict) -> bool:
    conn = None
    if not task_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        task_data['updated_at'] = now
        set_clauses = []
        params = []
        valid_columns = [
            'project_id', 'task_name', 'description', 'status_id', 'assignee_team_member_id',
            'reporter_team_member_id', 'due_date', 'priority', 'estimated_hours',
            'actual_hours_spent', 'parent_task_id', 'updated_at', 'completed_at'
        ]
        for key, value in task_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        if not set_clauses: return False
        sql = f"UPDATE Tasks SET {', '.join(set_clauses)} WHERE task_id = ?"
        params.append(task_id)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_task: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_task(task_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Tasks WHERE task_id = ?", (task_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_task: {e}")
        return False
    finally:
        if conn: conn.close()

# CRUD functions for KPIs
def add_kpi(kpi_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO KPIs (
                project_id, name, value, target, trend, unit, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            kpi_data.get('project_id'), kpi_data.get('name'), kpi_data.get('value'),
            kpi_data.get('target'), kpi_data.get('trend'), kpi_data.get('unit'),
            now, now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_kpi: {e}")
        return None
    finally:
        if conn: conn.close()

def get_kpi_by_id(kpi_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM KPIs WHERE kpi_id = ?", (kpi_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_kpi_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_kpis_for_project(project_id: str) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM KPIs WHERE project_id = ?", (project_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_kpis_for_project: {e}")
        return []
    finally:
        if conn: conn.close()

def update_kpi(kpi_id: int, kpi_data: dict) -> bool:
    conn = None
    if not kpi_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        kpi_data['updated_at'] = now
        set_clauses = []
        params = []
        valid_columns = ['project_id', 'name', 'value', 'target', 'trend', 'unit', 'updated_at']
        for key, value in kpi_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        if not set_clauses: return False
        sql = f"UPDATE KPIs SET {', '.join(set_clauses)} WHERE kpi_id = ?"
        params.append(kpi_id)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_kpi: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_kpi(kpi_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM KPIs WHERE kpi_id = ?", (kpi_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_kpi: {e}")
        return False
    finally:
        if conn: conn.close()

# StatusSettings lookup functions
def get_all_status_settings(status_type: str = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings"
        params = []
        if status_type:
            sql += " WHERE status_type = ?"
            params.append(status_type)
        sql += " ORDER BY status_type, status_name"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_all_status_settings: {e}")
        return []
    finally:
        if conn: conn.close()

def get_status_setting_by_id(status_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings WHERE status_id = ?", (status_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_status_setting_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_status_setting_by_name(status_name: str, status_type: str) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings WHERE status_name = ? AND status_type = ?", (status_name, status_type))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_status_setting_by_name: {e}")
        return None
    finally:
        if conn: conn.close()

# Task-related lookup functions
def get_all_tasks(active_only: bool = False, project_id_filter: str = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT t.* FROM Tasks t"
        params = []
        where_clauses = []
        if active_only:
            sql += " LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"
            where_clauses.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")
        if project_id_filter:
            where_clauses.append("t.project_id = ?")
            params.append(project_id_filter)
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY t.created_at DESC"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_tasks: {e}")
        return []
    finally:
        if conn: conn.close()

def get_tasks_by_assignee_id(assignee_team_member_id: int, active_only: bool = False) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT t.* FROM Tasks t"
        params = []
        where_clauses = ["t.assignee_team_member_id = ?"]
        params.append(assignee_team_member_id)
        if active_only:
            sql += " LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id"
            where_clauses.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY t.due_date ASC, t.priority DESC"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_tasks_by_assignee_id: {e}")
        return []
    finally:
        if conn: conn.close()
