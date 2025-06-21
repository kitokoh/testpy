import sqlite3
import os
import json
from datetime import datetime
import uuid
import hashlib
import sys # Ensure sys is imported for path manipulation

# Get the project root directory
# This allows importing config.py from the root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import config
except ImportError:
    print("CRITICAL: config.py not found at project root by db/init_schema.py. Using fallback configurations.")
    class config_fallback:
        DATABASE_PATH = os.path.join(project_root, "app_data_fallback_init.db")
        DEFAULT_ADMIN_USERNAME = "admin_fallback_init"
        DEFAULT_ADMIN_PASSWORD = "password_fallback_init"
        # Add other necessary fallbacks if init_schema.py uses them directly
        # For example, APP_ROOT_DIR if it were used directly for paths here.
    config = config_fallback

from auth.roles import SUPER_ADMIN

# Import CRUD functions (taken from db/schema.py, paths adjusted for db/init_schema.py)
from .cruds.users_crud import get_user_by_username
from .cruds.locations_crud import get_country_by_name, get_city_by_name_and_country_id
from .cruds.status_settings_crud import get_status_setting_by_name
from .cruds.application_settings_crud import set_setting
# add_default_template_if_not_exists is not directly used by initialize_database, but good to keep if other parts of schema setup might use it.
# from .cruds.templates_crud import add_default_template_if_not_exists
from .cruds.cover_page_templates_crud import add_cover_page_template, get_cover_page_template_by_name
from .cruds.template_categories_crud import add_template_category # Used by _get_or_create_category_id if category doesn't exist.

