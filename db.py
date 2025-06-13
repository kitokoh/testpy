import sqlite3
import uuid
import hashlib
from datetime import datetime
import json
import os # Added os import

# Utilities from the db package
from db.utils import get_db_connection

from config import DATABASE_PATH # Added

# Global variable for the database name
DATABASE_NAME = os.path.basename(DATABASE_PATH) # Updated to use DATABASE_PATH

# Constants for document context paths
# Assuming db.py is in a subdirectory of the app root (e.g., /app/core/db.py or /app/db.py)
# If db.py is directly in /app, then os.path.dirname(__file__) is /app
# If db.py is directly in /app, then os.path.dirname(__file__) is /app
APP_ROOT_DIR_CONTEXT = os.path.abspath(os.path.dirname(__file__))
LOGO_SUBDIR_CONTEXT = "company_logos" # This should match the setup in the test script and app_setup.py




# --- Document Context Data Function ---

# --- Document Context Data Function has been removed, it's now in db.utils ---

# Functions related to Clients, Products, Users that were refactored into specific
# CRUD classes (e.g., clients_crud.ClientsCRUD, products_crud.ProductsCRUD, users_crud.UsersCRUD)
# should now be imported directly from their respective modules using the class instances
# (e.g., from db.cruds.clients_crud import clients_crud_instance).
# This db.py file will serve as a facade for unrefactored CRUD modules or general DB utilities.

# Example: get_total_clients_count is now available via clients_crud_instance.get_total_clients_count()
# Example: get_total_products_count is now available via products_crud_instance.get_total_products_count()
# Example: get_clients_by_archival_status is now available via clients_crud_instance.get_clients_by_archival_status()

# get_total_projects_count is now available via projects_crud_instance.get_total_projects_count()
# def get_total_projects_count() -> int:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT COUNT(project_id) as total_count FROM Projects")
#         row = cursor.fetchone()
#         return row['total_count'] if row else 0
#     except sqlite3.Error as e:
#         print(f"Database error in get_total_projects_count: {e}")
#         return 0
#     finally:
#         if conn:
#             conn.close()

# get_active_projects_count is now available via projects_crud_instance.get_active_projects_count()
# def get_active_projects_count() -> int:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Select projects whose status_id is not in the set of completion or archival statuses,
#         # or projects who have no status_id (considered active by default).
#         sql = """
#             SELECT COUNT(p.project_id) as active_count
#             FROM Projects p
#             LEFT JOIN StatusSettings ss ON p.status_id = ss.status_id
#             WHERE (ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE) OR p.status_id IS NULL
#         """
#         cursor.execute(sql)
#         row = cursor.fetchone()
#         return row['active_count'] if row else 0
#     except sqlite3.Error as e:
#         print(f"Database error in get_active_projects_count: {e}")
#         return 0
#     finally:
#         if conn:
#             conn.close()

# get_clients_by_archival_status is now available via clients_crud_instance.get_clients_by_archival_status()
# def get_clients_by_archival_status(is_archived: bool, include_null_status_for_active: bool = True) -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         cursor.execute("SELECT status_id FROM StatusSettings WHERE status_type = 'Client' AND is_archival_status = TRUE")
#         archival_status_rows = cursor.fetchall()
#         archival_status_ids = [row['status_id'] for row in archival_status_rows]

#         base_query = """
#             SELECT
#                 c.client_id, c.client_name, c.company_name, c.primary_need_description,
#                 c.project_identifier, c.default_base_folder_path, c.selected_languages,
#                 c.price, c.notes, c.created_at, c.category, c.status_id, c.country_id, c.city_id,
#                 co.country_name AS country,
#                 ci.city_name AS city,
#                 s.status_name AS status,
#                 s.color_hex AS status_color,
#                 s.icon_name AS status_icon_name
#             FROM Clients c
#             LEFT JOIN Countries co ON c.country_id = co.country_id
#             LEFT JOIN Cities ci ON c.city_id = ci.city_id
#             LEFT JOIN StatusSettings s ON c.status_id = s.status_id AND s.status_type = 'Client'
#         """

#         params = []
#         where_conditions = []

#         if not archival_status_ids: # No statuses are defined as archival
#             if is_archived: # If we are looking for archived clients but no status is archival type
#                 return []
#             else: # If we are looking for active clients and no status is archival type, all clients (with or without status) are considered active
#                   # This case will fall through to the 'else' for where_conditions, fetching all.
#                   pass # No specific condition needed here if all are considered active
#         else: # Archival statuses exist
#             placeholders = ','.join('?' for _ in archival_status_ids)
#             if is_archived:
#                 where_conditions.append(f"c.status_id IN ({placeholders})")
#                 params.extend(archival_status_ids)
#             else: # Active clients
#                 not_in_condition = f"c.status_id NOT IN ({placeholders})"
#                 if include_null_status_for_active:
#                     where_conditions.append(f"({not_in_condition} OR c.status_id IS NULL)")
#                 else:
#                     where_conditions.append(not_in_condition)
#                 params.extend(archival_status_ids) # These params are for the NOT IN part

#         if where_conditions:
#             sql = f"{base_query} WHERE {' AND '.join(where_conditions)} ORDER BY c.client_name;"
#         else:
#             # If is_archived=False and no archival_status_ids, this means all clients are non-archived.
#             # If include_null_status_for_active is True, it includes clients with NULL status.
#             # If include_null_status_for_active is False, it implies only clients with a non-archival status.
#             # This default (no WHERE clause) correctly handles the "all active when no archival statuses defined"
#             # and "show all" if no specific archival filtering is applied.
#             sql = f"{base_query} ORDER BY c.client_name;"


#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_clients_by_archival_status: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# get_total_products_count is now handled by products_crud_instance.get_total_products_count()


# --- CRUD functions for FreightForwarders ---

def get_distinct_purchase_confirmed_at_for_client(client_id: str) -> list[str] | None:
    """
    Retrieves a list of distinct, non-null purchase_confirmed_at timestamps
    for a given client_id from the ClientProjectProducts table.
    Returns a list of ISO formatted timestamp strings, or None on error.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = """
            SELECT DISTINCT purchase_confirmed_at
            FROM ClientProjectProducts
            WHERE client_id = ? AND purchase_confirmed_at IS NOT NULL
            ORDER BY purchase_confirmed_at DESC;
        """
        # Using DESC order so more recent orders appear first in UI if not re-sorted there
        cursor.execute(sql, (client_id,))
        rows = cursor.fetchall()
        # sqlite3.Row objects behave like tuples for indexing
        return [row[0] for row in rows if row[0] is not None]
    except sqlite3.Error as e:
        print(f"Database error in get_distinct_purchase_confirmed_at_for_client for client {client_id}: {e}")
        return None # Return None to indicate an error condition
    except Exception as ex: # Catch any other unexpected errors
        print(f"Unexpected error in get_distinct_purchase_confirmed_at_for_client for client {client_id}: {ex}")
        return None
    finally:
        if conn:
            conn.close()

# --- CRUD functions for Client_Transporters ---

# --- CRUD functions for Client_FreightForwarders ---


if __name__ == '__main__':
    from db.init_schema import initialize_database # Corrected import
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

# def seed_initial_data(cursor: sqlite3.Cursor):
#     """
#     Seeds the database with initial data using the provided cursor.
#     All database operations within this function and any helper functions it calls
#     must use this provided cursor.
#     """
#     # Helper functions like get_user_by_username, get_country_by_name, etc.,
#     # which create their own connections, cannot be directly used here if we are to
#     # strictly use the provided cursor. Such logic needs to be adapted for direct cursor use
#     # or the helper functions refactored to accept a cursor.

#     try:
#         # 1. Users
#         cursor.execute("SELECT COUNT(*) FROM Users")
#         if cursor.fetchone()[0] == 0:
#             admin_user_id = str(uuid.uuid4())
#             admin_password_hash = hashlib.sha256('adminpassword'.encode('utf-8')).hexdigest()
#             cursor.execute("""
#                 INSERT OR IGNORE INTO Users (user_id, username, password_hash, full_name, email, role, is_active)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)
#             """, (admin_user_id, 'admin', admin_password_hash, 'Default Admin', 'admin@example.com', 'admin', True))
#             print("Seeded admin user.")

#         # The rest of the seeding logic will be moved here incrementally.
#         # For now, this function only seeds users.

#         # 2. Companies
#         default_company_id = None
#         cursor.execute("SELECT COUNT(*) FROM Companies")
#         if cursor.fetchone()[0] == 0:
#             default_company_id = str(uuid.uuid4())
#             cursor.execute("""
#                 INSERT OR IGNORE INTO Companies (company_id, company_name, address, is_default)
#                 VALUES (?, ?, ?, ?)
#             """, (default_company_id, "Default Company Inc.", "123 Default Street", True))
#             print("Seeded default company.")
#         else:
#             # If company exists, try to get the default one for personnel and other linking
#             cursor.execute("SELECT company_id FROM Companies WHERE is_default = TRUE")
#             row = cursor.fetchone()
#             if row:
#                 default_company_id = row[0]

#         # 3. CompanyPersonnel
#         if default_company_id:
#             cursor.execute("SELECT COUNT(*) FROM CompanyPersonnel WHERE company_id = ?", (default_company_id,))
#             if cursor.fetchone()[0] == 0: # Only add if no personnel for this company yet
#                 cursor.execute("""
#                     INSERT OR IGNORE INTO CompanyPersonnel (company_id, name, role, email, phone)
#                     VALUES (?, ?, ?, ?, ?)
#                 """, (default_company_id, "Admin Contact", "Administrator", "contact@defaultcomp.com", "123-456-7890"))
#                 print("Seeded default company personnel.")

#         # 4. TeamMembers (link to admin user if created)
#         # Note: get_user_by_username will need to be adapted or this logic changed for direct cursor use
#         # For now, assuming direct cursor usage for this specific check during seeding
#         cursor.execute("SELECT user_id FROM Users WHERE username = 'admin'")
#         admin_user_row = cursor.fetchone()
#         if admin_user_row:
#             admin_user_id_for_tm = admin_user_row[0]
#             cursor.execute("SELECT COUNT(*) FROM TeamMembers WHERE user_id = ?", (admin_user_id_for_tm,))
#             if cursor.fetchone()[0] == 0:
#                 cursor.execute("""
#                     INSERT OR IGNORE INTO TeamMembers (user_id, full_name, email, role_or_title)
#                     VALUES (?, ?, ?, ?)
#                 """, (admin_user_id_for_tm, 'Default Admin', 'admin@example.com', 'Administrator'))
#                 print("Seeded admin team member.")

#         # 5. Countries
#         default_countries = [
#             {'country_name': 'France'}, {'country_name': 'USA'}, {'country_name': 'Algeria'}
#         ]
#         for country in default_countries:
#             cursor.execute("INSERT OR IGNORE INTO Countries (country_name) VALUES (?)", (country['country_name'],))
#         print(f"Seeded {len(default_countries)} countries.")

#         # 6. Cities
#         default_cities_map = {
#             'France': 'Paris', 'USA': 'New York', 'Algeria': 'Algiers'
#         }
#         for country_name, city_name in default_cities_map.items():
#             cursor.execute("SELECT country_id FROM Countries WHERE country_name = ?", (country_name,))
#             country_row = cursor.fetchone()
#             if country_row:
#                 country_id = country_row[0]
#                 cursor.execute("INSERT OR IGNORE INTO Cities (country_id, city_name) VALUES (?, ?)", (country_id, city_name))
#         print(f"Seeded {len(default_cities_map)} cities.")

#         # 7. Clients
#         # Note: The following get_user_by_username, get_country_by_name, etc. create their own connections.
#         # This will need to be refactored to use the provided cursor or adapt logic.
#         # For this step, moving as is, refactoring helpers later.
#         cursor.execute("SELECT COUNT(*) FROM Clients")
#         if cursor.fetchone()[0] == 0:
#             admin_user_id_for_client = None
#             cursor.execute("SELECT user_id FROM Users WHERE username = 'admin'")
#             admin_user_client_row = cursor.fetchone()
#             if admin_user_client_row: admin_user_id_for_client = admin_user_client_row[0]

#             default_country_id_for_client = None
#             cursor.execute("SELECT country_id FROM Countries WHERE country_name = 'France'")
#             country_client_row = cursor.fetchone()
#             if country_client_row: default_country_id_for_client = country_client_row[0]

#             default_city_id_for_client = None
#             if default_country_id_for_client:
#                 cursor.execute("SELECT city_id FROM Cities WHERE city_name = 'Paris' AND country_id = ?", (default_country_id_for_client,))
#                 city_client_row = cursor.fetchone()
#                 if city_client_row: default_city_id_for_client = city_client_row[0]

#             active_client_status_id = None
#             cursor.execute("SELECT status_id FROM StatusSettings WHERE status_name = 'Actif' AND status_type = 'Client'")
#             status_client_row = cursor.fetchone()
#             if status_client_row: active_client_status_id = status_client_row[0]

#             if admin_user_id_for_client and default_country_id_for_client and default_city_id_for_client and active_client_status_id:
#                 client_uuid = str(uuid.uuid4())
#                 cursor.execute("""
#                     INSERT OR IGNORE INTO Clients (client_id, client_name, company_name, project_identifier, country_id, city_id, status_id, created_by_user_id, default_base_folder_path, primary_need_description, selected_languages)
#                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#                 """, (client_uuid, "Sample Client SARL", "Sample Client Company", "SC-PROJ-001", default_country_id_for_client, default_city_id_for_client, active_client_status_id, admin_user_id_for_client, f"clients/{client_uuid}", "General business services", "en,fr"))
#                 print("Seeded sample client.")
#             else:
#                 print("Could not seed sample client due to missing prerequisite data (admin user, country, city, or status).")

#         # 8. Projects
#         cursor.execute("SELECT COUNT(*) FROM Projects")
#         if cursor.fetchone()[0] == 0:
#             sample_client_id = None
#             cursor.execute("SELECT client_id FROM Clients WHERE client_name = 'Sample Client SARL'")
#             sample_client_proj_row = cursor.fetchone()
#             if sample_client_proj_row: sample_client_id = sample_client_proj_row[0]

#             planning_project_status_id = None
#             cursor.execute("SELECT status_id FROM StatusSettings WHERE status_name = 'Planning' AND status_type = 'Project'")
#             status_proj_row = cursor.fetchone()
#             if status_proj_row: planning_project_status_id = status_proj_row[0]

#             admin_user_id_for_project = None
#             cursor.execute("SELECT user_id FROM Users WHERE username = 'admin'") # Assuming admin user is manager
#             admin_user_proj_row = cursor.fetchone()
#             if admin_user_proj_row: admin_user_id_for_project = admin_user_proj_row[0]

#             if sample_client_id and planning_project_status_id and admin_user_id_for_project:
#                 project_uuid = str(uuid.uuid4())
#                 cursor.execute("""
#                     INSERT OR IGNORE INTO Projects (project_id, client_id, project_name, description, status_id, manager_team_member_id)
#                     VALUES (?, ?, ?, ?, ?, ?)
#                 """, (project_uuid, sample_client_id, "Initial Project for Sample Client", "First project description.", planning_project_status_id, admin_user_id_for_project))
#                 print("Seeded sample project.")
#             else:
#                 print("Could not seed sample project due to missing prerequisite data (client, status, or manager).")

#         # 9. Contacts
#         cursor.execute("SELECT COUNT(*) FROM Contacts WHERE email = 'contact@example.com'")
#         if cursor.fetchone()[0] == 0:
#                 cursor.execute("""
#                 INSERT OR IGNORE INTO Contacts (name, email, phone, position, company_name)
#                 VALUES (?, ?, ?, ?, ?)
#             """, ("Placeholder Contact", "contact@example.com", "555-1234", "General Contact", "VariousCompanies Inc."))
#                 print("Seeded generic contact.")

#         # 10. Products
#         cursor.execute("SELECT COUNT(*) FROM Products WHERE product_name = 'Default Product'")
#         if cursor.fetchone()[0] == 0:
#             cursor.execute("""
#                 INSERT OR IGNORE INTO Products (product_name, description, category, language_code, base_unit_price, unit_of_measure, is_active)
#                 VALUES (?, ?, ?, ?, ?, ?, ?)
#             """, ("Default Product", "This is a default product for testing and demonstration.", "General", "en", 10.00, "unit", True))
#             print("Seeded default product.")

#         # 11. SmtpConfigs
#         cursor.execute("SELECT COUNT(*) FROM SmtpConfigs")
#         if cursor.fetchone()[0] == 0:
#             cursor.execute("""
#                 INSERT OR IGNORE INTO SmtpConfigs (config_name, smtp_server, smtp_port, username, password_encrypted, use_tls, is_default, sender_email_address, sender_display_name)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """, ("Placeholder - Configure Me", "smtp.example.com", 587, "user", "placeholder_password", True, True, "noreply@example.com", "Placeholder Email"))
#             print("Seeded placeholder SMTP config.")

#         # 12. ApplicationSettings
#         # Calls to set_setting now correctly pass the cursor.
#         set_setting('initial_data_seeded_version', '1', cursor)
#         set_setting('default_app_language', 'en', cursor)
#         set_setting('google_maps_review_url', 'https://maps.google.com/?cid=YOUR_CID_HERE', cursor)
#         print("Seeded application settings.")

