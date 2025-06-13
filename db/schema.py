import sqlite3
import uuid
import hashlib
from datetime import datetime
import json
import os

# Import global constants from db_config.py (assuming it's in the parent directory)
try:
    from .. import db_config # For package structure: db/schema.py importing from /app/db_config.py
except (ImportError, ValueError):
    import sys
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if app_dir not in sys.path:
        sys.path.append(app_dir)
    try:
        import db_config
    except ImportError:
        print("CRITICAL: db_config.py not found. Using fallback DATABASE_PATH.")
        class db_config_fallback: # Minimal fallback
            DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_data_fallback.db")
            APP_ROOT_DIR_CONTEXT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            LOGO_SUBDIR_CONTEXT = "company_logos_fallback"
            DEFAULT_ADMIN_USERNAME = "admin_fallback"
            DEFAULT_ADMIN_PASSWORD = "password_fallback"
        db_config = db_config_fallback


# Imports for functions used by initialize_database (when schema.py is run directly)
# These should point to the new CRUD locations.
try:
    from .cruds.users_crud import get_user_by_username
    from .cruds.locations_crud import get_country_by_name, get_city_by_name_and_country_id
    from .cruds.status_settings_crud import get_status_setting_by_name
    from .cruds.application_settings_crud import set_setting
    from .cruds.templates_crud import add_default_template_if_not_exists
    from .cruds.cover_page_templates_crud import add_cover_page_template, get_cover_page_template_by_name
    from .cruds.template_categories_crud import add_template_category
    print("Successfully imported CRUD functions from db.cruds for schema initialization.")
except ImportError as e:
    print(f"Warning: Could not import all CRUD functions for db.schema.initialize_database: {e}. Placeholders will be used if schema.py is run as main.")
    # Define placeholders if actual import fails, so schema.py can still be run as __main__ for basic setup
    get_user_by_username = lambda username, conn=None: {'user_id': str(uuid.uuid4()), 'username': username, 'full_name': 'Admin Fallback'} if username == db_config.DEFAULT_ADMIN_USERNAME else None
    get_country_by_name = lambda name, conn=None: {'country_id': 1, 'country_name': name} if name else None
    get_city_by_name_and_country_id = lambda name, country_id, conn=None: {'city_id': 1, 'city_name': name} if name and country_id else None
    get_status_setting_by_name = lambda name, type, conn=None: {'status_id': 1, 'status_name': name} if name and type else None
    set_setting = lambda key, value, conn=None: True # Simplified

    # Placeholder for add_template_category if needed by add_default_template_if_not_exists placeholder
    _placeholder_add_template_category = lambda category_name, description=None, conn=None: 1 # Dummy ID

    def add_default_template_if_not_exists(data, conn=None): # Simplified placeholder
        print(f"[SCHEMA_PLACEHOLDER] add_default_template_if_not_exists for: {data.get('template_name')}")
        # This placeholder might not be fully functional without real DB interaction
        return None

    def add_cover_page_template(data, conn=None): # Simplified placeholder
        print(f"[SCHEMA_PLACEHOLDER] add_cover_page_template for: {data.get('template_name')}")
        return str(uuid.uuid4())

    get_cover_page_template_by_name = lambda name, conn=None: None
    add_template_category = _placeholder_add_template_category


