import sqlite3
import uuid
import hashlib
from datetime import datetime
import json

# Global variable for the database name
DATABASE_NAME = "app_data.db"

def initialize_database():
    """
    Initializes the database by creating tables if they don't already exist.
    """
    conn = sqlite3.connect(DATABASE_NAME)
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

    # Create StatusSettings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS StatusSettings (
        status_id INTEGER PRIMARY KEY AUTOINCREMENT,
        status_name TEXT NOT NULL,
        status_type TEXT NOT NULL, -- e.g., 'Client', 'Project', 'Task'
        color_hex TEXT,
        default_duration_days INTEGER,
        is_archival_status BOOLEAN DEFAULT FALSE,
        is_completion_status BOOLEAN DEFAULT FALSE,
        UNIQUE (status_name, status_type)
    )
    """)

    # --- Pre-populate StatusSettings ---
    default_statuses = [
        # Client Statuses
        {'status_name': 'En cours', 'status_type': 'Client', 'color_hex': '#3498db', 'is_completion_status': False, 'is_archival_status': False}, # Blue
        {'status_name': 'Prospect', 'status_type': 'Client', 'color_hex': '#f1c40f', 'is_completion_status': False, 'is_archival_status': False}, # Yellow
        {'status_name': 'Actif', 'status_type': 'Client', 'color_hex': '#2ecc71', 'is_completion_status': False, 'is_archival_status': False}, # Green
        {'status_name': 'Inactif', 'status_type': 'Client', 'color_hex': '#95a5a6', 'is_completion_status': False, 'is_archival_status': True},  # Grey
        {'status_name': 'Complété', 'status_type': 'Client', 'color_hex': '#27ae60', 'is_completion_status': True, 'is_archival_status': False}, # Darker Green
        {'status_name': 'Archivé', 'status_type': 'Client', 'color_hex': '#7f8c8d', 'is_completion_status': False, 'is_archival_status': True},  # Darker Grey
        {'status_name': 'Urgent', 'status_type': 'Client', 'color_hex': '#e74c3c', 'is_completion_status': False, 'is_archival_status': False},   # Red

        # Project Statuses
        {'status_name': 'Planning', 'status_type': 'Project', 'color_hex': '#1abc9c', 'is_completion_status': False, 'is_archival_status': False}, # Turquoise
        {'status_name': 'En cours', 'status_type': 'Project', 'color_hex': '#3498db', 'is_completion_status': False, 'is_archival_status': False}, # Blue
        {'status_name': 'En attente', 'status_type': 'Project', 'color_hex': '#f39c12', 'is_completion_status': False, 'is_archival_status': False},# Orange
        {'status_name': 'Terminé', 'status_type': 'Project', 'color_hex': '#2ecc71', 'is_completion_status': True, 'is_archival_status': False},  # Green
        {'status_name': 'Annulé', 'status_type': 'Project', 'color_hex': '#c0392b', 'is_completion_status': False, 'is_archival_status': True},   # Dark Red
        {'status_name': 'En pause', 'status_type': 'Project', 'color_hex': '#8e44ad', 'is_completion_status': False, 'is_archival_status': False}, # Purple

        # Task Statuses
        {'status_name': 'To Do', 'status_type': 'Task', 'color_hex': '#bdc3c7', 'is_completion_status': False, 'is_archival_status': False},      # Light Grey
        {'status_name': 'In Progress', 'status_type': 'Task', 'color_hex': '#3498db', 'is_completion_status': False, 'is_archival_status': False},# Blue
        {'status_name': 'Done', 'status_type': 'Task', 'color_hex': '#2ecc71', 'is_completion_status': True, 'is_archival_status': False},     # Green
        {'status_name': 'Blocked', 'status_type': 'Task', 'color_hex': '#e74c3c', 'is_completion_status': False, 'is_archival_status': False},    # Red
        {'status_name': 'Review', 'status_type': 'Task', 'color_hex': '#f1c40f', 'is_completion_status': False, 'is_archival_status': False},     # Yellow
        {'status_name': 'Cancelled', 'status_type': 'Task', 'color_hex': '#7f8c8d', 'is_completion_status': False, 'is_archival_status': True}   # Dark Grey
    ]

    for status in default_statuses:
        cursor.execute("""
            INSERT OR IGNORE INTO StatusSettings (
                status_name, status_type, color_hex, is_completion_status, is_archival_status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            status['status_name'], status['status_type'], status['color_hex'],
            status.get('is_completion_status', False),
            status.get('is_archival_status', False)
        ))

    # Create Clients table
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
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        position TEXT,
        company_name TEXT,
        notes TEXT,
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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL UNIQUE,
        description TEXT,
        category TEXT, 
        base_unit_price REAL NOT NULL,
        unit_of_measure TEXT, 
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # Create Templates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Templates (
        template_id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT NOT NULL,
        template_type TEXT NOT NULL, -- e.g., 'email', 'document_cover', 'report_section'
        description TEXT,
        base_file_name TEXT, -- e.g., 'invoice_template.docx'
        language_code TEXT, -- e.g., 'en_US', 'es_ES'
        is_default_for_type_lang BOOLEAN DEFAULT FALSE,
        category TEXT,
        content_definition TEXT, -- For simple templates, the content itself (e.g., HTML for email)
        email_subject_template TEXT,
        email_variables_info TEXT, -- JSON or text explaining available variables
        cover_page_config_json TEXT, -- JSON for document cover page configurations
        document_mapping_config_json TEXT, -- JSON for mapping data to document fields
        raw_template_file_data BLOB, -- For storing binary template files like .docx
        version TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by_user_id TEXT,
        FOREIGN KEY (created_by_user_id) REFERENCES Users (user_id),
        UNIQUE (template_name, template_type, language_code, version)
    )
    """)

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
                is_default_for_type_lang, category, content_definition, email_subject_template,
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
            template_data.get('category'),
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
        'is_default_for_type_lang' (optional, boolean, defaults to False)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        name = template_data.get('template_name')
        ttype = template_data.get('template_type')
        lang = template_data.get('language_code')
        filename = template_data.get('base_file_name')

        if not all([name, ttype, lang, filename]):
            print(f"Error: Missing required fields for default template: {template_data}")
            return None

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
                    description, category, is_default_for_type_lang,
                    created_at, updated_at
                    -- created_by_user_id could be NULL or a system user ID
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                name,
                ttype,
                lang,
                filename,
                template_data.get('description', f"Default {name} template"),
                template_data.get('category', "Général"),
                template_data.get('is_default_for_type_lang', True), # Make default templates the default for their type/lang
                now,
                now
            )
            cursor.execute(sql, params)
            conn.commit()
            new_id = cursor.lastrowid
            print(f"Added default template '{name}' ({ttype}, {lang}) with ID: {new_id}.")
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
        sql = """
            INSERT INTO Contacts (
                name, email, phone, position, company_name, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            contact_data.get('name'),
            contact_data.get('email'),
            contact_data.get('phone'),
            contact_data.get('position'),
            contact_data.get('company_name'),
            contact_data.get('notes'),
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
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Contacts"
        params = []
        where_clauses = []
        if filters:
            if 'company_name' in filters:
                where_clauses.append("company_name = ?")
                params.append(filters['company_name'])
            if 'name' in filters:
                where_clauses.append("name LIKE ?")
                params.append(f"%{filters['name']}%")
        
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
        
        set_clauses = [f"{key} = ?" for key in contact_data.keys()]
        params = list(contact_data.values())
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

# CRUD functions for Products
def add_product(product_data: dict) -> int | None:
    """Adds a new product. Returns product_id or None."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        sql = """
            INSERT INTO Products (
                product_name, description, category, base_unit_price, unit_of_measure, 
                is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            product_data.get('product_name'), product_data.get('description'),
            product_data.get('category'), product_data.get('base_unit_price'),
            product_data.get('unit_of_measure'), product_data.get('is_active', True),
            now, now
        )
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Database error in add_product: {e}")
        return None
    finally:
        if conn: conn.close()

def get_product_by_id(product_id: int) -> dict | None:
    """Retrieves a product by ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Products WHERE product_id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_product_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_product_by_name(product_name: str) -> dict | None:
    """Retrieves a product by its exact name. Returns a dict or None if not found."""
    conn = None
    if not product_name:
        return None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Products WHERE product_name = ?", (product_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Database error in get_product_by_name: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_all_products(filters: dict = None) -> list[dict]:
    """Retrieves all products. Filters by category (exact) or product_name (partial LIKE)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = "SELECT * FROM Products"
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
    """Updates an existing product. Sets updated_at."""
    conn = None
    if not product_data: return False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        product_data['updated_at'] = now
        
        set_clauses = [f"{key} = ?" for key in product_data.keys()]
        params = list(product_data.values())
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

# Functions for ClientProjectProducts association
def add_product_to_client_or_project(link_data: dict) -> int | None:
    """Links a product to a client or project, calculating total price."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        product_id = link_data.get('product_id')
        product_info = get_product_by_id(product_id) # Need this for base price
        if not product_info:
            print(f"Product with ID {product_id} not found.")
            return None

        quantity = link_data.get('quantity', 1)
        unit_price = link_data.get('unit_price_override', product_info['base_unit_price'])
        total_price_calculated = quantity * unit_price

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
            SELECT cpp.*, p.product_name, p.description as product_description, p.category as product_category, 
                   p.base_unit_price, p.unit_of_measure
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
        'style_config_json': {'font': 'Helvetica', 'primary_color': '#2a2a2a', 'secondary_color': '#5cb85c'}
    },
    {
        'template_name': 'Financial Statement Cover',
        'description': 'Cover page for official financial statements.',
        'default_title': 'Financial Statement',
        'default_subtitle': 'Fiscal Year Ending YYYY',
        'default_author': 'Finance Department',
        'style_config_json': {'font': 'Times New Roman', 'primary_color': '#003366', 'secondary_color': '#e0a800'}
    },
    {
        'template_name': 'Creative Project Brief',
        'description': 'A vibrant cover for creative project briefs and proposals.',
        'default_title': 'Creative Brief: [Project Name]',
        'default_subtitle': 'Client: [Client Name]',
        'default_author': 'Creative Team',
        'style_config_json': {'font': 'Montserrat', 'primary_color': '#ff6347', 'secondary_color': '#4682b4', 'layout_hint': 'two-column'}
    },
    {
        'template_name': 'Technical Document Cover',
        'description': 'A clean and formal cover for technical documentation.',
        'default_title': 'Technical Specification Document',
        'default_subtitle': 'Version [VersionNumber]',
        'default_author': 'Engineering Team',
        'style_config_json': {'font': 'Roboto', 'primary_color': '#191970', 'secondary_color': '#cccccc'}
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
                default_author, style_config_json, created_at, updated_at, created_by_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            new_template_id,
            template_data.get('template_name'),
            template_data.get('description'),
            template_data.get('default_title'),
            template_data.get('default_subtitle'),
            template_data.get('default_author'),
            style_config,
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

def get_all_cover_page_templates() -> list[dict]:
    """Retrieves all cover page templates."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CoverPageTemplates ORDER BY template_name")
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

        set_clauses = [f"{key} = ?" for key in update_data.keys() if key != 'template_id']
        params = [update_data[key] for key in update_data.keys() if key != 'template_id']
        params.append(template_id)

        sql = f"UPDATE CoverPageTemplates SET {', '.join(set_clauses)} WHERE template_id = ?"
        cursor.execute(sql, params)
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

