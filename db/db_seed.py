import os
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

# Import CRUD instances for refactored modules
from db.cruds.users_crud import users_crud_instance
from db.cruds.clients_crud import clients_crud_instance
from db.cruds.products_crud import products_crud_instance

# Imports for non-refactored or utility functions used in seeding
from db.cruds.template_categories_crud import add_template_category
from db.cruds.cover_page_templates_crud import get_cover_page_template_by_name, add_cover_page_template
# get_user_by_username will be called via users_crud_instance if needed for seeding logic outside Users table itself
from db.cruds.locations_crud import add_country, get_country_by_name, add_city, get_city_by_name_and_country_id
from db.cruds.status_settings_crud import get_status_setting_by_name
from db.cruds import partners_crud
# Assuming company and company personnel functions will be imported if they were used via db_main_manager
# For now, let's assume they are not, or will be handled if errors arise.

# Path adjustments for db_seed.py located in db/
# __file__ is db/db_seed.py. os.path.dirname(__file__) is db/. os.pardir goes up one level.
APP_ROOT_DIR_CONTEXT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
LOGO_SUBDIR_CONTEXT = "company_logos" # This should match the setup

# Redundant local helper functions and data are removed.
# _get_or_create_category_id, set_setting, add_default_template_if_not_exists,
# DEFAULT_COVER_PAGE_TEMPLATES, and _populate_default_cover_page_templates
# are now expected to be handled by init_schema.py or imported CRUD modules.

# Ensure add_default_template_if_not_exists is imported if used by seed_initial_data directly
# (It is used, so ensure it's available from db.cruds.templates_crud)
from db.cruds.templates_crud import add_default_template_if_not_exists
# Ensure set_setting is imported if used by seed_initial_data directly
# (It is used, so ensure it's available from db.cruds.application_settings_crud)
from db.cruds.application_settings_crud import set_setting


def _seed_default_partner_categories(cursor: sqlite3.Cursor):
    """Seeds default partner categories into the database."""
    print("Attempting to seed default partner categories...")
    default_categories = [
        {'category_name': 'Supplier', 'description': 'Providers of goods and materials.'},
        {'category_name': 'Service Provider', 'description': 'Companies offering services.'},
        {'category_name': 'Technology Partner', 'description': 'Partners providing technology solutions.'},
        {'category_name': 'Consultant', 'description': 'External consultants and advisors.'},
        {'category_name': 'Distributor', 'description': 'Entities distributing products.'}
    ]

    for category_def in default_categories:
        # Using the get_or_add_partner_category from partners_crud which handles connection management
        # and checks if category already exists. We pass the cursor to ensure it's part of the same transaction.
        # Note: get_or_add_partner_category expects 'conn_or_cursor' to be a Connection object
        # if it's going to manage the transaction itself. If a cursor is passed, it assumes
        # the transaction is managed externally (which is the case here in db_seed.py).
        # The @_manage_conn decorator in partners_crud.py needs to be aware of this.
        # For simplicity, let's assume `get_or_add_partner_category` is adapted or correctly
        # handles a passed cursor without trying to call .commit() or .rollback() on it.
        # A direct call to add_partner_category after a check might be cleaner if get_or_add isn't flexible.

        # Check if category exists using the cursor directly
        # Ensure partners_crud.get_partner_category_by_name can accept a cursor
        existing_category_row = partners_crud.get_partner_category_by_name(category_def['category_name'], cursor=cursor)

        if existing_category_row: # Check if it's not None
            print(f"Partner Category '{category_def['category_name']}' already exists with ID: {existing_category_row['partner_category_id']}. Skipping.")
        else:
            # Add category using the cursor directly
            # Ensure partners_crud.add_partner_category can accept a cursor
            category_id = partners_crud.add_partner_category(category_def, cursor=cursor)
            if category_id:
                print(f"Partner Category '{category_def['category_name']}' added with ID: {category_id}")
            else:
                print(f"Warning: Could not add partner category '{category_def['category_name']}'. Check logs from partners_crud.")
    print("Default partner categories seeding attempt finished.")

