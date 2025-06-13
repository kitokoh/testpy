import os
import sys
# Add the parent directory (project root) to sys.path
# os.path.dirname(__file__) is the directory of the current script (db)
# os.path.join(..., '..') goes one level up to the project root (/app)
# os.path.abspath ensures it's an absolute path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
import uuid
import hashlib
from datetime import datetime
import json

# Assuming config.py is in the parent directory (root)
from config import DATABASE_PATH
# Assuming config.py is in the parent directory (root)
from config import DATABASE_PATH

# Import necessary functions directly from their new CRUD module locations
from db.cruds.generic_crud import get_db_connection
# Make sure all imported CRUD functions expect 'conn' if called within a transaction, or manage their own.
from db.cruds import template_categories_crud # Changed to module import
from db.cruds import cover_page_templates_crud # Changed to module import
from db.cruds.users_crud import get_user_by_username
from db.cruds.locations_crud import add_country, get_country_by_name, add_city, get_city_by_name_and_country_id
from db.cruds.status_settings_crud import get_status_setting_by_name
from db.cruds import partners_crud # Added for partner category seeding
# Assuming company and company personnel functions will be imported if they were used via db_main_manager
# For now, let's assume they are not, or will be handled if errors arise.

# Path adjustments for db_seed.py located in db/
# __file__ is db/db_seed.py. os.path.dirname(__file__) is db/. os.pardir goes up one level.
APP_ROOT_DIR_CONTEXT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
LOGO_SUBDIR_CONTEXT = "company_logos" # This should match the setup

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
        return default_category_id

def set_setting(key: str, value: str, conn: sqlite3.Connection = None) -> bool: # Changed cursor to conn
    """
    Sets an application setting. Uses the provided connection if available,
    otherwise manages its own.
    """
    manage_connection = conn is None
    conn_to_use = conn

    try:
        if manage_connection:
            conn_to_use = get_db_connection() # Use imported function

        if not conn_to_use: # Ensure connection is valid
            print(f"DB error in set_setting for key '{key}': No valid connection.")
            return False

        cursor_to_use = conn_to_use.cursor()
        sql = "INSERT OR REPLACE INTO ApplicationSettings (setting_key, setting_value) VALUES (?, ?)"
        cursor_to_use.execute(sql, (key, value))

        if manage_connection: # Only commit if connection was created internally
            conn_to_use.commit()

        return cursor_to_use.rowcount > 0
    except sqlite3.Error as e:
        print(f"DB error in set_setting for key '{key}': {e}")
        if manage_connection and conn_to_use: # Rollback if connection was internal
            conn_to_use.rollback()
        return False
    finally:
        if manage_connection and conn_to_use: # Close if connection was internal
            conn_to_use.close()

