import sqlite3
import uuid
import hashlib
from datetime import datetime
import json
import os
import shutil # For file operations if needed
import docx # For reading .docx files
from app_config import CONFIG # For accessing templates_dir

# Global variable for the database name
DATABASE_NAME = "app_data.db"

# Constants for document context paths
# Assuming db.py is in a subdirectory of the app root (e.g., /app/core/db.py or /app/db.py)
# If db.py is directly in /app, then os.path.dirname(__file__) is /app
# If db.py is in /app/core, then os.path.dirname(__file__) is /app/core, so "../" goes to /app
APP_ROOT_DIR_CONTEXT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOGO_SUBDIR_CONTEXT = "company_logos" # Example, adjust if actual path is different, e.g., "static/logos" or "data/logos"


def initialize_database():
    """
    Initializes the database by creating tables if they don't already exist.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # <-- ADD THIS LINE
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
    # Check if StatusSettings table exists and if icon_name column is present
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='StatusSettings'")
    table_exists = cursor.fetchone()

    if table_exists:
        cursor.execute("PRAGMA table_info(StatusSettings)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'icon_name' not in columns:
            print("StatusSettings table exists but icon_name column is missing. Adding it now.")
            cursor.execute("ALTER TABLE StatusSettings ADD COLUMN icon_name TEXT")
            conn.commit() # Commit the schema change immediately
        else:
            print("StatusSettings table and icon_name column already exist.")
    else:
        print("StatusSettings table does not exist. It will be created.")

    # Create StatusSettings table (IF NOT EXISTS handles the case where it was just created or existed)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS StatusSettings (
        status_id INTEGER PRIMARY KEY AUTOINCREMENT,
        status_name TEXT NOT NULL,
        status_type TEXT NOT NULL, -- e.g., 'Client', 'Project', 'Task'
        color_hex TEXT,
        icon_name TEXT, -- Ensured by above logic or created here
        default_duration_days INTEGER,
        is_archival_status BOOLEAN DEFAULT FALSE,
        is_completion_status BOOLEAN DEFAULT FALSE,
        UNIQUE (status_name, status_type)
    )
    """)

    # --- Pre-populate StatusSettings ---
    # Values include icon_name, ensuring it's populated.
    default_statuses = [
        # Client Statuses
        {'status_name': 'En cours', 'status_type': 'Client', 'color_hex': '#3498db', 'icon_name': 'dialog-information', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Prospect', 'status_type': 'Client', 'color_hex': '#f1c40f', 'icon_name': 'user-status-pending', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Actif', 'status_type': 'Client', 'color_hex': '#2ecc71', 'icon_name': 'user-available', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Inactif', 'status_type': 'Client', 'color_hex': '#95a5a6', 'icon_name': 'user-offline', 'is_completion_status': False, 'is_archival_status': True},
        {'status_name': 'Complété', 'status_type': 'Client', 'color_hex': '#27ae60', 'icon_name': 'task-complete', 'is_completion_status': True, 'is_archival_status': False},
        {'status_name': 'Archivé', 'status_type': 'Client', 'color_hex': '#7f8c8d', 'icon_name': 'archive', 'is_completion_status': False, 'is_archival_status': True},
        {'status_name': 'Urgent', 'status_type': 'Client', 'color_hex': '#e74c3c', 'icon_name': 'dialog-warning', 'is_completion_status': False, 'is_archival_status': False},

        # Project Statuses
        {'status_name': 'Planning', 'status_type': 'Project', 'color_hex': '#1abc9c', 'icon_name': 'view-list-bullet', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'En cours', 'status_type': 'Project', 'color_hex': '#3498db', 'icon_name': 'view-list-ordered', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'En attente', 'status_type': 'Project', 'color_hex': '#f39c12', 'icon_name': 'view-list-remove', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Terminé', 'status_type': 'Project', 'color_hex': '#2ecc71', 'icon_name': 'task-complete', 'is_completion_status': True, 'is_archival_status': False},
        {'status_name': 'Annulé', 'status_type': 'Project', 'color_hex': '#c0392b', 'icon_name': 'dialog-cancel', 'is_completion_status': False, 'is_archival_status': True},
        {'status_name': 'En pause', 'status_type': 'Project', 'color_hex': '#8e44ad', 'icon_name': 'media-playback-pause', 'is_completion_status': False, 'is_archival_status': False},

        # Task Statuses
        {'status_name': 'To Do', 'status_type': 'Task', 'color_hex': '#bdc3c7', 'icon_name': 'view-list-todo', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'In Progress', 'status_type': 'Task', 'color_hex': '#3498db', 'icon_name': 'view-list-progress', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Done', 'status_type': 'Task', 'color_hex': '#2ecc71', 'icon_name': 'task-complete', 'is_completion_status': True, 'is_archival_status': False},
        {'status_name': 'Blocked', 'status_type': 'Task', 'color_hex': '#e74c3c', 'icon_name': 'dialog-error', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Review', 'status_type': 'Task', 'color_hex': '#f1c40f', 'icon_name': 'view-list-search', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Cancelled', 'status_type': 'Task', 'color_hex': '#7f8c8d', 'icon_name': 'dialog-cancel', 'is_completion_status': False, 'is_archival_status': True}
    ]

    for status in default_statuses:
        # Using INSERT OR REPLACE to ensure existing statuses are updated with latest values (e.g., icon_name, color_hex)
        # The UNIQUE constraint (status_name, status_type) is used by REPLACE.
        cursor.execute("""
            INSERT OR REPLACE INTO StatusSettings (
                status_name, status_type, color_hex, icon_name,
                is_completion_status, is_archival_status, default_duration_days -- Added default_duration_days if applicable
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            status['status_name'],
            status['status_type'],
            status['color_hex'],
            status.get('icon_name'),
            status.get('is_completion_status', False),
            status.get('is_archival_status', False),
            status.get('default_duration_days') # Ensure this key exists in your default_statuses or handle if missing
        ))
    # Note: If default_duration_days is not always present in default_statuses,
    # you might need to adjust the INSERT OR REPLACE or ensure the data structure is consistent.
    # For now, assuming it might be there or defaults to NULL if not provided and column allows NULL.

    # Create Clients tabhhhle
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Clients (
        client_id TEXT PRIMARY KEY,
        client_name TEXT NOT NULL,
        company_name TEXT,
        primary_need_description TEXT, -- Maps to 'need' from main.py
        project_identifier TEXT NOT NULL, -- Added from main.py
        country_id INTEGER,
        city_id INTEGER,
        default_base_folder_path TEXT UNIQUE, -- Added UNIQUE from main.py's base_folder_path
        status_id INTEGER,
        selected_languages TEXT, -- Comma-separated list of language codes
        price REAL DEFAULT 0, -- Added from main.py
        notes TEXT,
        category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Maps to creation_date from main.py
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Maps to last_modified from main.py
        created_by_user_id TEXT,
        FOREIGN KEY (country_id) REFERENCES Countries (country_id),
        FOREIGN KEY (city_id) REFERENCES Cities (city_id),
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id)
    )
    """)

    # Create ClientNotes table
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

    # Create Projects table
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
        FOREIGN KEY (manager_team_member_id) REFERENCES Users (user_id)
    )
    """)

    # Create Contacts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Contacts (
        contact_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Changed to INTEGER for AUTOINCREMENT
        name TEXT NOT NULL, -- This will be used as a fallback if displayName is not available
        email TEXT UNIQUE,
        phone TEXT, -- This will be the primary phone, specific type in phone_type
        position TEXT, -- Kept for general position, specific title in organization_title
        company_name TEXT, -- Kept for general company name, specific in organization_name
        notes TEXT, -- Used for notes_text
        givenName TEXT,
        familyName TEXT,
        displayName TEXT,
        phone_type TEXT, -- e.g., 'work', 'mobile', 'home'
        email_type TEXT, -- e.g., 'work', 'personal'
        address_formattedValue TEXT,
        address_streetAddress TEXT,
        address_city TEXT,
        address_region TEXT,
        address_postalCode TEXT,
        address_country TEXT,
        organization_name TEXT,
        organization_title TEXT,
        birthday_date TEXT, -- Store as TEXT in ISO format e.g., YYYY-MM-DD or MM-DD
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create ClientContacts table (associative table)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientContacts (
        client_contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        contact_id TEXT NOT NULL,
        is_primary_for_client BOOLEAN DEFAULT FALSE,
        can_receive_documents BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE, -- Added ON DELETE CASCADE
        FOREIGN KEY (contact_id) REFERENCES Contacts (contact_id) ON DELETE CASCADE, -- Added ON DELETE CASCADE
        UNIQUE (client_id, contact_id)
    )
    """)

    # Create Products table (New)
    # Idempotent ALTER TABLE for existing Products table
    try:
        cursor.execute("PRAGMA table_info(Products)")
        columns_info = cursor.fetchall()
        existing_column_names = {info['name'] for info in columns_info} # Assuming conn.row_factory = sqlite3.Row

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
            conn.commit() # Commit ALTER TABLE statements immediately

    except sqlite3.Error as e:
        # This might happen if Products table doesn't exist yet, which is fine.
        # The CREATE TABLE IF NOT EXISTS below will handle it.
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
        weight REAL, -- New column
        dimensions TEXT, -- New column (e.g., "LxWxH cm")
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (product_name, language_code)
    )
    """)

    # Create ProductEquivalencies table (New)
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

    # Create ClientProjectProducts table (New - Association)
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

    # Create ScheduledEmails table
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

    # Create EmailReminders table
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

    # Create ContactLists table
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

    # Create ContactListMembers table
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
    
    # Create ActivityLog table
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

    # Create TemplateCategories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TemplateCategories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT NOT NULL UNIQUE,
        description TEXT
    )
    """)
    # Pre-populate a "General" category
    general_category_id_for_migration = None
    try:
        cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                       ('General', 'General purpose templates'))
        # Fetch its ID for fallback during migration
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = 'General'")
        general_row = cursor.fetchone()
        if general_row:
            general_category_id_for_migration = general_row[0]

        # Pre-populate "Document Utilitaires" category
        try:
            cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                           ('Document Utilitaires', 'Modèles de documents utilitaires généraux (ex: catalogues, listes de prix)'))
        except sqlite3.Error as e_cat_util:
            print(f"Error initializing 'Document Utilitaires' category: {e_cat_util}")

            # Add "Modèles Email" category
            try:
                cursor.execute("INSERT OR IGNORE INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                               ('Modèles Email', 'Modèles pour les corps des emails'))
            except sqlite3.Error as e_cat_email:
                print(f"Error initializing 'Modèles Email' category: {e_cat_email}")

        conn.commit() # Commit category creation before potential DDL changes for Templates
    except sqlite3.Error as e_cat_init: # This specifically catches errors from the 'General' category block
        print(f"Error initializing General category or other categories in this block: {e_cat_init}")

        # Decide if this is fatal or if migration can proceed without a fallback ID
        # For now, migration will use None if this fails, which _get_or_create_category_id handles.

    # Ensure "Modèles Email" category exists
    try:
        email_category_name = "Modèles Email"
        email_category_description = "Modèles pour les corps des emails et sujets."
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", (email_category_name,))
        email_cat_row = cursor.fetchone()
        if not email_cat_row:
            cursor.execute("INSERT INTO TemplateCategories (category_name, description) VALUES (?, ?)",
                           (email_category_name, email_category_description))
            conn.commit() # Commit this change immediately
            print(f"Created '{email_category_name}' category.")
        else:
            print(f"'{email_category_name}' category already exists.")
    except sqlite3.Error as e_cat_email_init:
        print(f"Error ensuring '{email_category_name}' category: {e_cat_email_init}")


    # Check if Templates table needs migration
    cursor.execute("PRAGMA table_info(Templates)")
    columns = [column[1] for column in cursor.fetchall()]
    needs_migration = 'category' in columns and 'category_id' not in columns

    if needs_migration:
        print("Templates table needs migration. Starting migration process...")
        try:
            # 1. Rename Templates to Templates_old
            cursor.execute("ALTER TABLE Templates RENAME TO Templates_old")
            print("Renamed Templates to Templates_old.")

            # 2. Create the new Templates table with category_id FOREIGN KEY
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

            # 3. Iterate through Templates_old and insert into new Templates
            cursor.execute("SELECT * FROM Templates_old")
            old_templates = cursor.fetchall()

            # Make sure connection's row_factory is set to sqlite3.Row for dict-like access
            # This is usually set in get_db_connection, but ensure it's active for this part.
            # If cursor.fetchall() returns tuples, access by index. If dicts, by key.
            # Assuming get_db_connection sets row_factory, so fetchall() gives list of Row objects.

            # Need to get the column names from Templates_old to safely map
            cursor_old_desc = conn.execute("PRAGMA table_info(Templates_old)")
            old_column_names = [col_info[1] for col_info in cursor_old_desc.fetchall()]

            for old_template_tuple in old_templates:
                old_template_dict = {name: val for name, val in zip(old_column_names, old_template_tuple)}

                category_name_text = old_template_dict.get('category')
                # Use the internal helper _get_or_create_category_id
                # Pass the main cursor, not creating a new one for this helper
                new_cat_id = _get_or_create_category_id(cursor, category_name_text, general_category_id_for_migration)

                # Prepare values for insert, ensuring order and handling missing keys
                new_template_values = (
                    old_template_dict.get('template_id'),
                    old_template_dict.get('template_name'),
                    old_template_dict.get('template_type'),
                    old_template_dict.get('description'),
                    old_template_dict.get('base_file_name'),
                    old_template_dict.get('language_code'),
                    old_template_dict.get('is_default_for_type_lang', False), # Default if missing
                    new_cat_id, # New category_id
                    old_template_dict.get('content_definition'),
                    old_template_dict.get('email_subject_template'),
                    old_template_dict.get('email_variables_info'),
                    old_template_dict.get('cover_page_config_json'),
                    old_template_dict.get('document_mapping_config_json'),
                    old_template_dict.get('raw_template_file_data'),
                    old_template_dict.get('version'),
                    old_template_dict.get('created_at'),
                    old_template_dict.get('updated_at'),
                    old_template_dict.get('created_by_user_id')
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

            # 4. Drop Templates_old
            cursor.execute("DROP TABLE Templates_old")
            print("Dropped Templates_old table.")
            conn.commit()
            print("Templates table migration completed successfully.")
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error during Templates table migration: {e}. Rolled back changes.")
            # Consider re-creating the original Templates table if migration fails critically
            # Or, if the new Templates table was created, drop it to allow retry.
            # For now, just rollback and log. The DB might be in an inconsistent state (e.g. Templates_old exists).
    else:
        # Create Templates table if it doesn't exist (fresh setup or already migrated)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Templates (
            template_id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT NOT NULL,
            template_type TEXT NOT NULL,
            description TEXT,
            base_file_name TEXT,
            language_code TEXT,
            is_default_for_type_lang BOOLEAN DEFAULT FALSE,
            category_id INTEGER, -- New field
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
            FOREIGN KEY (category_id) REFERENCES TemplateCategories(category_id) ON DELETE SET NULL, -- Added FK
            UNIQUE (template_name, template_type, language_code, version)
        )
        """)
        # No conn.commit() here, let it be part of the larger transaction at the end of initialize_database

    # Create Tasks table (New)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        task_name TEXT NOT NULL,
        description TEXT,
        status_id INTEGER,
        assignee_team_member_id INTEGER, -- Changed to INTEGER to match TeamMembers.team_member_id
        reporter_team_member_id INTEGER,   -- Changed to INTEGER to match TeamMembers.team_member_id
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

    # Create ClientDocuments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientDocuments (
        document_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        project_id TEXT,
        document_name TEXT NOT NULL,
        file_name_on_disk TEXT NOT NULL, -- Actual name on the file system
        file_path_relative TEXT NOT NULL, -- Relative to a base documents folder
        document_type_generated TEXT, -- e.g., 'Proposal', 'Contract', 'Invoice'
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

    # Create SmtpConfigs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SmtpConfigs (
        smtp_config_id INTEGER PRIMARY KEY AUTOINCREMENT,
        config_name TEXT NOT NULL UNIQUE,
        smtp_server TEXT NOT NULL,
        smtp_port INTEGER NOT NULL,
        username TEXT,
        password_encrypted TEXT, -- Store encrypted password
        use_tls BOOLEAN DEFAULT TRUE,
        is_default BOOLEAN DEFAULT FALSE,
        sender_email_address TEXT NOT NULL,
        sender_display_name TEXT
    )
    """)

    # Create ApplicationSettings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ApplicationSettings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT
    )
    """)

    # Create KPIs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS KPIs (
        kpi_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL,
        name TEXT NOT NULL,
        value REAL NOT NULL,
        target REAL NOT NULL,
        trend TEXT NOT NULL, -- 'up', 'down', 'stable'
        unit TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES Projects (project_id) ON DELETE CASCADE
    )
    """)

    # Create CoverPageTemplates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CoverPageTemplates (
        template_id TEXT PRIMARY KEY,
        template_name TEXT NOT NULL UNIQUE,
        description TEXT,
        default_title TEXT,
        default_subtitle TEXT,
        default_author TEXT,
        style_config_json TEXT, -- JSON string for detailed styling (fonts, colors, layout hints)
        is_default_template INTEGER DEFAULT 0 NOT NULL, -- Added new flag
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )
    """)

    # Create CoverPages table (linking to Clients/Projects and Templates)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS CoverPages (
        cover_page_id TEXT PRIMARY KEY,
        cover_page_name TEXT, -- User-defined name for this instance
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
        creation_date DATE, -- Renamed from document_date for consistency with table
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

    conn.commit()
    conn.close()

def get_db_connection():
    """
    Returns a new database connection object.
    The connection is configured to return rows as dictionary-like objects.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# CRUD functions for Clients
def add_client(client_data: dict) -> str | None:
    """
    Adds a new client to the database.
    Returns the new client_id if successful, otherwise None.
    Ensures created_at and updated_at are set.
    Expects 'category_id' instead of 'category' text.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        new_client_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"

        # Ensure all required fields are present, or provide defaults
        sql = """
            INSERT INTO Clients (
                client_id, client_name, company_name, primary_need_description, project_identifier,
                country_id, city_id, default_base_folder_path, status_id,
                selected_languages, notes, category, created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_client_id,
            client_data.get('client_name'),
            client_data.get('company_name'),
            client_data.get('primary_need_description'),
            client_data.get('project_identifier'), # Added
            client_data.get('country_id'),
            client_data.get('city_id'),
            client_data.get('default_base_folder_path'),
            client_data.get('status_id'),
            client_data.get('selected_languages'),
            client_data.get('notes'),
            client_data.get('category'),
            now,  # created_at
            now,  # updated_at
            client_data.get('created_by_user_id')
        )
        
        cursor.execute(sql, params)
        conn.commit()
        return new_client_id
    except sqlite3.Error as e:
        print(f"Database error in add_client: {e}")
        # Consider raising a custom exception or logging more formally
        return None
    finally:
        if conn:
            conn.close()

