import sqlite3
from .generic_crud import _manage_conn, get_db_connection
import logging
from datetime import datetime

@_manage_conn
def add_activity_log(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    sql = """INSERT INTO ActivityLogs (user_id, action_type, details, related_entity_type, related_entity_id, created_at)
             VALUES (?, ?, ?, ?, ?, ?)"""
    params = (
        data.get('user_id'),
        data.get('action_type'),
        data.get('details'),
        data.get('related_entity_type'),
        data.get('related_entity_id'),
        now
    )
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Failed to add activity log: {e}")
        return None

@_manage_conn
def get_activity_logs(limit: int = 100, offset: int = 0, user_id_filter: str = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor = conn.cursor()
    sql = "SELECT * FROM ActivityLogs"
    filters_clauses = []
    params = []

    if user_id_filter:
        filters_clauses.append("user_id = ?")
        params.append(user_id_filter)

    # Add more filters here if needed, e.g., by date range, action_type, related_entity

    if filters_clauses:
        sql += " WHERE " + " AND ".join(filters_clauses)

    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        cursor.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logging.error(f"Failed to get activity logs: {e}")
        return []

@_manage_conn
def get_activity_log_by_id(log_id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    sql = "SELECT * FROM ActivityLogs WHERE log_id = ?"
    try:
        cursor.execute(sql, (log_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logging.error(f"Failed to get activity log by ID {log_id}: {e}")
        return None
