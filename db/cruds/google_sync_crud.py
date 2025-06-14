import sqlite3
import uuid
from datetime import datetime
import json
import logging
from .generic_crud import _manage_conn, get_db_connection

# --- UserGoogleAccounts CRUD ---
@_manage_conn
def add_user_google_account(data: dict, conn: sqlite3.Connection = None) -> str | None:
    """Adds a new UserGoogleAccount record."""
    cursor = conn.cursor()
    new_id = str(uuid.uuid4())
    now_utc_iso = datetime.utcnow().isoformat() + "Z"
    sql = """
        INSERT INTO UserGoogleAccounts (
            user_google_account_id, user_id, google_account_id, email,
            refresh_token, access_token, token_expiry, scopes,
            last_sync_initiated_at, last_sync_successful_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        new_id, data['user_id'], data['google_account_id'], data['email'],
        data.get('refresh_token'), data.get('access_token'), data.get('token_expiry'),
        json.dumps(data.get('scopes')), data.get('last_sync_initiated_at'), # Ensure scopes is stored as JSON string
        data.get('last_sync_successful_at'), now_utc_iso, now_utc_iso
    )
    try:
        cursor.execute(sql, params)
        return new_id
    except sqlite3.IntegrityError: # Handles UNIQUE constraint on google_account_id or FK violation
        logging.error(f"Integrity error adding UserGoogleAccount for user_id {data.get('user_id')} and google_account_id {data.get('google_account_id')}")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_user_google_account: {e}")
        return None

@_manage_conn
def get_user_google_account_by_user_id(user_id: str, conn: sqlite3.Connection = None) -> dict | None:
    """Fetches a UserGoogleAccount by user_id. Returns the first one if multiple (should not happen with proper logic)."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM UserGoogleAccounts WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        data = dict(row)
        if data.get('scopes'):
            try:
                data['scopes'] = json.loads(data['scopes'])
            except json.JSONDecodeError:
                logging.warning(f"Could not decode scopes JSON for user_google_account_id {data.get('user_google_account_id')}")
                # Keep raw string or set to None/empty list as appropriate
        return data
    return None

@_manage_conn
def get_user_google_account_by_google_account_id(google_account_id: str, conn: sqlite3.Connection = None) -> dict | None:
    """Fetches a UserGoogleAccount by google_account_id."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM UserGoogleAccounts WHERE google_account_id = ?", (google_account_id,))
    row = cursor.fetchone()
    if row:
        data = dict(row)
        if data.get('scopes'):
            try:
                data['scopes'] = json.loads(data['scopes'])
            except json.JSONDecodeError:
                logging.warning(f"Could not decode scopes JSON for user_google_account_id {data.get('user_google_account_id')}")
        return data
    return None

@_manage_conn
def get_user_google_account_by_id(user_google_account_id: str, conn: sqlite3.Connection = None) -> dict | None:
    """Fetches a UserGoogleAccount by its primary key."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM UserGoogleAccounts WHERE user_google_account_id = ?", (user_google_account_id,))
    row = cursor.fetchone()
    if row:
        data = dict(row)
        if data.get('scopes'):
            try:
                data['scopes'] = json.loads(data['scopes'])
            except json.JSONDecodeError:
                logging.warning(f"Could not decode scopes JSON for user_google_account_id {data.get('user_google_account_id')}")
        return data
    return None

