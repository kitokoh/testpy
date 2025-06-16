import sqlite3 # Standard library, typically not used directly with SQLAlchemy
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
import json
import os
import logging # For logging errors

# Attempt to import from db module (db.py at root)
# Assuming db.py contains the necessary database interaction functions
try:
    from db import (
        get_db_session, # Assuming get_db() is renamed or get_db_session() is preferred
        # The following functions are expected to be in db.py or a similar accessible module
        # For this implementation, we'll mock/stub their existence if direct import fails
        # get_company_by_id,
        # get_personnel_for_company,
        # get_client_by_id,
        # get_country_by_id,
        # get_city_by_id,
        # get_contacts_for_client,
        # get_project_by_id,
        # get_product_by_id, # Individual product fetch
        # get_products_for_client_or_project, # For fetching linked ClientProjectProducts
        # get_client_document_notes,
    )
    # For _get_batch_products_and_equivalents, it's complex.
    # If it's in db.py and meant to be shared, it should be importable.
    # from db import _get_batch_products_and_equivalents
    from db.cruds.application_settings_crud import get_next_invoice_number # For final invoice numbers
except ImportError as e:
    logging.warning(f"Could not import all dependencies from db or cruds: {e}. Using placeholder functions. Full functionality requires db.py and cruds to be correctly structured and accessible.")
    # Define placeholder functions if db.py or its functions are not found
    def get_db_session(): raise NotImplementedError("get_db_session not imported/defined")
    def get_company_by_id(session, company_id): return None
    def get_personnel_for_company(session, company_id): return []
    def get_client_by_id(session, client_id): return None
    def get_country_by_id(session, country_id): return None
    def get_city_by_id(session, city_id): return None
    def get_contacts_for_client(session, client_id, is_primary=None): return []
    def get_project_by_id(session, project_id): return None
    def get_product_by_id(session, product_id): return None
    def get_products_for_client_or_project(session, client_id, project_id=None): return []
    def get_client_document_notes(session, client_id, document_type, language_code): return "N/A"


# --- Constants (Potentially from app_config.py or settings) ---
APP_ROOT_DIR_CONTEXT = os.path.dirname(os.path.abspath(__file__)) # Example
LOGO_SUBDIR_CONTEXT = "assets/logos" # Example

# --- Helper Functions ---
def _parse_json_field(json_string, default_value=None):
    if default_value is None:
        default_value = {}
    if isinstance(json_string, (dict, list)): # Already parsed
        return json_string
    if isinstance(json_string, str):
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            logging.warning(f"JSONDecodeError for string: {json_string[:100]}")
            return default_value
    return default_value

def _parse_key_value_string(kv_string, default_value=None):
    if default_value is None:
        default_value = {}
    if not isinstance(kv_string, str):
        return default_value
    parsed_data = {}
    try:
        pairs = kv_string.split(';')
        for pair in pairs:
            if ':' in pair:
                key, value = pair.split(':', 1)
                parsed_data[key.strip().lower().replace(" ", "_")] = value.strip()
    except Exception as e:
        logging.warning(f"Error parsing key-value string '{kv_string[:100]}': {e}")
        return default_value
    return parsed_data

def _format_address_parts(address_line1, city, postal_code, country):
    parts = [address_line1, city, postal_code, country]
    return ", ".join(filter(None, [str(p).strip() for p in parts if p and str(p).strip() != "N/A"])) or "N/A"

def format_currency(amount, currency_symbol="€", decimal_places=2):
    if amount is None or not isinstance(amount, (int, float)):
        return f"N/A {currency_symbol}"
    return f"{amount:,.{decimal_places}f} {currency_symbol}".replace(",", " ").replace(".", ",") # French format like "1 234,56 €"

# Placeholder for _get_batch_products_and_equivalents
# This is a complex function that would normally interact with a ProductEquivalents table.
def _get_batch_products_and_equivalents(db_session, product_ids: list, target_language_code: str):
    """
    Simplified placeholder. Real implementation would query Products and ProductEquivalents.
    Returns a dictionary mapping product_id to its details including potential translation.
    """
    products_data = {}
    for pid in product_ids:
        # Simulate fetching product data - replace with actual DB call using get_product_by_id
        # This mocked version assumes product_id itself contains info or calls a simple getter
        product = get_product_by_id(db_session, pid) # This would be a SQLAlchemy object
        if product:
            products_data[pid] = {
                "id": product.id,
                "original_name": product.name,
                "original_description": product.description,
                "original_language_code": product.language_code, # Assuming Product model has this
                "base_unit_price": product.base_unit_price,
                "unit_of_measure": product.unit_of_measure,
                "product_weight_kg": product.product_weight_kg,
                "product_dimensions_cm": product.product_dimensions_cm,
                "equivalent_name": None,
                "equivalent_description": None,
                "equivalent_language_code": None,
            }
            # Simulate finding an equivalent if target language is different
            if target_language_code != product.language_code and target_language_code == 'fr':
                 # In a real scenario, query ProductEquivalents table here
                products_data[pid]["equivalent_name"] = f"{product.name} (FR)"
                products_data[pid]["equivalent_description"] = f"{product.description} (Description Française)"
                products_data[pid]["equivalent_language_code"] = "fr"
        else:
            products_data[pid] = None # Product not found
    return products_data