#         # 13. Email Templates (New)
#         # Calls to add_default_template_if_not_exists now pass the cursor.
#         add_default_template_if_not_exists({
#             'template_name': 'SAV Ticket Ouvert (FR)',
#             'template_type': 'email_sav_ticket_opened',
#             'language_code': 'fr',
#             'base_file_name': 'sav_ticket_opened_fr.html',
#             'description': 'Email envoyé quand un ticket SAV est ouvert.',
#             'category_name': 'Modèles Email SAV',
#             'email_subject_template': 'Ticket SAV #{{ticket.id}} Ouvert - {{project.name | default: "Référence Client"}}',
#             'is_default_for_type_lang': True
#         }, cursor)
#         add_default_template_if_not_exists({
#             'template_name': 'SAV Ticket Résolu (FR)',
#             'template_type': 'email_sav_ticket_resolved',
#             'language_code': 'fr',
#             'base_file_name': 'sav_ticket_resolved_fr.html',
#             'description': 'Email envoyé quand un ticket SAV est résolu.',
#             'category_name': 'Modèles Email SAV',
#             'email_subject_template': 'Ticket SAV #{{ticket.id}} Résolu - {{project.name | default: "Référence Client"}}',
#             'is_default_for_type_lang': True
#         }, cursor)
#         add_default_template_if_not_exists({
#             'template_name': 'Suivi Prospect Proforma (FR)',
#             'template_type': 'email_follow_up_prospect',
#             'language_code': 'fr',
#             'base_file_name': 'follow_up_prospect_fr.html',
#             'description': 'Email de suivi pour un prospect ayant reçu une proforma.',
#             'category_name': 'Modèles Email Marketing/Suivi',
#             'email_subject_template': 'Suite à votre demande de proforma : {{project.name | default: client.primary_need}}',
#             'is_default_for_type_lang': True
#         }, cursor)
#         add_default_template_if_not_exists({
#             'template_name': 'Vœux Noël (FR)',
#             'template_type': 'email_greeting_christmas',
#             'language_code': 'fr',
#             'base_file_name': 'greeting_holiday_christmas_fr.html',
#             'description': 'Email de vœux pour Noël.',
#             'category_name': 'Modèles Email Vœux',
#             'email_subject_template': 'Joyeux Noël de la part de {{seller.company_name}}!',
#             'is_default_for_type_lang': True
#         }, cursor)
#         add_default_template_if_not_exists({
#             'template_name': 'Vœux Nouvelle Année (FR)',
#             'template_type': 'email_greeting_newyear',
#             'language_code': 'fr',
#             'base_file_name': 'greeting_holiday_newyear_fr.html',
#             'description': 'Email de vœux pour la nouvelle année.',
#             'category_name': 'Modèles Email Vœux',
#             'email_subject_template': 'Bonne Année {{doc.current_year}} ! - {{seller.company_name}}',
#             'is_default_for_type_lang': True
#         }, cursor)
#         add_default_template_if_not_exists({
#             'template_name': 'Message Générique (FR)',
#             'template_type': 'email_generic_message',
#             'language_code': 'fr',
#             'base_file_name': 'generic_message_fr.html',
#             'description': 'Modèle générique pour communication spontanée.',
#             'category_name': 'Modèles Email Généraux',
#             'email_subject_template': 'Un message de {{seller.company_name}}',
#             'is_default_for_type_lang': True
#         }, cursor)
#         print("Seeded new email templates.")

#         # 14. CoverPageTemplates
#         _populate_default_cover_page_templates(cursor)
#         print("Called _populate_default_cover_page_templates for seeding.")

#         # All seeding operations that were previously in initialize_database's try block are now moved here.
#         # The main try...except...finally for the whole seeding process is around these calls within seed_initial_data.
#         # The commit for seed_initial_data will be handled by its caller.
#         print("Data seeding operations completed within seed_initial_data.")

#     except sqlite3.Error as e: # This except is part of seed_initial_data
#         print(f"An error occurred during data seeding within seed_initial_data: {e}")
#         # Rollback should be handled by the caller who owns the connection and cursor
#         raise # Re-raise the exception so the caller can handle rollback
#     # No finally block here for seed_initial_data, connection management is external.


# # CRUD functions for Projects
# def add_project(project_data: dict) -> str | None:
#     """
#     Adds a new project to the database.
#     Returns the new project_id if successful, otherwise None.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         new_project_id = uuid.uuid4().hex
#         now = datetime.utcnow().isoformat() + "Z"

#         sql = """
#             INSERT INTO Projects (
#                 project_id, client_id, project_name, description, start_date,
#                 deadline_date, budget, status_id, progress_percentage,
#                 manager_team_member_id, priority, created_at, updated_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             new_project_id,
#             project_data.get('client_id'),
#             project_data.get('project_name'),
#             project_data.get('description'),
#             project_data.get('start_date'),
#             project_data.get('deadline_date'),
#             project_data.get('budget'),
#             project_data.get('status_id'),
#             project_data.get('progress_percentage', 0),
#             project_data.get('manager_team_member_id'),
#             project_data.get('priority', 0),
#             now,  # created_at
#             now   # updated_at
#         )
        
#         cursor.execute(sql, params)
#         conn.commit()
#         return new_project_id
#     except sqlite3.Error as e:
#         print(f"Database error in add_project: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_project_by_id(project_id: str) -> dict | None:
#     """Retrieves a project by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Projects WHERE project_id = ?", (project_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_project_by_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_projects_by_client_id(client_id: str) -> list[dict]:
#     """Retrieves all projects for a given client_id."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Projects WHERE client_id = ?", (client_id,))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_projects_by_client_id: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_all_projects(filters: dict = None) -> list[dict]:
#     """
#     Retrieves all projects, optionally applying filters.
#     Allowed filters: client_id, status_id, manager_team_member_id, priority.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         sql = "SELECT * FROM Projects"
#         params = []
        
#         if filters:
#             where_clauses = []
#             allowed_filters = ['client_id', 'status_id', 'manager_team_member_id', 'priority']
#             for key, value in filters.items():
#                 if key in allowed_filters:
#                     where_clauses.append(f"{key} = ?")
#                     params.append(value)
#             if where_clauses:
#                 sql += " WHERE " + " AND ".join(where_clauses)

#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_projects: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_project(project_id: str, project_data: dict) -> bool:
#     """
#     Updates an existing project. Sets updated_at.
#     Returns True if update was successful, False otherwise.
#     """
#     conn = None
#     if not project_data:
#         return False

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         now = datetime.utcnow().isoformat() + "Z"
#         project_data['updated_at'] = now
        
#         set_clauses = []
#         params = []
        
#         # Ensure only valid columns are updated
#         valid_columns = [
#             'client_id', 'project_name', 'description', 'start_date', 'deadline_date',
#             'budget', 'status_id', 'progress_percentage', 'manager_team_member_id',
#             'priority', 'updated_at'
#         ]
#         for key, value in project_data.items():
#             if key in valid_columns:
#                  set_clauses.append(f"{key} = ?")
#                  params.append(value)

#         if not set_clauses:
#             return False
            
#         sql = f"UPDATE Projects SET {', '.join(set_clauses)} WHERE project_id = ?"
#         params.append(project_id)
        
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_project: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def delete_project(project_id: str) -> bool:
#     """Deletes a project. Returns True if deletion was successful."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # ON DELETE CASCADE for Tasks related to this project will be handled by SQLite
#         cursor.execute("DELETE FROM Projects WHERE project_id = ?", (project_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_project: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# # CRUD functions for Tasks
# def add_task(task_data: dict) -> int | None:
#     """
#     Adds a new task to the database. Returns the task_id if successful.
#     Sets created_at and updated_at.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"

#         sql = """
#             INSERT INTO Tasks (
#                 project_id, task_name, description, status_id, assignee_team_member_id,
#                 reporter_team_member_id, due_date, priority, estimated_hours,
#                 actual_hours_spent, parent_task_id, created_at, updated_at, completed_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             task_data.get('project_id'),
#             task_data.get('task_name'),
#             task_data.get('description'),
#             task_data.get('status_id'),
#             task_data.get('assignee_team_member_id'),
#             task_data.get('reporter_team_member_id'),
#             task_data.get('due_date'),
#             task_data.get('priority', 0),
#             task_data.get('estimated_hours'),
#             task_data.get('actual_hours_spent'),
#             task_data.get('parent_task_id'),
#             now,  # created_at
#             now,  # updated_at
#             task_data.get('completed_at') # Explicitly set if provided
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e:
#         print(f"Database error in add_task: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_task_by_id(task_id: int) -> dict | None:
#     """Retrieves a task by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Tasks WHERE task_id = ?", (task_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_task_by_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_tasks_by_project_id(project_id: str, filters: dict = None) -> list[dict]:
#     """
#     Retrieves tasks for a given project_id, optionally applying filters.
#     Allowed filters: assignee_team_member_id, status_id, priority.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql = "SELECT * FROM Tasks WHERE project_id = ?"
#         params = [project_id]

#         if filters:
#             where_clauses = []
#             allowed_filters = ['assignee_team_member_id', 'status_id', 'priority']
#             for key, value in filters.items():
#                 if key in allowed_filters:
#                     where_clauses.append(f"{key} = ?")
#                     params.append(value)
#             if where_clauses:
#                 sql += " AND " + " AND ".join(where_clauses)

#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_tasks_by_project_id: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_task(task_id: int, task_data: dict) -> bool:
#     """
#     Updates an existing task. Sets updated_at.
#     If 'completed_at' is in task_data, it will be updated.
#     (Logic for setting 'completed_at' based on status change should ideally be handled by calling code).
#     Returns True on success.
#     """
#     conn = None
#     if not task_data:
#         return False

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         task_data['updated_at'] = now

#         set_clauses = []
#         params = []

#         valid_columns = [
#             'project_id', 'task_name', 'description', 'status_id', 'assignee_team_member_id',
#             'reporter_team_member_id', 'due_date', 'priority', 'estimated_hours',
#             'actual_hours_spent', 'parent_task_id', 'updated_at', 'completed_at'
#         ]
#         for key, value in task_data.items():
#             if key in valid_columns: # Ensure key is a valid column
#                 set_clauses.append(f"{key} = ?")
#                 params.append(value)

#         if not set_clauses:
#             return False
            
#         sql = f"UPDATE Tasks SET {', '.join(set_clauses)} WHERE task_id = ?"
#         params.append(task_id)
        
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_task: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def delete_task(task_id: int) -> bool:
#     """Deletes a task. Returns True on success."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM Tasks WHERE task_id = ?", (task_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_task: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# # CRUD functions for Users
# def add_user(user_data: dict) -> str | None:
#     """
#     Adds a new user to the database.
#     Generates user_id (UUID), hashes password.
#     Returns the new user_id if successful, otherwise None.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         new_user_id = uuid.uuid4().hex
#         now = datetime.utcnow().isoformat() + "Z"
        
#         if 'password' not in user_data or not user_data['password']:
#             print("Password is required to create a user.")
#             return None
#         if 'username' not in user_data or not user_data['username']:
#             print("Username is required to create a user.")
#             return None
#         if 'email' not in user_data or not user_data['email']:
#             print("Email is required to create a user.")
#             return None
#         if 'role' not in user_data or not user_data['role']:
#             print("Role is required to create a user.")
#             return None

#         password_hash = hashlib.sha256(user_data['password'].encode('utf-8')).hexdigest()

#         sql = """
#             INSERT INTO Users (
#                 user_id, username, password_hash, full_name, email, role,
#                 is_active, created_at, updated_at, last_login_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             new_user_id,
#             user_data.get('username'),
#             password_hash,
#             user_data.get('full_name'),
#             user_data.get('email'),
#             user_data.get('role'),
#             user_data.get('is_active', True),
#             now,  # created_at
#             now,  # updated_at
#             user_data.get('last_login_at')
#         )
        
#         cursor.execute(sql, params)
#         conn.commit()
#         return new_user_id
#     except sqlite3.Error as e:
#         print(f"Database error in add_user: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_user_by_id(user_id: str) -> dict | None:
#     """Retrieves a user by their ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_user_by_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_user_by_email(email: str) -> dict | None:
#     """Retrieves a user by their email address."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Users WHERE email = ?", (email,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_user_by_email: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_user_by_username(username: str) -> dict | None:
#     """Retrieves a user by their username."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_user_by_username: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def update_user(user_id: str, user_data: dict) -> bool:
#     """
#     Updates an existing user's information.
#     If 'password' is in user_data, it will be hashed and updated.
#     Sets updated_at. Returns True on success.
#     """
#     conn = None
#     if not user_data:
#         return False

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         now = datetime.utcnow().isoformat() + "Z"
#         user_data['updated_at'] = now
        
#         if 'password' in user_data:
#             if user_data['password']: # Ensure password is not empty
#                 user_data['password_hash'] = hashlib.sha256(user_data.pop('password').encode('utf-8')).hexdigest()
#             else:
#                 user_data.pop('password') # Remove empty password from update data

#         set_clauses = []
#         params = []

#         valid_columns = ['username', 'password_hash', 'full_name', 'email', 'role', 'is_active', 'updated_at', 'last_login_at']
#         for key, value in user_data.items():
#             if key in valid_columns:
#                  set_clauses.append(f"{key} = ?")
#                  params.append(value)

#         if not set_clauses: # No valid fields to update (e.g. only empty password was provided)
#             return False

#         sql = f"UPDATE Users SET {', '.join(set_clauses)} WHERE user_id = ?"
#         params.append(user_id)

#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_user: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def verify_user_password(username: str, password: str) -> dict | None:
#     """
#     Verifies a user's password.
#     Returns user data (dict) if verification is successful, otherwise None.
#     """
#     user = get_user_by_username(username)
#     if user and user['is_active']: # Check if user exists and is active
#         password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
#         if password_hash == user['password_hash']:
#             # Optionally update last_login_at here if desired
#             # update_user(user['user_id'], {'last_login_at': datetime.utcnow().isoformat() + "Z"})
#             return user
#     return None

# def delete_user(user_id: str) -> bool:
#     """
#     Deletes a user (hard delete).
#     Returns True if deletion was successful.
#     Note: TeamMembers.user_id will be set to NULL due to ON DELETE SET NULL.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_user: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()


# # --- EmailReminders Functions ---
# def add_email_reminder(reminder_data: dict) -> int | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """INSERT INTO EmailReminders (scheduled_email_id, reminder_type, reminder_send_at, status)
#                  VALUES (?, ?, ?, ?)"""
#         params = (
#             reminder_data.get('scheduled_email_id'), reminder_data.get('reminder_type'),
#             reminder_data.get('reminder_send_at'), reminder_data.get('status', 'pending')
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e:
#         print(f"DB error in add_email_reminder: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_pending_reminders(before_time: str = None) -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM EmailReminders WHERE status = 'pending'"
#         params = []
#         if before_time:
#             sql += " AND reminder_send_at <= ?"
#             params.append(before_time)
#         sql += " ORDER BY reminder_send_at ASC"
#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows] # Consider joining with ScheduledEmails for context
#     except sqlite3.Error as e:
#         print(f"DB error in get_pending_reminders: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_reminder_status(reminder_id: int, status: str) -> bool:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "UPDATE EmailReminders SET status = ? WHERE reminder_id = ?"
#         cursor.execute(sql, (status, reminder_id))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"DB error in update_reminder_status: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_email_reminder(reminder_id: int) -> bool:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM EmailReminders WHERE reminder_id = ?", (reminder_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"DB error in delete_email_reminder: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# # --- ContactLists & ContactListMembers Functions ---
# def add_contact_list(list_data: dict) -> int | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         sql = """INSERT INTO ContactLists (list_name, description, created_by_user_id, created_at, updated_at)
#                  VALUES (?, ?, ?, ?, ?)"""
#         params = (
#             list_data.get('list_name'), list_data.get('description'),
#             list_data.get('created_by_user_id'), now, now
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e:
#         print(f"DB error in add_contact_list: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_contact_list_by_id(list_id: int) -> dict | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM ContactLists WHERE list_id = ?", (list_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"DB error in get_contact_list_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_all_contact_lists() -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM ContactLists ORDER BY list_name")
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"DB error in get_all_contact_lists: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_contact_list(list_id: int, list_data: dict) -> bool:
#     conn = None
#     if not list_data: return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         list_data['updated_at'] = datetime.utcnow().isoformat() + "Z"
#         set_clauses = [f"{key} = ?" for key in list_data.keys()]
#         params = list(list_data.values())
#         params.append(list_id)
#         sql = f"UPDATE ContactLists SET {', '.join(set_clauses)} WHERE list_id = ?"
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"DB error in update_contact_list: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_contact_list(list_id: int) -> bool:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # ON DELETE CASCADE handles ContactListMembers
#         cursor.execute("DELETE FROM ContactLists WHERE list_id = ?", (list_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"DB error in delete_contact_list: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def add_contact_to_list(list_id: int, contact_id: int) -> int | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "INSERT INTO ContactListMembers (list_id, contact_id) VALUES (?, ?)"
#         cursor.execute(sql, (list_id, contact_id))
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e: # Handles unique constraint violation
#         print(f"DB error in add_contact_to_list: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def remove_contact_from_list(list_id: int, contact_id: int) -> bool:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "DELETE FROM ContactListMembers WHERE list_id = ? AND contact_id = ?"
#         cursor.execute(sql, (list_id, contact_id))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"DB error in remove_contact_from_list: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def get_contacts_in_list(list_id: int) -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """SELECT c.*, clm.added_at
#                  FROM Contacts c
#                  JOIN ContactListMembers clm ON c.contact_id = clm.contact_id
#                  WHERE clm.list_id = ?"""
#         cursor.execute(sql, (list_id,))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"DB error in get_contacts_in_list: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# # CRUD functions for KPIs
# def add_kpi(kpi_data: dict) -> int | None:
#     """Adds a new KPI. Returns kpi_id or None."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         sql = """
#             INSERT INTO KPIs (
#                 project_id, name, value, target, trend, unit, created_at, updated_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             kpi_data.get('project_id'),
#             kpi_data.get('name'),
#             kpi_data.get('value'),
#             kpi_data.get('target'),
#             kpi_data.get('trend'),
#             kpi_data.get('unit'),
#             now,  # created_at
#             now   # updated_at
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e:
#         print(f"Database error in add_kpi: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_kpi_by_id(kpi_id: int) -> dict | None:
#     """Retrieves a KPI by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM KPIs WHERE kpi_id = ?", (kpi_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_kpi_by_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_kpis_for_project(project_id: str) -> list[dict]:
#     """Retrieves all KPIs for a given project_id."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM KPIs WHERE project_id = ?", (project_id,))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_kpis_for_project: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_kpi(kpi_id: int, kpi_data: dict) -> bool:
#     """Updates an existing KPI. Sets updated_at. Returns True on success."""
#     conn = None
#     if not kpi_data:
#         return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         kpi_data['updated_at'] = now

