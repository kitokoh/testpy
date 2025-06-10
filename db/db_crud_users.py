import sqlite3
import uuid
import hashlib
from datetime import datetime
import json # Keep for SmtpConfig json handling if any, or future use

from .db_config import get_db_connection

# CRUD functions for Companies
def add_company(company_data: dict) -> str | None:
    """Adds a new company. Generates UUID for company_id. Handles created_at, updated_at."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        new_company_id = str(uuid.uuid4())

        sql = """
            INSERT INTO Companies (
                company_id, company_name, address, payment_info, logo_path,
                other_info, is_default, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_company_id,
            company_data.get('company_name'),
            company_data.get('address'),
            company_data.get('payment_info'),
            company_data.get('logo_path'),
            company_data.get('other_info'),
            company_data.get('is_default', False),
            now,  # created_at
            now   # updated_at
        )
        cursor.execute(sql, params)
        conn.commit()
        return new_company_id
    except sqlite3.Error as e:
        print(f"Database error in add_company: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_company_by_id(company_id: str) -> dict | None:
    """Fetches a company by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Companies WHERE company_id = ?", (company_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_company_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_companies() -> list[dict]:
    """Fetches all companies."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Companies ORDER BY company_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_companies: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_company(company_id: str, company_data: dict) -> bool:
    """Updates company details. Manages updated_at."""
    conn = None
    if not company_data:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        company_data['updated_at'] = now

        set_clauses = [f"{key} = ?" for key in company_data.keys() if key != 'company_id']
        params = [value for key, value in company_data.items() if key != 'company_id']

        if not set_clauses:
            return False # No valid fields to update

        params.append(company_id)
        sql = f"UPDATE Companies SET {', '.join(set_clauses)} WHERE company_id = ?"

        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_company: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_company(company_id: str) -> bool:
    """Deletes a company."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # ON DELETE CASCADE will handle CompanyPersonnel
        cursor.execute("DELETE FROM Companies WHERE company_id = ?", (company_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_company: {e}")
        return False
    finally:
        if conn:
            conn.close()

def set_default_company(company_id: str) -> bool:
    """Sets a company as default, ensuring only one company can be default."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        conn.isolation_level = None # Start transaction
        cursor.execute("BEGIN")
        # Unset other defaults
        cursor.execute("UPDATE Companies SET is_default = FALSE WHERE is_default = TRUE AND company_id != ?", (company_id,))
        # Set the new default
        cursor.execute("UPDATE Companies SET is_default = TRUE WHERE company_id = ?", (company_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error in set_default_company: {e}")
        return False
    finally:
        if conn:
            conn.isolation_level = '' # Reset isolation level
            conn.close()

def get_default_company() -> dict | None:
    """
    Retrieves the company marked as default.
    Returns company data as a dictionary if found, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Companies WHERE is_default = TRUE")
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_default_company: {e}")
        return None
    finally:
        if conn:
            conn.close()

# CRUD functions for CompanyPersonnel
def add_company_personnel(personnel_data: dict) -> int | None:
    """Inserts new personnel linked to a company. Returns personnel_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO CompanyPersonnel (company_id, name, role, created_at)
            VALUES (?, ?, ?, ?)
        """
        params = (
            personnel_data.get('company_id'),
            personnel_data.get('name'),
            personnel_data.get('role'),
            now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_company_personnel: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_personnel_for_company(company_id: str, role: str = None) -> list[dict]:
    """Fetches personnel for a company, optionally filtering by role."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM CompanyPersonnel WHERE company_id = ?"
        params = [company_id]
        if role:
            sql += " AND role = ?"
            params.append(role)
        sql += " ORDER BY name"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_personnel_for_company: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_company_personnel(personnel_id: int, personnel_data: dict) -> bool:
    """Updates personnel details."""
    conn = None
    if not personnel_data:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        set_clauses = [f"{key} = ?" for key in personnel_data.keys() if key != 'personnel_id']
        params = [value for key, value in personnel_data.items() if key != 'personnel_id']

        if not set_clauses:
            return False

        params.append(personnel_id)
        sql = f"UPDATE CompanyPersonnel SET {', '.join(set_clauses)} WHERE personnel_id = ?"

        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_company_personnel: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_company_personnel(personnel_id: int) -> bool:
    """Deletes a personnel entry."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM CompanyPersonnel WHERE personnel_id = ?", (personnel_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_company_personnel: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for Users
def add_user(user_data: dict) -> str | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        new_user_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"
        if 'password' not in user_data or not user_data['password']:
            print("Password is required to create a user.")
            return None
        password_hash = hashlib.sha256(user_data['password'].encode('utf-8')).hexdigest()
        sql = """
            INSERT INTO Users (
                user_id, username, password_hash, full_name, email, role,
                is_active, created_at, updated_at, last_login_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_user_id, user_data.get('username'), password_hash,
            user_data.get('full_name'), user_data.get('email'),
            user_data.get('role'), user_data.get('is_active', True),
            now, now, user_data.get('last_login_at')
        )
        cursor.execute(sql, params)
        conn.commit()
        return new_user_id
    except sqlite3.Error as e:
        print(f"Database error in add_user: {e}")
        return None
    finally:
        if conn: conn.close()

def get_user_by_id(user_id: str) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_user_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_user_by_username(username: str) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_user_by_username: {e}")
        return None
    finally:
        if conn: conn.close()

def update_user(user_id: str, user_data: dict) -> bool:
    conn = None
    if not user_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        user_data['updated_at'] = now
        if 'password' in user_data:
            if user_data['password']:
                user_data['password_hash'] = hashlib.sha256(user_data.pop('password').encode('utf-8')).hexdigest()
            else:
                user_data.pop('password')
        set_clauses = []
        params = []
        valid_columns = ['username', 'password_hash', 'full_name', 'email', 'role', 'is_active', 'updated_at', 'last_login_at']
        for key, value in user_data.items():
            if key in valid_columns:
                 set_clauses.append(f"{key} = ?")
                 params.append(value)
        if not set_clauses: return False
        sql = f"UPDATE Users SET {', '.join(set_clauses)} WHERE user_id = ?"
        params.append(user_id)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_user: {e}")
        return False
    finally:
        if conn: conn.close()

def verify_user_password(username: str, password: str) -> dict | None:
    user = get_user_by_username(username)
    if user and user['is_active']:
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if password_hash == user['password_hash']:
            return user
    return None

def delete_user(user_id: str) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_user: {e}")
        return False
    finally:
        if conn: conn.close()

# CRUD functions for TeamMembers
def add_team_member(member_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO TeamMembers (
                user_id, full_name, email, role_or_title, department,
                phone_number, profile_picture_url, is_active, notes,
                hire_date, performance, skills,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            member_data.get('user_id'), member_data.get('full_name'),
            member_data.get('email'), member_data.get('role_or_title'),
            member_data.get('department'), member_data.get('phone_number'),
            member_data.get('profile_picture_url'), member_data.get('is_active', True),
            member_data.get('notes'), member_data.get('hire_date'),
            member_data.get('performance', 0), member_data.get('skills'),
            now, now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_team_member: {e}")
        return None
    finally:
        if conn: conn.close()

def get_team_member_by_id(team_member_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TeamMembers WHERE team_member_id = ?", (team_member_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_team_member_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_team_members(filters: dict = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM TeamMembers"
        params = []
        if filters:
            where_clauses = []
            allowed_filters = ['is_active', 'department', 'user_id']
            for key, value in filters.items():
                if key in allowed_filters:
                    if key == 'is_active' and isinstance(value, bool):
                         where_clauses.append(f"{key} = ?")
                         params.append(1 if value else 0)
                    else:
                        where_clauses.append(f"{key} = ?")
                        params.append(value)
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_team_members: {e}")
        return []
    finally:
        if conn: conn.close()

def update_team_member(team_member_id: int, member_data: dict) -> bool:
    conn = None
    if not member_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        member_data['updated_at'] = now
        set_clauses = []
        params = []
        valid_columns = [
            'user_id', 'full_name', 'email', 'role_or_title', 'department',
            'phone_number', 'profile_picture_url', 'is_active', 'notes',
            'hire_date', 'performance', 'skills', 'updated_at'
        ]
        for key, value in member_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        if not set_clauses: return False
        sql = f"UPDATE TeamMembers SET {', '.join(set_clauses)} WHERE team_member_id = ?"
        params.append(team_member_id)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_team_member: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_team_member(team_member_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM TeamMembers WHERE team_member_id = ?", (team_member_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_team_member: {e}")
        return False
    finally:
        if conn: conn.close()

# CRUD functions for SmtpConfigs
def _ensure_single_default_smtp(cursor: sqlite3.Cursor, exclude_id: int | None = None):
    sql = "UPDATE SmtpConfigs SET is_default = FALSE WHERE is_default = TRUE"
    if exclude_id is not None:
        sql += " AND smtp_config_id != ?"
        cursor.execute(sql, (exclude_id,))
    else:
        cursor.execute(sql)

def add_smtp_config(config_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        conn.isolation_level = None
        cursor = conn.cursor()
        cursor.execute("BEGIN")
        if config_data.get('is_default'):
            _ensure_single_default_smtp(cursor)
        sql = """
            INSERT INTO SmtpConfigs (
                config_name, smtp_server, smtp_port, username, password_encrypted,
                use_tls, is_default, sender_email_address, sender_display_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            config_data.get('config_name'), config_data.get('smtp_server'),
            config_data.get('smtp_port'), config_data.get('username'),
            config_data.get('password_encrypted'),
            config_data.get('use_tls', True),
            config_data.get('is_default', False),
            config_data.get('sender_email_address'),
            config_data.get('sender_display_name')
        )
        cursor.execute(sql, params)
        new_id = cursor.lastrowid
        conn.commit()
        return new_id
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Database error in add_smtp_config: {e}")
        return None
    finally:
        if conn:
            conn.isolation_level = ''
            conn.close()

def get_smtp_config_by_id(smtp_config_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM SmtpConfigs WHERE smtp_config_id = ?", (smtp_config_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_smtp_config_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_default_smtp_config() -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM SmtpConfigs WHERE is_default = TRUE")
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_default_smtp_config: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_smtp_configs() -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM SmtpConfigs ORDER BY config_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_smtp_configs: {e}")
        return []
    finally:
        if conn: conn.close()

def update_smtp_config(smtp_config_id: int, config_data: dict) -> bool:
    conn = None
    if not config_data: return False
    try:
        conn = get_db_connection()
        conn.isolation_level = None
        cursor = conn.cursor()
        cursor.execute("BEGIN")
        if config_data.get('is_default'):
            _ensure_single_default_smtp(cursor, exclude_id=smtp_config_id)
        valid_columns = [
            'config_name', 'smtp_server', 'smtp_port', 'username',
            'password_encrypted', 'use_tls', 'is_default',
            'sender_email_address', 'sender_display_name'
        ]
        current_config_data = {k: v for k,v in config_data.items() if k in valid_columns}
        if not current_config_data:
            conn.rollback()
            return False
        set_clauses = [f"{key} = ?" for key in current_config_data.keys()]
        params = list(current_config_data.values())
        params.append(smtp_config_id)
        sql = f"UPDATE SmtpConfigs SET {', '.join(set_clauses)} WHERE smtp_config_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Database error in update_smtp_config: {e}")
        return False
    finally:
        if conn:
            conn.isolation_level = ''
            conn.close()

def delete_smtp_config(smtp_config_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM SmtpConfigs WHERE smtp_config_id = ?", (smtp_config_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_smtp_config: {e}")
        return False
    finally:
        if conn: conn.close()

def set_default_smtp_config(smtp_config_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        conn.isolation_level = None
        cursor = conn.cursor()
        cursor.execute("BEGIN")
        _ensure_single_default_smtp(cursor, exclude_id=smtp_config_id)
        cursor.execute("UPDATE SmtpConfigs SET is_default = TRUE WHERE smtp_config_id = ?", (smtp_config_id,))
        updated_rows = cursor.rowcount
        conn.commit()
        return updated_rows > 0
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Database error in set_default_smtp_config: {e}")
        return False
    finally:
        if conn:
            conn.isolation_level = ''
            conn.close()

# --- ApplicationSettings Functions ---
def get_setting(key: str) -> str | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM ApplicationSettings WHERE setting_key = ?", (key,))
        row = cursor.fetchone()
        return row['setting_value'] if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_setting: {e}")
        return None
    finally:
        if conn: conn.close()

def set_setting(key: str, value: str) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT OR REPLACE INTO ApplicationSettings (setting_key, setting_value) VALUES (?, ?)"
        cursor.execute(sql, (key, value))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in set_setting: {e}")
        return False
    finally:
        if conn: conn.close()