def seed_initial_data(cursor: sqlite3.Cursor):
    """
    Seeds the database with initial data using the provided cursor.
    All database operations within this function and any helper functions it calls
    must use this provided cursor.
    """
    try:
        # 1. Users
        # Use users_crud_instance.add_user for seeding users
        # Connection will be passed to the instance method from run_seed()
        conn = cursor.connection # Get connection from cursor for instance methods

        cursor.execute("SELECT COUNT(*) FROM Users")
        if cursor.fetchone()[0] == 0:
            admin_user_data = {
                'username': 'admin',
                'password': 'adminpassword', # Plain text, add_user will hash it
                'full_name': 'Default Admin',
                'email': 'admin@example.com',
                'role': 'admin', # Assuming SUPER_ADMIN or similar role defined elsewhere
                'is_active': True
            }
            add_user_result = users_crud_instance.add_user(admin_user_data, conn=conn)
            if add_user_result['success']:
                admin_user_id = add_user_result['id']
                print(f"Seeded admin user with ID: {admin_user_id}")
            else:
                print(f"Failed to seed admin user: {add_user_result.get('error')}")
                admin_user_id = None # Ensure it's None if seeding failed
        else:
            # If admin user might already exist from init_schema, try to get its ID
            # This assumes init_schema.py seeds the admin user if Users table is empty.
            admin_user_dict = users_crud_instance.get_user_by_username('admin', conn=conn, internal_use=False) # Don't need hash/salt here
            admin_user_id = admin_user_dict['user_id'] if admin_user_dict else None
            if admin_user_id:
                 print(f"Admin user 'admin' already exists with ID: {admin_user_id}.")
            else:
                 print("Warning: Admin user not found and Users table was not empty. Seeding might rely on this user.")


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
        # admin_user_id obtained from user seeding step above
        if admin_user_id: # Check if admin_user_id was successfully obtained
            admin_user_for_tm_dict = users_crud_instance.get_user_by_id(admin_user_id, conn=conn) # Fetch details if needed
            if admin_user_for_tm_dict:
                 # Check using cursor if team member already exists for this user_id
                cursor.execute("SELECT COUNT(*) FROM TeamMembers WHERE user_id = ?", (admin_user_id,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        INSERT OR IGNORE INTO TeamMembers (user_id, full_name, email, role_or_title)
                        VALUES (?, ?, ?, ?)
                    """, (admin_user_id, admin_user_for_tm_dict['full_name'], admin_user_for_tm_dict['email'], admin_user_for_tm_dict['role']))
                    print("Seeded admin team member linked to user.")
            else:
                print(f"Could not retrieve admin user details for ID {admin_user_id}, cannot seed admin team member accurately.")
        else:
            print("Admin user ID not available, cannot seed admin team member.")


        # 5. Countries
        default_countries = [
            {'country_name': 'France'}, {'country_name': 'USA'}, {'country_name': 'Algeria'}
        ]
        for country_data in default_countries:
            add_country(country_data) # Use imported function
        print(f"Seeded {len(default_countries)} countries.")


        # 6. Cities
        default_cities_map = {
            'France': 'Paris', 'USA': 'New York', 'Algeria': 'Algiers'
        }
        for country_name, city_name in default_cities_map.items():
            country_row_dict = get_country_by_name(country_name) # Use imported function
            if country_row_dict:
                country_id = country_row_dict['country_id']
                add_city({'country_id': country_id, 'city_name': city_name}) # Use imported function
        print(f"Seeded {len(default_cities_map)} cities.")

        # 7. Clients
        # Using clients_crud_instance for client seeding
        cursor.execute("SELECT COUNT(*) FROM Clients")
        if cursor.fetchone()[0] == 0:
            # admin_user_id obtained from user seeding step
            default_country_for_client_dict = get_country_by_name('France') # location_crud
            default_country_id_for_client = default_country_for_client_dict['country_id'] if default_country_for_client_dict else None

            default_city_id_for_client = None
            if default_country_id_for_client:
                city_client_dict = get_city_by_name_and_country_id('Paris', default_country_id_for_client) # location_crud
                if city_client_dict: default_city_id_for_client = city_client_dict['city_id']

            active_client_status_dict = get_status_setting_by_name('Actif', 'Client') # status_settings_crud
            active_client_status_id = active_client_status_dict['status_id'] if active_client_status_dict else None

            if admin_user_id and default_country_id_for_client and default_city_id_for_client and active_client_status_id:
                client_data_seed = {
                    'client_name': "Sample Client SARL",
                    'company_name': "Sample Client Company",
                    'project_identifier': "SC-PROJ-001", # Ensure this is handled or schema allows nullable
                    'country_id': default_country_id_for_client,
                    'city_id': default_city_id_for_client,
                    'status_id': active_client_status_id,
                    'created_by_user_id': admin_user_id,
                    'default_base_folder_path': f"clients/{str(uuid.uuid4())}", # Ensure unique path
                    'primary_need_description': "General business services",
                    'selected_languages': "en,fr"
                }
                add_client_result = clients_crud_instance.add_client(client_data_seed, conn=conn)
                if add_client_result['success']:
                    sample_client_id_for_proj = add_client_result['client_id']
                    print(f"Seeded sample client with ID: {sample_client_id_for_proj}")
                else:
                    print(f"Failed to seed sample client: {add_client_result.get('error')}")
                    sample_client_id_for_proj = None
            else:
                print("Could not seed sample client due to missing prerequisite data (admin user, country, city, or status).")
                sample_client_id_for_proj = None
        else:
            # If client exists, try to get its ID for project seeding
            # This assumes only one "Sample Client SARL" for simplicity in seeding
            existing_clients = clients_crud_instance.get_all_clients(filters={'client_name': "Sample Client SARL"}, conn=conn)
            sample_client_id_for_proj = existing_clients[0]['client_id'] if existing_clients else None


        # 8. Projects
        cursor.execute("SELECT COUNT(*) FROM Projects")
        if cursor.fetchone()[0] == 0:
            planning_project_status_dict = get_status_setting_by_name('Planning', 'Project') # status_settings_crud
            planning_project_status_id = planning_project_status_dict['status_id'] if planning_project_status_dict else None

            # admin_user_id from user seeding
            # sample_client_id_for_proj from client seeding

            if sample_client_id_for_proj and planning_project_status_id and admin_user_id:
                project_uuid = str(uuid.uuid4()) # Projects table uses TEXT project_id
                # Assuming add_project is not yet refactored to a class instance
                # If it were, it would be projects_crud_instance.add_project(...)
                # For now, direct insert if no add_project function is available from imports
                cursor.execute("""
                    INSERT OR IGNORE INTO Projects (project_id, client_id, project_name, description, status_id, manager_team_member_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (project_uuid, sample_client_id_for_proj, "Initial Project for Sample Client", "First project description.", planning_project_status_id, admin_user_id))
                print("Seeded sample project.")
            else:
                print("Could not seed sample project due to missing prerequisite data (client, status, or manager).")

        # 9. Contacts (direct cursor - assuming contacts_crud not yet refactored or no add_contact available)
        cursor.execute("SELECT COUNT(*) FROM Contacts WHERE email = 'contact@example.com'")
        if cursor.fetchone()[0] == 0:
                cursor.execute("""
                INSERT OR IGNORE INTO Contacts (name, email, phone, position, company_name)
                VALUES (?, ?, ?, ?, ?)
            """, ("Placeholder Contact", "contact@example.com", "555-1234", "General Contact", "VariousCompanies Inc."))
                print("Seeded generic contact.")

        # 10. Products (direct cursor)
        # Using products_crud_instance for product seeding
        cursor.execute("SELECT COUNT(*) FROM Products WHERE product_name = 'Default Product'")
        if cursor.fetchone()[0] == 0:
            product_data_seed = {
                "product_name": "Default Product",
                "description": "This is a default product for testing and demonstration.",
                "category": "General",
                "language_code": "en",
                "base_unit_price": 10.00,
                "unit_of_measure": "unit",
                "is_active": True
            }
            add_product_result = products_crud_instance.add_product(product_data_seed, conn=conn)
            if add_product_result['success']:
                print(f"Seeded default product with ID: {add_product_result['id']}")
            else:
                print(f"Failed to seed default product: {add_product_result.get('error')}")

        # 11. SmtpConfigs (direct cursor - assuming smtp_configs_crud not yet refactored)
        cursor.execute("SELECT COUNT(*) FROM SmtpConfigs")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT OR IGNORE INTO SmtpConfigs (config_name, smtp_server, smtp_port, username, password_encrypted, use_tls, is_default, sender_email_address, sender_display_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("Placeholder - Configure Me", "smtp.example.com", 587, "user", "placeholder_password", True, True, "noreply@example.com", "Placeholder Email"))
            print("Seeded placeholder SMTP config.")

        # 12. ApplicationSettings (using imported set_setting, passing cursor)
        set_setting('initial_data_seeded_version', '1.1_seed_refactor', cursor=cursor)
        set_setting('default_app_language', 'en', cursor=cursor)
        set_setting('google_maps_review_url', 'https://maps.google.com/?cid=YOUR_CID_HERE', cursor=cursor)
        print("Seeded application settings.")

        # 13. Email Templates (using imported add_default_template_if_not_exists, passing cursor)
        # Ensure add_template_category is correctly imported and used within add_default_template_if_not_exists
        # (add_default_template_if_not_exists itself is now imported from cruds)
        add_default_template_if_not_exists({
            'template_name': 'SAV Ticket Ouvert (FR)', 'template_type': 'email_sav_ticket_opened', 'language_code': 'fr',
            'base_file_name': 'sav_ticket_opened_fr.html', 'description': 'Email envoyé quand un ticket SAV est ouvert.',
            'category_name': 'Modèles Email SAV', # This will be used by add_template_category within add_default_template_if_not_exists
            'email_subject_template': 'Ticket SAV #{{ticket.id}} Ouvert - {{project.name | default: "Référence Client"}}',
            'is_default_for_type_lang': True
        }, cursor=cursor) # Pass cursor
        add_default_template_if_not_exists({
            'template_name': 'SAV Ticket Résolu (FR)', 'template_type': 'email_sav_ticket_resolved', 'language_code': 'fr',
            'base_file_name': 'sav_ticket_resolved_fr.html', 'description': 'Email envoyé quand un ticket SAV est résolu.',
            'category_name': 'Modèles Email SAV',
            'email_subject_template': 'Ticket SAV #{{ticket.id}} Résolu - {{project.name | default: "Référence Client"}}',
            'is_default_for_type_lang': True
        }, cursor=cursor) # Pass cursor
        add_default_template_if_not_exists({
            'template_name': 'Suivi Prospect Proforma (FR)', 'template_type': 'email_follow_up_prospect', 'language_code': 'fr',
            'base_file_name': 'follow_up_prospect_fr.html', 'description': 'Email de suivi pour un prospect ayant reçu une proforma.',
            'category_name': 'Modèles Email Marketing/Suivi',
            'email_subject_template': 'Suite à votre demande de proforma : {{project.name | default: client.primary_need}}',
            'is_default_for_type_lang': True
        }, cursor=cursor) # Pass cursor
        add_default_template_if_not_exists({
            'template_name': 'Vœux Noël (FR)', 'template_type': 'email_greeting_christmas', 'language_code': 'fr',
            'base_file_name': 'greeting_holiday_christmas_fr.html', 'description': 'Email de vœux pour Noël.',
            'category_name': 'Modèles Email Vœux',
            'email_subject_template': 'Joyeux Noël de la part de {{seller.company_name}}!',
            'is_default_for_type_lang': True
        }, cursor=cursor) # Pass cursor
        add_default_template_if_not_exists({
            'template_name': 'Vœux Nouvelle Année (FR)', 'template_type': 'email_greeting_newyear', 'language_code': 'fr',
            'base_file_name': 'greeting_holiday_newyear_fr.html', 'description': 'Email de vœux pour la nouvelle année.',
            'category_name': 'Modèles Email Vœux',
            'email_subject_template': 'Bonne Année {{doc.current_year}} ! - {{seller.company_name}}',
            'is_default_for_type_lang': True
        }, cursor=cursor) # Pass cursor
        add_default_template_if_not_exists({
            'template_name': 'Message Générique (FR)', 'template_type': 'email_generic_message', 'language_code': 'fr',
            'base_file_name': 'generic_message_fr.html', 'description': 'Modèle générique pour communication spontanée.',
            'category_name': 'Modèles Email Généraux',
            'email_subject_template': 'Un message de {{seller.company_name}}',
            'is_default_for_type_lang': True
        }, cursor=cursor) # Pass cursor
        print("Seeded new email templates.")

        # 14. CoverPageTemplates: This is now handled by initialize_database from init_schema.py
        # The _populate_default_cover_page_templates call is removed from here.
        # If initialize_database did not run or did not commit these, they might be missing.
        # However, the subtask is to consolidate schema init, which includes this.
        print("Cover page templates are expected to be populated by initialize_database.")

        # 15. Partner Categories
        _seed_default_partner_categories(cursor)
        print("Called _seed_default_partner_categories for seeding.")

        print("Data seeding operations completed within seed_initial_data.")

    except sqlite3.Error as e:
        print(f"An error occurred during data seeding within seed_initial_data: {e}")
        raise

def run_seed():
    print(f"Attempting to seed database: {DATABASE_PATH}")
    conn = None
    try:
        # Use the imported get_db_connection
        conn = get_db_connection()
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

    # First, ensure the database and tables are created by calling initialize_database
    print("Ensuring database schema is initialized before seeding...")
    from db.init_schema import initialize_database # UPDATED IMPORT
    initialize_database()
    print("Database schema initialization check complete.")

    run_seed()