def get_proforma_invoice_context_data(
    client_id: str,
    company_id: str,
    target_language_code: str,
    project_id: str = None,
    linked_product_ids_for_doc: list[int] = None,
    additional_context: dict = None
) -> dict:
    if additional_context is None:
        additional_context = {}

    context = {
        "doc": {}, "client": {}, "seller": {}, "project": {},
        "products": [], "lang": {}, "additional": additional_context,
        "placeholders": {} # For flat key-value access in template
    }

    # --- Language & Static Text ---
    context["lang"]["target_language_code"] = target_language_code
    # Add French static text if needed, though most is in the template itself.
    # context["lang"]["invoice_title"] = "FACTURE PROFORMA"

    # --- Document Info (defaults and from additional_context) ---
    doc_ctx = context["doc"]
    doc_ctx["current_date"] = additional_context.get("current_date", datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    doc_ctx["current_year"] = str(datetime.now(timezone.utc).year)
    doc_ctx["currency_symbol"] = additional_context.get("currency_symbol", "€") # Default to Euro
    doc_ctx["vat_rate_percentage"] = float(additional_context.get("vat_rate_percentage", 20.0)) # Default 20%
    doc_ctx["discount_rate_percentage"] = float(additional_context.get("discount_rate_percentage", 0.0))
    doc_ctx["proforma_id"] = additional_context.get("proforma_id", f"PF-{uuid.uuid4().hex[:8].upper()}")
    doc_ctx["payment_terms"] = additional_context.get("payment_terms", "Paiement anticipé")
    doc_ctx["delivery_terms"] = additional_context.get("delivery_terms", "Selon accord")
    doc_ctx["incoterms"] = additional_context.get("incoterms", "EXW") # Ex Works
    doc_ctx["named_place_of_delivery"] = additional_context.get("named_place_of_delivery", "Lieu du vendeur")


    db_session = None # Initialize
    try:
        # It's better to pass the session if this function is called from a context that already has one.
        # For now, assuming get_db_session() creates one if not provided via additional_context.
        db_session = additional_context.get("db_session") or get_db_session()

        # --- Seller Data ---
        seller_ctx = context["seller"]
        seller_company_data = get_company_by_id(db_session, company_id) if company_id else None
        if seller_company_data:
            seller_ctx["id"] = seller_company_data.id
            seller_ctx["company_name"] = seller_company_data.name or "N/A"
            seller_ctx["email"] = seller_company_data.email or "N/A"
            seller_ctx["phone"] = seller_company_data.phone or "N/A"
            seller_ctx["website"] = seller_company_data.website or "N/A"

            raw_address = seller_company_data.address or ""
            payment_info = _parse_json_field(seller_company_data.payment_info)
            other_info_json = _parse_json_field(seller_company_data.other_info)
            other_info_kv = _parse_key_value_string(seller_company_data.other_info)

            seller_ctx["bank_name"] = payment_info.get("bank_name", additional_context.get("seller_bank_name", "N/A"))
            seller_ctx["bank_account_number"] = payment_info.get("account_number", additional_context.get("seller_bank_account_number", "N/A"))
            seller_ctx["bank_swift_bic"] = payment_info.get("swift_bic", additional_context.get("seller_bank_swift_bic", "N/A"))
            seller_ctx["bank_address"] = payment_info.get("bank_address", additional_context.get("seller_bank_address", "N/A"))
            seller_ctx["bank_account_holder_name"] = payment_info.get("account_holder_name", seller_ctx["company_name"])
            seller_ctx["bank_iban"] = payment_info.get("iban", additional_context.get("seller_bank_iban", seller_ctx["bank_account_number"]))


            seller_ctx["vat_id"] = other_info_json.get("vat_id", other_info_kv.get("vat", other_info_kv.get("vat_id", additional_context.get("seller_vat_id", "N/A"))))
            seller_ctx["registration_number"] = other_info_json.get("registration_number", other_info_kv.get("reg", other_info_kv.get("registration_number", additional_context.get("seller_registration_number", "N/A"))))

            seller_ctx["address_line1"] = raw_address # Or parse more granularly if possible
            seller_ctx["city"] = additional_context.get("seller_city", "")
            seller_ctx["postal_code"] = additional_context.get("seller_postal_code", "")
            seller_ctx["country"] = additional_context.get("seller_country", "")
            seller_ctx["address"] = _format_address_parts(seller_ctx["address_line1"], seller_ctx["city"], seller_ctx["postal_code"], seller_ctx["country"])
            seller_ctx["city_zip_country"] = _format_address_parts(None, seller_ctx["city"], seller_ctx["postal_code"], seller_ctx["country"])


            seller_personnel = get_personnel_for_company(db_session, company_id)
            # Assuming first personnel is the representative, or filter by a role
            seller_rep = seller_personnel[0] if seller_personnel else {}
            seller_ctx["representative_name"] = f"{seller_rep.get('first_name','')} {seller_rep.get('last_name','')}".strip() or "N/A"

            logo_filename = seller_company_data.logo_filename or additional_context.get("seller_logo_filename")
            if logo_filename:
                seller_ctx["logo_path"] = os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, logo_filename)
            else:
                seller_ctx["logo_path"] = None
        else: # Fallbacks if no seller_company_data
            for k in ["company_name", "email", "phone", "website", "bank_name", "bank_account_number", "bank_swift_bic", "bank_address", "bank_account_holder_name", "bank_iban", "vat_id", "registration_number", "address_line1", "city", "postal_code", "country", "address", "representative_name", "logo_path", "city_zip_country"]:
                seller_ctx[k] = additional_context.get(f"seller_{k}", "N/A")


        # --- Client Data ---
        client_ctx = context["client"]
        client_data = get_client_by_id(db_session, client_id) if client_id else None
        if client_data:
            client_ctx["id"] = client_data.id
            client_ctx["company_name"] = client_data.company_name or "N/A"
            client_ctx["contact_person_name_default"] = client_data.client_name or "N/A" # Main contact from client table

            client_notes_json = _parse_json_field(client_data.notes)
            client_notes_kv = _parse_key_value_string(client_data.notes)
            client_dist_info_json = _parse_json_field(client_data.distributor_specific_info)
            client_dist_info_kv = _parse_key_value_string(client_data.distributor_specific_info)

            client_ctx["vat_id"] = client_notes_json.get("vat_id", client_notes_kv.get("vat", client_dist_info_json.get("vat_id", client_dist_info_kv.get("vat", additional_context.get("client_vat_id", "N/A")))))
            client_ctx["registration_number"] = client_notes_json.get("registration_number", client_notes_kv.get("reg", client_dist_info_json.get("registration_number", client_dist_info_kv.get("reg", additional_context.get("client_registration_number", "N/A")))))

            primary_contacts = get_contacts_for_client(db_session, client_id, is_primary=True)
            primary_contact = primary_contacts[0] if primary_contacts else None

            if primary_contact: # Primary contact from Contacts table
                client_ctx["representative_name"] = f"{primary_contact.first_name or ''} {primary_contact.last_name or ''}".strip() or client_ctx["contact_person_name_default"]
                client_ctx["email"] = primary_contact.email or client_data.email or "N/A" # Client's email as fallback
                client_ctx["phone"] = primary_contact.phone or client_data.phone or "N/A" # Client's phone as fallback
                client_ctx["address_line1"] = primary_contact.address_streetAddress or "N/A"
                client_ctx["city"] = primary_contact.address_city or (get_city_by_id(db_session, client_data.city_id).name if client_data.city_id else "N/A")
                client_ctx["postal_code"] = primary_contact.address_postalCode or "N/A"
                client_ctx["country"] = primary_contact.address_country or (get_country_by_id(db_session, client_data.country_id).name if client_data.country_id else "N/A")
            else: # Fallback to client table data or additional_context
                client_ctx["representative_name"] = client_ctx["contact_person_name_default"]
                client_ctx["email"] = client_data.email or additional_context.get("client_email", "N/A")
                client_ctx["phone"] = client_data.phone or additional_context.get("client_phone", "N/A")
                client_ctx["address_line1"] = client_data.address_line1 if hasattr(client_data, 'address_line1') else additional_context.get("client_address_line1", "N/A")
                client_ctx["city"] = (get_city_by_id(db_session, client_data.city_id).name if client_data.city_id else None) or additional_context.get("client_city", "N/A")
                client_ctx["postal_code"] = additional_context.get("client_postal_code", "N/A")
                client_ctx["country"] = (get_country_by_id(db_session, client_data.country_id).name if client_data.country_id else None) or additional_context.get("client_country", "N/A")

            client_ctx["address"] = _format_address_parts(client_ctx["address_line1"], client_ctx["city"], client_ctx["postal_code"], client_ctx["country"])
            client_ctx["city_zip_country"] = _format_address_parts(None, client_ctx["city"], client_ctx["postal_code"], client_ctx["country"])

        else: # Fallbacks if no client_data
             for k in ["company_name", "email", "phone", "vat_id", "registration_number", "address_line1", "city", "postal_code", "country", "address", "representative_name", "city_zip_country"]:
                client_ctx[k] = additional_context.get(f"client_{k}", "N/A")


        # --- Project Data ---
        project_ctx = context["project"]
        project_data = get_project_by_id(db_session, project_id) if project_id else None
        if project_data:
            project_ctx["id"] = project_data.id
            project_ctx["name"] = project_data.name or "N/A"
            project_ctx["description"] = project_data.description or "N/A"
            project_ctx["identifier"] = project_data.project_identifier or "N/A"
        else: # Fallbacks
            project_ctx["id"] = project_id or "N/A"
            project_ctx["name"] = additional_context.get("project_name", "N/A")
            project_ctx["description"] = additional_context.get("project_description", "N/A")
            project_ctx["identifier"] = additional_context.get("project_identifier", (client_data.project_identifier if client_data else "N/A"))


        # --- Products Data ---
        products_list_for_doc = []
        products_table_html_rows_list = []
        subtotal_amount_calculated = 0.0

        product_items_to_fetch = [] # List of (product_id, quantity, unit_price_override)

        if additional_context.get('lite_selected_products'):
            # Format: list of dicts e.g. [{"product_id": pid, "quantity": qty, "unit_price_override": price}, ...]
            for item in additional_context['lite_selected_products']:
                product_items_to_fetch.append((item["product_id"], item.get("quantity", 1), item.get("unit_price_override")))
        elif linked_product_ids_for_doc: # Assuming these are ClientProjectProduct IDs
            # Need to fetch ClientProjectProduct entries then get Product details
            # This part would require a specific DB function, e.g. get_client_project_products_by_ids
            logging.warning("Fetching by linked_product_ids_for_doc (ClientProjectProduct IDs) is not fully implemented in this stub.")
            # Mock fetching: for pid_ref in linked_product_ids_for_doc:
            #   cpp_entry = db_session.query(ClientProjectProduct).get(pid_ref)
            #   if cpp_entry: product_items_to_fetch.append((cpp_entry.product_id, cpp_entry.quantity, cpp_entry.unit_price_override))
            pass # Placeholder
        else: # Default: products linked to client/project
            client_project_products = get_products_for_client_or_project(db_session, client_id, project_id)
            for cpp in client_project_products:
                product_items_to_fetch.append((cpp.product_id, cpp.quantity, cpp.unit_price_override))

        # Batch fetch product details and their equivalents
        all_product_ids = [item[0] for item in product_items_to_fetch]
        product_details_batch = _get_batch_products_and_equivalents(db_session, all_product_ids, target_language_code)

        for p_id, quantity, unit_price_override in product_items_to_fetch:
            original_product_details = product_details_batch.get(p_id)
            if not original_product_details:
                logging.warning(f"Product with ID {p_id} not found in batch details. Skipping.")
                continue

            product_name_for_doc = original_product_details["original_name"]
            product_description_for_doc = original_product_details["original_description"]
            language_match = (original_product_details["original_language_code"] == target_language_code)

            if not language_match and original_product_details["equivalent_name"]:
                product_name_for_doc = original_product_details["equivalent_name"]
                product_description_for_doc = original_product_details["equivalent_description"]
                language_match = True # Considered a match if equivalent is used

            effective_unit_price = unit_price_override if unit_price_override is not None else original_product_details["base_unit_price"]
            if effective_unit_price is None: effective_unit_price = 0.0 # Ensure float

            total_price = float(quantity) * float(effective_unit_price)
            subtotal_amount_calculated += total_price

            product_entry = {
                "id": original_product_details["id"],
                "name": product_name_for_doc,
                "description": product_description_for_doc,
                "quantity": quantity,
                "unit_price_raw": float(effective_unit_price),
                "unit_price_formatted": format_currency(float(effective_unit_price), doc_ctx["currency_symbol"]),
                "total_price_raw": total_price,
                "total_price_formatted": format_currency(total_price, doc_ctx["currency_symbol"]),
                "unit_of_measure": original_product_details["unit_of_measure"],
                "language_match": language_match,
                "original_name": original_product_details["original_name"],
                "original_description": original_product_details["original_description"],
                "weight_kg": original_product_details["product_weight_kg"],
                "dimensions_cm": original_product_details["product_dimensions_cm"],
            }
            products_list_for_doc.append(product_entry)

            # Generate HTML row for table
            # This is a simplified version. Actual template might handle this better with a loop.
            products_table_html_rows_list.append(
                f"<tr><td>{len(products_list_for_doc)}</td>"
                f"<td><strong>{product_entry['name']}</strong><br><small>{product_entry['description'] or ''}</small></td>"
                f"<td class='number'>{product_entry['quantity']}</td>"
                f"<td class='number'>{product_entry['unit_price_formatted']}</td>"
                f"<td class='number'>{product_entry['total_price_formatted']}</td></tr>"
            )

        context["products"] = products_list_for_doc
        doc_ctx["products_table_rows"] = "".join(products_table_html_rows_list)

        # --- Totals ---
        doc_ctx["subtotal_amount_raw"] = subtotal_amount_calculated
        doc_ctx["subtotal_amount_formatted"] = format_currency(subtotal_amount_calculated, doc_ctx["currency_symbol"])

        discount_amount = (doc_ctx["discount_rate_percentage"] / 100.0) * subtotal_amount_calculated
        doc_ctx["discount_amount_raw"] = discount_amount
        doc_ctx["discount_amount_formatted"] = format_currency(discount_amount, doc_ctx["currency_symbol"])

        amount_after_discount = subtotal_amount_calculated - discount_amount
        vat_amount = (doc_ctx["vat_rate_percentage"] / 100.0) * amount_after_discount
        doc_ctx["vat_amount_raw"] = vat_amount
        doc_ctx["vat_amount_formatted"] = format_currency(vat_amount, doc_ctx["currency_symbol"])

        grand_total_amount = amount_after_discount + vat_amount
        doc_ctx["grand_total_amount_raw"] = grand_total_amount
        doc_ctx["grand_total_amount_formatted"] = format_currency(grand_total_amount, doc_ctx["currency_symbol"])

        # Placeholder for amount in words - requires a library or complex logic
        doc_ctx["grand_total_amount_words"] = additional_context.get("grand_total_amount_words", "N/A")

        # --- Client Specific Notes ---
        doc_notes_type = additional_context.get("client_document_notes_type", "Proforma")
        notes_text = get_client_document_notes(db_session, client_id, doc_notes_type, target_language_code)
        doc_ctx["client_specific_footer_notes"] = notes_text.replace('\n', '<br>') if notes_text else "N/A"

    except Exception as e:
        logging.error(f"Error in get_proforma_invoice_context_data: {e}", exc_info=True)
        # Populate with N/A to prevent crashes in template rendering
        for section in ["doc", "client", "seller", "project"]:
            if not context[section]: # if section is empty due to early error
                context[section] = {k: "Error - See Logs" for k in ["name", "id", "address"]} # basic error indication
        # Ensure critical doc values exist for template
        doc_ctx.setdefault("currency_symbol", "$")
        doc_ctx.setdefault("products_table_rows", "<tr><td colspan='5'>Error loading product data.</td></tr>")
        # ... (add more critical fallbacks for doc_ctx if needed)

    finally:
        # If this function created the session, it should close it.
        # However, it's better practice for the caller to manage session lifecycle.
        # For now, assuming session is managed by caller or a context manager via get_db_session() if it were a context manager
        # if db_session and not additional_context.get("db_session"):
        #     db_session.close()
        pass


    # --- Final Placeholder Mapping ---
    # This flattens the context for easier use in simple template engines or direct access
    # More complex engines like Jinja2 can access nested context directly (e.g. seller.company_name)

    # Document details
    context["placeholders"]["PROFORMA_ID"] = doc_ctx.get("proforma_id", "N/A")
    context["placeholders"]["DATE"] = doc_ctx.get("current_date", "N/A")
    context["placeholders"]["PAYMENT_TERMS"] = doc_ctx.get("payment_terms", "N/A")
    context["placeholders"]["DELIVERY_TERMS"] = doc_ctx.get("delivery_terms", "N/A")
    context["placeholders"]["INCOTERMS"] = doc_ctx.get("incoterms", "N/A")
    context["placeholders"]["NAMED_PLACE_OF_DELIVERY"] = doc_ctx.get("named_place_of_delivery", "N/A")
    context["placeholders"]["DOCUMENT_CURRENCY"] = doc_ctx.get("currency_symbol", "N/A") # Used for table items

    # Seller details
    context["placeholders"]["SELLER_COMPANY_NAME"] = seller_ctx.get("company_name", "N/A")
    context["placeholders"]["SELLER_ADDRESS_LINE1"] = seller_ctx.get("address_line1", "N/A")
    context["placeholders"]["SELLER_CITY"] = seller_ctx.get("city", "")
    context["placeholders"]["SELLER_POSTAL_CODE"] = seller_ctx.get("postal_code", "")
    context["placeholders"]["SELLER_COUNTRY"] = seller_ctx.get("country", "")
    context["placeholders"]["SELLER_FULL_ADDRESS"] = seller_ctx.get("address", "N/A") # Full formatted
    context["placeholders"]["SELLER_CITY_ZIP_COUNTRY"] = seller_ctx.get("city_zip_country", "N/A")
    context["placeholders"]["SELLER_COMPANY_PHONE"] = seller_ctx.get("phone", "N/A")
    context["placeholders"]["SELLER_COMPANY_EMAIL"] = seller_ctx.get("email", "N/A")
    context["placeholders"]["SELLER_VAT_ID"] = seller_ctx.get("vat_id", "N/A")
    context["placeholders"]["SELLER_REGISTRATION_NUMBER"] = seller_ctx.get("registration_number", "N/A")
    context["placeholders"]["SELLER_COMPANY_LOGO_PATH"] = seller_ctx.get("logo_path") # May be None
    context["placeholders"]["SELLER_BANK_NAME"] = seller_ctx.get("bank_name", "N/A")
    context["placeholders"]["SELLER_BANK_ACCOUNT_HOLDER_NAME"] = seller_ctx.get("bank_account_holder_name", "N/A")
    context["placeholders"]["SELLER_BANK_ACCOUNT_NUMBER"] = seller_ctx.get("bank_account_number", "N/A") # Generic
    context["placeholders"]["SELLER_BANK_IBAN"] = seller_ctx.get("bank_iban", "N/A") # Specific
    context["placeholders"]["SELLER_BANK_SWIFT_BIC"] = seller_ctx.get("bank_swift_bic", "N/A")
    context["placeholders"]["SELLER_BANK_ADDRESS"] = seller_ctx.get("bank_address", "N/A")


    # Client (Buyer) details
    context["placeholders"]["BUYER_COMPANY_NAME"] = client_ctx.get("company_name", "N/A")
    context["placeholders"]["BUYER_REPRESENTATIVE_NAME"] = client_ctx.get("representative_name", "N/A")
    context["placeholders"]["BUYER_ADDRESS_LINE1"] = client_ctx.get("address_line1", "N/A")
    context["placeholders"]["BUYER_CITY"] = client_ctx.get("city", "")
    context["placeholders"]["BUYER_POSTAL_CODE"] = client_ctx.get("postal_code", "")
    context["placeholders"]["BUYER_COUNTRY"] = client_ctx.get("country", "")
    context["placeholders"]["BUYER_FULL_ADDRESS"] = client_ctx.get("address", "N/A") # Full formatted
    context["placeholders"]["BUYER_CITY_ZIP_COUNTRY"] = client_ctx.get("city_zip_country", "N/A")
    context["placeholders"]["BUYER_PHONE"] = client_ctx.get("phone", "N/A")
    context["placeholders"]["BUYER_EMAIL"] = client_ctx.get("email", "N/A")
    context["placeholders"]["BUYER_VAT_NUMBER"] = client_ctx.get("vat_id", "N/A") # Template uses BUYER_VAT_NUMBER
    context["placeholders"]["BUYER_COMPANY_REGISTRATION_NUMBER"] = client_ctx.get("registration_number", "N/A")

    # Project details
    context["placeholders"]["PROJECT_ID"] = project_ctx.get("identifier", "N/A") # Using identifier for display
    context["placeholders"]["PROJECT_NAME"] = project_ctx.get("name", "N/A")

    # Totals
    context["placeholders"]["SUBTOTAL_AMOUNT"] = doc_ctx.get("subtotal_amount_formatted", "N/A")
    context["placeholders"]["DISCOUNT_RATE"] = str(doc_ctx.get("discount_rate_percentage", 0.0))
    context["placeholders"]["DISCOUNT_AMOUNT"] = doc_ctx.get("discount_amount_formatted", "N/A")
    context["placeholders"]["VAT_RATE"] = str(doc_ctx.get("vat_rate_percentage", 0.0))
    context["placeholders"]["VAT_AMOUNT"] = doc_ctx.get("vat_amount_formatted", "N/A")
    context["placeholders"]["GRAND_TOTAL_AMOUNT"] = doc_ctx.get("grand_total_amount_formatted", "N/A")
    context["placeholders"]["GRAND_TOTAL_AMOUNT_WORDS"] = doc_ctx.get("grand_total_amount_words", "N/A")

    # Merge any remaining additional_context items, giving precedence to already processed data
    for key, value in additional_context.items():
        # Typically, specific keys from additional_context are already extracted.
        # This can be used for less common or dynamic placeholders.
        context["placeholders"].setdefault(key.upper(), value)
        context["placeholders"].setdefault(key, value)


    # For direct access in template if preferred over placeholders dict
    context["doc"].update(doc_ctx) # Ensure doc_ctx changes are reflected
    context["seller"].update(seller_ctx)
    context["client"].update(client_ctx)
    context["project"].update(project_ctx)

    return context

