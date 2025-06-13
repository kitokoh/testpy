import os
import json
import datetime
import logging
from decimal import Decimal, ROUND_HALF_UP

# Assuming db.cruds and other necessary modules exist in the parent directory or are accessible.
# Adjust these imports based on the actual project structure.
from db.cruds import (
    get_company_by_id,
    get_client_by_id,
    get_product_by_id,
    get_products_for_client_or_project,
    get_contacts_for_client,
    get_country_by_id,
    get_city_by_id,
    get_project_by_id,
    get_client_document_notes,
    get_product_equivalencies_for_product, # Placeholder, might need to be products_crud.get_product_equivalents
    get_media_links_for_product, # Placeholder, might need to be products_crud.get_media_links_for_product
    get_personnel_for_company,
)
from db.utils import get_db_connection
# Assuming these config variables are correctly defined in your project.
# from db_config import APP_ROOT_DIR_CONTEXT, LOGO_SUBDIR_CONTEXT
# from config import MEDIA_FILES_BASE_PATH

# Dummy config values for now, replace with actual imports
APP_ROOT_DIR_CONTEXT = "/app" # Example, replace with actual context
LOGO_SUBDIR_CONTEXT = "logos" # Example, replace with actual context
MEDIA_FILES_BASE_PATH = "/app/media" # Example, replace with actual context


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_currency(amount, currency_symbol='€', decimal_places=2):
    """
    Formats a numerical amount as a currency string.
    Example: format_currency(Decimal('1234.567'), currency_symbol='$') == '$1,234.57'
    """
    if amount is None:
        return f"{currency_symbol}0.00" # Or handle as an error/None

    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except Exception:
            return f"{currency_symbol}0.00" # Or handle as an error/None

    # Round to specified decimal places
    quantizer = Decimal('0.1') ** decimal_places
    rounded_amount = amount.quantize(quantizer, ROUND_HALF_UP)

    # Format with comma as thousands separator and dot as decimal separator
    # Adjust formatting as per specific locale requirements if necessary
    parts = str(rounded_amount).split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else '0' * decimal_places

    # Add thousands separators
    integer_part_with_commas = ""
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            integer_part_with_commas = "," + integer_part_with_commas
        integer_part_with_commas = digit + integer_part_with_commas

    if not decimal_part: # Ensure decimal part has correct number of zeros if missing
        decimal_part = '0' * decimal_places
    else:
        decimal_part = decimal_part.ljust(decimal_places, '0')


    return f"{currency_symbol}{integer_part_with_commas}.{decimal_part}"


