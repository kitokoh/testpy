import sqlite3
import os
import json
from datetime import datetime
import uuid # Added
import hashlib # Added

# Assuming config.py is in the parent directory of 'db'
# e.g. /app/config.py and this file is /app/db/ca.py
from config import DATABASE_PATH

# Placeholder imports for helper functions that reside in db.py
# These would need to be resolved correctly in a real scenario, e.g.,
# from .db_main import _get_or_create_category_id, _populate_default_cover_page_templates
# Or by ensuring db.py is structured to allow these imports.

# Import the original db.py as a module to access its helper functions
from db import db_seed as db_helpers

def initialize_database():
    """
    Initializes the database by creating tables if they don't already exist.
    """
    conn = sqlite3.connect(DATABASE_PATH) # Updated to use DATABASE_PATH
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
        phone TEXT, -- Added phone
        email TEXT, -- Added email
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
        {'status_name': 'Prospect (Proforma Envoyé)', 'status_type': 'Client', 'color_hex': '#e67e22', 'icon_name': 'document-send', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Actif', 'status_type': 'Client', 'color_hex': '#2ecc71', 'icon_name': 'user-available', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Vendu', 'status_type': 'Client', 'color_hex': '#5cb85c', 'icon_name': 'emblem-ok', 'is_completion_status': True, 'is_archival_status': False},
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
        {'status_name': 'Cancelled', 'status_type': 'Task', 'color_hex': '#7f8c8d', 'icon_name': 'dialog-cancel', 'is_completion_status': False, 'is_archival_status': True},

        # SAVTicket Statuses
        {'status_name': 'Ouvert', 'status_type': 'SAVTicket', 'color_hex': '#d35400', 'icon_name': 'folder-new', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'En Investigation', 'status_type': 'SAVTicket', 'color_hex': '#f39c12', 'icon_name': 'system-search', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'En Attente (Client)', 'status_type': 'SAVTicket', 'color_hex': '#3498db', 'icon_name': 'folder-locked', 'is_completion_status': False, 'is_archival_status': False},
        {'status_name': 'Résolu', 'status_type': 'SAVTicket', 'color_hex': '#2ecc71', 'icon_name': 'folder-check', 'is_completion_status': True, 'is_archival_status': False},
        {'status_name': 'Fermé', 'status_type': 'SAVTicket', 'color_hex': '#95a5a6', 'icon_name': 'folder', 'is_completion_status': True, 'is_archival_status': True}
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
        distributor_specific_info TEXT, -- Added for distributor specific information
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Maps to creation_date from main.py
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Maps to last_modified from main.py
        created_by_user_id TEXT,
        FOREIGN KEY (country_id) REFERENCES Countries (country_id),
        FOREIGN KEY (city_id) REFERENCES Cities (city_id),
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id)
    )
    """)

    # Check if distributor_specific_info column exists and add it if not.
    # This check is robust for multiple runs.
    cursor.execute("PRAGMA table_info(Clients)")
    columns_info = cursor.fetchall()
    column_names = [info['name'] for info in columns_info] # Use dict access due to row_factory
    if 'distributor_specific_info' not in column_names:
        try:
            # Ensure this ALTER TABLE is executed outside of any potential transaction
            # on the cursor if it was part of a larger one before this point.
            # However, standard practice is to commit DDL changes immediately.
            conn.execute("ALTER TABLE Clients ADD COLUMN distributor_specific_info TEXT")
            conn.commit() # Commit ALTER TABLE immediately
            print("Added 'distributor_specific_info' column to Clients table.")
        except sqlite3.Error as e:
            print(f"Error adding 'distributor_specific_info' column to Clients table: {e}")
            # Depending on the error (e.g., "duplicate column name"), might not need to rollback.
            # If other critical error, rollback might be considered if part of a larger uncommitted transaction.
            # For standalone ALTER, commit/rollback is managed per statement or by connection settings.

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

    # Create ProductDimensions table (New)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ProductDimensions (
        product_id INTEGER PRIMARY KEY,
        dim_A TEXT,
        dim_B TEXT,
        dim_C TEXT,
        dim_D TEXT,
        dim_E TEXT,
        dim_F TEXT,
        dim_G TEXT,
        dim_H TEXT,
        dim_I TEXT,
        dim_J TEXT,
        technical_image_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES Products (product_id) ON DELETE CASCADE
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
        serial_number TEXT,
        purchase_confirmed_at TIMESTAMP,
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
                new_cat_id = db_helpers._get_or_create_category_id(cursor, category_name_text, general_category_id_for_migration)


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
        order_identifier TEXT, -- New column
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

    # Check if order_identifier column exists in ClientDocuments and add it if not
    cursor.execute("PRAGMA table_info(ClientDocuments)")
    columns_cd = [column[1] for column in cursor.fetchall()]
    if 'order_identifier' not in columns_cd:
        try:
            cursor.execute("ALTER TABLE ClientDocuments ADD COLUMN order_identifier TEXT")
            conn.commit()
            print("Added 'order_identifier' column to ClientDocuments table.")
        except sqlite3.Error as e:
            print(f"Error adding 'order_identifier' column to ClientDocuments: {e}")

    # Create ClientDocumentNotes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ClientDocumentNotes (
        note_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        document_type TEXT NOT NULL, -- e.g., 'Proforma', 'Invoice', 'PackingList', 'CertificateOfOrigin'
        language_code TEXT NOT NULL, -- e.g., 'fr', 'en'
        note_content TEXT NOT NULL,  -- The actual notes, potentially multi-line
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        UNIQUE (client_id, document_type, language_code)
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

    # Indexes for Clients table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_status_id ON Clients(status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_country_id ON Clients(country_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_city_id ON Clients(city_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_project_identifier ON Clients(project_identifier)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_company_name ON Clients(company_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_category ON Clients(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_created_by_user_id ON Clients(created_by_user_id)")

    # Indexes for Projects table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_client_id ON Projects(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status_id ON Projects(status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_manager_team_member_id ON Projects(manager_team_member_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_priority ON Projects(priority)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_deadline_date ON Projects(deadline_date)")

    # Indexes for Tasks table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON Tasks(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_id ON Tasks(status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assignee_team_member_id ON Tasks(assignee_team_member_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_reporter_team_member_id ON Tasks(reporter_team_member_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON Tasks(due_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON Tasks(priority)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_parent_task_id ON Tasks(parent_task_id)")

    # Indexes for Templates table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_template_type ON Templates(template_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_language_code ON Templates(language_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_category_id ON Templates(category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_is_default_for_type_lang ON Templates(is_default_for_type_lang)")

    # Indexes for ClientDocuments table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_client_id ON ClientDocuments(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_project_id ON ClientDocuments(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_document_type_generated ON ClientDocuments(document_type_generated)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_source_template_id ON ClientDocuments(source_template_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientdocuments_order_identifier ON ClientDocuments(order_identifier)")

    # Indexes for TeamMembers table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teammembers_user_id ON TeamMembers(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teammembers_is_active ON TeamMembers(is_active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teammembers_department ON TeamMembers(department)")

    # Indexes for Contacts table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_company_name ON Contacts(company_name)")

    # Indexes for ClientContacts table (Associative)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientcontacts_contact_id ON ClientContacts(contact_id)")

    # Indexes for Products table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON Products(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_is_active ON Products(is_active)")

    # Indexes for ProductEquivalencies table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_productequivalencies_product_id_b ON ProductEquivalencies(product_id_b)")

    # Indexes for ClientProjectProducts table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientprojectproducts_product_id ON ClientProjectProducts(product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientprojectproducts_client_project ON ClientProjectProducts(client_id, project_id)")

    # Indexes for ActivityLog table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activitylog_user_id ON ActivityLog(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activitylog_created_at ON ActivityLog(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activitylog_action_type ON ActivityLog(action_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activitylog_related_entity ON ActivityLog(related_entity_type, related_entity_id)")

    # Indexes for ScheduledEmails table
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduledemails_status_time ON ScheduledEmails(status, scheduled_send_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduledemails_related_client_id ON ScheduledEmails(related_client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduledemails_related_project_id ON ScheduledEmails(related_project_id)")

    # StatusSettings: UNIQUE(status_name, status_type) already indexed. Index on status_type alone might be useful.
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_statussettings_type ON StatusSettings(status_type)")

    # Create SAVTickets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS SAVTickets (
        ticket_id TEXT PRIMARY KEY,
        client_id TEXT NOT NULL,
        client_project_product_id INTEGER,
        issue_description TEXT NOT NULL,
        status_id INTEGER NOT NULL,
        assigned_technician_id INTEGER,
        resolution_details TEXT,
        opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        closed_at TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (client_project_product_id) REFERENCES ClientProjectProducts (client_project_product_id) ON DELETE SET NULL,
        FOREIGN KEY (status_id) REFERENCES StatusSettings (status_id),
        FOREIGN KEY (assigned_technician_id) REFERENCES TeamMembers (team_member_id) ON DELETE SET NULL,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id) ON DELETE SET NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_savtickets_client_id ON SAVTickets(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_savtickets_status_id ON SAVTickets(status_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_savtickets_assigned_technician_id ON SAVTickets(assigned_technician_id)")

    # Create ImportantDates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ImportantDates (
        important_date_id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_name TEXT NOT NULL,
        date_value DATE NOT NULL,
        is_recurring_annually BOOLEAN DEFAULT TRUE,
        language_code TEXT,
        email_template_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (date_name, date_value, language_code),
        FOREIGN KEY (email_template_id) REFERENCES Templates (template_id) ON DELETE SET NULL
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_importantdates_date_value ON ImportantDates(date_value)")

    # Create Transporters table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Transporters (
        transporter_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        service_area TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transporters_name ON Transporters(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transporters_service_area ON Transporters(service_area)")

    # Create FreightForwarders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS FreightForwarders (
        forwarder_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        services_offered TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_freightforwarders_name ON FreightForwarders(name)")

    # Create Client_AssignedPersonnel association table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Client_AssignedPersonnel (
        assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        personnel_id INTEGER NOT NULL,
        role_in_project TEXT,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (personnel_id) REFERENCES CompanyPersonnel (personnel_id) ON DELETE CASCADE,
        UNIQUE (client_id, personnel_id, role_in_project)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientassignedpersonnel_client_id ON Client_AssignedPersonnel(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientassignedpersonnel_personnel_id ON Client_AssignedPersonnel(personnel_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientassignedpersonnel_role ON Client_AssignedPersonnel(role_in_project)")

    # Create Client_Transporters association table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Client_Transporters (
        client_transporter_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        transporter_id TEXT NOT NULL,
        transport_details TEXT,
        cost_estimate REAL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        email_status TEXT DEFAULT 'Pending', -- Added new column
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (transporter_id) REFERENCES Transporters (transporter_id) ON DELETE CASCADE,
        UNIQUE (client_id, transporter_id)
    )
    """)
    # Check and add email_status column to Client_Transporters if it doesn't exist
    cursor.execute("PRAGMA table_info(Client_Transporters)")
    columns_ct = [column['name'] for column in cursor.fetchall()] # Assumes conn.row_factory = sqlite3.Row
    if 'email_status' not in columns_ct:
        try:
            cursor.execute("ALTER TABLE Client_Transporters ADD COLUMN email_status TEXT DEFAULT 'Pending'")
            conn.commit() # Commit ALTER TABLE immediately
            print("Added 'email_status' column to Client_Transporters table.")
        except sqlite3.Error as e_ct_alter:
            print(f"Error adding 'email_status' column to Client_Transporters: {e_ct_alter}")
            # No rollback here, as it's a DDL change outside a larger transaction for this specific part.

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clienttransporters_client_id ON Client_Transporters(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clienttransporters_transporter_id ON Client_Transporters(transporter_id)")

    # Create Client_FreightForwarders association table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Client_FreightForwarders (
        client_forwarder_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id TEXT NOT NULL,
        forwarder_id TEXT NOT NULL,
        task_description TEXT,
        cost_estimate REAL,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES Clients (client_id) ON DELETE CASCADE,
        FOREIGN KEY (forwarder_id) REFERENCES FreightForwarders (forwarder_id) ON DELETE CASCADE,
        UNIQUE (client_id, forwarder_id)
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientfreightforwarders_client_id ON Client_FreightForwarders(client_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientfreightforwarders_forwarder_id ON Client_FreightForwarders(forwarder_id)")

    # --- New Partner Tables ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Partners (
            partner_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            location TEXT,
            email TEXT UNIQUE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerCategories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS PartnerCategoryLink (
            partner_id TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (partner_id, category_id),
            FOREIGN KEY (partner_id) REFERENCES Partners(partner_id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES PartnerCategories(category_id) ON DELETE CASCADE
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

    # --- Indexes for New Partner Tables ---
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partners_email ON Partners(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnercontacts_partner_id ON PartnerContacts(partner_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnercategorylink_category_id ON PartnerCategoryLink(category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_partnerdocuments_partner_id ON PartnerDocuments(partner_id)")
    # --- End Indexes for New Partner Tables ---

    # MediaItems Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MediaItems (
            media_item_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            item_type TEXT NOT NULL, -- 'video', 'image', 'link'
            filepath TEXT,           -- Relative path for 'video'/'image', NULL for 'link'
            url TEXT,                -- URL for 'link', NULL for 'video'/'image'
            uploader_user_id TEXT,   -- Optional: Who uploaded/added this item
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            thumbnail_path TEXT, -- Added for thumbnails
            metadata_json TEXT, -- New column for arbitrary JSON metadata
            FOREIGN KEY (uploader_user_id) REFERENCES Users(user_id) ON DELETE SET NULL
        );
    ''')
    # Add thumbnail_path and metadata_json columns if they don't exist (for existing databases)
    cursor.execute("PRAGMA table_info(MediaItems)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'thumbnail_path' not in columns:
        try:
            cursor.execute("ALTER TABLE MediaItems ADD COLUMN thumbnail_path TEXT;")
            print("Added 'thumbnail_path' column to MediaItems table.")
        except sqlite3.Error as e_alter:
            print(f"Error adding 'thumbnail_path' column: {e_alter}")

    if 'metadata_json' not in columns:
        try:
            cursor.execute("ALTER TABLE MediaItems ADD COLUMN metadata_json TEXT;")
            print("Added 'metadata_json' column to MediaItems table.")
        except sqlite3.Error as e_alter:
            print(f"Error adding 'metadata_json' column: {e_alter}")

    # Commit any ALTER TABLE changes immediately if they happened
    if 'thumbnail_path' not in columns or 'metadata_json' not in columns:
        conn.commit()

    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitems_item_type ON MediaItems(item_type);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitems_uploader_user_id ON MediaItems(uploader_user_id);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitems_created_at ON MediaItems(created_at);''')

    # Tags Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Tags (
            tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT NOT NULL UNIQUE
        );
    ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_tags_tag_name ON Tags(tag_name);''')

    # MediaItemTags Table (Junction Table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS MediaItemTags (
            media_item_tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_item_id TEXT NOT NULL,
            tag_id INTEGER NOT NULL,
            FOREIGN KEY (media_item_id) REFERENCES MediaItems(media_item_id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES Tags(tag_id) ON DELETE CASCADE,
            UNIQUE (media_item_id, tag_id)
        );
    ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitemtags_media_item_id ON MediaItemTags(media_item_id);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitemtags_tag_id ON MediaItemTags(tag_id);''')

    # Migration logic for existing MediaItems with 'category'
    cursor.execute("PRAGMA table_info(MediaItems)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'category' in columns:
        print("Migrating 'category' from MediaItems to Tags system...")
        # Fetch all items with categories
        cursor.execute("SELECT media_item_id, category FROM MediaItems WHERE category IS NOT NULL AND category != ''")
        items_with_categories = cursor.fetchall()

        migrated_count = 0
        for item_row in items_with_categories:
            item_id = item_row['media_item_id']
            category_name = item_row['category']

            # Get or create tag_id for the category_name
            cursor.execute("SELECT tag_id FROM Tags WHERE tag_name = ?", (category_name,))
            tag_row = cursor.fetchone()
            if tag_row:
                tag_id = tag_row['tag_id']
            else:
                cursor.execute("INSERT INTO Tags (tag_name) VALUES (?)", (category_name,))
                tag_id = cursor.lastrowid

            # Link item to this tag
            if tag_id:
                try:
                    cursor.execute("INSERT INTO MediaItemTags (media_item_id, tag_id) VALUES (?, ?)", (item_id, tag_id))
                    migrated_count +=1
                except sqlite3.IntegrityError: # Should not happen if logic is clean but good for safety
                    print(f"Warning: Could not link item {item_id} to tag '{category_name}' (ID: {tag_id}), possibly already linked.")

        conn.commit() # Commit tag creation and linking before altering table
        print(f"Committed {migrated_count} category-to-tag migrations.")

        # Recreate MediaItems table without the category column
        # This is the safer way in SQLite to drop a column if direct DROP is not universally available/safe.
        print("Recreating MediaItems table to remove 'category' column...")
        cursor.execute("ALTER TABLE MediaItems RENAME TO MediaItems_old_for_category_migration")

        # Create new MediaItems table without 'category'
        cursor.execute('''
            CREATE TABLE MediaItems (
                media_item_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                -- category TEXT, -- This column is now removed
                item_type TEXT NOT NULL,
                filepath TEXT,
                url TEXT,
                uploader_user_id TEXT,
                thumbnail_path TEXT,
                metadata_json TEXT, -- Added here for new table creation during migration
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploader_user_id) REFERENCES Users(user_id) ON DELETE SET NULL
            );
        ''')

        # Copy data from old table to new table, including new columns as NULL
        cursor.execute('''
            INSERT INTO MediaItems (media_item_id, title, description, item_type, filepath, url, uploader_user_id, thumbnail_path, metadata_json, created_at, updated_at)
            SELECT media_item_id, title, description, item_type, filepath, url, uploader_user_id, NULL, NULL, created_at, updated_at
            FROM MediaItems_old_for_category_migration;
        ''')

        cursor.execute("DROP TABLE MediaItems_old_for_category_migration")
        conn.commit() # Commit table recreation
        print("MediaItems table recreated without 'category' column and with 'thumbnail_path' and 'metadata_json', data copied.")
        # Re-create indexes for the new MediaItems table
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitems_item_type ON MediaItems(item_type);''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitems_uploader_user_id ON MediaItems(uploader_user_id);''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_mediaitems_created_at ON MediaItems(created_at);''')
        print("Indexes for new MediaItems table recreated.")

    # Playlists Table (ensure it exists, as PlaylistItems depends on it)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Playlists (
            playlist_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        );
    ''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_playlists_user_id ON Playlists(user_id);''')


    # PlaylistItems Table - Ensure FK to MediaItems is correctly defined
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PlaylistItems (
            playlist_item_id TEXT PRIMARY KEY,
            playlist_id TEXT NOT NULL,
            media_item_id TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (playlist_id) REFERENCES Playlists(playlist_id) ON DELETE CASCADE,
            FOREIGN KEY (media_item_id) REFERENCES MediaItems(media_item_id) ON DELETE CASCADE
        );
    ''')
    # Ensure indexes for PlaylistItems are also created (might be redundant if table already existed with them)
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_playlistitems_playlist_id ON PlaylistItems(playlist_id);''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_playlistitems_media_item_id ON PlaylistItems(media_item_id);''')

    # Schema creation is done. Commit and close connection for initialize_database.
    conn.commit()
    conn.close()
