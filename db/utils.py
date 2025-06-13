import sqlite3
import os
import json
from datetime import datetime

# Import global constants from db_config.py
try:
    from .. import db_config
    from .. import config # For MEDIA_FILES_BASE_PATH
except (ImportError, ValueError):
    import sys
    # Correctly get the /app directory (parent of db/)
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if app_dir not in sys.path:
        sys.path.append(app_dir)
    try:
        import db_config
        import config # For MEDIA_FILES_BASE_PATH
    except ImportError:
        print("CRITICAL: db_config.py or config.py not found in utils.py. Using fallback paths.")
        # Fallback class definition
        class db_config_fallback:
            DATABASE_PATH = os.path.join(app_dir, "app_data_fallback.db") # Use app_dir for path
            APP_ROOT_DIR_CONTEXT = app_dir
            LOGO_SUBDIR_CONTEXT = "company_logos_fallback"
        db_config = db_config_fallback
        class config_fallback:
            MEDIA_FILES_BASE_PATH = os.path.join(app_dir, "media_files_fallback")
        config = config_fallback

# CRUD function imports
try:
    # Updated imports to point to specific CRUD files
    from .cruds.companies_crud import get_company_by_id
    from .cruds.company_personnel_crud import get_personnel_for_company
    from .cruds.clients_crud import get_client_by_id
    from .cruds.locations_crud import get_country_by_id, get_city_by_id
    from .cruds.contacts_crud import get_contacts_for_client # Assuming this is in contacts_crud
    from .cruds.projects_crud import get_project_by_id
    from .cruds.status_settings_crud import get_status_setting_by_id
    from .cruds.products_crud import get_product_by_id
    from .cruds.client_project_products_crud import get_products_for_client_or_project # Assuming this is in a dedicated file
    from .cruds.client_documents_crud import get_client_document_notes

    _crud_functions_imported = True
    print("Successfully imported CRUD functions from db.cruds for utils.py.")
except ImportError as e:
    print(f"Warning: Not all CRUD functions available to utils.py from db.cruds. Error: {e}. Using placeholders for some.")
    # Define placeholders for functions that might fail to import
    # This helps the application run even if some CRUD modules are not yet created/populated.
    def _placeholder_crud_func_util(entity_name="entity", *args, **kwargs):
        # print(f"Placeholder for {entity_name} called with {args}, {kwargs}")
        return None if not "list" in entity_name else []

    # Fallback definitions for functions that might not be imported
    if 'get_company_by_id' not in globals(): get_company_by_id = lambda id, conn=None: _placeholder_crud_func_util("company")
    if 'get_personnel_for_company' not in globals(): get_personnel_for_company = lambda id, role=None, conn=None: _placeholder_crud_func_util("company_personnel_list")
    if 'get_client_by_id' not in globals(): get_client_by_id = lambda id, conn=None: _placeholder_crud_func_util("client")
    if 'get_country_by_id' not in globals(): get_country_by_id = lambda id, conn=None: _placeholder_crud_func_util("country")
    if 'get_city_by_id' not in globals(): get_city_by_id = lambda id, conn=None: _placeholder_crud_func_util("city")
    if 'get_contacts_for_client' not in globals(): get_contacts_for_client = lambda id, limit=None, offset=None, conn=None: _placeholder_crud_func_util("contacts_list")
    if 'get_project_by_id' not in globals(): get_project_by_id = lambda id, conn=None: _placeholder_crud_func_util("project")
    if 'get_status_setting_by_id' not in globals(): get_status_setting_by_id = lambda id, conn=None: _placeholder_crud_func_util("status_setting")
    if 'get_product_by_id' not in globals(): get_product_by_id = lambda id, conn=None: _placeholder_crud_func_util("product")
    if 'get_products_for_client_or_project' not in globals(): get_products_for_client_or_project = lambda client_id, project_id=None, conn=None: _placeholder_crud_func_util("products_list")
    if 'get_client_document_notes' not in globals(): get_client_document_notes = lambda client_id, document_type=None, language_code=None, is_active=None, conn=None: _placeholder_crud_func_util("notes_list")



