import sqlite3
import os
import sys  # Keep sys import for path manipulation
import json
import sys # Import sys
from datetime import datetime
import logging # Keep logging import

# --- Configuration Import ---
# Get the application root directory (parent of 'db' directory)
app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir) # Insert at the beginning to ensure it's checked first

try:
    import config  # This should now find config.py at the root
    db_config = config # Alias config as db_config for compatibility
except ImportError as e:
    # This block should ideally not be reached if config.py exists at the root
    logging.critical(f"CRITICAL: config.py not found at root ({app_dir}) by db/utils.py. Error: {e}")
    # Optionally, re-raise the error or exit, as the application cannot function without config.
    raise ImportError(f"config.py is essential and was not found at {app_dir}") from e

# --- End Configuration Import ---

# CRUD function imports

    # CRUD imports removed to prevent circular dependencies.
    # Functions requiring CRUD operations will import `db` directly.
    print("CRUD functions will be imported dynamically in functions that need them.")


# get_db_connection moved to db.connection
from .connection import get_db_connection


def format_currency(amount: float | None, symbol: str = "€", precision: int = 2) -> str:
    if amount is None: return ""
    try:
        num_amount = float(amount)
        return f"{symbol}{num_amount:,.{precision}f}"
    except (ValueError, TypeError): return str(amount) # Fallback to string representation if not a number

def _get_batch_products_and_equivalents(product_ids: list[int], target_language_code: str, conn_passed=None) -> dict:
    # from .. import db # Avoid importing full db package
    from ..cruds.products_crud import get_product_by_id_details as products_get_product_by_id_details
    # Note: If other db.crud functions are needed, they must be imported specifically.
    if not product_ids: return {}

    conn_is_internal = False
    if conn_passed is None:
        conn = get_db_connection()
        conn_is_internal = True
    else:
        conn = conn_passed

    results = {pid: {'original': None, 'equivalents': []} for pid in product_ids}
    try:
        cursor = conn.cursor()

        for pid_original in product_ids:
            product_detail = products_get_product_by_id_details(id=pid_original, conn=conn) # Use specific import
            if product_detail:
                results[pid_original]['original'] = product_detail

        for pid_original in product_ids:
            if not results[pid_original]['original']: # Skip if original product wasn't found
                continue

            equivalent_ids_for_pid = set()
            cursor.execute("SELECT product_id_b FROM ProductEquivalencies WHERE product_id_a = ?", (pid_original,))
            for eq_row in cursor.fetchall():
                if eq_row['product_id_b'] != pid_original:
                    equivalent_ids_for_pid.add(eq_row['product_id_b'])
            cursor.execute("SELECT product_id_a FROM ProductEquivalencies WHERE product_id_b = ?", (pid_original,))
            for eq_row in cursor.fetchall():
                if eq_row['product_id_a'] != pid_original:
                    equivalent_ids_for_pid.add(eq_row['product_id_a'])

            if equivalent_ids_for_pid:
                eq_placeholders = ','.join('?' for _ in equivalent_ids_for_pid)
                # Fetch full details for equivalents
                cursor.execute(f"SELECT * FROM Products WHERE product_id IN ({eq_placeholders})", tuple(equivalent_ids_for_pid))
                for eq_detail_row in cursor.fetchall():
                    eq_detail_dict = dict(eq_detail_row)
                    # Optionally fetch media links for equivalents too, if needed in template
                    # eq_media_links = products_get_media_links_for_product(eq_detail_dict['product_id'], conn=conn)
                    # eq_detail_dict['media_links'] = eq_media_links
                    results[pid_original]['equivalents'].append(eq_detail_dict)
        return results
    except sqlite3.Error as e:
        logging.error(f"DB error in _get_batch_products_and_equivalents: {e}")
        return results
    finally:
        if conn_is_internal and conn:
            conn.close()