#         set_clauses = []
#         params = []

#         valid_columns = ['project_id', 'name', 'value', 'target', 'trend', 'unit', 'updated_at']
#         for key, value in kpi_data.items():
#             if key in valid_columns:
#                 set_clauses.append(f"{key} = ?")
#                 params.append(value)

#         if not set_clauses:
#             return False

#         sql = f"UPDATE KPIs SET {', '.join(set_clauses)} WHERE kpi_id = ?"
#         params.append(kpi_id)

#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_kpi: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def delete_kpi(kpi_id: int) -> bool:
#     """Deletes a KPI. Returns True on success."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM KPIs WHERE kpi_id = ?", (kpi_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_kpi: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# # --- ApplicationSettings Functions ---
def get_setting(key: str) -> str | None: # Will need similar refactoring if used during seeding with a passed cursor
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

# # --- ActivityLog Functions ---
# def add_activity_log(log_data: dict) -> int | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """INSERT INTO ActivityLog (user_id, action_type, details, related_entity_type,
#                                         related_entity_id, related_client_id, ip_address, user_agent)
#                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
#         params = (
#             log_data.get('user_id'), log_data.get('action_type'), log_data.get('details'),
#             log_data.get('related_entity_type'), log_data.get('related_entity_id'),
#             log_data.get('related_client_id'), log_data.get('ip_address'), log_data.get('user_agent')
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e:
#         print(f"DB error in add_activity_log: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_activity_logs(limit: int = 50, filters: dict = None) -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM ActivityLog"
#         params = []
#         where_clauses = []
#         if filters:
#             allowed = ['user_id', 'action_type', 'related_entity_type', 'related_entity_id', 'related_client_id']
#             for key, value in filters.items():
#                 if key in allowed and value is not None:
#                     where_clauses.append(f"{key} = ?")
#                     params.append(value)

#         if where_clauses:
#             sql += " WHERE " + " AND ".join(where_clauses)

#         sql += " ORDER BY created_at DESC LIMIT ?"
#         params.append(limit)

#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"DB error in get_activity_logs: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# # --- Default Templates Population ---
# # DEFAULT_COVER_PAGE_TEMPLATES constant moved to db_seed.py

# # --- CoverPageTemplates CRUD ---
# def add_cover_page_template(template_data: dict, cursor: sqlite3.Cursor = None) -> str | None:
#     """Adds a new cover page template. Returns template_id or None. Uses provided cursor if available."""
#     manage_connection = cursor is None
#     conn_internal = None
#     try:
#         if manage_connection:
#             conn_internal = get_db_connection()
#             cursor_to_use = conn_internal.cursor()
#         else:
#             if not isinstance(cursor, sqlite3.Cursor):
#                 raise ValueError("Invalid cursor object passed to add_cover_page_template.")
#             cursor_to_use = cursor

#         new_template_id = uuid.uuid4().hex
#         now = datetime.utcnow().isoformat() + "Z"

#         style_config = template_data.get('style_config_json')
#         if isinstance(style_config, dict):
#             style_config = json.dumps(style_config)

#         sql = """
#             INSERT INTO CoverPageTemplates (
#                 template_id, template_name, description, default_title, default_subtitle,
#                 default_author, style_config_json, is_default_template,
#                 created_at, updated_at, created_by_user_id
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             new_template_id,
#             template_data.get('template_name'),
#             template_data.get('description'),
#             template_data.get('default_title'),
#             template_data.get('default_subtitle'),
#             template_data.get('default_author'),
#             style_config,
#             template_data.get('is_default_template', 0),
#             now, now,
#             template_data.get('created_by_user_id')
#         )
#         cursor_to_use.execute(sql, params)

#         if manage_connection and conn_internal:
#             conn_internal.commit()

#         return new_template_id
#     except sqlite3.Error as e:
#         print(f"Database error in add_cover_page_template: {e}")
#         if manage_connection and conn_internal:
#             conn_internal.rollback()
#         return None
#     finally:
#         if manage_connection and conn_internal:
#             conn_internal.close()

# def get_cover_page_template_by_id(template_id: str) -> dict | None:
#     """Retrieves a cover page template by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM CoverPageTemplates WHERE template_id = ?", (template_id,))
#         row = cursor.fetchone()
#         if row:
#             data = dict(row)
#             if data.get('style_config_json'):
#                 try:
#                     data['style_config_json'] = json.loads(data['style_config_json'])
#                 except json.JSONDecodeError:
#                     print(f"Warning: Could not parse style_config_json for template {template_id}")
#             return data
#         return None
#     except sqlite3.Error as e:
#         print(f"Database error in get_cover_page_template_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_cover_page_template_by_name(template_name: str, cursor: sqlite3.Cursor = None) -> dict | None:
#     """
#     Retrieves a cover page template by its unique name.
#     Uses provided cursor if available, otherwise manages its own connection.
#     """
#     manage_connection = cursor is None
#     conn_internal = None
#     try:
#         if manage_connection:
#             conn_internal = get_db_connection()
#             cursor_to_use = conn_internal.cursor()
#         else:
#             if not isinstance(cursor, sqlite3.Cursor):
#                 raise ValueError("Invalid cursor object passed to get_cover_page_template_by_name.")
#             cursor_to_use = cursor

#         cursor_to_use.execute("SELECT * FROM CoverPageTemplates WHERE template_name = ?", (template_name,))
#         row = cursor_to_use.fetchone()
#         if row:
#             data = dict(row)
#             if data.get('style_config_json'):
#                 try:
#                     data['style_config_json'] = json.loads(data['style_config_json'])
#                 except json.JSONDecodeError:
#                     print(f"Warning: Could not parse style_config_json for template {template_name}")
#             return data
#         return None
#     except sqlite3.Error as e:
#         print(f"Database error in get_cover_page_template_by_name: {e}")
#         return None
#     finally:
#         if manage_connection and conn_internal:
#             conn_internal.close()

# def get_all_cover_page_templates(is_default: bool = None, limit: int = 100, offset: int = 0) -> list[dict]:
#     """
#     Retrieves all cover page templates, optionally filtered by is_default.
#     Includes pagination.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql = "SELECT * FROM CoverPageTemplates"
#         params = []

#         if is_default is not None:
#             sql += " WHERE is_default_template = ?"
#             params.append(1 if is_default else 0)

#         sql += " ORDER BY template_name LIMIT ? OFFSET ?"
#         params.extend([limit, offset])

#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         templates = []
#         for row in rows:
#             data = dict(row)
#             if data.get('style_config_json'):
#                 try:
#                     data['style_config_json'] = json.loads(data['style_config_json'])
#                 except json.JSONDecodeError:
#                     print(f"Warning: Could not parse style_config_json for template ID {data['template_id']}")
#             templates.append(data)
#         return templates
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_cover_page_templates: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_cover_page_template(template_id: str, update_data: dict) -> bool:
#     """Updates an existing cover page template."""
#     conn = None
#     if not update_data: return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         update_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

#         if 'style_config_json' in update_data and isinstance(update_data['style_config_json'], dict):
#             update_data['style_config_json'] = json.dumps(update_data['style_config_json'])

#         # Ensure boolean/integer fields are correctly formatted for SQL if needed
#         if 'is_default_template' in update_data:
#             update_data['is_default_template'] = 1 if update_data['is_default_template'] else 0

#         valid_columns = [
#             'template_name', 'description', 'default_title', 'default_subtitle',
#             'default_author', 'style_config_json', 'is_default_template', 'updated_at'
#             # created_by_user_id is typically not updated this way
#         ]

#         set_clauses = []
#         sql_params = []

#         for key, value in update_data.items():
#             if key in valid_columns:
#                 set_clauses.append(f"{key} = ?")
#                 sql_params.append(value)

#         if not set_clauses:
#             return False # Nothing valid to update

#         sql_params.append(template_id)
#         sql = f"UPDATE CoverPageTemplates SET {', '.join(set_clauses)} WHERE template_id = ?"

#         cursor.execute(sql, sql_params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_cover_page_template: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_cover_page_template(template_id: str) -> bool:
#     """Deletes a cover page template."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Consider impact on CoverPages using this template (ON DELETE SET NULL)
#         cursor.execute("DELETE FROM CoverPageTemplates WHERE template_id = ?", (template_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_cover_page_template: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# # --- CoverPages CRUD ---
# def add_cover_page(cover_data: dict) -> str | None:
#     """Adds a new cover page instance. Returns cover_page_id or None."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         new_cover_id = uuid.uuid4().hex
#         now = datetime.utcnow().isoformat() + "Z"

#         custom_style_config = cover_data.get('custom_style_config_json')
#         if isinstance(custom_style_config, dict):
#             custom_style_config = json.dumps(custom_style_config)

#         sql = """
#             INSERT INTO CoverPages (
#                 cover_page_id, cover_page_name, client_id, project_id, template_id,
#                 title, subtitle, author_text, institution_text, department_text,
#                 document_type_text, document_version, creation_date,
#                 logo_name, logo_data, custom_style_config_json,
#                 created_at, updated_at, created_by_user_id
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             new_cover_id,
#             cover_data.get('cover_page_name'),
#             cover_data.get('client_id'),
#             cover_data.get('project_id'),
#             cover_data.get('template_id'),
#             cover_data.get('title'),
#             cover_data.get('subtitle'),
#             cover_data.get('author_text'),
#             cover_data.get('institution_text'),
#             cover_data.get('department_text'),
#             cover_data.get('document_type_text'),
#             cover_data.get('document_version'),
#             cover_data.get('creation_date'),
#             cover_data.get('logo_name'),
#             cover_data.get('logo_data'),
#             custom_style_config,
#             now, now,
#             cover_data.get('created_by_user_id')
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return new_cover_id
#     except sqlite3.Error as e:
#         print(f"Database error in add_cover_page: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_cover_page_by_id(cover_page_id: str) -> dict | None:
#     """Retrieves a cover page instance by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM CoverPages WHERE cover_page_id = ?", (cover_page_id,))
#         row = cursor.fetchone()
#         if row:
#             data = dict(row)
#             if data.get('custom_style_config_json'):
#                 try:
#                     data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
#                 except json.JSONDecodeError:
#                     print(f"Warning: Could not parse custom_style_config_json for cover page {cover_page_id}")
#             return data
#         return None
#     except sqlite3.Error as e:
#         print(f"Database error in get_cover_page_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_cover_pages_for_client(client_id: str) -> list[dict]:
#     """Retrieves all cover pages for a specific client."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM CoverPages WHERE client_id = ? ORDER BY created_at DESC", (client_id,))
#         rows = cursor.fetchall()
#         cover_pages = []
#         for row in rows:
#             data = dict(row)
#             # JSON parsing similar to get_cover_page_by_id if needed
#             cover_pages.append(data)
#         return cover_pages
#     except sqlite3.Error as e:
#         print(f"Database error in get_cover_pages_for_client: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_cover_pages_for_project(project_id: str) -> list[dict]:
#     """Retrieves all cover pages for a specific project."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM CoverPages WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
#         rows = cursor.fetchall()
#         cover_pages = []
#         for row in rows:
#             data = dict(row)
#             # JSON parsing similar to get_cover_page_by_id if needed
#             cover_pages.append(data)
#         return cover_pages
#     except sqlite3.Error as e:
#         print(f"Database error in get_cover_pages_for_project: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_cover_page(cover_page_id: str, update_data: dict) -> bool:
#     """Updates an existing cover page instance."""
#     conn = None
#     if not update_data: return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         update_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

#         if 'custom_style_config_json' in update_data and isinstance(update_data['custom_style_config_json'], dict):
#             update_data['custom_style_config_json'] = json.dumps(update_data['custom_style_config_json'])

#         set_clauses = [f"{key} = ?" for key in update_data.keys() if key != 'cover_page_id']
#         params = [update_data[key] for key in update_data.keys() if key != 'cover_page_id']
#         params.append(cover_page_id)