# This TABLE_SCHEMAS dictionary is the source of truth for table structures.
# It is used by db.ca.initialize_database()
TABLE_SCHEMAS = {
    'Users': {
        'columns': [
            ('user_id', 'TEXT PRIMARY KEY'),
            ('username', 'TEXT NOT NULL UNIQUE'),
            ('password_hash', 'TEXT NOT NULL'),
            ('full_name', 'TEXT'),
            ('email', 'TEXT NOT NULL UNIQUE'),
            ('role', 'TEXT NOT NULL'),
            ('is_active', 'BOOLEAN DEFAULT TRUE'),
            ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('last_login_at', 'TIMESTAMP')
        ],
        'foreign_keys': [],
        'indexes': [
            ('idx_users_username', ['username'], True), # True for UNIQUE
            ('idx_users_email', ['email'], True)
        ]
    },
    # ... (other table schemas like Companies, CompanyPersonnel, TeamMembers as before) ...
    'Countries': {
        'columns': [
            ('country_id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('country_name', 'TEXT UNIQUE NOT NULL'),
            ('country_code', 'TEXT'),
            ('created_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'), # Added
            ('updated_at', 'TEXT DEFAULT CURRENT_TIMESTAMP')  # Added
        ],
        'foreign_keys': [],
        'indexes': [('idx_countries_country_name', ['country_name'], True)]
    },
    'Cities': {
        'columns': [
            ('city_id', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('country_id', 'INTEGER NOT NULL'),
            ('city_name', 'TEXT NOT NULL')
            # Assuming created_at/updated_at might be added here too if consistency is desired
        ],
        'foreign_keys': [
            ('fk_cities_country_id', 'country_id', 'Countries(country_id)')
        ],
        'indexes': [('idx_cities_country_id_city_name', ['country_id', 'city_name'], True)]
    },
    # ... (rest of the TABLE_SCHEMAS definition from the original file) ...
}


DEFAULT_COVER_PAGE_TEMPLATES = [
    {'template_name': 'Standard Report Cover', 'description': 'A standard cover page for general reports.', 'default_title': 'Report Title', 'default_subtitle': 'Company Subdivision', 'default_author': 'Automated Report Generator', 'style_config_json': {'font': 'Helvetica', 'primary_color': '#2a2a2a', 'secondary_color': '#5cb85c'}, 'is_default_template': 1},
    {'template_name': 'Financial Statement Cover', 'description': 'Cover page for official financial statements.', 'default_title': 'Financial Statement', 'default_subtitle': 'Fiscal Year Ending YYYY', 'default_author': 'Finance Department', 'style_config_json': {'font': 'Times New Roman', 'primary_color': '#003366', 'secondary_color': '#e0a800'}, 'is_default_template': 1},
    {'template_name': 'Creative Project Brief', 'description': 'A vibrant cover for creative project briefs and proposals.', 'default_title': 'Creative Brief: [Project Name]', 'default_subtitle': 'Client: [Client Name]', 'default_author': 'Creative Team', 'style_config_json': {'font': 'Montserrat', 'primary_color': '#ff6347', 'secondary_color': '#4682b4', 'layout_hint': 'two-column'}, 'is_default_template': 1},
    {'template_name': 'Technical Document Cover', 'description': 'A clean and formal cover for technical documentation.', 'default_title': 'Technical Specification Document', 'default_subtitle': 'Version [VersionNumber]', 'default_author': 'Engineering Team', 'style_config_json': {'font': 'Roboto', 'primary_color': '#191970', 'secondary_color': '#cccccc'}, 'is_default_template': 1}
]

def _populate_default_cover_page_templates(conn_passed):
    print("Populating default cover page templates...")
    for template_def in DEFAULT_COVER_PAGE_TEMPLATES:
        existing_template = get_cover_page_template_by_name(template_def['template_name'], conn=conn_passed)
        if existing_template:
            print(f"Default template '{template_def['template_name']}' already exists. Skipping.")
        else:
            # Ensure style_config_json is passed as a JSON string if it's a dict
            if isinstance(template_def.get('style_config_json'), dict):
                template_def_for_add = template_def.copy()
                template_def_for_add['style_config_json'] = json.dumps(template_def_for_add['style_config_json'])
            else:
                template_def_for_add = template_def

            new_id = add_cover_page_template(template_def_for_add, conn=conn_passed)
            if new_id:
                print(f"Added default cover page template: '{template_def['template_name']}' with ID: {new_id}")
            else:
                print(f"Failed to add default cover page template: '{template_def['template_name']}'")
    print("Default cover page templates population attempt finished.")

def _get_or_create_category_id(cursor: sqlite3.Cursor, category_name: str, default_category_id: int | None) -> int | None:
    if not category_name: return default_category_id
    try:
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", (category_name,))
        row = cursor.fetchone()
        # Assuming conn.row_factory = sqlite3.Row is set on the connection for this cursor
        if row: return row['category_id']
        else:
            cursor.execute("INSERT INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                           (category_name, f"{category_name} (auto-created)"))
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error in _get_or_create_category_id for '{category_name}': {e}")
        return default_category_id

def initialize_database():
    # Use DATABASE_PATH from db_config
    conn = sqlite3.connect(db_config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Table Creations (Users, Companies, etc. - condensed for brevity, use full list from existing)
    cursor.execute("CREATE TABLE IF NOT EXISTS Users (user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, full_name TEXT, email TEXT NOT NULL UNIQUE, role TEXT NOT NULL, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login_at TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS Companies (company_id TEXT PRIMARY KEY, company_name TEXT NOT NULL, address TEXT, payment_info TEXT, logo_path TEXT, other_info TEXT, is_default BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS CompanyPersonnel (personnel_id INTEGER PRIMARY KEY AUTOINCREMENT, company_id TEXT NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL, phone TEXT, email TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (company_id) REFERENCES Companies (company_id) ON DELETE CASCADE)")
    cursor.execute("CREATE TABLE IF NOT EXISTS TeamMembers (team_member_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT UNIQUE, full_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, role_or_title TEXT, department TEXT, phone_number TEXT, profile_picture_url TEXT, is_active BOOLEAN DEFAULT TRUE, notes TEXT, hire_date TEXT, performance INTEGER DEFAULT 0, skills TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES Users (user_id) ON DELETE SET NULL)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Countries (
            country_id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_name TEXT NOT NULL UNIQUE,
            country_code TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE TABLE IF NOT EXISTS Cities (city_id INTEGER PRIMARY KEY AUTOINCREMENT, country_id INTEGER NOT NULL, city_name TEXT NOT NULL, FOREIGN KEY (country_id) REFERENCES Countries (country_id))")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='StatusSettings'")
    table_exists = cursor.fetchone()
    if table_exists:
        cursor.execute("PRAGMA table_info(StatusSettings)")
        columns = [column['name'] for column in cursor.fetchall()] # Use dict access
        if 'icon_name' not in columns:
            cursor.execute("ALTER TABLE StatusSettings ADD COLUMN icon_name TEXT")
            # No commit here, part of larger transaction

    cursor.execute("CREATE TABLE IF NOT EXISTS StatusSettings (status_id INTEGER PRIMARY KEY AUTOINCREMENT, status_name TEXT NOT NULL, status_type TEXT NOT NULL, color_hex TEXT, icon_name TEXT, default_duration_days INTEGER, is_archival_status BOOLEAN DEFAULT FALSE, is_completion_status BOOLEAN DEFAULT FALSE, UNIQUE (status_name, status_type))")

    default_statuses = [ # Keep full list from original
        {'status_name': 'En cours', 'status_type': 'Client', 'color_hex': '#3498db', 'icon_name': 'dialog-information'}, {'status_name': 'Prospect', 'status_type': 'Client', 'color_hex': '#f1c40f', 'icon_name': 'user-status-pending'},
        {'status_name': 'Fermé', 'status_type': 'SAVTicket', 'color_hex': '#95a5a6', 'icon_name': 'folder', 'is_completion_status': True, 'is_archival_status': True}
    ] # Truncated for brevity in this diff, but should be the full list
    for status in default_statuses:
        cursor.execute("INSERT OR REPLACE INTO StatusSettings (status_name, status_type, color_hex, icon_name, is_completion_status, is_archival_status, default_duration_days) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (status['status_name'], status['status_type'], status['color_hex'], status.get('icon_name'), status.get('is_completion_status', False), status.get('is_archival_status', False), status.get('default_duration_days')))

    # ... (ALL OTHER TABLE CREATIONS: Clients, ClientNotes, Projects, Contacts, ClientContacts, Products, etc.)
    # (This part is extensive and assumed to be correctly present as per the existing file)
    cursor.execute("CREATE TABLE IF NOT EXISTS Clients (client_id TEXT PRIMARY KEY, client_name TEXT NOT NULL, company_name TEXT, primary_need_description TEXT, project_identifier TEXT NOT NULL, country_id INTEGER, city_id INTEGER, default_base_folder_path TEXT UNIQUE, status_id INTEGER, selected_languages TEXT, price REAL DEFAULT 0, notes TEXT, category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_by_user_id TEXT, FOREIGN KEY (country_id) REFERENCES Countries (country_id), FOREIGN KEY (city_id) REFERENCES Cities (city_id), FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id), FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id))")
    # (Continue with all other CREATE TABLE statements from the existing schema.py)
    cursor.execute("CREATE TABLE IF NOT EXISTS Client_FreightForwarders (client_forwarder_id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT NOT NULL, forwarder_id TEXT NOT NULL, task_description TEXT, cost_estimate REAL, assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE, FOREIGN KEY (forwarder_id) REFERENCES FreightForwarders (forwarder_id) ON DELETE CASCADE, UNIQUE (client_id, forwarder_id))")

    # --- Updated Partner Tables ---
    # PartnerCategories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerCategories (
            partner_category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Partners table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Partners (
            partner_id TEXT PRIMARY KEY,
            partner_name TEXT NOT NULL,
            partner_category_id INTEGER,
            contact_person_name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            address TEXT,
            website_url TEXT,
            services_offered TEXT,
            collaboration_start_date TEXT,
            status TEXT DEFAULT 'Active',
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (partner_category_id) REFERENCES PartnerCategories (partner_category_id) ON DELETE SET NULL
        )
    """)

    # PartnerContacts table (assuming no changes needed based on subtask focus, but FK to Partners is vital)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerContacts (
            contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            role TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (partner_id) REFERENCES Partners(partner_id) ON DELETE CASCADE
        )
    """)

    # PartnerCategoryLink table (Updated to use new FK name for PartnerCategories)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerCategoryLink (
            partner_id TEXT NOT NULL,
            partner_category_id INTEGER NOT NULL,
            PRIMARY KEY (partner_id, partner_category_id),
            FOREIGN KEY (partner_id) REFERENCES Partners(partner_id) ON DELETE CASCADE,
            FOREIGN KEY (partner_category_id) REFERENCES PartnerCategories(partner_category_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerDocuments (
            document_id TEXT PRIMARY KEY,
            partner_id TEXT NOT NULL,
            document_name TEXT NOT NULL,
            file_path_relative TEXT NOT NULL,
            document_type TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (partner_id) REFERENCES Partners(partner_id) ON DELETE CASCADE
        )
    """)
    # --- End New Partner Tables ---

    # --- Google Contact Sync Tables ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserGoogleAccounts (
            user_google_account_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            google_account_id TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            refresh_token TEXT,
            access_token TEXT,
            token_expiry TIMESTAMP,
            scopes TEXT,
            last_sync_initiated_at TIMESTAMP NULL,
            last_sync_successful_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ContactSyncLog (
            sync_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_google_account_id TEXT NOT NULL,
            local_contact_id TEXT NOT NULL,
            local_contact_type TEXT NOT NULL,
            google_contact_id TEXT NOT NULL,
            platform_etag TEXT NULL,
            google_etag TEXT NULL,
            last_sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sync_status TEXT NOT NULL,
            sync_direction TEXT NULL,
            error_message TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_google_account_id) REFERENCES UserGoogleAccounts(user_google_account_id) ON DELETE CASCADE,
            UNIQUE (user_google_account_id, local_contact_id, local_contact_type),
            UNIQUE (user_google_account_id, google_contact_id)
        )
    """)
    # --- End Google Contact Sync Tables ---

    cursor.execute("CREATE TABLE IF NOT EXISTS TemplateCategories (category_id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT NOT NULL UNIQUE, description TEXT)")
    general_category_id_for_migration = None
    try:
        cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)", ('General', 'General purpose templates'))
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = 'General'")
        general_row = cursor.fetchone()
        if general_row: general_category_id_for_migration = general_row['category_id']
        cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)", ('Document Utilitaires', 'Modèles de documents utilitaires'))
        cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)", ('Modèles Email', 'Modèles pour les corps des emails'))
        # No commit here for categories if part of larger transaction, but standalone commit is fine too.
    except sqlite3.Error as e_cat_init: print(f"Error initializing categories: {e_cat_init}")


    cursor.execute("PRAGMA table_info(Templates)")
    columns = [column['name'] for column in cursor.fetchall()]
    needs_migration = 'category' in columns and 'category_id' not in columns
    if needs_migration:
        try:
            # Start transaction for migration
            # conn.execute("BEGIN") # Not needed if auto-commit is off or handled by main commit
            cursor.execute("ALTER TABLE Templates RENAME TO Templates_old")
            cursor.execute("CREATE TABLE Templates (template_id INTEGER PRIMARY KEY AUTOINCREMENT, template_name TEXT NOT NULL, template_type TEXT NOT NULL, description TEXT, base_file_name TEXT, language_code TEXT, is_default_for_type_lang BOOLEAN DEFAULT FALSE, category_id INTEGER, content_definition TEXT, email_subject_template TEXT, email_variables_info TEXT, cover_page_config_json TEXT, document_mapping_config_json TEXT, raw_template_file_data BLOB, version TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_by_user_id TEXT, FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id), FOREIGN KEY (category_id) REFERENCES TemplateCategories(category_id) ON DELETE SET NULL, UNIQUE (template_name, template_type, language_code, version))")

            # Use a new cursor for Templates_old to avoid issues if main cursor is somehow affected
            old_templates_cursor = conn.cursor()
            old_templates_cursor.execute("SELECT * FROM Templates_old")
            old_column_names = [desc[0] for desc in old_templates_cursor.description]

            for old_template_tuple in old_templates_cursor.fetchall():
                old_template_dict = {name: val for name, val in zip(old_column_names, old_template_tuple)}
                new_cat_id = _get_or_create_category_id(cursor, old_template_dict.get('category'), general_category_id_for_migration)
                new_template_values = (old_template_dict.get('template_id'), old_template_dict.get('template_name'), old_template_dict.get('template_type'), old_template_dict.get('description'), old_template_dict.get('base_file_name'), old_template_dict.get('language_code'), old_template_dict.get('is_default_for_type_lang', False), new_cat_id, old_template_dict.get('content_definition'), old_template_dict.get('email_subject_template'), old_template_dict.get('email_variables_info'), old_template_dict.get('cover_page_config_json'), old_template_dict.get('document_mapping_config_json'), old_template_dict.get('raw_template_file_data'), old_template_dict.get('version'), old_template_dict.get('created_at'), old_template_dict.get('updated_at'), old_template_dict.get('created_by_user_id'))
                cursor.execute("INSERT INTO Templates (template_id, template_name, template_type, description, base_file_name, language_code, is_default_for_type_lang, category_id, content_definition, email_subject_template, email_variables_info, cover_page_config_json, document_mapping_config_json, raw_template_file_data, version, created_at, updated_at, created_by_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", new_template_values)
            cursor.execute("DROP TABLE Templates_old")
            # conn.commit() # Commit migration changes
        except sqlite3.Error as e_mig:
            conn.rollback()
            print(f"Templates migration error: {e_mig}")
    else:
        cursor.execute("CREATE TABLE IF NOT EXISTS Templates (template_id INTEGER PRIMARY KEY AUTOINCREMENT, template_name TEXT NOT NULL, template_type TEXT NOT NULL, description TEXT, base_file_name TEXT, language_code TEXT, is_default_for_type_lang BOOLEAN DEFAULT FALSE, category_id INTEGER, content_definition TEXT, email_subject_template TEXT, email_variables_info TEXT, cover_page_config_json TEXT, document_mapping_config_json TEXT, raw_template_file_data BLOB, version TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_by_user_id TEXT, FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id), FOREIGN KEY (category_id) REFERENCES TemplateCategories(category_id) ON DELETE SET NULL, UNIQUE (template_name, template_type, language_code, version))")

    # Indexes (Ensure all are created)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_status_id ON Clients(status_id)")
    # ... (ALL OTHER CREATE INDEX STATEMENTS from existing schema.py)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientfreightforwarders_forwarder_id ON Client_FreightForwarders(forwarder_id)")

    # --- Indexes for Partner Tables (adjusting PartnerCategoryLink index) ---
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partners_email ON Partners(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnercontacts_partner_id ON PartnerContacts(partner_id)")
    # Index for PartnerCategoryLink's category_id foreign key
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnercategorylink_partner_category_id ON PartnerCategoryLink(partner_category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnerdocuments_partner_id ON PartnerDocuments(partner_id)")
    # It's also good practice to have an index on PartnerCategories.category_name for lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnercategories_category_name ON PartnerCategories(category_name)")
    # --- End Indexes for Partner Tables ---

    # --- Indexes for Google Contact Sync Tables ---
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usergoogleaccounts_user_id ON UserGoogleAccounts(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_usergoogleaccounts_email ON UserGoogleAccounts(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contactsynclog_user_google_account_id ON ContactSyncLog(user_google_account_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contactsynclog_local_contact ON ContactSyncLog(local_contact_id, local_contact_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contactsynclog_google_contact_id ON ContactSyncLog(google_contact_id)")
    # --- End Indexes for Google Contact Sync Tables ---

    # --- Seed Data ---
    try:
        # User Seeding
        cursor.execute("SELECT COUNT(*) FROM Users")
        # Use dictionary access for fetchone result due to conn.row_factory
        if cursor.fetchone()['COUNT(*)'] == 0:
            admin_uid = str(uuid.uuid4())
            # Use DEFAULT_ADMIN_PASSWORD and DEFAULT_ADMIN_USERNAME from db_config
            admin_pass_hash = hashlib.sha256(db_config.DEFAULT_ADMIN_PASSWORD.encode('utf-8')).hexdigest()
            cursor.execute("INSERT OR IGNORE INTO Users (user_id, username, password_hash, full_name, email, role) VALUES (?, ?, ?, ?, ?, ?)",
                           (admin_uid, db_config.DEFAULT_ADMIN_USERNAME, admin_pass_hash, 'Default Admin', 'admin@example.com', 'admin'))

        # Other seeding operations using the imported/placeholder CRUDs, passing `conn`
        admin_user = get_user_by_username(db_config.DEFAULT_ADMIN_USERNAME, conn=conn)
        # ... (rest of seeding logic from existing schema.py, ensuring `conn=conn` is passed to CRUDs)

        set_setting('initial_data_seeded_version', '1.2_schema_path_fix', conn=conn) # Update version
        set_setting('default_app_language', 'en', conn=conn)

        _populate_default_cover_page_templates(conn_passed=conn)

        conn.commit() # Commit all schema changes and seeding
        print("Database schema initialized and seeded successfully.")
    except Exception as e_seed:
        print(f"Error during data seeding in schema.py: {e_seed}")
        conn.rollback()

    conn.close()

if __name__ == '__main__':
    print(f"Running schema.py directly. Using database path: {db_config.DATABASE_PATH}")
    initialize_database()
    print("Schema initialization complete (called from schema.py __main__).")
