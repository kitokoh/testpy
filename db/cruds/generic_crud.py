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
    from ... import config    # For config.py in app/
    from ..utils import get_db_connection
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
        import db_config
        from utils import get_db_connection # utils is in db/
    except ImportError as e:
        print(f"CRITICAL: db_config.py or utils.py (for get_db_connection) not found in generic_crud.py. Using fallbacks. Error: {e}")
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