#         sql = f"UPDATE CoverPages SET {', '.join(set_clauses)} WHERE cover_page_id = ?"
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_cover_page: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_cover_page(cover_page_id: str) -> bool:
#     """Deletes a cover page instance."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM CoverPages WHERE cover_page_id = ?", (cover_page_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_cover_page: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def get_cover_pages_for_user(user_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
#     """Retrieves cover pages created by a specific user, with pagination."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Querying by 'created_by_user_id' as per the CoverPages table schema
#         sql = "SELECT * FROM CoverPages WHERE created_by_user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?"
#         params = (user_id, limit, offset)
#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         # It's good practice to parse JSON fields here if any, similar to other get functions
#         cover_pages = []
#         for row in rows:
#             data = dict(row)
#             if data.get('custom_style_config_json'):
#                 try:
#                     data['custom_style_config_json'] = json.loads(data['custom_style_config_json'])
#                 except json.JSONDecodeError:
#                     print(f"Warning: Could not parse custom_style_config_json for cover page {data['cover_page_id']}")
#             cover_pages.append(data)
#         return cover_pages
#     except sqlite3.Error as e:
#         print(f"Database error in get_cover_pages_for_user: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# # --- Lookup Table GET Functions ---
# def get_all_countries() -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Countries ORDER BY country_name")
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"DB error in get_all_countries: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_country_by_id(country_id: int) -> dict | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Countries WHERE country_id = ?", (country_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"DB error in get_country_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_country_by_name(country_name: str) -> dict | None:
#     """Retrieves a country by its name. Returns a dict or None if not found."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Countries WHERE country_name = ?", (country_name,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_country_by_name: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def add_country(country_data: dict) -> int | None:
#     """
#     Adds a new country to the Countries table.
#     Expects country_data to contain 'country_name'.
#     Returns the country_id of the newly added or existing country.
#     Returns None if an unexpected error occurs.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         country_name = country_data.get('country_name')
#         if not country_name:
#             print("Error: 'country_name' is required to add a country.")
#             return None

#         try:
#             cursor.execute("INSERT INTO Countries (country_name) VALUES (?)", (country_name,))
#             conn.commit()
#             return cursor.lastrowid
#         except sqlite3.IntegrityError:
#             # Country name already exists, fetch its ID
#             print(f"Country '{country_name}' already exists. Fetching its ID.")
#             cursor.execute("SELECT country_id FROM Countries WHERE country_name = ?", (country_name,))
#             row = cursor.fetchone()
#             return row['country_id'] if row else None

#     except sqlite3.Error as e:
#         print(f"Database error in add_country: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_all_cities(country_id: int = None) -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM Cities"
#         params = []
#         if country_id is not None:
#             sql += " WHERE country_id = ?"
#             params.append(country_id)
#         sql += " ORDER BY city_name"
#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"DB error in get_all_cities: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def add_city(city_data: dict) -> int | None:
#     """
#     Adds a new city to the Cities table.
#     Expects city_data to contain 'country_id' and 'city_name'.
#     Returns the city_id of the newly added or existing city.
#     Returns None if an unexpected error occurs or if country_id or city_name is missing.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         country_id = city_data.get('country_id')
#         city_name = city_data.get('city_name')

#         if not country_id or not city_name:
#             print("Error: 'country_id' and 'city_name' are required to add a city.")
#             return None

#         try:
#             # Check if city already exists for this country to avoid IntegrityError for composite uniqueness if not explicitly handled by schema (though schema doesn't show composite unique constraint for city_name+country_id, it's good practice)
#             # However, the current schema for Cities does not have a UNIQUE constraint on (country_id, city_name).
#             # It only has city_id as PK and country_id as FK.
#             # So, we will just insert. If a stricter uniqueness is needed, the table schema should be updated.
#             cursor.execute("INSERT INTO Cities (country_id, city_name) VALUES (?, ?)", (country_id, city_name))
#             conn.commit()
#             return cursor.lastrowid
#         except sqlite3.IntegrityError:
#             # This part would be relevant if there was a UNIQUE constraint on (country_id, city_name)
#             # For now, this block might not be hit unless city_name itself becomes unique across all countries (which is not typical)
#             print(f"IntegrityError likely means city '{city_name}' under country_id '{country_id}' already exists or other constraint failed.")
#             # If it were unique and we wanted to return existing:
#             # cursor.execute("SELECT city_id FROM Cities WHERE country_id = ? AND city_name = ?", (country_id, city_name))
#             # row = cursor.fetchone()
#             # return row['city_id'] if row else None
#             return None # For now, any IntegrityError is treated as a failure to add as new.

#     except sqlite3.Error as e:
#         print(f"Database error in add_city: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_city_by_name_and_country_id(city_name: str, country_id: int) -> dict | None:
#     """Retrieves a specific city by name for a given country_id."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Cities WHERE city_name = ? AND country_id = ?", (city_name, country_id))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_city_by_name_and_country_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_city_by_id(city_id: int) -> dict | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Cities WHERE city_id = ?", (city_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"DB error in get_city_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_all_templates(template_type_filter: str = None, language_code_filter: str = None) -> list[dict]:
#     """
#     Retrieves all templates, optionally filtered by template_type and/or language_code.
#     If template_type_filter is None, retrieves all templates regardless of type.
#     If language_code_filter is None, retrieves for all languages.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM Templates"
#         params = []
#         where_clauses = []

#         if template_type_filter:
#             where_clauses.append("template_type = ?")
#             params.append(template_type_filter)
#         if language_code_filter:
#             where_clauses.append("language_code = ?")
#             params.append(language_code_filter)

#         if where_clauses:
#             sql += " WHERE " + " AND ".join(where_clauses)

#         sql += " ORDER BY template_name, language_code"
#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_templates: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_distinct_languages_for_template_type(template_type: str) -> list[str]:
#     """
#     Retrieves a list of distinct language codes available for a given template type.
#     """
#     conn = None
#     languages = []
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT DISTINCT language_code FROM Templates WHERE template_type = ? ORDER BY language_code ASC", (template_type,))
#         rows = cursor.fetchall()
#         languages = [row['language_code'] for row in rows if row['language_code']] # Ensure not None
#     except sqlite3.Error as e:
#         print(f"Database error in get_distinct_languages_for_template_type for type '{template_type}': {e}")
#         # Return empty list on error
#     finally:
#         if conn:
#             conn.close()
#     return languages

# def get_all_file_based_templates() -> list[dict]:
#     """Retrieves all templates that have a base_file_name, suitable for document creation."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Selects templates that are likely file-based documents
#         # Changed 'category' to 'category_id'.
#         # If category_name is needed here, a JOIN with TemplateCategories would be required.
#         sql = "SELECT template_id, template_name, language_code, base_file_name, description, category_id FROM Templates WHERE base_file_name IS NOT NULL AND base_file_name != '' ORDER BY template_name, language_code"
#         cursor.execute(sql)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_file_based_templates: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_templates_by_category_id(category_id: int) -> list[dict]:
#     """Retrieves all templates for a given category_id."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Templates WHERE category_id = ? ORDER BY template_name, language_code", (category_id,))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_templates_by_category_id: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_all_products_for_selection_filtered(language_code: str = None, name_pattern: str = None) -> list[dict]:
#     """
#     Retrieves active products for selection, optionally filtered by language_code
#     and/or name_pattern (searches product_name and description).
#     Orders by product_name.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql_params = []
#         # Start with base selection of active products
#         sql_where_clauses = ["is_active = TRUE"]

#         if language_code:
#             sql_where_clauses.append("language_code = ?")
#             sql_params.append(language_code)

#         if name_pattern:
#             # The name_pattern should be passed with wildcards already, e.g., "%search_term%"
#             sql_where_clauses.append("(product_name LIKE ? OR description LIKE ?)")
#             sql_params.append(name_pattern)
#             sql_params.append(name_pattern)

#         sql = f"""
#             SELECT product_id, product_name, description, base_unit_price, language_code
#             FROM Products
#             WHERE {' AND '.join(sql_where_clauses)}
#             ORDER BY product_name
#         """

#         cursor.execute(sql, tuple(sql_params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_products_for_selection_filtered: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_all_tasks(active_only: bool = False, project_id_filter: str = None) -> list[dict]:
#     """
#     Retrieves all tasks, optionally filtering for active tasks only and/or by project_id.
#     Active tasks are those not linked to a status marked as completion or archival.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT t.* FROM Tasks t"
#         params = []
#         where_clauses = []

#         if active_only:
#             sql += """
#                 LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id
#             """
#             where_clauses.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")

#         if project_id_filter:
#             where_clauses.append("t.project_id = ?")
#             params.append(project_id_filter)

#         if where_clauses:
#             sql += " WHERE " + " AND ".join(where_clauses)

#         sql += " ORDER BY t.created_at DESC" # Or some other meaningful order

#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_tasks: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_tasks_by_assignee_id(assignee_team_member_id: int, active_only: bool = False) -> list[dict]:
#     """
#     Retrieves tasks assigned to a specific team member, optionally filtering for active tasks.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT t.* FROM Tasks t"
#         params = []
#         where_clauses = ["t.assignee_team_member_id = ?"]
#         params.append(assignee_team_member_id)

#         if active_only:
#             sql += """
#                 LEFT JOIN StatusSettings ss ON t.status_id = ss.status_id
#             """
#             where_clauses.append("(ss.is_completion_status IS NOT TRUE AND ss.is_archival_status IS NOT TRUE)")

#         if where_clauses: # Will always be true because of assignee_team_member_id
#             sql += " WHERE " + " AND ".join(where_clauses)

#         sql += " ORDER BY t.due_date ASC, t.priority DESC"

#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_tasks_by_assignee_id: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_all_status_settings(status_type: str = None) -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings" # Ensure icon_name is fetched
#         params = []
#         if status_type:
#             sql += " WHERE status_type = ?"
#             params.append(status_type)
#         sql += " ORDER BY status_type, status_name"
#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"DB error in get_all_status_settings: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_status_setting_by_id(status_id: int) -> dict | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings WHERE status_id = ?", (status_id,)) # Ensure icon_name is fetched
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"DB error in get_status_setting_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_status_setting_by_name(status_name: str, status_type: str) -> dict | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT status_id, status_name, status_type, color_hex, icon_name, default_duration_days, is_archival_status, is_completion_status FROM StatusSettings WHERE status_name = ? AND status_type = ?", (status_name, status_type)) # Ensure icon_name is fetched
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"DB error in get_status_setting_by_name: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# # CRUD functions for SAVTickets
# def add_sav_ticket(ticket_data: dict) -> str | None:
#     """Adds a new SAV ticket. Returns ticket_id (UUID) or None."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         new_ticket_id = str(uuid.uuid4())
#         now = datetime.utcnow().isoformat() + "Z"

#         sql = """
#             INSERT INTO SAVTickets (
#                 ticket_id, client_id, client_project_product_id, issue_description,
#                 status_id, assigned_technician_id, resolution_details,
#                 opened_at, closed_at, created_by_user_id
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             new_ticket_id,
#             ticket_data.get('client_id'),
#             ticket_data.get('client_project_product_id'),
#             ticket_data.get('issue_description'),
#             ticket_data.get('status_id'),
#             ticket_data.get('assigned_technician_id'),
#             ticket_data.get('resolution_details'),
#             ticket_data.get('opened_at', now), # Default to now if not provided
#             ticket_data.get('closed_at'),
#             ticket_data.get('created_by_user_id')
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return new_ticket_id
#     except sqlite3.Error as e:
#         print(f"Database error in add_sav_ticket: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_sav_ticket_by_id(ticket_id: str) -> dict | None:
#     """Retrieves an SAV ticket by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM SAVTickets WHERE ticket_id = ?", (ticket_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_sav_ticket_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_sav_tickets_for_client(client_id: str, status_id: int = None) -> list[dict]:
#     """Retrieves SAV tickets for a client, optionally filtered by status_id."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM SAVTickets WHERE client_id = ?"
#         params = [client_id]
#         if status_id is not None:
#             sql += " AND status_id = ?"
#             params.append(status_id)
#         sql += " ORDER BY opened_at DESC"
#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_sav_tickets_for_client: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_sav_ticket(ticket_id: str, update_data: dict) -> bool:
#     """Updates an SAV ticket. Returns True on success."""
#     conn = None
#     if not update_data: return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # Add closed_at timestamp automatically if status is changed to a completion/archival one
#         if 'status_id' in update_data:
#             status_info = get_status_setting_by_id(update_data['status_id'])
#             if status_info and (status_info['is_completion_status'] or status_info['is_archival_status']):
#                 if 'closed_at' not in update_data: # Only set if not already being explicitly set
#                     update_data['closed_at'] = datetime.utcnow().isoformat() + "Z"
#             elif 'closed_at' not in update_data: # If moving to a non-closed status, ensure closed_at is NULL unless specified
#                  # This logic might need refinement: if explicitly setting closed_at to null, allow it.
#                  # If status moves to open and closed_at is not in update_data, set it to NULL.
#                  current_ticket = get_sav_ticket_by_id(ticket_id)
#                  if current_ticket and current_ticket.get('closed_at') is not None:
#                     update_data['closed_at'] = None


#         valid_columns = [
#             'client_project_product_id', 'issue_description', 'status_id',
#             'assigned_technician_id', 'resolution_details', 'opened_at', 'closed_at'
#             # client_id and created_by_user_id are generally not updated post-creation
#         ]
#         set_clauses = []
#         params_list = []
#         for key, value in update_data.items():
#             if key in valid_columns:
#                 set_clauses.append(f"{key} = ?")
#                 params_list.append(value)

#         if not set_clauses: return False

#         params_list.append(ticket_id)
#         sql = f"UPDATE SAVTickets SET {', '.join(set_clauses)} WHERE ticket_id = ?"

#         cursor.execute(sql, tuple(params_list))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_sav_ticket: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_sav_ticket(ticket_id: str) -> bool:
#     """Deletes an SAV ticket. Consider if soft delete is more appropriate in a real app."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM SAVTickets WHERE ticket_id = ?", (ticket_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_sav_ticket: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# # CRUD functions for ImportantDates
# def add_important_date(date_data: dict) -> int | None:
#     """Adds a new important date. Returns important_date_id or None."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         sql = """
#             INSERT INTO ImportantDates (
#                 date_name, date_value, is_recurring_annually, language_code,
#                 email_template_id, created_at, updated_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             date_data.get('date_name'),
#             date_data.get('date_value'),
#             date_data.get('is_recurring_annually', True),
#             date_data.get('language_code'),
#             date_data.get('email_template_id'),
#             now, now
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.IntegrityError as ie: # Handles UNIQUE constraint
#         print(f"Database IntegrityError in add_important_date: {ie}")
#         return None
#     except sqlite3.Error as e:
#         print(f"Database error in add_important_date: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_important_date_by_id(date_id: int) -> dict | None:
#     """Retrieves an important date by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM ImportantDates WHERE important_date_id = ?", (date_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_important_date_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_all_important_dates(upcoming_only: bool = False) -> list[dict]:
#     """
#     Retrieves all important dates.
#     If upcoming_only is True, filters for dates from today onwards,
#     or recurring dates whose month/day is upcoming.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM ImportantDates"
#         params = []
#         if upcoming_only:
#             today_str = datetime.utcnow().strftime('%Y-%m-%d')
#             today_month_day = datetime.utcnow().strftime('%m-%d')
#             # Non-recurring dates: date_value >= today
#             # Recurring dates: month-day of date_value >= month-day of today
#             sql += """
#                 WHERE (is_recurring_annually = FALSE AND date_value >= ?)
#                    OR (is_recurring_annually = TRUE AND SUBSTR(date_value, 6) >= ?)
#             """
#             params.extend([today_str, today_month_day])

#         sql += " ORDER BY date_value ASC" # Or by month/day for recurring
#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_important_dates: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_important_date(date_id: int, update_data: dict) -> bool:
#     """Updates an important date. Returns True on success."""
#     conn = None
#     if not update_data: return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         update_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

#         valid_columns = [
#             'date_name', 'date_value', 'is_recurring_annually',
#             'language_code', 'email_template_id', 'updated_at'
#         ]
#         set_clauses = []
#         params_list = []
#         for key, value in update_data.items():
#             if key in valid_columns:
#                 set_clauses.append(f"{key} = ?")
#                 params_list.append(value)

#         if not set_clauses: return False

#         params_list.append(date_id)
#         sql = f"UPDATE ImportantDates SET {', '.join(set_clauses)} WHERE important_date_id = ?"

#         cursor.execute(sql, tuple(params_list))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.IntegrityError as ie:
#         print(f"Database IntegrityError in update_important_date: {ie}")
#         return False
#     except sqlite3.Error as e:
#         print(f"Database error in update_important_date: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_important_date(date_id: int) -> bool:
#     """Deletes an important date."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM ImportantDates WHERE important_date_id = ?", (date_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_important_date: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def get_db_connection():
#     """
#     Returns a new database connection object.
#     The connection is configured to return rows as dictionary-like objects.
#     """
#     conn = sqlite3.connect(DATABASE_PATH) # Updated to use DATABASE_PATH
#     conn.row_factory = sqlite3.Row
#     return conn

# # CRUD functions for Clients
# def add_client(client_data: dict) -> str | None:
#     """
#     Adds a new client to the database.
#     Returns the new client_id if successful, otherwise None.
#     Ensures created_at and updated_at are set.
#     Expects 'category_id' instead of 'category' text.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         new_client_id = uuid.uuid4().hex
#         now = datetime.utcnow().isoformat() + "Z"

#         # Ensure all required fields are present, or provide defaults
#         sql = """
#             INSERT INTO Clients (
#                 client_id, client_name, company_name, primary_need_description, project_identifier,
#                 country_id, city_id, default_base_folder_path, status_id,
#                 selected_languages, notes, category, distributor_specific_info,
#                 created_at, updated_at, created_by_user_id
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             new_client_id,
#             client_data.get('client_name'),
#             client_data.get('company_name'),
#             client_data.get('primary_need_description'),
#             client_data.get('project_identifier'),
#             client_data.get('country_id'),
#             client_data.get('city_id'),
#             client_data.get('default_base_folder_path'),
#             client_data.get('status_id'),
#             client_data.get('selected_languages'),
#             client_data.get('notes'),
#             client_data.get('category'),
#             client_data.get('distributor_specific_info'), # Handled by .get if missing, defaults to None
#             now,  # created_at
#             now,  # updated_at
#             client_data.get('created_by_user_id')
#         )

#         cursor.execute(sql, params)
#         conn.commit()
#         return new_client_id
#     except sqlite3.Error as e:
#         print(f"Database error in add_client: {e}")
#         # Consider raising a custom exception or logging more formally
#         return None
#     finally:
#         if conn:
#             conn.close()


# def get_or_add_country(country_name: str) -> dict | None:
#     """
#     Retrieves a country by its name. If not found, adds it to the database.
#     Returns the country data as a dictionary (including 'country_id' and 'country_name')
#     if found or successfully added, otherwise None.
#     """
#     if not country_name or not country_name.strip():
#         print("Error in get_or_add_country: country_name cannot be empty.")
#         return None

#     country_name_stripped = country_name.strip()

#     try:
#         existing_country = get_country_by_name(country_name_stripped)
#         if existing_country:
#             print(f"Country '{country_name_stripped}' found with ID: {existing_country.get('country_id')}")
#             return existing_country

#         print(f"Country '{country_name_stripped}' not found. Attempting to add it.")

#         new_country_id = add_country({'country_name': country_name_stripped})

#         if new_country_id is not None:
#             print(f"Country '{country_name_stripped}' processed by add_country. ID (new or existing): {new_country_id}.")
#             # add_country should return the ID of the new or existing (if UNIQUE constraint hit) country.
#             # Now, fetch the country data using this ID.
#             country_data = get_country_by_id(new_country_id)
#             if country_data:
#                 return country_data
#             else:
#                 # This would be unusual if new_country_id is valid.
#                 print(f"Error in get_or_add_country: Could not retrieve details for country ID {new_country_id} after add_country call.")
#                 return None
#         else:
#             # This implies add_country itself failed to return a valid ID, which is unexpected given its logic.
#             print(f"Error in get_or_add_country: add_country returned None for '{country_name_stripped}'.")
#             # As a fallback, try one last time to get by name, in case of race or other non-obvious scenario.
#             final_check_country = get_country_by_name(country_name_stripped)
#             if final_check_country:
#                 print(f"Final check: Country '{country_name_stripped}' now exists. Returning its data.")
#                 return final_check_country
#             return None

#     except sqlite3.Error as e: # Should ideally be caught by underlying functions
#         print(f"Database error in get_or_add_country for '{country_name_stripped}': {e}")
#         return None
#     except Exception as ex:
#         print(f"Unexpected error in get_or_add_country for '{country_name_stripped}': {ex}")
#         return None



# def get_client_segmentation_by_city() -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """
#             SELECT
#                 co.country_name,
#                 ci.city_name,
#                 COUNT(cl.client_id) as client_count
#             FROM Clients cl
#             JOIN Cities ci ON cl.city_id = ci.city_id
#             JOIN Countries co ON ci.country_id = co.country_id
#             GROUP BY co.country_name, ci.city_name
#             HAVING COUNT(cl.client_id) > 0
#             ORDER BY co.country_name, client_count DESC, ci.city_name
#         """
#         cursor.execute(sql)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_client_segmentation_by_city: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_client_segmentation_by_status() -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """
#             SELECT
#                 ss.status_name,
#                 COUNT(cl.client_id) as client_count
#             FROM Clients cl
#             JOIN StatusSettings ss ON cl.status_id = ss.status_id
#             GROUP BY ss.status_name
#             HAVING COUNT(cl.client_id) > 0
#             ORDER BY client_count DESC, ss.status_name
#         """
#         cursor.execute(sql)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_client_segmentation_by_status: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_client_segmentation_by_category() -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Assumes Clients.category is a simple text field.
#         # If category were an ID linking to another table, the query would need a JOIN.
#         sql = """
#             SELECT
#                 cl.category,
#                 COUNT(cl.client_id) as client_count
#             FROM Clients cl
#             WHERE cl.category IS NOT NULL AND cl.category != ''
#             GROUP BY cl.category
#             HAVING COUNT(cl.client_id) > 0
#             ORDER BY client_count DESC, cl.category
#         """
#         cursor.execute(sql)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_client_segmentation_by_category: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()


