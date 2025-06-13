import sqlite3
import uuid
import hashlib
from datetime import datetime
import json
import os
from config import DATABASE_PATH

# Global variable for the database name
DATABASE_NAME = os.path.basename(DATABASE_PATH)

# Constants for document context paths
APP_ROOT_DIR_CONTEXT = os.path.abspath(os.path.dirname(__file__))
LOGO_SUBDIR_CONTEXT = "company_logos"
