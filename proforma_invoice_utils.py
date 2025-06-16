import sqlite3 # Standard library, typically not used directly with SQLAlchemy
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
import json
import os
import logging
from typing import Optional, List, Dict, Any, Union

# Attempt to import ProformaInvoice model for type hinting
try:
    from api.models import ProformaInvoice
except ImportError:
    logging.warning("Could not import ProformaInvoice from api.models. Type hinting will use Any.")
    ProformaInvoice = Any # Fallback type

# Attempt to import from db module
try:
    from db import (
        get_db_session,
        get_company_by_id as db_get_company_by_id,
        get_personnel_for_company as db_get_personnel_for_company,
        get_client_by_id as db_get_client_by_id,
        get_country_by_id as db_get_country_by_id,
        get_city_by_id as db_get_city_by_id,
        get_contacts_for_client as db_get_contacts_for_client,
        get_project_by_id as db_get_project_by_id,
        get_product_by_id as db_get_product_by_id, # Renamed to avoid conflict if a local mock is used
        get_products_for_client_or_project as db_get_products_for_client_or_project,
        get_client_document_notes as db_get_client_document_notes,
    )
    # For _get_batch_products_and_equivalents, it's complex.
    # If it's in db.py and meant to be shared, it should be importable.
    # from db import _get_batch_products_and_equivalents
    from db.cruds.application_settings_crud import get_next_invoice_number # For final invoice numbers
except ImportError as e:
    logging.warning(f"Could not import all dependencies from db or cruds: {e}. Using placeholder functions. Full functionality requires db.py and cruds to be correctly structured and accessible.")
    # Define placeholder functions if db.py or its functions are not found

    def get_db_session(): raise NotImplementedError("get_db_session not imported/defined")
    def db_get_company_by_id(session, company_id): return None
    def db_get_personnel_for_company(session, company_id): return []
    def db_get_client_by_id(session, client_id): return None
    def db_get_country_by_id(session, country_id): return None
    def db_get_city_by_id(session, city_id): return None
    def db_get_contacts_for_client(session, client_id, is_primary=None): return []
    def db_get_project_by_id(session, project_id): return None
    # Mock Product needs attributes like id, name, description, language_code, base_unit_price etc.
    class MockProduct:
        def __init__(self, id, name, desc, lang, price, unit, weight=None, dims=None):
            self.id = id; self.name = name; self.description = desc; self.language_code = lang
            self.base_unit_price = price; self.unit_of_measure = unit
            self.product_weight_kg = weight; self.product_dimensions_cm = dims
    def db_get_product_by_id(session, product_id): return MockProduct(id=product_id, name=f"Mock Product {product_id}", desc="Mock Desc", lang="en", price=10.0, unit="pcs")
    def db_get_products_for_client_or_project(session, client_id, project_id=None): return []
    def db_get_client_document_notes(session, client_id, document_type, language_code): return "N/A"


# --- Constants ---
APP_ROOT_DIR_CONTEXT = os.path.dirname(os.path.abspath(__file__))
LOGO_SUBDIR_CONTEXT = "assets/logos"
CURRENCY_SYMBOLS = {
    "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
    # Add more as needed
}

# --- Helper Functions ---
# Ensure these functions are robust enough for various inputs (None, etc.)
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
def _get_batch_products_and_equivalents(db_session, product_ids: List[str], target_language_code: str) -> Dict[str, Dict[str, Any]]:
    """
    Fetches product details and their equivalents based on target language.
    Real implementation would query Products and ProductEquivalents tables/models.
    """
    products_data: Dict[str, Dict[str, Any]] = {}
    if not product_ids:
        return products_data

    for pid_str in product_ids:
        # Using db_get_product_by_id which uses the SQLAlchemy session (or mock)
        product = db_get_product_by_id(db_session, pid_str) # Assumes pid_str is the correct type for lookup
        if product and hasattr(product, 'id'): # Check if a valid product object was returned
            products_data[str(product.id)] = { # Ensure key is string
                "id": str(product.id),
                "original_name": getattr(product, 'name', 'N/A'), # Using getattr for safety on mock/real objects
                "original_description": getattr(product, 'description', 'N/A'),
                "original_language_code": getattr(product, 'language_code', 'N/A'),
                "base_unit_price": getattr(product, 'base_unit_price', 0.0),
                "unit_of_measure": getattr(product, 'unit_of_measure', 'N/A'),
                "product_weight_kg": getattr(product, 'product_weight_kg', None),
                "product_dimensions_cm": getattr(product, 'product_dimensions_cm', None),
                "equivalent_name": None, # Placeholder for translation logic
                "equivalent_description": None,
                "equivalent_language_code": None,
            }
            # Simple mock translation logic (replace with actual DB query for equivalents)
            current_product_data = products_data[str(product.id)]
            if target_language_code != current_product_data["original_language_code"] and target_language_code == 'fr':
                current_product_data["equivalent_name"] = f"{current_product_data['original_name']} (FR)"
                current_product_data["equivalent_description"] = f"{current_product_data['original_description']} (Description Française)"
                current_product_data["equivalent_language_code"] = "fr"
        else:
            logging.warning(f"Product with ID {pid_str} not found or is invalid.")
            products_data[pid_str] = None # Explicitly mark as not found / error
    return products_data