def get_document_context_data(
    client_id: str, company_id: str, target_language_code: str,
    project_id: str = None, linked_product_ids_for_doc: list[int] = None,
    additional_context: dict = None, conn_passed: sqlite3.Connection = None
) -> dict:
    # Import specific CRUD functions to avoid circular dependency with db package
    from ..cruds.companies_crud import get_company_by_id, get_personnel_for_company
    from ..cruds.clients_crud import get_client_by_id
    from ..cruds.locations_crud import get_country_by_id, get_city_by_id
    from ..cruds.contacts_crud import get_contacts_for_client
    from ..cruds.projects_crud import get_project_by_id
    from ..cruds.client_project_products_crud import get_client_project_product_by_id, get_products_for_client_or_project
    from ..cruds.templates_crud import get_client_document_notes # Assuming this is where it is

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
        cover_page_translations = {
            'en': {'cover_page_title_suffix': "Cover Page", 'cover_logo_alt_text': "Company Logo", 'cover_footer_confidential': "Confidential"},
            'fr': {'cover_page_title_suffix': "Page de Garde", 'cover_logo_alt_text': "Logo", 'cover_footer_confidential': "Confidentiel"}
        }
        context['lang'] = cover_page_translations.get(target_language_code, cover_page_translations.get('en', {}))

        context["doc"]["current_date"] = now_dt.strftime("%Y-%m-%d")
        context["doc"]["current_year"] = str(now_dt.year)
        context["doc"]["document_title"] = effective_additional_context.get("document_title", "Document")
        context["doc"]["currency_symbol"] = effective_additional_context.get("currency_symbol", "€")
        context["doc"]["vat_rate_percentage"] = float(effective_additional_context.get("vat_rate_percentage", 20.0))
        context["doc"]["discount_rate_percentage"] = float(effective_additional_context.get("discount_rate_percentage", 0.0))

        seller_company_data = get_company_by_id(company_id, conn=conn)
        if seller_company_data:
            context["seller"]["name"] = seller_company_data.get('company_name', "N/A")
            context["seller"]["address"] = seller_company_data.get('address', "N/A")
            context["seller"]["full_address"] = seller_company_data.get('address', "N/A") # Redundant, consider removing
            logo_path_relative = seller_company_data.get('logo_path')
            if logo_path_relative:
                # Ensure APP_ROOT_DIR and LOGO_SUBDIR are correctly defined in config
                abs_logo_path = os.path.join(config.APP_ROOT_DIR, config.LOGO_SUBDIR, logo_path_relative)
                context["seller"]["company_logo_path"] = f"file:///{abs_logo_path.replace(os.sep, '/')}" if os.path.exists(abs_logo_path) else None
            else:
                context["seller"]["company_logo_path"] = None

            seller_personnel_list = get_personnel_for_company(company_id, conn=conn)
            context["seller"]["phone"] = seller_company_data.get('phone', "N/A") # New
            context["seller"]["website"] = seller_company_data.get('website', "N/A") # New
            context["seller"]["vat_id"] = seller_company_data.get('vat_id', "N/A") # New
            context["seller"]["registration_number"] = seller_company_data.get('registration_number', "N/A") # New

            seller_personnel_list = get_personnel_for_company(company_id, conn=conn)
            if seller_personnel_list: # Check if list is not empty
                representative = seller_personnel_list[0] # Assuming the first person is representative
                context["seller"]["personnel"] = {
                    "representative_name": representative.get('name', "N/A"),
                    "representative_email": representative.get('email', "N/A"), # New
                    "representative_phone": representative.get('phone', "N/A")  # New
                }
            else:
                context["seller"]["personnel"] = {
                    "representative_name": "N/A",
                    "representative_email": "N/A",
                    "representative_phone": "N/A"
                }

        client_data = get_client_by_id(client_id, conn=conn)
        if client_data:
            context["client"]["id"] = client_data.get('client_id')
            context["client"]["name"] = client_data.get('client_name', "N/A") # Added for consistency
            context["client"]["company_name"] = client_data.get('company_name', client_data.get('client_name'))
            context["client"]["address"] = client_data.get('address', "N/A")
            context["client"]["phone"] = client_data.get('phone', "N/A") # New
            context["client"]["website"] = client_data.get('website', "N/A") # New
            context["client"]["vat_id"] = client_data.get('vat_id', "N/A") # New


            if client_data.get('country_id'):
                country = get_country_by_id(client_data['country_id'], conn=conn)
                context["client"]["country_name"] = country['country_name'] if country else "N/A"
            else:
                context["client"]["country_name"] = "N/A"

            if client_data.get('city_id'):
                city = get_city_by_id(client_data['city_id'], conn=conn)
                context["client"]["city_name"] = city['city_name'] if city else "N/A"
            else:
                context["client"]["city_name"] = "N/A"

            client_contacts = get_contacts_for_client(client_id, conn=conn) # Fetches all contacts
            primary_contact_data = None
            if client_contacts:
                # Try to find the one marked as primary
                for contact in client_contacts:
                    if contact.get('is_primary_for_client'): # Assuming 'is_primary_for_client' is set by get_contacts_for_client
                        primary_contact_data = contact
                        break
                if not primary_contact_data: # Fallback to the first contact if no primary is marked
                    primary_contact_data = client_contacts[0]

            if primary_contact_data:
                context["client"]["primary_contact_name"] = primary_contact_data.get('name', primary_contact_data.get('displayName', "N/A"))
                context["client"]["primary_contact_email"] = primary_contact_data.get('email', "N/A")
                context["client"]["primary_contact_phone"] = primary_contact_data.get('phone', "N/A") # New
            else:
                context["client"]["primary_contact_name"] = "N/A"
                context["client"]["primary_contact_email"] = "N/A"
                context["client"]["primary_contact_phone"] = "N/A" # New

        if project_id:
            project_data = get_project_by_id(project_id, conn=conn)
            if project_data:
                context["project"]["name"] = project_data.get('project_name')
                # Potentially add more project details if needed
        else:
            context["project"]["name"] = effective_additional_context.get("project_name", client_data.get('project_identifier', "N/A") if client_data else "N/A")

        all_product_ids_to_fetch = set()
        product_data_for_loop = []

        if effective_additional_context.get('lite_selected_products'):
            for p_info in effective_additional_context['lite_selected_products']:
                if isinstance(p_info, dict) and 'product_id' in p_info:
                    all_product_ids_to_fetch.add(p_info['product_id'])
                    # Store quantity and unit_price_override for later use
                    product_data_for_loop.append({
                        'product_id': p_info['product_id'],
                        'quantity': p_info.get('quantity', 1),
                        'unit_price_override': p_info.get('unit_price_override')
                    })
        elif linked_product_ids_for_doc: # Assuming this is a list of ClientProjectProduct IDs
            for cpp_id in linked_product_ids_for_doc:
                cpp_data = get_client_project_product_by_id(cpp_id, conn=conn)
                if cpp_data and cpp_data.get('product_id'):
                    all_product_ids_to_fetch.add(cpp_data['product_id'])
                    product_data_for_loop.append({
                        'product_id': cpp_data['product_id'],
                        'quantity': cpp_data.get('quantity', 1),
                        'unit_price_override': cpp_data.get('unit_price_override'),
                        'serial_number': cpp_data.get('serial_number')
                    })
        else: # Default to client/project products if no specific list provided
            client_project_products = get_products_for_client_or_project(client_id=client_id, project_id=project_id, conn=conn)
            for cpp_data in client_project_products:
                if cpp_data.get('product_id'):
                    all_product_ids_to_fetch.add(cpp_data['product_id'])
                    product_data_for_loop.append({
                        'product_id': cpp_data['product_id'],
                        'quantity': cpp_data.get('quantity', 1),
                        'unit_price_override': cpp_data.get('unit_price_override'),
                        'serial_number': cpp_data.get('serial_number')
                    })

        batched_product_details = {}
        if all_product_ids_to_fetch:
            batched_product_details = _get_batch_products_and_equivalents(list(all_product_ids_to_fetch), target_language_code, conn_passed=conn)

        products_table_html_rows_list = []
        subtotal_amount = 0.0

        for idx, item_data in enumerate(product_data_for_loop):
            prod_id = item_data['product_id']
            batch_info = batched_product_details.get(prod_id, {'original': None, 'equivalents': []})
            original_prod_details = batch_info['original']

            if not original_prod_details: continue

            prod_name = original_prod_details.get(f'product_name_{target_language_code}', original_prod_details.get('product_name', "N/A"))
            description = original_prod_details.get(f'description_{target_language_code}', original_prod_details.get('description', ""))

            qty = item_data.get('quantity', 1)
            unit_price_override = item_data.get('unit_price_override')
            unit_price = unit_price_override if unit_price_override is not None else original_prod_details.get('base_unit_price')
            unit_price_f = float(unit_price) if unit_price is not None else 0.0
            total_price_f = qty * unit_price_f
            subtotal_amount += total_price_f

            processed_media_links = []
            if original_prod_details.get('media_links'):
                for link in original_prod_details['media_links']:
                    image_url, thumbnail_url = None, None
                    if link.get('media_filepath'):
                        abs_image_path = os.path.join(config.MEDIA_FILES_BASE_PATH, link['media_filepath'])
                        image_url = f"file:///{abs_image_path.replace(os.sep, '/')}" if os.path.exists(abs_image_path) else None
                    if link.get('media_thumbnail_path'):
                        abs_thumbnail_path = os.path.join(config.MEDIA_FILES_BASE_PATH, link['media_thumbnail_path'])
                        thumbnail_url = f"file:///{abs_thumbnail_path.replace(os.sep, '/')}" if os.path.exists(abs_thumbnail_path) else image_url # Fallback to full image if no thumb

                    processed_media_links.append({
                        'url': image_url, 'thumbnail_url': thumbnail_url,
                        'alt_text': link.get('alt_text'), 'display_order': link.get('display_order'),
                        'title': link.get('media_title')
                    })

            product_context_item = {
                "id": prod_id, "name": prod_name, "quantity": qty,
                "unit_price_formatted": format_currency(unit_price_f, context['doc']['currency_symbol']),
                "total_price_formatted": format_currency(total_price_f, context['doc']['currency_symbol']),
                "raw_unit_price": unit_price_f, "raw_total_price": total_price_f,
                "description": description, "category": original_prod_details.get('category'),
                "unit_of_measure": original_prod_details.get('unit_of_measure'),
                "weight": original_prod_details.get('weight'), "dimensions": original_prod_details.get('dimensions'),
                "images": processed_media_links, "equivalents": batch_info.get('equivalents', [])
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
        if doc_type_for_notes and client_id and target_language_code:
            notes = get_client_document_notes(client_id=client_id, document_type=doc_type_for_notes, language_code=target_language_code, is_active=True, conn=conn)
            if notes: context['doc']['client_specific_footer_notes'] = notes[0]['note_content'].replace('\n','<br>')

        # Mapping to buyer_*, seller_* placeholders (ensure these are consistent)
        context["buyer_company_name"] = context["client"].get("company_name", "N/A")
        context["buyer_contact_name"] = context["client"].get("primary_contact_name", "N/A")
        context["buyer_address"] = context["client"].get("address", "N/A")
        context["buyer_phone"] = context["client"].get("primary_contact_phone", context["client"].get("phone", "N/A")) # New
        context["buyer_email"] = context["client"].get("primary_contact_email", "N/A") # New

        context["seller_company_name"] = context["seller"].get("name", "N/A")
        context["seller_contact_name"] = context["seller"].get("personnel", {}).get("representative_name", "N/A")
        context["seller_contact_email"] = context["seller"].get("personnel", {}).get("representative_email", "N/A") # New
        context["seller_contact_phone"] = context["seller"].get("personnel", {}).get("representative_phone", "N/A") # New
        context["seller_website"] = context["seller"].get("website", "N/A") # New
        context["seller_vat_id"] = context["seller"].get("vat_id", "N/A") # New


    except Exception as e_doc_ctx:
        logging.error(f"Error in get_document_context_data: {e_doc_ctx}")
        import traceback; traceback.print_exc(); # For more detailed error logging during development
    finally:
        if conn_is_internal and conn:
            conn.close()
    return context

__all__ = [
    # "get_db_connection", # Moved to db.connection
    "format_currency",
    "get_document_context_data",
]

if __name__ == '__main__': # pragma: no cover
    print("db.utils module direct execution (for testing, may require DB setup)")
    # Example calls for testing
    # test_conn = get_db_connection() # This would now use the import from .connection
    # if test_conn:
    #     print("DB connection successful via get_db_connection.")
    #     test_conn.close()
    # else:
    #     print("DB connection failed via get_db_connection.")
    pass
