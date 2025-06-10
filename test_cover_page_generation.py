import os
import db as db_manager
from datetime import datetime
import shutil
# Import app_setup to call initialize_default_templates if needed, and to access CONFIG
import app_setup

def setup_test_environment():
    print("--- 1. Setting up Test Environment ---")
    db_manager.initialize_database()
    print("Database initialized.")

    # Use APP_ROOT_DIR from app_setup for consistency
    APP_ROOT_DIR = app_setup.APP_ROOT_DIR
    LOGO_DIR = os.path.join(APP_ROOT_DIR, app_setup.LOGO_SUBDIR) # Use LOGO_SUBDIR from app_setup
    TEMPLATES_DIR = app_setup.CONFIG["templates_dir"] # Use templates_dir from CONFIG

    os.makedirs(LOGO_DIR, exist_ok=True)
    print(f"Logo directory ensured: {LOGO_DIR}")
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    print(f"Templates directory ensured: {TEMPLATES_DIR}")

    dummy_logo_filename = 'cover_test_logo.png'
    dummy_logo_path = os.path.join(LOGO_DIR, dummy_logo_filename)
    try:
        with open(dummy_logo_path, 'w') as f:
            f.write("dummy logo content")
        print(f"Dummy logo created at: {dummy_logo_path}")
    except IOError as e:
        print(f"Error creating dummy logo: {e}. Test might fail on logo path check.")

    # Ensure template language directories exist
    for lang_code in ['en', 'fr', 'ar', 'tr', 'pt']: # Include all languages for which templates might exist
        lang_dir = os.path.join(TEMPLATES_DIR, lang_code)
        os.makedirs(lang_dir, exist_ok=True)
        # Delete specific old cover page template to force recreation with new content
        template_file_path = os.path.join(lang_dir, 'cover_page_template.html')
        if os.path.exists(template_file_path):
            os.remove(template_file_path)
            print(f'Removed old template: {template_file_path}')

    # Now, initialize default templates. This will recreate cover_page_template.html with new content.
    print("Initializing default templates...")
    app_setup.initialize_default_templates(app_setup.CONFIG, APP_ROOT_DIR)
    print("Default templates initialized.")

    return APP_ROOT_DIR, LOGO_DIR, TEMPLATES_DIR, dummy_logo_filename

def cleanup_test_environment(logo_dir, dummy_logo_filename, company_id, client_id, project_id):
    print("\n--- 4. Cleaning Up Test Data ---")
    if project_id and db_manager.get_project_by_id(project_id):
        db_manager.delete_project(project_id)
        print(f"Deleted project ID: {project_id}")
    if company_id and db_manager.get_company_by_id(company_id):
        db_manager.delete_company(company_id)
        print(f"Deleted company ID: {company_id}")
    if client_id and db_manager.get_client_by_id(client_id):
        db_manager.delete_client(client_id)
        print(f"Deleted client ID: {client_id}")

    dummy_logo_path = os.path.join(logo_dir, dummy_logo_filename)
    if os.path.exists(dummy_logo_path):
        os.remove(dummy_logo_path)
        print(f"Deleted dummy logo: {dummy_logo_path}")

    print("Test data cleanup finished.")