def get_all_file_based_templates() -> list[dict]:
    """Retrieves all templates that have a base_file_name, suitable for document creation."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Selects templates that are likely file-based documents
        sql = "SELECT template_id, template_name, language_code, base_file_name, description, category FROM Templates WHERE base_file_name IS NOT NULL AND base_file_name != '' ORDER BY template_name, language_code"
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Database error in get_all_file_based_templates: {e}")
        return []
    finally:
        if conn: conn.close()

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
        sql = "SELECT * FROM StatusSettings"
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
        cursor.execute("SELECT * FROM StatusSettings WHERE status_id = ?", (status_id,))
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
        cursor.execute("SELECT * FROM StatusSettings WHERE status_name = ? AND status_type = ?", (status_name, status_type))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"DB error in get_status_setting_by_name: {e}")
        return None
    finally:
        if conn: conn.close()


if __name__ == '__main__':
    initialize_database()
    print(f"Database '{DATABASE_NAME}' initialized successfully with all tables, including Products, ClientProjectProducts, and Contacts PK/FK updates.")

    # Example Usage (Illustrative - uncomment and adapt to test)

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

    cpt1_id = add_cover_page_template({
        'template_name': 'Modern Minimalist',
        'description': 'A clean, modern template.',
        'default_title': 'Project Proposal',
        'default_subtitle': 'Prepared for [Client Name]',
        'default_author': 'Our Team',
        'style_config_json': {'font': 'Arial', 'primary_color': '#333333', 'secondary_color': '#007bff'},
        'created_by_user_id': cpt_user_id
    })
    if cpt1_id: print(f"Added Cover Page Template 'Modern Minimalist' ID: {cpt1_id}")

    cpt2_id = add_cover_page_template({'template_name': 'Classic Formal', 'default_title': 'Formal Report'})
    if cpt2_id: print(f"Added Cover Page Template 'Classic Formal' ID: {cpt2_id}")

    if cpt1_id:
        ret_cpt1 = get_cover_page_template_by_id(cpt1_id)
        print(f"Retrieved CPT by ID: {ret_cpt1['template_name'] if ret_cpt1 else 'Not found'}")
        ret_cpt_by_name = get_cover_page_template_by_name('Modern Minimalist')
        print(f"Retrieved CPT by Name: {ret_cpt_by_name['template_id'] if ret_cpt_by_name else 'Not found'}")

    all_cpts = get_all_cover_page_templates()
    print(f"All Cover Page Templates ({len(all_cpts)}):")
    for cpt in all_cpts:
        print(f"  - {cpt['template_name']} (Style: {cpt.get('style_config_json')})")

    if cpt1_id:
        update_cpt_success = update_cover_page_template(cpt1_id, {'description': 'Updated description for Modern Minimalist.'})
        print(f"Update CPT 'Modern Minimalist' success: {update_cpt_success}")

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
    if cp1_id: delete_cover_page(cp1_id)
    if cpt1_id: delete_cover_page_template(cpt1_id)
    if cpt2_id: delete_cover_page_template(cpt2_id)
    if cp_client_id: delete_client(cp_client_id) # Assumes client was created for this test
    if cpt_user_id: delete_user(cpt_user_id) # Assumes user was created for this test
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