import sqlite3
from .generic_crud import _manage_conn, get_db_connection
import logging
from datetime import datetime

@_manage_conn
def get_milestones_for_project(project_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    # Basic join with StatusSettings to get status_name and color_hex
    sql = """
        SELECT m.*, ss.status_name, ss.color_hex
        FROM Milestones m
        LEFT JOIN StatusSettings ss ON m.status_id = ss.status_id
        WHERE m.project_id = ?
        ORDER BY m.due_date ASC
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (project_id,))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Error getting milestones for project {project_id}: {e}")
        return []

@_manage_conn
def add_milestone(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor()
    now_utc_iso = datetime.utcnow().isoformat() + "Z" # Ensure 'Z' for UTC indication

    # Validate required fields
    if not all(k in data for k in ['project_id', 'milestone_name', 'due_date', 'status_id']):
        logging.error("Missing required fields for adding milestone.")
        # Consider raising ValueError or returning a specific error code/message
        return None

    sql = """INSERT INTO Milestones (project_id, milestone_name, description, due_date, status_id, created_at, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?)"""
    params = (
        data['project_id'],
        data['milestone_name'],
        data.get('description'), # Optional
        data['due_date'],
        data['status_id'],
        now_utc_iso,
        now_utc_iso
    )
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Failed to add milestone '{data.get('milestone_name')}': {e}")
        return None

@_manage_conn
def get_milestone_by_id(milestone_id: int, conn: sqlite3.Connection = None) -> dict | None:
    sql = """
        SELECT m.*, ss.status_name, ss.color_hex
        FROM Milestones m
        LEFT JOIN StatusSettings ss ON m.status_id = ss.status_id
        WHERE m.milestone_id = ?
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql, (milestone_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Error getting milestone by id {milestone_id}: {e}")
        return None

@_manage_conn
def update_milestone(milestone_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    now_utc_iso = datetime.utcnow().isoformat() + "Z"

    # Ensure required fields for update are present
    if not all(k in data for k in ['milestone_name', 'due_date', 'status_id']):
        logging.error(f"Missing required fields for updating milestone {milestone_id}.")
        # Consider raising ValueError or returning a specific error code/message
        return False

    sql = """UPDATE Milestones SET
             milestone_name = ?, description = ?, due_date = ?, status_id = ?, updated_at = ?
             WHERE milestone_id = ?"""
    params = (
        data['milestone_name'],
        data.get('description'), # Optional
        data['due_date'],
        data['status_id'],
        now_utc_iso,
        milestone_id
    )
    try:
        cursor.execute(sql, params)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to update milestone {milestone_id}: {e}")
        return False

@_manage_conn
def delete_milestone(milestone_id: int, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    sql = "DELETE FROM Milestones WHERE milestone_id = ?"
    try:
        cursor.execute(sql, (milestone_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Failed to delete milestone {milestone_id}: {e}")
        return False