def add_default_template_if_not_exists(template_data: dict, conn: sqlite3.Connection) -> int | None: # Changed cursor to conn
    """
    Adds a template to the Templates table if it doesn't already exist
    based on template_name, template_type, and language_code.
    Uses the provided connection and its cursor.
    Returns the template_id of the new or existing template, or None on error.
    """
    if not isinstance(conn, sqlite3.Connection):
        raise ValueError("Invalid connection object passed to add_default_template_if_not_exists.")

    cursor = conn.cursor() # Get cursor from connection

    try:
        name = template_data.get('template_name')
        ttype = template_data.get('template_type')
        lang = template_data.get('language_code')
        filename = template_data.get('base_file_name')
        category_name_text = template_data.get('category_name', "General")

        if not all([name, ttype, lang, filename]):
            print(f"Error: Missing required fields for default template: {template_data}")
            return None

        # Call add_template_category with the provided connection
        category_id = template_categories_crud.add_template_category(
            category_name_text,
            f"{category_name_text} (auto-created)",
            conn=conn # Pass the connection
        )
        if category_id is None:
            print(f"Error: Could not get or create category_id for '{category_name_text}' using provided connection.")
            return None

        cursor.execute("""
            SELECT template_id FROM Templates
            WHERE template_name = ? AND template_type = ? AND language_code = ?
        """, (name, ttype, lang))
        existing_template = cursor.fetchone()

        if existing_template:
            print(f"Default template '{name}' ({ttype}, {lang}) already exists with ID: {existing_template[0]}.")
            return existing_template[0]
        else:
            raw_template_content = None
            project_root = APP_ROOT_DIR_CONTEXT
            template_file_path = os.path.join(project_root, "email_template_designs", filename)

            if not os.path.exists(template_file_path):
                print(f"Warning: HTML template file {filename} not found at {template_file_path}. raw_template_file_data will be NULL.")
            else:
                try:
                    with open(template_file_path, 'r', encoding='utf-8') as f:
                        raw_template_content = f.read()
                    print(f"Successfully read content for {filename} from {template_file_path}")
                except Exception as e_read:
                    print(f"Error reading template file {filename} from {template_file_path}: {e_read}. raw_template_file_data will be NULL.")

            now = datetime.utcnow().isoformat() + "Z"
            # Ensure templates_crud.add_template expects `conn`
            from db.cruds import templates_crud # Ensure it's imported if not already at top
            new_id = templates_crud.add_template({
                **template_data, # Pass all original data
                'category_id': category_id, # Override with resolved category_id
                'raw_template_file_data': raw_template_content.encode('utf-8') if raw_template_content else None,
                'created_at': now, # Ensure these are set if add_template relies on them
                'updated_at': now
            }, conn=conn) # Pass the connection

            if new_id:
                 print(f"Added default template '{name}' ({ttype}, {lang}) with Category ID: {category_id}, new Template ID: {new_id}.")
            return new_id

    except sqlite3.Error as e:
        print(f"Database error in add_default_template_if_not_exists for '{template_data.get('template_name')}': {e}")
        return None

DEFAULT_COVER_PAGE_TEMPLATES = [
    {
        'template_name': 'Standard Report Cover',
        'description': 'A standard cover page for general reports.',
        'default_title': 'Report Title',
        'default_subtitle': 'Company Subdivision',
        'default_author': 'Automated Report Generator',
        'style_config_json': {'font': 'Helvetica', 'primary_color': '#2a2a2a', 'secondary_color': '#5cb85c'},
        'is_default_template': 1
    },
    {
        'template_name': 'Financial Statement Cover',
        'description': 'Cover page for official financial statements.',
        'default_title': 'Financial Statement',
        'default_subtitle': 'Fiscal Year Ending YYYY',
        'default_author': 'Finance Department',
        'style_config_json': {'font': 'Times New Roman', 'primary_color': '#003366', 'secondary_color': '#e0a800'},
        'is_default_template': 1
    },
    {
        'template_name': 'Creative Project Brief',
        'description': 'A vibrant cover for creative project briefs and proposals.',
        'default_title': 'Creative Brief: [Project Name]',
        'default_subtitle': 'Client: [Client Name]',
        'default_author': 'Creative Team',
        'style_config_json': {'font': 'Montserrat', 'primary_color': '#ff6347', 'secondary_color': '#4682b4', 'layout_hint': 'two-column'},
        'is_default_template': 1
    },
    {
        'template_name': 'Technical Document Cover',
        'description': 'A clean and formal cover for technical documentation.',
        'default_title': 'Technical Specification Document',
        'default_subtitle': 'Version [VersionNumber]',
        'default_author': 'Engineering Team',
        'style_config_json': {'font': 'Roboto', 'primary_color': '#191970', 'secondary_color': '#cccccc'},
        'is_default_template': 1
    }
]

