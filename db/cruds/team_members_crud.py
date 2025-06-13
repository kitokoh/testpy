import sqlite3
import uuid # Not used in these specific functions, but good for consistency
from datetime import datetime
import logging
from .generic_crud import _manage_conn, get_db_connection

logger = logging.getLogger(__name__)

@_manage_conn
def add_team_member(data: dict, conn: sqlite3.Connection = None) -> int | None:
    cursor=conn.cursor()
    now=datetime.utcnow().isoformat()+"Z"
    sql="""INSERT INTO TeamMembers
             (user_id, full_name, email, role_or_title, department, phone_number,
              profile_picture_url, is_active, notes, hire_date, performance, skills,
              created_at, updated_at)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    params=(data.get('user_id'), data.get('full_name'), data.get('email'),
            data.get('role_or_title'), data.get('department'), data.get('phone_number'),
            data.get('profile_picture_url'), data.get('is_active',True),
            data.get('notes'), data.get('hire_date'), data.get('performance',0),
            data.get('skills'), now, now)
    try:
        if not data.get('full_name') or not data.get('email'):
            logger.error("full_name and email are required for adding a team member.")
            return None
        cursor.execute(sql,params)
        return cursor.lastrowid
    except sqlite3.IntegrityError as e: # Handles UNIQUE constraints (e.g. email, user_id)
        logger.error(f"Integrity error adding team member {data.get('full_name')}: {e}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error adding team member {data.get('full_name')}: {e}")
        return None

@_manage_conn
def get_team_member_by_id(id: int, conn: sqlite3.Connection = None) -> dict | None:
    cursor=conn.cursor()
    try:
        cursor.execute("SELECT * FROM TeamMembers WHERE team_member_id = ?",(id,))
        row=cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Database error getting team member by ID {id}: {e}")
        return None

@_manage_conn
def get_all_team_members(filters: dict = None, conn: sqlite3.Connection = None) -> list[dict]:
    cursor=conn.cursor()
    sql="SELECT * FROM TeamMembers"
    q_params=[]
    if filters:
        clauses=[]
        valid_filters=['is_active','department','user_id']
        for k,v in filters.items():
            if k in valid_filters:
                if k=='is_active' and isinstance(v,bool):
                    clauses.append(f"{k}=?")
                    q_params.append(1 if v else 0)
                elif v is not None: # Ensure other filter values are not None before adding
                    clauses.append(f"{k}=?")
                    q_params.append(v)
        if clauses:
            sql+=" WHERE "+" AND ".join(clauses)
    sql += " ORDER BY full_name" # Added default ordering
    try:
        cursor.execute(sql,q_params)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Database error getting all team members with filters {filters}: {e}")
        return []

@_manage_conn
def update_team_member(id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    if not data: return False
    cursor=conn.cursor()
    now=datetime.utcnow().isoformat()+"Z"
    data['updated_at']=now

    valid_cols=['user_id','full_name','email','role_or_title','department',
                'phone_number','profile_picture_url','is_active','notes',
                'hire_date','performance','skills','updated_at']
    to_set={k:v for k,v in data.items() if k in valid_cols}

    if not to_set:
        logger.info(f"No valid fields to update for team member ID {id}.")
        return False

    set_c=[f"{k}=?" for k in to_set.keys()]
    params=list(to_set.values())
    params.append(id)

    sql=f"UPDATE TeamMembers SET {', '.join(set_c)} WHERE team_member_id = ?"
    try:
        cursor.execute(sql,params)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error updating team member ID {id}: {e}")
        return False

@_manage_conn
def delete_team_member(id: int, conn: sqlite3.Connection = None) -> bool:
    cursor=conn.cursor()
    try:
        cursor.execute("DELETE FROM TeamMembers WHERE team_member_id = ?",(id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Database error deleting team member ID {id}: {e}")
        return False
