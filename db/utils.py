import sqlite3
import os
import json
from datetime import datetime

# Ensure config is imported if APP_ROOT_DIR is used globally, or pass it around.
# For now, assuming DATABASE_PATH is the primary global use from config here.
from config import DATABASE_PATH, APP_ROOT_DIR


# No top-level CRUD imports here to prevent circular dependencies


def get_db_connection(db_path_override=None):
    """
    Returns a new database connection object.
    Uses DATABASE_PATH from config.py by default.
    An optional db_path_override can be provided (e.g., for tests).
    """
    path_to_connect = db_path_override if db_path_override else DATABASE_PATH
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
        cursor = conn.cursor()
        placeholders = ','.join('?' for _ in product_ids)
        cursor.execute(f"SELECT * FROM Products WHERE product_id IN ({placeholders})", tuple(product_ids))
        for row in cursor.fetchall():
            results[row['product_id']]['original'] = dict(row)

        for pid_original in product_ids: # Renamed pid to pid_original for clarity
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
    # Moved CRUD imports inside the function to break circular dependency
    from .cruds.companies_crud import get_company_by_id
    from .cruds.company_personnel_crud import get_all_company_personnel
    from .cruds.clients_crud import get_client_by_id
    from .cruds.locations_crud import get_country_by_id, get_city_by_id
    from .cruds.contacts_crud import get_contacts_for_client
    from .cruds.projects_crud import get_project_by_id
    from .cruds.status_settings_crud import get_status_setting_by_id
    from .cruds.products_crud import get_product_by_id
    from .cruds.client_project_products_crud import get_products_for_client_or_project
    from .cruds.client_document_notes_crud import get_client_document_notes

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
                # Assuming LOGO_SUBDIR_CONTEXT is defined in config or passed appropriately
                # For this example, direct use of APP_ROOT_DIR and a hardcoded/conf-loaded subdir name
                from config import LOGO_SUBDIR_CONTEXT # Ensure this is a valid import or handle otherwise
                abs_logo_path = os.path.join(APP_ROOT_DIR, LOGO_SUBDIR_CONTEXT, logo_path_relative)
                context["seller"]["company_logo_path"] = f"file:///{abs_logo_path.replace(os.sep, '/')}" if os.path.exists(abs_logo_path) else None
            else: context["seller"]["company_logo_path"] = None
            # ... other seller fields ...
            # Assuming get_all_company_personnel can be filtered by company_id or a more specific function exists
            seller_personnel_list = get_all_company_personnel(filters={'company_id': company_id}, conn=conn)
            context["seller"]["personnel"] = {"representative_name": seller_personnel_list[0]['full_name']} if seller_personnel_list else {} # Used full_name for consistency

        client_data = get_client_by_id(client_id, conn=conn)
        if client_data:
            context["client"]["id"] = client_data.get('client_id')
            context["client"]["company_name"] = client_data.get('company_name', client_data.get('client_name'))
            # ... other client fields ...
            if client_data.get('country_id'):
                country = get_country_by_id(client_data['country_id'], conn=conn)
                context["client"]["country_name"] = country['country_name'] if country else "N/A"
            if client_data.get('city_id'): # Added city fetch
                city = get_city_by_id(client_data['city_id'], conn=conn)
                context["client"]["city_name"] = city['city_name'] if city else "N/A"

            # Fetch primary contact (example logic, might need adjustment based on contacts_crud)
            client_contacts = get_contacts_for_client(client_id, filters={'is_primary_for_client': True}, conn=conn)
            if client_contacts:
                primary_contact = client_contacts[0]
                context["client"]["primary_contact_name"] = primary_contact.get('name')
                context["client"]["primary_contact_email"] = primary_contact.get('email')
                context["client"]["primary_contact_phone"] = primary_contact.get('phone')


        if project_id:
            project_data = get_project_by_id(project_id, conn=conn) # Already correct
            if project_data:
                context["project"]["name"] = project_data.get('project_name')
                # Fetch status name for project if status_id is present
                status_id = project_data.get('status_id')
                if status_id:
                    status_info = get_status_setting_by_id(status_id, conn=conn) # Pass conn
                    context["project"]["status_name"] = status_info.get('status_name') if status_info else "N/A"
        else:
            context["project"]["name"] = effective_additional_context.get("project_name", client_data.get('project_identifier', "N/A") if client_data else "N/A")

        # Product Processing Logic
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
        elif linked_product_ids_for_doc: # Assuming this is a list of ClientProjectProduct IDs
            # This branch would need to fetch ClientProjectProducts items then their Product details
            # For now, just ensuring the call to get_products_for_client_or_project (if used for this) passes conn
            # This part of logic might need more review based on how linked_product_ids_for_doc is actually used.
            # Placeholder: Assuming it might lead to a get_products_for_client_or_project call if not handled by lite_selected_products
            pass # This part needs to be carefully reviewed against original db.py if it's complex
        elif client_id: # Fallback to fetch products for client/project if no specific list
             product_data_for_loop = get_products_for_client_or_project(client_id, project_id, conn=conn) # Pass conn
             for p_info in product_data_for_loop:
                 if isinstance(p_info, dict) and 'product_id' in p_info:
                     all_product_ids_to_fetch.add(p_info['product_id'])
             # Note: product_data_for_loop here is already detailed, _get_batch_products_and_equivalents might be redundant
             # or used to enrich it further (e.g. with equivalents). This matches the original db.py structure.


        batched_product_details = {}
        if all_product_ids_to_fetch:
            batched_product_details = _get_batch_products_and_equivalents(list(all_product_ids_to_fetch), target_language_code, conn_passed=conn)

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

            prod_name = original_prod_details['product_name']
            # Language fallback logic...

            qty = item_data.get('quantity', 1)
            unit_price = item_data.get('unit_price_override', original_prod_details['base_unit_price'])
            unit_price_f = float(unit_price) if unit_price is not None else 0.0
            total_price_f = qty * unit_price_f
            subtotal_amount += total_price_f

            products_table_html_rows_list.append(f"<tr><td>{idx+1}</td><td>{prod_name}</td><td>{qty}</td><td>{format_currency(unit_price_f, context['doc']['currency_symbol'])}</td><td>{format_currency(total_price_f, context['doc']['currency_symbol'])}</td></tr>")
            context["products"].append({"id": prod_id, "name": prod_name, "raw_unit_price": unit_price_f, "raw_total_price": total_price_f})


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