# def get_client_counts_by_country() -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # This query assumes Clients table has country_id and Countries table has country_id and country_name
#         sql = """
#             SELECT
#                 co.country_name,
#                 COUNT(cl.client_id) as client_count
#             FROM Clients cl
#             JOIN Countries co ON cl.country_id = co.country_id
#             GROUP BY co.country_name
#             HAVING COUNT(cl.client_id) > 0
#             ORDER BY client_count DESC
#         """
#         cursor.execute(sql)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_client_counts_by_country: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_client_by_id(client_id: str) -> dict | None:
#     """Retrieves a client by their ID. Returns a dict or None if not found."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Clients WHERE client_id = ?", (client_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_client_by_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_all_clients(filters: dict = None) -> list[dict]:
#     """
#     Retrieves all clients, optionally applying filters.
#     Filters can be e.g. {'status_id': 1, 'category': 'VIP'}.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql = "SELECT * FROM Clients"
#         params = []

#         if filters:
#             where_clauses = []
#             for key, value in filters.items():
#                 # Basic protection against non-column names; ideally, validate keys against known columns
#                 if key in ['client_name', 'company_name', 'country_id', 'city_id', 'status_id', 'category', 'created_by_user_id']: # Add other filterable columns
#                     where_clauses.append(f"{key} = ?")
#                     params.append(value)
#             if where_clauses:
#                 sql += " WHERE " + " AND ".join(where_clauses)

#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_clients: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_client(client_id: str, client_data: dict) -> bool:
#     """
#     Updates an existing client's information.
#     Ensures updated_at is set to the current timestamp.
#     Returns True if update was successful, False otherwise.
#     """
#     conn = None
#     if not client_data:
#         return False # Nothing to update

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         now = datetime.utcnow().isoformat() + "Z"
#         client_data['updated_at'] = now

#         set_clauses = []
#         params = []

#         for key, value in client_data.items():
#             # Validate keys against actual column names to prevent SQL injection if keys are from unsafe source
#             if key in ['client_name', 'company_name', 'primary_need_description', 'project_identifier',
#                        'country_id', 'city_id', 'default_base_folder_path', 'status_id',
#                        'selected_languages', 'price', 'notes', 'category', 'distributor_specific_info',
#                        'updated_at', 'created_by_user_id']: # client_id should not be updated here
#                  set_clauses.append(f"{key} = ?")
#                  params.append(value)

#         if not set_clauses:
#             return False # No valid fields to update

#         sql = f"UPDATE Clients SET {', '.join(set_clauses)} WHERE client_id = ?"
#         params.append(client_id)

#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_client: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def delete_client(client_id: str) -> bool:
#     """
#     Deletes a client from the database.
#     Returns True if deletion was successful, False otherwise.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM Clients WHERE client_id = ?", (client_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_client: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def get_all_clients_with_details():
#     # Ensure status_type = 'Client' is part of the JOIN or WHERE clause if status_id is not unique across types
#     query = """
#     SELECT
#         c.client_id, c.client_name, c.company_name, c.primary_need_description,
#         c.project_identifier, c.default_base_folder_path, c.selected_languages,
#         c.price, c.notes, c.created_at, c.category, c.distributor_specific_info, -- Ensure new column is selected
#         c.status_id, c.country_id, c.city_id,
#         co.country_name AS country,
#         ci.city_name AS city,
#         s.status_name AS status
#     FROM clients c
#     LEFT JOIN countries co ON c.country_id = co.country_id
#     LEFT JOIN cities ci ON c.city_id = ci.city_id
#     LEFT JOIN status_settings s ON c.status_id = s.status_id AND s.status_type = 'Client'
#     ORDER BY c.client_name;
#     """
#     conn = None
#     try:
#         conn = get_db_connection() # Assumes get_db_connection sets row_factory = sqlite3.Row
#         cursor = conn.cursor()
#         cursor.execute(query)
#         rows = cursor.fetchall()
#         # Column names are directly keys in the dicts due to conn.row_factory = sqlite3.Row
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_clients_with_details: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_active_clients_count() -> int:
#     """
#     Retrieves the count of active clients.
#     An active client is one whose status is not marked as 'is_archival_status = TRUE'.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Select clients whose status_id is not in the set of archival statuses,
#         # or clients who have no status_id (considered active by default).
#         sql = """
#             SELECT COUNT(c.client_id) as active_count
#             FROM Clients c
#             LEFT JOIN StatusSettings ss ON c.status_id = ss.status_id
#             WHERE ss.is_archival_status IS NOT TRUE OR c.status_id IS NULL
#         """
#         cursor.execute(sql)
#         row = cursor.fetchone()
#         return row['active_count'] if row else 0
#     except sqlite3.Error as e:
#         print(f"Database error in get_active_clients_count: {e}")
#         return 0 # Return 0 in case of error
#     finally:
#         if conn:
#             conn.close()

# Client notes functions are now in clients_crud.py


# # CRUD functions for Companies
# def add_company(company_data: dict) -> str | None:
#     """Adds a new company. Generates UUID for company_id. Handles created_at, updated_at."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         new_company_id = str(uuid.uuid4())

#         sql = """
#             INSERT INTO Companies (
#                 company_id, company_name, address, payment_info, logo_path,
#                 other_info, is_default, created_at, updated_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             new_company_id,
#             company_data.get('company_name'),
#             company_data.get('address'),
#             company_data.get('payment_info'),
#             company_data.get('logo_path'),
#             company_data.get('other_info'),
#             company_data.get('is_default', False),
#             now,  # created_at
#             now   # updated_at
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return new_company_id
#     except sqlite3.Error as e:
#         print(f"Database error in add_company: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_company_by_id(company_id: str) -> dict | None:
#     """Fetches a company by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Companies WHERE company_id = ?", (company_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_company_by_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_all_companies() -> list[dict]:
#     """Fetches all companies."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Companies ORDER BY company_name")
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_companies: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_company(company_id: str, company_data: dict) -> bool:
#     """Updates company details. Manages updated_at."""
#     conn = None
#     if not company_data:
#         return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         company_data['updated_at'] = now

#         set_clauses = [f"{key} = ?" for key in company_data.keys() if key != 'company_id']
#         params = [value for key, value in company_data.items() if key != 'company_id']

#         if not set_clauses:
#             return False # No valid fields to update

#         params.append(company_id)
#         sql = f"UPDATE Companies SET {', '.join(set_clauses)} WHERE company_id = ?"

#         cursor.execute(sql, tuple(params))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_company: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def delete_company(company_id: str) -> bool:
#     """Deletes a company."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # ON DELETE CASCADE will handle CompanyPersonnel
#         cursor.execute("DELETE FROM Companies WHERE company_id = ?", (company_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_company: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def set_default_company(company_id: str) -> bool:
#     """Sets a company as default, ensuring only one company can be default."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         conn.isolation_level = None # Start transaction
#         cursor.execute("BEGIN")
#         # Unset other defaults
#         cursor.execute("UPDATE Companies SET is_default = FALSE WHERE is_default = TRUE AND company_id != ?", (company_id,))
#         # Set the new default
#         cursor.execute("UPDATE Companies SET is_default = TRUE WHERE company_id = ?", (company_id,))
#         conn.commit()
#         return True
#     except sqlite3.Error as e:
#         if conn:
#             conn.rollback()
#         print(f"Database error in set_default_company: {e}")
#         return False
#     finally:
#         if conn:
#             conn.isolation_level = '' # Reset isolation level
#             conn.close()

# def get_default_company() -> dict | None:
#     """
#     Retrieves the company marked as default.
#     Returns company data as a dictionary if found, otherwise None.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Companies WHERE is_default = TRUE")
#         row = cursor.fetchone()
#         if row:
#             return dict(row)
#         return None
#     except sqlite3.Error as e:
#         print(f"Database error in get_default_company: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# # CRUD functions for CompanyPersonnel
# def add_company_personnel(personnel_data: dict) -> int | None: # Keep signature, expect phone/email in dict
#     """Inserts new personnel linked to a company. Returns personnel_id."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         sql = """
#             INSERT INTO CompanyPersonnel (company_id, name, role, phone, email, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             personnel_data.get('company_id'),
#             personnel_data.get('name'),
#             personnel_data.get('role'),
#             personnel_data.get('phone'), # Get from dict
#             personnel_data.get('email'), # Get from dict
#             now
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e:
#         print(f"Database error in add_company_personnel: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_personnel_for_company(company_id: str, role: str = None) -> list[dict]:
#     """Fetches personnel for a company, optionally filtering by role."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM CompanyPersonnel WHERE company_id = ?"
#         params = [company_id]
#         if role:
#             sql += " AND role = ?"
#             params.append(role)
#         sql += " ORDER BY name"
#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_personnel_for_company: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_company_personnel(personnel_id: int, personnel_data: dict) -> bool:
#     """Updates personnel details."""
#     conn = None
#     if not personnel_data:
#         return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # We don't update created_at, but if there was an updated_at for this table:
#         # personnel_data['updated_at'] = datetime.utcnow().isoformat() + "Z"

#         # Define valid columns to prevent malicious or accidental updates to PK or FKs if they were in dict
#         valid_update_columns = ['name', 'role', 'phone', 'email']

#         set_clauses = []
#         params = []
#         for key, value in personnel_data.items():
#             if key in valid_update_columns:
#                 set_clauses.append(f"{key} = ?")
#                 params.append(value)

#         if not set_clauses:
#             return False

#         params.append(personnel_id)
#         sql = f"UPDATE CompanyPersonnel SET {', '.join(set_clauses)} WHERE personnel_id = ?"

#         cursor.execute(sql, tuple(params))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_company_personnel: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def delete_company_personnel(personnel_id: int) -> bool:
#     """Deletes a personnel entry."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM CompanyPersonnel WHERE personnel_id = ?", (personnel_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_company_personnel: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# # CRUD functions for TemplateCategories
# def add_template_category(category_name: str, description: str = None, cursor: sqlite3.Cursor = None) -> int | None:
#     """
#     Adds a new template category if it doesn't exist by name.
#     If a cursor is provided, it uses it for database operations and does not commit.
#     If no cursor is provided, it manages its own connection and transaction.
#     Returns the category_id of the new or existing category, or None on error.
#     """
#     is_external_cursor = cursor is not None
#     conn_internal = None

#     try:
#         if is_external_cursor:
#             if not isinstance(cursor, sqlite3.Cursor):
#                 raise ValueError("Invalid cursor object passed to add_template_category.")
#             cursor_to_use = cursor
#         else:
#             conn_internal = get_db_connection()
#             cursor_to_use = conn_internal.cursor()

#         cursor_to_use.execute("SELECT category_id FROM TemplateCategories WHERE category_name = ?", (category_name,))
#         row = cursor_to_use.fetchone()
#         if row:
#             return row[0] if isinstance(row, tuple) else row['category_id']

#         sql = "INSERT INTO TemplateCategories (category_name, description) VALUES (?, ?)"
#         cursor_to_use.execute(sql, (category_name, description))

#         if not is_external_cursor and conn_internal:
#             conn_internal.commit()

#         return cursor_to_use.lastrowid
#     except sqlite3.Error as e:
#         print(f"Database error in add_template_category for '{category_name}': {e}")
#         if not is_external_cursor and conn_internal:
#             conn_internal.rollback()
#         # If using an external cursor, the caller is responsible for rollback.
#         return None
#     finally:
#         if not is_external_cursor and conn_internal:
#             conn_internal.close()


# def get_template_category_by_id(category_id: int) -> dict | None:
#     """Retrieves a template category by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM TemplateCategories WHERE category_id = ?", (category_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_template_category_by_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_template_category_by_name(category_name: str) -> dict | None:
#     """Retrieves a template category by its name."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM TemplateCategories WHERE category_name = ?", (category_name,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_template_category_by_name: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_all_template_categories() -> list[dict]:
#     """Retrieves all template categories."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM TemplateCategories ORDER BY category_name")
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_template_categories: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_template_category(category_id: int, new_name: str = None, new_description: str = None) -> bool:
#     """
#     Updates a template category's name and/or description.
#     Returns True on success, False otherwise.
#     """
#     conn = None
#     if not new_name and not new_description:
#         return False # Nothing to update

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         set_clauses = []
#         params = []
#         if new_name:
#             set_clauses.append("category_name = ?")
#             params.append(new_name)
#         if new_description is not None: # Allow setting description to empty string
#             set_clauses.append("description = ?")
#             params.append(new_description)

#         if not set_clauses:
#             return False

#         sql = f"UPDATE TemplateCategories SET {', '.join(set_clauses)} WHERE category_id = ?"
#         params.append(category_id)

#         cursor.execute(sql, tuple(params))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_template_category: {e}")
#         if conn:
#             conn.rollback()
#         return False
#     finally:
#         if conn:
#             conn.close()

# def delete_template_category(category_id: int) -> bool:
#     """
#     Deletes a template category.
#     Templates using this category will have their category_id set to NULL
#     due to ON DELETE SET NULL foreign key constraint.
#     Returns True on success, False otherwise.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Before deleting, one might want to check if it's a protected category like "General"
#         # For now, allowing deletion of any category.
#         cursor.execute("DELETE FROM TemplateCategories WHERE category_id = ?", (category_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_template_category: {e}")
#         if conn:
#             conn.rollback()
#         return False
#     finally:
#         if conn:
#             conn.close()

# def get_template_category_details(category_id: int) -> dict | None:
#     """Retrieves details for a specific template category by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM TemplateCategories WHERE category_id = ?", (category_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_template_category_details: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# # CRUD functions for Templates
# def add_template(template_data: dict) -> int | None:
#     """
#     Adds a new template to the database. Returns the template_id if successful.
#     Ensures created_at and updated_at are set.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"

#         sql = """
#             INSERT INTO Templates (
#                 template_name, template_type, description, base_file_name, language_code,
#                 is_default_for_type_lang, category_id, content_definition, email_subject_template,
#                 email_variables_info, cover_page_config_json, document_mapping_config_json,
#                 raw_template_file_data, version, created_at, updated_at, created_by_user_id
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             template_data.get('template_name'),
#             template_data.get('template_type'),
#             template_data.get('description'),
#             template_data.get('base_file_name'),
#             template_data.get('language_code'),
#             template_data.get('is_default_for_type_lang', False),
#             template_data.get('category_id'), # Changed from 'category' to 'category_id'
#             template_data.get('content_definition'),
#             template_data.get('email_subject_template'),
#             template_data.get('email_variables_info'),
#             template_data.get('cover_page_config_json'),
#             template_data.get('document_mapping_config_json'),
#             template_data.get('raw_template_file_data'),
#             template_data.get('version'),
#             now,  # created_at
#             now,  # updated_at
#             template_data.get('created_by_user_id')
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid # For AUTOINCREMENT PK
#     except sqlite3.Error as e:
#         print(f"Database error in add_template: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_template_by_id(template_id: int) -> dict | None:
#     """Retrieves a template by its ID. Returns a dict or None if not found."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Templates WHERE template_id = ?", (template_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_template_by_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_templates_by_type(template_type: str, language_code: str = None) -> list[dict]:
#     """
#     Retrieves templates filtered by template_type.
#     If language_code is provided, also filters by language_code.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql = "SELECT * FROM Templates WHERE template_type = ?"
#         params = [template_type]

#         if language_code:
#             sql += " AND language_code = ?"
#             params.append(language_code)

#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_templates_by_type: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_template(template_id: int, template_data: dict) -> bool:
#     """
#     Updates an existing template.
#     Ensures updated_at is set.
#     Returns True on success.
#     """
#     conn = None
#     if not template_data:
#         return False

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         template_data['updated_at'] = now

#         set_clauses = []
#         params = []

#         for key, value in template_data.items():
#             if key != 'template_id': # template_id should not be updated
#                 set_clauses.append(f"{key} = ?")
#                 params.append(value)

#         if not set_clauses:
#             return False

#         sql = f"UPDATE Templates SET {', '.join(set_clauses)} WHERE template_id = ?"
#         params.append(template_id)

#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_template: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def delete_template(template_id: int) -> bool:
#     """Deletes a template from the database. Returns True on success."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_template: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def get_distinct_template_languages() -> list[tuple[str]]:
#     """Retrieves a list of distinct, non-empty language codes from templates."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT DISTINCT language_code FROM Templates WHERE language_code IS NOT NULL AND language_code != '' ORDER BY language_code;"
#         cursor.execute(sql)
#         # Returns list of tuples, e.g., [('en',), ('fr',)]
#         return cursor.fetchall()
#     except sqlite3.Error as e:
#         print(f"Database error in get_distinct_template_languages: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_distinct_template_types() -> list[tuple[str]]:
#     """Retrieves a list of distinct, non-empty template types from templates."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT DISTINCT template_type FROM Templates WHERE template_type IS NOT NULL AND template_type != '' ORDER BY template_type;"
#         cursor.execute(sql)
#         # Returns list of tuples, e.g., [('document_excel',), ('document_word',)]
#         return cursor.fetchall()
#     except sqlite3.Error as e:
#         print(f"Database error in get_distinct_template_types: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_filtered_templates(category_id: int = None, language_code: str = None, template_type: str = None) -> list[dict]:
#     """
#     Fetches templates based on the provided filters.
#     If a filter is None, it's not applied.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         base_sql = "SELECT * FROM Templates"
#         where_clauses = []
#         params = []

#         if category_id is not None:
#             where_clauses.append("category_id = ?")
#             params.append(category_id)
#         if language_code is not None:
#             where_clauses.append("language_code = ?")
#             params.append(language_code)
#         if template_type is not None:
#             where_clauses.append("template_type = ?")
#             params.append(template_type)

#         if where_clauses:
#             sql = f"{base_sql} WHERE {' AND '.join(where_clauses)}"
#         else:
#             sql = base_sql

