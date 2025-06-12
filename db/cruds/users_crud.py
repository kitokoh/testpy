import sqlite3
import uuid
import hashlib
from datetime import datetime
# Import _manage_conn and get_db_connection from generic_crud.py
# Assuming generic_crud.py is in the same directory (db/cruds/):
from .generic_crud import _manage_conn, get_db_connection

# --- Users CRUD ---
@_manage_conn
def add_user(user_data: dict, conn: sqlite3.Connection = None) -> str | None:
    cursor = conn.cursor()
    new_user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    password_hash = hashlib.sha256(user_data['password'].encode('utf-8')).hexdigest()
    sql = "INSERT INTO Users (user_id, username, password_hash, full_name, email, role, is_active, created_at, updated_at, last_login_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    params = (new_user_id, user_data['username'], password_hash, user_data.get('full_name'), user_data['email'], user_data['role'], user_data.get('is_active', True), now, now, user_data.get('last_login_at'))
    try:
        cursor.execute(sql, params)
        return new_user_id
    except sqlite3.IntegrityError: return None

@_manage_conn
def get_user_by_id(user_id: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_user_by_username(username: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_user_by_email(email: str, conn: sqlite3.Connection = None) -> dict | None:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def update_user(user_id: str, user_data: dict, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"

    update_fields = {}
    if 'username' in user_data: update_fields['username'] = user_data['username']
    if 'full_name' in user_data: update_fields['full_name'] = user_data['full_name']
    if 'email' in user_data: update_fields['email'] = user_data['email']
    if 'role' in user_data: update_fields['role'] = user_data['role']
    if 'is_active' in user_data: update_fields['is_active'] = user_data['is_active']
    if 'last_login_at' in user_data: update_fields['last_login_at'] = user_data['last_login_at']
    if 'password' in user_data and user_data['password']:
        update_fields['password_hash'] = hashlib.sha256(user_data['password'].encode('utf-8')).hexdigest()

    if not update_fields: return False
    update_fields['updated_at'] = now # Always update timestamp

    set_clauses = [f"{key} = ?" for key in update_fields.keys()]
    params = list(update_fields.values())
    params.append(user_id)

    sql = f"UPDATE Users SET {', '.join(set_clauses)} WHERE user_id = ?"
    cursor.execute(sql, params)
    return cursor.rowcount > 0

@_manage_conn
def delete_user(user_id: str, conn: sqlite3.Connection = None) -> bool:
    cursor = conn.cursor(); cursor.execute("DELETE FROM Users WHERE user_id = ?", (user_id,)); return cursor.rowcount > 0

@_manage_conn
def verify_user_password(username: str, password: str, conn: sqlite3.Connection = None) -> dict | None:
    # Need to call get_user_by_username using the same connection context
    user = get_user_by_username(username, conn=conn)
    if user and user['is_active']:
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if password_hash == user['password_hash']:
            # Need to call update_user using the same connection context
            update_user(user['user_id'], {'last_login_at': datetime.utcnow().isoformat() + "Z"}, conn=conn)
            return user
    return None
