import os
import sqlite3
import uuid
import hashlib
from datetime import datetime
import json

# Assuming config.py is in the parent directory (root)
from ..config import DATABASE_PATH
# Assuming db.py is in the parent directory (root)
from .. import db as db_main_manager

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
        # Depending on how critical this is, you might want to raise the error
        # or return the default_category_id as a fallback.
        return default_category_id

def set_setting(key: str, value: str, cursor: sqlite3.Cursor = None) -> bool:
    """
    Sets an application setting. Uses the provided cursor if available,
    otherwise manages its own connection.
    """
    manage_connection = cursor is None
    conn_internal = None
    try:
        if manage_connection:
            conn_internal = db_main_manager.get_db_connection() # Use main manager for connection
            cursor_to_use = conn_internal.cursor()
        else:
            if not isinstance(cursor, sqlite3.Cursor):
                raise ValueError("Invalid cursor object passed to set_setting.")
            cursor_to_use = cursor

        sql = "INSERT OR REPLACE INTO ApplicationSettings (setting_key, setting_value) VALUES (?, ?)"
        cursor_to_use.execute(sql, (key, value))

        if manage_connection and conn_internal:
            conn_internal.commit()

        return cursor_to_use.rowcount > 0 # Should be > 0 on success
    except sqlite3.Error as e:
        print(f"DB error in set_setting for key '{key}': {e}")
        if manage_connection and conn_internal:
            conn_internal.rollback()
        return False
    finally:
        if manage_connection and conn_internal:
            conn_internal.close()