@_manage_conn
def update_user_google_account(user_google_account_id: str, data: dict, conn: sqlite3.Connection = None) -> bool:
    """Updates specified fields for a UserGoogleAccount."""
    if not data: return False
    cursor = conn.cursor()
    now_utc_iso = datetime.utcnow().isoformat() + "Z"

    valid_fields = ['refresh_token', 'access_token', 'token_expiry', 'scopes', 'last_sync_initiated_at', 'last_sync_successful_at', 'email']
    fields_to_update = {k: v for k, v in data.items() if k in valid_fields}

    if not fields_to_update: return False # No valid fields to update

    if 'scopes' in fields_to_update and fields_to_update['scopes'] is not None:
        fields_to_update['scopes'] = json.dumps(fields_to_update['scopes'])

    fields_to_update['updated_at'] = now_utc_iso

    set_clauses = [f"{key} = ?" for key in fields_to_update.keys()]
    params = list(fields_to_update.values())
    params.append(user_google_account_id)

    sql = f"UPDATE UserGoogleAccounts SET {', '.join(set_clauses)} WHERE user_google_account_id = ?"
    try:
        cursor.execute(sql, params)
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error in update_user_google_account for {user_google_account_id}: {e}")
        return False

@_manage_conn
def delete_user_google_account(user_google_account_id: str, conn: sqlite3.Connection = None) -> bool:
    """Deletes a UserGoogleAccount by its primary key."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM UserGoogleAccounts WHERE user_google_account_id = ?", (user_google_account_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error in delete_user_google_account for {user_google_account_id}: {e}")
        return False

@_manage_conn
def get_all_user_google_accounts(conn: sqlite3.Connection = None) -> list[dict]:
    """Fetches all UserGoogleAccount records."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM UserGoogleAccounts ORDER BY email")
    accounts = []
    for row in cursor.fetchall():
        data = dict(row)
        if data.get('scopes'):
            try:
                data['scopes'] = json.loads(data['scopes'])
            except json.JSONDecodeError:
                logging.warning(f"Could not decode scopes JSON for user_google_account_id {data.get('user_google_account_id')}")
        accounts.append(data)
    return accounts
# --- End UserGoogleAccounts CRUD ---