def get_client_by_id(client_id: str) -> dict | None:
    """Retrieves a client by their ID. Returns a dict or None if not found."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Clients WHERE client_id = ?", (client_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_client_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_clients(filters: dict = None) -> list[dict]:
    """
    Retrieves all clients, optionally applying filters.
    Filters can be e.g. {'status_id': 1, 'category': 'VIP'}.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM Clients"
        params = []
        
        if filters:
            where_clauses = []
            for key, value in filters.items():
                # Basic protection against non-column names; ideally, validate keys against known columns
                if key in ['client_name', 'company_name', 'country_id', 'city_id', 'status_id', 'category', 'created_by_user_id']: # Add other filterable columns
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
                
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_clients: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_client(client_id: str, client_data: dict) -> bool:
    """
    Updates an existing client's information.
    Ensures updated_at is set to the current timestamp.
    Returns True if update was successful, False otherwise.
    """
    conn = None
    if not client_data:
        return False # Nothing to update

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat() + "Z"
        client_data['updated_at'] = now
        
        set_clauses = []
        params = []
        
        for key, value in client_data.items():
            # Validate keys against actual column names to prevent SQL injection if keys are from unsafe source
            # For now, assuming keys are controlled or map to valid columns
            if key != 'client_id': # client_id should not be updated here
                 set_clauses.append(f"{key} = ?")
                 params.append(value)
        
        if not set_clauses:
            return False # No valid fields to update
            
        sql = f"UPDATE Clients SET {', '.join(set_clauses)} WHERE client_id = ?"
        params.append(client_id)
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_client: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_client(client_id: str) -> bool:
    """
    Deletes a client from the database.
    Returns True if deletion was successful, False otherwise.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Clients WHERE client_id = ?", (client_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_client: {e}")
        return False
    finally:
        if conn:
            conn.close()

def add_client_note(client_id: str, note_text: str, user_id: str = None) -> int | None:
    """
    Adds a new note for a client.
    Returns the note_id if successful, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO ClientNotes (client_id, note_text, user_id)
            VALUES (?, ?, ?)
        """
        # timestamp is handled by DEFAULT CURRENT_TIMESTAMP
        params = (client_id, note_text, user_id)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid  # Returns the note_id of the inserted row
    except sqlite3.Error as e:
        print(f"Database error in add_client_note: {e}")
        if conn:
            conn.rollback() # Rollback any changes if an error occurred
        return None
    finally:
        if conn:
            conn.close()

def get_client_notes(client_id: str) -> list[dict]:
    """
    Retrieves all notes for a given client_id, ordered by timestamp (oldest first).
    Returns a list of dictionaries, where each dictionary represents a note.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT note_id, client_id, timestamp, note_text, user_id
            FROM ClientNotes
            WHERE client_id = ?
            ORDER BY timestamp ASC
        """
        cursor.execute(sql, (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_client_notes: {e}")
        return [] # Return an empty list in case of error
    finally:
        if conn:
            conn.close()

# CRUD functions for Companies
def add_company(company_data: dict) -> str | None:
    """Adds a new company. Generates UUID for company_id. Handles created_at, updated_at."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        new_company_id = str(uuid.uuid4())

        sql = """
            INSERT INTO Companies (
                company_id, company_name, address, payment_info, logo_path,
                other_info, is_default, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_company_id,
            company_data.get('company_name'),
            company_data.get('address'),
            company_data.get('payment_info'),
            company_data.get('logo_path'),
            company_data.get('other_info'),
            company_data.get('is_default', False),
            now,  # created_at
            now   # updated_at
        )
        cursor.execute(sql, params)
        conn.commit()
        return new_company_id
    except sqlite3.Error as e:
        print(f"Database error in add_company: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_company_by_id(company_id: str) -> dict | None:
    """Fetches a company by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Companies WHERE company_id = ?", (company_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_company_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_companies() -> list[dict]:
    """Fetches all companies."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Companies ORDER BY company_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_companies: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_company(company_id: str, company_data: dict) -> bool:
    """Updates company details. Manages updated_at."""
    conn = None
    if not company_data:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        company_data['updated_at'] = now

        set_clauses = [f"{key} = ?" for key in company_data.keys() if key != 'company_id']
        params = [value for key, value in company_data.items() if key != 'company_id']

        if not set_clauses:
            return False # No valid fields to update

        params.append(company_id)
        sql = f"UPDATE Companies SET {', '.join(set_clauses)} WHERE company_id = ?"

        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_company: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_company(company_id: str) -> bool:
    """Deletes a company."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # ON DELETE CASCADE will handle CompanyPersonnel
        cursor.execute("DELETE FROM Companies WHERE company_id = ?", (company_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_company: {e}")
        return False
    finally:
        if conn:
            conn.close()

def set_default_company(company_id: str) -> bool:
    """Sets a company as default, ensuring only one company can be default."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        conn.isolation_level = None # Start transaction
        cursor.execute("BEGIN")
        # Unset other defaults
        cursor.execute("UPDATE Companies SET is_default = FALSE WHERE is_default = TRUE AND company_id != ?", (company_id,))
        # Set the new default
        cursor.execute("UPDATE Companies SET is_default = TRUE WHERE company_id = ?", (company_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error in set_default_company: {e}")
        return False
    finally:
        if conn:
            conn.isolation_level = '' # Reset isolation level
            conn.close()

def get_default_company() -> dict | None:
    """
    Retrieves the company marked as default.
    Returns company data as a dictionary if found, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Companies WHERE is_default = TRUE")
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_default_company: {e}")
        return None
    finally:
        if conn:
            conn.close()

# CRUD functions for CompanyPersonnel
def add_company_personnel(personnel_data: dict) -> int | None:
    """Inserts new personnel linked to a company. Returns personnel_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO CompanyPersonnel (company_id, name, role, created_at)
            VALUES (?, ?, ?, ?)
        """
        params = (
            personnel_data.get('company_id'),
            personnel_data.get('name'),
            personnel_data.get('role'),
            now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_company_personnel: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_personnel_for_company(company_id: str, role: str = None) -> list[dict]:
    """Fetches personnel for a company, optionally filtering by role."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM CompanyPersonnel WHERE company_id = ?"
        params = [company_id]
        if role:
            sql += " AND role = ?"
            params.append(role)
        sql += " ORDER BY name"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_personnel_for_company: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_company_personnel(personnel_id: int, personnel_data: dict) -> bool:
    """Updates personnel details."""
    conn = None
    if not personnel_data:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # We don't update created_at, but if there was an updated_at for this table:
        # personnel_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

        set_clauses = [f"{key} = ?" for key in personnel_data.keys() if key != 'personnel_id']
        params = [value for key, value in personnel_data.items() if key != 'personnel_id']

        if not set_clauses:
            return False

        params.append(personnel_id)
        sql = f"UPDATE CompanyPersonnel SET {', '.join(set_clauses)} WHERE personnel_id = ?"

        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_company_personnel: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_company_personnel(personnel_id: int) -> bool:
    """Deletes a personnel entry."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM CompanyPersonnel WHERE personnel_id = ?", (personnel_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_company_personnel: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for TemplateCategories
def add_template_category(category_name: str, description: str = None) -> int | None:
    """
    Adds a new template category if it doesn't exist by name.
    Returns the category_id of the new or existing category, or None on error.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if category already exists
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", (category_name,))
        row = cursor.fetchone()
        if row:
            return row['category_id']

        # If not, insert new category
        sql = "INSERT INTO TemplateCategories (category_name, description) VALUES (?, ?)"
        cursor.execute(sql, (category_name, description))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_template_category: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

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


def get_template_category_by_id(category_id: int) -> dict | None:
    """Retrieves a template category by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TemplateCategories WHERE category_id = ?", (category_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_template_category_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_template_category_by_name(category_name: str) -> dict | None:
    """Retrieves a template category by its name."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TemplateCategories WHERE category_name = ?", (category_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_template_category_by_name: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_template_categories() -> list[dict]:
    """Retrieves all template categories."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TemplateCategories ORDER BY category_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_template_categories: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_template_category(category_id: int, new_name: str = None, new_description: str = None) -> bool:
    """
    Updates a template category's name and/or description.
    Returns True on success, False otherwise.
    """
    conn = None
    if not new_name and not new_description:
        return False # Nothing to update

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        set_clauses = []
        params = []
        if new_name:
            set_clauses.append("category_name = ?")
            params.append(new_name)
        if new_description is not None: # Allow setting description to empty string
            set_clauses.append("description = ?")
            params.append(new_description)

        if not set_clauses:
            return False

        sql = f"UPDATE TemplateCategories SET {', '.join(set_clauses)} WHERE category_id = ?"
        params.append(category_id)

        cursor.execute(sql, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_template_category: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def delete_template_category(category_id: int) -> bool:
    """
    Deletes a template category.
    Templates using this category will have their category_id set to NULL
    due to ON DELETE SET NULL foreign key constraint.
    Returns True on success, False otherwise.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Before deleting, one might want to check if it's a protected category like "General"
        # For now, allowing deletion of any category.
        cursor.execute("DELETE FROM TemplateCategories WHERE category_id = ?", (category_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_template_category: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for Templates
def add_template(template_data: dict) -> int | None:
    """
    Adds a new template to the database. Returns the template_id if successful.
    Ensures created_at and updated_at are set.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"

        sql = """
            INSERT INTO Templates (
                template_name, template_type, description, base_file_name, language_code,
                is_default_for_type_lang, category_id, content_definition, email_subject_template,
                email_variables_info, cover_page_config_json, document_mapping_config_json,
                raw_template_file_data, version, created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            template_data.get('template_name'),
            template_data.get('template_type'),
            template_data.get('description'),
            template_data.get('base_file_name'),
            template_data.get('language_code'),
            template_data.get('is_default_for_type_lang', False),
            template_data.get('category_id'), # Changed from 'category' to 'category_id'
            template_data.get('content_definition'),
            template_data.get('email_subject_template'),
            template_data.get('email_variables_info'),
            template_data.get('cover_page_config_json'),
            template_data.get('document_mapping_config_json'),
            template_data.get('raw_template_file_data'),
            template_data.get('version'),
            now,  # created_at
            now,  # updated_at
            template_data.get('created_by_user_id')
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid # For AUTOINCREMENT PK
    except sqlite3.Error as e:
        print(f"Database error in add_template: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_template_by_id(template_id: int) -> dict | None:
    """Retrieves a template by its ID. Returns a dict or None if not found."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Templates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_template_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_templates_by_type(template_type: str, language_code: str = None) -> list[dict]:
    """
    Retrieves templates filtered by template_type.
    If language_code is provided, also filters by language_code.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM Templates WHERE template_type = ?"
        params = [template_type]
        
        if language_code:
            sql += " AND language_code = ?"
            params.append(language_code)
            
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_templates_by_type: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_template(template_id: int, template_data: dict) -> bool:
    """
    Updates an existing template.
    Ensures updated_at is set.
    Returns True on success.
    """
    conn = None
    if not template_data:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        template_data['updated_at'] = now
        
        set_clauses = []
        params = []
        
        for key, value in template_data.items():
            if key != 'template_id': # template_id should not be updated
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
            
        sql = f"UPDATE Templates SET {', '.join(set_clauses)} WHERE template_id = ?"
        params.append(template_id)
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_template: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_template(template_id: int) -> bool:
    """Deletes a template from the database. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_template: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_template_details_for_preview(template_id: int) -> dict | None:
    """
    Fetches base_file_name and language_code for a given template_id for preview purposes.
    Returns a dictionary like {'base_file_name': 'name.xlsx', 'language_code': 'fr'} or None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT base_file_name, language_code FROM Templates WHERE template_id = ?",
            (template_id,)
        )
        row = cursor.fetchone()
        if row:
            return {'base_file_name': row['base_file_name'], 'language_code': row['language_code']}
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_template_details_for_preview: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_template_path_info(template_id: int) -> dict | None:
    """
    Fetches base_file_name (as file_name) and language_code (as language) for a given template_id.
    Returns {'file_name': 'name.xlsx', 'language': 'fr'} or None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT base_file_name, language_code FROM Templates WHERE template_id = ?",
            (template_id,)
        )
        row = cursor.fetchone()
        if row:
            return {'file_name': row['base_file_name'], 'language': row['language_code']}
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_template_path_info: {e}")
        return None
    finally:
        if conn:
            conn.close()

def delete_template_and_get_file_info(template_id: int) -> dict | None:
    """
    Deletes the template record by template_id after fetching its file information.
    Returns {'file_name': 'name.xlsx', 'language': 'fr'} if successful, None otherwise.
    """
    conn = None
    try:
        conn = get_db_connection()
        conn.isolation_level = None # Start transaction
        cursor = conn.cursor()
        cursor.execute("BEGIN")

        # First, fetch the required information
        cursor.execute(
            "SELECT base_file_name, language_code FROM Templates WHERE template_id = ?",
            (template_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            print(f"Template with ID {template_id} not found for deletion.")
            return None

        file_info = {'file_name': row['base_file_name'], 'language': row['language_code']}

        # Proceed with deletion
        cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))

        if cursor.rowcount > 0:
            conn.commit()
            return file_info
        else:
            # This case should ideally not be reached if the select was successful
            # but included for robustness
            conn.rollback()
            print(f"Failed to delete template with ID {template_id} after fetching info.")
            return None

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error in delete_template_and_get_file_info: {e}")
        return None
    finally:
        if conn:
            conn.isolation_level = '' # Reset isolation level
            conn.close()

def set_default_template_by_id(template_id: int) -> bool:
    """
    Sets a template as the default for its template_type and language_code.
    Unsets other templates of the same type and language.
    Returns True on success, False on error.
    """
    conn = None
    try:
        conn = get_db_connection()
        conn.isolation_level = None # Start transaction
        cursor = conn.cursor()
        cursor.execute("BEGIN")

        # Get template_type and language_code for the given template_id
        cursor.execute(
            "SELECT template_type, language_code FROM Templates WHERE template_id = ?",
            (template_id,)
        )
        template_info = cursor.fetchone()

        if not template_info:
            print(f"Template with ID {template_id} not found.")
            conn.rollback()
            return False

        current_template_type = template_info['template_type']
        current_language_code = template_info['language_code']

        # Set is_default_for_type_lang = 0 for all templates of the same type and language
        cursor.execute(
            """
            UPDATE Templates
            SET is_default_for_type_lang = 0
            WHERE template_type = ? AND language_code = ?
            """,
            (current_template_type, current_language_code)
        )

        # Set is_default_for_type_lang = 1 for the specified template_id
        cursor.execute(
            "UPDATE Templates SET is_default_for_type_lang = 1 WHERE template_id = ?",
            (template_id,)
        )

        conn.commit()
        return True

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(f"Database error in set_default_template_by_id: {e}")
        return False
    finally:
        if conn:
            conn.isolation_level = '' # Reset isolation level
            conn.close()

def add_default_template_if_not_exists(template_data: dict) -> int | None:
    """
    Adds a template to the Templates table if it doesn't already exist
    based on template_name, template_type, and language_code.
    Returns the template_id of the new or existing template, or None on error.
    Expects template_data to include:
        'template_name' (e.g., "Proforma"),
        'template_type' (e.g., "document_excel", "document_word"),
        'language_code' (e.g., "fr", "en"),
        'base_file_name' (e.g., "proforma_template.xlsx"),
        'description' (optional),
        'category' (optional, e.g., "Finance", "Technical"),
        'is_default_for_type_lang' (optional, boolean, defaults to False),
        'category_name' (optional, string, defaults to "General")
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor() # Get a cursor from the connection

        name = template_data.get('template_name')
        ttype = template_data.get('template_type')
        lang = template_data.get('language_code')
        filename = template_data.get('base_file_name')
        category_name_text = template_data.get('category_name', "General")

        if not all([name, ttype, lang, filename]):
            print(f"Error: Missing required fields for default template: {template_data}")
            return None

        # Get or create category_id (using a separate connection for this, or pass cursor)
        # For simplicity here, calling the public function.
        # In a high-performance scenario, might pass the cursor.
        category_id = add_template_category(category_name_text, f"{category_name_text} (auto-created)")
        if category_id is None:
            print(f"Error: Could not get or create category_id for '{category_name_text}'.")
            return None # Cannot proceed without a category_id

        # Check if this specific template (name, type, lang) already exists
        cursor.execute("""
            SELECT template_id FROM Templates
            WHERE template_name = ? AND template_type = ? AND language_code = ?
        """, (name, ttype, lang))
        existing_template = cursor.fetchone()

        if existing_template:
            print(f"Default template '{name}' ({ttype}, {lang}) already exists with ID: {existing_template['template_id']}.")
            return existing_template['template_id']
        else:
            now = datetime.utcnow().isoformat() + "Z"
            sql = """
                INSERT INTO Templates (
                    template_name, template_type, language_code, base_file_name,
                    description, category_id, is_default_for_type_lang,
                    email_subject_template, -- Added email_subject_template
                    created_at, updated_at
                    -- created_by_user_id could be NULL or a system user ID
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) -- Added placeholder for email_subject_template
            """
            params = (
                name,
                ttype,
                lang,
                filename,
                template_data.get('description', f"Default {name} template"),
                category_id, # Use the fetched/created category_id
                template_data.get('is_default_for_type_lang', True),
                template_data.get('email_subject_template'), # Get email_subject_template
                now,
                now
            )
            cursor.execute(sql, params)
            conn.commit()
            new_id = cursor.lastrowid
            print(f"Added default template '{name}' ({ttype}, {lang}) with Category ID: {category_id}, new Template ID: {new_id}.")
            return new_id

    except sqlite3.Error as e:
        print(f"Database error in add_default_template_if_not_exists for '{template_data.get('template_name')}': {e}")
        if conn:
            conn.rollback() # Rollback on error
        return None
    finally:
        if conn:
            conn.close()

# CRUD functions for Projects
def add_project(project_data: dict) -> str | None:
    """
    Adds a new project to the database.
    Returns the new project_id if successful, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        new_project_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"

        sql = """
            INSERT INTO Projects (
                project_id, client_id, project_name, description, start_date, 
                deadline_date, budget, status_id, progress_percentage, 
                manager_team_member_id, priority, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_project_id,
            project_data.get('client_id'),
            project_data.get('project_name'),
            project_data.get('description'),
            project_data.get('start_date'),
            project_data.get('deadline_date'),
            project_data.get('budget'),
            project_data.get('status_id'),
            project_data.get('progress_percentage', 0),
            project_data.get('manager_team_member_id'),
            project_data.get('priority', 0),
            now,  # created_at
            now   # updated_at
        )
        
        cursor.execute(sql, params)
        conn.commit()
        return new_project_id
    except sqlite3.Error as e:
        print(f"Database error in add_project: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_project_by_id(project_id: str) -> dict | None:
    """Retrieves a project by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Projects WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_project_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_projects_by_client_id(client_id: str) -> list[dict]:
    """Retrieves all projects for a given client_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Projects WHERE client_id = ?", (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_projects_by_client_id: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_projects(filters: dict = None) -> list[dict]:
    """
    Retrieves all projects, optionally applying filters.
    Allowed filters: client_id, status_id, manager_team_member_id, priority.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM Projects"
        params = []
        
        if filters:
            where_clauses = []
            allowed_filters = ['client_id', 'status_id', 'manager_team_member_id', 'priority']
            for key, value in filters.items():
                if key in allowed_filters:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
                
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_projects: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_project(project_id: str, project_data: dict) -> bool:
    """
    Updates an existing project. Sets updated_at.
    Returns True if update was successful, False otherwise.
    """
    conn = None
    if not project_data:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat() + "Z"
        project_data['updated_at'] = now
        
        set_clauses = []
        params = []
        
        # Ensure only valid columns are updated
        valid_columns = [
            'client_id', 'project_name', 'description', 'start_date', 'deadline_date', 
            'budget', 'status_id', 'progress_percentage', 'manager_team_member_id', 
            'priority', 'updated_at'
        ]
        for key, value in project_data.items():
            if key in valid_columns:
                 set_clauses.append(f"{key} = ?")
                 params.append(value)
        
        if not set_clauses:
            return False 
            
        sql = f"UPDATE Projects SET {', '.join(set_clauses)} WHERE project_id = ?"
        params.append(project_id)
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_project: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_project(project_id: str) -> bool:
    """Deletes a project. Returns True if deletion was successful."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # ON DELETE CASCADE for Tasks related to this project will be handled by SQLite
        cursor.execute("DELETE FROM Projects WHERE project_id = ?", (project_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_project: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for Tasks
def add_task(task_data: dict) -> int | None:
    """
    Adds a new task to the database. Returns the task_id if successful.
    Sets created_at and updated_at.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"

        sql = """
            INSERT INTO Tasks (
                project_id, task_name, description, status_id, assignee_team_member_id,
                reporter_team_member_id, due_date, priority, estimated_hours,
                actual_hours_spent, parent_task_id, created_at, updated_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            task_data.get('project_id'),
            task_data.get('task_name'),
            task_data.get('description'),
            task_data.get('status_id'),
            task_data.get('assignee_team_member_id'),
            task_data.get('reporter_team_member_id'),
            task_data.get('due_date'),
            task_data.get('priority', 0),
            task_data.get('estimated_hours'),
            task_data.get('actual_hours_spent'),
            task_data.get('parent_task_id'),
            now,  # created_at
            now,  # updated_at
            task_data.get('completed_at') # Explicitly set if provided
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_task: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_task_by_id(task_id: int) -> dict | None:
    """Retrieves a task by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_task_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_tasks_by_project_id(project_id: str, filters: dict = None) -> list[dict]:
    """
    Retrieves tasks for a given project_id, optionally applying filters.
    Allowed filters: assignee_team_member_id, status_id, priority.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM Tasks WHERE project_id = ?"
        params = [project_id]
        
        if filters:
            where_clauses = []
            allowed_filters = ['assignee_team_member_id', 'status_id', 'priority']
            for key, value in filters.items():
                if key in allowed_filters:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
            if where_clauses:
                sql += " AND " + " AND ".join(where_clauses)
                
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_tasks_by_project_id: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_task(task_id: int, task_data: dict) -> bool:
    """
    Updates an existing task. Sets updated_at.
    If 'completed_at' is in task_data, it will be updated.
    (Logic for setting 'completed_at' based on status change should ideally be handled by calling code).
    Returns True on success.
    """
    conn = None
    if not task_data:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        task_data['updated_at'] = now
        
        set_clauses = []
        params = []
        
        valid_columns = [
            'project_id', 'task_name', 'description', 'status_id', 'assignee_team_member_id',
            'reporter_team_member_id', 'due_date', 'priority', 'estimated_hours',
            'actual_hours_spent', 'parent_task_id', 'updated_at', 'completed_at'
        ]
        for key, value in task_data.items():
            if key in valid_columns: # Ensure key is a valid column
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
            
        sql = f"UPDATE Tasks SET {', '.join(set_clauses)} WHERE task_id = ?"
        params.append(task_id)
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_task: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_task(task_id: int) -> bool:
    """Deletes a task. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Tasks WHERE task_id = ?", (task_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_task: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for Users
def add_user(user_data: dict) -> str | None:
    """
    Adds a new user to the database.
    Generates user_id (UUID), hashes password.
    Returns the new user_id if successful, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        new_user_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"
        
        if 'password' not in user_data or not user_data['password']:
            print("Password is required to create a user.")
            return None
        if 'username' not in user_data or not user_data['username']:
            print("Username is required to create a user.")
            return None
        if 'email' not in user_data or not user_data['email']:
            print("Email is required to create a user.")
            return None
        if 'role' not in user_data or not user_data['role']:
            print("Role is required to create a user.")
            return None

        password_hash = hashlib.sha256(user_data['password'].encode('utf-8')).hexdigest()

        sql = """
            INSERT INTO Users (
                user_id, username, password_hash, full_name, email, role, 
                is_active, created_at, updated_at, last_login_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_user_id,
            user_data.get('username'),
            password_hash,
            user_data.get('full_name'),
            user_data.get('email'),
            user_data.get('role'),
            user_data.get('is_active', True),
            now,  # created_at
            now,  # updated_at
            user_data.get('last_login_at') 
        )
        
        cursor.execute(sql, params)
        conn.commit()
        return new_user_id
    except sqlite3.Error as e:
        print(f"Database error in add_user: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_by_id(user_id: str) -> dict | None:
    """Retrieves a user by their ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_user_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_by_username(username: str) -> dict | None:
    """Retrieves a user by their username."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_user_by_username: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_user(user_id: str, user_data: dict) -> bool:
    """
    Updates an existing user's information.
    If 'password' is in user_data, it will be hashed and updated.
    Sets updated_at. Returns True on success.
    """
    conn = None
    if not user_data:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat() + "Z"
        user_data['updated_at'] = now
        
        if 'password' in user_data:
            if user_data['password']: # Ensure password is not empty
                user_data['password_hash'] = hashlib.sha256(user_data.pop('password').encode('utf-8')).hexdigest()
            else:
                user_data.pop('password') # Remove empty password from update data
        
        set_clauses = []
        params = []
        
        valid_columns = ['username', 'password_hash', 'full_name', 'email', 'role', 'is_active', 'updated_at', 'last_login_at']
        for key, value in user_data.items():
            if key in valid_columns:
                 set_clauses.append(f"{key} = ?")
                 params.append(value)
        
        if not set_clauses: # No valid fields to update (e.g. only empty password was provided)
            return False 
            
        sql = f"UPDATE Users SET {', '.join(set_clauses)} WHERE user_id = ?"
        params.append(user_id)
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_user: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_user_password(username: str, password: str) -> dict | None:
    """
    Verifies a user's password.
    Returns user data (dict) if verification is successful, otherwise None.
    """
    user = get_user_by_username(username)
    if user and user['is_active']: # Check if user exists and is active
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        if password_hash == user['password_hash']:
            # Optionally update last_login_at here if desired
            # update_user(user['user_id'], {'last_login_at': datetime.utcnow().isoformat() + "Z"})
            return user
    return None

def delete_user(user_id: str) -> bool:
    """
    Deletes a user (hard delete).
    Returns True if deletion was successful.
    Note: TeamMembers.user_id will be set to NULL due to ON DELETE SET NULL.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_user: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for TeamMembers
def add_team_member(member_data: dict) -> int | None:
    """
    Adds a new team member. Returns team_member_id (AUTOINCREMENT) or None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"

        sql = """
            INSERT INTO TeamMembers (
                user_id, full_name, email, role_or_title, department, 
                phone_number, profile_picture_url, is_active, notes, 
                hire_date, performance, skills,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            member_data.get('user_id'), # Can be None
            member_data.get('full_name'),
            member_data.get('email'),
            member_data.get('role_or_title'),
            member_data.get('department'),
            member_data.get('phone_number'),
            member_data.get('profile_picture_url'),
            member_data.get('is_active', True),
            member_data.get('notes'),
            member_data.get('hire_date'),
            member_data.get('performance', 0),
            member_data.get('skills'),
            now, # created_at
            now  # updated_at
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_team_member: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_team_member_by_id(team_member_id: int) -> dict | None:
    """Retrieves a team member by their ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM TeamMembers WHERE team_member_id = ?", (team_member_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_team_member_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_team_members(filters: dict = None) -> list[dict]:
    """
    Retrieves all team members, optionally applying filters.
    Allowed filters: is_active (boolean), department (string).
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM TeamMembers"
        params = []
        
        if filters:
            where_clauses = []
            allowed_filters = ['is_active', 'department', 'user_id'] 
            for key, value in filters.items():
                if key in allowed_filters:
                    if key == 'is_active' and isinstance(value, bool):
                         where_clauses.append(f"{key} = ?")
                         params.append(1 if value else 0)
                    else:
                        where_clauses.append(f"{key} = ?")
                        params.append(value)
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
                
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_team_members: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_team_member(team_member_id: int, member_data: dict) -> bool:
    """
    Updates an existing team member. Sets updated_at.
    Returns True on success.
    """
    conn = None
    if not member_data:
        return False

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        member_data['updated_at'] = now
        
        set_clauses = []
        params = []
        
        valid_columns = [
            'user_id', 'full_name', 'email', 'role_or_title', 'department', 
            'phone_number', 'profile_picture_url', 'is_active', 'notes',
            'hire_date', 'performance', 'skills', 'updated_at'
        ]
        for key, value in member_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
            
        sql = f"UPDATE TeamMembers SET {', '.join(set_clauses)} WHERE team_member_id = ?"
        params.append(team_member_id)
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_team_member: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_team_member(team_member_id: int) -> bool:
    """Deletes a team member (hard delete). Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM TeamMembers WHERE team_member_id = ?", (team_member_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_team_member: {e}")
        return False
    finally:
        if conn:
            conn.close()

# CRUD functions for Contacts
def add_contact(contact_data: dict) -> int | None:
    """Adds a new contact. Returns contact_id (AUTOINCREMENT) or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"

        # Fallback for 'name' if 'displayName' is not provided
        name_to_insert = contact_data.get('displayName', contact_data.get('name'))

        sql = """
            INSERT INTO Contacts (
                name, email, phone, position, company_name, notes,
                givenName, familyName, displayName, phone_type, email_type,
                address_formattedValue, address_streetAddress, address_city,
                address_region, address_postalCode, address_country,
                organization_name, organization_title, birthday_date,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            name_to_insert,
            contact_data.get('email'),
            contact_data.get('phone'),
            contact_data.get('position'),
            contact_data.get('company_name'),
            contact_data.get('notes'), # notes_text
            contact_data.get('givenName'),
            contact_data.get('familyName'),
            contact_data.get('displayName'),
            contact_data.get('phone_type'),
            contact_data.get('email_type'),
            contact_data.get('address_formattedValue'),
            contact_data.get('address_streetAddress'),
            contact_data.get('address_city'),
            contact_data.get('address_region'),
            contact_data.get('address_postalCode'),
            contact_data.get('address_country'),
            contact_data.get('organization_name'),
            contact_data.get('organization_title'),
            contact_data.get('birthday_date'),
            now, now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_contact: {e}")
        return None
    finally:
        if conn: conn.close()

def get_contact_by_id(contact_id: int) -> dict | None:
    """Retrieves a contact by their ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Contacts WHERE contact_id = ?", (contact_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_contact_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_contact_by_email(email: str) -> dict | None:
    """Retrieves a contact by their email."""
    conn = None
    if not email: return None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Contacts WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_contact_by_email: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_contacts(filters: dict = None) -> list[dict]:
    """
    Retrieves all contacts. Filters by 'company_name' (exact) or 'name' (partial LIKE).
    Now selects all new columns.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Contacts" # Selects all columns including new ones
        params = []
        where_clauses = []
        if filters:
            if 'company_name' in filters:
                where_clauses.append("company_name = ?")
                params.append(filters['company_name'])
            if 'name' in filters: # This will search in 'name' or 'displayName'
                where_clauses.append("(name LIKE ? OR displayName LIKE ?)")
                params.append(f"%{filters['name']}%")
                params.append(f"%{filters['name']}%")
            # TODO: Add filters for new fields if needed
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
            
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_contacts: {e}")
        return []
    finally:
        if conn: conn.close()

def update_contact(contact_id: int, contact_data: dict) -> bool:
    """Updates an existing contact. Sets updated_at."""
    conn = None
    if not contact_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        contact_data['updated_at'] = now

        # Fallback for 'name' if 'displayName' is provided and 'name' is not
        if 'displayName' in contact_data and 'name' not in contact_data:
            contact_data['name'] = contact_data['displayName']
        elif 'name' in contact_data and 'displayName' not in contact_data:
             # If only 'name' is provided, ensure 'displayName' is also updated if it's meant to be the primary display
             # This depends on application logic, for now, we'll update 'name' if 'displayName' isn't explicitly set to something else.
             # A more robust approach might be to always set displayName = name if displayName is not in contact_data.
             # For now, let's assume if 'displayName' is not in contact_data, it's not being changed.
             pass


        # Ensure only valid columns are updated
        valid_columns = [
            'name', 'email', 'phone', 'position', 'company_name', 'notes',
            'givenName', 'familyName', 'displayName', 'phone_type', 'email_type',
            'address_formattedValue', 'address_streetAddress', 'address_city',
            'address_region', 'address_postalCode', 'address_country',
            'organization_name', 'organization_title', 'birthday_date', 'updated_at'
        ]

        set_clauses = []
        params = []

        for key, value in contact_data.items():
            if key in valid_columns: # Check if the key is a valid column to update
                set_clauses.append(f"{key} = ?")
                params.append(value)
            elif key == 'contact_id': # Skip primary key
                continue
        
        if not set_clauses:
            print("Warning: No valid fields to update in update_contact.")
            return False

        params.append(contact_id)
        
        sql = f"UPDATE Contacts SET {', '.join(set_clauses)} WHERE contact_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_contact: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_contact(contact_id: int) -> bool:
    """Deletes a contact. Associated ClientContacts are handled by ON DELETE CASCADE."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Contacts WHERE contact_id = ?", (contact_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_contact: {e}")
        return False
    finally:
        if conn: conn.close()

# Functions for ClientContacts association
def link_contact_to_client(client_id: str, contact_id: int, is_primary: bool = False, can_receive_documents: bool = True) -> int | None:
    """Links a contact to a client."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            INSERT INTO ClientContacts (client_id, contact_id, is_primary_for_client, can_receive_documents)
            VALUES (?, ?, ?, ?)
        """
        params = (client_id, contact_id, is_primary, can_receive_documents)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e: # Handles UNIQUE constraint violation if link already exists
        print(f"Database error in link_contact_to_client: {e}")
        return None
    finally:
        if conn: conn.close()

def unlink_contact_from_client(client_id: str, contact_id: int) -> bool:
    """Unlinks a contact from a client."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM ClientContacts WHERE client_id = ? AND contact_id = ?"
        cursor.execute(sql, (client_id, contact_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in unlink_contact_from_client: {e}")
        return False
    finally:
        if conn: conn.close()

def get_contacts_for_client(client_id: str) -> list[dict]:
    """Retrieves all contacts for a given client, including link details."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT c.*, cc.is_primary_for_client, cc.can_receive_documents, cc.client_contact_id
            FROM Contacts c
            JOIN ClientContacts cc ON c.contact_id = cc.contact_id
            WHERE cc.client_id = ?
        """
        cursor.execute(sql, (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_contacts_for_client: {e}")
        return []
    finally:
        if conn: conn.close()

def get_clients_for_contact(contact_id: int) -> list[dict]:
    """Retrieves all clients associated with a contact."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT cl.*, cc.is_primary_for_client, cc.can_receive_documents, cc.client_contact_id
            FROM Clients cl
            JOIN ClientContacts cc ON cl.client_id = cc.client_id
            WHERE cc.contact_id = ?
        """
        cursor.execute(sql, (contact_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_clients_for_contact: {e}")
        return []
    finally:
        if conn: conn.close()

def get_specific_client_contact_link_details(client_id: str, contact_id: int) -> dict | None:
    """
    Retrieves specific details (client_contact_id, is_primary_for_client, can_receive_documents)
    for a single link between a client and a contact.
    Returns a dict if the link is found, otherwise None.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT client_contact_id, is_primary_for_client, can_receive_documents
            FROM ClientContacts
            WHERE client_id = ? AND contact_id = ?
        """
        cursor.execute(sql, (client_id, contact_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_specific_client_contact_link_details: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_client_contact_link(client_contact_id: int, details: dict) -> bool:
    """Updates details of a client-contact link (is_primary, can_receive_documents)."""
    conn = None
    if not details or not any(key in details for key in ['is_primary_for_client', 'can_receive_documents']):
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        set_clauses = []
        params = []
        if 'is_primary_for_client' in details:
            set_clauses.append("is_primary_for_client = ?")
            params.append(details['is_primary_for_client'])
        if 'can_receive_documents' in details:
            set_clauses.append("can_receive_documents = ?")
            params.append(details['can_receive_documents'])
        
        if not set_clauses: return False # Should not happen due to check above

        params.append(client_contact_id)
        sql = f"UPDATE ClientContacts SET {', '.join(set_clauses)} WHERE client_contact_id = ?"
        
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_client_contact_link: {e}")
        return False
    finally:
        if conn: conn.close()

# CRUD functions for ProductEquivalencies
def add_product_equivalence(product_id_a: int, product_id_b: int) -> int | None:
    """
    Adds a product equivalence pair.
    Ensures product_id_a < product_id_b to maintain uniqueness.
    Returns equivalence_id of the new or existing record.
    """
    if product_id_a == product_id_b:
        print("Error: Cannot create equivalence for a product with itself.")
        return None

    p_a = min(product_id_a, product_id_b)
    p_b = max(product_id_a, product_id_b)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO ProductEquivalencies (product_id_a, product_id_b) VALUES (?, ?)"
        cursor.execute(sql, (p_a, p_b))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Pair already exists
        print(f"IntegrityError: Product equivalence pair ({p_a}, {p_b}) likely already exists.")
        cursor.execute("SELECT equivalence_id FROM ProductEquivalencies WHERE product_id_a = ? AND product_id_b = ?", (p_a, p_b))
        row = cursor.fetchone()
        return row['equivalence_id'] if row else None # Should find it if IntegrityError was due to this UNIQUE constraint
    except sqlite3.Error as e:
        print(f"Database error in add_product_equivalence: {e}")
        return None
    finally:
        if conn: conn.close()

def get_equivalent_products(product_id: int) -> list[dict]:
    """
    Retrieves all products equivalent to the given product_id.
    Returns a list of product dictionaries.
    """
    conn = None
    equivalent_product_ids = set()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Find pairs where product_id is product_id_a
        cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (product_id,))
        rows_a = cursor.fetchall()
        for row in rows_a:
            equivalent_product_ids.add(row['product_id_b'])

        # Find pairs where product_id is product_id_b
        cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (product_id,))
        rows_b = cursor.fetchall()
        for row in rows_b:
            equivalent_product_ids.add(row['product_id_a'])

        equivalent_products = []
        if equivalent_product_ids:
            # Fetch full details for each equivalent product ID
            # Using a placeholder for multiple IDs to avoid complex IN clause for now, iterate instead.
            # For larger sets, an IN clause would be more efficient.
            for eq_id in equivalent_product_ids:
                prod_details = get_product_by_id(eq_id) # This function now includes weight and dimensions
                if prod_details:
                    equivalent_products.append(prod_details)
        return equivalent_products

    except sqlite3.Error as e:
        print(f"Database error in get_equivalent_products: {e}")
        return []
    finally:
        if conn: conn.close()

# CRUD functions for ProductEquivalencies
def add_product_equivalence(product_id_a: int, product_id_b: int) -> int | None:
    """
    Adds a product equivalence pair.
    Ensures product_id_a < product_id_b to maintain uniqueness.
    Returns equivalence_id of the new or existing record.
    """
    if product_id_a == product_id_b:
        print("Error: Cannot create equivalence for a product with itself.")
        return None

    # Ensure p_a is always the smaller ID
    p_a = min(product_id_a, product_id_b)
    p_b = max(product_id_a, product_id_b)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO ProductEquivalencies (product_id_a, product_id_b) VALUES (?, ?)"
        cursor.execute(sql, (p_a, p_b))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError: # Pair already exists
        print(f"IntegrityError: Product equivalence pair ({p_a}, {p_b}) likely already exists.")
        # Fetch the ID of the existing pair
        try:
            cursor.execute("SELECT equivalence_id FROM ProductEquivalencies WHERE product_id_a = ? AND product_id_b = ?", (p_a, p_b))
            row = cursor.fetchone()
            if row:
                return row['equivalence_id']
            else:
                # This case should be rare if IntegrityError was due to the unique constraint
                print(f"Warning: IntegrityError for pair ({p_a}, {p_b}) but could not retrieve existing ID.")
                return None
        except sqlite3.Error as e_select:
            print(f"Database error while trying to retrieve existing equivalence_id for ({p_a}, {p_b}): {e_select}")
            return None
    except sqlite3.Error as e:
        print(f"Database error in add_product_equivalence: {e}")
        if conn:
            conn.rollback() # Rollback if not an integrity error on insert
        return None
    finally:
        if conn: conn.close()

def get_equivalent_products(product_id: int) -> list[dict]:
    """
    Retrieves all products equivalent to the given product_id.
    Returns a list of product dictionaries (including weight and dimensions).
    """
    conn = None
    equivalent_product_ids = set()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Find pairs where product_id is product_id_a
        cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (product_id,))
        rows_a = cursor.fetchall()
        for row in rows_a:
            equivalent_product_ids.add(row['product_id_b'])

        # Find pairs where product_id is product_id_b
        cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (product_id,))
        rows_b = cursor.fetchall()
        for row in rows_b:
            equivalent_product_ids.add(row['product_id_a'])

        equivalent_products_details = []
        if equivalent_product_ids:
            for eq_id in equivalent_product_ids:
                prod_details = get_product_by_id(eq_id) # get_product_by_id will be updated to include new fields
                if prod_details:
                    equivalent_products_details.append(prod_details)
        return equivalent_products_details

    except sqlite3.Error as e:
        print(f"Database error in get_equivalent_products: {e}")
        return []
    finally:
        if conn: conn.close()

# CRUD functions for Products
def add_product(product_data: dict) -> int | None:
    """Adds a new product, including weight and dimensions. Returns product_id or None."""
    conn = None
    try:
        product_name = product_data.get('product_name')
        base_unit_price = product_data.get('base_unit_price')
        language_code = product_data.get('language_code', 'fr') # Default to 'fr'

        if not product_name:
            print("Error in add_product: 'product_name' is required.")
            # Consider raising an error or returning a more specific indicator of failure
            return None
        if base_unit_price is None: # Price can be 0.0, so check for None explicitly
            print("Error in add_product: 'base_unit_price' is required.")
            # Consider raising an error or returning a more specific indicator of failure
            return None
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO Products (
                product_name, description, category, language_code, base_unit_price,
                unit_of_measure, weight, dimensions, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            product_name, product_data.get('description'),
            product_data.get('category'),
            language_code,
            base_unit_price,
            product_data.get('unit_of_measure'),
            product_data.get('weight'),
            product_data.get('dimensions'),
            product_data.get('is_active', True),
            now, now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        # This will catch the UNIQUE constraint violation for (product_name, language_code)
        print(f"IntegrityError in add_product for name '{product_name}' and lang '{language_code}': {e}")
        if conn:
            conn.rollback()
        # Optionally, here you could query for the existing product_id if needed:
        # cursor.execute("SELECT product_id FROM Products WHERE product_name = ? AND language_code = ?", (product_name, language_code))
        # existing_product = cursor.fetchone()
        # if existing_product: return existing_product['product_id']
        return None # Indicates "add failed" or "already exists"
    except sqlite3.Error as e:
        print(f"Database error in add_product: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn: conn.close()

def get_product_by_id(product_id: int) -> dict | None:
    """Retrieves a product by ID, including weight and dimensions."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Ensure all desired columns including new ones are selected
        cursor.execute("SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at FROM Products WHERE product_id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_product_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_product_by_name(product_name: str) -> dict | None:
    """Retrieves a product by its exact name, including weight and dimensions. Returns a dict or None if not found."""
    conn = None
    if not product_name:
        return None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Ensure all desired columns including new ones are selected
        cursor.execute("SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at FROM Products WHERE product_name = ?", (product_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_product_by_name: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_products(filters: dict = None) -> list[dict]:
    """Retrieves all products, including weight and dimensions. Filters by category (exact) or product_name (partial LIKE)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Ensure all desired columns including new ones are selected
        sql = "SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at FROM Products"
        params = []
        where_clauses = []
        if filters:
            if 'category' in filters:
                where_clauses.append("category = ?")
                params.append(filters['category'])
            if 'product_name' in filters:
                where_clauses.append("product_name LIKE ?")
                params.append(f"%{filters['product_name']}%")
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
            
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_products: {e}")
        return []
    finally:
        if conn: conn.close()

def update_product(product_id: int, product_data: dict) -> bool:
    """Updates an existing product, including weight and dimensions. Sets updated_at."""
    conn = None
    if not product_data:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        product_data['updated_at'] = now
        
        # Ensure only valid columns are updated
        valid_columns = [
            'product_name', 'description', 'category', 'language_code',
            'base_unit_price', 'unit_of_measure', 'weight', 'dimensions',
            'is_active', 'updated_at'
        ]
        
        set_clauses = []
        params = []
        for key, value in product_data.items():
            if key in valid_columns: # Check if the key is a valid column to update
                set_clauses.append(f"{key} = ?")
                params.append(value)

        if not set_clauses:
            print("Warning: No valid fields to update in update_product.")
            return False

        params.append(product_id)
        sql = f"UPDATE Products SET {', '.join(set_clauses)} WHERE product_id = ?"

        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_product: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_product(product_id: int) -> bool:
    """Deletes a product. Associated ClientProjectProducts are handled by ON DELETE CASCADE."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Products WHERE product_id = ?", (product_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_product: {e}")
        return False
    finally:
        if conn: conn.close()

def get_products_by_name_pattern(pattern: str) -> list[dict] | None:
    """
    Retrieves products where the product_name matches the given pattern (LIKE %pattern%).
    Returns a list of up to 10 matching products as dictionaries, or None on error.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        search_pattern = f"%{pattern}%"
        # Ensure all desired columns including new ones are selected
        sql = """
            SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at
            FROM Products
            WHERE product_name LIKE ?
            ORDER BY product_name
            LIMIT 10
        """
        cursor.execute(sql, (search_pattern,))
        rows = cursor.fetchall()

        products = [dict(row) for row in rows]
        return products

    except sqlite3.Error as e:
        print(f"Database error in get_products_by_name_pattern: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_products_for_selection(language_code: str = None, name_pattern: str = None) -> list[dict]:
    """
    Retrieves active products for selection, optionally filtered by language_code
    and/or name_pattern (searches product_name and description).
    Orders by product_name.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql_params = []
        # Start with base selection of active products
        sql_where_clauses = ["is_active = TRUE"]

        if language_code:
            sql_where_clauses.append("language_code = ?")
            sql_params.append(language_code)

        if name_pattern:
            # The name_pattern should be passed with wildcards already, e.g., "%search_term%"
            sql_where_clauses.append("(product_name LIKE ? OR description LIKE ?)")
            sql_params.append(name_pattern)
            sql_params.append(name_pattern)

        sql = f"""
            SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at
            FROM Products
            WHERE {' AND '.join(sql_where_clauses)}
            ORDER BY product_name
        """

        cursor.execute(sql, tuple(sql_params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_products_for_selection: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Functions for ClientProjectProducts association
def add_product_to_client_or_project(link_data: dict) -> int | None:
    """Links a product to a client or project, calculating total price."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Initialize effective_unit_price in case of early exit or error before its definition
        effective_unit_price = None # Ensure it's in scope for the except block
        product_info = None # Ensure it's in scope for the except block

        product_id = link_data.get('product_id')
        product_info = get_product_by_id(product_id) # Need this for base price
        if not product_info:
            print(f"Product with ID {product_id} not found.")
            return None

        quantity = link_data.get('quantity', 1)
        unit_price_override = link_data.get('unit_price_override')

        if unit_price_override is not None: # Explicit check for None
            effective_unit_price = unit_price_override
        else:
            effective_unit_price = product_info.get('base_unit_price')

        # Ensure effective_unit_price is not None before multiplication
        if effective_unit_price is None:
            # This case should ideally not be reached if base_unit_price is NOT NULL in DB
            # and product_info is correctly fetched.
            print(f"Warning: effective_unit_price was None for product ID {product_id} (Quantity: {quantity}, Override: {unit_price_override}, Base from DB: {product_info.get('base_unit_price') if product_info else 'N/A'}). Defaulting to 0.0.")
            effective_unit_price = 0.0

        total_price_calculated = quantity * effective_unit_price

        sql = """
            INSERT INTO ClientProjectProducts (
                client_id, project_id, product_id, quantity, unit_price_override, total_price_calculated, added_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            link_data.get('client_id'),
            link_data.get('project_id'), # Can be NULL
            product_id,
            quantity,
            link_data.get('unit_price_override'), # Store override, or NULL if base used
            total_price_calculated,
            datetime.utcnow().isoformat() + "Z"
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except TypeError as te: # Specifically catch the error we are investigating
        print(f"TypeError in add_product_to_client_or_project: {te}")
        print(f"  product_id: {link_data.get('product_id')}")
        print(f"  quantity: {link_data.get('quantity', 1)}")
        print(f"  unit_price_override from link_data: {link_data.get('unit_price_override')}")
        if product_info: # product_info might be None if error happened before it was fetched
            print(f"  base_unit_price from product_info: {product_info.get('base_unit_price')}")
        else:
            print(f"  product_info was None or not fetched prior to error.")
        print(f"  effective_unit_price at point of error: {effective_unit_price if 'effective_unit_price' in locals() else 'Not yet defined or error before definition'}")
        return None # Indicate failure
    except sqlite3.Error as e:
        print(f"Database error in add_product_to_client_or_project: {e}")
        return None
    finally:
        if conn: conn.close()

def get_products_for_client_or_project(client_id: str, project_id: str = None) -> list[dict]:
    """Fetches products for a client, optionally filtered by project_id. Joins with Products."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT cpp.*,
                   p.product_id as product_id_original_lang, p.product_name, p.description as product_description,
                   p.category as product_category, p.base_unit_price, p.unit_of_measure,
                   p.weight, p.dimensions, p.language_code
            FROM ClientProjectProducts cpp
            JOIN Products p ON cpp.product_id = p.product_id
            WHERE cpp.client_id = ?
        """
        params = [client_id]
        
        if project_id:
            sql += " AND cpp.project_id = ?"
            params.append(project_id)
        else: # Explicitly handle case where we want products not tied to any project for this client
            sql += " AND cpp.project_id IS NULL"
            
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_products_for_client_or_project: {e}")
        return []
    finally:
        if conn: conn.close()

def update_client_project_product(link_id: int, update_data: dict) -> bool:
    """Updates a ClientProjectProduct link. Recalculates total_price if needed."""
    conn = None
    if not update_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch current link data to get product_id and existing values for price calculation
        cursor.execute("SELECT * FROM ClientProjectProducts WHERE client_project_product_id = ?", (link_id,))
        current_link = cursor.fetchone()
        if not current_link:
            print(f"ClientProjectProduct link with ID {link_id} not found.")
            return False
        
        current_link_dict = dict(current_link)
        new_quantity = update_data.get('quantity', current_link_dict['quantity'])
        new_unit_price_override = update_data.get('unit_price_override', current_link_dict['unit_price_override'])

        final_unit_price = new_unit_price_override
        if final_unit_price is None: # If override is removed or was never there, use base price
            product_info = get_product_by_id(current_link_dict['product_id'])
            if not product_info: return False # Should not happen if data is consistent
            final_unit_price = product_info['base_unit_price']
        
        update_data['total_price_calculated'] = new_quantity * final_unit_price
        
        set_clauses = [f"{key} = ?" for key in update_data.keys()]
        params_list = list(update_data.values())
        params_list.append(link_id)
        
        sql = f"UPDATE ClientProjectProducts SET {', '.join(set_clauses)} WHERE client_project_product_id = ?"
        cursor.execute(sql, params_list)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_client_project_product: {e}")
        return False
    finally:
        if conn: conn.close()

def remove_product_from_client_or_project(link_id: int) -> bool:
    """Removes a product link from a client/project."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM ClientProjectProducts WHERE client_project_product_id = ?"
        cursor.execute(sql, (link_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in remove_product_from_client_or_project: {e}")
        return False
    finally:
        if conn: conn.close()

# CRUD functions for ClientDocuments
def add_client_document(doc_data: dict) -> str | None:
    """Adds a new client document. Returns document_id (UUID) or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        doc_id = uuid.uuid4().hex

        sql = """
            INSERT INTO ClientDocuments (
                document_id, client_id, project_id, document_name, file_name_on_disk,
                file_path_relative, document_type_generated, source_template_id,
                version_tag, notes, created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            doc_id, doc_data.get('client_id'), doc_data.get('project_id'),
            doc_data.get('document_name'), doc_data.get('file_name_on_disk'),
            doc_data.get('file_path_relative'), doc_data.get('document_type_generated'),
            doc_data.get('source_template_id'), doc_data.get('version_tag'),
            doc_data.get('notes'), now, now, doc_data.get('created_by_user_id')
        )
        cursor.execute(sql, params)
        conn.commit()
        return doc_id
    except sqlite3.Error as e:
        print(f"Database error in add_client_document: {e}")
        return None
    finally:
        if conn: conn.close()

def get_document_by_id(document_id: str) -> dict | None:
    """Retrieves a document by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ClientDocuments WHERE document_id = ?", (document_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_document_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_documents_for_client(client_id: str, filters: dict = None) -> list[dict]:
    """
    Retrieves documents for a client. 
    Filters by 'document_type_generated' (exact) or 'project_id' (exact).
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM ClientDocuments WHERE client_id = ?"
        params = [client_id]
        
        if filters:
            if 'document_type_generated' in filters:
                sql += " AND document_type_generated = ?"
                params.append(filters['document_type_generated'])
            if 'project_id' in filters: # Can be None to filter for client-general docs
                if filters['project_id'] is None:
                    sql += " AND project_id IS NULL"
                else:
                    sql += " AND project_id = ?"
                    params.append(filters['project_id'])
            
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_documents_for_client: {e}")
        return []
    finally:
        if conn: conn.close()

def get_documents_for_project(project_id: str, filters: dict = None) -> list[dict]:
    """
    Retrieves documents for a project. 
    Filters by 'document_type_generated' (exact).
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM ClientDocuments WHERE project_id = ?"
        params = [project_id]
        
        if filters and 'document_type_generated' in filters:
            sql += " AND document_type_generated = ?"
            params.append(filters['document_type_generated'])
            
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_documents_for_project: {e}")
        return []
    finally:
        if conn: conn.close()

def update_client_document(document_id: str, doc_data: dict) -> bool:
    """Updates an existing client document. Sets updated_at."""
    conn = None
    if not doc_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        doc_data['updated_at'] = now
        
        # Exclude primary key from update set
        valid_columns = [
            'client_id', 'project_id', 'document_name', 'file_name_on_disk', 
            'file_path_relative', 'document_type_generated', 'source_template_id', 
            'version_tag', 'notes', 'updated_at', 'created_by_user_id'
        ]
        current_doc_data = {k: v for k, v in doc_data.items() if k in valid_columns}

        if not current_doc_data: return False

        set_clauses = [f"{key} = ?" for key in current_doc_data.keys()]
        params = list(current_doc_data.values())
        params.append(document_id)
        
        sql = f"UPDATE ClientDocuments SET {', '.join(set_clauses)} WHERE document_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_client_document: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_client_document(document_id: str) -> bool:
    """Deletes a client document."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ClientDocuments WHERE document_id = ?", (document_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_client_document: {e}")
        return False
    finally:
        if conn: conn.close()

# CRUD functions for SmtpConfigs
def _ensure_single_default_smtp(cursor: sqlite3.Cursor, exclude_id: int | None = None):
    """Internal helper to ensure only one SMTP config is default."""
    sql = "UPDATE SmtpConfigs SET is_default = FALSE WHERE is_default = TRUE"
    if exclude_id is not None:
        sql += " AND smtp_config_id != ?"
        cursor.execute(sql, (exclude_id,))
    else:
        cursor.execute(sql)

def add_smtp_config(config_data: dict) -> int | None:
    """
    Adds a new SMTP config. Returns smtp_config_id or None.
    Expects 'password_encrypted'. Handles 'is_default' logic.
    """
    conn = None
    try:
        conn = get_db_connection()
        # Use a transaction for default handling
        conn.isolation_level = None # Explicitly start transaction for some Python versions / DB drivers
        cursor = conn.cursor()
        cursor.execute("BEGIN")

        if config_data.get('is_default'):
            _ensure_single_default_smtp(cursor)

        now = datetime.utcnow().isoformat() + "Z" # Not in schema, but good practice if it were
        sql = """
            INSERT INTO SmtpConfigs (
                config_name, smtp_server, smtp_port, username, password_encrypted,
                use_tls, is_default, sender_email_address, sender_display_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            config_data.get('config_name'), config_data.get('smtp_server'),
            config_data.get('smtp_port'), config_data.get('username'),
            config_data.get('password_encrypted'), # Assumed pre-encrypted
            config_data.get('use_tls', True),
            config_data.get('is_default', False),
            config_data.get('sender_email_address'),
            config_data.get('sender_display_name')
        )
        cursor.execute(sql, params)
        new_id = cursor.lastrowid
        conn.commit()
        return new_id
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Database error in add_smtp_config: {e}")
        return None
    finally:
        if conn: 
            conn.isolation_level = '' # Reset to default
            conn.close()


def get_smtp_config_by_id(smtp_config_id: int) -> dict | None:
    """Retrieves an SMTP config by ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM SmtpConfigs WHERE smtp_config_id = ?", (smtp_config_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_smtp_config_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_default_smtp_config() -> dict | None:
    """Retrieves the default SMTP config."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM SmtpConfigs WHERE is_default = TRUE")
        row = cursor.fetchone()
        return dict(row) if row else None # Could be multiple if DB constraint not present, returns first
    except sqlite3.Error as e:
        print(f"Database error in get_default_smtp_config: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_smtp_configs() -> list[dict]:
    """Retrieves all SMTP configs."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM SmtpConfigs ORDER BY config_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_smtp_configs: {e}")
        return []
    finally:
        if conn: conn.close()

def update_smtp_config(smtp_config_id: int, config_data: dict) -> bool:
    """
    Updates an SMTP config. Handles 'is_default' logic.
    Expects 'password_encrypted' if password is to be changed.
    """
    conn = None
    if not config_data: return False
    try:
        conn = get_db_connection()
        conn.isolation_level = None
        cursor = conn.cursor()
        cursor.execute("BEGIN")

        if config_data.get('is_default'):
            _ensure_single_default_smtp(cursor, exclude_id=smtp_config_id)
        
        # Ensure password_encrypted is handled if present, otherwise original remains
        # This assumes if 'password_encrypted' is not in config_data, it's not being updated.
        valid_columns = [
            'config_name', 'smtp_server', 'smtp_port', 'username', 
            'password_encrypted', 'use_tls', 'is_default', 
            'sender_email_address', 'sender_display_name'
        ]
        current_config_data = {k: v for k,v in config_data.items() if k in valid_columns}
        if not current_config_data:
            conn.rollback() # No valid fields to update
            return False

        set_clauses = [f"{key} = ?" for key in current_config_data.keys()]
        params = list(current_config_data.values())
        params.append(smtp_config_id)
        
        sql = f"UPDATE SmtpConfigs SET {', '.join(set_clauses)} WHERE smtp_config_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Database error in update_smtp_config: {e}")
        return False
    finally:
        if conn: 
            conn.isolation_level = ''
            conn.close()

def delete_smtp_config(smtp_config_id: int) -> bool:
    """Deletes an SMTP config."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Consider logic if deleting the default config (e.g., pick another or ensure none is default)
        # For now, direct delete.
        cursor.execute("DELETE FROM SmtpConfigs WHERE smtp_config_id = ?", (smtp_config_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_smtp_config: {e}")
        return False
    finally:
        if conn: conn.close()

def set_default_smtp_config(smtp_config_id: int) -> bool:
    """Sets a specific SMTP config as default and unsets others."""
    conn = None
    try:
        conn = get_db_connection()
        conn.isolation_level = None
        cursor = conn.cursor()
        cursor.execute("BEGIN")
        
        _ensure_single_default_smtp(cursor, exclude_id=smtp_config_id)
        cursor.execute("UPDATE SmtpConfigs SET is_default = TRUE WHERE smtp_config_id = ?", (smtp_config_id,))
        updated_rows = cursor.rowcount
        
        conn.commit()
        return updated_rows > 0
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"Database error in set_default_smtp_config: {e}")
        return False
    finally:
        if conn: 
            conn.isolation_level = ''
            conn.close()

# --- ScheduledEmails Functions ---
def add_scheduled_email(email_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """INSERT INTO ScheduledEmails (recipient_email, subject, body_html, body_text, 
                                           scheduled_send_at, status, related_client_id, 
                                           related_project_id, created_by_user_id, created_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            email_data.get('recipient_email'), email_data.get('subject'),
            email_data.get('body_html'), email_data.get('body_text'),
            email_data.get('scheduled_send_at'), email_data.get('status', 'pending'),
            email_data.get('related_client_id'), email_data.get('related_project_id'),
            email_data.get('created_by_user_id'), now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error in add_scheduled_email: {e}")
        return None
    finally:
        if conn: conn.close()

def get_scheduled_email_by_id(scheduled_email_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ScheduledEmails WHERE scheduled_email_id = ?", (scheduled_email_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_scheduled_email_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_pending_scheduled_emails(before_time: str = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM ScheduledEmails WHERE status = 'pending'"
        params = []
        if before_time:
            sql += " AND scheduled_send_at <= ?"
            params.append(before_time)
        sql += " ORDER BY scheduled_send_at ASC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_pending_scheduled_emails: {e}")
        return []
    finally:
        if conn: conn.close()

def update_scheduled_email_status(scheduled_email_id: int, status: str, sent_at: str = None, error_message: str = None) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "UPDATE ScheduledEmails SET status = ?, sent_at = ?, error_message = ? WHERE scheduled_email_id = ?"
        params = (status, sent_at, error_message, scheduled_email_id)
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in update_scheduled_email_status: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_scheduled_email(scheduled_email_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # ON DELETE CASCADE handles EmailReminders
        cursor.execute("DELETE FROM ScheduledEmails WHERE scheduled_email_id = ?", (scheduled_email_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in delete_scheduled_email: {e}")
        return False
    finally:
        if conn: conn.close()

# --- EmailReminders Functions ---
def add_email_reminder(reminder_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO EmailReminders (scheduled_email_id, reminder_type, reminder_send_at, status)
                 VALUES (?, ?, ?, ?)"""
        params = (
            reminder_data.get('scheduled_email_id'), reminder_data.get('reminder_type'),
            reminder_data.get('reminder_send_at'), reminder_data.get('status', 'pending')
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error in add_email_reminder: {e}")
        return None
    finally:
        if conn: conn.close()

def get_pending_reminders(before_time: str = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM EmailReminders WHERE status = 'pending'"
        params = []
        if before_time:
            sql += " AND reminder_send_at <= ?"
            params.append(before_time)
        sql += " ORDER BY reminder_send_at ASC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows] # Consider joining with ScheduledEmails for context
    except sqlite3.Error as e:
        print(f"DB error in get_pending_reminders: {e}")
        return []
    finally:
        if conn: conn.close()

def update_reminder_status(reminder_id: int, status: str) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "UPDATE EmailReminders SET status = ? WHERE reminder_id = ?"
        cursor.execute(sql, (status, reminder_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in update_reminder_status: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_email_reminder(reminder_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM EmailReminders WHERE reminder_id = ?", (reminder_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in delete_email_reminder: {e}")
        return False
    finally:
        if conn: conn.close()

# --- ContactLists & ContactListMembers Functions ---
def add_contact_list(list_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """INSERT INTO ContactLists (list_name, description, created_by_user_id, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?)"""
        params = (
            list_data.get('list_name'), list_data.get('description'),
            list_data.get('created_by_user_id'), now, now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error in add_contact_list: {e}")
        return None
    finally:
        if conn: conn.close()

def get_contact_list_by_id(list_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ContactLists WHERE list_id = ?", (list_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_contact_list_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_contact_lists() -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ContactLists ORDER BY list_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_all_contact_lists: {e}")
        return []
    finally:
        if conn: conn.close()

def update_contact_list(list_id: int, list_data: dict) -> bool:
    conn = None
    if not list_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        list_data['updated_at'] = datetime.utcnow().isoformat() + "Z"
        set_clauses = [f"{key} = ?" for key in list_data.keys()]
        params = list(list_data.values())
        params.append(list_id)
        sql = f"UPDATE ContactLists SET {', '.join(set_clauses)} WHERE list_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in update_contact_list: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_contact_list(list_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # ON DELETE CASCADE handles ContactListMembers
        cursor.execute("DELETE FROM ContactLists WHERE list_id = ?", (list_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in delete_contact_list: {e}")
        return False
    finally:
        if conn: conn.close()

def add_contact_to_list(list_id: int, contact_id: int) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "INSERT INTO ContactListMembers (list_id, contact_id) VALUES (?, ?)"
        cursor.execute(sql, (list_id, contact_id))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e: # Handles unique constraint violation
        print(f"DB error in add_contact_to_list: {e}")
        return None
    finally:
        if conn: conn.close()

def remove_contact_from_list(list_id: int, contact_id: int) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "DELETE FROM ContactListMembers WHERE list_id = ? AND contact_id = ?"
        cursor.execute(sql, (list_id, contact_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in remove_contact_from_list: {e}")
        return False
    finally:
        if conn: conn.close()

def get_contacts_in_list(list_id: int) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """SELECT c.*, clm.added_at 
                 FROM Contacts c 
                 JOIN ContactListMembers clm ON c.contact_id = clm.contact_id 
                 WHERE clm.list_id = ?"""
        cursor.execute(sql, (list_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_contacts_in_list: {e}")
        return []
    finally:
        if conn: conn.close()

# CRUD functions for KPIs
def add_kpi(kpi_data: dict) -> int | None:
    """Adds a new KPI. Returns kpi_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO KPIs (
                project_id, name, value, target, trend, unit, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            kpi_data.get('project_id'),
            kpi_data.get('name'),
            kpi_data.get('value'),
            kpi_data.get('target'),
            kpi_data.get('trend'),
            kpi_data.get('unit'),
            now,  # created_at
            now   # updated_at
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_kpi: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_kpi_by_id(kpi_id: int) -> dict | None:
    """Retrieves a KPI by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM KPIs WHERE kpi_id = ?", (kpi_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_kpi_by_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_kpis_for_project(project_id: str) -> list[dict]:
    """Retrieves all KPIs for a given project_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM KPIs WHERE project_id = ?", (project_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_kpis_for_project: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_kpi(kpi_id: int, kpi_data: dict) -> bool:
    """Updates an existing KPI. Sets updated_at. Returns True on success."""
    conn = None
    if not kpi_data:
        return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        kpi_data['updated_at'] = now

        set_clauses = []
        params = []

        valid_columns = ['project_id', 'name', 'value', 'target', 'trend', 'unit', 'updated_at']
        for key, value in kpi_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                params.append(value)

        if not set_clauses:
            return False

        sql = f"UPDATE KPIs SET {', '.join(set_clauses)} WHERE kpi_id = ?"
        params.append(kpi_id)

        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_kpi: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_kpi(kpi_id: int) -> bool:
    """Deletes a KPI. Returns True on success."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM KPIs WHERE kpi_id = ?", (kpi_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_kpi: {e}")
        return False
    finally:
        if conn:
            conn.close()

# --- ApplicationSettings Functions ---
def get_setting(key: str) -> str | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT setting_value FROM ApplicationSettings WHERE setting_key = ?", (key,))
        row = cursor.fetchone()
        return row['setting_value'] if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_setting: {e}")
        return None
    finally:
        if conn: conn.close()

def set_setting(key: str, value: str) -> bool:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Using INSERT OR REPLACE (UPSERT)
        sql = "INSERT OR REPLACE INTO ApplicationSettings (setting_key, setting_value) VALUES (?, ?)"
        cursor.execute(sql, (key, value))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in set_setting: {e}")
        return False
    finally:
        if conn: conn.close()

# --- ActivityLog Functions ---
def add_activity_log(log_data: dict) -> int | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """INSERT INTO ActivityLog (user_id, action_type, details, related_entity_type, 
                                        related_entity_id, related_client_id, ip_address, user_agent)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            log_data.get('user_id'), log_data.get('action_type'), log_data.get('details'),
            log_data.get('related_entity_type'), log_data.get('related_entity_id'),
            log_data.get('related_client_id'), log_data.get('ip_address'), log_data.get('user_agent')
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"DB error in add_activity_log: {e}")
        return None
    finally:
        if conn: conn.close()

def get_activity_logs(limit: int = 50, filters: dict = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM ActivityLog"
        params = []
        where_clauses = []
        if filters:
            allowed = ['user_id', 'action_type', 'related_entity_type', 'related_entity_id', 'related_client_id']
            for key, value in filters.items():
                if key in allowed and value is not None:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
        
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_activity_logs: {e}")
        return []
    finally:
        if conn: conn.close()

# --- Default Templates Population ---
DEFAULT_COVER_PAGE_TEMPLATES = [
    {
        'template_name': 'Standard Report Cover',
        'description': 'A standard cover page for general reports.',
        'default_title': 'Report Title',
        'default_subtitle': 'Company Subdivision',
        'default_author': 'Automated Report Generator',
        'style_config_json': {'font': 'Helvetica', 'primary_color': '#2a2a2a', 'secondary_color': '#5cb85c'},
        'is_default_template': 1 # Mark as default
    },
    {
        'template_name': 'Financial Statement Cover',
        'description': 'Cover page for official financial statements.',
        'default_title': 'Financial Statement',
        'default_subtitle': 'Fiscal Year Ending YYYY',
        'default_author': 'Finance Department',
        'style_config_json': {'font': 'Times New Roman', 'primary_color': '#003366', 'secondary_color': '#e0a800'},
        'is_default_template': 1 # Mark as default
    },
    {
        'template_name': 'Creative Project Brief',
        'description': 'A vibrant cover for creative project briefs and proposals.',
        'default_title': 'Creative Brief: [Project Name]',
        'default_subtitle': 'Client: [Client Name]',
        'default_author': 'Creative Team',
        'style_config_json': {'font': 'Montserrat', 'primary_color': '#ff6347', 'secondary_color': '#4682b4', 'layout_hint': 'two-column'},
        'is_default_template': 1 # Mark as default
    },
    {
        'template_name': 'Technical Document Cover',
        'description': 'A clean and formal cover for technical documentation.',
        'default_title': 'Technical Specification Document',
        'default_subtitle': 'Version [VersionNumber]',
        'default_author': 'Engineering Team',
        'style_config_json': {'font': 'Roboto', 'primary_color': '#191970', 'secondary_color': '#cccccc'},
        'is_default_template': 1 # Mark as default
    }
]

def _populate_default_cover_page_templates():
    """
    Populates the CoverPageTemplates table with predefined default templates
    if they do not already exist by name.
    """
    print("Attempting to populate default cover page templates...")
    # Optionally, fetch a system user ID if you want to set created_by_user_id
    # system_user = get_user_by_username('system_user') # Define or fetch a system user
    # system_user_id = system_user['user_id'] if system_user else None

    for template_def in DEFAULT_COVER_PAGE_TEMPLATES:
        existing_template = get_cover_page_template_by_name(template_def['template_name'])
        if existing_template:
            print(f"Default template '{template_def['template_name']}' already exists. Skipping.")
        else:
            # template_def_with_user = {**template_def, 'created_by_user_id': system_user_id}
            # new_id = add_cover_page_template(template_def_with_user)
            new_id = add_cover_page_template(template_def) # Simpler: no user_id for defaults for now
            if new_id:
                print(f"Added default cover page template: '{template_def['template_name']}' with ID: {new_id}")
            else:
                print(f"Failed to add default cover page template: '{template_def['template_name']}'")
    print("Default cover page templates population attempt finished.")

# --- CoverPageTemplates CRUD ---
def add_cover_page_template(template_data: dict) -> str | None:
    """Adds a new cover page template. Returns template_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        new_template_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"

        style_config = template_data.get('style_config_json')
        if isinstance(style_config, dict): # Ensure it's a JSON string
            style_config = json.dumps(style_config)

        sql = """
            INSERT INTO CoverPageTemplates (
                template_id, template_name, description, default_title, default_subtitle,
                default_author, style_config_json, is_default_template,
                created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_template_id,
            template_data.get('template_name'),
            template_data.get('description'),
            template_data.get('default_title'),
            template_data.get('default_subtitle'),
            template_data.get('default_author'),
            style_config,
            template_data.get('is_default_template', 0), # Handle new field, default to 0
            now, now,
            template_data.get('created_by_user_id')
        )
        cursor.execute(sql, params)
        conn.commit()
        return new_template_id
    except sqlite3.Error as e:
        print(f"Database error in add_cover_page_template: {e}")
        return None
    finally:
        if conn: conn.close()

def get_cover_page_template_by_id(template_id: str) -> dict | None:
    """Retrieves a cover page template by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_id = ?", (template_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('style_config_json'):
                try:
                    data['style_config_json'] = json.loads(data['style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse style_config_json for template {template_id}")
                    # Keep as string or set to default dict? For now, keep as is.
            return data
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_cover_page_template_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_cover_page_template_by_name(template_name: str) -> dict | None:
    """Retrieves a cover page template by its unique name."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_name = ?", (template_name,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('style_config_json'):
                try:
                    data['style_config_json'] = json.loads(data['style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse style_config_json for template {template_name}")
            return data
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_cover_page_template_by_name: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_cover_page_templates(is_default: bool = None, limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Retrieves all cover page templates, optionally filtered by is_default.
    Includes pagination.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "SELECT * FROM CoverPageTemplates"
        params = []

        if is_default is not None:
            sql += " WHERE is_default_template = ?"
            params.append(1 if is_default else 0)

        sql += " ORDER BY template_name LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        templates = []
        for row in rows:
            data = dict(row)
            if data.get('style_config_json'):
                try:
                    data['style_config_json'] = json.loads(data['style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse style_config_json for template ID {data['template_id']}")
            templates.append(data)
        return templates
    except sqlite3.Error as e:
        print(f"Database error in get_all_cover_page_templates: {e}")
        return []
    finally:
        if conn: conn.close()

def update_cover_page_template(template_id: str, update_data: dict) -> bool:
    """Updates an existing cover page template."""
    conn = None
    if not update_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        update_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

        if 'style_config_json' in update_data and isinstance(update_data['style_config_json'], dict):
            update_data['style_config_json'] = json.dumps(update_data['style_config_json'])

        # Ensure boolean/integer fields are correctly formatted for SQL if needed
        if 'is_default_template' in update_data:
            update_data['is_default_template'] = 1 if update_data['is_default_template'] else 0

        valid_columns = [
            'template_name', 'description', 'default_title', 'default_subtitle',
            'default_author', 'style_config_json', 'is_default_template', 'updated_at'
            # created_by_user_id is typically not updated this way
        ]

        set_clauses = []
        sql_params = []

        for key, value in update_data.items():
            if key in valid_columns:
                set_clauses.append(f"{key} = ?")
                sql_params.append(value)

        if not set_clauses:
            return False # Nothing valid to update

        sql_params.append(template_id)
        sql = f"UPDATE CoverPageTemplates SET {', '.join(set_clauses)} WHERE template_id = ?"

        cursor.execute(sql, sql_params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_cover_page_template: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_cover_page_template(template_id: str) -> bool:
    """Deletes a cover page template."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Consider impact on CoverPages using this template (ON DELETE SET NULL)
        cursor.execute("DELETE FROM CoverPageTemplates WHERE template_id = ?", (template_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_cover_page_template: {e}")
        return False
    finally:
        if conn: conn.close()

# --- CoverPages CRUD ---
def add_cover_page(cover_data: dict) -> str | None:
    """Adds a new cover page instance. Returns cover_page_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        new_cover_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat() + "Z"

        custom_style_config = cover_data.get('custom_style_config_json')
        if isinstance(custom_style_config, dict):
            custom_style_config = json.dumps(custom_style_config)

        sql = """
            INSERT INTO CoverPages (
                cover_page_id, cover_page_name, client_id, project_id, template_id,
                title, subtitle, author_text, institution_text, department_text,
                document_type_text, document_version, creation_date,
                logo_name, logo_data, custom_style_config_json,
                created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_cover_id,
            cover_data.get('cover_page_name'),
            cover_data.get('client_id'),
            cover_data.get('project_id'),
            cover_data.get('template_id'),
            cover_data.get('title'),
            cover_data.get('subtitle'),
            cover_data.get('author_text'),
            cover_data.get('institution_text'),
            cover_data.get('department_text'),
            cover_data.get('document_type_text'),
            cover_data.get('document_version'),
            cover_data.get('creation_date'),
            cover_data.get('logo_name'),
            cover_data.get('logo_data'),
            custom_style_config,
            now, now,
            cover_data.get('created_by_user_id')
        )
        cursor.execute(sql, params)
        conn.commit()
        return new_cover_id
    except sqlite3.Error as e:
        print(f"Database error in add_cover_page: {e}")
        return None
    finally:
        if conn: conn.close()

def get_cover_page_by_id(cover_page_id: str) -> dict | None:
    """Retrieves a cover page instance by its ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPages WHERE cover_page_id = ?", (cover_page_id,))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            if data.get('custom_style_config_json'):
                try:
                    data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse custom_style_config_json for cover page {cover_page_id}")
            return data
        return None
    except sqlite3.Error as e:
        print(f"Database error in get_cover_page_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_cover_pages_for_client(client_id: str) -> list[dict]:
    """Retrieves all cover pages for a specific client."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPages WHERE client_id = ? ORDER BY created_at DESC", (client_id,))
        rows = cursor.fetchall()
        cover_pages = []
        for row in rows:
            data = dict(row)
            # JSON parsing similar to get_cover_page_by_id if needed
            cover_pages.append(data)
        return cover_pages
    except sqlite3.Error as e:
        print(f"Database error in get_cover_pages_for_client: {e}")
        return []
    finally:
        if conn: conn.close()

def get_cover_pages_for_project(project_id: str) -> list[dict]:
    """Retrieves all cover pages for a specific project."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPages WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        rows = cursor.fetchall()
        cover_pages = []
        for row in rows:
            data = dict(row)
            # JSON parsing similar to get_cover_page_by_id if needed
            cover_pages.append(data)
        return cover_pages
    except sqlite3.Error as e:
        print(f"Database error in get_cover_pages_for_project: {e}")
        return []
    finally:
        if conn: conn.close()

def update_cover_page(cover_page_id: str, update_data: dict) -> bool:
    """Updates an existing cover page instance."""
    conn = None
    if not update_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        update_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

        if 'custom_style_config_json' in update_data and isinstance(update_data['custom_style_config_json'], dict):
            update_data['custom_style_config_json'] = json.dumps(update_data['custom_style_config_json'])

        set_clauses = [f"{key} = ?" for key in update_data.keys() if key != 'cover_page_id']
        params = [update_data[key] for key in update_data.keys() if key != 'cover_page_id']
        params.append(cover_page_id)

        sql = f"UPDATE CoverPages SET {', '.join(set_clauses)} WHERE cover_page_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in update_cover_page: {e}")
        return False
    finally:
        if conn: conn.close()

def delete_cover_page(cover_page_id: str) -> bool:
    """Deletes a cover page instance."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM CoverPages WHERE cover_page_id = ?", (cover_page_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error in delete_cover_page: {e}")
        return False
    finally:
        if conn: conn.close()

def get_cover_pages_for_user(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Retrieves cover pages created by a specific user, with pagination."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Querying by 'created_by_user_id' as per the CoverPages table schema
        sql = "SELECT * FROM CoverPages WHERE created_by_user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params = (user_id, limit, offset)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        # It's good practice to parse JSON fields here if any, similar to other get functions
        cover_pages = []
        for row in rows:
            data = dict(row)
            if data.get('custom_style_config_json'):
                try:
                    data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse custom_style_config_json for cover page {data['cover_page_id']}")
            cover_pages.append(data)
        return cover_pages
    except sqlite3.Error as e:
        print(f"Database error in get_cover_pages_for_user: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- Lookup Table GET Functions ---
def get_all_countries() -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Countries ORDER BY country_name")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_all_countries: {e}")
        return []
    finally:
        if conn: conn.close()

def get_country_by_id(country_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Countries WHERE country_id = ?", (country_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_country_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_country_by_name(country_name: str) -> dict | None:
    """Retrieves a country by its name. Returns a dict or None if not found."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Countries WHERE country_name = ?", (country_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_country_by_name: {e}")
        return None
    finally:
        if conn:
            conn.close()

def add_country(country_data: dict) -> int | None:
    """
    Adds a new country to the Countries table.
    Expects country_data to contain 'country_name'.
    Returns the country_id of the newly added or existing country.
    Returns None if an unexpected error occurs.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        country_name = country_data.get('country_name')
        if not country_name:
            print("Error: 'country_name' is required to add a country.")
            return None

        try:
            cursor.execute("INSERT INTO Countries (country_name) VALUES (?)", (country_name,))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Country name already exists, fetch its ID
            print(f"Country '{country_name}' already exists. Fetching its ID.")
            cursor.execute("SELECT country_id FROM Countries WHERE country_name = ?", (country_name,))
            row = cursor.fetchone()
            return row['country_id'] if row else None

    except sqlite3.Error as e:
        print(f"Database error in add_country: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_cities(country_id: int = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Cities"
        params = []
        if country_id is not None:
            sql += " WHERE country_id = ?"
            params.append(country_id)
        sql += " ORDER BY city_name"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_all_cities: {e}")
        return []
    finally:
        if conn: conn.close()

def add_city(city_data: dict) -> int | None:
    """
    Adds a new city to the Cities table.
    Expects city_data to contain 'country_id' and 'city_name'.
    Returns the city_id of the newly added or existing city.
    Returns None if an unexpected error occurs or if country_id or city_name is missing.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        country_id = city_data.get('country_id')
        city_name = city_data.get('city_name')

        if not country_id or not city_name:
            print("Error: 'country_id' and 'city_name' are required to add a city.")
            return None

        try:
            # Check if city already exists for this country to avoid IntegrityError for composite uniqueness if not explicitly handled by schema (though schema doesn't show composite unique constraint for city_name+country_id, it's good practice)
            # However, the current schema for Cities does not have a UNIQUE constraint on (country_id, city_name).
            # It only has city_id as PK and country_id as FK.
            # So, we will just insert. If a stricter uniqueness is needed, the table schema should be updated.
            cursor.execute("INSERT INTO Cities (country_id, city_name) VALUES (?, ?)", (country_id, city_name))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # This part would be relevant if there was a UNIQUE constraint on (country_id, city_name)
            # For now, this block might not be hit unless city_name itself becomes unique across all countries (which is not typical)
            print(f"IntegrityError likely means city '{city_name}' under country_id '{country_id}' already exists or other constraint failed.")
            # If it were unique and we wanted to return existing:
            # cursor.execute("SELECT city_id FROM Cities WHERE country_id = ? AND city_name = ?", (country_id, city_name))
            # row = cursor.fetchone()
            # return row['city_id'] if row else None
            return None # For now, any IntegrityError is treated as a failure to add as new.

    except sqlite3.Error as e:
        print(f"Database error in add_city: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_city_by_name_and_country_id(city_name: str, country_id: int) -> dict | None:
    """Retrieves a specific city by name for a given country_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Cities WHERE city_name = ? AND country_id = ?", (city_name, country_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_city_by_name_and_country_id: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_city_by_id(city_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Cities WHERE city_id = ?", (city_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_city_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_templates(template_type_filter: str = None, language_code_filter: str = None) -> list[dict]:
    """
    Retrieves all templates, optionally filtered by template_type and/or language_code.
    If template_type_filter is None, retrieves all templates regardless of type.
    If language_code_filter is None, retrieves for all languages.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Templates"
        params = []
        where_clauses = []

        if template_type_filter:
            where_clauses.append("template_type = ?")
            params.append(template_type_filter)
        if language_code_filter:
            where_clauses.append("language_code = ?")
            params.append(language_code_filter)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY template_name, language_code"
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_templates: {e}")
        return []
    finally:
        if conn: conn.close()

def get_distinct_languages_for_template_type(template_type: str) -> list[str]:
    """
    Retrieves a list of distinct language codes available for a given template type.
    """
    conn = None
    languages = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT language_code FROM Templates WHERE template_type = ? ORDER BY language_code ASC", (template_type,))
        rows = cursor.fetchall()
        languages = [row['language_code'] for row in rows if row['language_code']] # Ensure not None
    except sqlite3.Error as e:
        print(f"Database error in get_distinct_languages_for_template_type for type '{template_type}': {e}")
        # Return empty list on error
    finally:
        if conn:
            conn.close()
    return languages

def get_all_file_based_templates() -> list[dict]:
    """Retrieves all templates that have a base_file_name, suitable for document creation."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Selects templates that are likely file-based documents
        # Changed 'category' to 'category_id'.
        # If category_name is needed here, a JOIN with TemplateCategories would be required.
        sql = "SELECT template_id, template_name, language_code, base_file_name, description, category_id FROM Templates WHERE base_file_name IS NOT NULL AND base_file_name != '' ORDER BY template_name, language_code"
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_file_based_templates: {e}")
        return []
    finally:
        if conn: conn.close()

def get_templates_by_category_id(category_id: int) -> list[dict]:
    """Retrieves all templates for a given category_id."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Templates WHERE category_id = ? ORDER BY template_name, language_code", (category_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_templates_by_category_id: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- Email Body Template Specific Functions ---

def add_email_body_template(
    name: str,
    template_type: str, # e.g., 'email_body_html', 'email_body_text'
    language_code: str,
    base_file_name: str,
    description: str = None,
    email_subject_template: str = None,
    email_variables_info: str = None,
    created_by_user_id: str = None
) -> int | None:
    """
    Adds an email body template record to the Templates table, associating it
    with the "Modèles Email" category.
    Returns the template_id if successful, otherwise None.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get "Modèles Email" category ID
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", ("Modèles Email",))
        category_row = cursor.fetchone()
        if not category_row:
            print("Error: 'Modèles Email' category not found. Cannot add email body template.")
            return None
        email_category_id = category_row['category_id']

        template_data = {
            'template_name': name,
            'template_type': template_type, # Specific type like 'email_body_html'
            'description': description,
            'base_file_name': base_file_name,
            'language_code': language_code,
            'is_default_for_type_lang': False, # Email templates are usually not "default" in the same way as docs
            'category_id': email_category_id,
            'email_subject_template': email_subject_template,
            'email_variables_info': email_variables_info, # JSON string or text describing placeholder variables
            'created_by_user_id': created_by_user_id
            # 'raw_template_file_data': None, # Not storing file content directly in DB for these
            # 'version': '1.0' # Optional: could add versioning later
        }
        # Call the generic add_template function
        return add_template(template_data)
    except sqlite3.Error as e:
        print(f"Database error in add_email_body_template: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_email_body_templates(language_code: str, template_type_filter: str = None) -> list[dict]:
    """
    Retrieves email body templates for a specific language, optionally filtered by template_type.
    Fetches templates belonging to the "Modèles Email" category.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get "Modèles Email" category ID
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", ("Modèles Email",))
        category_row = cursor.fetchone()
        if not category_row:
            print("Error: 'Modèles Email' category not found. Cannot retrieve email body templates.")
            return []
        email_category_id = category_row['category_id']

        sql = """
            SELECT template_id, template_name, template_type, base_file_name,
                   language_code, description, email_subject_template, email_variables_info,
                   created_at, updated_at, created_by_user_id
            FROM Templates
            WHERE category_id = ? AND language_code = ?
        """
        params = [email_category_id, language_code]

        if template_type_filter:
            sql += " AND template_type = ?"
            params.append(template_type_filter)

        sql += " ORDER BY template_name"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_email_body_templates: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- Utility Document Template Specific Functions ---

def add_utility_document_template(
    name: str,
    language_code: str,
    base_file_name: str,
    description: str = None,
    # template_type is derived internally from base_file_name's extension
    created_by_user_id: str = None
) -> int | None:
    """
    Adds a utility document template record to the Templates table,
    associating it with the "Documents Utilitaires" category.
    template_type is derived from base_file_name's extension.
    Returns the template_id if successful, otherwise None.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get "Documents Utilitaires" category ID
        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", ("Documents Utilitaires",))
        category_row = cursor.fetchone()
        if not category_row:
            print("Error: 'Documents Utilitaires' category not found. Attempting to create.")
            # Attempt to create it if it's missing (should have been created by initialize_database)
            util_category_id = add_template_category("Documents Utilitaires", "Modèles de documents utilitaires généraux (ex: catalogues, listes de prix)")
            if not util_category_id:
                print("Critical Error: Could not create 'Documents Utilitaires' category.")
                return None
        else:
            util_category_id = category_row['category_id']

        # Determine template_type from file extension
        file_ext = os.path.splitext(base_file_name)[1].lower()
        # Example template_types: 'utility_document_pdf', 'utility_document_docx', 'utility_document_xlsx'
        template_type = f"utility_document_{file_ext.replace('.', '')}" if file_ext else "utility_document_generic"

        template_data = {
            'template_name': name,
            'template_type': template_type,
            'description': description,
            'base_file_name': base_file_name,
            'language_code': language_code,
            'is_default_for_type_lang': False,
            'category_id': util_category_id,
            'created_by_user_id': created_by_user_id
        }
        return add_template(template_data) # Uses the generic add_template function
    except sqlite3.Error as e:
        print(f"Database error in add_utility_document_template: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_utility_documents(language_code: str = None) -> list[dict]:
    """
    Retrieves utility documents, optionally filtered by language_code.
    Fetches templates belonging to the "Documents Utilitaires" category.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", ("Documents Utilitaires",))
        category_row = cursor.fetchone()
        if not category_row:
            print("Error: 'Documents Utilitaires' category not found.")
            return []
        util_category_id = category_row['category_id']

        # Build query based on whether language_code is provided
        sql = "SELECT * FROM Templates WHERE category_id = ?"
        params = [util_category_id]

        if language_code:
            sql += " AND language_code = ?"
            params.append(language_code)

        sql += " ORDER BY template_name"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    except sqlite3.Error as e:
        print(f"Database error in get_utility_documents: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- General Document File Operations (for Utility Docs, Email Templates etc.) ---

def save_general_document_file(
    source_file_path: str,
    document_type_subfolder: str, # e.g., "email_bodies", "utility_documents"
    language_code: str,
    target_base_name: str
) -> str | None:
    """
    Saves a document file to a structured path under the main templates directory.
    Path: CONFIG["templates_dir"] / document_type_subfolder / language_code / target_base_name
    Returns the full path of the saved file if successful, None otherwise.
    """
    if not all([source_file_path, document_type_subfolder, language_code, target_base_name]):
        print("Error: Missing one or more required parameters for saving general document file.")
        return None

    try:
        templates_base_dir = CONFIG.get("templates_dir", "templates") # Default if not in CONFIG
        # Ensure language_code is a string, as it's used in path construction
        if not isinstance(language_code, str):
            print(f"Warning: language_code '{language_code}' is not a string. Converting.")
            language_code = str(language_code)

        target_dir = os.path.join(templates_base_dir, document_type_subfolder, language_code)

        os.makedirs(target_dir, exist_ok=True)

        final_target_path = os.path.join(target_dir, target_base_name)

        shutil.copy(source_file_path, final_target_path)

        print(f"Document file saved successfully to: {final_target_path}")
        return final_target_path

    except FileNotFoundError:
        print(f"Error: Source file not found at {source_file_path}")
        return None
    except Exception as e:
        print(f"Error saving document file '{target_base_name}' to '{target_dir}': {str(e)}")
        return None

def delete_general_document_file(
    document_type_subfolder: str,
    language_code: str,
    base_file_name: str
) -> bool:
    """
    Deletes a general document file from the structured path.
    Returns True if successful or if file was already deleted, False on error.
    """
    if not all([document_type_subfolder, language_code, base_file_name]):
        print("Error: Missing one or more required parameters for deleting general document file.")
        return False

    try:
        templates_base_dir = CONFIG.get("templates_dir", "templates")
        if not isinstance(language_code, str):
            language_code = str(language_code)

        file_path = os.path.join(templates_base_dir, document_type_subfolder, language_code, base_file_name)

        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Document file deleted successfully: {file_path}")
            return True
        else:
            print(f"Document file not found (already deleted?): {file_path}")
            return True # Consider True as the desired state (not present) is achieved

    except Exception as e:
        print(f"Error deleting document file at '{file_path}': {str(e)}")
        return False

# --- Email Body Template File Operations (Kept for direct use by email template logic if needed) ---
# Note: save_uploaded_email_template_file can be refactored to use save_general_document_file
# save_uploaded_email_template_file can be potentially refactored to use save_general_document_file
# by passing "email_bodies" as document_type_subfolder.

def save_uploaded_email_template_file(
    uploaded_file_source_path: str,
    language_code: str,
    target_base_file_name: str
) -> str | None:
    """
    Saves an email template file to the 'email_bodies' subfolder.
    Returns the target_base_file_name if successful, None otherwise.
    """
    # This now acts as a specific wrapper for save_general_document_file
    full_path = save_general_document_file(
        source_file_path=uploaded_file_source_path,
        document_type_subfolder="email_bodies",
        language_code=language_code,
        target_base_name=target_base_file_name
    )
    return target_base_file_name if full_path else None


def get_email_body_template_content(template_id: int) -> str | None:
    """
    Retrieves the content of an email body template file.
    Handles .html, .txt, and .docx file types based on template_type.
    """
    template_info = get_template_by_id(template_id)
    if not template_info:
        print(f"Error: Template with ID {template_id} not found.")
        return None

    base_file_name = template_info.get('base_file_name')
    language_code = template_info.get('language_code')
    template_type = template_info.get('template_type') # e.g., 'email_body_html', 'email_body_word'

    if not all([base_file_name, language_code, template_type]):
        print(f"Error: Template metadata incomplete for ID {template_id} (missing file name, language, or type).")
        return None

    try:
        # Construct the path: CONFIG["templates_dir"]/email_bodies/<language_code>/<template_file_name>
        # Ensure CONFIG is accessible, might need to import app_config or pass templates_dir
        templates_base_dir = CONFIG.get("templates_dir", "templates") # Default if not in CONFIG
        file_path = os.path.join(templates_base_dir, "email_bodies", language_code, base_file_name)

        if not os.path.exists(file_path):
            print(f"Error: Template file not found at {file_path}")
            return None

        content = ""
        if template_type in ['email_body_html', 'email_body_text']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif template_type == 'email_body_word':
            if base_file_name.endswith('.docx'):
                doc = docx.Document(file_path)
                full_text = [para.text for para in doc.paragraphs]
                content = '\n'.join(full_text)
            else:
                print(f"Error: Template type is 'email_body_word' but file extension is not .docx for {base_file_name}")
                return None
        else:
            print(f"Error: Unsupported template_type '{template_type}' for content retrieval.")
            return None

        return content

    except FileNotFoundError:
        print(f"Error: Template file not found for ID {template_id} at path: {file_path}")
        return None
    except Exception as e:
        print(f"Error reading template content for ID {template_id}: {str(e)}")
        return None

def get_all_products_for_selection_filtered(language_code: str = None, name_pattern: str = None) -> list[dict]:
    """
    Retrieves active products for selection, optionally filtered by language_code
    and/or name_pattern (searches product_name and description).
    Orders by product_name.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql_params = []
        # Start with base selection of active products
        sql_where_clauses = ["is_active = TRUE"]

        if language_code:
            sql_where_clauses.append("language_code = ?")
            sql_params.append(language_code)

        if name_pattern:
            # The name_pattern should be passed with wildcards already, e.g., "%search_term%"
            sql_where_clauses.append("(product_name LIKE ? OR description LIKE ?)")
            sql_params.append(name_pattern)
            sql_params.append(name_pattern)

        sql = f"""
            SELECT product_id, product_name, description, base_unit_price, language_code
            FROM Products
            WHERE {' AND '.join(sql_where_clauses)}
            ORDER BY product_name
        """

        cursor.execute(sql, tuple(sql_params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_products_for_selection_filtered: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_all_tasks(active_only: bool = False, project_id_filter: str = None) -> list[dict]:
    """
    Retrieves all tasks, optionally filtering for active tasks only and/or by project_id.
    Active tasks are those not linked to a status marked as completion or archival.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT t.* FROM Tasks t"
        params = []
        where_clauses = []

        if active_only:
            sql += """
                LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id
            """
            where_clauses.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")

        if project_id_filter:
            where_clauses.append("t.project_id = ?")
            params.append(project_id_filter)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY t.created_at DESC" # Or some other meaningful order

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_tasks: {e}")
        return []
    finally:
        if conn: conn.close()

def get_tasks_by_assignee_id(assignee_team_member_id: int, active_only: bool = False) -> list[dict]:
    """
    Retrieves tasks assigned to a specific team member, optionally filtering for active tasks.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT t.* FROM Tasks t"
        params = []
        where_clauses = ["t.assignee_team_member_id = ?"]
        params.append(assignee_team_member_id)

        if active_only:
            sql += """
                LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id
            """
            where_clauses.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")

        if where_clauses: # Will always be true because of assignee_team_member_id
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY t.due_date ASC, t.priority DESC"

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_tasks_by_assignee_id: {e}")
        return []
    finally:
        if conn: conn.close()

def get_all_status_settings(status_type: str = None) -> list[dict]:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings" # Ensure icon_name is fetched
        params = []
        if status_type:
            sql += " WHERE status_type = ?"
            params.append(status_type)
        sql += " ORDER BY status_type, status_name"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"DB error in get_all_status_settings: {e}")
        return []
    finally:
        if conn: conn.close()

def get_status_setting_by_id(status_id: int) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings WHERE status_id = ?", (status_id,)) # Ensure icon_name is fetched
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_status_setting_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_status_setting_by_name(status_name: str, status_type: str) -> dict | None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings WHERE status_name = ? AND status_type = ?", (status_name, status_type)) # Ensure icon_name is fetched
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_status_setting_by_name: {e}")
        return None
    finally:
        if conn: conn.close()

# --- Document Context Data Function ---

def format_currency(amount: float | None, symbol: str = "€", precision: int = 2) -> str:
    """Formats a numerical amount into a currency string."""
    if amount is None:
        return ""
    return f"{symbol}{amount:,.{precision}f}"

def get_document_context_data(
    client_id: str,
    company_id: str, # For seller info
    target_language_code: str, # New parameter
    project_id: str = None,
    # product_ids: list[int] = None, # This might be ClientProjectProducts IDs if only specific items are part of the proforma
    linked_product_ids_for_doc: list[int] = None, # Use this for specific ClientProjectProducts line items
    additional_context: dict = None
) -> dict:
    """
    Gathers and structures data for document generation, with product language resolution.
    """
    context = {
        "doc": {}, "client": {}, "seller": {}, "project": {}, "products": [],
        "additional": additional_context if isinstance(additional_context, dict) else {}
    }
    now_dt = datetime.now()
    context["doc"]["current_date"] = now_dt.strftime("%Y-%m-%d")
    context["doc"]["current_year"] = str(now_dt.year)
    # Default currency, can be overridden by additional_context or seller settings later
    context["doc"]["currency_symbol"] = context["additional"].get("currency_symbol", "€")
    context["doc"]["vat_rate_percentage"] = context["additional"].get("vat_rate_percentage", 20.0) # Default VAT rate
    context["doc"]["discount_rate_percentage"] = context["additional"].get("discount_rate_percentage", 0.0) # Default discount rate

    # Document specific IDs and terms - to be primarily filled from additional_context
    context["doc"]["proforma_id"] = context["additional"].get("proforma_id", "PRO-" + now_dt.strftime("%Y%m%d-%H%M"))
    context["doc"]["invoice_id"] = context["additional"].get("invoice_id", "INV-" + now_dt.strftime("%Y%m%d-%H%M"))
    context["doc"]["packing_list_id"] = context["additional"].get("packing_list_id", "PL-" + now_dt.strftime("%Y%m%d-%H%M"))
    context["doc"]["contract_id"] = context["additional"].get("contract_id", "CON-" + now_dt.strftime("%Y%m%d-%H%M"))
    context["doc"]["warranty_certificate_id"] = context["additional"].get("warranty_id", "WAR-" + now_dt.strftime("%Y%m%d-%H%M"))
    context["doc"]["payment_terms"] = context["additional"].get("payment_terms", "Net 30 Days")
    context["doc"]["delivery_terms"] = context["additional"].get("delivery_terms", "FOB Port of Loading") # Incoterms related
    context["doc"]["incoterms"] = context["additional"].get("incoterms", "FOB")
    context["doc"]["named_place_of_delivery"] = context["additional"].get("named_place_of_delivery", "Port of Loading")
    context["doc"]["port_of_loading"] = context["additional"].get("port_of_loading", "N/A")
    context["doc"]["port_of_discharge"] = context["additional"].get("port_of_discharge", "N/A")
    context["doc"]["final_destination_country"] = context["additional"].get("final_destination_country", "N/A")
    context["doc"]["vessel_flight_no"] = context["additional"].get("vessel_flight_no", "N/A")
    context["doc"]["estimated_shipment_date"] = context["additional"].get("estimated_shipment_date", "To be confirmed")
    context["doc"]["packing_type_description"] = context["additional"].get("packing_type_description", "Standard Export Packing")
    context["doc"]["warranty_period_months"] = context["additional"].get("warranty_period_months", "12")
    context["doc"]["warranty_start_condition"] = context["additional"].get("warranty_start_condition", "date of delivery")
    context["doc"]["inspection_clause_detail"] = context["additional"].get("inspection_clause_detail", "Inspection by Seller before shipment.")
    context["doc"]["inspection_agency_name"] = context["additional"].get("inspection_agency_name", "N/A")
    context["doc"]["jurisdiction_country_name"] = context["additional"].get("jurisdiction_country_name", "Seller's Country")
    context["doc"]["arbitration_location"] = context["additional"].get("arbitration_location", "Seller's City")
    context["doc"]["arbitration_rules_body"] = context["additional"].get("arbitration_rules_body", "International Chamber of Commerce (ICC)")
    context["doc"]["notify_party_name"] = context["additional"].get("notify_party_name", context["client"].get("company_name", "Same as Consignee"))
    context["doc"]["notify_party_address"] = context["additional"].get("notify_party_address", context["client"].get("address", "N/A"))


    # --- Fetch Seller (Our User's Company) Information ---
    seller_company_data = get_company_by_id(company_id)
    if seller_company_data:
        context["seller"]["name"] = seller_company_data.get('company_name', "N/A")
        context["seller"]["company_name"] = seller_company_data.get('company_name', "N/A")
        raw_address = seller_company_data.get('address', "N/A")
        context["seller"]["address"] = raw_address
        context["seller"]["address_line1"] = raw_address # Simplistic, assumes address is single line
        context["seller"]["city_zip_country"] = "N/A (Structure adr. manquante)" # Placeholder
        # TODO: Parse raw_address or add structured fields (city, zip, country) to Companies table
        context["seller"]["full_address"] = raw_address # For templates that use a single full address block

        context["seller"]["payment_info"] = seller_company_data.get('payment_info')
        context["seller"]["other_info"] = seller_company_data.get('other_info')

        logo_path_relative = seller_company_data.get('logo_path')
        context["seller"]["logo_path_relative"] = logo_path_relative
        if logo_path_relative:
            abs_logo_path = os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, logo_path_relative)
            if os.path.exists(abs_logo_path):
                 context["seller"]["logo_path_absolute"] = abs_logo_path
                 context["seller"]["company_logo_path"] = f"file:///{abs_logo_path.replace(os.sep, '/')}"
            else:
                 context["seller"]["logo_path_absolute"] = None
                 context["seller"]["company_logo_path"] = None # Or a default/placeholder logo URL
                 print(f"Warning: Seller logo file not found at {abs_logo_path}")
        else:
            context["seller"]["logo_path_absolute"] = None
            context["seller"]["company_logo_path"] = None

        # More specific seller details (assuming they might be in 'other_info' or need new schema fields)
        # For now, providing placeholders or deriving from existing if possible.
        context["seller"]["phone"] = context["additional"].get("seller_phone", "N/A Seller Phone")
        context["seller"]["email"] = context["additional"].get("seller_email", "N/A Seller Email")
        context["seller"]["vat_id"] = context["additional"].get("seller_vat_id", "N/A Seller VAT ID")
        context["seller"]["registration_number"] = context["additional"].get("seller_registration_number", "N/A Seller Reg No.")

        context["seller"]["bank_details_raw"] = seller_company_data.get('payment_info', "N/A")
        context["seller"]["bank_name"] = context["additional"].get("seller_bank_name", "N/A Bank")
        context["seller"]["bank_account_number"] = context["additional"].get("seller_bank_account_number", "N/A Account No.")
        context["seller"]["bank_swift_bic"] = context["additional"].get("seller_bank_swift_bic", "N/A SWIFT/BIC")
        context["seller"]["bank_address"] = context["additional"].get("seller_bank_address", "N/A Bank Address")
        context["seller"]["bank_account_holder_name"] = context["seller"]["company_name"] # Default to company name

        context["seller"]["footer_company_name"] = context["seller"]["company_name"]
        context["seller"]["footer_contact_info"] = f"{context['seller']['phone']} | {context['seller']['email']}"
        context["seller"]["footer_additional_info"] = seller_company_data.get('other_info', "")

    # --- Fetch Seller Personnel (from CompanyPersonnel) ---
    # Using a general personnel dictionary within seller context
    context["seller"]["personnel"] = {}
    seller_personnel_list = get_personnel_for_company(company_id) # Get all personnel
    if seller_personnel_list:
        # Example: find first person with role 'seller' or default to first person
        main_seller_contact = next((p for p in seller_personnel_list if p.get('role') == 'seller'), seller_personnel_list[0])
        context["seller"]["personnel"]["representative_name"] = main_seller_contact.get('name')
        context["seller"]["personnel"]["representative_title"] = main_seller_contact.get('role') # Or a more specific title if available

        # For specific roles mentioned in templates
        context["seller"]["personnel"]["sales_person_name"] = next((p.get('name') for p in seller_personnel_list if p.get('role') == 'seller'), "N/A")
        context["seller"]["personnel"]["technical_manager_name"] = next((p.get('name') for p in seller_personnel_list if p.get('role') == 'technical_manager'), "N/A")
        # Generic authorized signatory for some docs (can be overridden by additional_context)
        context["seller"]["personnel"]["authorized_signature_name"] = context["seller"]["personnel"]["sales_person_name"]
        context["seller"]["personnel"]["authorized_signature_title"] = next((p.get('role') for p in seller_personnel_list if p.get('name') == context["seller"]["personnel"]["authorized_signature_name"]), "N/A")

    else: # No personnel found
        context["seller"]["personnel"]["representative_name"] = "N/A"
        context["seller"]["personnel"]["representative_title"] = "N/A"
        context["seller"]["personnel"]["sales_person_name"] = "N/A"
        context["seller"]["personnel"]["technical_manager_name"] = "N/A"
        context["seller"]["personnel"]["authorized_signature_name"] = "N/A"
        context["seller"]["personnel"]["authorized_signature_title"] = "N/A"

    # --- Fetch Client Information (The Buyer/Consignee) ---
    # This is 'client_id' passed to the function
    client_data = get_client_by_id(client_id)
    if client_data:
        context["client"]["id"] = client_data.get('client_id')
        # Distinguish between contact person name and company name
        context["client"]["contact_person_name"] = client_data.get('client_name') # client_name from Clients table is often a person
        context["client"]["company_name"] = client_data.get('company_name', client_data.get('client_name')) # Fallback to client_name if company_name is empty

        context["client"]["project_identifier"] = client_data.get('project_identifier')
        context["client"]["primary_need"] = client_data.get('primary_need_description')
        context["client"]["notes"] = client_data.get('notes')
        context["client"]["price_formatted"] = format_currency(client_data.get('price'), context["doc"]["currency_symbol"])
        context["client"]["raw_price"] = client_data.get('price')

        client_country_name, client_city_name = "N/A", "N/A"
        if client_data.get('country_id'):
            country = get_country_by_id(client_data['country_id'])
            if country: client_country_name = country.get('country_name', "N/A")
        if client_data.get('city_id'):
            city = get_city_by_id(client_data['city_id'])
            if city: client_city_name = city.get('city_name', "N/A")

        context["client"]["country_name"] = client_country_name
        context["client"]["city_name"] = client_city_name
        # Construct full_address (assuming 'address' field in Clients table is missing, using city/country)
        # This would be improved if Clients table had a full 'address' field or structured address.
        address_parts = [part for part in [client_city_name, client_country_name] if part != "N/A"]
        context["client"]["address"] = ", ".join(address_parts) if address_parts else "N/A (Adresse manquante)"
        context["client"]["city_zip_country"] = context["client"]["address"] # Simplified

        # Client contact details (primary contact from Contacts table)
        client_contacts = get_contacts_for_client(client_id)
        primary_client_contact = next((c for c in client_contacts if c.get('is_primary_for_client')), None)
        if not primary_client_contact and client_contacts: primary_client_contact = client_contacts[0]

        if primary_client_contact:
            # Override client.contact_person_name if a more specific primary contact exists
            context["client"]["contact_person_name"] = primary_client_contact.get('name', client_data.get('client_name')) # Fallback to client_name if primary contact name is empty
            context["client"]["contact_email"] = primary_client_contact.get('email', "N/A")
            context["client"]["contact_phone"] = primary_client_contact.get('phone', "N/A")
            context["client"]["contact_position"] = primary_client_contact.get('position', "N/A")
        else:
            context["client"]["contact_email"] = "N/A"
            context["client"]["contact_phone"] = "N/A"
            context["client"]["contact_position"] = "N/A"

        context["client"]["vat_id"] = context["additional"].get("client_vat_id", "N/A Client VAT ID")
        context["client"]["registration_number"] = context["additional"].get("client_registration_number", "N/A Client Reg No.")
        context["client"]["full_address"] = context["client"]["address"] # For templates that use a single full address block


        # Buyer representative details (often the primary contact)
        context["client"]["representative_name"] = context["client"].get("contact_person_name", client_data.get('client_name'))
        context["client"]["representative_title"] = context["client"]["contact_position"]

    # --- Fetch Project Information (if project_id is provided) ---
    if project_id:
        project_data = get_project_by_id(project_id)
        if project_data:
            context["project"]["name"] = project_data.get('project_name')
            context["project"]["id"] = project_data.get('project_id')
            context["project"]["description"] = project_data.get('description')
            context["project"]["start_date"] = project_data.get('start_date')
            context["project"]["deadline_date"] = project_data.get('deadline_date')
            context["project"]["budget_formatted"] = format_currency(project_data.get('budget'), context["doc"]["currency_symbol"])
            context["project"]["raw_budget"] = project_data.get('budget')
            context["project"]["progress_percentage"] = project_data.get('progress_percentage')
            context["project"]["manager_id"] = project_data.get('manager_team_member_id') # Needs fetch for name

            status_id = project_data.get('status_id')
            status_info = get_status_setting_by_id(status_id) if status_id else None
            context["project"]["status_name"] = status_info.get('status_name') if status_info else "N/A"
    else: # No project_id, provide defaults for project fields
        context["project"]["name"] = context["additional"].get("project_name", client_data.get('project_identifier', "N/A")) # Fallback to project_identifier
        context["project"]["description"] = context["additional"].get("project_description", client_data.get('primary_need_description', ""))


    # --- Fetch Products and Generate HTML Rows ---
    fetched_products_data = []
    # ... (rest of the initial context["doc"] setup as before) ...
    now_dt = datetime.now()
    context["doc"]["current_date"] = now_dt.strftime("%Y-%m-%d")
    context["doc"]["current_year"] = str(now_dt.year)
    context["doc"]["currency_symbol"] = context["additional"].get("currency_symbol", "€")
    context["doc"]["vat_rate_percentage"] = context["additional"].get("vat_rate_percentage", 20.0)
    context["doc"]["discount_rate_percentage"] = context["additional"].get("discount_rate_percentage", 0.0)
    # ... (other context["doc"] fields) ...

    # --- Fetch Seller (Our User's Company) Information ---
    # ... (seller info fetching as before) ...
    seller_company_data = get_company_by_id(company_id)
    if seller_company_data:
        context["seller"]["name"] = seller_company_data.get('company_name', "N/A")
        # ... (populate rest of seller fields) ...
        # Simplified for brevity
        context["seller"]["company_logo_path"] = f"file:///{os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, seller_company_data.get('logo_path',''))}" if seller_company_data.get('logo_path') else ""


    # --- Fetch Client Information (The Buyer/Consignee) ---
    # ... (client info fetching as before) ...
    client_data = get_client_by_id(client_id)
    if client_data:
        context["client"]["id"] = client_data.get('client_id')
        # ... (populate rest of client fields) ...


    # --- Fetch Project Information (if project_id is provided) ---
    # ... (project info fetching as before) ...
    if project_id:
        project_data = get_project_by_id(project_id)
        if project_data:
            context["project"]["name"] = project_data.get('project_name')
            # ... (populate rest of project fields) ...
    else:
        context["project"]["name"] = client_data.get('project_identifier', "N/A") if client_data else "N/A"


    # --- Enhanced Product Fetching and Language Resolution ---
    linked_products_query_result = []
    if linked_product_ids_for_doc: # Fetch specific linked products if IDs are provided
        conn_temp = get_db_connection()
        cursor_temp = conn_temp.cursor()
        for link_id in linked_product_ids_for_doc:
            cursor_temp.execute("""
                SELECT cpp.*, p.product_name AS original_product_name, p.description AS original_description,
                       p.language_code AS original_language_code, p.weight, p.dimensions,
                       p.base_unit_price, p.unit_of_measure
                FROM ClientProjectProducts cpp
                JOIN Products p ON cpp.product_id = p.product_id
                WHERE cpp.client_project_product_id = ?
            """, (link_id,))
            row = cursor_temp.fetchone()
            if row:
                linked_products_query_result.append(dict(row))
        conn_temp.close()
    else: # Fetch all for client/project
        linked_products_query_result = get_products_for_client_or_project(client_id, project_id)
        # get_products_for_client_or_project already joins with Products and fetches its columns.
        # We need to ensure it fetches original_language_code, original_product_name, original_description
        # and the new weight/dimensions. The alias for Products table is 'p'.
        # The previous subtask updated get_products_for_client_or_project to include p.weight, p.dimensions.
        # It also implicitly included p.language_code, p.product_name, p.description.

    products_table_html_rows = ""
    subtotal_amount_calculated = 0.0
    item_counter = 0

    for linked_prod_data in linked_products_query_result:
        item_counter += 1
        original_product_id = linked_prod_data['product_id'] # This is the ID of the product in its original language
        original_lang_code = linked_prod_data.get('language_code') # Language of the product in Products table for this link

        product_name_for_doc = linked_prod_data.get('product_name') # Default to original
        product_description_for_doc = linked_prod_data.get('product_description') # Default to original
        is_language_match = (original_lang_code == target_language_code)

        if not is_language_match:
            equivalents = get_equivalent_products(original_product_id)
            found_equivalent_in_target_lang = False
            for eq_prod in equivalents:
                if eq_prod.get('language_code') == target_language_code:
                    product_name_for_doc = eq_prod.get('product_name')
                    product_description_for_doc = eq_prod.get('description')
                    is_language_match = True # Now it's a match because we found an equivalent
                    found_equivalent_in_target_lang = True
                    break
            if not found_equivalent_in_target_lang:
                # No equivalent found in target language, is_language_match remains False.
                # product_name_for_doc and product_description_for_doc retain original language values.
                print(f"Warning: No equivalent found for product ID {original_product_id} in target language {target_language_code}.")


        quantity = linked_prod_data.get('quantity', 1)
        unit_price_override = linked_prod_data.get('unit_price_override')
        base_unit_price = linked_prod_data.get('base_unit_price')

        effective_unit_price = unit_price_override if unit_price_override is not None else base_unit_price
        try:
            unit_price_float = float(effective_unit_price) if effective_unit_price is not None else 0.0
        except ValueError:
            unit_price_float = 0.0

        total_price = quantity * unit_price_float
        subtotal_amount_calculated += total_price

        products_table_html_rows += f"""<tr>
            <td>{item_counter}</td>
            <td>{product_name_for_doc if product_name_for_doc else 'N/A'}</td>
            <td>{quantity}</td>
            <td>{format_currency(unit_price_float, context["doc"]["currency_symbol"])}</td>
            <td>{format_currency(total_price, context["doc"]["currency_symbol"])}</td>
        </tr>"""

        context["products"].append({
            "id": original_product_id,
            "name": product_name_for_doc,
            "description": product_description_for_doc,
            "quantity": quantity,
            "unit_price_formatted": format_currency(unit_price_float, context["doc"]["currency_symbol"]),
            "total_price_formatted": format_currency(total_price, context["doc"]["currency_symbol"]),
            "raw_unit_price": unit_price_float,
            "raw_total_price": total_price,
            "unit_of_measure": linked_prod_data.get('unit_of_measure'),
            "weight": linked_prod_data.get('weight'), # From joined Products table
            "dimensions": linked_prod_data.get('dimensions'), # From joined Products table
            "is_language_match": is_language_match
        })

    context["doc"]["products_table_rows"] = products_table_html_rows
    context["doc"]["subtotal_amount"] = format_currency(subtotal_amount_calculated, context["doc"]["currency_symbol"])
    # ... (rest of currency calculations and context population as before) ...

    discount_rate = context["doc"]["discount_rate_percentage"] / 100.0
    discount_amount_calculated = subtotal_amount_calculated * discount_rate
    context["doc"]["discount_amount"] = format_currency(discount_amount_calculated, context["doc"]["currency_symbol"])

    amount_after_discount = subtotal_amount_calculated - discount_amount_calculated

    vat_rate = context["doc"]["vat_rate_percentage"] / 100.0
    vat_amount_calculated = amount_after_discount * vat_rate
    context["doc"]["vat_amount"] = format_currency(vat_amount_calculated, context["doc"]["currency_symbol"])

    grand_total_amount_calculated = amount_after_discount + vat_amount_calculated
    context["doc"]["grand_total_amount"] = format_currency(grand_total_amount_calculated, context["doc"]["currency_symbol"])
    context["doc"]["grand_total_amount_words"] = "N/A (Number to words not implemented)" # Placeholder

    # ... (packing list and warranty specific placeholders as before) ...
    # ... (common template placeholder mappings as before) ...

    discount_rate = context["doc"]["discount_rate_percentage"] / 100.0
    discount_amount_calculated = subtotal_amount_calculated * discount_rate
    context["doc"]["discount_amount"] = format_currency(discount_amount_calculated, context["doc"]["currency_symbol"])

    amount_after_discount = subtotal_amount_calculated - discount_amount_calculated

    vat_rate = context["doc"]["vat_rate_percentage"] / 100.0
    vat_amount_calculated = amount_after_discount * vat_rate
    context["doc"]["vat_amount"] = format_currency(vat_amount_calculated, context["doc"]["currency_symbol"])

    grand_total_amount_calculated = amount_after_discount + vat_amount_calculated
    context["doc"]["grand_total_amount"] = format_currency(grand_total_amount_calculated, context["doc"]["currency_symbol"])
    # For {{GRAND_TOTAL_AMOUNT_WORDS}}, this would require a number-to-words library, skipping for now.
    context["doc"]["grand_total_amount_words"] = "N/A (Number to words not implemented)"


    # Packing List specific totals (example, needs real data if fields differ)
    context["doc"]["total_packages"] = context["additional"].get("total_packages", str(len(fetched_products_data))) # Simplistic
    context["doc"]["total_net_weight"] = context["additional"].get("total_net_weight", "N/A kg")
    context["doc"]["total_gross_weight"] = context["additional"].get("total_gross_weight", "N/A kg")
    context["doc"]["total_volume_cbm"] = context["additional"].get("total_volume_cbm", "N/A CBM")
    context["doc"]["packing_list_items"] = context["additional"].get("packing_list_items_html", "<tr><td colspan='7'>Packing details not specified.</td></tr>")


    # Warranty specific placeholders (mostly from additional_context or defaults)
    context["doc"]["product_name_warranty"] = context["additional"].get("product_name_warranty", "N/A")
    context["doc"]["product_model_warranty"] = context["additional"].get("product_model_warranty", "N/A")
    context["doc"]["product_serial_numbers_warranty"] = context["additional"].get("product_serial_numbers_warranty", "N/A")
    context["doc"]["purchase_supply_date"] = context["additional"].get("purchase_supply_date", context["doc"]["current_date"])
    context["doc"]["original_invoice_id_warranty"] = context["additional"].get("original_invoice_id_warranty", context["doc"]["invoice_id"])
    context["doc"]["warranty_period_text"] = context["additional"].get("warranty_period_text", f"{context['doc']['warranty_period_months']} months")
    context["doc"]["warranty_start_point_text"] = context["additional"].get("warranty_start_point_text", "date of purchase")
    context["doc"]["warranty_coverage_details"] = context["additional"].get("warranty_coverage_details", "Standard parts and labor.")
    context["doc"]["other_exclusions_list"] = context["additional"].get("other_exclusions_list", "<li>Damage due to natural disasters.</li>")
    context["doc"]["warranty_claim_contact_info"] = context["additional"].get("warranty_claim_contact_info", context['seller'].get('email', 'N/A'))
    context["doc"]["warranty_claim_procedure_detail"] = context["additional"].get("warranty_claim_procedure_detail", "Contact us with proof of purchase.")

    # --- Map to common template placeholder patterns (already populated above or directly in context["doc"]) ---
    context["buyer_name"] = context["client"].get("company_name", context["client"].get("contact_person_name", "N/A"))
    context["buyer_address"] = context["client"].get("address", "N/A")
    context["buyer_city_zip_country"] = context["client"].get("city_zip_country", "N/A")
    context["buyer_phone"] = context["client"].get("contact_phone", "N/A")
    context["buyer_email"] = context["client"].get("contact_email", "N/A")
    context["buyer_vat_number"] = context["client"].get("vat_id", "N/A")
    context["buyer_company_name"] = context["client"].get("company_name", "N/A")
    context["buyer_company_address"] = context["client"].get("address", "N/A") # Assuming same as client address
    context["buyer_company_registration_number"] = context["client"].get("registration_number", "N/A")
    context["buyer_representative_name"] = context["client"].get("representative_name", "N/A")
    context["buyer_representative_title"] = context["client"].get("representative_title", "N/A")

    context["seller_company_logo_path"] = context["seller"].get("company_logo_path", "") # Default to empty if None
    context["seller_company_name"] = context["seller"].get("name", "N/A")
    context["seller_company_address"] = context["seller"].get("address", "N/A")
    context["seller_address_line1"] = context["seller"].get("address_line1", context["seller"].get("address", "N/A")) # Use specific if available
    context["seller_city_zip_country"] = context["seller"].get("city_zip_country", "N/A")
    context["seller_company_phone"] = context["seller"].get("phone", "N/A")
    context["seller_company_email"] = context["seller"].get("email", "N/A")
    context["seller_vat_id"] = context["seller"].get("vat_id", "N/A")
    context["seller_company_registration_number"] = context["seller"].get("registration_number", "N/A")
    context["seller_representative_name"] = context["seller"].get("personnel", {}).get("representative_name", "N/A")
    context["seller_representative_title"] = context["seller"].get("personnel", {}).get("representative_title", "N/A")
    context["seller_bank_name"] = context["seller"].get("bank_name", "N/A")
    context["seller_bank_address"] = context["seller"].get("bank_address", "N/A")
    context["seller_bank_iban"] = context["seller"].get("bank_iban", "N/A")
    context["seller_bank_swift_bic"] = context["seller"].get("bank_swift_bic", "N/A")
    context["seller_bank_account_holder_name"] = context["seller"].get("bank_account_holder_name", context["seller"].get("name", "N/A"))
    context["seller_full_address"] = context["seller"].get("address", "N/A")


    context["project_description"] = context["project"].get("description", "")
    context["project_id"] = context["project"].get("id", client_data.get("project_identifier", "N/A")) # Ensure PROJECT_ID is available

    # Packing List specific mappings
    context["company_logo_path_for_stamp"] = context["seller_company_logo_path"]
    context["exporter_company_name"] = context["seller_company_name"]
    context["exporter_address"] = context["seller_company_address"]
    context["exporter_contact_person"] = context["seller_representative_name"]
    context["exporter_phone"] = context["seller_company_phone"]
    context["exporter_email"] = context["seller_company_email"]

    context["consignee_name"] = context["buyer_name"]
    context["consignee_address"] = context["buyer_address"]
    context["consignee_contact_person"] = context["buyer_representative_name"]
    context["consignee_phone"] = context["buyer_phone"]
    context["consignee_email"] = context["buyer_email"]

    context["primary_contact_name"] = context["client"].get("contact_person_name", "N/A") # For general use
    context["primary_contact_email"] = context["client"].get("contact_email", "N/A")
    context["primary_contact_position"] = context["client"].get("contact_position", "N/A")


    context["authorized_signature_name"] = context["seller"].get("personnel",{}).get("authorized_signature_name", "N/A")
    context["authorized_signature_title"] = context["seller"].get("personnel",{}).get("authorized_signature_title", "N/A")

    # Warranty Document specific mappings
    context["beneficiary_name"] = context["buyer_name"]
    context["beneficiary_address"] = context["buyer_address"]
    context["beneficiary_contact_person"] = context["buyer_representative_name"]
    context["beneficiary_phone"] = context["buyer_phone"]
    context["beneficiary_email"] = context["buyer_email"]

    context["warrantor_company_name"] = context["seller_company_name"]
    context["warrantor_address"] = context["seller_company_address"]
    context["warrantor_contact_person"] = context["seller"].get("personnel",{}).get("technical_manager_name", context["seller_representative_name"])
    context["warrantor_phone"] = context["seller_company_phone"]
    context["warrantor_email"] = context["seller_company_email"]

    # Cover Page specific mappings
    context["company_logo_path"] = context["seller_company_logo_path"] # Already mapped
    context["client_name"] = context["buyer_name"] # Already mapped for consistency
    context["client_company_name"] = context["client"].get("company_name", "")
    context["client_full_address"] = context["client"].get("full_address", "N/A")
    context["project_name"] = context["project"].get("name", "N/A")
    context["author_name"] = context["seller"].get("personnel",{}).get("sales_person_name", context["seller_company_name"])
    context["date"] = context["doc"]["current_date"] # General date
    context["current_year"] = context["doc"]["current_year"]


    # Fill from additional_context, providing defaults for some common ones
    # These are already in context["doc"] or context["project"] etc.
    # No need to re-assign unless overriding logic is intended.
    # context["document_title"] = context["additional"].get("document_title", "Document")
    # ... and so on

    return context


if __name__ == '__main__':
    initialize_database()
    print(f"Database '{DATABASE_NAME}' initialized successfully with all tables, including Products, ClientProjectProducts, and Contacts PK/FK updates.")

    # Example Usage (Illustrative - uncomment and adapt to test)

    # --- Test Companies and CompanyPersonnel ---
    print("\n--- Testing Companies and CompanyPersonnel ---")
    comp1_id = add_company({'company_name': 'Default Corp', 'address': '123 Main St', 'is_default': True})
    if comp1_id:
        print(f"Added company 'Default Corp' with ID: {comp1_id}")
        set_default_company(comp1_id) # Ensure it's default
        ret_comp1 = get_company_by_id(comp1_id)
        print(f"Retrieved company: {ret_comp1['company_name']}, Default: {ret_comp1['is_default']}")

        pers1_id = add_company_personnel({'company_id': comp1_id, 'name': 'John Doe', 'role': 'seller'})
        if pers1_id:
            print(f"Added personnel 'John Doe' with ID: {pers1_id} to {comp1_id}")

        pers2_id = add_company_personnel({'company_id': comp1_id, 'name': 'Jane Smith', 'role': 'technical_manager'})
        if pers2_id:
            print(f"Added personnel 'Jane Smith' with ID: {pers2_id} to {comp1_id}")

        all_personnel = get_personnel_for_company(comp1_id)
        print(f"All personnel for Default Corp: {len(all_personnel)}")
        sellers = get_personnel_for_company(comp1_id, role='seller')
        print(f"Sellers for Default Corp: {len(sellers)}")

        if pers1_id:
            update_company_personnel(pers1_id, {'name': 'Johnathan Doe', 'role': 'senior_seller'})
            updated_pers1 = get_personnel_for_company(comp1_id, role='senior_seller') # Check if update worked
            if updated_pers1: print(f"Updated personnel: {updated_pers1[0]['name']}")

    comp2_id = add_company({'company_name': 'Second Ent.', 'address': '456 Side Ave'})
    if comp2_id:
        print(f"Added company 'Second Ent.' with ID: {comp2_id}")
        set_default_company(comp1_id) # Try setting first one as default again
        ret_comp2 = get_company_by_id(comp2_id)
        if ret_comp2: print(f"Company 'Second Ent.' is_default: {ret_comp2['is_default']}")
        ret_comp1_after = get_company_by_id(comp1_id)
        if ret_comp1_after: print(f"Company 'Default Corp' is_default after re-set: {ret_comp1_after['is_default']}")


    all_companies = get_all_companies()
    print(f"Total companies: {len(all_companies)}")

    # Cleanup (optional, for testing)
    # if pers1_id: delete_company_personnel(pers1_id)
    # if pers2_id: delete_company_personnel(pers2_id)
    # if comp1_id: delete_company(comp1_id) # This would cascade delete personnel
    # if comp2_id: delete_company(comp2_id)


    # --- Pre-populate base data for FK constraints (Countries, Cities, StatusSettings) ---
    # (This setup code is largely the same as the previous step, ensuring essential lookup data)
    conn_main_setup = get_db_connection()
    try:
        cursor_main_setup = conn_main_setup.cursor()
        # ... (Country, City, StatusSettings insertions as before) ...
        cursor_main_setup.execute("INSERT OR IGNORE INTO Countries (country_id, country_name) VALUES (1, 'Default Country')")
        cursor_main_setup.execute("INSERT OR IGNORE INTO Cities (city_id, country_id, city_name) VALUES (1, 1, 'Default City')")
        cursor_main_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_id, status_name, status_type) VALUES (1, 'Active Client', 'Client')")
        cursor_main_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_id, status_name, status_type, is_completion_status) VALUES (10, 'Project Planning', 'Project', FALSE)")
        cursor_main_setup.execute("INSERT OR IGNORE INTO StatusSettings (status_id, status_name, status_type, is_completion_status) VALUES (22, 'Task Done', 'Task', TRUE)")

        conn_main_setup.commit()
        print("Default data for Countries, Cities, StatusSettings ensured for testing.")
    except sqlite3.Error as e_setup:
        print(f"Error ensuring default lookup data in __main__: {e_setup}")
    finally:
        if conn_main_setup:
            conn_main_setup.close()

    # --- Setup common entities for tests: User, Client, Project, Template ---
    test_user_id = add_user({'username': 'docuser', 'password': 'password', 'full_name': 'Doc User', 'email': 'doc@example.com', 'role': 'editor'})
    if test_user_id: print(f"Created user 'docuser' (ID: {test_user_id}) for document tests.")

    test_client_id_for_docs = None
    existing_doc_clients = get_all_clients({'client_name': 'Doc Test Client'})
    if not existing_doc_clients:
        test_client_id_for_docs = add_client({'client_name': 'Doc Test Client', 'created_by_user_id': test_user_id})
        if test_client_id_for_docs: print(f"Added 'Doc Test Client' (ID: {test_client_id_for_docs})")
    else:
        test_client_id_for_docs = existing_doc_clients[0]['client_id']
        print(f"Using existing 'Doc Test Client' (ID: {test_client_id_for_docs})")
    
    test_project_id_for_docs = None
    if test_client_id_for_docs and test_user_id:
        client_projects_for_docs = get_projects_by_client_id(test_client_id_for_docs)
        if not client_projects_for_docs:
            test_project_id_for_docs = add_project({
                'client_id': test_client_id_for_docs, 
                'project_name': 'Doc Test Project', 
                'manager_team_member_id': test_user_id, 
                'status_id': 10
            })
            if test_project_id_for_docs: print(f"Added 'Doc Test Project' (ID: {test_project_id_for_docs})")
        else:
            test_project_id_for_docs = client_projects_for_docs[0]['project_id']
            print(f"Using existing 'Doc Test Project' (ID: {test_project_id_for_docs})")

    test_template_id = None
    # Assuming a template might be needed for source_template_id
    templates = get_templates_by_type('general_document') # or some relevant type
    if not templates:
        test_template_id = add_template({
            'template_name': 'General Document Template for Docs', 
            'template_type': 'general_document', 
            'language_code': 'en_US',
            'created_by_user_id': test_user_id
        })
        if test_template_id: print(f"Added a test template (ID: {test_template_id}) for documents.")
    else:
        test_template_id = templates[0]['template_id']
        print(f"Using existing test template (ID: {test_template_id}) for documents.")


    print("\n--- ClientDocuments CRUD Examples ---")
    doc1_id = None
    if test_client_id_for_docs and test_user_id:
        doc1_id = add_client_document({
            'client_id': test_client_id_for_docs,
            'project_id': test_project_id_for_docs, # Optional
            'document_name': 'Initial Proposal.pdf',
            'file_name_on_disk': 'proposal_v1_final.pdf',
            'file_path_relative': f"{test_client_id_for_docs}/{test_project_id_for_docs if test_project_id_for_docs else '_client'}/proposal_v1_final.pdf",
            'document_type_generated': 'Proposal',
            'source_template_id': test_template_id, # Optional
            'created_by_user_id': test_user_id
        })
        if doc1_id:
            print(f"Added client document 'Initial Proposal.pdf' with ID: {doc1_id}")
            ret_doc = get_document_by_id(doc1_id)
            print(f"Retrieved document by ID: {ret_doc['document_name'] if ret_doc else 'Not found'}")

            update_doc_success = update_client_document(doc1_id, {'notes': 'Client approved.', 'version_tag': 'v1.1'})
            print(f"Client document update successful: {update_doc_success}")
        else:
            print("Failed to add client document.")

    if test_client_id_for_docs:
        client_docs = get_documents_for_client(test_client_id_for_docs, filters={'document_type_generated': 'Proposal'})
        print(f"Proposal documents for client {test_client_id_for_docs}: {len(client_docs)}")
        
        # Test fetching client-general documents (project_id IS NULL)
        client_general_doc_id = add_client_document({
            'client_id': test_client_id_for_docs,
            'document_name': 'Client Onboarding Checklist.docx',
            'file_name_on_disk': 'client_onboarding.docx',
            'file_path_relative': f"{test_client_id_for_docs}/client_onboarding.docx",
            'document_type_generated': 'Checklist',
            'created_by_user_id': test_user_id
        })
        if client_general_doc_id: print(f"Added client-general document ID: {client_general_doc_id}")
        
        client_general_docs = get_documents_for_client(test_client_id_for_docs, filters={'project_id': None})
        print(f"Client-general documents for client {test_client_id_for_docs}: {len(client_general_docs)}")


    if test_project_id_for_docs:
        project_docs = get_documents_for_project(test_project_id_for_docs)
        print(f"Documents for project {test_project_id_for_docs}: {len(project_docs)}")


    print("\n--- SmtpConfigs CRUD Examples ---")
    # Assuming password is encrypted elsewhere before calling add/update
    encrypted_pass = "dummy_encrypted_password_string" 
    
    smtp1_id = add_smtp_config({
        'config_name': 'Primary Gmail', 'smtp_server': 'smtp.gmail.com', 'smtp_port': 587,
        'username': 'user@gmail.com', 'password_encrypted': encrypted_pass, 
        'use_tls': True, 'is_default': True, 
        'sender_email_address': 'user@gmail.com', 'sender_display_name': 'My Gmail Account'
    })
    if smtp1_id:
        print(f"Added SMTP config 'Primary Gmail' with ID: {smtp1_id}")
        ret_smtp = get_smtp_config_by_id(smtp1_id)
        print(f"Retrieved SMTP by ID: {ret_smtp['config_name'] if ret_smtp else 'Not found'}, Default: {ret_smtp.get('is_default') if ret_smtp else ''}")
    else:
        print("Failed to add 'Primary Gmail' SMTP config.")

    smtp2_id = add_smtp_config({
        'config_name': 'Secondary Outlook', 'smtp_server': 'smtp.office365.com', 'smtp_port': 587,
        'username': 'user@outlook.com', 'password_encrypted': encrypted_pass, 
        'is_default': False, # Explicitly false
        'sender_email_address': 'user@outlook.com', 'sender_display_name': 'My Outlook Account'
    })
    if smtp2_id:
        print(f"Added SMTP config 'Secondary Outlook' with ID: {smtp2_id}")
        default_conf = get_default_smtp_config()
        print(f"Current default SMTP config: {default_conf['config_name'] if default_conf else 'None'}") # Should still be Gmail
    else:
        print("Failed to add 'Secondary Outlook' SMTP config.")

    if smtp2_id: # Set Outlook as default
        set_default_success = set_default_smtp_config(smtp2_id)
        print(f"Set 'Secondary Outlook' as default successful: {set_default_success}")
        default_conf_after_set = get_default_smtp_config()
        print(f"New default SMTP config: {default_conf_after_set['config_name'] if default_conf_after_set else 'None'}")
        
        # Verify Gmail is no longer default
        gmail_conf_after_set = get_smtp_config_by_id(smtp1_id)
        if gmail_conf_after_set:
            print(f"'Primary Gmail' is_default status: {gmail_conf_after_set['is_default']}")


    all_smtps = get_all_smtp_configs()
    print(f"Total SMTP configs: {len(all_smtps)}")

    if smtp1_id:
        update_smtp_success = update_smtp_config(smtp1_id, {'sender_display_name': 'Updated Gmail Name', 'is_default': True})
        print(f"SMTP config update for Gmail (set default again) successful: {update_smtp_success}")
        updated_smtp1 = get_smtp_config_by_id(smtp1_id)
        print(f"Updated Gmail display name: {updated_smtp1['sender_display_name'] if updated_smtp1 else ''}, Default: {updated_smtp1.get('is_default') if updated_smtp1 else ''}")
        
        # Verify Outlook is no longer default
        outlook_conf_after_gmail_default = get_smtp_config_by_id(smtp2_id)
        if outlook_conf_after_gmail_default:
            print(f"'Secondary Outlook' is_default status: {outlook_conf_after_gmail_default['is_default']}")


    # Cleanup examples (use with caution)
    # if doc1_id: delete_client_document(doc1_id)
    # if client_general_doc_id: delete_client_document(client_general_doc_id)
    # if smtp1_id: delete_smtp_config(smtp1_id)
    # if smtp2_id: delete_smtp_config(smtp2_id)
    # # test_project_id_for_docs, test_client_id_for_docs, test_user_id, test_template_id might be deleted by previous test block's commented out deletions
    # # Consider re-fetching or ensuring they exist before these deletions if running sequentially multiple times
    # if test_project_id_for_docs and get_project_by_id(test_project_id_for_docs): delete_project(test_project_id_for_docs)
    # if test_client_id_for_docs and get_client_by_id(test_client_id_for_docs): delete_client(test_client_id_for_docs)
    # if test_template_id and get_template_by_id(test_template_id): delete_template(test_template_id)
    # if test_user_id and get_user_by_id(test_user_id): delete_user(test_user_id)

    print("\n--- TeamMembers Extended Fields and KPIs CRUD Examples ---")

    # --- Cover Page Templates and Cover Pages Test ---
    print("\n--- Testing Cover Page Templates and Cover Pages ---")
    cpt_user_id = add_user({'username': 'cpt_user', 'password': 'password123', 'full_name': 'Cover Template User', 'email': 'cpt@example.com', 'role': 'designer'})
    if not cpt_user_id: cpt_user_id = get_user_by_username('cpt_user')['user_id']

    cpt_custom_id = add_cover_page_template({ # Renamed to avoid confusion with defaults
        'template_name': 'My Custom Report',
        'description': 'A custom template for special reports.',
        'default_title': 'Custom Report Title',
        'style_config_json': {'font': 'Georgia', 'primary_color': '#AA00AA'},
        'created_by_user_id': cpt_user_id,
        'is_default_template': 0 # Explicitly not default
    })
    if cpt_custom_id: print(f"Added Custom Cover Page Template 'My Custom Report' ID: {cpt_custom_id}, IsDefault: 0")

    if cpt_custom_id:
        ret_cpt_custom = get_cover_page_template_by_id(cpt_custom_id)
        print(f"Retrieved Custom CPT by ID: {ret_cpt_custom['template_name'] if ret_cpt_custom else 'Not found'}, IsDefault: {ret_cpt_custom.get('is_default_template') if ret_cpt_custom else 'N/A'}")

        # Test update: make it a default template (then change back for other tests)
        update_cpt_success = update_cover_page_template(cpt_custom_id, {'description': 'Updated custom description.', 'is_default_template': 1})
        print(f"Update Custom CPT 'My Custom Report' to be default success: {update_cpt_success}")
        ret_cpt_custom_updated = get_cover_page_template_by_id(cpt_custom_id)
        print(f"Retrieved updated Custom CPT: {ret_cpt_custom_updated['template_name'] if ret_cpt_custom_updated else 'N/A'}, IsDefault: {ret_cpt_custom_updated.get('is_default_template') if ret_cpt_custom_updated else 'N/A'}")
        assert ret_cpt_custom_updated.get('is_default_template') == 1

        # Change it back to not default
        update_cpt_success_back = update_cover_page_template(cpt_custom_id, {'is_default_template': 0})
        print(f"Update Custom CPT 'My Custom Report' back to NOT default success: {update_cpt_success_back}")
        ret_cpt_custom_final = get_cover_page_template_by_id(cpt_custom_id)
        print(f"Retrieved final Custom CPT: {ret_cpt_custom_final['template_name'] if ret_cpt_custom_final else 'N/A'}, IsDefault: {ret_cpt_custom_final.get('is_default_template') if ret_cpt_custom_final else 'N/A'}")
        assert ret_cpt_custom_final.get('is_default_template') == 0


    print(f"\n--- Testing get_all_cover_page_templates with is_default filter ---")
    all_tmpls = get_all_cover_page_templates() # No filter
    print(f"Total templates (no filter): {len(all_tmpls)}")

    default_tmpls = get_all_cover_page_templates(is_default=True)
    print(f"Default templates (is_default=True): {len(default_tmpls)}")
    for t in default_tmpls:
        print(f"  - Default: {t['template_name']} (IsDefault: {t['is_default_template']})")
        assert t['is_default_template'] == 1, f"Template '{t['template_name']}' should be default!"

    non_default_tmpls = get_all_cover_page_templates(is_default=False)
    print(f"Non-default templates (is_default=False): {len(non_default_tmpls)}")
    if cpt_custom_id and ret_cpt_custom_final and ret_cpt_custom_final.get('is_default_template') == 0:
        found_in_non_default = any(t['template_id'] == cpt_custom_id for t in non_default_tmpls)
        assert found_in_non_default, "'My Custom Report' was set to non-default but NOT found in non-defaults."
        print(f"'My Custom Report' correctly found in non-default list.")
    for t in non_default_tmpls:
         print(f"  - Non-Default: {t['template_name']} (IsDefault: {t['is_default_template']})")
         assert t['is_default_template'] == 0, f"Template '{t['template_name']}' should be non-default!"

    # Test get_cover_page_template_by_name for a default template
    standard_report_template = get_cover_page_template_by_name('Standard Report Cover')
    if standard_report_template:
        print(f"Retrieved 'Standard Report Cover' by name. IsDefault: {standard_report_template.get('is_default_template')}")
        assert standard_report_template.get('is_default_template') == 1, "'Standard Report Cover' should be default by name."
    else:
        print("Could not retrieve 'Standard Report Cover' by name for is_default check.")

    # Cover Page instance
    cp_client_id = add_client({'client_name': 'CoverPage Client', 'project_identifier': 'CP_Test_001'})
    if not cp_client_id: cp_client_id = get_all_clients({'client_name': 'CoverPage Client'})[0]['client_id']

    cp1_id = None
    if cp_client_id and cpt1_id and cpt_user_id:
        cp1_id = add_cover_page({
            'cover_page_name': 'Client X - Proposal Cover V1',
            'client_id': cp_client_id,
            'template_id': cpt1_id,
            'title': 'Specific Project Proposal',
            'subtitle': 'For CoverPage Client',
            'author_text': 'Sales Team', # Updated field name
            'institution_text': 'Our Company LLC',
            'department_text': 'Sales Department',
            'document_type_text': 'Proposal',
            'document_version': '1.0',
            'creation_date': datetime.utcnow().date().isoformat(),
            'logo_name': 'specific_logo.png', # Updated field name
            'logo_data': b'somedummyimagedata',   # Added field
            'custom_style_config_json': {'secondary_color': '#FF0000'},
            'created_by_user_id': cpt_user_id
        })
        if cp1_id: print(f"Added Cover Page instance ID: {cp1_id}")

    if cp1_id:
        ret_cp1 = get_cover_page_by_id(cp1_id)
        print(f"Retrieved Cover Page by ID: {ret_cp1['title'] if ret_cp1 else 'Not found'}")
        print(f"  Custom Style: {ret_cp1.get('custom_style_config_json') if ret_cp1 else ''}")

    if cp_client_id:
        client_cover_pages = get_cover_pages_for_client(cp_client_id)
        print(f"Cover pages for client {cp_client_id}: {len(client_cover_pages)}")

    # Clean up Cover Page related test data
    if cp1_id and get_cover_page_by_id(cp1_id): delete_cover_page(cp1_id) # cp1_id is a cover page instance
    if cpt_custom_id and get_cover_page_template_by_id(cpt_custom_id): # cpt_custom_id is a template
        delete_cover_page_template(cpt_custom_id)
        print(f"Cleaned up custom template ID {cpt_custom_id}")
    # Default templates (like 'Classic Formal' referenced by cpt2_id) should not be deleted here by tests.

    # Test get_cover_pages_for_user (using cpt_user_id for whom defaults were made)
    if cpt_user_id:
        # Add a cover page specifically for this user to test retrieval
        # Ensure cp_client_id is still valid or re-fetch/re-create.
        # For simplicity, assume cp_client_id created earlier is still usable for this test.
        # If cp_client_id was deleted, this part needs adjustment or ensure it's created before this block.

        # Let's ensure a client exists for this test section
        test_get_user_pages_client_id = cp_client_id # Try to reuse if available
        if not test_get_user_pages_client_id or not get_client_by_id(test_get_user_pages_client_id):
            test_get_user_pages_client_id = add_client({'client_name': 'ClientForUserPageTest', 'project_identifier': 'CPUPT_001', 'created_by_user_id': cpt_user_id})

        temp_cp_for_user_test_id = None
        if test_get_user_pages_client_id and cpt_user_id:
             temp_cp_for_user_test_id = add_cover_page({
                'cover_page_name': 'User Specific Cover Test for Get',
                'client_id': test_get_user_pages_client_id,
                'title': 'User Test Document - Get Test',
                'created_by_user_id': cpt_user_id
            })

        if temp_cp_for_user_test_id:
            print(f"\n--- Testing get_cover_pages_for_user for user: {cpt_user_id} ---")
            user_cover_pages = get_cover_pages_for_user(cpt_user_id)
            print(f"Found {len(user_cover_pages)} cover page(s) for user {cpt_user_id}.")
            if user_cover_pages:
                print(f"First cover page found: '{user_cover_pages[0]['cover_page_name']}' with title '{user_cover_pages[0]['title']}'")
            delete_cover_page(temp_cp_for_user_test_id) # Cleanup
            print(f"Cleaned up temporary cover page ID: {temp_cp_for_user_test_id}")
        else:
            print(f"\nCould not create a temporary cover page for user {cpt_user_id} for get_cover_pages_for_user test.")

        if test_get_user_pages_client_id and test_get_user_pages_client_id != cp_client_id: # If we created a new one for this test
             delete_client(test_get_user_pages_client_id)


    if cp_client_id and get_client_by_id(cp_client_id): delete_client(cp_client_id)
    if cpt_user_id and get_user_by_id(cpt_user_id): delete_user(cpt_user_id)
    print("--- Cover Page testing completed and cleaned up. ---")

    initialize_database() # Ensure tables are created with new schema

    # --- Populate Default Cover Page Templates ---
    # This should be called AFTER initialize_database() to ensure tables exist.
    _populate_default_cover_page_templates()

    # Test TeamMembers
    print("\nTesting TeamMembers...")
    tm_email = "new.teammember@example.com"
    # Clean up if exists from previous failed run
    existing_tm_list = get_all_team_members()
    for tm in existing_tm_list:
        if tm['email'] == tm_email:
            delete_team_member(tm['team_member_id'])
            print(f"Deleted existing test team member with email {tm_email}")

    team_member_id = add_team_member({
        'full_name': 'New Member',
        'email': tm_email,
        'role_or_title': 'Developer',
        'department': 'Engineering',
        'hire_date': '2024-01-15',
        'performance': 8,
        'skills': 'Python, SQL, FastAPI'
    })
    if team_member_id:
        print(f"Added team member 'New Member' with ID: {team_member_id}")
        member = get_team_member_by_id(team_member_id)
        print(f"Retrieved member: {member}")

        updated = update_team_member(team_member_id, {
            'performance': 9,
            'skills': 'Python, SQL, FastAPI, Docker'
        })
        print(f"Team member update successful: {updated}")
        member = get_team_member_by_id(team_member_id)
        print(f"Updated member: {member}")
    else:
        print("Failed to add team member.")

    # Test KPIs - Requires a project
    print("\nTesting KPIs...")
    # Need a client and user for project
    kpi_test_user_id = add_user({'username': 'kpi_user', 'password': 'password', 'full_name': 'KPI User', 'email': 'kpi@example.com', 'role': 'manager'})
    if not kpi_test_user_id:
        # Attempt to get existing user if add failed due to uniqueness
        kpi_user_existing = get_user_by_username('kpi_user')
        if kpi_user_existing:
            kpi_test_user_id = kpi_user_existing['user_id']
            print(f"Using existing user 'kpi_user' (ID: {kpi_test_user_id})")
        else:
            print("Failed to create or find user 'kpi_user' for KPI tests. Aborting KPI tests.")
            kpi_test_user_id = None

    kpi_test_client_id = None
    if kpi_test_user_id:
        kpi_test_client_id = add_client({'client_name': 'KPI Test Client', 'created_by_user_id': kpi_test_user_id})
        if not kpi_test_client_id:
            existing_kpi_client = get_all_clients({'client_name': 'KPI Test Client'})
            if existing_kpi_client:
                kpi_test_client_id = existing_kpi_client[0]['client_id']
                print(f"Using existing client 'KPI Test Client' (ID: {kpi_test_client_id})")
            else:
                print("Failed to create or find client 'KPI Test Client'. Aborting KPI tests.")
                kpi_test_client_id = None

    test_project_for_kpi_id = None
    if kpi_test_client_id and kpi_test_user_id:
        # Clean up existing project if any
        existing_projects = get_projects_by_client_id(kpi_test_client_id)
        for p in existing_projects:
            if p['project_name'] == 'KPI Test Project':
                # Need to delete KPIs associated with this project first
                kpis_to_delete = get_kpis_for_project(p['project_id'])
                for kpi_del in kpis_to_delete:
                    delete_kpi(kpi_del['kpi_id'])
                delete_project(p['project_id'])
                print(f"Deleted existing 'KPI Test Project' and its KPIs.")

        test_project_for_kpi_id = add_project({
            'client_id': kpi_test_client_id,
            'project_name': 'KPI Test Project',
            'manager_team_member_id': kpi_test_user_id, # Assuming user_id can be used here as per schema
            'status_id': 10 # Assuming status_id 10 exists ('Project Planning')
        })
        if test_project_for_kpi_id:
            print(f"Added 'KPI Test Project' with ID: {test_project_for_kpi_id} for KPI tests.")
        else:
            print("Failed to add project for KPI tests.")

    if test_project_for_kpi_id:
        kpi_id = add_kpi({
            'project_id': test_project_for_kpi_id,
            'name': 'Customer Satisfaction',
            'value': 85.5,
            'target': 90.0,
            'trend': 'up',
            'unit': '%'
        })
        if kpi_id:
            print(f"Added KPI 'Customer Satisfaction' with ID: {kpi_id}")

            ret_kpi = get_kpi_by_id(kpi_id)
            print(f"Retrieved KPI by ID: {ret_kpi}")

            kpis_for_proj = get_kpis_for_project(test_project_for_kpi_id)
            print(f"KPIs for project {test_project_for_kpi_id}: {kpis_for_proj}")

            updated_kpi = update_kpi(kpi_id, {'value': 87.0, 'trend': 'stable'})
            print(f"KPI update successful: {updated_kpi}")
            ret_kpi_updated = get_kpi_by_id(kpi_id)
            print(f"Updated KPI: {ret_kpi_updated}")

            deleted_kpi = delete_kpi(kpi_id)
            print(f"KPI delete successful: {deleted_kpi}")
        else:
            print("Failed to add KPI.")
    else:
        print("Skipping KPI tests as project setup failed.")

    # Clean up test data
    print("\nCleaning up test data...")
    if team_member_id and get_team_member_by_id(team_member_id):
        delete_team_member(team_member_id)
        print(f"Deleted team member ID: {team_member_id}")

    if test_project_for_kpi_id and get_project_by_id(test_project_for_kpi_id):
        # Ensure KPIs are deleted if any test failed mid-way
        kpis_left = get_kpis_for_project(test_project_for_kpi_id)
        for kpi_left_obj in kpis_left:
            delete_kpi(kpi_left_obj['kpi_id'])
            print(f"Cleaned up leftover KPI ID: {kpi_left_obj['kpi_id']}")
        delete_project(test_project_for_kpi_id)
        print(f"Deleted project ID: {test_project_for_kpi_id}")

    if kpi_test_client_id and get_client_by_id(kpi_test_client_id):
        delete_client(kpi_test_client_id)
        print(f"Deleted client ID: {kpi_test_client_id}")

    if kpi_test_user_id and get_user_by_id(kpi_test_user_id):
        delete_user(kpi_test_user_id)
        print(f"Deleted user ID: {kpi_test_user_id}")

    print("\n--- Schema changes and basic tests completed. ---")

    print("\n--- Testing get_default_company ---")
    initialize_database() # Ensure tables are fresh or correctly set up

    company_name1 = "Test Default Co"
    company_name2 = "New Default Co"
    test_comp1_id = None
    test_comp2_id = None

    # Clean up any previous test companies with the same names to ensure test idempotency
    all_comps_initial = get_all_companies()
    for comp_init in all_comps_initial:
        if comp_init['company_name'] == company_name1:
            print(f"Deleting pre-existing company: {comp_init['company_name']} (ID: {comp_init['company_id']})")
            delete_company(comp_init['company_id'])
        if comp_init['company_name'] == company_name2:
            print(f"Deleting pre-existing company: {comp_init['company_name']} (ID: {comp_init['company_id']})")
            delete_company(comp_init['company_id'])

    # 1. Add first company
    test_comp1_id = add_company({'company_name': company_name1, 'address': '1 First St'})
    if test_comp1_id:
        print(f"Added company '{company_name1}' with ID: {test_comp1_id}")
    else:
        print(f"Failed to add company '{company_name1}'")
        # Cannot proceed with test if this fails
        exit()

    # 2. Set first company as default
    print(f"Setting '{company_name1}' as default...")
    set_default_company(test_comp1_id)

    # 3. Get default company and assert it's the first one
    default_co = get_default_company()
    if default_co:
        print(f"Retrieved default company: {default_co['company_name']} (ID: {default_co['company_id']})")
        assert default_co['company_name'] == company_name1, f"Assertion Failed: Expected default company name to be '{company_name1}', got '{default_co['company_name']}'"
        assert default_co['company_id'] == test_comp1_id, f"Assertion Failed: Expected default company ID to be '{test_comp1_id}', got '{default_co['company_id']}'"
        print(f"SUCCESS: '{company_name1}' is correctly set and retrieved as default.")
    else:
        print(f"Assertion Failed: Expected to retrieve '{company_name1}' as default, but got None.")
        # Cannot proceed reliably if this fails
        if test_comp1_id: delete_company(test_comp1_id)
        exit()

    # 4. Add second company
    test_comp2_id = add_company({'company_name': company_name2, 'address': '2 Second St'})
    if test_comp2_id:
        print(f"Added company '{company_name2}' with ID: {test_comp2_id}")
    else:
        print(f"Failed to add company '{company_name2}'")
        if test_comp1_id: delete_company(test_comp1_id) # Clean up first company
        exit()

    # 5. Set second company as default
    print(f"Setting '{company_name2}' as default...")
    set_default_company(test_comp2_id)

    # 6. Get default company and assert it's the second one
    default_co_new = get_default_company()
    if default_co_new:
        print(f"Retrieved new default company: {default_co_new['company_name']} (ID: {default_co_new['company_id']})")
        assert default_co_new['company_name'] == company_name2, f"Assertion Failed: Expected new default company name to be '{company_name2}', got '{default_co_new['company_name']}'"
        assert default_co_new['company_id'] == test_comp2_id, f"Assertion Failed: Expected new default company ID to be '{test_comp2_id}', got '{default_co_new['company_id']}'"
        print(f"SUCCESS: '{company_name2}' is correctly set and retrieved as new default.")
    else:
        print(f"Assertion Failed: Expected to retrieve '{company_name2}' as new default, but got None.")
        # Clean up both companies before exiting
        if test_comp1_id: delete_company(test_comp1_id)
        if test_comp2_id: delete_company(test_comp2_id)
        exit()

    # 7. Assert that the first company is no longer the default
    comp1_check = get_company_by_id(test_comp1_id)
    if comp1_check:
        assert not comp1_check['is_default'], f"Assertion Failed: Company '{company_name1}' should no longer be default, but 'is_default' is {comp1_check['is_default']}"
        print(f"SUCCESS: Company '{company_name1}' is_default is correctly False after '{company_name2}' became default.")
    else:
        print(f"Error: Could not retrieve company '{company_name1}' for final check.")
        # Fallback check: ensure get_default_company doesn't return it
        current_default_still_comp2 = get_default_company()
        if current_default_still_comp2 and current_default_still_comp2['company_id'] == test_comp2_id:
             print(f"Fallback check: Current default is still '{company_name2}', so '{company_name1}' is not default. This is acceptable.")
        else:
            print(f"Fallback check failed: Default company is not '{company_name2}' or is None.")


    # 8. Clean up
    print("Cleaning up test companies...")
    if test_comp1_id:
        delete_company(test_comp1_id)
        print(f"Deleted company '{company_name1}' (ID: {test_comp1_id})")
    if test_comp2_id:
        delete_company(test_comp2_id)
        print(f"Deleted company '{company_name2}' (ID: {test_comp2_id})")

    final_default_check = get_default_company()
    if final_default_check is None:
        print("SUCCESS: Default company is None after cleanup, as expected.")
    else:
        print(f"Warning: A default company still exists after cleanup: {final_default_check['company_name']}. This might indicate issues in other tests or test setup.")


    print("--- Finished testing get_default_company ---")