def add_default_template_if_not_exists(template_data: dict, cursor: sqlite3.Cursor) -> int | None:
    """
    Adds a template to the Templates table if it doesn't already exist
    based on template_name, template_type, and language_code.
    Uses the provided cursor and does not manage connection or transaction.
    Returns the template_id of the new or existing template, or None on error.
    """
    if not isinstance(cursor, sqlite3.Cursor):
        raise ValueError("Invalid cursor object passed to add_default_template_if_not_exists.")

    try:
        name = template_data.get('template_name')
        ttype = template_data.get('template_type')
        lang = template_data.get('language_code')
        filename = template_data.get('base_file_name')
        category_name_text = template_data.get('category_name', "General")

        if not all([name, ttype, lang, filename]):
            print(f"Error: Missing required fields for default template: {template_data}")
            return None

        # Call add_template_category with the provided cursor, using db_main_manager
        category_id = db_main_manager.add_template_category(category_name_text,
                                            f"{category_name_text} (auto-created)",
                                            cursor=cursor) # Pass the cursor
        if category_id is None:
            print(f"Error: Could not get or create category_id for '{category_name_text}' using provided cursor.")
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
            # Corrected path logic for files within the main project structure
            project_root = APP_ROOT_DIR_CONTEXT # app_root_dir is already parent of db/

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
            sql_insert_template = """
                INSERT INTO Templates (
                    template_name, template_type, language_code, base_file_name,
                    description, category_id, is_default_for_type_lang,
                    email_subject_template, raw_template_file_data,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params_template = (
                name, ttype, lang, filename,
                template_data.get('description', f"Default {name} template"),
                category_id,
                template_data.get('is_default_for_type_lang', True),
                template_data.get('email_subject_template'),
                raw_template_content.encode('utf-8') if raw_template_content else None,
                now, now
            )
            cursor.execute(sql_insert_template, params_template)
            # No commit here, handled by the caller managing the transaction
            new_id = cursor.lastrowid
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

def _populate_default_cover_page_templates(cursor: sqlite3.Cursor):
    """
    Populates the CoverPageTemplates table with predefined default templates
    if they do not already exist by name. Uses the provided cursor.
    """
    if not isinstance(cursor, sqlite3.Cursor):
        raise ValueError("Invalid cursor object passed to _populate_default_cover_page_templates.")

    print("Attempting to populate default cover page templates...")
    for template_def in DEFAULT_COVER_PAGE_TEMPLATES:
        # Use get_cover_page_template_by_name with the passed cursor, from db_main_manager
        existing_template = db_main_manager.get_cover_page_template_by_name(template_def['template_name'], cursor=cursor)
        if existing_template:
            print(f"Default template '{template_def['template_name']}' already exists. Skipping.")
        else:
            # Pass the cursor to add_cover_page_template, from db_main_manager
            new_id = db_main_manager.add_cover_page_template(template_def, cursor=cursor)
            if new_id:
                print(f"Added default cover page template: '{template_def['template_name']}' with ID: {new_id}")
            else:
                print(f"Failed to add default cover page template: '{template_def['template_name']}'")
    print("Default cover page templates population attempt finished.")

def seed_initial_data(cursor: sqlite3.Cursor):
    """
    Seeds the database with initial data using the provided cursor.
    All database operations within this function and any helper functions it calls
    must use this provided cursor.
    """
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
        admin_user_for_tm_dict = db_main_manager.get_user_by_username('admin')
        if admin_user_for_tm_dict:
            admin_user_id_for_tm = admin_user_for_tm_dict['user_id']
            # Check using cursor if team member already exists for this user_id
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
            {'country_name': 'France'}, {'country_name': 'USA'}, {'country_name': 'Algeria'}
        ]
        for country_data in default_countries:
            db_main_manager.add_country(country_data)
        print(f"Seeded {len(default_countries)} countries (using db_main_manager.add_country).")


        # 6. Cities
        default_cities_map = {
            'France': 'Paris', 'USA': 'New York', 'Algeria': 'Algiers'
        }
        for country_name, city_name in default_cities_map.items():
            country_row_dict = db_main_manager.get_country_by_name(country_name)
            if country_row_dict:
                country_id = country_row_dict['country_id']
                db_main_manager.add_city({'country_id': country_id, 'city_name': city_name})
        print(f"Seeded {len(default_cities_map)} cities (using db_main_manager.add_city).")

        # 7. Clients
        # Using db_main_manager for gets, and direct cursor for insert if it's the first client
        cursor.execute("SELECT COUNT(*) FROM Clients")
        if cursor.fetchone()[0] == 0:
            admin_user_for_client_dict = db_main_manager.get_user_by_username('admin')
            default_country_for_client_dict = db_main_manager.get_country_by_name('France')

            admin_user_id_for_client = admin_user_for_client_dict['user_id'] if admin_user_for_client_dict else None
            default_country_id_for_client = default_country_for_client_dict['country_id'] if default_country_for_client_dict else None

            default_city_id_for_client = None
            if default_country_id_for_client:
                city_client_dict = db_main_manager.get_city_by_name_and_country_id('Paris', default_country_id_for_client)
                if city_client_dict: default_city_id_for_client = city_client_dict['city_id']

            active_client_status_dict = db_main_manager.get_status_setting_by_name('Actif', 'Client')
            active_client_status_id = active_client_status_dict['status_id'] if active_client_status_dict else None

            if admin_user_id_for_client and default_country_id_for_client and default_city_id_for_client and active_client_status_id:
                client_uuid = str(uuid.uuid4())
                cursor.execute("""
                    INSERT OR IGNORE INTO Clients (client_id, client_name, company_name, project_identifier, country_id, city_id, status_id, created_by_user_id, default_base_folder_path, primary_need_description, selected_languages)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (client_uuid, "Sample Client SARL", "Sample Client Company", "SC-PROJ-001", default_country_id_for_client, default_city_id_for_client, active_client_status_id, admin_user_id_for_client, f"clients/{client_uuid}", "General business services", "en,fr"))
                print("Seeded sample client.")
            else:
                print("Could not seed sample client due to missing prerequisite data from db_main_manager calls (admin user, country, city, or status).")

        # 8. Projects
        cursor.execute("SELECT COUNT(*) FROM Projects")
        if cursor.fetchone()[0] == 0:
            sample_client_id_for_proj = None
            # Get client_id using a direct cursor query if it was just seeded
            cursor.execute("SELECT client_id FROM Clients WHERE client_name = 'Sample Client SARL'")
            sample_client_proj_row = cursor.fetchone()
            if sample_client_proj_row: sample_client_id_for_proj = sample_client_proj_row[0]

            planning_project_status_dict = db_main_manager.get_status_setting_by_name('Planning', 'Project')
            planning_project_status_id = planning_project_status_dict['status_id'] if planning_project_status_dict else None

            admin_user_for_project_dict = db_main_manager.get_user_by_username('admin')
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

        # 9. Contacts (direct cursor)
        cursor.execute("SELECT COUNT(*) FROM Contacts WHERE email = 'contact@example.com'")
        if cursor.fetchone()[0] == 0:
                cursor.execute("""
                INSERT OR IGNORE INTO Contacts (name, email, phone, position, company_name)
                VALUES (?, ?, ?, ?, ?)
            """, ("Placeholder Contact", "contact@example.com", "555-1234", "General Contact", "VariousCompanies Inc."))
                print("Seeded generic contact.")

        # 10. Products (direct cursor)
        cursor.execute("SELECT COUNT(*) FROM Products WHERE product_name = 'Default Product'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT OR IGNORE INTO Products (product_name, description, category, language_code, base_unit_price, unit_of_measure, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("Default Product", "This is a default product for testing and demonstration.", "General", "en", 10.00, "unit", True))
            print("Seeded default product.")

        # 11. SmtpConfigs (direct cursor)
        cursor.execute("SELECT COUNT(*) FROM SmtpConfigs")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT OR IGNORE INTO SmtpConfigs (config_name, smtp_server, smtp_port, username, password_encrypted, use_tls, is_default, sender_email_address, sender_display_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("Placeholder - Configure Me", "smtp.example.com", 587, "user", "placeholder_password", True, True, "noreply@example.com", "Placeholder Email"))
            print("Seeded placeholder SMTP config.")

        # 12. ApplicationSettings (using local set_setting which uses the passed cursor)
        set_setting('initial_data_seeded_version', '1.1', cursor)
        set_setting('default_app_language', 'en', cursor)
        set_setting('google_maps_review_url', 'https://maps.google.com/?cid=YOUR_CID_HERE', cursor)
        print("Seeded application settings.")

        # 13. Email Templates (using local add_default_template_if_not_exists)
        add_default_template_if_not_exists({
            'template_name': 'SAV Ticket Ouvert (FR)', 'template_type': 'email_sav_ticket_opened', 'language_code': 'fr',
            'base_file_name': 'sav_ticket_opened_fr.html', 'description': 'Email envoyé quand un ticket SAV est ouvert.',
            'category_name': 'Modèles Email SAV',
            'email_subject_template': 'Ticket SAV #{{ticket.id}} Ouvert - {{project.name | default: "Référence Client"}}',
            'is_default_for_type_lang': True
        }, cursor)
        add_default_template_if_not_exists({
            'template_name': 'SAV Ticket Résolu (FR)', 'template_type': 'email_sav_ticket_resolved', 'language_code': 'fr',
            'base_file_name': 'sav_ticket_resolved_fr.html', 'description': 'Email envoyé quand un ticket SAV est résolu.',
            'category_name': 'Modèles Email SAV',
            'email_subject_template': 'Ticket SAV #{{ticket.id}} Résolu - {{project.name | default: "Référence Client"}}',
            'is_default_for_type_lang': True
        }, cursor)
        add_default_template_if_not_exists({
            'template_name': 'Suivi Prospect Proforma (FR)', 'template_type': 'email_follow_up_prospect', 'language_code': 'fr',
            'base_file_name': 'follow_up_prospect_fr.html', 'description': 'Email de suivi pour un prospect ayant reçu une proforma.',
            'category_name': 'Modèles Email Marketing/Suivi',
            'email_subject_template': 'Suite à votre demande de proforma : {{project.name | default: client.primary_need}}',
            'is_default_for_type_lang': True
        }, cursor)
        add_default_template_if_not_exists({
            'template_name': 'Vœux Noël (FR)', 'template_type': 'email_greeting_christmas', 'language_code': 'fr',
            'base_file_name': 'greeting_holiday_christmas_fr.html', 'description': 'Email de vœux pour Noël.',
            'category_name': 'Modèles Email Vœux',
            'email_subject_template': 'Joyeux Noël de la part de {{seller.company_name}}!',
            'is_default_for_type_lang': True
        }, cursor)
        add_default_template_if_not_exists({
            'template_name': 'Vœux Nouvelle Année (FR)', 'template_type': 'email_greeting_newyear', 'language_code': 'fr',
            'base_file_name': 'greeting_holiday_newyear_fr.html', 'description': 'Email de vœux pour la nouvelle année.',
            'category_name': 'Modèles Email Vœux',
            'email_subject_template': 'Bonne Année {{doc.current_year}} ! - {{seller.company_name}}',
            'is_default_for_type_lang': True
        }, cursor)
        add_default_template_if_not_exists({
            'template_name': 'Message Générique (FR)', 'template_type': 'email_generic_message', 'language_code': 'fr',
            'base_file_name': 'generic_message_fr.html', 'description': 'Modèle générique pour communication spontanée.',
            'category_name': 'Modèles Email Généraux',
            'email_subject_template': 'Un message de {{seller.company_name}}',
            'is_default_for_type_lang': True
        }, cursor)
        print("Seeded new email templates.")

        # 14. CoverPageTemplates (using local _populate_default_cover_page_templates)
        _populate_default_cover_page_templates(cursor)
        print("Called _populate_default_cover_page_templates for seeding.")

        print("Data seeding operations completed within seed_initial_data.")

    except sqlite3.Error as e:
        print(f"An error occurred during data seeding within seed_initial_data: {e}")
        raise

def run_seed():
    print(f"Attempting to seed database: {DATABASE_PATH}")
    conn = None
    try:
        # Use the get_db_connection from the main db.py (via db_main_manager)
        conn = db_main_manager.get_db_connection()
        cursor = conn.cursor()
        seed_initial_data(cursor) # Call the local seed_initial_data
        conn.commit()
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

    # First, ensure the database and tables are created by calling initialize_database from the main module
    print("Ensuring database schema is initialized before seeding...")
    db_main_manager.initialize_database()
    print("Database schema initialization check complete.")

    run_seed()
