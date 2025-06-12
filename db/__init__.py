"""
Database package for the application.

This package handles all database interactions, including schema initialization,
CRUD operations, and database utility functions.
"""

# Import and expose key functions from the schema module
from .schema import initialize_database

# Import and expose key functions from the utils module
from .utils import get_db_connection, format_currency, get_document_context_data

# Import and expose all functions from the crud module
# This makes all CRUD functions directly available under db.function_name
# e.g., db.add_user(), db.get_client_by_id()
from .crud import *

# Define __all__ for the db package to specify what is exported when 'from db import *' is used.
# It should ideally include all names from crud.__all__ plus the explicitly imported ones above.
# For now, let's re-export based on what's imported. A more dynamic approach might be
# to combine __all__ lists from submodules if they exist and are accurate.

# We assume crud.__all__ is comprehensive for functions from crud.py
# If crud.__all__ is not defined or needs to be combined, this would need adjustment.
_crud_exports = [name for name in dir() if not name.startswith('_') and callable(globals()[name]) and globals()[name].__module__ == 'db.crud']


__all__ = [
    "initialize_database",
    "get_db_connection",
    "format_currency",
    "get_document_context_data",
] + _crud_exports

# Clean up to avoid exposing dir and _crud_exports itself if someone does import *
del _crud_exports
del dir
del globals
del callable