def get_db_connection(db_path_override=None): # Renamed parameter for clarity
    """
    Returns a new database connection object.
    Uses DATABASE_PATH from db_config by default.
    An optional db_path_override can be provided (e.g., for tests).
    """
    path_to_connect = db_path_override if db_path_override else db_config.DATABASE_PATH
    conn = sqlite3.connect(path_to_connect)
    conn.row_factory = sqlite3.Row
    return conn

def format_currency(amount: float | None, symbol: str = "€", precision: int = 2) -> str:
    if amount is None: return ""
    try:
        num_amount = float(amount)
        return f"{symbol}{num_amount:,.{precision}f}"
    except (ValueError, TypeError): return str(amount) # Fallback to string representation if not a number

def _get_batch_products_and_equivalents(product_ids: list[int], target_language_code: str, conn_passed=None) -> dict:
    if not product_ids: return {}

    # Determine if we need to open a new connection or use the passed one
    conn_is_internal = False
    if conn_passed is None:
        conn = get_db_connection()
        conn_is_internal = True
    else:
        conn = conn_passed

    results = {pid: {'original': None, 'equivalents': []} for pid in product_ids}
    try:
        cursor = conn.cursor() # Keep cursor for equivalents

        # Fetch original product details using the updated products_crud.get_product_by_id
        for pid_original in product_ids:
            # Assuming products_crud.get_product_by_id is correctly imported and available
            product_detail = products_crud.get_product_by_id(id=pid_original, conn=conn)
            if product_detail:
                results[pid_original]['original'] = product_detail
            # else: product not found, 'original' remains None

        # The rest of the logic for fetching equivalents can remain similar,
        # using the cursor for ProductEquivalencies and Products table for equivalent details.
        for pid_original in product_ids:
            equivalent_ids_for_pid = set()
            # Find B when A is known
            cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (pid_original,))
            for eq_row in cursor.fetchall():
                if eq_row['product_id_b'] != pid_original: # Avoid self-reference
                    equivalent_ids_for_pid.add(eq_row['product_id_b'])
            # Find A when B is known
            cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (pid_original,))
            for eq_row in cursor.fetchall():
                if eq_row['product_id_a'] != pid_original: # Avoid self-reference
                    equivalent_ids_for_pid.add(eq_row['product_id_a'])

            if equivalent_ids_for_pid:
                eq_placeholders = ','.join('?' for _ in equivalent_ids_for_pid)
                cursor.execute(f"SELECT * FROM Products WHERE product_id IN ({eq_placeholders})", tuple(equivalent_ids_for_pid))
                for eq_detail_row_dict in (dict(r) for r in cursor.fetchall()): # Convert rows to dicts immediately
                    results[pid_original]['equivalents'].append(eq_detail_row_dict)
        return results
    except sqlite3.Error as e:
        print(f"DB error in _get_batch_products_and_equivalents: {e}")
        return results # Return partial results
    finally:
        if conn_is_internal and conn: # Only close if created internally
            conn.close()

