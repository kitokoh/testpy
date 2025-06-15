import os
import sqlite3
import uuid
import hashlib
from datetime import datetime
import json
import logging

# Assuming config.py is in the parent directory (root)
from config import DATABASE_PATH, DEFAULT_ADMIN_USERNAME

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
from db.cruds.locations_crud import get_or_add_country, get_or_add_city, get_country_by_name, get_city_by_name_and_country_id
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


def _seed_default_partner_categories(cursor: sqlite3.Cursor, logger_passed: logging.Logger):
    """Seeds default partner categories into the database."""
    logger = logger_passed
    logger.info("Attempting to seed default partner categories...")
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
        existing_category_row = partners_crud.get_partner_category_by_name(category_def['category_name'], conn=cursor.connection)

        if existing_category_row: # Check if it's not None
            logger.info(f"Partner Category '{category_def['category_name']}' already exists with ID: {existing_category_row['partner_category_id']}. Skipping.")
        else:
            # Add category using the cursor directly
            # Ensure partners_crud.add_partner_category can accept a cursor
            category_id = partners_crud.add_partner_category(category_def, conn=cursor.connection)
            if category_id:
                logger.info(f"Partner Category '{category_def['category_name']}' added with ID: {category_id}")
            else:
                logger.warning(f"Could not add partner category '{category_def['category_name']}'. Check logs from partners_crud.")
    logger.info("Default partner categories seeding attempt finished.")