def get_document_context(
    client_id: int,
    company_id: int,
    language_code: str,
    project_id: int = None,
    document_type: str = None, # e.g., 'proforma_invoice', 'technical_sheet'
    additional_data: dict = None,
    db_conn=None
) -> dict:
    """
    Fetches and structures data for document generation.

    Args:
        client_id: ID of the client.
        company_id: ID of the seller company.
        language_code: Language code for translations (e.g., 'en', 'es').
        project_id: Optional ID of the project.
        document_type: Optional type of the document being generated.
        additional_data: Optional dictionary for overrides or extra information.
        db_conn: Optional existing database connection.

    Returns:
        A dictionary containing structured data for the document.
    """
    if additional_data is None:
        additional_data = {}

    context = {
        "doc": {},
        "client": {},
        "seller": {},
        "project": {},
        "products": [],
        "lang": {},
        "placeholders": {},
        "additional": additional_data,
    }

    conn = db_conn if db_conn else get_db_connection()

    try:
        # 1. Document Info (doc section)
        context["doc"]["current_date"] = datetime.date.today().strftime("%Y-%m-%d")
        context["doc"]["current_year"] = datetime.date.today().year
        context["doc"]["currency_symbol"] = additional_data.get("currency_symbol", "€")
        context["doc"]["vat_rate"] = Decimal(additional_data.get("vat_rate", "0.20")) # Example VAT
        context["doc"]["discount_rate"] = Decimal(additional_data.get("discount_rate", "0.00"))

        # 2. Language Info (lang section)
        # This can be expanded with actual translations for cover pages, etc.
        context["lang"]["code"] = language_code
        # Example: context["lang"]["cover_title"] = "Project Proposal" if language_code == 'en' else "Propuesta de Proyecto"

        # 3. Seller Information (seller section)
        seller_company = get_company_by_id(conn, company_id)
        if seller_company:
            context["seller"]["name"] = seller_company.get("name")
            context["seller"]["address_line1"] = seller_company.get("address_line1")
            context["seller"]["address_line2"] = seller_company.get("address_line2")
            context["seller"]["city"] = seller_company.get("city_name") # Assuming city_name is available
            context["seller"]["postal_code"] = seller_company.get("postal_code")
            context["seller"]["country"] = seller_company.get("country_name") # Assuming country_name is available
            context["seller"]["phone"] = seller_company.get("phone")
            context["seller"]["email"] = seller_company.get("email")
            context["seller"]["website"] = seller_company.get("website")
            context["seller"]["vat_id"] = seller_company.get("vat_id")

            logo_relative_path = seller_company.get("logo_path")
            if logo_relative_path:
                # Correctly join paths for the logo
                logo_abs_path = os.path.join(APP_ROOT_DIR_CONTEXT, logo_relative_path.lstrip('/'))
                if os.path.exists(logo_abs_path):
                    context["seller"]["logo_path"] = f"file://{logo_abs_path}"
                else:
                    context["seller"]["logo_path"] = None
                    logger.warning(f"Seller logo not found at: {logo_abs_path}")
            else:
                context["seller"]["logo_path"] = None

            # Seller representative (simplified - picks the first one or based on a flag)
            personnel_list = get_personnel_for_company(conn, company_id)
            if personnel_list:
                # Prioritize personnel marked as 'representative' or similar if such a field exists
                representative = next((p for p in personnel_list if p.get("is_representative")), personnel_list[0])
                context["seller"]["representative_name"] = representative.get("full_name")
                context["seller"]["representative_email"] = representative.get("email")
                context["seller"]["representative_phone"] = representative.get("phone")
        else:
            logger.error(f"Seller company with ID {company_id} not found.")

        # 4. Client Information (client section)
        client_data = get_client_by_id(conn, client_id)
        if client_data:
            context["client"]["id"] = client_data.get("id")
            context["client"]["name"] = client_data.get("name") # Individual client name
            context["client"]["company_name"] = client_data.get("company_name")
            context["client"]["address_line1"] = client_data.get("address_line1")
            context["client"]["address_line2"] = client_data.get("address_line2")
            context["client"]["postal_code"] = client_data.get("postal_code")
            context["client"]["vat_id"] = client_data.get("vat_id")

            client_city_id = client_data.get("city_id")
            if client_city_id:
                city = get_city_by_id(conn, client_city_id)
                context["client"]["city"] = city.get("name") if city else None

            client_country_id = client_data.get("country_id")
            if client_country_id:
                country = get_country_by_id(conn, client_country_id)
                context["client"]["country"] = country.get("name") if country else None

            primary_contact = None
            contacts = get_contacts_for_client(conn, client_id)
            if contacts:
                primary_contact = next((c for c in contacts if c.get("is_primary")), contacts[0])
                if primary_contact:
                    context["client"]["contact_name"] = primary_contact.get("name")
                    context["client"]["contact_email"] = primary_contact.get("email")
                    context["client"]["contact_phone"] = primary_contact.get("phone")
        else:
            logger.error(f"Client with ID {client_id} not found.")

        # 5. Project Information (project section)
        if project_id:
            project_data = get_project_by_id(conn, project_id)
            if project_data:
                context["project"]["id"] = project_data.get("id")
                context["project"]["name"] = project_data.get("name")
                context["project"]["identifier"] = project_data.get("identifier")
            else:
                logger.warning(f"Project with ID {project_id} not found.")
        elif "project_name" in additional_data or "project_identifier" in additional_data:
            context["project"]["name"] = additional_data.get("project_name")
            context["project"]["identifier"] = additional_data.get("project_identifier")
        elif client_data and client_data.get("default_project_identifier"): # Fallback to client's default project
             context["project"]["identifier"] = client_data.get("default_project_identifier")
             context["project"]["name"] = client_data.get("default_project_name") # if available


        # 6. Product Information (products section)
        product_ids_to_fetch = additional_data.get('lite_selected_products', []) # List of product IDs
        if not product_ids_to_fetch and 'linked_product_ids_for_doc' in additional_data:
             product_ids_to_fetch = additional_data.get('linked_product_ids_for_doc', [])

        products_raw = []
        if product_ids_to_fetch:
            for pid in product_ids_to_fetch:
                prod = get_product_by_id(conn, pid) # Assumes quantity is handled elsewhere or is 1
                if prod:
                    # Check if quantity is provided in additional_data, perhaps per product_id
                    quantity = additional_data.get("products_quantities", {}).get(pid, 1)
                    prod_with_quantity = {**prod, "quantity": quantity}
                    products_raw.append(prod_with_quantity)
        else:
            # Default: fetch all products linked to client or project
            products_raw = get_products_for_client_or_project(conn, client_id=client_id, project_id=project_id)
            # Ensure products_raw have a quantity, default to 1 if not present
            for prod in products_raw:
                if "quantity" not in prod:
                    prod["quantity"] = 1


        total_items_price = Decimal("0.0")
        for prod_data in products_raw:
            product_id = prod_data.get("id")
            if not product_id:
                logger.warning(f"Skipping product with missing ID: {prod_data}")
                continue

            # Base product details are already in prod_data if fetched by get_product_by_id
            # If get_products_for_client_or_project doesn't return full details, fetch them:
            # current_product_details = get_product_by_id(conn, product_id) or {}
            current_product_details = prod_data # Assuming prod_data has all base fields

            # Fetch product equivalents for the given language
            # This simulates products_crud.get_product_equivalents(product_id, language_code)
            # or the logic from _get_batch_products_and_equivalents
            equivalents = get_product_equivalencies_for_product(conn, product_id, language_code)

            translated_name = current_product_details.get("name") # Default to original name
            translated_description = current_product_details.get("description") # Default to original desc

            if equivalents: # Assuming equivalents is a list and we take the first one or best match
                # This logic might need refinement based on how equivalents are structured
                best_equivalent = equivalents[0] # Simplistic choice
                translated_name = best_equivalent.get("name", translated_name)
                translated_description = best_equivalent.get("description", translated_description)

            # Fetch media links
            # This simulates products_crud.get_media_links_for_product(product_id)
            media_links_raw = get_media_links_for_product(conn, product_id)
            media_links_processed = []
            if media_links_raw:
                for media_link in media_links_raw:
                    file_path = media_link.get("file_path")
                    if file_path:
                        # Ensure MEDIA_FILES_BASE_PATH is defined and correct
                        abs_media_path = os.path.join(MEDIA_FILES_BASE_PATH, file_path.lstrip('/'))
                        if os.path.exists(abs_media_path):
                             media_links_processed.append({
                                 "url": f"file://{abs_media_path}",
                                 "type": media_link.get("type", "image"), # e.g., image, datasheet
                                 "description": media_link.get("description")
                             })
                        else:
                            logger.warning(f"Media file not found: {abs_media_path} for product {product_id}")

            quantity = Decimal(str(prod_data.get("quantity", 1)))
            unit_price = Decimal(str(current_product_details.get("unit_price", "0.00")))
            item_total_price = quantity * unit_price

            context["products"].append({
                "id": product_id,
                "original_name": current_product_details.get("name"),
                "original_description": current_product_details.get("description"),
                "sku": current_product_details.get("sku"),
                "name": translated_name,
                "description": translated_description,
                "quantity": quantity,
                "unit_price": format_currency(unit_price, context["doc"]["currency_symbol"]),
                "total_price": format_currency(item_total_price, context["doc"]["currency_symbol"]),
                "unit_price_decimal": unit_price,
                "total_price_decimal": item_total_price,
                "media_links": media_links_processed,
                # Add other product fields as necessary
            })
            total_items_price += item_total_price

        # 7. Totals Calculation (doc section)
        subtotal = total_items_price
        discount_amount = subtotal * context["doc"]["discount_rate"]
        subtotal_after_discount = subtotal - discount_amount
        vat_amount = subtotal_after_discount * context["doc"]["vat_rate"]
        grand_total = subtotal_after_discount + vat_amount

        context["doc"]["subtotal_amount_raw"] = subtotal
        context["doc"]["discount_amount_raw"] = discount_amount
        context["doc"]["vat_amount_raw"] = vat_amount
        context["doc"]["grand_total_amount_raw"] = grand_total

        cs = context["doc"]["currency_symbol"]
        context["doc"]["subtotal_amount"] = format_currency(subtotal, cs)
        context["doc"]["discount_amount"] = format_currency(discount_amount, cs)
        context["doc"]["vat_amount"] = format_currency(vat_amount, cs)
        context["doc"]["grand_total_amount"] = format_currency(grand_total, cs)


        # 8. Client-Specific Notes (doc section)
        # Ensure document_type is passed if notes are type-specific
        doc_type_for_notes = additional_data.get("document_type_for_notes", document_type)
        if doc_type_for_notes and client_id and language_code:
            notes = get_client_document_notes(conn, client_id, doc_type_for_notes, language_code)
            context["doc"]["client_specific_notes"] = notes # Assuming notes is a list of strings or a single string
        else:
            context["doc"]["client_specific_notes"] = []


        # 9. Placeholders Dictionary (placeholders section)
        # Basic placeholders, can be expanded
        context["placeholders"]["BUYER_COMPANY_NAME"] = context["client"].get("company_name", context["client"].get("name"))
        context["placeholders"]["BUYER_CONTACT_NAME"] = context["client"].get("contact_name")
        context["placeholders"]["BUYER_ADDRESS_LINE1"] = context["client"].get("address_line1")
        context["placeholders"]["BUYER_CITY"] = context["client"].get("city")
        context["placeholders"]["BUYER_COUNTRY"] = context["client"].get("country")
        context["placeholders"]["SELLER_COMPANY_NAME"] = context["seller"].get("name")
        context["placeholders"]["SELLER_ADDRESS_LINE1"] = context["seller"].get("address_line1")
        context["placeholders"]["SELLER_CITY"] = context["seller"].get("city")
        context["placeholders"]["SELLER_COUNTRY"] = context["seller"].get("country")
        context["placeholders"]["SELLER_REPRESENTATIVE_NAME"] = context["seller"].get("representative_name")
        context["placeholders"]["SELLER_LOGO"] = context["seller"].get("logo_path")
        context["placeholders"]["PROJECT_NAME"] = context["project"].get("name")
        context["placeholders"]["PROJECT_IDENTIFIER"] = context["project"].get("identifier")
        context["placeholders"]["CURRENT_DATE"] = context["doc"]["current_date"]
        context["placeholders"]["GRAND_TOTAL_AMOUNT"] = context["doc"]["grand_total_amount"]
        context["placeholders"]["SUBTOTAL_AMOUNT"] = context["doc"]["subtotal_amount"]
        context["placeholders"]["CURRENCY_SYMBOL"] = context["doc"]["currency_symbol"]

        # Add all product details to placeholders, prefixed for lists
        # For simplicity, this example doesn't create complex list placeholders here.
        # Typically, templating engines handle lists of objects directly.

    except Exception as e:
        logger.error(f"Error building document context: {e}", exc_info=True)
        # Ensure a partial context is still returned to avoid breaking consumers
    finally:
        if db_conn is None and conn: # Only close if created within this function
            conn.close()

    return context