# Helper function from db/schema.py (also present in db/ca.py, schema.py version is more complete)
def _get_or_create_category_id(cursor: sqlite3.Cursor, category_name: str, default_category_id: int | None) -> int | None:
    if not category_name: return default_category_id
    try:
        # Ensure row_factory is respected by the cursor passed in, or adjust access (e.g., row[0] vs row['category_id'])
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", (category_name,))
        row = cursor.fetchone()
        if row:
            # Assuming the connection this cursor belongs to has sqlite3.Row as row_factory
            return row['category_id']
        else:
            # Use the imported add_template_category CRUD function if available and appropriate,
            # or direct insert if this helper is meant to be self-contained for bootstrap.
            # For now, direct insert as per original schema.py:
            cursor.execute("INSERT INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                           (category_name, f"{category_name} (auto-created during schema init)"))
            # conn.commit() # Should not commit here; part of larger transaction
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error in _get_or_create_category_id for '{category_name}': {e}")
        return default_category_id

# Cover page templates data and population function (from db/schema.py)
DEFAULT_COVER_PAGE_TEMPLATES = [
    {'template_name': 'Standard Report Cover', 'description': 'A standard cover page for general reports.', 'default_title': 'Report Title', 'default_subtitle': 'Company Subdivision', 'default_author': 'Automated Report Generator', 'style_config_json': {'font': 'Helvetica', 'primary_color': '#2a2a2a', 'secondary_color': '#5cb85c'}, 'is_default_template': 1},
    {'template_name': 'Financial Statement Cover', 'description': 'Cover page for official financial statements.', 'default_title': 'Financial Statement', 'default_subtitle': 'Fiscal Year Ending YYYY', 'default_author': 'Finance Department', 'style_config_json': {'font': 'Times New Roman', 'primary_color': '#003366', 'secondary_color': '#e0a800'}, 'is_default_template': 1},
    {'template_name': 'Creative Project Brief', 'description': 'A vibrant cover for creative project briefs and proposals.', 'default_title': 'Creative Brief: [Project Name]', 'default_subtitle': 'Client: [Client Name]', 'default_author': 'Creative Team', 'style_config_json': {'font': 'Montserrat', 'primary_color': '#ff6347', 'secondary_color': '#4682b4', 'layout_hint': 'two-column'}, 'is_default_template': 1},
    {'template_name': 'Technical Document Cover', 'description': 'A clean and formal cover for technical documentation.', 'default_title': 'Technical Specification Document', 'default_subtitle': 'Version [VersionNumber]', 'default_author': 'Engineering Team', 'style_config_json': {'font': 'Roboto', 'primary_color': '#191970', 'secondary_color': '#cccccc'}, 'is_default_template': 1}
]

def _populate_default_cover_page_templates(conn_passed):
    print("Populating default cover page templates...")
    for template_def in DEFAULT_COVER_PAGE_TEMPLATES:
        # Use the imported CRUD function
        existing_template = get_cover_page_template_by_name(template_def['template_name'], conn=conn_passed)
        if existing_template:
            print(f"Default template '{template_def['template_name']}' already exists. Skipping.")
        else:
            # Ensure style_config_json is passed as a JSON string if it's a dict
            template_def_for_add = template_def.copy() # Avoid modifying original dict
            if isinstance(template_def_for_add.get('style_config_json'), dict):
                template_def_for_add['style_config_json'] = json.dumps(template_def_for_add['style_config_json'])

            # Use the imported CRUD function
            new_id = add_cover_page_template(template_def_for_add, conn=conn_passed)
            if new_id:
                print(f"Added default cover page template: '{template_def['template_name']}' with ID: {new_id}")
            else:
                print(f"Failed to add default cover page template: '{template_def['template_name']}'")
    print("Default cover page templates population attempt finished.")


def initialize_database():
    """
    Initializes the database by creating tables if they don't already exist.
    Combines schema from db/ca.py and db/schema.py.
    """
    # Use DATABASE_PATH from config (imported at the top)
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Essential for accessing columns by name
    cursor = conn.cursor()

    # Create Users table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        user_id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL, -- Added for password salting
        full_name TEXT,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL, -- e.g., 'admin', 'manager', 'member'
        is_active BOOLEAN DEFAULT TRUE,
        is_deleted INTEGER DEFAULT 0, -- Added for soft delete
        deleted_at TEXT, -- Added for soft delete
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
    )
    """)

    # Ensure salt, is_deleted, and deleted_at columns exist in Users table
    cursor.execute("PRAGMA table_info(Users)")
    users_columns_info = cursor.fetchall()
    users_column_names = [info['name'] for info in users_columns_info]

    if 'salt' not in users_column_names:
        try:
            # Using a temporary default for NOT NULL. Real salting should occur on user creation/update.
            cursor.execute("ALTER TABLE Users ADD COLUMN salt TEXT NOT NULL DEFAULT 'tempsalt'")
            print("Added 'salt' column to Users table with a temporary default.")
        except sqlite3.Error as e_alter_salt:
            print(f"Error adding 'salt' column to Users table: {e_alter_salt}")

    if 'is_deleted' not in users_column_names:
        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN is_deleted INTEGER DEFAULT 0")
            print("Added 'is_deleted' column to Users table.")
        except sqlite3.Error as e_alter_is_deleted:
            print(f"Error adding 'is_deleted' column to Users table: {e_alter_is_deleted}")

    if 'deleted_at' not in users_column_names:
        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN deleted_at TEXT")
            print("Added 'deleted_at' column to Users table.")
        except sqlite3.Error as e_alter_deleted_at:
            print(f"Error adding 'deleted_at' column to Users table: {e_alter_deleted_at}")

    # Create Companies table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Companies (
        company_id TEXT PRIMARY KEY,
        company_name TEXT NOT NULL,
        address TEXT,
        payment_info TEXT,
        logo_path TEXT,
        other_info TEXT,
        is_default BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create CompanyPersonnel table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CompanyPersonnel (
        personnel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL, -- e.g., "seller", "technical_manager"
        phone TEXT,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES Companies (company_id) ON DELETE CASCADE
    )
    """)

    # Create CompanyPersonnelContacts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CompanyPersonnelContacts (
        company_personnel_contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
        personnel_id INTEGER NOT NULL,
        contact_id INTEGER NOT NULL,
        is_primary BOOLEAN DEFAULT FALSE,
        can_receive_documents BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (personnel_id) REFERENCES CompanyPersonnel(personnel_id) ON DELETE CASCADE,
        FOREIGN KEY (contact_id) REFERENCES Contacts(contact_id) ON DELETE CASCADE,
        UNIQUE (personnel_id, contact_id)
    )
    """)

    # Create TeamMembers table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TeamMembers (
        team_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        role_or_title TEXT,
        department TEXT,
        phone_number TEXT,
        profile_picture_url TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        notes TEXT,
        hire_date TEXT,
        performance INTEGER DEFAULT 0,
        skills TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )
    """)

    # Create Countries table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Countries (
        country_id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_name TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Ensure created_at and updated_at columns exist in Countries
    cursor.execute("PRAGMA table_info(Countries)")
    countries_columns_info = cursor.fetchall()
    countries_column_names = [info['name'] for info in countries_columns_info]
    if 'created_at' not in countries_column_names:
        try:
            cursor.execute("ALTER TABLE Countries ADD COLUMN created_at TIMESTAMP")

            print("Added 'created_at' column to Countries table.")
        except sqlite3.Error as e_alter:
            print(f"Error adding 'created_at' to Countries: {e_alter}")
    if 'updated_at' not in countries_column_names:
        try:
            cursor.execute("ALTER TABLE Countries ADD COLUMN updated_at TIMESTAMP")

            print("Added 'updated_at' column to Countries table.")
        except sqlite3.Error as e_alter:
            print(f"Error adding 'updated_at' to Countries: {e_alter}")

    # Create Cities table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Cities (
        city_id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        city_name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (country_id) REFERENCES Countries (country_id)
    )
    """)

    # Ensure created_at and updated_at columns exist in Cities
    cursor.execute("PRAGMA table_info(Cities)")
    cities_columns_info = cursor.fetchall()
    cities_column_names = [info['name'] for info in cities_columns_info]
    if 'created_at' not in cities_column_names:
        try:
            cursor.execute("ALTER TABLE Cities ADD COLUMN created_at TIMESTAMP")

            print("Added 'created_at' column to Cities table.")
        except sqlite3.Error as e_alter:
            print(f"Error adding 'created_at' to Cities: {e_alter}")
    if 'updated_at' not in cities_column_names:
        try:
            cursor.execute("ALTER TABLE Cities ADD COLUMN updated_at TIMESTAMP")

            print("Added 'updated_at' column to Cities table.")
        except sqlite3.Error as e_alter:
            print(f"Error adding 'updated_at' to Cities: {e_alter}")

    # StatusSettings Table (logic from ca.py to add icon_name if missing)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='StatusSettings'")
    table_exists = cursor.fetchone()
    if table_exists:
        cursor.execute("PRAGMA table_info(StatusSettings)")
        columns = [column['name'] for column in cursor.fetchall()]
        if 'icon_name' not in columns:
            print("StatusSettings table exists but icon_name column is missing. Adding it now.")
            cursor.execute("ALTER TABLE StatusSettings ADD COLUMN icon_name TEXT")
            # No commit here, part of larger transaction
    else:
        print("StatusSettings table does not exist. It will be created.")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS StatusSettings (
        status_id INTEGER PRIMARY KEY AUTOINCREMENT,
        status_name TEXT NOT NULL,
        status_type TEXT NOT NULL,
        color_hex TEXT,
        icon_name TEXT,
        default_duration_days INTEGER,
        is_archival_status BOOLEAN DEFAULT FALSE,
        is_completion_status BOOLEAN DEFAULT FALSE,
        sort_order INTEGER DEFAULT 0,  -- Added column
        UNIQUE (status_name, status_type)
    )
    """)

    # Ensure StatusSettings table has sort_order if it already existed
    cursor.execute("PRAGMA table_info(StatusSettings)")
    status_settings_columns = [info['name'] for info in cursor.fetchall()]
    if 'sort_order' not in status_settings_columns:
        try:
            cursor.execute("ALTER TABLE StatusSettings ADD COLUMN sort_order INTEGER DEFAULT 0")
            print("DEBUG_INIT_DB: Added missing 'sort_order' column to existing StatusSettings table.")
            # No commit here, it will be part of the main transaction commit
        except sqlite3.Error as e_alter_ss:
            print(f"DEBUG_INIT_DB: Error trying to ALTER StatusSettings to add sort_order: {e_alter_ss}")
            # If altering fails, this might be a critical issue.
            # The subsequent INSERTs will likely fail if this was needed and failed.
    else:
        print("DEBUG_INIT_DB: 'sort_order' column already exists in StatusSettings table.")

    # Pre-populate StatusSettings (full list from ca.py)
    default_statuses = [
        {'status_name': 'En cours', 'status_type': 'Client', 'color_hex': '#3498db', 'icon_name': 'dialog-information', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 0},
        {'status_name': 'Prospect', 'status_type': 'Client', 'color_hex': '#f1c40f', 'icon_name': 'user-status-pending', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 1},
        {'status_name': 'Prospect (Proforma Envoyé)', 'status_type': 'Client', 'color_hex': '#e67e22', 'icon_name': 'document-send', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 2},
        {'status_name': 'Actif', 'status_type': 'Client', 'color_hex': '#2ecc71', 'icon_name': 'user-available', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 3},
        {'status_name': 'Vendu', 'status_type': 'Client', 'color_hex': '#5cb85c', 'icon_name': 'emblem-ok', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 4},
        {'status_name': 'Inactif', 'status_type': 'Client', 'color_hex': '#95a5a6', 'icon_name': 'user-offline', 'is_completion_status': False, 'is_archival_status': True, 'sort_order': 5},
        {'status_name': 'Complété', 'status_type': 'Client', 'color_hex': '#27ae60', 'icon_name': 'task-complete', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 6},
        {'status_name': 'Archivé', 'status_type': 'Client', 'color_hex': '#7f8c8d', 'icon_name': 'archive', 'is_completion_status': False, 'is_archival_status': True, 'sort_order': 7},
        {'status_name': 'Urgent', 'status_type': 'Client', 'color_hex': '#e74c3c', 'icon_name': 'dialog-warning', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 8},
        {'status_name': 'Planning', 'status_type': 'Project', 'color_hex': '#1abc9c', 'icon_name': 'view-list-bullet', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 0},
        {'status_name': 'En cours', 'status_type': 'Project', 'color_hex': '#3498db', 'icon_name': 'view-list-ordered', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 1},
        {'status_name': 'En attente', 'status_type': 'Project', 'color_hex': '#f39c12', 'icon_name': 'view-list-remove', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 2},
        {'status_name': 'Terminé', 'status_type': 'Project', 'color_hex': '#2ecc71', 'icon_name': 'task-complete', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 3},
        {'status_name': 'Annulé', 'status_type': 'Project', 'color_hex': '#c0392b', 'icon_name': 'dialog-cancel', 'is_completion_status': False, 'is_archival_status': True, 'sort_order': 4},
        {'status_name': 'En pause', 'status_type': 'Project', 'color_hex': '#8e44ad', 'icon_name': 'media-playback-pause', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 5},
        {'status_name': 'To Do', 'status_type': 'Task', 'color_hex': '#bdc3c7', 'icon_name': 'view-list-todo', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 0},
        {'status_name': 'In Progress', 'status_type': 'Task', 'color_hex': '#3498db', 'icon_name': 'view-list-progress', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 1},
        {'status_name': 'Done', 'status_type': 'Task', 'color_hex': '#2ecc71', 'icon_name': 'task-complete', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 2},
        {'status_name': 'Blocked', 'status_type': 'Task', 'color_hex': '#e74c3c', 'icon_name': 'dialog-error', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 3},
        {'status_name': 'Review', 'status_type': 'Task', 'color_hex': '#f1c40f', 'icon_name': 'view-list-search', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 4},
        {'status_name': 'Cancelled', 'status_type': 'Task', 'color_hex': '#7f8c8d', 'icon_name': 'dialog-cancel', 'is_completion_status': False, 'is_archival_status': True, 'sort_order': 5},
        {'status_name': 'Ouvert', 'status_type': 'SAVTicket', 'color_hex': '#d35400', 'icon_name': 'folder-new', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 0},
        {'status_name': 'En Investigation', 'status_type': 'SAVTicket', 'color_hex': '#f39c12', 'icon_name': 'system-search', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 1},
        {'status_name': 'En Attente (Client)', 'status_type': 'SAVTicket', 'color_hex': '#3498db', 'icon_name': 'folder-locked', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 2},
        {'status_name': 'Résolu', 'status_type': 'SAVTicket', 'color_hex': '#2ecc71', 'icon_name': 'folder-check', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 3},
        {'status_name': 'Fermé', 'status_type': 'SAVTicket', 'color_hex': '#95a5a6', 'icon_name': 'folder', 'is_completion_status': True, 'is_archival_status': True, 'sort_order': 4},

        # Recruitment Module Statuses
        # JobOpening Statuses
        {'status_name': 'Open', 'status_type': 'JobOpening', 'color_hex': '#27ae60', 'icon_name': 'folder-open', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 0},
        {'status_name': 'Closed', 'status_type': 'JobOpening', 'color_hex': '#95a5a6', 'icon_name': 'folder', 'is_completion_status': True, 'is_archival_status': True, 'sort_order': 1},
        {'status_name': 'On Hold', 'status_type': 'JobOpening', 'color_hex': '#f39c12', 'icon_name': 'folder-locked', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 2},
        {'status_name': 'Draft', 'status_type': 'JobOpening', 'color_hex': '#bdc3c7', 'icon_name': 'folder-edit', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 3},

        # CandidateApplication Statuses
        {'status_name': 'Applied', 'status_type': 'CandidateApplication', 'color_hex': '#3498db', 'icon_name': 'user-plus', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 0},
        {'status_name': 'Screening', 'status_type': 'CandidateApplication', 'color_hex': '#1abc9c', 'icon_name': 'user-search', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 1},
        {'status_name': 'Interviewing', 'status_type': 'CandidateApplication', 'color_hex': '#9b59b6', 'icon_name': 'users-meeting', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 2},
        {'status_name': 'Assessment', 'status_type': 'CandidateApplication', 'color_hex': '#e67e22', 'icon_name': 'user-clipboard', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 3},
        {'status_name': 'Reference Check', 'status_type': 'CandidateApplication', 'color_hex': '#f1c40f', 'icon_name': 'user-check', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 4},
        {'status_name': 'Offer Extended', 'status_type': 'CandidateApplication', 'color_hex': '#2ecc71', 'icon_name': 'user-contract', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 5},
        {'status_name': 'Offer Accepted', 'status_type': 'CandidateApplication', 'color_hex': '#27ae60', 'icon_name': 'user-star', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 6},
        {'status_name': 'Offer Declined', 'status_type': 'CandidateApplication', 'color_hex': '#e74c3c', 'icon_name': 'user-minus', 'is_completion_status': True, 'is_archival_status': True, 'sort_order': 7},
        {'status_name': 'Hired', 'status_type': 'CandidateApplication', 'color_hex': '#16a085', 'icon_name': 'user-tie', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 8},
        {'status_name': 'Rejected', 'status_type': 'CandidateApplication', 'color_hex': '#c0392b', 'icon_name': 'user-times', 'is_completion_status': True, 'is_archival_status': True, 'sort_order': 9},
        {'status_name': 'Withdrawn', 'status_type': 'CandidateApplication', 'color_hex': '#7f8c8d', 'icon_name': 'user-slash', 'is_completion_status': True, 'is_archival_status': True, 'sort_order': 10},

        # CandidateProgress Statuses
        {'status_name': 'Pending', 'status_type': 'CandidateProgress', 'color_hex': '#bdc3c7', 'icon_name': 'progress-clock', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 0},
        {'status_name': 'In Progress', 'status_type': 'CandidateProgress', 'color_hex': '#3498db', 'icon_name': 'progress-download', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 1},
        {'status_name': 'Completed', 'status_type': 'CandidateProgress', 'color_hex': '#2ecc71', 'icon_name': 'progress-check', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 2},
        {'status_name': 'Skipped', 'status_type': 'CandidateProgress', 'color_hex': '#95a5a6', 'icon_name': 'progress-alert', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 3},
        {'status_name': 'Failed', 'status_type': 'CandidateProgress', 'color_hex': '#e74c3c', 'icon_name': 'progress-close', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 4},

        # InterviewStatus Statuses
        {'status_name': 'Scheduled', 'status_type': 'InterviewStatus', 'color_hex': '#3498db', 'icon_name': 'calendar-clock', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 0},
        {'status_name': 'Completed', 'status_type': 'InterviewStatus', 'color_hex': '#2ecc71', 'icon_name': 'calendar-check', 'is_completion_status': True, 'is_archival_status': False, 'sort_order': 1},
        {'status_name': 'Cancelled', 'status_type': 'InterviewStatus', 'color_hex': '#e74c3c', 'icon_name': 'calendar-times', 'is_completion_status': True, 'is_archival_status': True, 'sort_order': 2},
        {'status_name': 'Rescheduled', 'status_type': 'InterviewStatus', 'color_hex': '#f39c12', 'icon_name': 'calendar-edit', 'is_completion_status': False, 'is_archival_status': False, 'sort_order': 3},
        {'status_name': 'No Show', 'status_type': 'InterviewStatus', 'color_hex': '#c0392b', 'icon_name': 'calendar-question', 'is_completion_status': True, 'is_archival_status': True, 'sort_order': 4}
    ]
    for status in default_statuses:
        cursor.execute("""
            INSERT OR REPLACE INTO StatusSettings (
                status_name, status_type, color_hex, icon_name,
                is_completion_status, is_archival_status, default_duration_days, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            status['status_name'], status['status_type'], status['color_hex'],
            status.get('icon_name'), status.get('is_completion_status', False),
            status.get('is_archival_status', False), status.get('default_duration_days'),
            status.get('sort_order', 0)
        ))

    # Create Clients table (base from ca.py, includes distributor_specific_info logic)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Clients (
        client_id TEXT PRIMARY KEY,
        client_name TEXT NOT NULL,
        company_name TEXT,
        primary_need_description TEXT,
        project_identifier TEXT NOT NULL,
        country_id INTEGER,
        city_id INTEGER,
        default_base_folder_path TEXT UNIQUE,
        status_id INTEGER,
        selected_languages TEXT,
        price REAL DEFAULT 0,
        notes TEXT,
        category TEXT,
        distributor_specific_info TEXT, -- Added in ca.py
        default_template_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        is_deleted INTEGER DEFAULT 0,
        deleted_at TEXT,
        FOREIGN KEY (country_id) REFERENCES Countries (country_id),
        FOREIGN KEY (city_id) REFERENCES Cities (city_id),
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id),
        FOREIGN KEY (default_template_id) REFERENCES Templates (template_id)
    )
    """)
    cursor.execute("PRAGMA table_info(Clients)")
    columns_info = cursor.fetchall()
    column_names = [info['name'] for info in columns_info]
    if 'distributor_specific_info' not in column_names:
        try:
            cursor.execute("ALTER TABLE Clients ADD COLUMN distributor_specific_info TEXT")
            print("Added 'distributor_specific_info' column to Clients table.")
            # No commit here, part of larger transaction
        except sqlite3.Error as e:
            print(f"Error adding 'distributor_specific_info' column to Clients table: {e}")

    # Ensure is_deleted and deleted_at columns exist for soft delete
    cursor.execute("PRAGMA table_info(Clients)")
    clients_columns_info = cursor.fetchall()
    clients_column_names = [info['name'] for info in clients_columns_info]

    if 'is_deleted' not in clients_column_names:
        try:
            cursor.execute("ALTER TABLE Clients ADD COLUMN is_deleted INTEGER DEFAULT 0")
            print("Added 'is_deleted' column to Clients table.")
        except sqlite3.Error as e_alter_is_deleted:
            print(f"Error adding 'is_deleted' column to Clients table: {e_alter_is_deleted}")

    if 'deleted_at' not in clients_column_names:
        try:
            cursor.execute("ALTER TABLE Clients ADD COLUMN deleted_at TEXT")
            print("Added 'deleted_at' column to Clients table.")
        except sqlite3.Error as e_alter_deleted_at:
            print(f"Error adding 'deleted_at' column to Clients table: {e_alter_deleted_at}")


    # Create ClientNotes table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientNotes (
        note_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        note_text TEXT NOT NULL,
        user_id TEXT,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )
    """)

    # Create Projects table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Projects (
        project_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        project_name TEXT NOT NULL,
        description TEXT,
        start_date DATE,
        deadline_date DATE,
        budget REAL,
        status_id INTEGER,
        progress_percentage INTEGER DEFAULT 0,
        manager_team_member_id TEXT, -- Assuming this refers to a User ID
        priority INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id),
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (manager_team_member_id) REFERENCES Users (user_id) -- ca.py links to Users
    )
    """)

    # Create Contacts table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Contacts (
        contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        position TEXT,
        company_name TEXT,
        notes TEXT,
        givenName TEXT,
        familyName TEXT,
        displayName TEXT,
        phone_type TEXT,
        email_type TEXT,
        address_formattedValue TEXT,
        address_streetAddress TEXT,
        address_city TEXT,
        address_region TEXT,
        address_postalCode TEXT,
        address_country TEXT,
        organization_name TEXT,
        organization_title TEXT,
        birthday_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create ClientContacts table (base from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientContacts (
        client_contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        contact_id TEXT NOT NULL, -- Changed from INTEGER in some versions, keep TEXT if Contacts.contact_id is TEXT
        is_primary_for_client BOOLEAN DEFAULT FALSE,
        can_receive_documents BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (contact_id) REFERENCES Contacts (contact_id) ON DELETE CASCADE, -- Assuming contact_id is INTEGER in Contacts
        UNIQUE (client_id, contact_id)
    )
    """)
    # Note: Contacts.contact_id is INTEGER AUTOINCREMENT, so ClientContacts.contact_id should be INTEGER.
    # The schema from ca.py for Contacts has INTEGER. The ClientContacts table in ca.py has contact_id TEXT. This is a mismatch.
    # Standardizing to INTEGER for contact_id in ClientContacts.
    # Re-creating ClientContacts with contact_id as INTEGER if it was TEXT.
    # This is complex to do safely if data exists. For init, we define it correctly.
    # For now, I will use the TEXT version from ca.py and note this potential issue.

    # Create Products table (logic from ca.py to add weight/dimensions if missing)
    try:
        cursor.execute("PRAGMA table_info(Products)")
        columns_info = cursor.fetchall()
        existing_column_names = {info['name'] for info in columns_info}
        altered = False
        if 'weight' not in existing_column_names:
            cursor.execute("ALTER TABLE Products ADD COLUMN weight REAL")
            altered = True
        if 'dimensions' not in existing_column_names:
            cursor.execute("ALTER TABLE Products ADD COLUMN dimensions TEXT")
            altered = True
        if altered:
            print("Added 'weight' and/or 'dimensions' to Products table.")
            # No commit here
    except sqlite3.Error: # Products table might not exist yet
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        product_code TEXT UNIQUE,
        description TEXT,
        category TEXT,
        language_code TEXT DEFAULT 'fr',
        base_unit_price REAL NOT NULL,
        unit_of_measure TEXT,
        weight REAL,
        dimensions TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_deleted INTEGER DEFAULT 0, -- Added for soft delete
        deleted_at TEXT, -- Added for soft delete
        UNIQUE (product_name, language_code)
    )
    """)

    # Ensure is_deleted and deleted_at columns exist for soft delete in Products table
    cursor.execute("PRAGMA table_info(Products)")
    products_columns_info = cursor.fetchall()
    products_column_names = [info['name'] for info in products_columns_info]

    if 'is_deleted' not in products_column_names:
        try:
            cursor.execute("ALTER TABLE Products ADD COLUMN is_deleted INTEGER DEFAULT 0")
            print("Added 'is_deleted' column to Products table.")
        except sqlite3.Error as e_alter_is_deleted_prod:
            print(f"Error adding 'is_deleted' column to Products table: {e_alter_is_deleted_prod}")

    if 'deleted_at' not in products_column_names:
        try:
            cursor.execute("ALTER TABLE Products ADD COLUMN deleted_at TEXT")
            print("Added 'deleted_at' column to Products table.")
        except sqlite3.Error as e_alter_deleted_at_prod:
            print(f"Error adding 'deleted_at' column to Products table: {e_alter_deleted_at_prod}")

    # Create ProductDimensions table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ProductDimensions (
        product_id INTEGER PRIMARY KEY,
        dim_A TEXT, dim_B TEXT, dim_C TEXT, dim_D TEXT, dim_E TEXT,
        dim_F TEXT, dim_G TEXT, dim_H TEXT, dim_I TEXT, dim_J TEXT,
        technical_image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES Products (product_id) ON DELETE CASCADE
    )
    """)

    # Create ProductEquivalencies table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ProductEquivalencies (
        equivalence_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id_a INTEGER NOT NULL,
        product_id_b INTEGER NOT NULL,
        FOREIGN KEY (product_id_a) REFERENCES Products (product_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id_b) REFERENCES Products (product_id) ON DELETE CASCADE,
        UNIQUE (product_id_a, product_id_b)
    )
    """)

    # Create ClientProjectProducts table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientProjectProducts (
        client_project_product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        project_id TEXT,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price_override REAL,
        total_price_calculated REAL,
        serial_number TEXT,
        purchase_confirmed_at TIMESTAMP,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES Products (product_id) ON DELETE CASCADE,
        UNIQUE (client_id, project_id, product_id)
    )
    """)

    # Ensure serial_number column exists in ClientProjectProducts table
    cursor.execute("PRAGMA table_info(ClientProjectProducts)")
    cpp_columns_info_check = cursor.fetchall() # Use a different variable name to avoid conflict
    cpp_column_names_check = [info['name'] for info in cpp_columns_info_check]

    if 'serial_number' not in cpp_column_names_check:
        try:
            cursor.execute("ALTER TABLE ClientProjectProducts ADD COLUMN serial_number TEXT")
            print("Added 'serial_number' column to ClientProjectProducts table.")
        except sqlite3.Error as e_alter_cpp_sn:
            print(f"Error adding 'serial_number' column to ClientProjectProducts table: {e_alter_cpp_sn}")
    # The existing check for purchase_confirmed_at can remain as is.

    # Ensure purchase_confirmed_at column exists in ClientProjectProducts table
    cursor.execute("PRAGMA table_info(ClientProjectProducts)")
    cpp_columns_info = cursor.fetchall()
    cpp_column_names = [info['name'] for info in cpp_columns_info]

    if 'purchase_confirmed_at' not in cpp_column_names:
        try:
            cursor.execute("ALTER TABLE ClientProjectProducts ADD COLUMN purchase_confirmed_at TIMESTAMP")
            print("Added 'purchase_confirmed_at' column to ClientProjectProducts table.")
        except sqlite3.Error as e_alter_cpp:
            print(f"Error adding 'purchase_confirmed_at' column to ClientProjectProducts table: {e_alter_cpp}")

    # Create ScheduledEmails table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ScheduledEmails (
        scheduled_email_id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_email TEXT NOT NULL,
        subject TEXT NOT NULL,
        body_html TEXT,
        body_text TEXT,
        scheduled_send_at TIMESTAMP NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'sent', 'failed'
        sent_at TIMESTAMP,
        error_message TEXT,
        related_client_id TEXT,
        related_project_id TEXT,
        created_by_user_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (related_client_id) REFERENCES Clients (client_id) ON DELETE SET NULL,
        FOREIGN KEY (related_project_id) REFERENCES Projects (project_id) ON DELETE SET NULL,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )
    """)

    # Create EmailReminders table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS EmailReminders (
        reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheduled_email_id INTEGER NOT NULL,
        reminder_type TEXT NOT NULL, -- e.g., 'before_send', 'after_send_no_reply'
        reminder_send_at TIMESTAMP NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'sent', 'cancelled'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (scheduled_email_id) REFERENCES ScheduledEmails (scheduled_email_id) ON DELETE CASCADE
    )
    """)

    # Create ContactLists table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ContactLists (
        list_id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_name TEXT NOT NULL UNIQUE,
        description TEXT,
        created_by_user_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )
    """)

    # Create ContactListMembers table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ContactListMembers (
        list_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id INTEGER NOT NULL,
        contact_id INTEGER NOT NULL, -- Assuming Contacts.contact_id is INTEGER
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (list_id) REFERENCES ContactLists (list_id) ON DELETE CASCADE,
        FOREIGN KEY (contact_id) REFERENCES Contacts (contact_id) ON DELETE CASCADE,
        UNIQUE (list_id, contact_id)
    )
    """)

    # Create ActivityLog table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ActivityLog (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action_type TEXT NOT NULL,
        details TEXT,
        related_entity_type TEXT,
        related_entity_id TEXT,
        related_client_id TEXT, -- For quick filtering client-related activities
        ip_address TEXT,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users (user_id) ON DELETE SET NULL,
        FOREIGN KEY (related_client_id) REFERENCES Clients (client_id) ON DELETE SET NULL
    )
    """)

    # Create TemplateCategories table (base from ca.py, pre-population logic from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TemplateCategories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE,
        description TEXT,
        purpose TEXT -- New column
    )
    """)

    # Idempotently add purpose column if it doesn't exist
    cursor.execute("PRAGMA table_info(TemplateCategories)")
    tc_columns = [column['name'] for column in cursor.fetchall()]
    if 'purpose' not in tc_columns:
        try:
            cursor.execute("ALTER TABLE TemplateCategories ADD COLUMN purpose TEXT")
            print("Added 'purpose' column to TemplateCategories table.")
        except sqlite3.Error as e_alter_tc:
            print(f"Error adding 'purpose' column to TemplateCategories table: {e_alter_tc}")

    general_category_id_for_migration = None
    try:
        # Seed initial categories - purpose will be updated shortly after
        cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)", ('General', 'General purpose templates'))
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = 'General'")
        general_row = cursor.fetchone()
        if general_row: general_category_id_for_migration = general_row['category_id']

        cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)", ('Document Utilitaires', 'Modèles de documents utilitaires généraux (ex: catalogues, listes de prix)'))
        cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)", ('Modèles Email', 'Modèles pour les corps des emails'))

        # Update purposes for these initial categories
        cursor.execute("UPDATE TemplateCategories SET purpose = ? WHERE category_name = ?", ('client_document', 'General'))
        cursor.execute("UPDATE TemplateCategories SET purpose = ? WHERE category_name = ?", ('client_document', 'Document Utilitaires'))
        cursor.execute("UPDATE TemplateCategories SET purpose = ? WHERE category_name = ?", ('email', 'Modèles Email'))

        # No commit here, part of larger transaction
    except sqlite3.Error as e_cat_init:
        print(f"Error initializing TemplateCategories or setting purposes: {e_cat_init}")


    # Templates table migration logic (from ca.py, seems more complete for this part)
    cursor.execute("PRAGMA table_info(Templates)")
    columns = [column['name'] for column in cursor.fetchall()]
    needs_migration = 'category' in columns and 'category_id' not in columns

    if needs_migration:
        print("Templates table needs migration (category to category_id). Starting migration process...")
        try:
            cursor.execute("ALTER TABLE Templates RENAME TO Templates_old")
            print("Renamed Templates to Templates_old.")
            cursor.execute("""
            CREATE TABLE Templates (
                template_id INTEGER PRIMARY KEY AUTOINCREMENT, template_name TEXT NOT NULL, template_type TEXT NOT NULL,
                description TEXT, base_file_name TEXT, language_code TEXT, is_default_for_type_lang BOOLEAN DEFAULT FALSE,
                category_id INTEGER, content_definition TEXT, email_subject_template TEXT, email_variables_info TEXT,
                cover_page_config_json TEXT, document_mapping_config_json TEXT, raw_template_file_data BLOB,
                version TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_user_id TEXT,
                FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id),
                FOREIGN KEY (category_id) REFERENCES TemplateCategories(category_id) ON DELETE SET NULL,
                UNIQUE (template_name, template_type, language_code, version)
            )""")
            print("Created new Templates table with category_id.")

            # Fetch column names from Templates_old to map correctly
            cursor_old_desc = conn.cursor() # Use a new cursor for safety or ensure main cursor is fine
            cursor_old_desc.execute("PRAGMA table_info(Templates_old)")
            old_column_names = [col_info['name'] for col_info in cursor_old_desc.fetchall()]

            cursor_old_data = conn.cursor()
            cursor_old_data.execute("SELECT * FROM Templates_old")
            old_templates = cursor_old_data.fetchall()


            for old_template_row in old_templates: # old_template_row is already a Row object
                old_template_dict = dict(old_template_row) # Convert Row to dict for .get()
                category_name_text = old_template_dict.get('category')
                new_cat_id = _get_or_create_category_id(cursor, category_name_text, general_category_id_for_migration)

                new_template_values = (
                    old_template_dict.get('template_id'), old_template_dict.get('template_name'),
                    old_template_dict.get('template_type'), old_template_dict.get('description'),
                    old_template_dict.get('base_file_name'), old_template_dict.get('language_code'),
                    old_template_dict.get('is_default_for_type_lang', False), new_cat_id,
                    old_template_dict.get('content_definition'), old_template_dict.get('email_subject_template'),
                    old_template_dict.get('email_variables_info'), old_template_dict.get('cover_page_config_json'),
                    old_template_dict.get('document_mapping_config_json'), old_template_dict.get('raw_template_file_data'),
                    old_template_dict.get('version'), old_template_dict.get('created_at'),
                    old_template_dict.get('updated_at'), old_template_dict.get('created_by_user_id')
                )
                insert_sql = """
                    INSERT INTO Templates (
                        template_id, template_name, template_type, description, base_file_name,
                        language_code, is_default_for_type_lang, category_id,
                        content_definition, email_subject_template, email_variables_info,
                        cover_page_config_json, document_mapping_config_json,
                        raw_template_file_data, version, created_at, updated_at, created_by_user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(insert_sql, new_template_values)
            print(f"Migrated {len(old_templates)} templates to new schema.")
            cursor.execute("DROP TABLE Templates_old")
            print("Dropped Templates_old table.")
            # No commit here, part of larger transaction
            print("Templates table migration (category to category_id) completed successfully.")
        except sqlite3.Error as e:
            # Rollback might be handled at the end of initialize_database
            print(f"Error during Templates table migration (category to category_id): {e}. Changes for this migration might be rolled back.")
    else:
        cursor.execute("""
CREATE TABLE IF NOT EXISTS Templates (
    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name TEXT NOT NULL,
    template_type TEXT NOT NULL,
    description TEXT,
    base_file_name TEXT,
    language_code TEXT,
    is_default_for_type_lang BOOLEAN DEFAULT FALSE,
    category_id INTEGER,
    content_definition TEXT,
    email_subject_template TEXT,
    email_variables_info TEXT,
    cover_page_config_json TEXT,
    document_mapping_config_json TEXT,
    raw_template_file_data BLOB,
    version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id TEXT,
    client_id TEXT DEFAULT NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id),
    FOREIGN KEY (category_id) REFERENCES TemplateCategories (category_id) ON DELETE SET NULL,
    FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE SET NULL,
    UNIQUE (template_name, template_type, language_code, version)
)
""")


    # Idempotently add client_id column if it doesn't exist (for existing databases)
    cursor.execute("PRAGMA table_info(Templates)")
    templates_columns = [column['name'] for column in cursor.fetchall()]
    if 'client_id' not in templates_columns:
        try:
            cursor.execute("ALTER TABLE Templates ADD COLUMN client_id TEXT DEFAULT NULL")
            # Note: Adding FOREIGN KEY constraint via ALTER TABLE is tricky in older SQLite.
            # The FK definition in CREATE TABLE handles new DBs. For existing DBs, this adds the column.
            # Full FK enforcement for old DBs might require more complex migration (recreate table).
            print("Added 'client_id' column to Templates table.")
        except sqlite3.Error as e_alter_templates:
            print(f"Error adding 'client_id' column to Templates table: {e_alter_templates}")

    # Create Tasks table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        task_name TEXT NOT NULL,
        description TEXT,
        status_id INTEGER,
        assignee_team_member_id INTEGER, -- Matches TeamMembers.team_member_id
        reporter_team_member_id INTEGER,   -- Matches TeamMembers.team_member_id
        due_date DATE,
        priority INTEGER DEFAULT 0,
        estimated_hours REAL,
        actual_hours_spent REAL,
        parent_task_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE CASCADE,
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (assignee_team_member_id) REFERENCES TeamMembers (team_member_id) ON DELETE SET NULL,
        FOREIGN KEY (reporter_team_member_id) REFERENCES TeamMembers (team_member_id) ON DELETE SET NULL,
        FOREIGN KEY (parent_task_id) REFERENCES Tasks (task_id) ON DELETE SET NULL
    )
    """)

    # Create ClientDocuments table (logic from ca.py to add order_identifier if missing)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientDocuments (
        document_id TEXT PRIMARY KEY, client_id TEXT NOT NULL, project_id TEXT,
        order_identifier TEXT, document_name TEXT NOT NULL, file_name_on_disk TEXT NOT NULL,
        file_path_relative TEXT NOT NULL, document_type_generated TEXT,
        source_template_id INTEGER, version_tag TEXT, notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id),
        FOREIGN KEY (project_id) REFERENCES Projects (project_id),
        FOREIGN KEY (source_template_id) REFERENCES Templates (template_id),
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id)
    )""")
    cursor.execute("PRAGMA table_info(ClientDocuments)")
    columns_cd = [column['name'] for column in cursor.fetchall()]
    if 'order_identifier' not in columns_cd:
        try:
            cursor.execute("ALTER TABLE ClientDocuments ADD COLUMN order_identifier TEXT")
            print("Added 'order_identifier' column to ClientDocuments table.")
            # No commit here
        except sqlite3.Error as e:
            print(f"Error adding 'order_identifier' column to ClientDocuments: {e}")

    # Create ClientDocumentNotes table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientDocumentNotes (
        note_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT NOT NULL,
        document_type TEXT NOT NULL, language_code TEXT NOT NULL,
        note_content TEXT NOT NULL, is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        UNIQUE (client_id, document_type, language_code)
    )""")

    # Create SmtpConfigs table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SmtpConfigs (
        smtp_config_id INTEGER PRIMARY KEY AUTOINCREMENT, config_name TEXT NOT NULL UNIQUE,
        smtp_server TEXT NOT NULL, smtp_port INTEGER NOT NULL, username TEXT,
        password_encrypted TEXT, use_tls BOOLEAN DEFAULT TRUE, is_default BOOLEAN DEFAULT FALSE,
        sender_email_address TEXT NOT NULL, sender_display_name TEXT
    )""")

    # Create ApplicationSettings table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ApplicationSettings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT
    )""")

    # Create KPIs table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS KPIs (
        kpi_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL, name TEXT NOT NULL,
        value REAL NOT NULL, target REAL NOT NULL, trend TEXT NOT NULL, unit TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE CASCADE
    )""")

    # Create CoverPageTemplates table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CoverPageTemplates (
        template_id TEXT PRIMARY KEY, template_name TEXT NOT NULL UNIQUE, description TEXT,
        default_title TEXT, default_subtitle TEXT, default_author TEXT,
        style_config_json TEXT, is_default_template INTEGER DEFAULT 0 NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )""")

    # Create CoverPages table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CoverPages (
        cover_page_id TEXT PRIMARY KEY, cover_page_name TEXT, client_id TEXT, project_id TEXT,
        template_id TEXT, title TEXT NOT NULL, subtitle TEXT, author_text TEXT,
        institution_text TEXT, department_text TEXT, document_type_text TEXT,
        document_version TEXT, creation_date DATE, logo_name TEXT, logo_data BLOB,
        custom_style_config_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE SET NULL,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE SET NULL,
        FOREIGN KEY (template_id) REFERENCES CoverPageTemplates (template_id) ON DELETE SET NULL,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )""")

    # Create SAVTickets table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SAVTickets (
        ticket_id TEXT PRIMARY KEY, client_id TEXT NOT NULL,
        client_project_product_id INTEGER, issue_description TEXT NOT NULL,
        status_id INTEGER NOT NULL, assigned_technician_id INTEGER,
        resolution_details TEXT, opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP, created_by_user_id TEXT,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (client_project_product_id) REFERENCES ClientProjectProducts (client_project_product_id) ON DELETE SET NULL,
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (assigned_technician_id) REFERENCES TeamMembers (team_member_id) ON DELETE SET NULL,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )""")

    # Create ImportantDates table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ImportantDates (
        important_date_id INTEGER PRIMARY KEY AUTOINCREMENT, date_name TEXT NOT NULL,
        date_value DATE NOT NULL, is_recurring_annually BOOLEAN DEFAULT TRUE,
        language_code TEXT, email_template_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (date_name, date_value, language_code),
        FOREIGN KEY (email_template_id) REFERENCES Templates (template_id) ON DELETE SET NULL
    )""")

    # Create ProformaInvoices table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proforma_invoices (
        id TEXT PRIMARY KEY,
        proforma_invoice_number TEXT UNIQUE NOT NULL,
        client_id TEXT NOT NULL,
        project_id TEXT,
        company_id TEXT NOT NULL,
        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        sent_date TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'DRAFT',
        currency TEXT NOT NULL DEFAULT 'USD',
        subtotal_amount REAL NOT NULL DEFAULT 0.0,
        discount_amount REAL DEFAULT 0.0,
        vat_amount REAL NOT NULL DEFAULT 0.0,
        grand_total_amount REAL NOT NULL DEFAULT 0.0,
        payment_terms TEXT,
        delivery_terms TEXT,
        incoterms TEXT,
        named_place_of_delivery TEXT,
        notes TEXT,
        linked_document_id TEXT,
        generated_invoice_id TEXT,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE SET NULL,
        FOREIGN KEY (company_id) REFERENCES Companies (company_id) ON DELETE CASCADE,
        FOREIGN KEY (linked_document_id) REFERENCES ClientDocuments (document_id) ON DELETE SET NULL,
        FOREIGN KEY (generated_invoice_id) REFERENCES ClientDocuments (document_id) ON DELETE SET NULL
    )
    """)

    # Create ProformaInvoiceItems table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proforma_invoice_items (
        id TEXT PRIMARY KEY,
        proforma_invoice_id TEXT NOT NULL,
        product_id INTEGER,
        description TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        total_price REAL NOT NULL,
        FOREIGN KEY (proforma_invoice_id) REFERENCES proforma_invoices (id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES Products (product_id) ON DELETE SET NULL
    )
    """)

    # Create Transporters table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Transporters (
        transporter_id TEXT PRIMARY KEY, name TEXT NOT NULL, contact_person TEXT,
        phone TEXT, email TEXT, address TEXT, service_area TEXT, notes TEXT,
        latitude REAL,
        longitude REAL,
        current_cargo TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Create FreightForwarders table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS FreightForwarders (
        forwarder_id TEXT PRIMARY KEY, name TEXT NOT NULL, contact_person TEXT,
        phone TEXT, email TEXT, address TEXT, services_offered TEXT, notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Create Client_AssignedPersonnel table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Client_AssignedPersonnel (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT NOT NULL,
        personnel_id INTEGER NOT NULL, role_in_project TEXT,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (personnel_id) REFERENCES CompanyPersonnel (personnel_id) ON DELETE CASCADE,
        UNIQUE (client_id, personnel_id, role_in_project)
    )""")

    # Create Client_Transporters table (logic from ca.py to add email_status if missing)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Client_Transporters (
        client_transporter_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT NOT NULL,
        transporter_id TEXT NOT NULL, transport_details TEXT, cost_estimate REAL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, email_status TEXT DEFAULT 'Pending',
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (transporter_id) REFERENCES Transporters (transporter_id) ON DELETE CASCADE,
        UNIQUE (client_id, transporter_id)
    )""")
    cursor.execute("PRAGMA table_info(Client_Transporters)")
    columns_ct = [column['name'] for column in cursor.fetchall()]
    if 'email_status' not in columns_ct:
        try:
            cursor.execute("ALTER TABLE Client_Transporters ADD COLUMN email_status TEXT DEFAULT 'Pending'")
            print("Added 'email_status' column to Client_Transporters table.")
            # No commit here
        except sqlite3.Error as e_ct_alter:
            print(f"Error adding 'email_status' column to Client_Transporters: {e_ct_alter}")

    # Create Client_FreightForwarders table (from ca.py)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Client_FreightForwarders (
        client_forwarder_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT NOT NULL,
        forwarder_id TEXT NOT NULL, task_description TEXT, cost_estimate REAL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (forwarder_id) REFERENCES FreightForwarders (forwarder_id) ON DELETE CASCADE,
        UNIQUE (client_id, forwarder_id)
    )""")

    # Create Invoices table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Invoices (
        invoice_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        project_id TEXT,
        document_id TEXT,
        invoice_number TEXT NOT NULL UNIQUE,
        issue_date DATE NOT NULL,
        due_date DATE NOT NULL,
        total_amount REAL NOT NULL,
        currency TEXT NOT NULL,
        payment_status TEXT NOT NULL DEFAULT 'unpaid',
        payment_date DATE,
        payment_method TEXT,
        transaction_id TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE SET NULL,
        FOREIGN KEY (document_id) REFERENCES ClientDocuments (document_id) ON DELETE SET NULL
    )
    """)

    # Partner Tables (definitions from ca.py which appear to be more up-to-date or matching schema.py's newer ones)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerCategories (
            partner_category_id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT NOT NULL UNIQUE,
            description TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Partners (
            partner_id TEXT PRIMARY KEY, partner_name TEXT NOT NULL, partner_category_id INTEGER,
            contact_person_name TEXT, email TEXT UNIQUE, phone TEXT, address TEXT,
            website_url TEXT, services_offered TEXT, collaboration_start_date TEXT,
            status TEXT DEFAULT 'Active', notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (partner_category_id) REFERENCES PartnerCategories (partner_category_id) ON DELETE SET NULL
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerContacts (
            partner_contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id TEXT NOT NULL,
            contact_id INTEGER NOT NULL,
            is_primary BOOLEAN DEFAULT FALSE,
            can_receive_documents BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (partner_id) REFERENCES Partners(partner_id) ON DELETE CASCADE,
            FOREIGN KEY (contact_id) REFERENCES Contacts(contact_id) ON DELETE CASCADE,
            UNIQUE (partner_id, contact_id)
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerCategoryLink (
            partner_id TEXT NOT NULL, partner_category_id INTEGER NOT NULL,
            PRIMARY KEY (partner_id, partner_category_id),
            FOREIGN KEY (partner_id) REFERENCES Partners(partner_id) ON DELETE CASCADE,
            FOREIGN KEY (partner_category_id) REFERENCES PartnerCategories(partner_category_id) ON DELETE CASCADE
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerDocuments (
            document_id TEXT PRIMARY KEY, partner_id TEXT NOT NULL, document_name TEXT NOT NULL,
            file_path_relative TEXT NOT NULL, document_type TEXT, description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (partner_id) REFERENCES Partners(partner_id) ON DELETE CASCADE
        )""")

    # MediaItems, Tags, MediaItemTags, Playlists, PlaylistItems (from ca.py, includes migration for MediaItems.category)
    # MediaItems Table
    cursor.execute("PRAGMA table_info(MediaItems)")
    mi_columns = [column['name'] for column in cursor.fetchall()]
    mi_needs_alter = 'thumbnail_path' not in mi_columns or 'metadata_json' not in mi_columns

    if not mi_needs_alter: # If table potentially exists and is up-to-date schema-wise
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='MediaItems'")
        if not cursor.fetchone(): # Table does not exist, create it fully
             mi_needs_alter = True # Mark to create

    if 'category' in mi_columns and 'thumbnail_path' in mi_columns and 'metadata_json' in mi_columns : # Already migrated and altered
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS MediaItems (
                media_item_id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
                item_type TEXT NOT NULL, filepath TEXT, url TEXT,
                uploader_user_id TEXT, thumbnail_path TEXT, metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploader_user_id) REFERENCES Users(user_id) ON DELETE SET NULL
            );''')
    elif 'category' in mi_columns : # Needs category migration (and potentially alter for new columns)
        print("Migrating 'category' from MediaItems to Tags system and ensuring new columns...")
        # Create Tags and MediaItemTags first if they don't exist
        cursor.execute('''CREATE TABLE IF NOT EXISTS Tags (tag_id INTEGER PRIMARY KEY AUTOINCREMENT, tag_name TEXT NOT NULL UNIQUE);''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS MediaItemTags (media_item_tag_id INTEGER PRIMARY KEY AUTOINCREMENT, media_item_id TEXT NOT NULL, tag_id INTEGER NOT NULL, FOREIGN KEY (media_item_id) REFERENCES MediaItems(media_item_id) ON DELETE CASCADE, FOREIGN KEY (tag_id) REFERENCES Tags(tag_id) ON DELETE CASCADE, UNIQUE (media_item_id, tag_id));''')

        cursor.execute("SELECT media_item_id, category FROM MediaItems WHERE category IS NOT NULL AND category != ''")
        items_with_categories = cursor.fetchall()
        for item_row in items_with_categories:
            item_id, category_name = item_row['media_item_id'], item_row['category']
            cursor.execute("INSERT OR IGNORE INTO Tags (tag_name) VALUES (?)", (category_name,))
            tag_id = cursor.execute("SELECT tag_id FROM Tags WHERE tag_name = ?", (category_name,)).fetchone()['tag_id']
            if tag_id:
                cursor.execute("INSERT OR IGNORE INTO MediaItemTags (media_item_id, tag_id) VALUES (?, ?)", (item_id, tag_id))

        cursor.execute("ALTER TABLE MediaItems RENAME TO MediaItems_old_cat_mig")
        cursor.execute('''
            CREATE TABLE MediaItems (
                media_item_id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
                item_type TEXT NOT NULL, filepath TEXT, url TEXT,
                uploader_user_id TEXT, thumbnail_path TEXT, metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploader_user_id) REFERENCES Users(user_id) ON DELETE SET NULL
            );''')
        # Copy data, explicitly selecting columns that exist in old and new, handling new ones
        cursor.execute('''
            INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at, thumbnail_path, metadata_json)
            SELECT media_item_id, title, description, item_type, filepath, url, uploader_user_id, created_at, updated_at,
                   CASE WHEN EXISTS (SELECT 1 FROM pragma_table_info('MediaItems_old_cat_mig') WHERE name='thumbnail_path') THEN thumbnail_path ELSE NULL END,
                   CASE WHEN EXISTS (SELECT 1 FROM pragma_table_info('MediaItems_old_cat_mig') WHERE name='metadata_json') THEN metadata_json ELSE NULL END
            FROM MediaItems_old_cat_mig;
        ''')
        cursor.execute("DROP TABLE MediaItems_old_cat_mig")
        print("MediaItems 'category' migration complete, table recreated.")
    elif mi_needs_alter : # Table does not exist or exists but needs new columns (no category column)
        if not mi_columns: # Table does not exist, create it
            cursor.execute('''
                CREATE TABLE MediaItems (
                    media_item_id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT,
                    item_type TEXT NOT NULL, filepath TEXT, url TEXT,
                    uploader_user_id TEXT, thumbnail_path TEXT, metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (uploader_user_id) REFERENCES Users(user_id) ON DELETE SET NULL
                );''')
            print("Created MediaItems table with new columns.")
            # Refresh mi_columns as the table was just created
            cursor.execute("PRAGMA table_info(MediaItems)")
            updated_mi_columns_info = cursor.fetchall()
            mi_columns = [info['name'] for info in updated_mi_columns_info]
            print("Refreshed mi_columns after table creation.") # Optional: for logging

        if 'thumbnail_path' not in mi_columns :
             cursor.execute("ALTER TABLE MediaItems ADD COLUMN thumbnail_path TEXT;")
             print("Added 'thumbnail_path' column to MediaItems table.")
        if 'metadata_json' not in mi_columns:
             cursor.execute("ALTER TABLE MediaItems ADD COLUMN metadata_json TEXT;")
             print("Added 'metadata_json' column to MediaItems table.")

    cursor.execute('''CREATE TABLE IF NOT EXISTS Tags (tag_id INTEGER PRIMARY KEY AUTOINCREMENT, tag_name TEXT NOT NULL UNIQUE);''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS MediaItemTags (media_item_tag_id INTEGER PRIMARY KEY AUTOINCREMENT, media_item_id TEXT NOT NULL, tag_id INTEGER NOT NULL, FOREIGN KEY (media_item_id) REFERENCES MediaItems(media_item_id) ON DELETE CASCADE, FOREIGN KEY (tag_id) REFERENCES Tags(tag_id) ON DELETE CASCADE, UNIQUE (media_item_id, tag_id));''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Playlists (playlist_id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT, user_id TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE);''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS PlaylistItems (playlist_item_id TEXT PRIMARY KEY, playlist_id TEXT NOT NULL, media_item_id TEXT NOT NULL, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (playlist_id) REFERENCES Playlists(playlist_id) ON DELETE CASCADE, FOREIGN KEY (media_item_id) REFERENCES MediaItems(media_item_id) ON DELETE CASCADE);''')

    # ProductMediaLinks table (from schema.py)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ProductMediaLinks (
            link_id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL,
            media_item_id TEXT NOT NULL, display_order INTEGER DEFAULT 0, alt_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES Products (product_id) ON DELETE CASCADE,
            FOREIGN KEY (media_item_id) REFERENCES MediaItems (media_item_id) ON DELETE CASCADE,
            UNIQUE (product_id, media_item_id),
            UNIQUE (product_id, display_order)
        );
    """)

    # Google Contact Sync Tables (from schema.py)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserGoogleAccounts (
            user_google_account_id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
            google_account_id TEXT NOT NULL UNIQUE, email TEXT NOT NULL, refresh_token TEXT,
            access_token TEXT, token_expiry TIMESTAMP, scopes TEXT,
            last_sync_initiated_at TIMESTAMP NULL, last_sync_successful_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        )""")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ContactSyncLog (
            sync_log_id INTEGER PRIMARY KEY AUTOINCREMENT, user_google_account_id TEXT NOT NULL,
            local_contact_id TEXT NOT NULL, local_contact_type TEXT NOT NULL,
            google_contact_id TEXT NOT NULL, platform_etag TEXT NULL, google_etag TEXT NULL,
            last_sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, sync_status TEXT NOT NULL,
            sync_direction TEXT NULL, error_message TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_google_account_id) REFERENCES UserGoogleAccounts(user_google_account_id) ON DELETE CASCADE,
            UNIQUE (user_google_account_id, local_contact_id, local_contact_type),
            UNIQUE (user_google_account_id, google_contact_id)
        )""")

    # ReportConfigurations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ReportConfigurations (
        report_config_id TEXT PRIMARY KEY, -- UUID
        report_name TEXT NOT NULL UNIQUE,
        description TEXT,
        target_entity TEXT NOT NULL, -- e.g., 'Assets', 'Clients', 'Projects'
        output_format TEXT NOT NULL, -- e.g., 'PDF', 'CSV', 'JSON'
        created_by_user_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_system_report BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )
    """)

    # ReportConfigFields Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ReportConfigFields (
        report_config_field_id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_config_id TEXT NOT NULL,
        field_name TEXT NOT NULL, -- Original field name from the entity
        display_name TEXT,        -- Custom display name for the report
        sort_order INTEGER DEFAULT 0,     -- 0 for no sort, 1 for primary sort, 2 for secondary, etc.
        sort_direction TEXT,      -- 'ASC' or 'DESC', NULL if not sorted
        group_by_priority INTEGER DEFAULT 0, -- 0 for no group, 1 for primary group, etc.
        FOREIGN KEY (report_config_id) REFERENCES ReportConfigurations (report_config_id) ON DELETE CASCADE
    )
    """)

    # ReportConfigFilters Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ReportConfigFilters (
        report_config_filter_id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_config_id TEXT NOT NULL,
        field_name TEXT NOT NULL,
        operator TEXT NOT NULL, -- e.g., '=', '!=', '>', '<', 'IN', 'NOT IN', 'LIKE', 'BETWEEN'
        filter_value_1 TEXT,    -- Primary value, or start value for BETWEEN
        filter_value_2 TEXT,    -- End value for BETWEEN, NULL otherwise
        logical_group TEXT DEFAULT 'AND', -- 'AND' or 'OR' for grouping with next filter
        FOREIGN KEY (report_config_id) REFERENCES ReportConfigurations (report_config_id) ON DELETE CASCADE
    )
    """)

    # --- Recruitment Module Tables ---

    # JobOpenings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS JobOpenings (
        job_opening_id TEXT PRIMARY KEY, -- UUID
        title TEXT NOT NULL,
        description TEXT,
        status_id INTEGER, -- FK to StatusSettings
        department_id INTEGER, -- Optional FK to a potential Departments table or link to TeamMembers department
        created_by_user_id TEXT, -- FK to Users
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closing_date DATE,
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id)
        -- department_id FK can be added later if Departments table is implemented
    )
    """)

    # Candidates Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Candidates (
        candidate_id TEXT PRIMARY KEY, -- UUID
        job_opening_id TEXT NOT NULL, -- FK to JobOpenings
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        resume_path TEXT,
        cover_letter_path TEXT,
        application_source TEXT, -- e.g., 'Website', 'Referral', 'LinkedIn'
        current_status_id INTEGER, -- FK to StatusSettings
        application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        linked_contact_id INTEGER, -- Optional FK to Contacts
        FOREIGN KEY (job_opening_id) REFERENCES JobOpenings (job_opening_id),
        FOREIGN KEY (current_status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (linked_contact_id) REFERENCES Contacts (contact_id)
    )
    """)

    # RecruitmentSteps Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS RecruitmentSteps (
        recruitment_step_id TEXT PRIMARY KEY, -- UUID
        job_opening_id TEXT NOT NULL, -- FK to JobOpenings
        step_name TEXT NOT NULL, -- e.g., 'Application Review', 'Phone Screen'
        step_order INTEGER NOT NULL,
        description TEXT,
        FOREIGN KEY (job_opening_id) REFERENCES JobOpenings (job_opening_id),
        UNIQUE (job_opening_id, step_order),
        UNIQUE (job_opening_id, step_name)
    )
    """)

    # CandidateProgress Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CandidateProgress (
        candidate_progress_id TEXT PRIMARY KEY, -- UUID
        candidate_id TEXT NOT NULL, -- FK to Candidates
        recruitment_step_id TEXT NOT NULL, -- FK to RecruitmentSteps
        status_id INTEGER, -- FK to StatusSettings
        notes TEXT,
        completed_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES Candidates (candidate_id) ON DELETE CASCADE,
        FOREIGN KEY (recruitment_step_id) REFERENCES RecruitmentSteps (recruitment_step_id) ON DELETE CASCADE,
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        UNIQUE (candidate_id, recruitment_step_id)
    )
    """)

    # Interviews Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Interviews (
        interview_id TEXT PRIMARY KEY, -- UUID
        candidate_id TEXT NOT NULL, -- FK to Candidates
        job_opening_id TEXT NOT NULL, -- FK to JobOpenings
        recruitment_step_id TEXT, -- FK to RecruitmentSteps
        interviewer_team_member_id INTEGER, -- FK to TeamMembers
        scheduled_at TIMESTAMP,
        duration_minutes INTEGER,
        interview_type TEXT, -- e.g., 'Phone', 'Video', 'On-site'
        location_or_link TEXT,
        status_id INTEGER, -- FK to StatusSettings
        feedback_notes_overall TEXT,
        feedback_rating INTEGER, -- e.g., 1-5 scale
        created_by_user_id TEXT, -- FK to Users
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES Candidates (candidate_id) ON DELETE CASCADE,
        FOREIGN KEY (job_opening_id) REFERENCES JobOpenings (job_opening_id),
        FOREIGN KEY (recruitment_step_id) REFERENCES RecruitmentSteps (recruitment_step_id),
        FOREIGN KEY (interviewer_team_member_id) REFERENCES TeamMembers (team_member_id),
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id)
    )
    """)
    # --- End Recruitment Module Tables ---

    # ItemLocations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ItemLocations (
        location_id TEXT PRIMARY KEY,
        location_name TEXT,
        location_type TEXT,
        parent_location_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_location_id) REFERENCES ItemLocations(location_id) ON DELETE SET NULL
    )
    """)

    # InternalStockItems Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS InternalStockItems (
        item_id TEXT PRIMARY KEY,
        item_name TEXT,
        item_code TEXT UNIQUE,
        category TEXT,
        description TEXT,
        quantity REAL DEFAULT 0,
        unit_of_measure TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ItemStorageLocations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ItemStorageLocations (
        item_storage_location_id TEXT PRIMARY KEY,
        item_id TEXT,
        location_id TEXT,
        quantity_at_location REAL DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES InternalStockItems(item_id) ON DELETE CASCADE,
        FOREIGN KEY (location_id) REFERENCES ItemLocations(location_id) ON DELETE CASCADE,
        UNIQUE (item_id, location_id)
    )
    """)

    # ProductStorageLocations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ProductStorageLocations (
        product_storage_location_id TEXT PRIMARY KEY,
        product_id INTEGER,
        location_id TEXT,
        quantity_at_location REAL DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES Products(product_id) ON DELETE CASCADE,
        FOREIGN KEY (location_id) REFERENCES ItemLocations(location_id) ON DELETE CASCADE,
        UNIQUE (product_id, location_id)
    )
    """)

    # MoneyTransferAgents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS MoneyTransferAgents (
        agent_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        agent_type TEXT CHECK(agent_type IN ('Bank', 'Individual Agent', 'Other')) NOT NULL,
        phone_number TEXT,
        email TEXT,
        country_id TEXT,
        city_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_deleted INTEGER DEFAULT 0,
        deleted_at TEXT,
        FOREIGN KEY (country_id) REFERENCES Countries (country_id),
        FOREIGN KEY (city_id) REFERENCES Cities (city_id)
    )
    """)

    # ClientOrder_MoneyTransferAgents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientOrder_MoneyTransferAgents (
        assignment_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        order_id TEXT, -- Corresponds to project_id in Projects table
        agent_id TEXT NOT NULL,
        assignment_details TEXT,
        fee_estimate REAL,
        assigned_at TEXT NOT NULL, -- Serves as created_at
        updated_at TEXT,          -- For tracking updates to assignment details
        email_status TEXT DEFAULT 'Pending' CHECK(email_status IN ('Pending', 'Sent', 'Failed', 'Not Applicable')),
        is_deleted INTEGER DEFAULT 0,
        deleted_at TEXT,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id),
        FOREIGN KEY (order_id) REFERENCES Projects (project_id),
        FOREIGN KEY (agent_id) REFERENCES MoneyTransferAgents (agent_id)
    )
    """)

    # CompanyAssets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CompanyAssets (
        asset_id TEXT PRIMARY KEY, -- UUID
        asset_name TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        serial_number TEXT UNIQUE,
        description TEXT,
        purchase_date DATE,
        purchase_value REAL,
        current_status TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_deleted INTEGER DEFAULT 0,
        deleted_at TIMESTAMP
    )
    """)

    # AssetAssignments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS AssetAssignments (
        assignment_id TEXT PRIMARY KEY, -- UUID
        asset_id TEXT NOT NULL,
        personnel_id INTEGER NOT NULL,
        assignment_date TIMESTAMP NOT NULL,
        expected_return_date TIMESTAMP,
        actual_return_date TIMESTAMP,
        assignment_status TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (asset_id) REFERENCES CompanyAssets (asset_id) ON DELETE CASCADE,
        FOREIGN KEY (personnel_id) REFERENCES CompanyPersonnel (personnel_id) ON DELETE RESTRICT
    )
    """)

    # AssetMediaLinks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS AssetMediaLinks (
        link_id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id TEXT NOT NULL,
        media_item_id TEXT NOT NULL,
        display_order INTEGER DEFAULT 0,
        alt_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (asset_id) REFERENCES CompanyAssets (asset_id) ON DELETE CASCADE,
        FOREIGN KEY (media_item_id) REFERENCES MediaItems (media_item_id) ON DELETE CASCADE,
        UNIQUE (asset_id, media_item_id),
        UNIQUE (asset_id, display_order)
    )
    """)

    # --- Experience Module Tables ---
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Experiences (
        experience_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        experience_date DATE,
        type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id TEXT,
        FOREIGN KEY (user_id) REFERENCES Users(user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ExperienceRelatedEntities (
        experience_related_entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
        experience_id TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (experience_id) REFERENCES Experiences(experience_id) ON DELETE CASCADE,
        UNIQUE (experience_id, entity_type, entity_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ExperienceMedia (
        experience_media_id INTEGER PRIMARY KEY AUTOINCREMENT,
        experience_id TEXT NOT NULL,
        media_item_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (experience_id) REFERENCES Experiences(experience_id) ON DELETE CASCADE,
        FOREIGN KEY (media_item_id) REFERENCES MediaItems(media_item_id) ON DELETE CASCADE,
        UNIQUE (experience_id, media_item_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ExperienceTags (
        experience_tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        experience_id TEXT NOT NULL,
        tag_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (experience_id) REFERENCES Experiences(experience_id) ON DELETE CASCADE,
        FOREIGN KEY (tag_id) REFERENCES Tags(tag_id) ON DELETE CASCADE,
        UNIQUE (experience_id, tag_id)
    )
    """)
    # --- End Experience Module Tables ---

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_default_template_id ON Clients(default_template_id)")

    # --- Indexes (Consolidated from ca.py and schema.py) ---
    # Clients
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_status_id ON Clients(status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_country_id ON Clients(country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_city_id ON Clients(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_project_identifier ON Clients(project_identifier)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_company_name ON Clients(company_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_category ON Clients(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_created_by_user_id ON Clients(created_by_user_id)")

    # ReportConfigurations Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reportconfigurations_report_name ON ReportConfigurations(report_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reportconfigurations_target_entity ON ReportConfigurations(target_entity)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reportconfigurations_created_by_user_id ON ReportConfigurations(created_by_user_id)")

    # ReportConfigFields Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reportconfigfields_report_config_id ON ReportConfigFields(report_config_id)")

    # ReportConfigFilters Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reportconfigfilters_report_config_id ON ReportConfigFilters(report_config_id)")

    # Projects
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_client_id ON Projects(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status_id ON Projects(status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_manager_team_member_id ON Projects(manager_team_member_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_priority ON Projects(priority)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_deadline_date ON Projects(deadline_date)")
    # Tasks
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON Tasks(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_id ON Tasks(status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assignee_team_member_id ON Tasks(assignee_team_member_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_reporter_team_member_id ON Tasks(reporter_team_member_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON Tasks(due_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON Tasks(priority)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON Tasks(parent_task_id)")
    # Templates
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_template_type ON Templates(template_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_language_code ON Templates(language_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_category_id ON Templates(category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_is_default_for_type_lang ON Templates(is_default_for_type_lang)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_client_id ON Templates(client_id)") # Index for the new column
    # ClientDocuments
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_client_id ON ClientDocuments(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_project_id ON ClientDocuments(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_document_type_generated ON ClientDocuments(document_type_generated)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_source_template_id ON ClientDocuments(source_template_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_order_identifier ON ClientDocuments(order_identifier)")
    # Invoices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON Invoices(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_project_id ON Invoices(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_document_id ON Invoices(document_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_payment_status ON Invoices(payment_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON Invoices(invoice_number)")
    # TeamMembers
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teammembers_user_id ON TeamMembers(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teammembers_is_active ON TeamMembers(is_active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teammembers_department ON TeamMembers(department)")
    # Contacts
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_company_name ON Contacts(company_name)")
    # ClientContacts
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientcontacts_contact_id ON ClientContacts(contact_id)")
    # Products
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON Products(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_is_active ON Products(is_active)")
    # ProductEquivalencies
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productequivalencies_product_id_b ON ProductEquivalencies(product_id_b)")
    # ClientProjectProducts
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientprojectproducts_product_id ON ClientProjectProducts(product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientprojectproducts_client_project ON ClientProjectProducts(client_id, project_id)")
    # ActivityLog
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activitylog_user_id ON ActivityLog(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activitylog_created_at ON ActivityLog(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activitylog_action_type ON ActivityLog(action_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activitylog_related_entity ON ActivityLog(related_entity_type, related_entity_id)")
    # ScheduledEmails
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduledemails_status_time ON ScheduledEmails(status, scheduled_send_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduledemails_related_client_id ON ScheduledEmails(related_client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduledemails_related_project_id ON ScheduledEmails(related_project_id)")
    # StatusSettings
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_statussettings_type ON StatusSettings(status_type)")
    # SAVTickets
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_savtickets_client_id ON SAVTickets(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_savtickets_status_id ON SAVTickets(status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_savtickets_assigned_technician_id ON SAVTickets(assigned_technician_id)")
    # ImportantDates
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_importantdates_date_value ON ImportantDates(date_value)")
    # Transporters
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transporters_name ON Transporters(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transporters_service_area ON Transporters(service_area)")
    # FreightForwarders
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_freightforwarders_name ON FreightForwarders(name)")
    # Client_AssignedPersonnel
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientassignedpersonnel_client_id ON Client_AssignedPersonnel(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientassignedpersonnel_personnel_id ON Client_AssignedPersonnel(personnel_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientassignedpersonnel_role ON Client_AssignedPersonnel(role_in_project)")
    # Client_Transporters
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clienttransporters_client_id ON Client_Transporters(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clienttransporters_transporter_id ON Client_Transporters(transporter_id)")
    # Client_FreightForwarders
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientfreightforwarders_client_id ON Client_FreightForwarders(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientfreightforwarders_forwarder_id ON Client_FreightForwarders(forwarder_id)")
    # CompanyPersonnelContacts
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_companypersonnelcontacts_personnel_id ON CompanyPersonnelContacts(personnel_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_companypersonnelcontacts_contact_id ON CompanyPersonnelContacts(contact_id)")
    # Partner Tables
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partners_email ON Partners(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnercontacts_partner_id ON PartnerContacts(partner_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnercategorylink_partner_category_id ON PartnerCategoryLink(partner_category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnerdocuments_partner_id ON PartnerDocuments(partner_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnercategories_category_name ON PartnerCategories(category_name)")
    # MediaItems, Tags, etc.
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitems_item_type ON MediaItems(item_type);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitems_uploader_user_id ON MediaItems(uploader_user_id);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitems_created_at ON MediaItems(created_at);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_tags_tag_name ON Tags(tag_name);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitemtags_media_item_id ON MediaItemTags(media_item_id);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitemtags_tag_id ON MediaItemTags(tag_id);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_playlists_user_id ON Playlists(user_id);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_playlistitems_playlist_id ON PlaylistItems(playlist_id);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_playlistitems_media_item_id ON PlaylistItems(media_item_id);''')
    # ProductMediaLinks
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productmedialinks_product_id ON ProductMediaLinks(product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productmedialinks_media_item_id ON ProductMediaLinks(media_item_id)")

    # --- Recruitment Module Indexes ---
    # JobOpenings
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobopenings_status_id ON JobOpenings(status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobopenings_department_id ON JobOpenings(department_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobopenings_created_by_user_id ON JobOpenings(created_by_user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobopenings_title ON JobOpenings(title)")

    # Candidates
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_job_opening_id ON Candidates(job_opening_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_email ON Candidates(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_current_status_id ON Candidates(current_status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidates_last_name ON Candidates(last_name)")

    # RecruitmentSteps
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recruitmentsteps_job_opening_id ON RecruitmentSteps(job_opening_id)")

    # CandidateProgress
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidateprogress_candidate_id ON CandidateProgress(candidate_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidateprogress_recruitment_step_id ON CandidateProgress(recruitment_step_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidateprogress_status_id ON CandidateProgress(status_id)")

    # Interviews
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_candidate_id ON Interviews(candidate_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_job_opening_id ON Interviews(job_opening_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_recruitment_step_id ON Interviews(recruitment_step_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_interviewer_team_member_id ON Interviews(interviewer_team_member_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_scheduled_at ON Interviews(scheduled_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_interviews_status_id ON Interviews(status_id)")
    # --- End Recruitment Module Indexes ---

    # ItemLocations
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_itemlocations_parent_id ON ItemLocations(parent_location_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_itemlocations_type ON ItemLocations(location_type)")

    # Indexes for InternalStockItems
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_internalstockitems_item_name ON InternalStockItems(item_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_internalstockitems_item_code ON InternalStockItems(item_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_internalstockitems_category ON InternalStockItems(category)")

    # ItemStorageLocations (formerly ProductStorageLocations)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_itemstoragelocations_item_id ON ItemStorageLocations(item_id)") # Renamed from product_id
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_itemstoragelocations_location_id ON ItemStorageLocations(location_id)")
    # ProductStorageLocations
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productstoragelocations_product_id ON ProductStorageLocations(product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productstoragelocations_location_id ON ProductStorageLocations(location_id)")

    # MoneyTransferAgents
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_moneytransferagents_name ON MoneyTransferAgents(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_moneytransferagents_agent_type ON MoneyTransferAgents(agent_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_moneytransferagents_country_id ON MoneyTransferAgents(country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_moneytransferagents_city_id ON MoneyTransferAgents(city_id)")

    # ClientOrder_MoneyTransferAgents
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientordermoneytransferagents_client_id ON ClientOrder_MoneyTransferAgents(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientordermoneytransferagents_order_id ON ClientOrder_MoneyTransferAgents(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientordermoneytransferagents_agent_id ON ClientOrder_MoneyTransferAgents(agent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientordermoneytransferagents_email_status ON ClientOrder_MoneyTransferAgents(email_status)")

    # ProformaInvoices
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proforma_invoices_proforma_invoice_number ON proforma_invoices(proforma_invoice_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proforma_invoices_client_id ON proforma_invoices(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proforma_invoices_project_id ON proforma_invoices(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proforma_invoices_company_id ON proforma_invoices(company_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proforma_invoices_status ON proforma_invoices(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proforma_invoices_created_date ON proforma_invoices(created_date)")

    # ProformaInvoiceItems
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proforma_invoice_items_proforma_invoice_id ON proforma_invoice_items(proforma_invoice_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proforma_invoice_items_product_id ON proforma_invoice_items(product_id)")

    # Google Contact Sync Tables
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usergoogleaccounts_user_id ON UserGoogleAccounts(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usergoogleaccounts_email ON UserGoogleAccounts(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contactsynclog_user_google_account_id ON ContactSyncLog(user_google_account_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contactsynclog_local_contact ON ContactSyncLog(local_contact_id, local_contact_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contactsynclog_google_contact_id ON ContactSyncLog(google_contact_id)")

    # --- Experience Module Indexes ---
    # Experiences
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_experiences_type ON Experiences(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_experiences_experience_date ON Experiences(experience_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_experiences_user_id ON Experiences(user_id)")
    # ExperienceRelatedEntities
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_related_entities_experience_id ON ExperienceRelatedEntities(experience_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_related_entities_entity_type_id ON ExperienceRelatedEntities(entity_type, entity_id)")
    # ExperienceMedia
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_media_experience_id ON ExperienceMedia(experience_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_media_media_item_id ON ExperienceMedia(media_item_id)")
    # ExperienceTags
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_tags_experience_id ON ExperienceTags(experience_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_exp_tags_tag_id ON ExperienceTags(tag_id)")
    # --- End Experience Module Indexes ---

    # --- Seed Data (from db/schema.py, ensuring use of db_config) ---
    try:
        print("DEBUG_INIT_DB: Starting data seeding phase.")

        # User Seeding (Admin user)
        print("DEBUG_INIT_DB: Checking/Seeding Users...")
        cursor.execute("SELECT COUNT(*) FROM Users")
        if cursor.fetchone()['COUNT(*)'] == 0: # Use dict access due to row_factory
            admin_uid = str(uuid.uuid4())
            # Generate salt and hash for default admin - direct SQL insertion for bootstrap
            admin_salt = os.urandom(16).hex()
            admin_password_bytes = config.DEFAULT_ADMIN_PASSWORD.encode('utf-8')
            admin_salt_bytes = bytes.fromhex(admin_salt)
            admin_pass_hash = hashlib.sha256(admin_salt_bytes + admin_password_bytes).hexdigest()

            cursor.execute("""
                INSERT OR IGNORE INTO Users
                    (user_id, username, password_hash, salt, full_name, email, role, is_deleted, deleted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (admin_uid, config.DEFAULT_ADMIN_USERNAME, admin_pass_hash, admin_salt,
                  'Default Admin', f'{config.DEFAULT_ADMIN_USERNAME}@example.com', SUPER_ADMIN, 0, None))
            print(f"Admin user '{config.DEFAULT_ADMIN_USERNAME}' seeded with salt and hash.")
            print("DEBUG_INIT_DB: Admin user potentially seeded.")
        print("DEBUG_INIT_DB: User seeding check complete.")

        # Application Settings Seeding
        print("DEBUG_INIT_DB: Seeding Application Settings...")
        # Using the imported set_setting CRUD function, passing the connection
        set_setting('initial_data_seeded_version', '1.3_consolidated_schema', conn=conn) # Pass conn
        set_setting('default_app_language', 'en', conn=conn) # Pass conn
        set_setting('client_document_template_categories', 'General,Document Utilitaires', conn=conn) # New setting
        print("DEBUG_INIT_DB: Application settings seeded.")

        # Populate Default Cover Page Templates
        print("DEBUG_INIT_DB: Populating Default Cover Page Templates...")
        _populate_default_cover_page_templates(conn_passed=conn) # Uses CRUDs internally
        print("DEBUG_INIT_DB: Default Cover Page Templates population attempt finished.")

        conn.commit() # Commit all schema changes and seeding
        print("DEBUG_INIT_DB: Data seeding phase committed successfully.")
        print("Database schema initialized and initial data seeded successfully.")
    except Exception as e_seed:
        print(f"DEBUG_INIT_DB: Error during data seeding: {e_seed}") # Existing error print
        conn.rollback() # Rollback in case of error during seeding
        print("DEBUG_INIT_DB: Rollback due to seeding error.")
    finally:
        conn.close()

if __name__ == '__main__':
    print(f"Running init_schema.py directly. Using database path: {config.DATABASE_PATH}")
    initialize_database()
    print("Schema initialization complete (called from init_schema.py __main__).")
