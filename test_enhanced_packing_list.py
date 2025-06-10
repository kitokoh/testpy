import os
import db as db_manager
from datetime import datetime
import shutil

def setup_test_environment():
    print("--- 1. Setting up Test Environment ---")
    db_manager.initialize_database()
    print("Database initialized.")

    APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    LOGO_DIR = os.path.join(APP_ROOT_DIR, "company_logos")
    TEMPLATES_DIR = os.path.join(APP_ROOT_DIR, "templates")

    os.makedirs(LOGO_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

    dummy_logo_filename = 'test_logo.png'
    dummy_logo_path = os.path.join(LOGO_DIR, dummy_logo_filename)
    try:
        with open(dummy_logo_path, 'w') as f: # Create empty file
            f.write("dummy content")
        print(f"Dummy logo created at: {dummy_logo_path}")
    except IOError as e:
        print(f"Error creating dummy logo: {e}. Test might fail on logo path check.")

    # Ensure template language directories exist for context (though templates not directly rendered)
    for lang_code in ['en', 'fr', 'ar', 'tr']:
        os.makedirs(os.path.join(TEMPLATES_DIR, lang_code), exist_ok=True)

    return APP_ROOT_DIR, LOGO_DIR, TEMPLATES_DIR, dummy_logo_filename

def cleanup_test_environment(app_root_dir, logo_dir, dummy_logo_filename, company_id, client_id, product_ids, note_ids):
    print("\n--- 4. Cleaning Up Test Data ---")
    if company_id and db_manager.get_company_by_id(company_id):
        db_manager.delete_company(company_id)
        print(f"Deleted company ID: {company_id}")
    if client_id and db_manager.get_client_by_id(client_id):
        # ClientProjectProducts are cascaded by client deletion if FK is set up correctly
        db_manager.delete_client(client_id)
        print(f"Deleted client ID: {client_id}")

    for prod_id in product_ids:
        if prod_id and db_manager.get_product_by_id(prod_id):
            db_manager.delete_product(prod_id)
            print(f"Deleted product ID: {prod_id}")

    for note_id in note_ids:
        if note_id and db_manager.get_client_document_note_by_id(note_id):
            db_manager.delete_client_document_note(note_id)
            print(f"Deleted client document note ID: {note_id}")

    dummy_logo_path = os.path.join(logo_dir, dummy_logo_filename)
    if os.path.exists(dummy_logo_path):
        os.remove(dummy_logo_path)
        print(f"Deleted dummy logo: {dummy_logo_path}")

    # Optionally remove LOGO_DIR and TEMPLATES_DIR if they were created solely for this test
    # For now, just removing the dummy logo.
    # if os.path.exists(logo_dir): shutil.rmtree(logo_dir)
    # if os.path.exists(os.path.join(app_root_dir, "templates")): shutil.rmtree(os.path.join(app_root_dir, "templates"))
    print("Test data cleanup finished.")


def main():
    print("--- Starting Enhanced Packing List Generation Test ---")
    APP_ROOT_DIR, LOGO_DIR, TEMPLATES_DIR, dummy_logo_filename = setup_test_environment()

    default_company_id = None
    client_id = None
    prod_a_en_id, prod_a_fr_id, prod_b_en_id = None, None, None
    note_fr_id, note_en_id = None, None
    created_product_ids = []
    created_note_ids = []

    try:
        # 2. Create Test Data
        print("\n--- 2. Creating Test Data ---")

        # Default Company (Exporter)
        existing_exporter_list = db_manager.get_all_companies()
        for ex_co in existing_exporter_list: # Cleanup if exists from failed run
            if ex_co['company_name'] == 'Test Exporter Co.':
                db_manager.delete_company(ex_co['company_id'])

        default_company_id = db_manager.add_company({'company_name': 'Test Exporter Co.', 'address': 'Exporter Address, Exportland', 'logo_path': dummy_logo_filename, 'is_default': False})
        if not default_company_id: raise Exception("Failed to create Test Exporter Co.")
        db_manager.set_default_company(default_company_id)
        default_company = db_manager.get_default_company()
        assert default_company and default_company['company_id'] == default_company_id, "Failed to set/get default company"
        print(f"Default Company: {default_company['company_name']} (ID: {default_company_id})")

        # Client Company (Consignee)
        # Ensure country/city exist for client creation
        country_id = db_manager.add_country({'country_name': 'Importland'})
        if not country_id: country_id = db_manager.get_country_by_name('Importland')['country_id']
        city_id = db_manager.add_city({'country_id': country_id, 'city_name': 'Importcity'})
        if not city_id: city_id = db_manager.get_city_by_name_and_country_id('Importcity', country_id)['city_id']

        client_id = db_manager.add_client({'client_name': 'Importer Contact', 'company_name': 'Test Importer Ltd.', 'project_identifier': 'PACKTEST01', 'country_id': country_id, 'city_id': city_id})
        if not client_id: raise Exception("Failed to create client.")
        print(f"Client: Test Importer Ltd. (ID: {client_id})")

        # Products
        prod_a_en_id = db_manager.add_product({'product_name': 'Product A EN', 'description': 'English Product A', 'base_unit_price': 10, 'weight': 10.5, 'dimensions': '10x10x10cm', 'language_code': 'en'})
        if not prod_a_en_id: raise Exception("Failed to create Product A EN")
        created_product_ids.append(prod_a_en_id)
        prod_a_fr_id = db_manager.add_product({'product_name': 'Produit A FR', 'description': 'French Product A', 'base_unit_price': 10, 'weight': 10.5, 'dimensions': '10x10x10cm', 'language_code': 'fr'})
        if not prod_a_fr_id: raise Exception("Failed to create Product A FR")
        created_product_ids.append(prod_a_fr_id)
        db_manager.add_product_equivalence(prod_a_en_id, prod_a_fr_id)
        print(f"Product A EN (ID:{prod_a_en_id}), FR (ID:{prod_a_fr_id}) created and linked.")

        prod_b_en_id = db_manager.add_product({'product_name': 'Product B EN', 'description': 'English Product B', 'base_unit_price': 20, 'weight': 22.0, 'dimensions': '20x20x20cm', 'language_code': 'en'})
        if not prod_b_en_id: raise Exception("Failed to create Product B EN")
        created_product_ids.append(prod_b_en_id)
        print(f"Product B EN (ID:{prod_b_en_id}) created.")

        # Link Products to Client
        db_manager.add_product_to_client_or_project({'client_id': client_id, 'product_id': prod_a_en_id, 'quantity': 2})
        db_manager.add_product_to_client_or_project({'client_id': client_id, 'product_id': prod_b_en_id, 'quantity': 3})
        print("Products linked to client.")

        # Client Document Notes
        note_fr_id = db_manager.add_client_document_note({'client_id': client_id, 'document_type': 'HTML_PACKING_LIST', 'language_code': 'fr', 'note_content': 'Note spéciale pour le client FR.'})
        if not note_fr_id:
            print("Warning: Failed to add FR note.")
        else:
            created_note_ids.append(note_fr_id)
        note_en_id = db_manager.add_client_document_note({'client_id': client_id, 'document_type': 'HTML_PACKING_LIST', 'language_code': 'en', 'note_content': 'Special note for EN client.'})
        if not note_en_id:
            print("Warning: Failed to add EN note.")
        else:
            created_note_ids.append(note_en_id)
        print("Client document notes added.")

        # 3. Simulate CreateDocumentDialog data preparation
        print("\n--- 3. Simulating Dialog Data Preparation & Testing Context Generation ---")
        client_info_from_db = db_manager.get_client_by_id(client_id) # Simulate self.client_info
        if not client_info_from_db: raise Exception("Failed to fetch client_info from DB.")

        for target_lang in ['en', 'fr', 'ar', 'tr']:
            print(f"\n--- Testing Language: {target_lang.upper()} ---")
            additional_context = {}
            additional_context['document_type'] = 'packing_list'
            additional_context['current_document_type_for_notes'] = 'HTML_PACKING_LIST'

            packing_details_payload = {}
            linked_products = db_manager.get_products_for_client_or_project(client_id, project_id=None) # Fetch client-level products
            linked_products = linked_products if linked_products else []

            packing_items_data = []
            total_net_w = 0.0
            total_gross_w = 0.0
            total_pkg_count = 0

            for idx, product in enumerate(linked_products):
                net_w = float(product.get('weight', 0.0) or 0.0)
                quantity = float(product.get('quantity', 1.0) or 1.0)
                gross_w = net_w * 1.05 # Example: 5% markup for packaging
                dims = product.get('dimensions', 'N/A')
                num_pkgs_item = 1 # Default

                packing_items_data.append({
                    'marks_nos': f'PKGS {total_pkg_count + 1}',
                    'product_id': product.get('product_id'),
                    'product_name_override': None, # Let context resolver handle name
                    'quantity_description': f"{quantity} {product.get('unit_of_measure', 'units')}",
                    'num_packages': num_pkgs_item,
                    'package_type': 'Box', # Default
                    'net_weight_kg_item': net_w * quantity,
                    'gross_weight_kg_item': gross_w * quantity,
                    'dimensions_cm_item': dims
                })
                total_net_w += net_w * quantity
                total_gross_w += gross_w * quantity
                total_pkg_count += num_pkgs_item

            if not linked_products:
                 packing_items_data.append({
                    'marks_nos': 'N/A', 'product_id': None, 'product_name_override': 'No products found for this client/project.',
                    'quantity_description': '', 'num_packages': 0, 'package_type': '',
                    'net_weight_kg_item': 0, 'gross_weight_kg_item': 0, 'dimensions_cm_item': ''
                })

            packing_details_payload['items'] = packing_items_data
            packing_details_payload['total_packages'] = total_pkg_count
            packing_details_payload['total_net_weight_kg'] = round(total_net_w, 2)
            packing_details_payload['total_gross_weight_kg'] = round(total_gross_w, 2)
            packing_details_payload['total_volume_cbm'] = 'N/A' # Placeholder

            # Mimic dialog's way of setting these for additional_context
            additional_context['packing_list_id'] = f"PL-AUTO-{target_lang.upper()}"
            additional_context['invoice_id'] = f"INVREF-AUTO-{target_lang.upper()}" # Example reference
            additional_context['project_id'] = client_info_from_db.get('project_identifier', 'N/A')


            additional_context['packing_details'] = packing_details_payload

            context = db_manager.get_document_context_data(
                client_id,
                default_company['company_id'],
                target_lang,
                project_id=None, # Simulate no specific project passed to func, relying on client_info or additional_context
                additional_context=additional_context
            )

            # Assertions
            assert context['seller']['company_name'] == 'Test Exporter Co.', f"Seller name mismatch for {target_lang}"
            logo_path_check = context['seller'].get('company_logo_path', '')
            assert logo_path_check is not None and 'test_logo.png' in logo_path_check, f"Seller logo path error for {target_lang}, got: {logo_path_check}"
            assert context['client']['company_name'] == 'Test Importer Ltd.', f"Client name mismatch for {target_lang}"
            assert context['doc']['packing_list_id'] == f"PL-AUTO-{target_lang.upper()}", f"Packing list ID mismatch for {target_lang}, got {context['doc']['packing_list_id']}"

            assert len(context['doc']['packing_list_items']) > 0, f"Packing list items HTML is empty for {target_lang}"

            # Check product name resolution
            if target_lang == 'fr':
                assert 'Produit A FR' in context['doc']['packing_list_items'], f"FR name 'Produit A FR' missing for {target_lang}"
            elif target_lang == 'en':
                assert 'Product A EN' in context['doc']['packing_list_items'], f"EN name 'Product A EN' missing for {target_lang}"
            else: # AR, TR should fallback to original (EN in this case for Product A)
                assert 'Product A EN' in context['doc']['packing_list_items'], f"Fallback EN name 'Product A EN' missing for {target_lang}"

            assert 'Product B EN' in context['doc']['packing_list_items'], f"Product B EN name missing for {target_lang}"

            # Check weights and dimensions from items are present in the HTML string
            assert str(10.5 * 2) in context['doc']['packing_list_items'] or str(round(10.5 * 2, 2)) in context['doc']['packing_list_items'], f"Product A total net weight missing for {target_lang}" # Product A (10.5kg) * 2
            assert str(22.0 * 3) in context['doc']['packing_list_items'] or str(round(22.0 * 3, 2)) in context['doc']['packing_list_items'], f"Product B total net weight missing for {target_lang}" # Product B (22.0kg) * 3
            assert '10x10x10cm' in context['doc']['packing_list_items'], f"Product A dimensions missing for {target_lang}"

            # Price exclusion checks
            assert '€' not in context['doc']['packing_list_items'], f"Currency symbol € found in packing list items for {target_lang}"
            assert 'price' not in context['doc']['packing_list_items'].lower(), f"Term 'price' found in packing list items for {target_lang}"

            # Check notes
            if target_lang == 'fr':
                assert 'Note spéciale pour le client FR.' in context['doc']['client_specific_footer_notes'], f"FR note missing for {target_lang}"
            elif target_lang == 'en':
                assert 'Special note for EN client.' in context['doc']['client_specific_footer_notes'], f"EN note missing for {target_lang}"
            else: # AR, TR - no specific note added, so should be empty or default
                assert not context['doc']['client_specific_footer_notes'], f"Notes should be empty for {target_lang}, got: {context['doc']['client_specific_footer_notes']}"


            print(f"Context for {target_lang} generated.")
            print(f"  Packing List ID: {context['doc']['packing_list_id']}")
            print(f"  Total Net W: {context['doc']['total_net_weight']}, Total Gross W: {context['doc']['total_gross_weight']}, Total Pkgs: {context['doc']['total_packages']}")
            print(f"  Items HTML (snippet): {context['doc']['packing_list_items'][:250]}...")
            print(f"  Client Note: {context['doc']['client_specific_footer_notes']}")
            print(f"Context checks passed for {target_lang.upper()}")

        print("\nAll language tests completed successfully.")

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
        cleanup_test_environment(APP_ROOT_DIR, LOGO_DIR, dummy_logo_filename, default_company_id, client_id, created_product_ids, created_note_ids)
        print("\n--- Enhanced Packing List Generation Test Finished ---")

if __name__ == '__main__':
    main()