def seed_initial_data(cursor: sqlite3.Cursor):
    """
    Seeds the database with initial data using the provided cursor.
    All database operations within this function and any helper functions it calls
    must use this provided cursor.
    """
    logger = logging.getLogger(__name__)
    conn = cursor.connection # Get connection from cursor for instance methods

    try:
        # 1. Users
        # Admin user is expected to be created by init_schema.py.
        # We fetch the admin_user_id for associating other seeded data.
        logger.info(f"Attempting to retrieve admin user ID for '{DEFAULT_ADMIN_USERNAME}' for seeding purposes.")
        admin_user_dict = users_crud_instance.get_user_by_username(DEFAULT_ADMIN_USERNAME, conn=conn)
        admin_user_id = admin_user_dict['user_id'] if admin_user_dict else None

        if admin_user_id:
            logger.info(f"Found admin user '{DEFAULT_ADMIN_USERNAME}' with ID: {admin_user_id}. This user will be used for associating seeded data.")
        else:
            logger.warning(f"Admin user '{DEFAULT_ADMIN_USERNAME}' not found. Some seeded data may not be associated with an admin user. This might indicate an issue with initial schema setup from init_schema.py.")
            # Depending on requirements, one might choose to raise an error here if admin_user_id is critical.
            # For now, proceeding but logging a warning.

        # 2. Companies
        default_company_id = None
        cursor.execute("SELECT COUNT(*) FROM Companies")
        if cursor.fetchone()[0] == 0:
            default_company_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT OR IGNORE INTO Companies (company_id, company_name, address, is_default)
                VALUES (?, ?, ?, ?)
            """, (default_company_id, "Default Company Inc.", "123 Default Street", True))
            logger.info("Seeded default company.")
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
                logger.info("Seeded default company personnel.")

        # 4. TeamMembers
        # admin_user_id obtained from user seeding step above (retrieval attempt)
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
                    logger.info("Seeded admin team member linked to user.")
            else:
                logger.warning(f"Could not retrieve admin user details for ID {admin_user_id}, cannot seed admin team member accurately.")
        else:
            logger.warning("Admin user ID not available, cannot seed admin team member.")

        # Seed Default Operational User
        DEFAULT_OPERATIONAL_USERNAME = "default_operational_user"
        DEFAULT_OPERATIONAL_USER_ROLE = "User" # Assuming 'User' is a valid, less-privileged role

        logger.info(f"Checking for default operational user '{DEFAULT_OPERATIONAL_USERNAME}'...")
        existing_operational_user = users_crud_instance.get_user_by_username(DEFAULT_OPERATIONAL_USERNAME, conn=conn)

        if existing_operational_user is None:
            logger.info(f"Default operational user '{DEFAULT_OPERATIONAL_USERNAME}' not found. Creating...")
            operational_user_data = {
                'username': DEFAULT_OPERATIONAL_USERNAME,
                'password': uuid.uuid4().hex, # Secure random password
                'email': f"{DEFAULT_OPERATIONAL_USERNAME}@example.local", # Unique placeholder email
                'role': DEFAULT_OPERATIONAL_USER_ROLE,
                'full_name': "Default Operational User",
                'is_active': True
            }
            try:
                op_user_result = users_crud_instance.add_user(operational_user_data, conn=conn)
                if op_user_result['success']:
                    logger.info(f"Successfully created default operational user '{DEFAULT_OPERATIONAL_USERNAME}' with ID: {op_user_result['user_id']}.")
                else:
                    logger.error(f"Failed to create default operational user '{DEFAULT_OPERATIONAL_USERNAME}'. Error: {op_user_result.get('error', 'Unknown error')}")
            except Exception as e_op_user:
                logger.error(f"Exception during creation of default operational user '{DEFAULT_OPERATIONAL_USERNAME}': {e_op_user}", exc_info=True)
        else:
            logger.info(f"Default operational user '{DEFAULT_OPERATIONAL_USERNAME}' already exists with ID: {existing_operational_user['user_id']}. Skipping creation.")

        # 5. Countries
        logger.info("Seeding default countries...")
        default_countries = [
            {'country_name': 'France'}, {'country_name': 'USA'}, {'country_name': 'Algeria'}
        ]
        for country_data in default_countries:
            get_or_add_country(country_data['country_name']) # Use imported function
        logger.info(f"Seeded {len(default_countries)} countries.")


        # 6. Cities
        logger.info("Seeding default cities...")
        default_cities_map = {
            'France': 'Paris', 'USA': 'New York', 'Algeria': 'Algiers'
        }
        for country_name, city_name in default_cities_map.items():
            country_row_dict = get_country_by_name(country_name) # Use imported function
            if country_row_dict:
                country_id = country_row_dict['country_id']
                get_or_add_city(city_name, country_id) # Use imported function
        logger.info(f"Seeded {len(default_cities_map)} cities.")

        # 7. Clients
        logger.info("Seeding sample client...")
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
                    logger.info(f"Seeded sample client with ID: {sample_client_id_for_proj}")
                else:
                    logger.error(f"Failed to seed sample client: {add_client_result.get('error')}")
                    sample_client_id_for_proj = None
            else:
                logger.warning("Could not seed sample client due to missing prerequisite data (admin user, country, city, or status).")
                sample_client_id_for_proj = None
        else:
            # If client exists, try to get its ID for project seeding
            # This assumes only one "Sample Client SARL" for simplicity in seeding
            existing_clients = clients_crud_instance.get_all_clients(filters={'client_name': "Sample Client SARL"}, conn=conn)
            if existing_clients:
                sample_client_id_for_proj = existing_clients[0]['client_id']
                logger.info(f"Found existing sample client with ID: {sample_client_id_for_proj}")
            else:
                sample_client_id_for_proj = None
                logger.info("No existing sample client found by name 'Sample Client SARL'.")


        # 8. Projects
        logger.info("Seeding sample project...")
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
                logger.info("Seeded sample project.")
            else:
                logger.warning("Could not seed sample project due to missing prerequisite data (client, status, or manager).")

        # 9. Contacts (direct cursor - assuming contacts_crud not yet refactored or no add_contact available)
        logger.info("Seeding generic contact...")
        cursor.execute("SELECT COUNT(*) FROM Contacts WHERE email = 'contact@example.com'")
        if cursor.fetchone()[0] == 0:
                cursor.execute("""
                INSERT OR IGNORE INTO Contacts (name, email, phone, position, company_name)
                VALUES (?, ?, ?, ?, ?)
            """, ("Placeholder Contact", "contact@example.com", "555-1234", "General Contact", "VariousCompanies Inc."))
                logger.info("Seeded generic contact.")

        # 10. Products
        logger.info("Seeding default and sample products...")
        # Using products_crud_instance for product seeding

        sample_products = [
            {
                "product_name": "Default Product",
                "description": "This is a default product for testing and demonstration.",
                "category": "General",
                "language_code": "en",
                "base_unit_price": 10.00,
                "unit_of_measure": "unit",
                "is_active": True
            },
            {
                "product_name": "Industrial Widget",
                "description": "A robust widget for industrial applications.",
                "category": "Widgets",
                "language_code": "en",
                "base_unit_price": 100.00,
                "unit_of_measure": "piece",
                "is_active": True
            },
            {
                "product_name": "Gadget Standard",
                "description": "Un gadget standard pour diverses utilisations.",
                "category": "Gadgets",
                "language_code": "fr",
                "base_unit_price": 50.00,
                "unit_of_measure": "unité",
                "is_active": True
            },
            {
                "product_name": "Advanced Gizmo",
                "description": "High-performance gizmo with advanced features.",
                "category": "Gizmos",
                "language_code": "en",
                "base_unit_price": 250.00,
                "unit_of_measure": "item",
                "is_active": True
            }
        ]

        for product_data_seed in sample_products:
            # Check if product already exists (by name and language_code to be more specific)
            # products_crud_instance.get_product_by_name expects name and optional language_code
            # Assuming get_products (plural) or a more specific getter might be better,
            # but let's use what's likely available and simple.
            # For now, we'll rely on a simple name check as per the original code for "Default Product".
            # A more robust check would be:
            # existing_product = products_crud_instance.get_product_by_name_and_lang(
            #    product_data_seed["product_name"], product_data_seed["language_code"], conn=conn
            # )
            # if existing_product:
            #    logger.info(f"Product '{product_data_seed['product_name']}' ({product_data_seed['language_code']}) already exists. Skipping.")
            #    continue

            # Simpler check based on original pattern:
            cursor.execute("SELECT COUNT(*) FROM Products WHERE product_name = ? AND language_code = ?",
                           (product_data_seed["product_name"], product_data_seed["language_code"]))
            if cursor.fetchone()[0] == 0:
                add_product_result = products_crud_instance.add_product(product_data_seed, conn=conn)
                if add_product_result['success']:
                    logger.info(f"Seeded product '{product_data_seed['product_name']}' with ID: {add_product_result['id']}")
                else:
                    logger.error(f"Failed to seed product '{product_data_seed['product_name']}': {add_product_result.get('error')}")
            else:
                logger.info(f"Product '{product_data_seed['product_name']}' ({product_data_seed['language_code']}) already exists. Skipping.")

        # 11. SmtpConfigs (direct cursor - assuming smtp_configs_crud not yet refactored)
        logger.info("Seeding placeholder SMTP config...")
        cursor.execute("SELECT COUNT(*) FROM SmtpConfigs")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT OR IGNORE INTO SmtpConfigs (config_name, smtp_server, smtp_port, username, password_encrypted, use_tls, is_default, sender_email_address, sender_display_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("Placeholder - Configure Me", "smtp.example.com", 587, "user", "placeholder_password", True, True, "noreply@example.com", "Placeholder Email"))
            logger.info("Seeded placeholder SMTP config.")

        # 12. ApplicationSettings
        # 'initial_data_seeded_version' and 'default_app_language' are now set by init_schema.py
        logger.info("Seeding additional application settings...")
        set_setting('google_maps_review_url', 'https://maps.google.com/?cid=YOUR_CID_HERE', cursor=cursor)
        logger.info("Seeded additional application settings.")

        # 13. Email Templates (using imported add_default_template_if_not_exists, passing cursor)
        logger.info("Seeding email templates...")
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
        logger.info("Seeded new email templates.")

        # 14. CoverPageTemplates: This is now handled by initialize_database from init_schema.py
        logger.info("Cover page templates are expected to be populated by initialize_database from init_schema.py.")

        # 15. Partner Categories
        _seed_default_partner_categories(cursor, logger_passed=logger) # Pass logger
        logger.info("Called _seed_default_partner_categories for seeding.")

        logger.info("Data seeding operations completed within seed_initial_data.")

    except sqlite3.Error as e:
        logger.error(f"An SQLite error occurred during data seeding within seed_initial_data: {e}", exc_info=True)
        raise
    except Exception as e_gen:
        logger.error(f"A general error occurred during data seeding within seed_initial_data: {e_gen}", exc_info=True)
        raise


def run_seed():
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to seed database: {DATABASE_PATH}")
    conn = None
    try:
        # Use the imported get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        seed_initial_data(cursor) # Call the local seed_initial_data
        conn.commit()
        logger.info("Seeding process completed and committed.")
    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(f"Error during seeding process, transaction rolled back: {e}", exc_info=True)
        else:
            logger.error(f"Error during seeding process (connection might not have been established): {e}", exc_info=True)
        # Optionally re-raise e or handle more gracefully
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed after seeding attempt.")

if __name__ == '__main__':
    # Basic logging configuration for direct script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    main_logger = logging.getLogger(__name__) # Get a logger for the __main__ scope

    # This allows running the seed script directly for testing or initial setup
    # Note: db_main_manager.initialize_database() should typically be called before seeding
    # if the database schema itself might not exist.
    # However, run_seed() assumes the schema is already in place.

    # First, ensure the database and tables are created by calling initialize_database
    main_logger.info("Ensuring database schema is initialized before seeding...")
    from db.init_schema import initialize_database # UPDATED IMPORT
    try:
        initialize_database() # This function now also uses logging
        main_logger.info("Database schema initialization check complete.")
        run_seed()
    except Exception as e_main:
        main_logger.critical(f"Critical error during __main__ execution of db_seed: {e_main}", exc_info=True)
