import sqlite3
import uuid # Required by some CRUD functions, even if not directly in generic
import hashlib # Required by some CRUD functions, even if not directly in generic
from datetime import datetime # Required by some CRUD functions, even if not directly in generic
import json # Required by some CRUD functions, even if not directly in generic
import os # Keep os if used by other parts of the file, but not for path manipulation for config.
import logging

# Configuration and Utilities
try:
    # This is the primary and now should be the ONLY way it gets get_db_connection
    from ..connection import get_db_connection
except ImportError as e:
    # If this import fails, it's a problem with db.connection or the package structure.
    # generic_crud.py should not try to work around it with its own config loading.
    logging.critical(f"CRITICAL: Failed to import get_db_connection from ..connection in generic_crud.py. Error: {e}")
    # Re-raise the error as the CRUD operations cannot function without a db connection.
    raise ImportError(f"Essential import get_db_connection from ..connection failed in generic_crud.py") from e

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

    # Helper function to convert sqlite3.Row objects to dictionaries
    # This is useful if not using conn.row_factory = sqlite3.Row globally,
    # or if needing to ensure dict conversion at a specific point.
    # However, with conn.row_factory = sqlite3.Row, direct dict(row) works.
    # Let's define it here for explicitness and potential complex object handling later.
    def _object_to_dict(self, db_row: sqlite3.Row) -> dict | None:
        """Converts a sqlite3.Row object to a dictionary."""
        if db_row is None:
            return None
        return dict(db_row)

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
        return self._object_to_dict(row)

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
        return [self._object_to_dict(row) for row in rows]

    # Placeholder for query construction helper
    # def _build_query(self, query_type: str, **kwargs) -> str:
    #     """Helper method to construct SQL queries dynamically."""
    #     # This method would handle more complex query building logic
    #     # For example, handling multiple conditions, joins, etc.
    #     pass

# Utility function, can be outside the class if preferred, or static.
# Making it a top-level function for easier import/use by other modules if needed.
def object_to_dict(db_row: sqlite3.Row) -> dict | None:
    """Converts a sqlite3.Row object to a dictionary."""
    if db_row is None:
        return None
    return dict(db_row)