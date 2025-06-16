import sqlite3
import uuid
import hashlib
import os # For os.urandom
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

@_manage_conn
def get_all_users(conn: sqlite3.Connection = None, skip: int = 0, limit: int = 100) -> list[dict]:
    print(f"Placeholder: get_all_users called with session (conn parameter), skip={skip}, limit={limit}")
    # Example for a real implementation:
    # cursor = conn.cursor()
    # cursor.execute("SELECT * FROM Users ORDER BY username LIMIT ? OFFSET ?", (limit, skip))
    # rows = cursor.fetchall()
    # return [dict(row) for row in rows]
    return []
import re # For email validation
from .generic_crud import GenericCRUD, _manage_conn, get_db_connection # Updated import
import logging

class UsersCRUD(GenericCRUD):
    """
    Manages CRUD operations for users, with a strong focus on security,
    particularly password handling (salting and hashing) and soft deletes.
    Inherits from GenericCRUD for some basic operations.
    """
    def __init__(self):
        """
        Initializes the UsersCRUD class.
        Sets table_name, id_column for GenericCRUD, and a basic regex for email validation.
        """
        self.table_name = "Users"
        self.id_column = "user_id"
        # Basic email regex (not fully RFC compliant but good enough for many cases)
        self.email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

    def _generate_salt(self) -> str:
        """
        Generates a cryptographically secure random salt.

        Returns:
            str: A hex-encoded string representation of the 16-byte salt.
        """
        return os.urandom(16).hex()

    def _hash_password(self, password: str, salt: str) -> str:
        """
        Hashes a password using SHA256 combined with a provided salt.
        The salt is expected to be a hex string, which is converted to bytes before use.

        Args:
            password (str): The plain-text password to hash.
            salt (str): The salt as a hex-encoded string. This salt should be unique per user.

        Returns:
            str: A hex-encoded string representation of the SHA256 hash.
        """
        salt_bytes = bytes.fromhex(salt)
        password_bytes = password.encode('utf-8')
        return hashlib.sha256(salt_bytes + password_bytes).hexdigest()

    @_manage_conn
    def add_user(self, user_data: dict, conn: sqlite3.Connection = None) -> dict:
        """
        Adds a new user to the database.

        Performs input validation for required fields, email format, and password complexity.
        Generates a unique salt for the user, hashes the password with this salt (SHA256),
        and stores both the salt and the hash. Sets 'is_deleted' to 0 by default.

        Args:
            user_data (dict): Data for the new user. Must include 'username', 'password',
                              'email', 'role'. Optional: 'full_name', 'is_active', 'last_login_at'.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'id': new_user_id} on success,
                  {'success': False, 'error': 'message'} on failure.
        """
        required_fields = ['username', 'password', 'email', 'role']
        for field in required_fields:
            if not user_data.get(field):
                return {'success': False, 'error': f"Missing required field: {field}"}

        if not re.match(self.email_regex, user_data['email']):
            return {'success': False, 'error': "Invalid email format."}

        # Basic password complexity: min 8 characters
        if len(user_data['password']) < 8:
            return {'success': False, 'error': "Password must be at least 8 characters long."}

        cursor = conn.cursor()
        new_user_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"

        salt = self._generate_salt()
        password_hash = self._hash_password(user_data['password'], salt)

        is_deleted = 0
        deleted_at = None

        sql = """INSERT INTO Users
                 (user_id, username, password_hash, salt, full_name, email, role,
                  is_active, created_at, updated_at, last_login_at, is_deleted, deleted_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (new_user_id, user_data['username'], password_hash, salt,
                  user_data.get('full_name'), user_data['email'], user_data['role'],
                  user_data.get('is_active', True), now, now, user_data.get('last_login_at'),
                  is_deleted, deleted_at)
        try:
            cursor.execute(sql, params)
            return {'success': True, 'id': new_user_id}
        except sqlite3.IntegrityError as e:
            logging.error(f"IntegrityError adding user {user_data['username']}: {e}")
            if 'username' in str(e).lower(): # Basic check
                return {'success': False, 'error': "Username already exists."}
            if 'email' in str(e).lower():
                return {'success': False, 'error': "Email already exists."}
            return {'success': False, 'error': f"Database integrity error: {str(e)}"}
        except sqlite3.Error as e:
            logging.error(f"SQLite error adding user {user_data['username']}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def get_user_by_id(self, user_id: str, conn: sqlite3.Connection = None, include_deleted: bool = False) -> dict | None:
        """
        Fetches a user by their user_id.
        Uses GenericCRUD.get_by_id and applies soft delete logic.
        Note: This method, by using super().get_by_id, will return all fields,
        including 'password_hash' and 'salt'. For external use, prefer methods that
        explicitly exclude sensitive data or use an additional filtering step.

        Args:
            user_id (str): The UUID of the user.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted users. Defaults to False.

        Returns:
            dict | None: User data if found, else None.
        """
        user = super().get_by_id(self.table_name, self.id_column, user_id, conn=conn)
        if user:
            if not include_deleted and (user.get('is_deleted') == 1 or user.get('is_deleted') is True):
                return None
            # SECURITY NOTE: `password_hash` and `salt` are returned here.
            # This method should be used with caution, typically for internal processes
            # or followed by filtering if exposed externally.
        return user

    @_manage_conn
    def get_user_by_username(self, username: str, conn: sqlite3.Connection = None, include_deleted: bool = False, internal_use: bool = False) -> dict | None:
        """
        Fetches a user by their username.

        Args:
            username (str): The username to search for.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted users. Defaults to False.
            internal_use (bool, optional): If True, 'password_hash' and 'salt' are included
                                           in the returned dict. Defaults to False, excluding them.
                                           This should only be True for trusted internal processes
                                           like password verification.

        Returns:
            dict | None: User data if found, else None. Sensitive fields are excluded unless
                         `internal_use` is True.
        """
        query = f"SELECT * FROM {self.table_name} WHERE username = ?"
        params = [username]

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        user = cursor.fetchone()

        if user:
            user_dict = dict(user)
            if not include_deleted and (user_dict.get('is_deleted') == 1 or user_dict.get('is_deleted') is True):
                return None
            if not internal_use: # Avoid leaking sensitive info unless necessary
                user_dict.pop('password_hash', None)
                user_dict.pop('salt', None)
            return user_dict
        return None

    @_manage_conn
    def get_user_by_email(self, email: str, conn: sqlite3.Connection = None, include_deleted: bool = False) -> dict | None:
        """
        Fetches a user by their email address.

        Args:
            email (str): The email address to search for.
            conn (sqlite3.Connection, optional): Database connection.
            include_deleted (bool, optional): If True, includes soft-deleted users. Defaults to False.

        Returns:
            dict | None: User data if found, else None. 'password_hash' and 'salt' are excluded.
        """
        query = f"SELECT * FROM {self.table_name} WHERE email = ?"
        params = [email]

        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        user = cursor.fetchone()
        if user:
            user_dict = dict(user)
            if not include_deleted and (user_dict.get('is_deleted') == 1 or user_dict.get('is_deleted') is True):
                return None
            # Avoid leaking sensitive info
            user_dict.pop('password_hash', None)
            user_dict.pop('salt', None)
            return user_dict
        return None

    @_manage_conn
    def update_user(self, user_id: str, user_data: dict, conn: sqlite3.Connection = None) -> dict:
        """
        Updates an existing user's information.

        If 'password' is in `user_data`, it will be re-hashed with a *new* salt.
        Validates required `user_id`, email format, and password complexity if provided.
        Allows updating soft delete fields `is_deleted` and `deleted_at`.

        Args:
            user_id (str): The UUID of the user to update.
            user_data (dict): Data to update. Keys should correspond to column names.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'updated_count': count} or {'success': False, 'error': 'message'}.
        """
        if not user_id:
            return {'success': False, 'error': "User ID is required for update."}
        if not user_data:
            return {'success': False, 'error': "No data provided for update."}

        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"

        update_fields = {}
        valid_cols = ['username', 'full_name', 'email', 'role', 'is_active',
                        'last_login_at', 'is_deleted', 'deleted_at']

        for col in valid_cols:
            if col in user_data:
                if col == 'email' and not re.match(self.email_regex, user_data['email']):
                    return {'success': False, 'error': "Invalid email format."}
                update_fields[col] = user_data[col]

        if 'password' in user_data and user_data['password']:
            if len(user_data['password']) < 8: # Basic password complexity check
                 return {'success': False, 'error': "Password must be at least 8 characters long."}
            new_salt = self._generate_salt()
            update_fields['salt'] = new_salt
            update_fields['password_hash'] = self._hash_password(user_data['password'], new_salt)

        if not update_fields:
            return {'success': False, 'error': "No valid fields to update."}

        update_fields['updated_at'] = now

        set_clauses = [f"{key} = ?" for key in update_fields.keys()]
        params = list(update_fields.values())
        params.append(user_id)

        sql = f"UPDATE {self.table_name} SET {', '.join(set_clauses)} WHERE {self.id_column} = ?"
        try:
            cursor.execute(sql, params)
            return {'success': cursor.rowcount > 0, 'updated_count': cursor.rowcount}
        except sqlite3.IntegrityError as e:
            logging.error(f"IntegrityError updating user {user_id}: {e}")
            return {'success': False, 'error': f"Database integrity error: {str(e)}"}
        except sqlite3.Error as e:
            logging.error(f"SQLite error updating user {user_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def delete_user(self, user_id: str, conn: sqlite3.Connection = None) -> dict:
        """
        Soft deletes a user by setting `is_deleted = 1`, `deleted_at` to current UTC time,
        and `is_active = 0`.

        Args:
            user_id (str): The UUID of the user to soft delete.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict: {'success': True, 'message': 'User soft deleted.'} on success,
                  {'success': False, 'error': 'User not found or no change made.'} if no update,
                  {'success': False, 'error': 'DB error message'} on database error.
        """
        if not user_id:
            return {'success': False, 'error': "User ID is required for deletion."}

        now = datetime.utcnow().isoformat() + "Z"
        # Set is_active to False as well for soft deleted users as a common practice.
        update_data = {'is_deleted': 1, 'deleted_at': now, 'is_active': 0}

        set_clauses = [f"{key} = ?" for key in update_data.keys()]
        params = list(update_data.values())
        params.append(user_id)

        sql = f"UPDATE {self.table_name} SET {', '.join(set_clauses)} WHERE {self.id_column} = ?"
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if cursor.rowcount > 0:
                return {'success': True, 'message': f"User {user_id} soft deleted."}
            else:
                return {'success': False, 'error': f"User {user_id} not found or no change made."}
        except sqlite3.Error as e:
            logging.error(f"SQLite error soft deleting user {user_id}: {e}")
            return {'success': False, 'error': str(e)}

    @_manage_conn
    def verify_user_password(self, username: str, password: str, conn: sqlite3.Connection = None) -> dict | None:
        """
        Verifies a user's password against the stored salted hash.
        Updates `last_login_at` on successful verification.

        Args:
            username (str): The username of the user.
            password (str): The plain-text password to verify.
            conn (sqlite3.Connection, optional): Database connection.

        Returns:
            dict | None: User data (excluding hash and salt) if verification is successful
                         and user is active and not deleted. None otherwise.
        """
        # Get user, including salt and hash - use internal_use=True
        user = self.get_user_by_username(username, conn=conn, include_deleted=False, internal_use=True)

        if user and user.get('is_active'): # Ensure user is active and not soft-deleted
            # Salt and password_hash must exist if user was created with add_user
            if not user.get('salt') or not user.get('password_hash'):
                logging.error(f"User {username} is missing salt or password_hash. Cannot verify.")
                return None

            expected_hash = self._hash_password(password, user['salt'])
            if expected_hash == user['password_hash']:
                # Update last_login_at - call update_user method of this class instance
                self.update_user(user['user_id'], {'last_login_at': datetime.utcnow().isoformat() + "Z"}, conn=conn)
                # Return user dict without sensitive info for external use
                user.pop('password_hash', None)
                user.pop('salt', None)
                return user
        return None

    @_manage_conn
    def get_all_users(self, conn: sqlite3.Connection = None, limit: int = None, offset: int = 0, include_deleted: bool = False) -> list[dict]:
        """
        Retrieves all users, with optional pagination and inclusion of soft-deleted records.
        'password_hash' and 'salt' are excluded from the returned user data.

        Args:
            conn (sqlite3.Connection, optional): Database connection.
            limit (int, optional): Max number of records for pagination.
            offset (int, optional): Offset for pagination. Defaults to 0.
            include_deleted (bool, optional): If True, includes soft-deleted users.
                                              Defaults to False.

        Returns:
            list[dict]: A list of user records.
        """
        sql = f"SELECT * FROM {self.table_name} u" # Alias for clarity
        q_params = []
        conditions = []

        if not include_deleted:
            conditions.append("(u.is_deleted IS NULL OR u.is_deleted = 0)")

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY u.username" # Default ordering

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            q_params.extend([limit, offset])

        try:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(q_params))
            users = [dict(row) for row in cursor.fetchall()]
            # Remove sensitive info
            for user in users:
                user.pop('password_hash', None)
                user.pop('salt', None)
            return users
        except sqlite3.Error as e:
            logging.error(f"Error getting all users: {e}")
            return []

# Instantiate the CRUD class for easy import and use elsewhere
users_crud_instance = UsersCRUD()
