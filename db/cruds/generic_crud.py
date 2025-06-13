import sqlite3
import uuid # Required by some CRUD functions, even if not directly in generic
import hashlib # Required by some CRUD functions, even if not directly in generic
from datetime import datetime # Required by some CRUD functions, even if not directly in generic
import json # Required by some CRUD functions, even if not directly in generic
import os
import logging

# Configuration and Utilities
try:
    from ... import db_config # For db_config.py in app/
    # from ... import config    # config.py might not be needed directly by generic_crud's connection logic
    from ..connection import get_db_connection # Changed to import from db.connection
except (ImportError, ValueError) as e_import_primary:
    import sys
    # Determine the /app directory path relative to this file (db/cruds/generic_crud.py)
    # generic_crud.py -> cruds/ -> db/ -> app/
    app_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if app_root_dir not in sys.path:
        sys.path.append(app_root_dir)

    # Path to the 'db' directory, which contains 'utils.py'
    db_dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This should be /app/db
    if db_dir_path not in sys.path:
         sys.path.append(db_dir_path)

    try:
        import db_config # Assumes db_config.py is at app_root_dir (added to sys.path)
        from connection import get_db_connection # Assumes connection.py is in db/ (db_dir_path added to sys.path)
    except ImportError as e:
        print(f"CRITICAL: db_config.py or connection.py (for get_db_connection) not found in generic_crud.py fallback. Error: {e}")
        class db_config: # Minimal fallback for db_config
            DATABASE_NAME = "app_data_fallback_generic.db"
            APP_ROOT_DIR_CONTEXT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # app/
            LOGO_SUBDIR_CONTEXT = "company_logos_fallback_generic"

        def get_db_connection(db_name=None): # Fallback get_db_connection
            name_to_connect = db_name if db_name else db_config.DATABASE_NAME
            db_path = os.path.join(db_config.APP_ROOT_DIR_CONTEXT, name_to_connect)
            conn_fallback = sqlite3.connect(db_path)
            conn_fallback.row_factory = sqlite3.Row
            return conn_fallback

# Helper to manage connection lifecycle for CRUD functions
def _manage_conn(func):
    def wrapper(*args, **kwargs):
        conn_passed = kwargs.get('conn')
        conn_is_external = conn_passed is not None
        conn_to_use = conn_passed if conn_is_external else get_db_connection()

        try:
            kwargs_for_func = {**kwargs, 'conn': conn_to_use}
            result = func(*args, **kwargs_for_func)

            if not conn_is_external:
                write_ops_keywords = ['add', 'update', 'delete', 'set', 'link', 'unlink', 'assign', 'unassign', 'populate', 'insert', 'execute', 'remove', 'create', 'drop', 'alter']
                is_write_operation = any(op in func.__name__ for op in write_ops_keywords)

                # Check if the function returned a cursor and it performed a write operation
                # This is a heuristic and might need refinement based on actual function behaviors
                if hasattr(result, 'lastrowid') and result.lastrowid is not None: # e.g. INSERT
                    is_write_operation = True
                elif hasattr(result, 'rowcount') and result.rowcount > 0 and not func.__name__.startswith('get') and not func.__name__.startswith('fetch'): # e.g. UPDATE, DELETE
                    is_write_operation = True


                if is_write_operation:
                    conn_to_use.commit()
            return result
        except sqlite3.Error as e:
            # logging.error(f"Database error in {func.__name__}: {e}") # Consider logging
            if not conn_is_external and conn_to_use:
                conn_to_use.rollback()
            raise
        finally:
            if not conn_is_external and conn_to_use:
                conn_to_use.close()
    return wrapper


# Generic CRUD Base Class
class GenericCRUD:
    """
    A base class providing generic CRUD (Create, Read, Update, Delete) operations
    that can be inherited by specific CRUD classes for different database tables.

    This class is designed to work with SQLite and uses a connection management
    decorator (`@_manage_conn`) for its methods. Child classes should typically
    define `table_name` and `id_column` attributes in their `__init__` method
    if they intend to use these generic methods directly without overriding or
    if they call super() to these methods.
    """
    @_manage_conn
    def get_by_id(self, table_name: str, id_column: str, item_id: any, conn: sqlite3.Connection) -> dict | None:
        """
        Fetches a single record from a specified table by its ID.

        Args:
            table_name (str): The name of the table to query.
            id_column (str): The name of the ID column in the table.
            item_id (any): The ID of the item to fetch.
            conn (sqlite3.Connection): The database connection object.

        Returns:
            dict | None: A dictionary representing the record if found, otherwise None.
        """
        query = f"SELECT * FROM {table_name} WHERE {id_column} = ?"
        cursor = conn.execute(query, (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @_manage_conn
    def delete_by_id(self, table_name: str, id_column: str, item_id: any, conn: sqlite3.Connection) -> bool:
        """
        Deletes a record from a specified table by its ID.
        This performs a hard delete.

        Args:
            table_name (str): The name of the table.
            id_column (str): The name of the ID column.
            item_id (any): The ID of the item to delete.
            conn (sqlite3.Connection): The database connection object.

        Returns:
            bool: True if a record was deleted, False otherwise.
        """
        query = f"DELETE FROM {table_name} WHERE {id_column} = ?"
        cursor = conn.execute(query, (item_id,))
        return cursor.rowcount > 0

    @_manage_conn
    def exists_by_id(self, table_name: str, id_column: str, item_id: any, conn: sqlite3.Connection) -> bool:
        """
        Checks if a record exists in a specified table by its ID.

        Args:
            table_name (str): The name of the table.
            id_column (str): The name of the ID column.
            item_id (any): The ID of the item to check for.
            conn (sqlite3.Connection): The database connection object.

        Returns:
            bool: True if the record exists, False otherwise.
        """
        query = f"SELECT 1 FROM {table_name} WHERE {id_column} = ?"
        cursor = conn.execute(query, (item_id,))
        return cursor.fetchone() is not None

    @_manage_conn
    def get_all(self, table_name: str, conn: sqlite3.Connection, order_by: str = None) -> list[dict]:
        """
        Fetches all records from a specified table, with optional ordering.

        Args:
            table_name (str): The name of the table.
            conn (sqlite3.Connection): The database connection object.
            order_by (str, optional): A string to use for the ORDER BY clause
                                      (e.g., "column_name ASC"). Defaults to None.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary represents a record.
                        Returns an empty list if the table is empty or not found.
        """
        query = f"SELECT * FROM {table_name}"
        if order_by:
            query += f" ORDER BY {order_by}"
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # Placeholder for query construction helper
    # def _build_query(self, query_type: str, **kwargs) -> str:
    #     """Helper method to construct SQL queries dynamically."""
    #     # This method would handle more complex query building logic
    #     # For example, handling multiple conditions, joins, etc.
    #     pass