if __name__ == '__main__':
    # This is a placeholder for testing the function.
    # You would need a running database and actual data to test this properly.
    logger.info("Starting context builder test run...")

    # Example Usage (requires database setup and mock CRUD functions or a live DB)
    # Create a dummy connection or mock get_db_connection and CRUDs for local testing.

    # Mock db_connection and cruds for standalone testing if needed:
    class MockDbConnection:
        def cursor(self): return self
        def execute(self, query, params=None): return self
        def fetchone(self): return None
        def fetchall(self): return []
        def close(self): pass

    def mock_get_db_connection():
        return MockDbConnection()

    # Replace actual get_db_connection with mock for this test
    # global get_db_connection # If you need to reassign global, not usually recommended
    # original_get_db_conn = get_db_connection
    # get_db_connection = mock_get_db_connection

    # Mock CRUD functions (replace with more detailed mocks as needed)
    # For example:
    # def mock_get_company_by_id(conn, company_id):
    #     return {"id": company_id, "name": "Test Seller Inc.", "logo_path": "dummy_logo.png"}
    # global get_company_by_id
    # get_company_by_id = mock_get_company_by_id

    try:
        # Note: Without proper mocks for all DB calls, this will likely log errors.
        test_context = get_document_context(
            client_id=1,
            company_id=1,
            language_code='en',
            project_id=1,
            additional_data={
                "currency_symbol": "$",
                "vat_rate": "0.10",
                # "lite_selected_products": [101, 102],
                # "products_quantities": {101: 2, 102: 5}
            }
            # db_conn=mock_get_db_connection() # Pass mock connection
        )
        logger.info(f"Generated context (test run, likely with errors if DB not mocked):")
        # Using json.dumps for pretty printing, handling Decimal by converting to str
        # logger.info(json.dumps(test_context, indent=2, default=str))

    except Exception as e:
        logger.error(f"Error during test run: {e}", exc_info=True)
    finally:
        # Restore original functions if they were globally mocked
        # get_db_connection = original_get_db_conn
        logger.info("Context builder test run finished.")

    # To run this file directly for testing:
    # Ensure that the paths for db.cruds, db.utils, db_config, config are correct
    # or provide mock implementations for them.
    # Example:
    # PYTHONPATH=. python document_generator/context_builder.py (if run from project root)

```
