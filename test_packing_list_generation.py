import os
import db as db_manager
import datetime # Not directly used but good for context
import json # Not directly used but good for context
import shutil # For potential directory cleanup if needed, though os.remove is used for files

def main():
    print("--- Starting Packing List Generation Test ---")

    # 1. Setup
    print("\n--- 1. Script Setup ---")
    db_manager.initialize_database()
    print("Database initialized.")

    APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    LOGO_DIR = os.path.join(APP_ROOT_DIR, "company_logos")
    TEMPLATES_DIR = os.path.join(APP_ROOT_DIR, "templates") # Used for reading templates

    os.makedirs(LOGO_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True) # Ensure base templates dir exists for reading
    # Language specific template dirs are assumed to be created by the previous subtask

    dummy_logo_filename = 'dummy_logo.png'
    dummy_logo_path = os.path.join(LOGO_DIR, dummy_logo_filename)
    try:
        open(dummy_logo_path, 'a').close()
        print(f"Dummy logo created at: {dummy_logo_path}")
    except IOError as e:
        print(f"Error creating dummy logo: {e}. Test might fail on logo path check.")


    # 2. Create Test Data
    print("\n--- 2. Creating Test Data ---")
    default_company_id = None
    client_id = None
    prod1_en_id = None
    prod1_fr_id = None

    try:
        # Default Company (Exporter)
        default_company = db_manager.get_default_company()
        if not default_company or default_company.get('company_name') != 'Test Exporter Co.':
            print("Default company 'Test Exporter Co.' not found or not set as default. Attempting to create/set.")
            # Clean up if a different default exists or if our target company exists but isn't default
            existing_exporter_co_list = db_manager.get_all_companies()
            for comp in existing_exporter_co_list:
                if comp['company_name'] == 'Test Exporter Co.':
                    db_manager.delete_company(comp['company_id']) # Remove if exists to ensure clean slate for logo path etc.
                    print(f"Removed pre-existing 'Test Exporter Co.' (ID: {comp['company_id']}) to recreate.")

            temp_company_id = db_manager.add_company({
                'company_name': 'Test Exporter Co.',
                'address': '123 Export Lane, Export City, EX1 2BC',
                'logo_path': dummy_logo_filename, # Relative path
                'is_default': False # Add as not default first
            })
            if temp_company_id is None:
                print("Error: Failed to create 'Test Exporter Co.'. Exiting.")
                return
            print(f"Created 'Test Exporter Co.' with ID: {temp_company_id}")
            if not db_manager.set_default_company(temp_company_id):
                print(f"Error: Failed to set 'Test Exporter Co.' (ID: {temp_company_id}) as default. Exiting.")
                db_manager.delete_company(temp_company_id) # cleanup
                return
            default_company = db_manager.get_default_company()
            if not default_company or default_company['company_id'] != temp_company_id:
                 print(f"Error: Failed to retrieve 'Test Exporter Co.' as default after setting. Exiting.")
                 db_manager.delete_company(temp_company_id) # cleanup
                 return

        default_company_id = default_company['company_id']
        print(f"Using Default Company: {default_company['company_name']} (ID: {default_company_id}) with logo: {default_company.get('logo_path')}")

        # Client Company (Consignee)
        existing_clients = db_manager.get_all_clients(filters={'project_identifier': 'PKL-TEST-001'})
        if existing_clients:
            client_id = existing_clients[0]['client_id']
            print(f"Using existing Client: {existing_clients[0].get('company_name', existing_clients[0]['client_name'])} (ID: {client_id})")
        else:
            # Need Country and City for client. Let's ensure some exist.
            country1_id = db_manager.add_country({'country_name': 'Testland'})
            if not country1_id: country1_id = db_manager.get_country_by_name('Testland')['country_id']
            city1_id = db_manager.add_city({'country_id': country1_id, 'city_name': 'Testville'})
            if not city1_id: city1_id = db_manager.get_city_by_name_and_country_id('Testville', country1_id)['city_id']

            client_id = db_manager.add_client({
                'client_name': 'Test Importer Contact',
                'company_name': 'Test Importer Inc.',
                'project_identifier': 'PKL-TEST-001',
                'country_id': country1_id,
                'city_id': city1_id
            })
            if client_id is None:
                print("Error: Failed to create Client. Exiting.")
                return
            print(f"Created Client: Test Importer Inc. (ID: {client_id})")

        # Products
        prod1_en = db_manager.get_product_by_name('Heavy Widget')
        if not prod1_en:
            prod1_en_id = db_manager.add_product({'product_name': 'Heavy Widget', 'description': 'A very heavy widget.', 'base_unit_price': 100, 'weight': 55.7, 'dimensions': '50x50x50 cm', 'language_code': 'en'})
        else:
            prod1_en_id = prod1_en['product_id']
        print(f"Product 'Heavy Widget' EN ID: {prod1_en_id}")
        if not prod1_en_id: print("Warning: Failed to create/get 'Heavy Widget' EN.")

        prod1_fr = db_manager.get_product_by_name('Widget Lourd')
        if not prod1_fr:
            prod1_fr_id = db_manager.add_product({'product_name': 'Widget Lourd', 'description': 'Un widget très lourd.', 'base_unit_price': 100, 'weight': 55.7, 'dimensions': '50x50x50 cm', 'language_code': 'fr'})
        else:
            prod1_fr_id = prod1_fr['product_id']
        print(f"Product 'Widget Lourd' FR ID: {prod1_fr_id}")
        if not prod1_fr_id: print("Warning: Failed to create/get 'Widget Lourd' FR.")

        if prod1_en_id and prod1_fr_id:
            equiv_id = db_manager.add_product_equivalence(prod1_en_id, prod1_fr_id)
            if equiv_id:
                print(f"Added equivalence between EN ID {prod1_en_id} and FR ID {prod1_fr_id}.")
            else:
                print(f"Failed to add equivalence or already exists for EN ID {prod1_en_id} and FR ID {prod1_fr_id}.")


        # 3. Define packing_details
        print("\n--- 3. Defining Packing Details Payload ---")
        heavy_widget_en_info = db_manager.get_product_by_id(prod1_en_id) if prod1_en_id else None
        heavy_widget_id_for_packing = heavy_widget_en_info['product_id'] if heavy_widget_en_info else None

        packing_items_data = [
            {
                'marks_nos': 'BOX 1/2', 'product_id': None,
                'product_name_override': 'Deluxe Gadget Model X',
                'quantity_description': '10 units per box',
                'num_packages': 1, 'package_type': 'Carton Box',
                'net_weight_kg_item': 25.5, 'gross_weight_kg_item': 27.0, 'dimensions_cm_item': '60x40x30 cm'
            }
        ]
        if heavy_widget_id_for_packing and heavy_widget_en_info:
            packing_items_data.append({
                'marks_nos': 'BOX 2/2', 'product_id': heavy_widget_id_for_packing,
                'product_name_override': None, # Test name resolution from product_id
                'quantity_description': 'Contains 5 Heavy Widgets',
                'num_packages': 1, 'package_type': 'Wooden Crate',
                'net_weight_kg_item': (heavy_widget_en_info.get('weight', 55.7) * 5),
                'gross_weight_kg_item': ((heavy_widget_en_info.get('weight', 55.7) + 2.3) * 5), # Example: gross = net + 2.3kg packaging per unit
                'dimensions_cm_item': '120x100x80 cm'
            })
        else:
            print("Warning: Heavy Widget product not found or ID missing, second packing item will use defaults.")
            packing_items_data.append({
                'marks_nos': 'BOX 2/2', 'product_id': None,
                'product_name_override': 'Generic Heavy Item',
                'quantity_description': '5 units',
                'num_packages': 1, 'package_type': 'Wooden Crate',
                'net_weight_kg_item': 250.0, 'gross_weight_kg_item': 260.0, 'dimensions_cm_item': '120x100x80 cm'
            })

        packing_details_payload = {
            'packing_list_id_override': 'PL-TEST-2024-001', # Used by db.py to fill context['doc']['packing_list_id']
            'invoice_id_override': 'INV-TEST-2024-001', # Used by db.py
            'project_id_override': 'PROJ-TEST-XYZ',
            'vessel_flight_no': 'OceanLiner-789',
            'port_of_loading': 'Port of Exportland',
            'port_of_discharge': 'Port of Importville',
            'final_destination_country': 'Republic of Importia',
            'notify_party_name': 'Global Notify Corp',
            'notify_party_address': '1 Notify Plaza, Notify City',
            'items': packing_items_data,
            'total_packages': sum(item.get('num_packages', 0) for item in packing_items_data),
            'total_net_weight_kg': sum(item.get('net_weight_kg_item', 0) for item in packing_items_data),
            'total_gross_weight_kg': sum(item.get('gross_weight_kg_item', 0) for item in packing_items_data),
            'total_volume_cbm': 1.5
        }
        print("Packing details payload defined.")

        # 4. Loop through target languages
        print("\n--- 4. Testing Context Generation and Templates ---")
        target_languages = ['en', 'fr', 'ar', 'tr']

        # Language specific static text checks
        lang_specific_checks = {
            'en': "Description of Goods",
            'fr': "Description des Marchandises",
            'ar': "وصف البضائع",
            'tr': "Malın Tanımı"
        }

        for lang_code in target_languages:
            print(f"\n--- Testing Language: {lang_code.upper()} ---")

            additional_context = {
                'document_type': 'packing_list',
                'packing_details': packing_details_payload,
                'packing_list_id': packing_details_payload['packing_list_id_override'], # Ensure this is passed
                'invoice_id': packing_details_payload['invoice_id_override'],
                'project_id': packing_details_payload['project_id_override'],
                'current_document_type_for_notes': 'PackingList' # For fetching notes
            }

            # Ensure client_id and default_company_id are valid before calling
            if not client_id or not default_company_id:
                print(f"Error: client_id ({client_id}) or default_company_id ({default_company_id}) is invalid for language {lang_code}. Skipping.")
                continue

            context = db_manager.get_document_context_data(
                client_id,
                default_company_id,
                lang_code,
                project_id=None, # Project ID for products usually comes from client_project_products, here we use packing_details
                additional_context=additional_context
            )

            # Assertions
            assert context['seller']['company_name'] == 'Test Exporter Co.', f"Seller name mismatch for {lang_code}"
            assert context['seller']['company_logo_path'] is not None and dummy_logo_filename in context['seller']['company_logo_path'], f"Seller logo path error for {lang_code}: {context['seller']['company_logo_path']}"
            assert context['client']['company_name'] == 'Test Importer Inc.', f"Client name mismatch for {lang_code}"

            # Check if overrides from packing_details_payload are effective in context['doc']
            assert context['doc']['packing_list_id'] == packing_details_payload['packing_list_id_override'], f"Packing list ID mismatch for {lang_code}"
            assert context['doc']['invoice_id'] == packing_details_payload['invoice_id_override'], f"Invoice ID mismatch for {lang_code}"
            # Note: context['project']['id'] might be from client.project_identifier if project_id not in additional_context for the main project field.
            # The packing_details_payload['project_id_override'] is primarily for display on the document itself if the template uses it.
            # Let's check if the project_id used for display in shipment_info section is the override:
            assert context['project_id'] == packing_details_payload['project_id_override'], f"Project ID for display mismatch in {lang_code}"


            assert str(packing_details_payload['total_net_weight_kg']) in context['doc']['total_net_weight'], f"Total net weight mismatch for {lang_code}: expected part of {packing_details_payload['total_net_weight_kg']}, got {context['doc']['total_net_weight']}"
            assert 'kg' in context['doc']['total_net_weight'], f"Missing 'kg' in total net weight for {lang_code}"
            assert str(packing_details_payload['total_gross_weight_kg']) in context['doc']['total_gross_weight'], f"Total gross weight mismatch for {lang_code}: expected part of {packing_details_payload['total_gross_weight_kg']}, got {context['doc']['total_gross_weight']}"
            assert 'kg' in context['doc']['total_gross_weight'], f"Missing 'kg' in total gross weight for {lang_code}"
            assert str(packing_details_payload['total_volume_cbm']) in context['doc']['total_volume_cbm'], f"Total volume mismatch for {lang_code}"
            assert 'CBM' in context['doc']['total_volume_cbm'], f"Missing 'CBM' in total volume for {lang_code}"

            # Item details checks
            assert 'Deluxe Gadget Model X' in context['doc']['packing_list_items'], f"Item 1 name 'Deluxe Gadget Model X' missing for {lang_code} in {context['doc']['packing_list_items']}"

            if heavy_widget_id_for_packing: # Only if the product was successfully created/found
                if lang_code == 'fr':
                    assert 'Widget Lourd' in context['doc']['packing_list_items'], f"French product name 'Widget Lourd' not resolved for Heavy Widget in {lang_code} in {context['doc']['packing_list_items']}"
                elif lang_code == 'en': # English should use English name
                     assert 'Heavy Widget' in context['doc']['packing_list_items'], f"English product name 'Heavy Widget' not found for Heavy Widget in {lang_code} in {context['doc']['packing_list_items']}"
                # For AR and TR, if no equivalent, it should fallback to original name from DB (which is English for prod1_en_id)
                elif lang_code in ['ar', 'tr']:
                     assert 'Heavy Widget' in context['doc']['packing_list_items'], f"Fallback English product name 'Heavy Widget' not found for Heavy Widget in {lang_code} in {context['doc']['packing_list_items']}"

            assert str(packing_items_data[0]['net_weight_kg_item']) in context['doc']['packing_list_items'], f"Item 1 net weight ({packing_items_data[0]['net_weight_kg_item']}) missing for {lang_code} in {context['doc']['packing_list_items']}"
            assert str(packing_items_data[1]['gross_weight_kg_item']) in context['doc']['packing_list_items'], f"Item 2 gross weight ({packing_items_data[1]['gross_weight_kg_item']}) missing for {lang_code} in {context['doc']['packing_list_items']}"

            # Price exclusion checks
            assert '€' not in context['doc']['packing_list_items'] and 'EUR' not in context['doc']['packing_list_items'].upper(), f"Currency symbol found in packing list items for {lang_code}"
            assert 'unit_price' not in context['doc']['packing_list_items'].lower() and 'prix unitaire' not in context['doc']['packing_list_items'].lower(), f"Unit price found in packing list items for {lang_code}"
            assert 'total_price' not in context['doc']['packing_list_items'].lower() and 'prix total' not in context['doc']['packing_list_items'].lower(), f"Total price found in packing list items for {lang_code}"

            assert not context.get('products', True), f"context['products'] not empty for packing list in {lang_code}. Content: {context.get('products')}" # Check if empty or None

            # Template file content check
            template_file_path = os.path.join(TEMPLATES_DIR, lang_code, 'packing_list_template.html')
            if os.path.exists(template_file_path):
                with open(template_file_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                check_text = lang_specific_checks.get(lang_code)
                assert check_text in template_content, f"Language-specific text '{check_text}' not found in template {template_file_path}"
                print(f"Template for {lang_code} read and specific text '{check_text}' confirmed.")
            else:
                print(f"Warning: Template file not found at {template_file_path}")

            print(f"Context data and template checks passed for language: {lang_code.upper()}")

        print("\nAll language tests completed successfully.")

    except AssertionError as e:
        print(f"\nAssertionError: {e}")
        print("TEST FAILED.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        print("TEST FAILED.")
    finally:
        # 5. Cleanup
        print("\n--- 5. Cleaning Up Test Data ---")
        if default_company_id and db_manager.get_company_by_id(default_company_id):
            db_manager.delete_company(default_company_id)
            print(f"Deleted company ID: {default_company_id}")
        if client_id and db_manager.get_client_by_id(client_id):
            db_manager.delete_client(client_id)
            print(f"Deleted client ID: {client_id}")

        # Product deletion needs to happen before equivalency (though cascade should handle it)
        # Equivalencies are deleted when products are deleted due to ON DELETE CASCADE
        if prod1_en_id and db_manager.get_product_by_id(prod1_en_id):
            db_manager.delete_product(prod1_en_id)
            print(f"Deleted product 'Heavy Widget' EN (ID: {prod1_en_id})")
        if prod1_fr_id and db_manager.get_product_by_id(prod1_fr_id):
            db_manager.delete_product(prod1_fr_id)
            print(f"Deleted product 'Widget Lourd' FR (ID: {prod1_fr_id})")

        if os.path.exists(dummy_logo_path):
            os.remove(dummy_logo_path)
            print(f"Deleted dummy logo: {dummy_logo_path}")

        print("Test data cleanup finished.")
        print("\n--- Packing List Generation Test Finished ---")

if __name__ == '__main__':
    main()