def main():
    print("--- Starting Cover Page Generation Test ---")
    APP_ROOT_DIR, LOGO_DIR, TEMPLATES_DIR, dummy_logo_filename = setup_test_environment()

    default_company_id = None
    client_id = None
    project_id_for_test = None # Renamed to avoid conflict with project_id var in loop

    try:
        # 2. Create Test Data
        print("\n--- 2. Creating Test Data ---")

        # Default Company (Exporter)
        # Clean up if exists from a failed run to ensure is_default logic works
        existing_exporter_list = db_manager.get_all_companies()
        for ex_co in existing_exporter_list:
            if ex_co['company_name'] == 'Cover Test Exporter Inc.':
                db_manager.delete_company(ex_co['company_id'])
                print(f"Deleted pre-existing 'Cover Test Exporter Inc.' (ID: {ex_co['company_id']})")

        default_company_id = db_manager.add_company({
            'company_name': 'Cover Test Exporter Inc.',
            'address': '1 Tech Park, Silicon Valley',
            'logo_path': dummy_logo_filename,
            'is_default': False
        })
        if not default_company_id: raise Exception("Failed to create 'Cover Test Exporter Inc.'")
        db_manager.set_default_company(default_company_id)
        default_company_check = db_manager.get_default_company()
        assert default_company_check and default_company_check['company_id'] == default_company_id, "Failed to set/get default company for exporter."
        print(f"Default Company: {default_company_check['company_name']} (ID: {default_company_id})")

        # Client Company
        # Ensure country/city exist for client creation
        country_id = db_manager.add_country({'country_name': 'Client Nation'})
        if not country_id: country_id = db_manager.get_country_by_name('Client Nation')['country_id']
        city_id = db_manager.add_city({'country_id': country_id, 'city_name': 'Client City'})
        if not city_id: city_id = db_manager.get_city_by_name_and_country_id('Client City', country_id)['city_id']

        client_id = db_manager.add_client({
            'client_name': 'Mr. Client Contact',
            'company_name': 'Cover Test Client Corp.',
            'project_identifier': 'CVR-TST-01',
            'country_id': country_id,
            'city_id': city_id
        })
        if not client_id: raise Exception("Failed to create client 'Cover Test Client Corp.'")
        print(f"Client: Cover Test Client Corp. (ID: {client_id})")

        # Project
        project_id_for_test = db_manager.add_project({
            'client_id': client_id,
            'project_name': 'Annual Report Cover Test'
            # Add other required fields for project if any, e.g., status_id
        })
        if not project_id_for_test: raise Exception("Failed to create project 'Annual Report Cover Test'")
        print(f"Project: Annual Report Cover Test (ID: {project_id_for_test})")


        # 3. Loop through target languages
        print("\n--- 3. Testing Context Generation and Template Content ---")

        default_company_for_context = db_manager.get_default_company() # Fetch again to ensure it's the correct one
        if not default_company_for_context:
             raise Exception("Default company could not be fetched for context generation.")

        target_languages = ['en', 'fr', 'ar', 'tr']
        for target_lang in target_languages:
            print(f"\n--- Testing Cover Page Language: {target_lang.upper()} ---")

            additional_context = {
                'document_type': 'HTML_COVER_PAGE',
                'document_title': f'Annual Report {target_lang.upper()}',
                'document_subtitle': f'Q4 Summary {target_lang.upper()}',
                'document_version': f'2.1.{target_lang}',
                'project_id': project_id_for_test, # Pass the actual project_id
            }

            context = db_manager.get_document_context_data(
                client_id,
                default_company_for_context['company_id'],
                target_lang,
                project_id=project_id_for_test, # Pass project_id here as well
                additional_context=additional_context
            )

            # Assertions
            assert context['seller']['company_name'] == 'Cover Test Exporter Inc.', f"Seller name mismatch for {target_lang}"
            logo_path_from_context = context['seller'].get('company_logo_path', '')
            assert logo_path_from_context is not None and dummy_logo_filename in logo_path_from_context, f"Seller logo path error for {target_lang}, got: '{logo_path_from_context}'"
            assert context['client']['company_name'] == 'Cover Test Client Corp.', f"Client name mismatch for {target_lang}"
            assert context['project']['name'] == 'Annual Report Cover Test', f"Project name mismatch for {target_lang}"
            assert context['doc']['document_title'] == f'Annual Report {target_lang.upper()}', f"Doc title mismatch for {target_lang}"
            assert context['doc']['document_version'] == f'2.1.{target_lang}', f"Doc version mismatch for {target_lang}"

            assert 'lang' in context, f"Lang dictionary missing in context for {target_lang}"
            assert context['lang'].get('cover_client_label') is not None, f"Client label missing in lang context for {target_lang}"

            if target_lang == 'fr':
                assert context['lang']['cover_client_label'] == 'Client', f"French translation error for client label"
                assert context['lang']['cover_page_title_suffix'] == 'Page de Garde', f"French translation error for title suffix"
            elif target_lang == 'ar':
                assert context['lang']['cover_page_title_suffix'] == 'صفحة الغلاف', f"Arabic translation error for title suffix"
                assert context['lang']['cover_prepared_for_title'] == 'أعدت لـ', f"Arabic translation error for prepared_for"

            # Check that notes are not populated for cover page if not specified
            notes_value = context['doc'].get('client_specific_footer_notes')
            assert notes_value == '' or notes_value is None, f"Client notes should be empty for cover page in {target_lang}, got: '{notes_value}'"

            print(f"  Document Title: {context['doc']['document_title']}")
            print(f"  Document Version: {context['doc']['document_version']}")
            print(f"  Lang Context Keys (sample): cover_client_label = '{context['lang'].get('cover_client_label')}'")

            # Verify Template File Content
            template_file_path = os.path.join(TEMPLATES_DIR, target_lang, "cover_page_template.html")
            assert os.path.exists(template_file_path), f"Template file missing: {template_file_path}"

            with open(template_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            assert "{{ doc.document_version }}" in content, f"Placeholder for document_version missing in template {target_lang}"
            assert "{{ lang.cover_client_label }}" in content, f"Placeholder for client label missing in template {target_lang}"
            assert "font-family: 'Roboto', Arial, sans-serif;" in content, f"CSS change for font-family not found in template {target_lang}"
            assert "border-top: 8px solid #3498db;" in content, f"CSS change for border-top not found in template {target_lang}"

            if target_lang == 'ar':
                # For RTL, check for dir="rtl" in <html> or body, or specific text-align in a main container
                assert 'dir="rtl"' in content.lower() or 'text-align: right' in content.lower(), f"RTL specific CSS/attribute might be missing for Arabic template."

            print(f"Template file {template_file_path} exists and key checks passed.")
            print(f"Context and template checks passed for {target_lang.upper()}")

        print("\nAll language tests for cover page completed successfully.")

    except AssertionError as e:
        print(f"\nAssertionError: {e}")
        import traceback
        traceback.print_exc()
        print("TEST FAILED.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        print("TEST FAILED.")
    finally:
        cleanup_test_environment(LOGO_DIR, dummy_logo_filename, default_company_id, client_id, project_id_for_test)
        print("\n--- Cover Page Generation Test Finished ---")

if __name__ == '__main__':
    main()