if __name__ == '__main__':
    # This section is for example usage and basic testing.
    # It requires a mock DB setup or connection to a real DB with test data.
    print("Proforma Invoice Utilities Loaded.")

    # Example of how to call (requires mock data and DB session setup)
    # mock_additional_context = {
    #     "db_session": None, # Replace with actual or mocked DB session
    #     "seller_city": "Lyon",
    #     "seller_postal_code": "69001",
    #     "seller_country": "France",
    #     "currency_symbol": "EUR",
    #     # ... other overrides or additional data
    #     'lite_selected_products': [
    #         {"product_id": 1, "quantity": 2, "unit_price_override": 150.0},
    #         {"product_id": 2, "quantity": 5}
    #     ]
    # }

    # try:
    #     # Replace with actual IDs for testing
    #     # context_data = get_proforma_invoice_context_data(
    #     #     client_id="some_client_uuid_or_id",
    #     #     company_id="some_company_uuid_or_id",
    #     #     target_language_code="fr",
    #     #     project_id="some_project_uuid_or_id",
    #     #     additional_context=mock_additional_context
    #     # )
    #     # import pprint
    #     # pprint.pprint(context_data)
    #     print("To test, uncomment the example call and provide mock data/session.")
    # except Exception as e:
    #     print(f"Error during example test run: {e}")
    pass


