import sqlite3
import json # For style_config_json in DEFAULT_COVER_PAGE_TEMPLATES and Templates migration
from datetime import datetime # For add_cover_page_template if it were here, and initialize_database
import uuid # For add_cover_page_template if it were here

# Imports from other modules in the 'db' package (will be created later)
# For _populate_default_cover_page_templates:
# from .db_crud_users import get_user_by_username # Line using this is commented out
# from .db_crud_cover_pages import add_cover_page_template, get_cover_page_template_by_name, DEFAULT_COVER_PAGE_TEMPLATES

from .db_config import DATABASE_NAME # initialize_database uses this

# Placeholder for DEFAULT_COVER_PAGE_TEMPLATES until db_crud_cover_pages.py is created
# This is to avoid NameError if _populate_default_cover_page_templates is called,
# even though its dependencies on actual CRUD functions are still an issue.
DEFAULT_COVER_PAGE_TEMPLATES = []


def _get_or_create_category_id(cursor: sqlite3.Cursor, category_name: str, default_category_id: int | None) -> int | None:
    """
    Internal helper: Gets category_id for a name, creates if not exists.
    Uses the provided cursor and does not manage connection or transaction.
    Returns category_id or default_category_id if name is None/empty.
    """
    if not category_name:
        return default_category_id
    try:
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", (category_name,))
        row = cursor.fetchone()
        if row:
            return row['category_id']
        else:
            # Category does not exist, create it
            cursor.execute("INSERT INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                           (category_name, f"{category_name} (auto-created during migration)"))
            # No conn.commit() here as it's part of a larger transaction
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error in _get_or_create_category_id for '{category_name}': {e}")
        # Depending on how critical this is, you might want to raise the error
        # or return the default_category_id as a fallback.
        return default_category_id

def _populate_default_cover_page_templates():
    """
    Populates the CoverPageTemplates table with predefined default templates
    if they do not already exist by name.
    """
    # This function will be fully functional once db_crud_cover_pages and db_crud_users are created
    # and the imports at the top of this file are uncommented and correct.
    print("Attempting to populate default cover page templates...")

    # Temporarily define dependencies here or comment out the logic
    # For now, using the placeholder DEFAULT_COVER_PAGE_TEMPLATES
    # and commenting out calls to functions that don't exist yet.

    # from .db_crud_cover_pages import add_cover_page_template, get_cover_page_template_by_name, DEFAULT_COVER_PAGE_TEMPLATES
    # from .db_crud_users import get_user_by_username

    # system_user = get_user_by_username('system_user') # Define or fetch a system user
    # system_user_id = system_user['user_id'] if system_user else None

    # Using the placeholder:
    if not DEFAULT_COVER_PAGE_TEMPLATES:
        print("WARNING: DEFAULT_COVER_PAGE_TEMPLATES is empty. Cannot populate.")
        return

    for template_def in DEFAULT_COVER_PAGE_TEMPLATES:
        # existing_template = get_cover_page_template_by_name(template_def['template_name']) # BROKEN until db_crud_cover_pages.py
        existing_template = None # Temporary
        if existing_template:
            print(f"Default template '{template_def['template_name']}' already exists. Skipping.")
        else:
            # new_id = add_cover_page_template(template_def) # BROKEN until db_crud_cover_pages.py
            new_id = None # Temporary
            if new_id:
                print(f"Added default cover page template: '{template_def['template_name']}' with ID: {new_id}")
            else:
                # Print this way because the actual add_cover_page_template is commented out
                print(f"INFO: Would add default cover page template: '{template_def['template_name']}' (currently skipped due to refactoring stage).")
    print("Default cover page templates population attempt finished (simulated).")


def initialize_database():
    """
    Initializes the database by creating tables if they don't already exist.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        user_id TEXT PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL, -- e.g., 'admin', 'manager', 'member'
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
    )
    """)

    # Create Companies table
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

    # Create CompanyPersonnel table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CompanyPersonnel (
        personnel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL, -- e.g., "seller", "technical_manager"
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES Companies (company_id) ON DELETE CASCADE
    )
    """)

    # Create TeamMembers table (New, depends on Users)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TeamMembers (
        team_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE,      -- Link to Users table, can be NULL
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        role_or_title TEXT,       -- e.g., 'Project Manager', 'Developer', 'Designer'
        department TEXT,          -- e.g., 'Engineering', 'Design', 'Sales'
        phone_number TEXT,
        profile_picture_url TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        notes TEXT,
        hire_date TEXT,
        performance INTEGER DEFAULT 0,
        skills TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users (user_id) ON DELETE SET NULL -- If user is deleted, set user_id to NULL
    )
    """)

    # Create Countries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Countries (
        country_id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_name TEXT NOT NULL UNIQUE
    )
    """)

    # Create Cities table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Cities (
        city_id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        city_name TEXT NOT NULL,
        FOREIGN KEY (country_id) REFERENCES Countries (country_id)
    )
    """)

    # --- StatusSettings Table ---
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='StatusSettings'")
    table_exists = cursor.fetchone()

    if table_exists:
        cursor.execute("PRAGMA table_info(StatusSettings)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'icon_name' not in columns:
            print("StatusSettings table exists but icon_name column is missing. Adding it now.")
            cursor.execute("ALTER TABLE StatusSettings ADD COLUMN icon_name TEXT")
            conn.commit()
        else:
            print("StatusSettings table and icon_name column already exist.")
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
        UNIQUE (status_name, status_type)
    )
    """)

    default_statuses = [
        {'status_name': 'En cours', 'status_type': 'Client', 'color_hex': '#3498db', 'icon_name': 'dialog-information', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Prospect', 'status_type': 'Client', 'color_hex': '#f1c40f', 'icon_name': 'user-status-pending', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Actif', 'status_type': 'Client', 'color_hex': '#2ecc71', 'icon_name': 'user-available', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Inactif', 'status_type': 'Client', 'color_hex': '#95a5a6', 'icon_name': 'user-offline', 'is_completion_status': False, 'is_archival_status': True},
        {'status_name': 'Complété', 'status_type': 'Client', 'color_hex': '#27ae60', 'icon_name': 'task-complete', 'is_completion_status': True, 'is_archival_status': False},
        {'status_name': 'Archivé', 'status_type': 'Client', 'color_hex': '#7f8c8d', 'icon_name': 'archive', 'is_completion_status': False, 'is_archival_status': True},
        {'status_name': 'Urgent', 'status_type': 'Client', 'color_hex': '#e74c3c', 'icon_name': 'dialog-warning', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Planning', 'status_type': 'Project', 'color_hex': '#1abc9c', 'icon_name': 'view-list-bullet', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'En cours', 'status_type': 'Project', 'color_hex': '#3498db', 'icon_name': 'view-list-ordered', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'En attente', 'status_type': 'Project', 'color_hex': '#f39c12', 'icon_name': 'view-list-remove', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Terminé', 'status_type': 'Project', 'color_hex': '#2ecc71', 'icon_name': 'task-complete', 'is_completion_status': True, 'is_archival_status': False},
        {'status_name': 'Annulé', 'status_type': 'Project', 'color_hex': '#c0392b', 'icon_name': 'dialog-cancel', 'is_completion_status': False, 'is_archival_status': True},
        {'status_name': 'En pause', 'status_type': 'Project', 'color_hex': '#8e44ad', 'icon_name': 'media-playback-pause', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'To Do', 'status_type': 'Task', 'color_hex': '#bdc3c7', 'icon_name': 'view-list-todo', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'In Progress', 'status_type': 'Task', 'color_hex': '#3498db', 'icon_name': 'view-list-progress', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Done', 'status_type': 'Task', 'color_hex': '#2ecc71', 'icon_name': 'task-complete', 'is_completion_status': True, 'is_archival_status': False},
        {'status_name': 'Blocked', 'status_type': 'Task', 'color_hex': '#e74c3c', 'icon_name': 'dialog-error', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Review', 'status_type': 'Task', 'color_hex': '#f1c40f', 'icon_name': 'view-list-search', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Cancelled', 'status_type': 'Task', 'color_hex': '#7f8c8d', 'icon_name': 'dialog-cancel', 'is_completion_status': False, 'is_archival_status': True}
    ]

    for status in default_statuses:
        cursor.execute("""
            INSERT OR REPLACE INTO StatusSettings (
                status_name, status_type, color_hex, icon_name,
                is_completion_status, is_archival_status, default_duration_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            status['status_name'],
            status['status_type'],
            status['color_hex'],
            status.get('icon_name'),
            status.get('is_completion_status', False),
            status.get('is_archival_status', False),
            status.get('default_duration_days')
        ))

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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (country_id) REFERENCES Countries (country_id),
        FOREIGN KEY (city_id) REFERENCES Cities (city_id),
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id)
    )
    """)

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
        manager_team_member_id TEXT,
        priority INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id),
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (manager_team_member_id) REFERENCES Users (user_id)
    )
    """)

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientContacts (
        client_contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        contact_id TEXT NOT NULL,
        is_primary_for_client BOOLEAN DEFAULT FALSE,
        can_receive_documents BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (contact_id) REFERENCES Contacts (contact_id) ON DELETE CASCADE,
        UNIQUE (client_id, contact_id)
    )
    """)

    try:
        cursor.execute("PRAGMA table_info(Products)")
        columns_info = cursor.fetchall()
        existing_column_names = {info['name'] for info in columns_info}

        altered = False
        if 'weight' not in existing_column_names:
            cursor.execute("ALTER TABLE Products ADD COLUMN weight REAL")
            print("Added 'weight' column to Products table.")
            altered = True
        if 'dimensions' not in existing_column_names:
            cursor.execute("ALTER TABLE Products ADD COLUMN dimensions TEXT")
            print("Added 'dimensions' column to Products table.")
            altered = True

        if altered:
            conn.commit()
    except sqlite3.Error as e:
        print(f"Info: Checking columns for Products table, it might not exist yet or other error: {e}")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
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
        UNIQUE (product_name, language_code)
    )
    """)

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientProjectProducts (
        client_project_product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        project_id TEXT,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price_override REAL,
        total_price_calculated REAL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES Products (product_id) ON DELETE CASCADE,
        UNIQUE (client_id, project_id, product_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ScheduledEmails (
        scheduled_email_id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_email TEXT NOT NULL,
        subject TEXT NOT NULL,
        body_html TEXT,
        body_text TEXT,
        scheduled_send_at TIMESTAMP NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS EmailReminders (
        reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheduled_email_id INTEGER NOT NULL,
        reminder_type TEXT NOT NULL,
        reminder_send_at TIMESTAMP NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (scheduled_email_id) REFERENCES ScheduledEmails (scheduled_email_id) ON DELETE CASCADE
    )
    """)

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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ContactListMembers (
        list_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        list_id INTEGER NOT NULL,
        contact_id INTEGER NOT NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (list_id) REFERENCES ContactLists (list_id) ON DELETE CASCADE,
        FOREIGN KEY (contact_id) REFERENCES Contacts (contact_id) ON DELETE CASCADE,
        UNIQUE (list_id, contact_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ActivityLog (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action_type TEXT NOT NULL,
        details TEXT,
        related_entity_type TEXT,
        related_entity_id TEXT,
        related_client_id TEXT,
        ip_address TEXT,
        user_agent TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES Users (user_id) ON DELETE SET NULL,
        FOREIGN KEY (related_client_id) REFERENCES Clients (client_id) ON DELETE SET NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TemplateCategories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE,
        description TEXT
    )
    """)
    general_category_id_for_migration = None
    try:
        cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                       ('General', 'General purpose templates'))
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = 'General'")
        general_row = cursor.fetchone()
        if general_row:
            general_category_id_for_migration = general_row[0]

        try:
            cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                           ('Document Utilitaires', 'Modèles de documents utilitaires généraux (ex: catalogues, listes de prix)'))
        except sqlite3.Error as e_cat_util:
            print(f"Error initializing 'Document Utilitaires' category: {e_cat_util}")

        try:
            cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                               ('Modèles Email', 'Modèles pour les corps des emails'))
        except sqlite3.Error as e_cat_email:
            print(f"Error initializing 'Modèles Email' category: {e_cat_email}")
        conn.commit()
    except sqlite3.Error as e_cat_init:
        print(f"Error initializing General category or other categories in this block: {e_cat_init}")

    cursor.execute("PRAGMA table_info(Templates)")
    columns = [column[1] for column in cursor.fetchall()]
    needs_migration = 'category' in columns and 'category_id' not in columns

    if needs_migration:
        print("Templates table needs migration. Starting migration process...")
        try:
            cursor.execute("ALTER TABLE Templates RENAME TO Templates_old")
            print("Renamed Templates to Templates_old.")

            cursor.execute("""
            CREATE TABLE Templates (
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
                FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id),
                FOREIGN KEY (category_id) REFERENCES TemplateCategories(category_id) ON DELETE SET NULL,
                UNIQUE (template_name, template_type, language_code, version)
            )
            """)
            print("Created new Templates table with category_id.")

            cursor.execute("SELECT * FROM Templates_old")
            old_templates = cursor.fetchall()
            cursor_old_desc = conn.execute("PRAGMA table_info(Templates_old)")
            old_column_names = [col_info[1] for col_info in cursor_old_desc.fetchall()]

            for old_template_tuple in old_templates:
                old_template_dict = {name: val for name, val in zip(old_column_names, old_template_tuple)}
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
            conn.commit()
            print("Templates table migration completed successfully.")
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error during Templates table migration: {e}. Rolled back changes.")
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
            FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id),
            FOREIGN KEY (category_id) REFERENCES TemplateCategories(category_id) ON DELETE SET NULL,
            UNIQUE (template_name, template_type, language_code, version)
        )
        """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        task_name TEXT NOT NULL,
        description TEXT,
        status_id INTEGER,
        assignee_team_member_id INTEGER,
        reporter_team_member_id INTEGER,
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientDocuments (
        document_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        project_id TEXT,
        document_name TEXT NOT NULL,
        file_name_on_disk TEXT NOT NULL,
        file_path_relative TEXT NOT NULL,
        document_type_generated TEXT,
        source_template_id INTEGER,
        version_tag TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id),
        FOREIGN KEY (project_id) REFERENCES Projects (project_id),
        FOREIGN KEY (source_template_id) REFERENCES Templates (template_id),
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SmtpConfigs (
        smtp_config_id INTEGER PRIMARY KEY AUTOINCREMENT,
        config_name TEXT NOT NULL UNIQUE,
        smtp_server TEXT NOT NULL,
        smtp_port INTEGER NOT NULL,
        username TEXT,
        password_encrypted TEXT,
        use_tls BOOLEAN DEFAULT TRUE,
        is_default BOOLEAN DEFAULT FALSE,
        sender_email_address TEXT NOT NULL,
        sender_display_name TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ApplicationSettings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS KPIs (
        kpi_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        name TEXT NOT NULL,
        value REAL NOT NULL,
        target REAL NOT NULL,
        trend TEXT NOT NULL,
        unit TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CoverPageTemplates (
        template_id TEXT PRIMARY KEY,
        template_name TEXT NOT NULL UNIQUE,
        description TEXT,
        default_title TEXT,
        default_subtitle TEXT,
        default_author TEXT,
        style_config_json TEXT,
        is_default_template INTEGER DEFAULT 0 NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CoverPages (
        cover_page_id TEXT PRIMARY KEY,
        cover_page_name TEXT,
        client_id TEXT,
        project_id TEXT,
        template_id TEXT,
        title TEXT NOT NULL,
        subtitle TEXT,
        author_text TEXT,
        institution_text TEXT,
        department_text TEXT,
        document_type_text TEXT,
        document_version TEXT,
        creation_date DATE,
        logo_name TEXT,
        logo_data BLOB,
        custom_style_config_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE SET NULL,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE SET NULL,
        FOREIGN KEY (template_id) REFERENCES CoverPageTemplates (template_id) ON DELETE SET NULL,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )
    """)

    # Call to populate default cover page templates
    _populate_default_cover_page_templates()


    conn.commit()
    conn.close()