#         sql += " ORDER BY category_id, template_name;" # Order for consistent display

#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_filtered_templates: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def get_template_details_for_preview(template_id: int) -> dict | None:
#     """
#     Fetches base_file_name and language_code for a given template_id for preview purposes.
#     Returns a dictionary like {'base_file_name': 'name.xlsx', 'language_code': 'fr'} or None.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute(
#             "SELECT base_file_name, language_code FROM Templates WHERE template_id = ?",
#             (template_id,)
#         )
#         row = cursor.fetchone()
#         if row:
#             return {'base_file_name': row['base_file_name'], 'language_code': row['language_code']}
#         return None
#     except sqlite3.Error as e:
#         print(f"Database error in get_template_details_for_preview: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_template_path_info(template_id: int) -> dict | None:
#     """
#     Fetches base_file_name (as file_name) and language_code (as language) for a given template_id.
#     Returns {'file_name': 'name.xlsx', 'language': 'fr'} or None.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute(
#             "SELECT base_file_name, language_code FROM Templates WHERE template_id = ?",
#             (template_id,)
#         )
#         row = cursor.fetchone()
#         if row:
#             return {'file_name': row['base_file_name'], 'language': row['language_code']}
#         return None
#     except sqlite3.Error as e:
#         print(f"Database error in get_template_path_info: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def delete_template_and_get_file_info(template_id: int) -> dict | None:
#     """
#     Deletes the template record by template_id after fetching its file information.
#     Returns {'file_name': 'name.xlsx', 'language': 'fr'} if successful, None otherwise.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         conn.isolation_level = None # Start transaction
#         cursor = conn.cursor()
#         cursor.execute("BEGIN")

#         # First, fetch the required information
#         cursor.execute(
#             "SELECT base_file_name, language_code FROM Templates WHERE template_id = ?",
#             (template_id,)
#         )
#         row = cursor.fetchone()

#         if not row:
#             conn.rollback()
#             print(f"Template with ID {template_id} not found for deletion.")
#             return None

#         file_info = {'file_name': row['base_file_name'], 'language': row['language_code']}

#         # Proceed with deletion
#         cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))

#         if cursor.rowcount > 0:
#             conn.commit()
#             return file_info
#         else:
#             # This case should ideally not be reached if the select was successful
#             # but included for robustness
#             conn.rollback()
#             print(f"Failed to delete template with ID {template_id} after fetching info.")
#             return None

#     except sqlite3.Error as e:
#         if conn:
#             conn.rollback()
#         print(f"Database error in delete_template_and_get_file_info: {e}")
#         return None
#     finally:
#         if conn:
#             conn.isolation_level = '' # Reset isolation level
#             conn.close()

# def set_default_template_by_id(template_id: int) -> bool:
#     """
#     Sets a template as the default for its template_type and language_code.
#     Unsets other templates of the same type and language.
#     Returns True on success, False on error.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         conn.isolation_level = None # Start transaction
#         cursor = conn.cursor()
#         cursor.execute("BEGIN")

#         # Get template_type and language_code for the given template_id
#         cursor.execute(
#             "SELECT template_type, language_code FROM Templates WHERE template_id = ?",
#             (template_id,)
#         )
#         template_info = cursor.fetchone()

#         if not template_info:
#             print(f"Template with ID {template_id} not found.")
#             conn.rollback()
#             return False

#         current_template_type = template_info['template_type']
#         current_language_code = template_info['language_code']

#         # Set is_default_for_type_lang = 0 for all templates of the same type and language
#         cursor.execute(
#             """
#             UPDATE Templates
#             SET is_default_for_type_lang = 0
#             WHERE template_type = ? AND language_code = ?
#             """,
#             (current_template_type, current_language_code)
#         )

#         # Set is_default_for_type_lang = 1 for the specified template_id
#         cursor.execute(
#             "UPDATE Templates SET is_default_for_type_lang = 1 WHERE template_id = ?",
#             (template_id,)
#         )

#         conn.commit()
#         return True

#     except sqlite3.Error as e:
#         if conn:
#             conn.rollback()
#         print(f"Database error in set_default_template_by_id: {e}")
#         return False
#     finally:
#         if conn:
#             conn.isolation_level = '' # Reset isolation level
#             conn.close()

# def get_template_by_type_lang_default(template_type: str, language_code: str) -> dict | None:
#     """
#     Retrieves the default template for a given type and language.
#     Returns a dict or None if not found.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM Templates WHERE template_type = ? AND language_code = ? AND is_default_for_type_lang = TRUE LIMIT 1"
#         cursor.execute(sql, (template_type, language_code))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_template_by_type_lang_default: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()


# # CRUD functions for TeamMembers
# def add_team_member(member_data: dict) -> int | None:
#     """
#     Adds a new team member. Returns team_member_id (AUTOINCREMENT) or None.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"

#         sql = """
#             INSERT INTO TeamMembers (
#                 user_id, full_name, email, role_or_title, department,
#                 phone_number, profile_picture_url, is_active, notes,
#                 hire_date, performance, skills,
#                 created_at, updated_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             member_data.get('user_id'), # Can be None
#             member_data.get('full_name'),
#             member_data.get('email'),
#             member_data.get('role_or_title'),
#             member_data.get('department'),
#             member_data.get('phone_number'),
#             member_data.get('profile_picture_url'),
#             member_data.get('is_active', True),
#             member_data.get('notes'),
#             member_data.get('hire_date'),
#             member_data.get('performance', 0),
#             member_data.get('skills'),
#             now, # created_at
#             now  # updated_at
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e:
#         print(f"Database error in add_team_member: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_team_member_by_id(team_member_id: int) -> dict | None:
#     """Retrieves a team member by their ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM TeamMembers WHERE team_member_id = ?", (team_member_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_team_member_by_id: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_all_team_members(filters: dict = None) -> list[dict]:
#     """
#     Retrieves all team members, optionally applying filters.
#     Allowed filters: is_active (boolean), department (string).
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql = "SELECT * FROM TeamMembers"
#         params = []

#         if filters:
#             where_clauses = []
#             allowed_filters = ['is_active', 'department', 'user_id']
#             for key, value in filters.items():
#                 if key in allowed_filters:
#                     if key == 'is_active' and isinstance(value, bool):
#                          where_clauses.append(f"{key} = ?")
#                          params.append(1 if value else 0)
#                     else:
#                         where_clauses.append(f"{key} = ?")
#                         params.append(value)
#             if where_clauses:
#                 sql += " WHERE " + " AND ".join(where_clauses)

#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_team_members: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_team_member(team_member_id: int, member_data: dict) -> bool:
#     """
#     Updates an existing team member. Sets updated_at.
#     Returns True on success.
#     """
#     conn = None
#     if not member_data:
#         return False

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         member_data['updated_at'] = now

#         set_clauses = []
#         params = []

#         valid_columns = [
#             'user_id', 'full_name', 'email', 'role_or_title', 'department',
#             'phone_number', 'profile_picture_url', 'is_active', 'notes',
#             'hire_date', 'performance', 'skills', 'updated_at'
#         ]
#         for key, value in member_data.items():
#             if key in valid_columns:
#                 set_clauses.append(f"{key} = ?")
#                 params.append(value)

#         if not set_clauses:
#             return False

#         sql = f"UPDATE TeamMembers SET {', '.join(set_clauses)} WHERE team_member_id = ?"
#         params.append(team_member_id)

#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_team_member: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# def delete_team_member(team_member_id: int) -> bool:
#     """Deletes a team member (hard delete). Returns True on success."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM TeamMembers WHERE team_member_id = ?", (team_member_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_team_member: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()

# CRUD functions for Contacts
# def add_contact(contact_data: dict) -> int | None:
#     """Adds a new contact. Returns contact_id (AUTOINCREMENT) or None."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"

#         # Fallback for 'name' if 'displayName' is not provided
#         name_to_insert = contact_data.get('displayName', contact_data.get('name'))

#         sql = """
#             INSERT INTO Contacts (
#                 name, email, phone, position, company_name, notes,
#                 givenName, familyName, displayName, phone_type, email_type,
#                 address_formattedValue, address_streetAddress, address_city,
#                 address_region, address_postalCode, address_country,
#                 organization_name, organization_title, birthday_date,
#                 created_at, updated_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             name_to_insert,
#             contact_data.get('email'),
#             contact_data.get('phone'),
#             contact_data.get('position'),
#             contact_data.get('company_name'),
#             contact_data.get('notes'), # notes_text
#             contact_data.get('givenName'),
#             contact_data.get('familyName'),
#             contact_data.get('displayName'),
#             contact_data.get('phone_type'),
#             contact_data.get('email_type'),
#             contact_data.get('address_formattedValue'),
#             contact_data.get('address_streetAddress'),
#             contact_data.get('address_city'),
#             contact_data.get('address_region'),
#             contact_data.get('address_postalCode'),
#             contact_data.get('address_country'),
#             contact_data.get('organization_name'),
#             contact_data.get('organization_title'),
#             contact_data.get('birthday_date'),
#             now, now
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e:
#         print(f"Database error in add_contact: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_contact_by_id(contact_id: int) -> dict | None:
#     """Retrieves a contact by their ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Contacts WHERE contact_id = ?", (contact_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_contact_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_contact_by_email(email: str) -> dict | None:
#     """Retrieves a contact by their email."""
#     conn = None
#     if not email: return None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM Contacts WHERE email = ?", (email,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_contact_by_email: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_all_contacts(filters: dict = None) -> list[dict]:
#     """
#     Retrieves all contacts. Filters by 'company_name' (exact) or 'name' (partial LIKE).
#     Now selects all new columns.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM Contacts" # Selects all columns including new ones
#         params = []
#         where_clauses = []
#         if filters:
#             if 'company_name' in filters:
#                 where_clauses.append("company_name = ?")
#                 params.append(filters['company_name'])
#             if 'name' in filters: # This will search in 'name' or 'displayName'
#                 where_clauses.append("(name LIKE ? OR displayName LIKE ?)")
#                 params.append(f"%{filters['name']}%")
#                 params.append(f"%{filters['name']}%")
#             # TODO: Add filters for new fields if needed

#         if where_clauses:
#             sql += " WHERE " + " AND ".join(where_clauses)

#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_contacts: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_contact(contact_id: int, contact_data: dict) -> bool:
#     """Updates an existing contact. Sets updated_at."""
#     conn = None
#     if not contact_data: return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         contact_data['updated_at'] = now

#         # Fallback for 'name' if 'displayName' is provided and 'name' is not
#         if 'displayName' in contact_data and 'name' not in contact_data:
#             contact_data['name'] = contact_data['displayName']
#         elif 'name' in contact_data and 'displayName' not in contact_data:
#              # If only 'name' is provided, ensure 'displayName' is also updated if it's meant to be the primary display
#              # This depends on application logic, for now, we'll update 'name' if 'displayName' isn't explicitly set to something else.
#              # A more robust approach might be to always set displayName = name if displayName is not in contact_data.
#              # For now, let's assume if 'displayName' is not in contact_data, it's not being changed.
#              pass


#         # Ensure only valid columns are updated
#         valid_columns = [
#             'name', 'email', 'phone', 'position', 'company_name', 'notes',
#             'givenName', 'familyName', 'displayName', 'phone_type', 'email_type',
#             'address_formattedValue', 'address_streetAddress', 'address_city',
#             'address_region', 'address_postalCode', 'address_country',
#             'organization_name', 'organization_title', 'birthday_date', 'updated_at'
#         ]

#         set_clauses = []
#         params = []

#         for key, value in contact_data.items():
#             if key in valid_columns: # Check if the key is a valid column to update
#                 set_clauses.append(f"{key} = ?")
#                 params.append(value)
#             elif key == 'contact_id': # Skip primary key
#                 continue

#         if not set_clauses:
#             print("Warning: No valid fields to update in update_contact.")
#             return False

#         params.append(contact_id)

#         sql = f"UPDATE Contacts SET {', '.join(set_clauses)} WHERE contact_id = ?"
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_contact: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_contact(contact_id: int) -> bool:
#     """Deletes a contact. Associated ClientContacts are handled by ON DELETE CASCADE."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM Contacts WHERE contact_id = ?", (contact_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_contact: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# Functions for ClientContacts association
# def link_contact_to_client(client_id: str, contact_id: int, is_primary: bool = False, can_receive_documents: bool = True) -> int | None:
#     """Links a contact to a client."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """
#             INSERT INTO ClientContacts (client_id, contact_id, is_primary_for_client, can_receive_documents)
#             VALUES (?, ?, ?, ?)
#         """
#         params = (client_id, contact_id, is_primary, can_receive_documents)
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e: # Handles UNIQUE constraint violation if link already exists
#         print(f"Database error in link_contact_to_client: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def unlink_contact_from_client(client_id: str, contact_id: int) -> bool:
#     """Unlinks a contact from a client."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "DELETE FROM ClientContacts WHERE client_id = ? AND contact_id = ?"
#         cursor.execute(sql, (client_id, contact_id))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in unlink_contact_from_client: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def get_contacts_for_client(client_id: str, limit: int = None, offset: int = 0) -> list[dict]:
#     """Retrieves contacts for a given client, including link details, with optional pagination."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """
#             SELECT c.*, cc.is_primary_for_client, cc.can_receive_documents, cc.client_contact_id
#             FROM Contacts c
#             JOIN ClientContacts cc ON c.contact_id = cc.contact_id
#             WHERE cc.client_id = ?
#             ORDER BY c.name  -- Or any other preferred order
#         """
#         params = [client_id]

#         if limit is not None:
#             sql += " LIMIT ? OFFSET ?"
#             params.extend([limit, offset])

#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_contacts_for_client: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_contacts_for_client_count(client_id: str) -> int:
#     """Retrieves the count of contacts linked to a specific client_id."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Counts entries in the ClientContacts association table for the given client_id
#         sql = "SELECT COUNT(contact_id) FROM ClientContacts WHERE client_id = ?"
#         cursor.execute(sql, (client_id,))
#         row = cursor.fetchone()
#         return row[0] if row else 0
#     except sqlite3.Error as e:
#         print(f"Database error in get_contacts_for_client_count for client_id {client_id}: {e}")
#         return 0 # Return 0 in case of error to prevent further issues
#     finally:
#         if conn:
#             conn.close()

# def get_clients_for_contact(contact_id: int) -> list[dict]:
#     """Retrieves all clients associated with a contact."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """
#             SELECT cl.*, cc.is_primary_for_client, cc.can_receive_documents, cc.client_contact_id
#             FROM Clients cl
#             JOIN ClientContacts cc ON cl.client_id = cc.client_id
#             WHERE cc.contact_id = ?
#         """
#         cursor.execute(sql, (contact_id,))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_clients_for_contact: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_specific_client_contact_link_details(client_id: str, contact_id: int) -> dict | None:
#     """
#     Retrieves specific details (client_contact_id, is_primary_for_client, can_receive_documents)
#     for a single link between a client and a contact.
#     Returns a dict if the link is found, otherwise None.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """
#             SELECT client_contact_id, is_primary_for_client, can_receive_documents
#             FROM ClientContacts
#             WHERE client_id = ? AND contact_id = ?
#         """
#         cursor.execute(sql, (client_id, contact_id))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_specific_client_contact_link_details: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def update_client_contact_link(client_contact_id: int, details: dict) -> bool:
#     """Updates details of a client-contact link (is_primary, can_receive_documents)."""
#     conn = None
#     if not details or not any(key in details for key in ['is_primary_for_client', 'can_receive_documents']):
#         return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         set_clauses = []
#         params = []
#         if 'is_primary_for_client' in details:
#             set_clauses.append("is_primary_for_client = ?")
#             params.append(details['is_primary_for_client'])
#         if 'can_receive_documents' in details:
#             set_clauses.append("can_receive_documents = ?")
#             params.append(details['can_receive_documents'])

#         if not set_clauses: return False # Should not happen due to check above

#         params.append(client_contact_id)
#         sql = f"UPDATE ClientContacts SET {', '.join(set_clauses)} WHERE client_contact_id = ?"

#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_client_contact_link: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def get_all_product_equivalencies() -> list[dict]:
#     """
#     Retrieves all product equivalencies with product details for both products in the pair.
#     Returns a list of dictionaries.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """
#             SELECT
#                 pe.equivalence_id,
#                 pe.product_id_a,
#                 pA.product_name AS product_name_a,
#                 pA.language_code AS language_code_a,
#                 pA.weight AS weight_a,
#                 pA.dimensions AS dimensions_a,
#                 pe.product_id_b,
#                 pB.product_name AS product_name_b,
#                 pB.language_code AS language_code_b,
#                 pB.weight AS weight_b,
#                 pB.dimensions AS dimensions_b
#             FROM ProductEquivalencies pe
#             JOIN Products pA ON pe.product_id_a = pA.product_id
#             JOIN Products pB ON pe.product_id_b = pB.product_id
#             ORDER BY pA.product_name, pB.product_name;
#         """
#         cursor.execute(sql)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_product_equivalencies: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def remove_product_equivalence(equivalence_id: int) -> bool:
#     """
#     Deletes a product equivalence by its equivalence_id.
#     Returns True if deletion was successful, False otherwise.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM ProductEquivalencies WHERE equivalence_id = ?", (equivalence_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in remove_product_equivalence: {e}")
#         return False
#     finally:
#         if conn:
#             conn.close()


# # CRUD functions for ProductEquivalencies
# def add_product_equivalence(product_id_a: int, product_id_b: int) -> int | None:
#     """
#     Adds a product equivalence pair.
#     Ensures product_id_a < product_id_b to maintain uniqueness.
#     Returns equivalence_id of the new or existing record.
#     """
#     if product_id_a == product_id_b:
#         print("Error: Cannot create equivalence for a product with itself.")
#         return None