def get_proforma_invoice_context_data(
    client_id_arg: Optional[str] = None,
    company_id_arg: Optional[str] = None,
    target_language_code: str = "fr",
    project_id_arg: Optional[str] = None,
    proforma_instance: Optional[ProformaInvoice] = None, # Type hint with actual ProformaInvoice model
    linked_product_ids_for_doc: Optional[List[str]] = None, # Not directly used if proforma_instance is primary
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:

    client_id = client_id_arg
    company_id = company_id_arg
    project_id = project_id_arg

    if proforma_instance:
        logging.info(f"Using ProformaInvoice instance {proforma_instance.id} for context data.")
        client_id = proforma_instance.client_id
        company_id = proforma_instance.company_id
        project_id = proforma_instance.project_id
        # target_language_code could also be on proforma_instance, e.g.
        # target_language_code = getattr(proforma_instance, 'language_code', target_language_code)

    if additional_context is None:
        additional_context = {}

    context: Dict[str, Any] = {
        "doc": {}, "client": {}, "seller": {}, "project": {},
        "products": [], "lang": {}, "additional": additional_context,
        "placeholders": {}
    }

    context["lang"]["target_language_code"] = target_language_code
    doc_ctx = context["doc"]

    # --- Populate Document Info (doc_ctx) ---
    # Priority: proforma_instance -> additional_context -> defaults
    if proforma_instance:
        doc_ctx["proforma_id"] = proforma_instance.proforma_invoice_number
        doc_ctx["payment_terms"] = proforma_instance.payment_terms
        doc_ctx["delivery_terms"] = proforma_instance.delivery_terms
        doc_ctx["incoterms"] = proforma_instance.incoterms
        doc_ctx["named_place_of_delivery"] = proforma_instance.named_place_of_delivery
        doc_ctx["currency_symbol"] = CURRENCY_SYMBOLS.get(str(proforma_instance.currency).upper(), str(proforma_instance.currency))
        doc_ctx["proforma_notes"] = proforma_instance.notes
        # Financials directly from instance
        doc_ctx["subtotal_amount_raw"] = float(proforma_instance.subtotal_amount)
        doc_ctx["discount_amount_raw"] = float(proforma_instance.discount_amount or 0.0)
        doc_ctx["vat_amount_raw"] = float(proforma_instance.vat_amount)
        doc_ctx["grand_total_amount_raw"] = float(proforma_instance.grand_total_amount)
        # Dates
        doc_ctx["current_date"] = proforma_instance.created_date.strftime('%Y-%m-%d') if proforma_instance.created_date else datetime.now(timezone.utc).strftime('%Y-%m-%d')
        doc_ctx["sent_date"] = proforma_instance.sent_date.strftime('%Y-%m-%d') if proforma_instance.sent_date else None
    else:
        # Fallback to additional_context or defaults if no proforma_instance
        doc_ctx["proforma_id"] = additional_context.get("proforma_id", f"PF-{uuid.uuid4().hex[:8].upper()}")
        doc_ctx["payment_terms"] = additional_context.get("payment_terms", "Paiement anticipé")
        doc_ctx["delivery_terms"] = additional_context.get("delivery_terms", "Selon accord")
        doc_ctx["incoterms"] = additional_context.get("incoterms", "EXW")
        doc_ctx["named_place_of_delivery"] = additional_context.get("named_place_of_delivery", "Lieu du vendeur")
        doc_ctx["currency_symbol"] = additional_context.get("currency_symbol", "€")
        doc_ctx["proforma_notes"] = additional_context.get("notes", "")
        doc_ctx["current_date"] = additional_context.get("current_date", datetime.now(timezone.utc).strftime('%Y-%m-%d'))
        doc_ctx["sent_date"] = additional_context.get("sent_date")


    # VAT and Discount rates often come from additional_context during creation/regeneration
    doc_ctx["vat_rate_percentage"] = float(additional_context.get("vat_rate_percentage", 20.0))
    doc_ctx["discount_rate_percentage"] = float(additional_context.get("discount_rate_percentage", 0.0))
    doc_ctx["current_year"] = str(datetime.now(timezone.utc).year)


    db_session = None
    try:
        db_session = additional_context.get("db_session") or get_db_session()

        # --- Seller Data ---
        seller_ctx = context["seller"]
        seller_company_data: Optional[Any] = None # Using Any for mocked DB objects
        if proforma_instance and hasattr(proforma_instance, 'company') and proforma_instance.company:
            seller_company_data = proforma_instance.company
            logging.info(f"Using seller company from proforma_instance: {seller_company_data.id if hasattr(seller_company_data, 'id') else 'N/A'}")
        elif company_id:
            seller_company_data = db_get_company_by_id(db_session, company_id)
            logging.info(f"Fetched seller company by ID {company_id}: {'Found' if seller_company_data else 'Not Found'}")

        if seller_company_data:
            seller_ctx["id"] = getattr(seller_company_data, 'id', company_id)
            seller_ctx["company_name"] = getattr(seller_company_data, 'company_name', getattr(seller_company_data, 'name', "N/A")) # Adapt field name
            seller_ctx["email"] = getattr(seller_company_data, 'email', "N/A")
            seller_ctx["phone"] = getattr(seller_company_data, 'phone', "N/A")
            seller_ctx["website"] = getattr(seller_company_data, 'website', "N/A")

            raw_address = getattr(seller_company_data, 'address', "")
            payment_info = _parse_json_field(getattr(seller_company_data, 'payment_info', "{}"))
            other_info_raw = getattr(seller_company_data, 'other_info', "")
            other_info_json = _parse_json_field(other_info_raw)
            other_info_kv = _parse_key_value_string(other_info_raw if isinstance(other_info_raw, str) else "")


            seller_ctx["bank_name"] = payment_info.get("bank_name", additional_context.get("seller_bank_name", "N/A"))
            seller_ctx["bank_account_number"] = payment_info.get("account_number", additional_context.get("seller_bank_account_number", "N/A"))
            seller_ctx["bank_swift_bic"] = payment_info.get("swift_bic", additional_context.get("seller_bank_swift_bic", "N/A"))
            seller_ctx["bank_address"] = payment_info.get("bank_address", additional_context.get("seller_bank_address", "N/A"))
            seller_ctx["bank_account_holder_name"] = payment_info.get("account_holder_name", seller_ctx["company_name"])
            seller_ctx["bank_iban"] = payment_info.get("iban", additional_context.get("seller_bank_iban", seller_ctx["bank_account_number"]))

            seller_ctx["vat_id"] = other_info_json.get("vat_id", other_info_kv.get("vat", other_info_kv.get("vat_id", additional_context.get("seller_vat_id", "N/A"))))
            seller_ctx["registration_number"] = other_info_json.get("registration_number", other_info_kv.get("reg", other_info_kv.get("registration_number", additional_context.get("seller_registration_number", "N/A"))))

            seller_ctx["address_line1"] = raw_address
            # Assume city, postal_code, country might be part of 'address' or need separate fields/parsing
            seller_ctx["city"] = payment_info.get("city", additional_context.get("seller_city", "")) # Example: if stored in payment_info
            seller_ctx["postal_code"] = payment_info.get("postal_code", additional_context.get("seller_postal_code", ""))
            seller_ctx["country"] = payment_info.get("country", additional_context.get("seller_country", ""))
            seller_ctx["address"] = _format_address_parts(seller_ctx["address_line1"], seller_ctx["city"], seller_ctx["postal_code"], seller_ctx["country"])
            seller_ctx["city_zip_country"] = _format_address_parts(None, seller_ctx["city"], seller_ctx["postal_code"], seller_ctx["country"])

            seller_personnel = db_get_personnel_for_company(db_session, seller_ctx["id"])
            seller_rep = seller_personnel[0] if seller_personnel and isinstance(seller_personnel, list) and seller_personnel[0] else {}
            seller_ctx["representative_name"] = f"{seller_rep.get('first_name','')} {seller_rep.get('last_name','')}".strip() or "N/A"

            logo_filename = getattr(seller_company_data, 'logo_filename', getattr(seller_company_data, 'logo_path', None)) or additional_context.get("seller_logo_filename")
            if logo_filename and isinstance(logo_filename, str) and not logo_filename.startswith("http"): # if it's a filename not a full URL
                seller_ctx["logo_path"] = os.path.join(APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT, os.path.basename(logo_filename))
            elif logo_filename and isinstance(logo_filename, str): # if it's a full path or URL
                seller_ctx["logo_path"] = logo_filename
            else:
                seller_ctx["logo_path"] = None
        else:
            logging.warning(f"Seller company data not found for ID {company_id}. Using fallbacks.")
            for k_seller in ["company_name", "email", "phone", "website", "bank_name", "bank_account_number", "bank_swift_bic", "bank_address", "bank_account_holder_name", "bank_iban", "vat_id", "registration_number", "address_line1", "city", "postal_code", "country", "address", "representative_name", "logo_path", "city_zip_country"]:
                seller_ctx[k_seller] = additional_context.get(f"seller_{k_seller}", "N/A")

        # --- Client Data ---
        client_ctx = context["client"]
        client_data: Optional[Any] = None
        if proforma_instance and hasattr(proforma_instance, 'client') and proforma_instance.client:
            client_data = proforma_instance.client
            logging.info(f"Using client from proforma_instance: {client_data.id if hasattr(client_data, 'id') else 'N/A'}")
        elif client_id:
            client_data = db_get_client_by_id(db_session, client_id)
            logging.info(f"Fetched client by ID {client_id}: {'Found' if client_data else 'Not Found'}")

        if client_data:
            client_ctx["id"] = getattr(client_data, 'id', client_id)
            client_ctx["company_name"] = getattr(client_data, 'company_name', "N/A")
            client_ctx["contact_person_name_default"] = getattr(client_data, 'client_name', "N/A")

            client_notes_raw = getattr(client_data, 'notes', "")
            client_notes_json = _parse_json_field(client_notes_raw)
            client_notes_kv = _parse_key_value_string(client_notes_raw if isinstance(client_notes_raw, str) else "")

            client_dist_info_raw = getattr(client_data, 'distributor_specific_info', "")
            client_dist_info_json = _parse_json_field(client_dist_info_raw)
            client_dist_info_kv = _parse_key_value_string(client_dist_info_raw if isinstance(client_dist_info_raw, str) else "")

            client_ctx["vat_id"] = client_notes_json.get("vat_id", client_notes_kv.get("vat", client_dist_info_json.get("vat_id", client_dist_info_kv.get("vat", additional_context.get("client_vat_id", "N/A")))))
            client_ctx["registration_number"] = client_notes_json.get("registration_number", client_notes_kv.get("reg", client_dist_info_json.get("registration_number", client_dist_info_kv.get("reg", additional_context.get("client_registration_number", "N/A")))))

            primary_contacts = db_get_contacts_for_client(db_session, client_ctx["id"], is_primary=True)
            primary_contact = primary_contacts[0] if primary_contacts and isinstance(primary_contacts, list) and primary_contacts[0] else None

            if primary_contact:
                client_ctx["representative_name"] = f"{getattr(primary_contact, 'first_name','')} {getattr(primary_contact, 'last_name','')}".strip() or client_ctx["contact_person_name_default"]
                client_ctx["email"] = getattr(primary_contact, 'email', getattr(client_data, 'email', "N/A"))
                client_ctx["phone"] = getattr(primary_contact, 'phone', getattr(client_data, 'phone', "N/A"))
                client_ctx["address_line1"] = getattr(primary_contact, 'address_streetAddress', "N/A")
                client_city_obj = db_get_city_by_id(db_session, getattr(client_data, 'city_id', None)) if getattr(client_data, 'city_id', None) else None
                client_ctx["city"] = getattr(primary_contact, 'address_city', getattr(client_city_obj, 'name', "N/A"))
                client_ctx["postal_code"] = getattr(primary_contact, 'address_postalCode', "N/A")
                client_country_obj = db_get_country_by_id(db_session, getattr(client_data, 'country_id', None)) if getattr(client_data, 'country_id', None) else None
                client_ctx["country"] = getattr(primary_contact, 'address_country', getattr(client_country_obj, 'name', "N/A"))
            else:
                client_ctx["representative_name"] = client_ctx["contact_person_name_default"]
                client_ctx["email"] = getattr(client_data, 'email', additional_context.get("client_email", "N/A"))
                client_ctx["phone"] = getattr(client_data, 'phone', additional_context.get("client_phone", "N/A"))
                client_ctx["address_line1"] = getattr(client_data, 'address_line1', additional_context.get("client_address_line1", "N/A")) # Assuming client_data might have address_line1
                client_city_obj_fallback = db_get_city_by_id(db_session, getattr(client_data, 'city_id', None)) if getattr(client_data, 'city_id', None) else None
                client_ctx["city"] = getattr(client_city_obj_fallback, 'name', additional_context.get("client_city", "N/A"))
                client_ctx["postal_code"] = additional_context.get("client_postal_code", "N/A") # Assuming client_data might not have postal_code
                client_country_obj_fallback = db_get_country_by_id(db_session, getattr(client_data, 'country_id', None)) if getattr(client_data, 'country_id', None) else None
                client_ctx["country"] = getattr(client_country_obj_fallback, 'name', additional_context.get("client_country", "N/A"))

            client_ctx["address"] = _format_address_parts(client_ctx["address_line1"], client_ctx["city"], client_ctx["postal_code"], client_ctx["country"])
            client_ctx["city_zip_country"] = _format_address_parts(None, client_ctx["city"], client_ctx["postal_code"], client_ctx["country"])
        else:
            logging.warning(f"Client data not found for ID {client_id}. Using fallbacks.")
            for k_client in ["company_name", "email", "phone", "vat_id", "registration_number", "address_line1", "city", "postal_code", "country", "address", "representative_name", "city_zip_country"]:
                client_ctx[k_client] = additional_context.get(f"client_{k_client}", "N/A")

        # --- Project Data ---
        project_ctx = context["project"]
        project_data: Optional[Any] = None
        if proforma_instance and hasattr(proforma_instance, 'project') and proforma_instance.project:
            project_data = proforma_instance.project
            logging.info(f"Using project from proforma_instance: {project_data.id if hasattr(project_data, 'id') else 'N/A'}")
        elif project_id:
            project_data = db_get_project_by_id(db_session, project_id)
            logging.info(f"Fetched project by ID {project_id}: {'Found' if project_data else 'Not Found'}")

        if project_data:
            project_ctx["id"] = getattr(project_data, 'id', project_id)
            project_ctx["name"] = getattr(project_data, 'name', "N/A") # SQLAlchemy model might use 'name'
            project_ctx["description"] = getattr(project_data, 'description', "N/A")
            project_ctx["identifier"] = getattr(project_data, 'project_identifier', "N/A") # SQLAlchemy model might use 'project_identifier'
        else: # Fallbacks
            project_ctx["id"] = project_id or "N/A"
            project_ctx["name"] = additional_context.get("project_name", "N/A")
            project_ctx["description"] = additional_context.get("project_description", "N/A")
            project_ctx["identifier"] = additional_context.get("project_identifier", (getattr(client_data, 'project_identifier', "N/A") if client_data else "N/A"))


        # --- Products Data ---
        products_list_for_doc = []
        products_table_html_rows_list = []
        # If proforma_instance is not used for totals, this will be calculated from items below
        subtotal_amount_calculated_from_items = 0.0
        product_items_to_process: List[Dict[str, Any]] = []
        product_ids_for_batch_fetch: List[str] = []

        if proforma_instance and hasattr(proforma_instance, 'items') and proforma_instance.items:
            logging.info(f"Processing {len(proforma_instance.items)} items from proforma_instance.")
            for item_instance in proforma_instance.items:
                product_items_to_process.append({
                    "product_id": getattr(item_instance, 'product_id', None),
                    "quantity": float(getattr(item_instance, 'quantity', 0)),
                    "unit_price": float(getattr(item_instance, 'unit_price', 0.0)),
                    "description": getattr(item_instance, 'description', "N/A"),
                    "total_price": float(getattr(item_instance, 'total_price', 0.0)),
                })
                if getattr(item_instance, 'product_id', None):
                    product_ids_for_batch_fetch.append(str(getattr(item_instance, 'product_id')))

        elif additional_context.get('lite_selected_products'):
            logging.info("Processing items from additional_context['lite_selected_products'].")
            # This list should conform to: [{"product_id": str, "quantity": float, "unit_price_override": float, "description": Optional[str]}, ...]
            for item_data_ac in additional_context['lite_selected_products']:
                pid_ac = item_data_ac.get("product_id")
                if pid_ac: product_ids_for_batch_fetch.append(str(pid_ac))
                # Description and unit_price will be resolved after batch fetching product details
                product_items_to_process.append({
                    "product_id": pid_ac,
                    "quantity": float(item_data_ac.get("quantity", 1)),
                    "unit_price_override": float(item_data_ac.get("unit_price_override")) if item_data_ac.get("unit_price_override") is not None else None,
                    "description_override": item_data_ac.get("description"), # Explicit description from context
                    # total_price will be calculated
                })
        # elif linked_product_ids_for_doc: ... (existing logic, can be adapted similarly if needed)

        product_details_batch = {}
        if product_ids_for_batch_fetch:
            product_details_batch = _get_batch_products_and_equivalents(db_session, list(set(product_ids_for_batch_fetch)), target_language_code)

        for item_data_to_render in product_items_to_process:
            p_id_render = item_data_to_render.get("product_id")
            original_product_details = product_details_batch.get(str(p_id_render)) if p_id_render else None

            # Determine effective unit price and description
            effective_unit_price = item_data_to_render.get("unit_price") # From ProformaInvoiceItem
            if effective_unit_price is None: # Not from ProformaInvoiceItem (e.g. from lite_selected_products)
                effective_unit_price = item_data_to_render.get("unit_price_override")
                if effective_unit_price is None and original_product_details:
                    effective_unit_price = original_product_details.get("base_unit_price", 0.0)
                elif effective_unit_price is None:
                    effective_unit_price = 0.0

            description_for_render = item_data_to_render.get("description") # From ProformaInvoiceItem
            if description_for_render is None: # Not from ProformaInvoiceItem
                description_for_render = item_data_to_render.get("description_override")
                if description_for_render is None and original_product_details:
                    description_for_render = original_product_details.get("original_name", "Custom Item")
                elif description_for_render is None:
                    description_for_render = "Custom Item"

            quantity_render = item_data_to_render.get("quantity", 0.0)
            total_price_render = item_data_to_render.get("total_price") # From ProformaInvoiceItem
            if total_price_render is None: # Calculate if not from ProformaInvoiceItem
                total_price_render = quantity_render * effective_unit_price

            if not proforma_instance: # If not using totals from instance, sum here
                subtotal_amount_calculated_from_items += total_price_render

            # Language handling for name/description if needed (using original_product_details)
            product_name_display = description_for_render # Default to the determined description
            product_secondary_desc_display = "" # Could be original translated description
            language_match = True # Assume true if desc is taken from item/override

            if original_product_details:
                # If stored description is same as original name, and translation exists, use translation for display name
                if description_for_render == original_product_details.get("original_name") and \
                   target_language_code != original_product_details.get("original_language_code") and \
                   original_product_details.get("equivalent_name"):
                    product_name_display = original_product_details["equivalent_name"]
                    # product_secondary_desc_display = original_product_details.get("equivalent_description", "")
                # If description_for_render is short, maybe append translated original description
                # elif len(description_for_render.split()) < 5 and original_product_details.get("equivalent_description"):
                #    product_secondary_desc_display = original_product_details.get("equivalent_description")


            product_entry = {
                "id": str(p_id_render) if p_id_render else uuid.uuid4().hex[:8],
                "name": product_name_display,
                "description": product_secondary_desc_display, # Use if you want a sub-description
                "quantity": quantity_render,
                "unit_price_raw": float(effective_unit_price),
                "unit_price_formatted": format_currency(float(effective_unit_price), doc_ctx["currency_symbol"]),
                "total_price_raw": float(total_price_render),
                "total_price_formatted": format_currency(float(total_price_render), doc_ctx["currency_symbol"]),
                "unit_of_measure": original_product_details.get("unit_of_measure", "N/A") if original_product_details else "N/A",
                "language_match": language_match, # This needs more robust logic based on source of name/desc
                "original_name": original_product_details.get("original_name", "") if original_product_details else "",
                "original_description": original_product_details.get("original_description", "") if original_product_details else "",
                "weight_kg": original_product_details.get("product_weight_kg") if original_product_details else None,
                "dimensions_cm": original_product_details.get("product_dimensions_cm") if original_product_details else None,
            }
            products_list_for_doc.append(product_entry)
            products_table_html_rows_list.append(
                f"<tr><td>{len(products_list_for_doc)}</td>"
                f"<td><strong>{product_entry['name']}</strong><br><small>{product_entry['description'] or ''}</small></td>"
                f"<td class='number'>{product_entry['quantity']}</td>"
                f"<td class='number'>{product_entry['unit_price_formatted']}</td>"
                f"<td class='number'>{product_entry['total_price_formatted']}</td></tr>"
            )
        context["products"] = products_list_for_doc
        doc_ctx["products_table_rows"] = "".join(products_table_html_rows_list)

        # --- Totals Finalization ---
        if not proforma_instance: # If totals were not sourced from proforma_instance
            doc_ctx["subtotal_amount_raw"] = subtotal_amount_calculated_from_items
            # Recalculate discount, vat, grand_total based on subtotal_amount_calculated_from_items
            # and discount_rate_percentage, vat_rate_percentage from additional_context or defaults
            current_discount_rate = doc_ctx.get("discount_rate_percentage", 0.0)
            doc_ctx["discount_amount_raw"] = (current_discount_rate / 100.0) * doc_ctx["subtotal_amount_raw"]

            amount_after_discount = doc_ctx["subtotal_amount_raw"] - doc_ctx["discount_amount_raw"]
            current_vat_rate = doc_ctx.get("vat_rate_percentage", 20.0) # Default VAT if not set
            doc_ctx["vat_amount_raw"] = (current_vat_rate / 100.0) * amount_after_discount
            doc_ctx["grand_total_amount_raw"] = amount_after_discount + doc_ctx["vat_amount_raw"]

        # Format all raw amounts (whether from instance or calculated)
        doc_ctx["subtotal_amount_formatted"] = format_currency(doc_ctx["subtotal_amount_raw"], doc_ctx["currency_symbol"])
        doc_ctx["discount_amount_formatted"] = format_currency(doc_ctx["discount_amount_raw"], doc_ctx["currency_symbol"])
        doc_ctx["vat_amount_formatted"] = format_currency(doc_ctx["vat_amount_raw"], doc_ctx["currency_symbol"])
        doc_ctx["grand_total_amount_formatted"] = format_currency(doc_ctx["grand_total_amount_raw"], doc_ctx["currency_symbol"])
        doc_ctx["grand_total_amount_words"] = additional_context.get("grand_total_amount_words", "N/A") # Placeholder

        # --- Client Specific Notes ---
        doc_notes_type = additional_context.get("client_document_notes_type", "Proforma") # e.g. Proforma, Invoice
        if client_id: # Only fetch notes if client_id is available
            notes_text = db_get_client_document_notes(db_session, client_id, doc_notes_type, target_language_code)
            doc_ctx["client_specific_footer_notes"] = notes_text.replace('\n', '<br>') if notes_text and isinstance(notes_text, str) else ""
        else:
            doc_ctx["client_specific_footer_notes"] = ""


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
    # This flattens the context for easier use in simple template engines
    context["placeholders"]["PROFORMA_ID"] = doc_ctx.get("proforma_id", "N/A")
    context["placeholders"]["DATE"] = doc_ctx.get("current_date", "N/A")
    context["placeholders"]["SENT_DATE"] = doc_ctx.get("sent_date", "N/A")
    context["placeholders"]["PAYMENT_TERMS"] = doc_ctx.get("payment_terms", "N/A")
    context["placeholders"]["DELIVERY_TERMS"] = doc_ctx.get("delivery_terms", "N/A")
    context["placeholders"]["INCOTERMS"] = doc_ctx.get("incoterms", "N/A")
    context["placeholders"]["NAMED_PLACE_OF_DELIVERY"] = doc_ctx.get("named_place_of_delivery", "N/A")
    context["placeholders"]["DOCUMENT_CURRENCY"] = doc_ctx.get("currency_symbol", "N/A")
    context["placeholders"]["PROFORMA_NOTES"] = doc_ctx.get("proforma_notes", "")


    # Seller details (ensure seller_ctx is populated before this)
    seller_ctx_final = context.get("seller", {})
    context["placeholders"]["SELLER_COMPANY_NAME"] = seller_ctx_final.get("company_name", "N/A")
    context["placeholders"]["SELLER_ADDRESS_LINE1"] = seller_ctx.get("address_line1", "N/A")
    context["placeholders"]["SELLER_CITY"] = seller_ctx.get("city", "")
    context["placeholders"]["SELLER_POSTAL_CODE"] = seller_ctx_final.get("postal_code", "")
    context["placeholders"]["SELLER_COUNTRY"] = seller_ctx_final.get("country", "")
    context["placeholders"]["SELLER_FULL_ADDRESS"] = seller_ctx_final.get("address", "N/A")
    context["placeholders"]["SELLER_CITY_ZIP_COUNTRY"] = seller_ctx_final.get("city_zip_country", "N/A")
    context["placeholders"]["SELLER_COMPANY_PHONE"] = seller_ctx_final.get("phone", "N/A")
    context["placeholders"]["SELLER_COMPANY_EMAIL"] = seller_ctx_final.get("email", "N/A")
    context["placeholders"]["SELLER_VAT_ID"] = seller_ctx_final.get("vat_id", "N/A")
    context["placeholders"]["SELLER_REGISTRATION_NUMBER"] = seller_ctx_final.get("registration_number", "N/A")
    context["placeholders"]["SELLER_COMPANY_LOGO_PATH"] = seller_ctx_final.get("logo_path")
    context["placeholders"]["SELLER_BANK_NAME"] = seller_ctx_final.get("bank_name", "N/A")
    context["placeholders"]["SELLER_BANK_ACCOUNT_HOLDER_NAME"] = seller_ctx_final.get("bank_account_holder_name", "N/A")
    context["placeholders"]["SELLER_BANK_ACCOUNT_NUMBER"] = seller_ctx_final.get("bank_account_number", "N/A")
    context["placeholders"]["SELLER_BANK_IBAN"] = seller_ctx_final.get("bank_iban", "N/A")
    context["placeholders"]["SELLER_BANK_SWIFT_BIC"] = seller_ctx_final.get("bank_swift_bic", "N/A")
    context["placeholders"]["SELLER_BANK_ADDRESS"] = seller_ctx_final.get("bank_address", "N/A")

    client_ctx_final = context.get("client", {})
    context["placeholders"]["BUYER_COMPANY_NAME"] = client_ctx_final.get("company_name", "N/A")
    context["placeholders"]["BUYER_REPRESENTATIVE_NAME"] = client_ctx_final.get("representative_name", "N/A")
    context["placeholders"]["BUYER_ADDRESS_LINE1"] = client_ctx_final.get("address_line1", "N/A")
    context["placeholders"]["BUYER_CITY"] = client_ctx_final.get("city", "")
    context["placeholders"]["BUYER_POSTAL_CODE"] = client_ctx_final.get("postal_code", "")
    context["placeholders"]["BUYER_COUNTRY"] = client_ctx_final.get("country", "")
    context["placeholders"]["BUYER_FULL_ADDRESS"] = client_ctx_final.get("address", "N/A")
    context["placeholders"]["BUYER_CITY_ZIP_COUNTRY"] = client_ctx_final.get("city_zip_country", "N/A")
    context["placeholders"]["BUYER_PHONE"] = client_ctx_final.get("phone", "N/A")
    context["placeholders"]["BUYER_EMAIL"] = client_ctx_final.get("email", "N/A")
    context["placeholders"]["BUYER_VAT_NUMBER"] = client_ctx_final.get("vat_id", "N/A")
    context["placeholders"]["BUYER_COMPANY_REGISTRATION_NUMBER"] = client_ctx_final.get("registration_number", "N/A")

    project_ctx_final = context.get("project", {})
    context["placeholders"]["PROJECT_ID"] = project_ctx_final.get("identifier", "N/A")
    context["placeholders"]["PROJECT_NAME"] = project_ctx_final.get("name", "N/A")

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