def _populate_default_cover_page_templates(conn: sqlite3.Connection): # Changed cursor to conn
    """
    Populates the CoverPageTemplates table with predefined default templates
    if they do not already exist by name. Uses the provided connection.
    """
    if not isinstance(conn, sqlite3.Connection):
        raise ValueError("Invalid connection object passed to _populate_default_cover_page_templates.")

    print("Attempting to populate default cover page templates...")
    for template_def in DEFAULT_COVER_PAGE_TEMPLATES:
        # Use get_cover_page_template_by_name with the passed connection
        existing_template = cover_page_templates_crud.get_cover_page_template_by_name(template_def['template_name'], conn=conn)
        if existing_template:
            print(f"Default template '{template_def['template_name']}' already exists. Skipping.")
        else:
            # Pass the connection to add_cover_page_template
            new_id = cover_page_templates_crud.add_cover_page_template(template_def, conn=conn)
            if new_id:
                print(f"Added default cover page template: '{template_def['template_name']}' with ID: {new_id}")
            else:
                print(f"Failed to add default cover page template: '{template_def['template_name']}'")
    print("Default cover page templates population attempt finished.")

def _seed_default_partner_categories(conn: sqlite3.Connection): # Changed cursor to conn
    """Seeds default partner categories into the database using the provided connection."""
    print("Attempting to seed default partner categories...")
    default_categories = [
        {'category_name': 'Supplier', 'description': 'Providers of goods and materials.'},
        {'category_name': 'Service Provider', 'description': 'Companies offering services.'},
        {'category_name': 'Technology Partner', 'description': 'Partners providing technology solutions.'},
        {'category_name': 'Consultant', 'description': 'External consultants and advisors.'},
        {'category_name': 'Distributor', 'description': 'Entities distributing products.'}
    ]

    for category_def in default_categories:
        # Pass the connection to CRUD functions
        existing_category = partners_crud.get_partner_category_by_name(category_def['category_name'], conn=conn)
        if existing_category:
            print(f"Partner Category '{category_def['category_name']}' already exists with ID: {existing_category['partner_category_id']}. Skipping.")
        else:
            category_data_dict = {
                'category_name': category_def['category_name'],
                'description': category_def.get('description')
            }
            category_id = partners_crud.add_partner_category(category_data_dict, conn=conn)
            if category_id:
                print(f"Partner Category '{category_def['category_name']}' added with ID: {category_id}")
            else:
                print(f"Warning: Could not add partner category '{category_def['category_name']}'. Check logs from partners_crud.")
    print("Default partner categories seeding attempt finished.")