#     p_a = min(product_id_a, product_id_b)
#     p_b = max(product_id_a, product_id_b)

#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "INSERT INTO ProductEquivalencies (product_id_a, product_id_b) VALUES (?, ?)"
#         cursor.execute(sql, (p_a, p_b))
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.IntegrityError: # Pair already exists
#         print(f"IntegrityError: Product equivalence pair ({p_a}, {p_b}) likely already exists.")
#         cursor.execute("SELECT equivalence_id FROM ProductEquivalencies WHERE product_id_a = ? AND product_id_b = ?", (p_a, p_b))
#         row = cursor.fetchone()
#         return row['equivalence_id'] if row else None # Should find it if IntegrityError was due to this UNIQUE constraint
#     except sqlite3.Error as e:
#         print(f"Database error in add_product_equivalence: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_equivalent_products(product_id: int) -> list[dict]:
#     """
#     Retrieves all products equivalent to the given product_id.
#     Returns a list of product dictionaries.
#     """
#     conn = None
#     equivalent_product_ids = set()
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # Find pairs where product_id is product_id_a
#         cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (product_id,))
#         for row in cursor.fetchall():
#             equivalent_product_ids.add(row['product_id_b'])

#         # Find pairs where product_id is product_id_b
#         cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (product_id,))
#         for row in cursor.fetchall():
#             equivalent_product_ids.add(row['product_id_a'])

#         # Remove the original product_id itself if it's in the set
#         equivalent_product_ids.discard(product_id)

#         equivalent_products_details = []
#         if not equivalent_product_ids:
#             return []

#         # Fetch all equivalent products in a single query
#         placeholders = ','.join('?' for _ in equivalent_product_ids)
#         sql = f"SELECT * FROM Products WHERE product_id IN ({placeholders})"
#         cursor.execute(sql, tuple(equivalent_product_ids))
#         rows = cursor.fetchall()
#         equivalent_products_details = [dict(row) for row in rows]

#         return equivalent_products_details

#     except sqlite3.Error as e:
#         print(f"Database error in get_equivalent_products: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# CRUD functions for ProductDimensions
# def add_or_update_product_dimension(product_id: int, dimension_data: dict) -> bool:
#     """
#     Adds or updates a product's dimensions.
#     Performs an "upsert" operation. Updates 'updated_at' timestamp.
#     Returns True on success, False on failure.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"

#         # Check if record exists
#         cursor.execute("SELECT product_id FROM ProductDimensions WHERE product_id = ?", (product_id,))
#         exists = cursor.fetchone()

#         if exists:
#             # Update existing record
#             dimension_data['updated_at'] = now
#             set_clauses = [f"{key} = ?" for key in dimension_data.keys() if key != 'product_id']
#             # Filter out product_id from params if it was accidentally included in dimension_data keys
#             params = [value for key, value in dimension_data.items() if key != 'product_id']

#             if not set_clauses: # No actual dimension data to update, only product_id was passed
#                 # Still, we might want to update the 'updated_at' timestamp
#                 # Forcing an update to 'updated_at' even if other fields are empty
#                 cursor.execute("UPDATE ProductDimensions SET updated_at = ? WHERE product_id = ?", (now, product_id))
#                 conn.commit()
#                 return True

#             params.append(product_id)
#             sql = f"UPDATE ProductDimensions SET {', '.join(set_clauses)} WHERE product_id = ?"
#             cursor.execute(sql, params)
#         else:
#             # Insert new record
#             # Ensure all dimension columns are potentially included, defaulting to None if not in dimension_data
#             all_dim_columns = ['dim_A', 'dim_B', 'dim_C', 'dim_D', 'dim_E', 'dim_F', 'dim_G', 'dim_H', 'dim_I', 'dim_J', 'technical_image_path']

#             columns_to_insert = ['product_id', 'created_at', 'updated_at']
#             values_to_insert = [product_id, now, now]

#             for col in all_dim_columns:
#                 columns_to_insert.append(col)
#                 values_to_insert.append(dimension_data.get(col))

#             placeholders = ', '.join(['?'] * len(columns_to_insert))
#             sql = f"INSERT INTO ProductDimensions ({', '.join(columns_to_insert)}) VALUES ({placeholders})"
#             cursor.execute(sql, tuple(values_to_insert))

#         conn.commit()
#         return cursor.rowcount > 0 or (not exists and cursor.lastrowid is not None) # For INSERT, check lastrowid
#     except sqlite3.Error as e:
#         print(f"Database error in add_or_update_product_dimension for product_id {product_id}: {e}")
#         if conn:
#             conn.rollback()
#         return False
#     finally:
#         if conn:
#             conn.close()

# def get_product_dimension(product_id: int) -> dict | None:
#     """
#     Fetches the dimension data for the given product_id.
#     Returns a dictionary of the dimension data if found, otherwise None.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM ProductDimensions WHERE product_id = ?", (product_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_product_dimension for product_id {product_id}: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def delete_product_dimension(product_id: int) -> bool:
#     """
#     Deletes the dimension record for the given product_id.
#     Returns True if a row was deleted, False otherwise.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM ProductDimensions WHERE product_id = ?", (product_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_product_dimension for product_id {product_id}: {e}")
#         if conn:
#             conn.rollback()
#         return False
#     finally:
#         if conn:
#             conn.close()

# CRUD functions for Products
# def add_product(product_data: dict) -> int | None:
#     """Adds a new product, including weight and dimensions. Returns product_id or None."""
#     conn = None
#     try:
#         product_name = product_data.get('product_name')
#         base_unit_price = product_data.get('base_unit_price')
#         language_code = product_data.get('language_code', 'fr') # Default to 'fr'

#         if not product_name:
#             print("Error in add_product: 'product_name' is required.")
#             # Consider raising an error or returning a more specific indicator of failure
#             return None
#         if base_unit_price is None: # Price can be 0.0, so check for None explicitly
#             print("Error in add_product: 'base_unit_price' is required.")
#             # Consider raising an error or returning a more specific indicator of failure
#             return None
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         sql = """
#             INSERT INTO Products (
#                 product_name, description, category, language_code, base_unit_price,
#                 unit_of_measure, weight, dimensions, is_active, created_at, updated_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             product_name, product_data.get('description'),
#             product_data.get('category'),
#             language_code,
#             base_unit_price,
#             product_data.get('unit_of_measure'),
#             product_data.get('weight'),
#             product_data.get('dimensions'),
#             product_data.get('is_active', True),
#             now, now
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.IntegrityError as e:
#         # This will catch the UNIQUE constraint violation for (product_name, language_code)
#         print(f"IntegrityError in add_product for name '{product_name}' and lang '{language_code}': {e}")
#         if conn:
#             conn.rollback()
#         # Optionally, here you could query for the existing product_id if needed:
#         # cursor.execute("SELECT product_id FROM Products WHERE product_name = ? AND language_code = ?", (product_name, language_code))
#         # existing_product = cursor.fetchone()
#         # if existing_product: return existing_product['product_id']
#         return None # Indicates "add failed" or "already exists"
#     except sqlite3.Error as e:
#         print(f"Database error in add_product: {e}")
#         if conn:
#             conn.rollback()
#         return None
#     finally:
#         if conn: conn.close()

# def get_product_by_id(product_id: int) -> dict | None:
#     """Retrieves a product by ID, including weight and dimensions."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Ensure all desired columns including new ones are selected
#         cursor.execute("SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at FROM Products WHERE product_id = ?", (product_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_product_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_product_by_name(product_name: str) -> dict | None:
#     """Retrieves a product by its exact name, including weight and dimensions. Returns a dict or None if not found."""
#     conn = None
#     if not product_name:
#         return None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Ensure all desired columns including new ones are selected
#         cursor.execute("SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at FROM Products WHERE product_name = ?", (product_name,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_product_by_name: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_all_products(filters: dict = None) -> list[dict]:
#     """Retrieves all products, including weight and dimensions. Filters by category (exact) or product_name (partial LIKE)."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Ensure all desired columns including new ones are selected
#         sql = "SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at FROM Products"
#         params = []
#         where_clauses = []
#         if filters:
#             if 'category' in filters:
#                 where_clauses.append("category = ?")
#                 params.append(filters['category'])
#             if 'product_name' in filters:
#                 where_clauses.append("product_name LIKE ?")
#                 params.append(f"%{filters['product_name']}%")

#         if where_clauses:
#             sql += " WHERE " + " AND ".join(where_clauses)

#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_products: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_product(product_id: int, product_data: dict) -> bool:
#     """Updates an existing product, including weight and dimensions. Sets updated_at."""
#     conn = None
#     if not product_data:
#         return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         product_data['updated_at'] = now

#         # Ensure only valid columns are updated
#         valid_columns = [
#             'product_name', 'description', 'category', 'language_code',
#             'base_unit_price', 'unit_of_measure', 'weight', 'dimensions',
#             'is_active', 'updated_at'
#         ]

#         set_clauses = []
#         params = []
#         for key, value in product_data.items():
#             if key in valid_columns: # Check if the key is a valid column to update
#                 set_clauses.append(f"{key} = ?")
#                 params.append(value)

#         if not set_clauses:
#             print("Warning: No valid fields to update in update_product.")
#             return False

#         params.append(product_id)
#         sql = f"UPDATE Products SET {', '.join(set_clauses)} WHERE product_id = ?"

#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_product: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_product(product_id: int) -> bool:
#     """Deletes a product. Associated ClientProjectProducts are handled by ON DELETE CASCADE."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM Products WHERE product_id = ?", (product_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_product: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def get_products(language_code: str = None) -> list[dict]:
#     """
#     Fetches products from the Products table.
#     If language_code is provided, it filters products by this language.
#     Returns a list of dictionaries, where each dictionary represents a product.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql = "SELECT product_id, product_name, description, base_unit_price, language_code, category, unit_of_measure, weight, dimensions, is_active FROM Products"
#         params = []

#         if language_code:
#             sql += " WHERE language_code = ? AND is_active = TRUE"
#             params.append(language_code)
#         else:
#             sql += " WHERE is_active = TRUE"

#         sql += " ORDER BY product_name"

#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_products: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def update_product_price(product_id: int, new_price: float) -> bool:
#     """
#     Updates the base_unit_price of the product with the given product_id.
#     Returns True if the update was successful, False otherwise.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         now = datetime.utcnow().isoformat() + "Z"
#         sql = "UPDATE Products SET base_unit_price = ?, updated_at = ? WHERE product_id = ?"
#         params = (new_price, now, product_id)

#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_product_price for product_id {product_id}: {e}")
#         if conn:
#             conn.rollback()
#         return False
#     finally:
#         if conn:
#             conn.close()

# def get_products_by_name_pattern(pattern: str) -> list[dict] | None:
#     """
#     Retrieves products where the product_name matches the given pattern (LIKE %pattern%).
#     Returns a list of up to 10 matching products as dictionaries, or None on error.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         search_pattern = f"%{pattern}%"
#         # Ensure all desired columns including new ones are selected
#         sql = """
#             SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at
#             FROM Products
#             WHERE product_name LIKE ?
#             ORDER BY product_name
#             LIMIT 10
#         """
#         cursor.execute(sql, (search_pattern,))
#         rows = cursor.fetchall()

#         products = [dict(row) for row in rows]
#         return products

#     except sqlite3.Error as e:
#         print(f"Database error in get_products_by_name_pattern: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# def get_all_products_for_selection(language_code: str = None, name_pattern: str = None) -> list[dict]:
#     """
#     Retrieves active products for selection, optionally filtered by language_code
#     and/or name_pattern (searches product_name and description).
#     Orders by product_name.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql_params = []
#         # Start with base selection of active products
#         sql_where_clauses = ["is_active = TRUE"]

#         if language_code:
#             sql_where_clauses.append("language_code = ?")
#             sql_params.append(language_code)

#         if name_pattern:
#             # The name_pattern should be passed with wildcards already, e.g., "%search_term%"
#             sql_where_clauses.append("(product_name LIKE ? OR description LIKE ?)")
#             sql_params.append(name_pattern)
#             sql_params.append(name_pattern)

#         sql = f"""
#             SELECT product_id, product_name, description, category, language_code, base_unit_price, unit_of_measure, weight, dimensions, is_active, created_at, updated_at
#             FROM Products
#             WHERE {' AND '.join(sql_where_clauses)}
#             ORDER BY product_name
#         """

#         cursor.execute(sql, tuple(sql_params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_products_for_selection: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# Functions for ClientProjectProducts association
# def add_product_to_client_or_project(link_data: dict) -> int | None:
#     """Links a product to a client or project, calculating total price."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Initialize effective_unit_price in case of early exit or error before its definition
#         effective_unit_price = None # Ensure it's in scope for the except block
#         product_info = None # Ensure it's in scope for the except block

#         product_id = link_data.get('product_id')
#         product_info = get_product_by_id(product_id) # Need this for base price
#         if not product_info:
#             print(f"Product with ID {product_id} not found.")
#             return None

#         quantity = link_data.get('quantity', 1)
#         unit_price_override = link_data.get('unit_price_override')

#         if unit_price_override is not None: # Explicit check for None
#             effective_unit_price = unit_price_override
#         else:
#             effective_unit_price = product_info.get('base_unit_price')

#         # Ensure effective_unit_price is not None before multiplication
#         if effective_unit_price is None:
#             # This case should ideally not be reached if base_unit_price is NOT NULL in DB
#             # and product_info is correctly fetched.
#             print(f"Warning: effective_unit_price was None for product ID {product_id} (Quantity: {quantity}, Override: {unit_price_override}, Base from DB: {product_info.get('base_unit_price') if product_info else 'N/A'}). Defaulting to 0.0.")
#             effective_unit_price = 0.0

#         total_price_calculated = quantity * effective_unit_price

#         sql = """
#             INSERT INTO ClientProjectProducts (
#                 client_id, project_id, product_id, quantity, unit_price_override,
#                 total_price_calculated, serial_number, purchase_confirmed_at, added_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             link_data.get('client_id'),
#             link_data.get('project_id'), # Can be NULL
#             product_id,
#             quantity,
#             link_data.get('unit_price_override'), # Store override, or NULL if base used
#             total_price_calculated,
#             link_data.get('serial_number'), # New field
#             link_data.get('purchase_confirmed_at'), # New field
#             datetime.utcnow().isoformat() + "Z"
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except TypeError as te: # Specifically catch the error we are investigating
#         print(f"TypeError in add_product_to_client_or_project: {te}")
#         print(f"  product_id: {link_data.get('product_id')}")
#         print(f"  quantity: {link_data.get('quantity', 1)}")
#         print(f"  unit_price_override from link_data: {link_data.get('unit_price_override')}")
#         if product_info: # product_info might be None if error happened before it was fetched
#             print(f"  base_unit_price from product_info: {product_info.get('base_unit_price')}")
#         else:
#             print(f"  product_info was None or not fetched prior to error.")
#         print(f"  effective_unit_price at point of error: {effective_unit_price if 'effective_unit_price' in locals() else 'Not yet defined or error before definition'}")
#         return None # Indicate failure
#     except sqlite3.Error as e:
#         print(f"Database error in add_product_to_client_or_project: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_products_for_client_or_project(client_id: str, project_id: str = None) -> list[dict]:
#     """Fetches products for a client, optionally filtered by project_id. Joins with Products."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql = """
#             SELECT cpp.*,
#                    p.product_id as product_id_original_lang, p.product_name, p.description as product_description,
#                    p.category as product_category, p.base_unit_price, p.unit_of_measure,
#                    p.weight, p.dimensions, p.language_code,
#                    cpp.serial_number, cpp.purchase_confirmed_at
#             FROM ClientProjectProducts cpp
#             JOIN Products p ON cpp.product_id = p.product_id
#             WHERE cpp.client_id = ?
#         """
#         params = [client_id]

#         if project_id:
#             sql += " AND cpp.project_id = ?"
#             params.append(project_id)
#         else: # Explicitly handle case where we want products not tied to any project for this client
#             sql += " AND cpp.project_id IS NULL"

#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_products_for_client_or_project: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_client_project_product(link_id: int, update_data: dict) -> bool:
#     """Updates a ClientProjectProduct link. Recalculates total_price if needed."""
#     conn = None
#     if not update_data: return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         # Fetch current link data to get product_id and existing values for price calculation
#         cursor.execute("SELECT * FROM ClientProjectProducts WHERE client_project_product_id = ?", (link_id,))
#         current_link = cursor.fetchone()
#         if not current_link:
#             print(f"ClientProjectProduct link with ID {link_id} not found.")
#             return False

#         current_link_dict = dict(current_link)
#         new_quantity = update_data.get('quantity', current_link_dict['quantity'])
#         new_unit_price_override = update_data.get('unit_price_override', current_link_dict['unit_price_override'])

#         # Handle new optional fields for update
#         new_serial_number = update_data.get('serial_number', current_link_dict.get('serial_number'))
#         new_purchase_confirmed_at = update_data.get('purchase_confirmed_at', current_link_dict.get('purchase_confirmed_at'))


#         final_unit_price = new_unit_price_override
#         if final_unit_price is None: # If override is removed or was never there, use base price
#             product_info = get_product_by_id(current_link_dict['product_id'])
#             if not product_info: return False # Should not happen if data is consistent
#             final_unit_price = product_info['base_unit_price']

#         update_data['total_price_calculated'] = new_quantity * float(final_unit_price or 0) # Ensure float for calc

