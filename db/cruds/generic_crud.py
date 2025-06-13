import sqlite3
import uuid # Required by some CRUD functions, even if not directly in generic
import hashlib # Required by some CRUD functions, even if not directly in generic
from datetime import datetime # Required by some CRUD functions, even if not directly in generic
import json # Required by some CRUD functions, even if not directly in generic
import os
import logging

# Simplified import for get_db_connection using relative path
from ..utils import get_db_connection

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