def get_final_invoice_context_data(
    client_id: str,
    company_id: str,
    target_language_code: str,
    project_id: str = None,
    # line_items can be passed in additional_context:
    # e.g., additional_context['line_items'] = [{'product_id': X, 'quantity': Y, 'unit_price': Z}, ...]
    # linked_product_ids_for_doc is less likely for final invoice if prices/qtys are fixed from a quote/order
    additional_context: dict = None
) -> dict:
    if additional_context is None:
        additional_context = {}

    context = {
        "doc": {}, "client": {}, "seller": {}, "project": {},
        "products": [], "lang": {}, "additional": additional_context,
        "placeholders": {}
    }

    # --- Language & Static Text ---
    context["lang"]["target_language_code"] = target_language_code
    # Title can be set here or in template. If set here, it can be dynamic.
    # For multilingual, template is better for static titles.
    # We'll set a default that can be overridden by additional_context or template.
    context["doc"]["invoice_title"] = additional_context.get("invoice_title", "INVOICE")
    if target_language_code == "fr":
        context["doc"]["invoice_title"] = additional_context.get("invoice_title", "FACTURE")


    # --- Document Info (defaults and from additional_context) ---
    doc_ctx = context["doc"]
    # issue_date and due_date should ideally come from additional_context or be set when the invoice record is created.
    doc_ctx["issue_date"] = additional_context.get("issue_date", datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    default_due_date = (datetime.strptime(doc_ctx["issue_date"], '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')
    doc_ctx["due_date"] = additional_context.get("due_date", default_due_date)

    doc_ctx["currency_symbol"] = additional_context.get("currency_symbol", "€")
    doc_ctx["payment_terms"] = additional_context.get("final_payment_terms",
        "Payment due within 30 days" if target_language_code == "en" else "Paiement dû sous 30 jours")
    doc_ctx["notes"] = additional_context.get("invoice_notes", "")

    # Tax details from additional_context or defaults
    doc_ctx["tax_label"] = additional_context.get("tax_label", "VAT" if target_language_code == "en" else "TVA")
    doc_ctx["tax_rate_percentage"] = float(additional_context.get("tax_rate_percentage", 20.0)) # Default 20%
    doc_ctx["discount_rate_percentage"] = float(additional_context.get("discount_rate_percentage", 0.0))


    db_session = None
    try:
        db_session = additional_context.get("db_session") or get_db_session()

        # --- Invoice Number ---
        # Pass db_session to get_next_invoice_number if it's part of a larger transaction managed by the caller
        # If get_next_invoice_number manages its own session, conn=None or conn=db_session might not matter as much
        # but for consistency and potential transaction control, pass it.
        doc_ctx["invoice_number"] = additional_context.get("invoice_number") or get_next_invoice_number(conn=db_session)


        # --- Seller Data (largely reused from proforma) ---
        seller_ctx = context["seller"]
        seller_company_data = get_company_by_id(db_session, company_id) if company_id else None
        if seller_company_data:
            seller_ctx["id"] = seller_company_data.id
            seller_ctx["company_name"] = seller_company_data.name or "N/A"
            seller_ctx["email"] = seller_company_data.email or "N/A"
            seller_ctx["phone"] = seller_company_data.phone or "N/A"
            seller_ctx["website"] = seller_company_data.website or "N/A"

            raw_address = seller_company_data.address or ""
            payment_info = _parse_json_field(seller_company_data.payment_info)
            other_info_json = _parse_json_field(seller_company_data.other_info)

            # Bank details are crucial for final invoice
            seller_ctx["bank_name"] = payment_info.get("bank_name", additional_context.get("seller_bank_name", "N/A"))
            seller_ctx["bank_account_holder_name"] = payment_info.get("account_holder_name", seller_ctx["company_name"])
            seller_ctx["bank_iban"] = payment_info.get("iban", additional_context.get("seller_bank_iban", "N/A"))
            seller_ctx["bank_swift_bic"] = payment_info.get("swift_bic", additional_context.get("seller_bank_swift_bic", "N/A"))
            # seller_ctx["bank_account_number"] = payment_info.get("account_number", "N/A") # IBAN is usually preferred
            # seller_ctx["bank_address"] = payment_info.get("bank_address", "N/A")


            seller_ctx["vat_id"] = other_info_json.get("vat_id", additional_context.get("seller_vat_id", "N/A"))
            # seller_ctx["registration_number"] = other_info_json.get("registration_number", "N/A")

            seller_ctx["address_line1"] = raw_address
            seller_ctx["city"] = additional_context.get("seller_city", other_info_json.get("city", "N/A"))
            seller_ctx["postal_code"] = additional_context.get("seller_postal_code", other_info_json.get("postal_code", "N/A"))
            seller_ctx["country"] = additional_context.get("seller_country", other_info_json.get("country", "N/A"))
            seller_ctx["address"] = _format_address_parts(seller_ctx["address_line1"], seller_ctx["city"], seller_ctx["postal_code"], seller_ctx["country"])
            seller_ctx["city_zip_country"] = _format_address_parts(None, seller_ctx["city"], seller_ctx["postal_code"], seller_ctx["country"])


            logo_filename = seller_company_data.logo_filename or additional_context.get("seller_logo_filename")
            if logo_filename:
                 # Ensure APP_ROOT_DIR_CONTEXT is correctly defined for your app structure
                seller_ctx["logo_path"] = os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, logo_filename)
            else:
                seller_ctx["logo_path"] = None
        else: # Fallbacks
            for k in ["company_name", "email", "phone", "website", "bank_name", "bank_account_holder_name", "bank_iban", "bank_swift_bic", "vat_id", "address_line1", "city", "postal_code", "country", "address", "logo_path", "city_zip_country"]:
                seller_ctx[k] = additional_context.get(f"seller_{k}", "N/A")

        # --- Client Data (largely reused) ---
        client_ctx = context["client"]
        client_data = get_client_by_id(db_session, client_id) if client_id else None
        if client_data:
            client_ctx["id"] = client_data.id
            client_ctx["company_name"] = client_data.company_name or "N/A"
            client_ctx["representative_name"] = client_data.client_name or "N/A" # Fallback representative

            client_dist_info_json = _parse_json_field(client_data.distributor_specific_info)
            client_ctx["vat_id"] = client_dist_info_json.get("vat_id", additional_context.get("client_vat_id", "N/A"))

            primary_contacts = get_contacts_for_client(db_session, client_id, is_primary=True)
            primary_contact = primary_contacts[0] if primary_contacts else None

            if primary_contact:
                client_ctx["representative_name"] = f"{primary_contact.first_name or ''} {primary_contact.last_name or ''}".strip() or client_ctx["representative_name"]
                client_ctx["address_line1"] = primary_contact.address_streetAddress or "N/A"
                client_ctx["city"] = primary_contact.address_city or (get_city_by_id(db_session, client_data.city_id).name if client_data.city_id else "N/A")
                client_ctx["postal_code"] = primary_contact.address_postalCode or "N/A"
                client_ctx["country"] = primary_contact.address_country or (get_country_by_id(db_session, client_data.country_id).name if client_data.country_id else "N/A")
            else:
                client_ctx["address_line1"] = additional_context.get("client_address_line1", "N/A")
                client_ctx["city"] = (get_city_by_id(db_session, client_data.city_id).name if client_data.city_id else None) or additional_context.get("client_city", "N/A")
                client_ctx["postal_code"] = additional_context.get("client_postal_code", "N/A")
                client_ctx["country"] = (get_country_by_id(db_session, client_data.country_id).name if client_data.country_id else None) or additional_context.get("client_country", "N/A")

            client_ctx["address"] = _format_address_parts(client_ctx["address_line1"], client_ctx["city"], client_ctx["postal_code"], client_ctx["country"])
            client_ctx["city_zip_country"] = _format_address_parts(None, client_ctx["city"], client_ctx["postal_code"], client_ctx["country"])
        else:
             for k in ["company_name", "representative_name", "address_line1", "city", "postal_code", "country", "address", "vat_id", "city_zip_country"]:
                client_ctx[k] = additional_context.get(f"client_{k}", "N/A")

        # --- Project Data (largely reused) ---
        project_ctx = context["project"]
        if project_id:
            project_data = get_project_by_id(db_session, project_id)
            if project_data:
                project_ctx["id"] = project_data.id
                project_ctx["name"] = project_data.name or "N/A"
            else: project_ctx["name"] = "Project Not Found"
        else: project_ctx["name"] = additional_context.get("project_name","N/A")


        # --- Products / Line Items ---
        products_list_for_doc = []
        subtotal_amount_calculated = 0.0

        # Line items for a final invoice should ideally come from `additional_context`
        # to reflect agreed-upon quantities and prices from an order or quote.
        line_items_source = additional_context.get('line_items', [])

        if line_items_source:
            all_product_ids_from_items = [item["product_id"] for item in line_items_source if "product_id" in item]
            product_details_batch = _get_batch_products_and_equivalents(db_session, all_product_ids_from_items, target_language_code)

            for item_data in line_items_source:
                p_id = item_data.get("product_id")
                original_product_details = product_details_batch.get(p_id)
                if not original_product_details:
                    # Product details not found, use provided item_data or skip
                    product_name_for_doc = item_data.get("name", "Unknown Product")
                    product_description_for_doc = item_data.get("description", "")
                    language_match = False # Cannot determine without original details
                    unit_of_measure = "N/A"
                else:
                    product_name_for_doc = original_product_details["original_name"]
                    product_description_for_doc = original_product_details["original_description"]
                    language_match = (original_product_details["original_language_code"] == target_language_code)
                    unit_of_measure = original_product_details["unit_of_measure"]
                    if not language_match and original_product_details["equivalent_name"]:
                        product_name_for_doc = original_product_details["equivalent_name"]
                        product_description_for_doc = original_product_details["equivalent_description"]
                        language_match = True

                quantity = float(item_data.get("quantity", 0))
                # Critical: unit_price for final invoice should be from item_data if provided
                unit_price = float(item_data.get("unit_price", original_product_details.get("base_unit_price", 0) if original_product_details else 0))

                total_price = quantity * unit_price
                subtotal_amount_calculated += total_price

                product_entry = {
                    "id": p_id, "name": product_name_for_doc, "description": product_description_for_doc,
                    "quantity": quantity,
                    "unit_price_raw": unit_price,
                    "unit_price_formatted": format_currency(unit_price, doc_ctx["currency_symbol"]),
                    "total_price_raw": total_price,
                    "total_price_formatted": format_currency(total_price, doc_ctx["currency_symbol"]),
                    "unit_of_measure": unit_of_measure, "language_match": language_match,
                }
                products_list_for_doc.append(product_entry)
        else:
            logging.warning("No 'line_items' provided in additional_context for final invoice. Product list will be empty.")
            # Optionally, could fall back to ClientProjectProducts like proforma, but this is less typical for final invoices.

        context["products"] = products_list_for_doc

        # --- Totals ---
        doc_ctx["subtotal_amount_raw"] = subtotal_amount_calculated
        doc_ctx["subtotal_amount_formatted"] = format_currency(subtotal_amount_calculated, doc_ctx["currency_symbol"])

        discount_amount = (doc_ctx["discount_rate_percentage"] / 100.0) * subtotal_amount_calculated
        doc_ctx["discount_amount_raw"] = discount_amount # Store raw value for template logic
        doc_ctx["discount_amount_formatted"] = format_currency(discount_amount, doc_ctx["currency_symbol"])

        amount_after_discount = subtotal_amount_calculated - discount_amount
        doc_ctx["amount_after_discount_raw"] = amount_after_discount # For tax calculation base

        tax_amount = (doc_ctx["tax_rate_percentage"] / 100.0) * amount_after_discount
        doc_ctx["tax_amount_raw"] = tax_amount
        doc_ctx["tax_amount_formatted"] = format_currency(tax_amount, doc_ctx["currency_symbol"])

        grand_total_amount = amount_after_discount + tax_amount
        doc_ctx["grand_total_amount_raw"] = grand_total_amount
        doc_ctx["grand_total_amount_formatted"] = format_currency(grand_total_amount, doc_ctx["currency_symbol"])
        doc_ctx["grand_total_amount_words"] = additional_context.get("grand_total_amount_words", "N/A") # Placeholder

    except Exception as e:
        logging.error(f"Error in get_final_invoice_context_data: {e}", exc_info=True)
        # Populate with N/A to prevent crashes in template rendering (similar to proforma)
        for section_key in ["doc", "client", "seller", "project"]:
            if not context[section_key]: # if section is empty due to early error
                context[section_key] = {k: "Error - See Logs" for k in ["name", "id", "address"]}
        doc_ctx.setdefault("currency_symbol", "$")
        doc_ctx.setdefault("invoice_number", "ERROR-GEN")
        # ... (add more critical fallbacks for doc_ctx if needed)
    finally:
        # Session management: if this function created the session, it should close it.
        # Assuming session is managed by caller or a context manager via get_db_session()
        if db_session and not additional_context.get("db_session"):
            # This check is problematic if get_db_session() returns a new session each time
            # and is not a context manager. The caller of this function should manage the session.
            # For now, let's assume the caller handles session closing.
            pass

    # --- Final Placeholder Mapping (Flat dictionary for simple template engines) ---
    # This can be useful but for Handlebars/Jinja2, direct context access (e.g. {{doc.invoice_number}}) is common.
    # For consistency with proforma and potential simpler template engines, we can populate placeholders.

    # Document details
    context["placeholders"]["doc.invoice_title"] = doc_ctx.get("invoice_title", "INVOICE")
    context["placeholders"]["doc.invoice_number"] = doc_ctx.get("invoice_number", "N/A")
    context["placeholders"]["doc.issue_date"] = doc_ctx.get("issue_date", "N/A")
    context["placeholders"]["doc.due_date"] = doc_ctx.get("due_date", "N/A")
    context["placeholders"]["doc.payment_terms"] = doc_ctx.get("payment_terms", "N/A")
    context["placeholders"]["doc.notes"] = doc_ctx.get("notes", "")
    context["placeholders"]["doc.currency_symbol"] = doc_ctx.get("currency_symbol", "€")

    # Seller details
    context["placeholders"]["seller.company_name"] = seller_ctx.get("company_name", "N/A")
    context["placeholders"]["seller.address_line1"] = seller_ctx.get("address_line1", "N/A")
    context["placeholders"]["seller.city_zip_country"] = seller_ctx.get("city_zip_country", "N/A")
    context["placeholders"]["seller.phone"] = seller_ctx.get("phone", "N/A")
    context["placeholders"]["seller.email"] = seller_ctx.get("email", "N/A")
    context["placeholders"]["seller.website"] = seller_ctx.get("website", "N/A")
    context["placeholders"]["seller.vat_id"] = seller_ctx.get("vat_id", "N/A")
    context["placeholders"]["seller.logo_path"] = seller_ctx.get("logo_path")
    context["placeholders"]["seller.bank_name"] = seller_ctx.get("bank_name", "N/A")
    context["placeholders"]["seller.bank_account_holder_name"] = seller_ctx.get("bank_account_holder_name", "N/A")
    context["placeholders"]["seller.bank_iban"] = seller_ctx.get("bank_iban", "N/A")
    context["placeholders"]["seller.bank_swift_bic"] = seller_ctx.get("bank_swift_bic", "N/A")

    # Client details
    context["placeholders"]["client.company_name"] = client_ctx.get("company_name", "N/A")
    context["placeholders"]["client.representative_name"] = client_ctx.get("representative_name", "N/A")
    context["placeholders"]["client.address_line1"] = client_ctx.get("address_line1", "N/A")
    context["placeholders"]["client.city_zip_country"] = client_ctx.get("city_zip_country", "N/A")
    context["placeholders"]["client.vat_id"] = client_ctx.get("vat_id", "N/A")

    # Project details
    context["placeholders"]["project.name"] = project_ctx.get("name", "N/A")

    # Totals and Tax
    context["placeholders"]["doc.subtotal_amount_formatted"] = doc_ctx.get("subtotal_amount_formatted", "N/A")
    context["placeholders"]["doc.discount_rate_percentage"] = str(doc_ctx.get("discount_rate_percentage", "0.0"))
    context["placeholders"]["doc.discount_amount_raw"] = doc_ctx.get("discount_amount_raw", 0.0) # For conditional display
    context["placeholders"]["doc.discount_amount_formatted"] = doc_ctx.get("discount_amount_formatted", "N/A")
    context["placeholders"]["doc.tax_label"] = doc_ctx.get("tax_label", "VAT")
    context["placeholders"]["doc.tax_rate_percentage"] = str(doc_ctx.get("tax_rate_percentage", "0.0"))
    context["placeholders"]["doc.tax_amount_formatted"] = doc_ctx.get("tax_amount_formatted", "N/A")
    context["placeholders"]["doc.grand_total_amount_formatted"] = doc_ctx.get("grand_total_amount_formatted", "N/A")
    context["placeholders"]["doc.grand_total_amount_words"] = doc_ctx.get("grand_total_amount_words", "N/A")


    # Update main context sections for direct access if templates use e.g. {{doc.invoice_number}}
    context["doc"].update(doc_ctx)
    context["seller"].update(seller_ctx)
    context["client"].update(client_ctx)
    context["project"].update(project_ctx)

    # It's useful to return the full context dict which has nested structure
    # and also the flat placeholders dict if needed by a specific template engine.
    # For Handlebars/Jinja2, the nested context is usually preferred.
    # The template examples given use dot notation (e.g. {{doc.invoice_number}}),
    # so the nested context structure is what they'd use.
    # The `context["placeholders"]` can be removed if not used by the template engine.

    return context