#         # Add new fields to update_data if they were provided in the call, so they get included in set_clauses
#         if 'serial_number' in update_data:
#             update_data['serial_number'] = new_serial_number
#         if 'purchase_confirmed_at' in update_data:
#             update_data['purchase_confirmed_at'] = new_purchase_confirmed_at

#         # Construct SET clauses only for fields present in update_data keys
#         set_clauses = []
#         params_list = []
#         valid_update_keys = ['quantity', 'unit_price_override', 'total_price_calculated', 'serial_number', 'purchase_confirmed_at']
#         for key in valid_update_keys:
#             if key in update_data:
#                 set_clauses.append(f"{key} = ?")
#                 params_list.append(update_data[key])

#         if not set_clauses: # No valid fields to update
#             return False

#         params_list.append(link_id)

#         sql = f"UPDATE ClientProjectProducts SET {', '.join(set_clauses)} WHERE client_project_product_id = ?"
#         cursor.execute(sql, tuple(params_list)) # Use tuple for params
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_client_project_product: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def remove_product_from_client_or_project(link_id: int) -> bool:
#     """Removes a product link from a client/project."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "DELETE FROM ClientProjectProducts WHERE client_project_product_id = ?"
#         cursor.execute(sql, (link_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in remove_product_from_client_or_project: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def get_client_project_product_by_id(link_id: int) -> dict | None:
#     """Retrieves a specific client-project-product link by its ID, joining with Products."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = """
#             SELECT cpp.*, p.product_name, p.description as product_description,
#                    p.category as product_category, p.base_unit_price, p.unit_of_measure,
#                    p.weight, p.dimensions, p.language_code
#             FROM ClientProjectProducts cpp
#             JOIN Products p ON cpp.product_id = p.product_id
#             WHERE cpp.client_project_product_id = ?
#         """
#         cursor.execute(sql, (link_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_client_project_product_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# # CRUD functions for ClientDocuments
# def add_client_document(doc_data: dict) -> str | None:
#     """Adds a new client document. Returns document_id (UUID) or None."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         doc_id = uuid.uuid4().hex

#         sql = """
#             INSERT INTO ClientDocuments (
#                 document_id, client_id, project_id, order_identifier, document_name,
#                 file_name_on_disk, file_path_relative, document_type_generated,
#                 source_template_id, version_tag, notes, created_at,
#                 updated_at, created_by_user_id
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             doc_id, doc_data.get('client_id'), doc_data.get('project_id'),
#             doc_data.get('order_identifier'), doc_data.get('document_name'),
#             doc_data.get('file_name_on_disk'), doc_data.get('file_path_relative'),
#             doc_data.get('document_type_generated'), doc_data.get('source_template_id'),
#             doc_data.get('version_tag'), doc_data.get('notes'),
#             now, now, doc_data.get('created_by_user_id')
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return doc_id
#     except sqlite3.Error as e:
#         print(f"Database error in add_client_document: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_document_by_id(document_id: str) -> dict | None:
#     """Retrieves a document by its ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM ClientDocuments WHERE document_id = ?", (document_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_document_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_documents_for_client(client_id: str, filters: dict = None) -> list[dict]:
#     """
#     Retrieves documents for a client.
#     Filters by 'document_type_generated' (exact) or 'project_id' (exact) or 'order_identifier'.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM ClientDocuments WHERE client_id = ?"
#         params = [client_id]

#         if filters:
#             if 'document_type_generated' in filters:
#                 sql += " AND document_type_generated = ?"
#                 params.append(filters['document_type_generated'])
#             if 'project_id' in filters: # Can be None to filter for client-general docs
#                 if filters['project_id'] is None:
#                     sql += " AND project_id IS NULL"
#                 else:
#                     sql += " AND project_id = ?"
#                     params.append(filters['project_id'])
#             if 'order_identifier' in filters:
#                 if filters['order_identifier'] is None:
#                     sql += " AND order_identifier IS NULL"
#                 else:
#                     sql += " AND order_identifier = ?"
#                     params.append(filters['order_identifier'])

#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_documents_for_client: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def get_documents_for_project(project_id: str, filters: dict = None) -> list[dict]:
#     """
#     Retrieves documents for a project.
#     Filters by 'document_type_generated' (exact).
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM ClientDocuments WHERE project_id = ?"
#         params = [project_id]

#         if filters and 'document_type_generated' in filters:
#             sql += " AND document_type_generated = ?"
#             params.append(filters['document_type_generated'])

#         cursor.execute(sql, tuple(params))
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_documents_for_project: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_client_document(document_id: str, doc_data: dict) -> bool:
#     """Updates an existing client document. Sets updated_at."""
#     conn = None
#     if not doc_data: return False
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         doc_data['updated_at'] = now

#         # Exclude primary key from update set
#         valid_columns = [
#             'client_id', 'project_id', 'order_identifier', 'document_name', 'file_name_on_disk',
#             'file_path_relative', 'document_type_generated', 'source_template_id',
#             'version_tag', 'notes', 'updated_at', 'created_by_user_id'
#         ]
#         current_doc_data = {k: v for k, v in doc_data.items() if k in valid_columns}

#         if not current_doc_data: return False

#         set_clauses = [f"{key} = ?" for key in current_doc_data.keys()]
#         params_list = list(current_doc_data.values()) # Renamed to avoid conflict
#         params_list.append(document_id)

#         sql = f"UPDATE ClientDocuments SET {', '.join(set_clauses)} WHERE document_id = ?"
#         cursor.execute(sql, params_list) # Use new params_list
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in update_client_document: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_client_document(document_id: str) -> bool:
#     """Deletes a client document."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM ClientDocuments WHERE document_id = ?", (document_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_client_document: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# --- ClientDocumentNotes CRUD Functions ---
# def add_client_document_note(data: dict) -> int | None:
#     """
#     Adds a new client document note.
#     data should contain client_id, document_type, language_code, note_content.
#     Optionally is_active (defaults to True).
#     Returns note_id on success, None on failure (e.g., UNIQUE constraint violation).
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"

#         sql = """
#             INSERT INTO ClientDocumentNotes (
#                 client_id, document_type, language_code, note_content,
#                 is_active, created_at, updated_at
#             ) VALUES (?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             data.get('client_id'),
#             data.get('document_type'),
#             data.get('language_code'),
#             data.get('note_content'),
#             data.get('is_active', True),
#             now, # created_at
#             now  # updated_at
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.IntegrityError as ie: # Catches UNIQUE constraint violation
#         print(f"Database IntegrityError in add_client_document_note (likely duplicate): {ie}")
#         if conn: conn.rollback()
#         return None
#     except sqlite3.Error as e:
#         print(f"Database error in add_client_document_note: {e}")
#         if conn: conn.rollback()
#         return None
#     finally:
#         if conn: conn.close()

# def get_client_document_notes(client_id: str, document_type: str = None, language_code: str = None, is_active: bool = None) -> list[dict]:
#     """
#     Fetches client document notes based on provided filters.
#     If a filter is None, it's not applied.
#     is_active=None means fetch all regardless of active status.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()

#         sql = "SELECT * FROM ClientDocumentNotes WHERE client_id = ?"
#         params = [client_id]

#         if document_type is not None:
#             sql += " AND document_type = ?"
#             params.append(document_type)
#         if language_code is not None:
#             sql += " AND language_code = ?"
#             params.append(language_code)
#         if is_active is not None: # True or False
#             sql += " AND is_active = ?"
#             params.append(1 if is_active else 0)

#         sql += " ORDER BY created_at DESC"

#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_client_document_notes: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_client_document_note(note_id: int, data: dict) -> bool:
#     """
#     Updates an existing client document note.
#     data can contain document_type, language_code, note_content, is_active.
#     Updates 'updated_at'. Returns True on success, False otherwise.
#     """
#     conn = None
#     if not data: return False

#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"

#         set_clauses = []
#         params = []

#         valid_update_columns = ['document_type', 'language_code', 'note_content', 'is_active']

#         for key, value in data.items():
#             if key in valid_update_columns:
#                 set_clauses.append(f"{key} = ?")
#                 params.append(value)

#         if not set_clauses:
#             print("Warning: No valid fields provided for update_client_document_note.")
#             return False

#         set_clauses.append("updated_at = ?")
#         params.append(now)

#         params.append(note_id)

#         sql = f"UPDATE ClientDocumentNotes SET {', '.join(set_clauses)} WHERE note_id = ?"

#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.IntegrityError as ie:
#         print(f"Database IntegrityError in update_client_document_note (likely duplicate on update): {ie}")
#         if conn: conn.rollback()
#         return False
#     except sqlite3.Error as e:
#         print(f"Database error in update_client_document_note for note_id {note_id}: {e}")
#         if conn: conn.rollback()
#         return False
#     finally:
#         if conn: conn.close()

# def delete_client_document_note(note_id: int) -> bool:
#     """Deletes a client document note by its note_id."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("DELETE FROM ClientDocumentNotes WHERE note_id = ?", (note_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_client_document_note for note_id {note_id}: {e}")
#         if conn: conn.rollback()
#         return False
#     finally:
#         if conn: conn.close()

# def get_client_document_note_by_id(note_id: int) -> dict | None:
#     """
#     Fetches a single client document note by its note_id.
#     Returns a dictionary containing all fields of the note, or None if not found.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM ClientDocumentNotes WHERE note_id = ?", (note_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_client_document_note_by_id for note_id {note_id}: {e}")
#         return None
#     finally:
#         if conn:
#             conn.close()

# CRUD functions for SmtpConfigs
# def _ensure_single_default_smtp(cursor: sqlite3.Cursor, exclude_id: int | None = None):
#     """Internal helper to ensure only one SMTP config is default."""
#     sql = "UPDATE SmtpConfigs SET is_default = FALSE WHERE is_default = TRUE"
#     if exclude_id is not None:
#         sql += " AND smtp_config_id != ?"
#         cursor.execute(sql, (exclude_id,))
#     else:
#         cursor.execute(sql)

# def add_smtp_config(config_data: dict) -> int | None:
#     """
#     Adds a new SMTP config. Returns smtp_config_id or None.
#     Expects 'password_encrypted'. Handles 'is_default' logic.
#     """
#     conn = None
#     try:
#         conn = get_db_connection()
#         # Use a transaction for default handling
#         conn.isolation_level = None # Explicitly start transaction for some Python versions / DB drivers
#         cursor = conn.cursor()
#         cursor.execute("BEGIN")

#         if config_data.get('is_default'):
#             _ensure_single_default_smtp(cursor)

#         now = datetime.utcnow().isoformat() + "Z" # Not in schema, but good practice if it were
#         sql = """
#             INSERT INTO SmtpConfigs (
#                 config_name, smtp_server, smtp_port, username, password_encrypted,
#                 use_tls, is_default, sender_email_address, sender_display_name
#             ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
#         """
#         params = (
#             config_data.get('config_name'), config_data.get('smtp_server'),
#             config_data.get('smtp_port'), config_data.get('username'),
#             config_data.get('password_encrypted'), # Assumed pre-encrypted
#             config_data.get('use_tls', True),
#             config_data.get('is_default', False),
#             config_data.get('sender_email_address'),
#             config_data.get('sender_display_name')
#         )
#         cursor.execute(sql, params)
#         new_id = cursor.lastrowid
#         conn.commit()
#         return new_id
#     except sqlite3.Error as e:
#         if conn: conn.rollback()
#         print(f"Database error in add_smtp_config: {e}")
#         return None
#     finally:
#         if conn:
#             conn.isolation_level = '' # Reset to default
#             conn.close()


# def get_smtp_config_by_id(smtp_config_id: int) -> dict | None:
#     """Retrieves an SMTP config by ID."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM SmtpConfigs WHERE smtp_config_id = ?", (smtp_config_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"Database error in get_smtp_config_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_default_smtp_config() -> dict | None:
#     """Retrieves the default SMTP config."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM SmtpConfigs WHERE is_default = TRUE")
#         row = cursor.fetchone()
#         return dict(row) if row else None # Could be multiple if DB constraint not present, returns first
#     except sqlite3.Error as e:
#         print(f"Database error in get_default_smtp_config: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_all_smtp_configs() -> list[dict]:
#     """Retrieves all SMTP configs."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM SmtpConfigs ORDER BY config_name")
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"Database error in get_all_smtp_configs: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_smtp_config(smtp_config_id: int, config_data: dict) -> bool:
#     """
#     Updates an SMTP config. Handles 'is_default' logic.
#     Expects 'password_encrypted' if password is to be changed.
#     """
#     conn = None
#     if not config_data: return False
#     try:
#         conn = get_db_connection()
#         conn.isolation_level = None
#         cursor = conn.cursor()
#         cursor.execute("BEGIN")

#         if config_data.get('is_default'):
#             _ensure_single_default_smtp(cursor, exclude_id=smtp_config_id)

#         # Ensure password_encrypted is handled if present, otherwise original remains
#         # This assumes if 'password_encrypted' is not in config_data, it's not being updated.
#         valid_columns = [
#             'config_name', 'smtp_server', 'smtp_port', 'username',
#             'password_encrypted', 'use_tls', 'is_default',
#             'sender_email_address', 'sender_display_name'
#         ]
#         current_config_data = {k: v for k,v in config_data.items() if k in valid_columns}
#         if not current_config_data:
#             conn.rollback() # No valid fields to update
#             return False

#         set_clauses = [f"{key} = ?" for key in current_config_data.keys()]
#         params = list(current_config_data.values())
#         params.append(smtp_config_id)

#         sql = f"UPDATE SmtpConfigs SET {', '.join(set_clauses)} WHERE smtp_config_id = ?"
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         if conn: conn.rollback()
#         print(f"Database error in update_smtp_config: {e}")
#         return False
#     finally:
#         if conn:
#             conn.isolation_level = ''
#             conn.close()

# def delete_smtp_config(smtp_config_id: int) -> bool:
#     """Deletes an SMTP config."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # Consider logic if deleting the default config (e.g., pick another or ensure none is default)
#         # For now, direct delete.
#         cursor.execute("DELETE FROM SmtpConfigs WHERE smtp_config_id = ?", (smtp_config_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"Database error in delete_smtp_config: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def set_default_smtp_config(smtp_config_id: int) -> bool:
#     """Sets a specific SMTP config as default and unsets others."""
#     conn = None
#     try:
#         conn = get_db_connection()
#         conn.isolation_level = None
#         cursor = conn.cursor()
#         cursor.execute("BEGIN")

#         _ensure_single_default_smtp(cursor, exclude_id=smtp_config_id)
#         cursor.execute("UPDATE SmtpConfigs SET is_default = TRUE WHERE smtp_config_id = ?", (smtp_config_id,))
#         updated_rows = cursor.rowcount

#         conn.commit()
#         return updated_rows > 0
#     except sqlite3.Error as e:
#         if conn: conn.rollback()
#         print(f"Database error in set_default_smtp_config: {e}")
#         return False
#     finally:
#         if conn:
#             conn.isolation_level = ''
#             conn.close()

# --- ScheduledEmails Functions ---
# def add_scheduled_email(email_data: dict) -> int | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         now = datetime.utcnow().isoformat() + "Z"
#         sql = """INSERT INTO ScheduledEmails (recipient_email, subject, body_html, body_text,
#                                            scheduled_send_at, status, related_client_id,
#                                            related_project_id, created_by_user_id, created_at)
#                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
#         params = (
#             email_data.get('recipient_email'), email_data.get('subject'),
#             email_data.get('body_html'), email_data.get('body_text'),
#             email_data.get('scheduled_send_at'), email_data.get('status', 'pending'),
#             email_data.get('related_client_id'), email_data.get('related_project_id'),
#             email_data.get('created_by_user_id'), now
#         )
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.lastrowid
#     except sqlite3.Error as e:
#         print(f"DB error in add_scheduled_email: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_scheduled_email_by_id(scheduled_email_id: int) -> dict | None:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM ScheduledEmails WHERE scheduled_email_id = ?", (scheduled_email_id,))
#         row = cursor.fetchone()
#         return dict(row) if row else None
#     except sqlite3.Error as e:
#         print(f"DB error in get_scheduled_email_by_id: {e}")
#         return None
#     finally:
#         if conn: conn.close()

# def get_pending_scheduled_emails(before_time: str = None) -> list[dict]:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "SELECT * FROM ScheduledEmails WHERE status = 'pending'"
#         params = []
#         if before_time:
#             sql += " AND scheduled_send_at <= ?"
#             params.append(before_time)
#         sql += " ORDER BY scheduled_send_at ASC"
#         cursor.execute(sql, params)
#         rows = cursor.fetchall()
#         return [dict(row) for row in rows]
#     except sqlite3.Error as e:
#         print(f"DB error in get_pending_scheduled_emails: {e}")
#         return []
#     finally:
#         if conn: conn.close()

# def update_scheduled_email_status(scheduled_email_id: int, status: str, sent_at: str = None, error_message: str = None) -> bool:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         sql = "UPDATE ScheduledEmails SET status = ?, sent_at = ?, error_message = ? WHERE scheduled_email_id = ?"
#         params = (status, sent_at, error_message, scheduled_email_id)
#         cursor.execute(sql, params)
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"DB error in update_scheduled_email_status: {e}")
#         return False
#     finally:
#         if conn: conn.close()

# def delete_scheduled_email(scheduled_email_id: int) -> bool:
#     conn = None
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
#         # ON DELETE CASCADE handles EmailReminders
#         cursor.execute("DELETE FROM ScheduledEmails WHERE scheduled_email_id = ?", (scheduled_email_id,))
#         conn.commit()
#         return cursor.rowcount > 0
#     except sqlite3.Error as e:
#         print(f"DB error in delete_scheduled_email: {e}")
#         return False
#     finally:
#         if conn: conn.close()