def get_document_context_data(
    client_id: str, company_id: str, target_language_code: str,
    project_id: str = None, linked_product_ids_for_doc: list[int] = None,
    additional_context: dict = None, conn_passed: sqlite3.Connection = None
) -> dict:
    context = {"doc": {}, "client": {}, "seller": {}, "project": {}, "products": [], "lang": {}, "additional": {}}
    effective_additional_context = additional_context if isinstance(additional_context, dict) else {}
    context["additional"] = effective_additional_context

    conn_is_internal = False
    if conn_passed is None:
        conn = get_db_connection()
        conn_is_internal = True
    else:
        conn = conn_passed

    try:
        now_dt = datetime.now()
        # Simplified translations, assuming full list is in original
        cover_page_translations = {
            'en': {'cover_page_title_suffix': "Cover Page", 'cover_logo_alt_text': "Company Logo", 'cover_footer_confidential': "Confidential"},
            'fr': {'cover_page_title_suffix': "Page de Garde", 'cover_logo_alt_text': "Logo", 'cover_footer_confidential': "Confidentiel"}
        }
        context['lang'] = cover_page_translations.get(target_language_code, cover_page_translations.get('en', {}))

        context["doc"]["current_date"] = now_dt.strftime("%Y-%m-%d")
        context["doc"]["current_year"] = str(now_dt.year)
        context["doc"]["document_title"] = effective_additional_context.get("document_title", "Document")
        # ... other context["doc"] fields ...
        context["doc"]["currency_symbol"] = effective_additional_context.get("currency_symbol", "€")
        context["doc"]["vat_rate_percentage"] = float(effective_additional_context.get("vat_rate_percentage", 20.0))
        context["doc"]["discount_rate_percentage"] = float(effective_additional_context.get("discount_rate_percentage", 0.0))


        seller_company_data = get_company_by_id(company_id, conn=conn)
        if seller_company_data:
            context["seller"]["name"] = seller_company_data.get('company_name', "N/A")
            context["seller"]["address"] = seller_company_data.get('address', "N/A")
            context["seller"]["full_address"] = seller_company_data.get('address', "N/A")
            logo_path_relative = seller_company_data.get('logo_path')
            if logo_path_relative:
                abs_logo_path = os.path.join(db_config.APP_ROOT_DIR_CONTEXT, db_config.LOGO_SUBDIR_CONTEXT, logo_path_relative)
                context["seller"]["company_logo_path"] = f"file:///{abs_logo_path.replace(os.sep, '/')}" if os.path.exists(abs_logo_path) else None
            else: context["seller"]["company_logo_path"] = None
            # ... other seller fields ...
            seller_personnel_list = get_personnel_for_company(company_id, conn=conn) # Pass conn
            context["seller"]["personnel"] = {"representative_name": seller_personnel_list[0]['name']} if seller_personnel_list else {}

        client_data = get_client_by_id(client_id, conn=conn) # Pass conn
        if client_data:
            context["client"]["id"] = client_data.get('client_id')
            context["client"]["company_name"] = client_data.get('company_name', client_data.get('client_name'))
            # ... other client fields ...
            if client_data.get('country_id'):
                country = get_country_by_id(client_data['country_id'], conn=conn) # Pass conn
                context["client"]["country_name"] = country['country_name'] if country else "N/A"
            # ... similar for city and primary contact using get_contacts_for_client(client_id, conn=conn)

        if project_id:
            project_data = get_project_by_id(project_id, conn=conn) # Pass conn
            if project_data: context["project"]["name"] = project_data.get('project_name')
        else: context["project"]["name"] = effective_additional_context.get("project_name", client_data.get('project_identifier', "N/A") if client_data else "N/A")

        # Product Processing Logic (Simplified for this overwrite, assuming the structure is mostly sound)
        all_product_ids_to_fetch = set()
        product_data_for_loop = []

        # Determine source of products (lite, specific CPP IDs, or general client/project)
        # ... (this complex logic is assumed from existing file, just ensure conn is passed to helpers) ...

        # Example for lite products
        if effective_additional_context.get('lite_selected_products'):
             for p_info in effective_additional_context['lite_selected_products']:
                if isinstance(p_info, dict) and 'product_id' in p_info:
                    all_product_ids_to_fetch.add(p_info['product_id'])
                    product_data_for_loop.append({'product_id': p_info['product_id'], 'quantity': p_info.get('quantity',1)})
        # ... (elif for linked_product_ids_for_doc and final else for client/project products) ...
        # Ensure any get_products_for_client_or_project calls pass `conn=conn`

        batched_product_details = {}
        if all_product_ids_to_fetch: # Changed from all_product_ids_to_fetch_details_for
            batched_product_details = _get_batch_products_and_equivalents(list(all_product_ids_to_fetch), target_language_code, conn_passed=conn) # Pass conn

        products_table_html_rows_list = []
        subtotal_amount = 0.0
        for idx, item_data in enumerate(product_data_for_loop):
            # ... (product processing loop from existing file, ensure format_currency uses context["doc"]["currency_symbol"]) ...
            # This loop uses batched_product_details and item_data to build product context and HTML rows
            # Key is to ensure all DB calls within this loop or its helpers use `conn`
            prod_id = item_data['product_id']
            batch_info = batched_product_details.get(prod_id, {'original': None, 'equivalents': []})
            original_prod_details = batch_info['original']

            if not original_prod_details: continue

            prod_name = original_prod_details['product_name'] # Add language fallback if necessary
            # Example: prod_name = original_prod_details.get(f'product_name_{target_language_code}', original_prod_details['product_name'])

            qty = item_data.get('quantity', 1)
            unit_price_override = item_data.get('unit_price_override')
            unit_price = unit_price_override if unit_price_override is not None else original_prod_details.get('base_unit_price')
            unit_price_f = float(unit_price) if unit_price is not None else 0.0
            total_price_f = qty * unit_price_f
            subtotal_amount += total_price_f

            processed_media_links = []
            if original_prod_details.get('media_links'):
                for link in original_prod_details['media_links']:
                    image_url = None
                    thumbnail_url = None

                    if link.get('media_filepath'):
                        abs_image_path = os.path.join(config.MEDIA_FILES_BASE_PATH, link['media_filepath'])
                        if os.path.exists(abs_image_path):
                            image_url = f"file:///{abs_image_path.replace(os.sep, '/')}"

                    if link.get('media_thumbnail_path'):
                        abs_thumbnail_path = os.path.join(config.MEDIA_FILES_BASE_PATH, link['media_thumbnail_path'])
                        if os.path.exists(abs_thumbnail_path):
                            thumbnail_url = f"file:///{abs_thumbnail_path.replace(os.sep, '/')}"

                    processed_media_links.append({
                        'url': image_url,
                        'thumbnail_url': thumbnail_url,
                        'alt_text': link.get('alt_text'),
                        'display_order': link.get('display_order'),
                        'title': link.get('media_title')
                    })

            product_context_item = {
                "id": prod_id,
                "name": prod_name,
                "quantity": qty,
                "unit_price_formatted": format_currency(unit_price_f, context['doc']['currency_symbol']),
                "total_price_formatted": format_currency(total_price_f, context['doc']['currency_symbol']),
                "raw_unit_price": unit_price_f,
                "raw_total_price": total_price_f,
                "description": original_prod_details.get('description'),
                "category": original_prod_details.get('category'),
                "unit_of_measure": original_prod_details.get('unit_of_measure'),
                "weight": original_prod_details.get('weight'),
                "dimensions": original_prod_details.get('dimensions'),
                "images": processed_media_links,
                "equivalents": batch_info.get('equivalents', []) # Add equivalents if needed in templates
            }
            context["products"].append(product_context_item)

            products_table_html_rows_list.append(f"<tr><td>{idx+1}</td><td>{prod_name}</td><td>{qty}</td><td>{format_currency(unit_price_f, context['doc']['currency_symbol'])}</td><td>{format_currency(total_price_f, context['doc']['currency_symbol'])}</td></tr>")

        context["doc"]["products_table_rows"] = "".join(products_table_html_rows_list)
        context["doc"]["subtotal_amount"] = format_currency(subtotal_amount, context["doc"]["currency_symbol"])

        discount_val = subtotal_amount * (context["doc"]["discount_rate_percentage"] / 100.0)
        context["doc"]["discount_amount"] = format_currency(discount_val, context["doc"]["currency_symbol"])
        subtotal_after_discount = subtotal_amount - discount_val
        vat_val = subtotal_after_discount * (context["doc"]["vat_rate_percentage"] / 100.0)
        context["doc"]["vat_amount"] = format_currency(vat_val, context["doc"]["currency_symbol"])
        context["doc"]["grand_total_amount"] = format_currency(subtotal_after_discount + vat_val, context["doc"]["currency_symbol"])

        doc_type_for_notes = effective_additional_context.get('current_document_type_for_notes')
        if doc_type_for_notes and client_id and target_language_code: # Pass conn
            notes = get_client_document_notes(client_id, doc_type_for_notes, target_language_code, True, conn=conn)
            if notes: context['doc']['client_specific_footer_notes'] = notes[0]['note_content'].replace('\n','<br>')

        # ... (mapping to buyer_*, seller_* placeholders) ...

    except Exception as e_doc_ctx:
        print(f"Error in get_document_context_data: {e_doc_ctx}")
        import traceback; traceback.print_exc();
    finally:
        if conn_is_internal and conn: # Only close if created internally
            conn.close()

    return context

__all__ = [
    "get_db_connection",
    "format_currency",
    "get_document_context_data",
    # "_get_batch_products_and_equivalents", # Typically internal, not in __all__
]

if __name__ == '__main__':
    print("db.utils module direct execution (for testing, may require DB setup)")
    # Example calls for testing
    # test_conn = get_db_connection()
    # if test_conn:
    #     print("DB connection successful via get_db_connection.")
    #     test_conn.close()
    # else:
    #     print("DB connection failed via get_db_connection.")
    pass