def seed_initial_data(conn: sqlite3.Connection): # Changed cursor to conn
    """
    Seeds the database with initial data using the provided connection.
    All database operations within this function and any helper functions it calls
    must use this provided connection and get their own cursors.
    """
    cursor = conn.cursor() # Obtain cursor from connection
    try:
        # 1. Users
        cursor.execute("SELECT COUNT(*) FROM Users")
        if cursor.fetchone()[0] == 0:
            admin_user_id = str(uuid.uuid4())
            admin_password_hash = hashlib.sha256('adminpassword'.encode('utf-8')).hexdigest()
            cursor.execute("""
                INSERT OR IGNORE INTO Users (user_id, username, password_hash, full_name, email, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (admin_user_id, 'admin', admin_password_hash, 'Default Admin', 'admin@example.com', 'admin', True))
            print("Seeded admin user.")

        # 2. Companies
        default_company_id = None
        cursor.execute("SELECT COUNT(*) FROM Companies")
        if cursor.fetchone()[0] == 0:
            default_company_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT OR IGNORE INTO Companies (company_id, company_name, address, is_default)
                VALUES (?, ?, ?, ?)
            """, (default_company_id, "Default Company Inc.", "123 Default Street", True))
            print("Seeded default company.")
        else:
            cursor.execute("SELECT company_id FROM Companies WHERE is_default = TRUE")
            row = cursor.fetchone()
            if row:
                default_company_id = row[0]

        # 3. CompanyPersonnel
        if default_company_id:
            cursor.execute("SELECT COUNT(*) FROM CompanyPersonnel WHERE company_id = ?", (default_company_id,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT OR IGNORE INTO CompanyPersonnel (company_id, name, role, email, phone)
                    VALUES (?, ?, ?, ?, ?)
                """, (default_company_id, "Admin Contact", "Administrator", "contact@defaultcomp.com", "123-456-7890"))
                print("Seeded default company personnel.")

        # 4. TeamMembers
        # Pass conn to get_user_by_username
        admin_user_for_tm_dict = get_user_by_username('admin', conn=conn)
        if admin_user_for_tm_dict:
            admin_user_id_for_tm = admin_user_for_tm_dict['user_id']
            cursor.execute("SELECT COUNT(*) FROM TeamMembers WHERE user_id = ?", (admin_user_id_for_tm,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT OR IGNORE INTO TeamMembers (user_id, full_name, email, role_or_title)
                    VALUES (?, ?, ?, ?)
                """, (admin_user_id_for_tm, admin_user_for_tm_dict['full_name'], admin_user_for_tm_dict['email'], admin_user_for_tm_dict['role']))
                print("Seeded admin team member.")
        else:
             print("Admin user not found, cannot seed admin team member.")

        # 5. Countries
        default_countries = [
            {'country_name': 'France', 'country_code': 'FR'},
            {'country_name': 'USA', 'country_code': 'US'},
            {'country_name': 'Algeria', 'country_code': 'DZ'}
        ]
        for country_data in default_countries:
            # Pass conn to add_country
            add_country(country_data, conn=conn)
        print(f"Seeded {len(default_countries)} countries.")

        # 6. Cities
        default_cities_map = {
            'France': 'Paris', 'USA': 'New York', 'Algeria': 'Algiers'
        }
        for country_name, city_name in default_cities_map.items():
            # Pass conn to get_country_by_name and add_city
            country_row_dict = get_country_by_name(country_name, conn=conn)
            if country_row_dict:
                country_id = country_row_dict['country_id']
                add_city({'country_id': country_id, 'city_name': city_name}, conn=conn)
        print(f"Seeded {len(default_cities_map)} cities.")

        # 7. Clients
        cursor.execute("SELECT COUNT(*) FROM Clients")
        if cursor.fetchone()[0] == 0:
            admin_user_for_client_dict = get_user_by_username('admin', conn=conn)
            default_country_for_client_dict = get_country_by_name('France', conn=conn)
            admin_user_id_for_client = admin_user_for_client_dict['user_id'] if admin_user_for_client_dict else None
            default_country_id_for_client = default_country_for_client_dict['country_id'] if default_country_for_client_dict else None
            default_city_id_for_client = None
            if default_country_id_for_client:
                city_client_dict = get_city_by_name_and_country_id('Paris', default_country_id_for_client, conn=conn)
                if city_client_dict: default_city_id_for_client = city_client_dict['city_id']
            active_client_status_dict = get_status_setting_by_name('Actif', 'Client', conn=conn)
            active_client_status_id = active_client_status_dict['status_id'] if active_client_status_dict else None

            if admin_user_id_for_client and default_country_id_for_client and default_city_id_for_client and active_client_status_id:
                client_uuid = str(uuid.uuid4())
                cursor.execute("""
                    INSERT OR IGNORE INTO Clients (client_id, client_name, company_name, project_identifier, country_id, city_id, status_id, created_by_user_id, default_base_folder_path, primary_need_description, selected_languages)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (client_uuid, "Sample Client SARL", "Sample Client Company", "SC-PROJ-001", default_country_id_for_client, default_city_id_for_client, active_client_status_id, admin_user_id_for_client, f"clients/{client_uuid}", "General business services", "en,fr"))
                print("Seeded sample client.")
            else:
                print("Could not seed sample client due to missing prerequisite data (admin user, country, city, or status).")

        # 8. Projects
        cursor.execute("SELECT COUNT(*) FROM Projects")
        if cursor.fetchone()[0] == 0:
            sample_client_id_for_proj = None
            cursor.execute("SELECT client_id FROM Clients WHERE client_name = 'Sample Client SARL'")
            sample_client_proj_row = cursor.fetchone()
            if sample_client_proj_row: sample_client_id_for_proj = sample_client_proj_row[0]
            planning_project_status_dict = get_status_setting_by_name('Planning', 'Project', conn=conn)
            planning_project_status_id = planning_project_status_dict['status_id'] if planning_project_status_dict else None
            admin_user_for_project_dict = get_user_by_username('admin', conn=conn)
            admin_user_id_for_project = admin_user_for_project_dict['user_id'] if admin_user_for_project_dict else None

            if sample_client_id_for_proj and planning_project_status_id and admin_user_id_for_project:
                project_uuid = str(uuid.uuid4())
                cursor.execute("""
                    INSERT OR IGNORE INTO Projects (project_id, client_id, project_name, description, status_id, manager_team_member_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (project_uuid, sample_client_id_for_proj, "Initial Project for Sample Client", "First project description.", planning_project_status_id, admin_user_id_for_project))
                print("Seeded sample project.")
            else:
                print("Could not seed sample project due to missing prerequisite data.")

        # 9. Contacts
        cursor.execute("SELECT COUNT(*) FROM Contacts WHERE email = 'contact@example.com'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT OR IGNORE INTO Contacts (name, email, phone, position, company_name)
                VALUES (?, ?, ?, ?, ?)
            """, ("Placeholder Contact", "contact@example.com", "555-1234", "General Contact", "VariousCompanies Inc."))
            print("Seeded generic contact.")

        # 10. Products
        cursor.execute("SELECT COUNT(*) FROM Products WHERE product_name = 'Default Product'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT OR IGNORE INTO Products (product_name, description, category, language_code, base_unit_price, unit_of_measure, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("Default Product", "This is a default product for testing and demonstration.", "General", "en", 10.00, "unit", True))
            print("Seeded default product.")

        # 11. SmtpConfigs
        cursor.execute("SELECT COUNT(*) FROM SmtpConfigs")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT OR IGNORE INTO SmtpConfigs (config_name, smtp_server, smtp_port, username, password_encrypted, use_tls, is_default, sender_email_address, sender_display_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("Placeholder - Configure Me", "smtp.example.com", 587, "user", "placeholder_password", True, True, "noreply@example.com", "Placeholder Email"))
            print("Seeded placeholder SMTP config.")

        # 12. ApplicationSettings (pass conn to set_setting)
        set_setting('initial_data_seeded_version', '1.1', conn=conn) # Pass conn
        set_setting('default_app_language', 'en', conn=conn) # Pass conn
        set_setting('google_maps_review_url', 'https://maps.google.com/?cid=YOUR_CID_HERE', conn=conn) # Pass conn
        print("Seeded application settings.")

        # 13. Email Templates (pass conn to add_default_template_if_not_exists)
        add_default_template_if_not_exists({
            'template_name': 'SAV Ticket Ouvert (FR)', 'template_type': 'email_sav_ticket_opened', 'language_code': 'fr',
            'base_file_name': 'sav_ticket_opened_fr.html', 'description': 'Email envoyé quand un ticket SAV est ouvert.',
            'category_name': 'Modèles Email SAV',
            'email_subject_template': 'Ticket SAV #{{ticket.id}} Ouvert - {{project.name | default: "Référence Client"}}',
            'is_default_for_type_lang': True
        }, conn=conn) # Pass conn
        add_default_template_if_not_exists({
            'template_name': 'SAV Ticket Résolu (FR)', 'template_type': 'email_sav_ticket_resolved', 'language_code': 'fr',
            'base_file_name': 'sav_ticket_resolved_fr.html', 'description': 'Email envoyé quand un ticket SAV est résolu.',
            'category_name': 'Modèles Email SAV',
            'email_subject_template': 'Ticket SAV #{{ticket.id}} Résolu - {{project.name | default: "Référence Client"}}',
            'is_default_for_type_lang': True
        }, conn=conn) # Pass conn
        # ... (apply conn=conn to all other add_default_template_if_not_exists calls) ...
        add_default_template_if_not_exists({
            'template_name': 'Suivi Prospect Proforma (FR)', 'template_type': 'email_follow_up_prospect', 'language_code': 'fr',
            'base_file_name': 'follow_up_prospect_fr.html', 'description': 'Email de suivi pour un prospect ayant reçu une proforma.',
            'category_name': 'Modèles Email Marketing/Suivi',
            'email_subject_template': 'Suite à votre demande de proforma : {{project.name | default: client.primary_need}}',
            'is_default_for_type_lang': True
        }, conn=conn)
        add_default_template_if_not_exists({
            'template_name': 'Vœux Noël (FR)', 'template_type': 'email_greeting_christmas', 'language_code': 'fr',
            'base_file_name': 'greeting_holiday_christmas_fr.html', 'description': 'Email de vœux pour Noël.',
            'category_name': 'Modèles Email Vœux',
            'email_subject_template': 'Joyeux Noël de la part de {{seller.company_name}}!',
            'is_default_for_type_lang': True
        }, conn=conn)
        add_default_template_if_not_exists({
            'template_name': 'Vœux Nouvelle Année (FR)', 'template_type': 'email_greeting_newyear', 'language_code': 'fr',
            'base_file_name': 'greeting_holiday_newyear_fr.html', 'description': 'Email de vœux pour la nouvelle année.',
            'category_name': 'Modèles Email Vœux',
            'email_subject_template': 'Bonne Année {{doc.current_year}} ! - {{seller.company_name}}',
            'is_default_for_type_lang': True
        }, conn=conn)
        add_default_template_if_not_exists({
            'template_name': 'Message Générique (FR)', 'template_type': 'email_generic_message', 'language_code': 'fr',
            'base_file_name': 'generic_message_fr.html', 'description': 'Modèle générique pour communication spontanée.',
            'category_name': 'Modèles Email Généraux',
            'email_subject_template': 'Un message de {{seller.company_name}}',
            'is_default_for_type_lang': True
        }, conn=conn)
        print("Seeded new email templates.")

        # 14. CoverPageTemplates (pass conn to _populate_default_cover_page_templates)
        _populate_default_cover_page_templates(conn=conn) # Pass conn
        print("Called _populate_default_cover_page_templates for seeding.")

        # 15. Partner Categories (pass conn to _seed_default_partner_categories)
        _seed_default_partner_categories(conn=conn) # Pass conn
        print("Called _seed_default_partner_categories for seeding.")

        print("Data seeding operations completed within seed_initial_data.")

    except sqlite3.Error as e:
        print(f"An error occurred during data seeding within seed_initial_data: {e}")
        raise # Re-raise to be caught by run_seed for rollback

def run_seed():
    print(f"Attempting to seed database: {DATABASE_PATH}")
    conn = None
    try:
        conn = get_db_connection()
        # Changed: seed_initial_data now takes conn directly
        seed_initial_data(conn)
        conn.commit() # Commit the overall transaction
        print("Seeding process completed and committed.")
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error during seeding process: {e}")
        # Optionally re-raise e or handle more gracefully
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # This allows running the seed script directly for testing or initial setup
    # Note: db_main_manager.initialize_database() should typically be called before seeding
    # if the database schema itself might not exist.
    # However, run_seed() assumes the schema is already in place.

    # First, ensure the database and tables are created by calling initialize_database
    print("Ensuring database schema is initialized before seeding...")
    from db.ca import initialize_database # Import as per subtask instruction
    initialize_database()
    print("Database schema initialization check complete.")

    run_seed()