# --- ContactSyncLog CRUD ---
@_manage_conn
def add_contact_sync_log(data: dict, conn: sqlite3.Connection = None) -> int | None:
    """Adds a new ContactSyncLog record."""
    cursor = conn.cursor()
    now_utc_iso = datetime.utcnow().isoformat() + "Z"
    sql = """
        INSERT INTO ContactSyncLog (
            user_google_account_id, local_contact_id, local_contact_type, google_contact_id,
            platform_etag, google_etag, last_sync_timestamp, sync_status, sync_direction, error_message,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        data['user_google_account_id'], data['local_contact_id'], data['local_contact_type'],
        data['google_contact_id'], data.get('platform_etag'), data.get('google_etag'),
        data.get('last_sync_timestamp', now_utc_iso), data['sync_status'], data.get('sync_direction'),
        data.get('error_message'), now_utc_iso, now_utc_iso
    )
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Handles UNIQUE constraints or FK violation
        logging.error(f"Integrity error adding ContactSyncLog for user_google_account_id {data.get('user_google_account_id')}, local_contact_id {data.get('local_contact_id')}, google_contact_id {data.get('google_contact_id')}")
        return None
    except sqlite3.Error as e:
        logging.error(f"Database error in add_contact_sync_log: {e}")
        return None

@_manage_conn
def get_contact_sync_log_by_local_contact(user_google_account_id: str, local_contact_id: str, local_contact_type: str, conn: sqlite3.Connection = None) -> dict | None:
    """Fetches a ContactSyncLog by local contact identifiers."""
    cursor = conn.cursor()
    sql = "SELECT * FROM ContactSyncLog WHERE user_google_account_id = ? AND local_contact_id = ? AND local_contact_type = ?"
    cursor.execute(sql, (user_google_account_id, local_contact_id, local_contact_type))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_contact_sync_log_by_google_contact_id(user_google_account_id: str, google_contact_id: str, conn: sqlite3.Connection = None) -> dict | None:
    """Fetches a ContactSyncLog by Google Contact ID."""
    cursor = conn.cursor()
    sql = "SELECT * FROM ContactSyncLog WHERE user_google_account_id = ? AND google_contact_id = ?"
    cursor.execute(sql, (user_google_account_id, google_contact_id))
    # BUG: fetchone() was missing from the original code for this function in crud.py
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def get_contact_sync_log_by_id(sync_log_id: int, conn: sqlite3.Connection = None) -> dict | None:
    """Fetches a ContactSyncLog by its primary key."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ContactSyncLog WHERE sync_log_id = ?", (sync_log_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

@_manage_conn
def update_contact_sync_log(sync_log_id: int, data: dict, conn: sqlite3.Connection = None) -> bool:
    """Updates specified fields for a ContactSyncLog."""
    if not data: return False
    cursor = conn.cursor()
    now_utc_iso = datetime.utcnow().isoformat() + "Z"

    valid_fields = [
        'local_contact_id', 'local_contact_type', 'google_contact_id',
        'platform_etag', 'google_etag', 'last_sync_timestamp',
        'sync_status', 'sync_direction', 'error_message'
    ]
    fields_to_update = {k: v for k, v in data.items() if k in valid_fields}

    if not fields_to_update: return False

    fields_to_update['updated_at'] = now_utc_iso
    if 'last_sync_timestamp' not in fields_to_update: # Also update last_sync_timestamp if not explicitly set
        fields_to_update['last_sync_timestamp'] = now_utc_iso

    set_clauses = [f"{key} = ?" for key in fields_to_update.keys()]
    params = list(fields_to_update.values())
    params.append(sync_log_id)

    sql = f"UPDATE ContactSyncLog SET {', '.join(set_clauses)} WHERE sync_log_id = ?"
    try:
        cursor.execute(sql, params)
        return cursor.rowcount > 0
    except sqlite3.IntegrityError: # Handles UNIQUE constraints
        logging.error(f"Integrity error updating ContactSyncLog for sync_log_id {sync_log_id}")
        return False
    except sqlite3.Error as e:
        logging.error(f"Database error in update_contact_sync_log for {sync_log_id}: {e}")
        return False

@_manage_conn
def delete_contact_sync_log(sync_log_id: int, conn: sqlite3.Connection = None) -> bool:
    """Deletes a ContactSyncLog by its primary key."""
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ContactSyncLog WHERE sync_log_id = ?", (sync_log_id,))
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error in delete_contact_sync_log for {sync_log_id}: {e}")
        return False

@_manage_conn
def get_contacts_pending_sync(user_google_account_id: str, status_filter: str = 'pending_google_update', limit: int = 100, conn: sqlite3.Connection = None) -> list[dict]:
    """Fetches ContactSyncLog records pending sync for a user."""
    cursor = conn.cursor()
    sql = "SELECT * FROM ContactSyncLog WHERE user_google_account_id = ? AND sync_status = ? ORDER BY last_sync_timestamp ASC LIMIT ?"
    cursor.execute(sql, (user_google_account_id, status_filter, limit))
    return [dict(row) for row in cursor.fetchall()]

@_manage_conn
def get_all_sync_logs_for_account(user_google_account_id: str, conn: sqlite3.Connection = None) -> list[dict]:
    """Fetches all ContactSyncLog records for a given UserGoogleAccount."""
    cursor = conn.cursor()
    sql = "SELECT * FROM ContactSyncLog WHERE user_google_account_id = ? ORDER BY last_sync_timestamp DESC"
    cursor.execute(sql, (user_google_account_id,))
    return [dict(row) for row in cursor.fetchall()]
# --- End ContactSyncLog CRUD ---

__all__ = [
    "add_user_google_account",
    "get_user_google_account_by_user_id",
    "get_user_google_account_by_google_account_id",
    "get_user_google_account_by_id",
    "update_user_google_account",
    "delete_user_google_account",
    "get_all_user_google_accounts",
    "add_contact_sync_log",
    "get_contact_sync_log_by_local_contact",
    "get_contact_sync_log_by_google_contact_id",
    "get_contact_sync_log_by_id",
    "update_contact_sync_log",
    "delete_contact_sync_log",
    "get_contacts_pending_sync",
    "get_all_sync_logs_for_account",
]
