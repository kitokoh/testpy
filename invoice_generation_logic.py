import os
import logging
from datetime import datetime

# Assuming proforma_invoice_utils.py is in the same directory or accessible in PYTHONPATH
from proforma_invoice_utils import get_final_invoice_context_data
# Assuming html_to_pdf_util.py is in the same directory or accessible
from html_to_pdf_util import render_html_template, convert_html_to_pdf, WeasyPrintError

# Adjust import path based on actual project structure
# If this file is in, e.g., an 'invoicing' or 'logic' subdirectory:
try:
    from ..app_config import TEMPLATES_DIR
    from ..db.cruds import clients_crud # Though not directly used in this func as per spec
except (ImportError, ValueError):
    # Fallback if running script directly from its folder or structure is different
    # This assumes app_config.py and db/cruds/ are siblings of this file's parent directory
    # For robust imports, ensure your project's root is in PYTHONPATH
    # or use relative imports correctly based on your structure.
    logging.warning("Could not perform relative imports for TEMPLATES_DIR/clients_crud. Attempting direct. This might fail if not in PYTHONPATH.")
    from app_config import TEMPLATES_DIR
    from db.cruds import clients_crud


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_final_invoice_pdf(
    client_id: str,
    company_id: str,
    target_language_code: str,
    line_items: list, # Expected: [{'product_id': X, 'quantity': Y, 'unit_price': Z, 'name' (opt), 'description' (opt)}, ...]
    project_id: str = None,
    additional_context_overrides: dict = None
) -> tuple[bytes | None, str | None, dict | None]:
    """
    Generates a final invoice PDF as bytes and suggests a filename.

    Args:
        client_id: The client's unique identifier.
        company_id: The seller company's unique identifier.
        target_language_code: Language code for the template (e.g., "en", "fr").
        line_items: A list of dictionaries, each representing a product/service line item.
                    Each dict should contain at least 'product_id', 'quantity', and 'unit_price'.
                    'name' and 'description' can be included to override catalog values if needed.
        project_id: Optional project identifier to associate with the invoice.
        additional_context_overrides: Dictionary to override or add values to the document context
                                      (e.g., issue_date, due_date, tax_rate_percentage, payment_terms).

    Returns:
        A tuple containing:
        - pdf_bytes (bytes | None): The generated PDF as bytes, or None on failure.
        - suggested_filename (str | None): A suggested filename for the PDF, or None on failure.
        - full_context (dict | None): The context data used for generation, for debugging or record-keeping.
    """
    logging.info(f"Starting final invoice PDF generation for client_id: {client_id}, company_id: {company_id}, lang: {target_language_code}")

    prepared_additional_context = {'line_items': line_items if line_items else []}
    if additional_context_overrides:
        prepared_additional_context.update(additional_context_overrides)

    try:
        # Assuming get_db_session is handled within get_final_invoice_context_data or via its own mechanism
        # If a shared session is needed, it should be passed via prepared_additional_context
        full_context = get_final_invoice_context_data(
            client_id=client_id,
            company_id=company_id,
            target_language_code=target_language_code,
            project_id=project_id,
            additional_context=prepared_additional_context
        )
    except Exception as e:
        logging.error(f"Failed to generate invoice context data: {e}", exc_info=True)
        return None, None, None

    if not full_context or not full_context.get("doc"):
        logging.error("Context generation returned empty or invalid data.")
        return None, None, full_context # Return context for debugging

    # Determine Template Path
    template_filename = "final_invoice_template.html"
    template_path = os.path.join(TEMPLATES_DIR, target_language_code, template_filename)

    if not os.path.exists(template_path):
        logging.error(f"Invoice template not found at: {template_path}")
        # Fallback to English template if target language template is missing?
        # For now, strict failure.
        # fallback_template_path = os.path.join(TEMPLATES_DIR, "en", template_filename)
        # if os.path.exists(fallback_template_path):
        #     logging.warning(f"Using fallback English template as {target_language_code} not found.")
        #     template_path = fallback_template_path
        # else:
        #     logging.error(f"Fallback English template also not found at: {fallback_template_path}")
        return None, None, full_context

    # Read and Render HTML Template
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()

        # The context itself (with nested dicts) is passed for Handlebars-like engines
        rendered_html = render_html_template(template_content, full_context)
        logging.info(f"Successfully rendered HTML template: {template_path}")
    except Exception as e:
        logging.error(f"Failed to read or render HTML template {template_path}: {e}", exc_info=True)
        return None, None, full_context

    # Convert HTML to PDF
    # base_url should point to a directory from which assets (like CSS, images referenced relatively in HTML) can be found.
    # Since the logo path in context is absolute, this base_url is mainly for other potential relative assets in the template.
    # Using the directory of the template itself is a common choice.
    pdf_base_url = os.path.dirname(template_path)
    try:
        pdf_bytes = convert_html_to_pdf(rendered_html, base_url=pdf_base_url)
        if not pdf_bytes: # convert_html_to_pdf might return None on failure
             raise WeasyPrintError("convert_html_to_pdf returned None, indicating an unspecified error.")
        logging.info("Successfully converted HTML to PDF bytes.")
    except WeasyPrintError as e:
        logging.error(f"PDF generation failed (WeasyPrintError): {e}", exc_info=True)
        return None, None, full_context
    except Exception as e:
        logging.error(f"An unexpected error occurred during PDF conversion: {e}", exc_info=True)
        return None, None, full_context

    # Generate Suggested Filename
    doc_info = full_context.get("doc", {})
    client_info = full_context.get("client", {})

    invoice_number_cleaned = doc_info.get("invoice_number", "INV_UNKNOWN").replace("/", "-").replace("\\", "-")

    client_name_for_file = "UnknownClient"
    if client_info.get("company_name") and client_info["company_name"] != "N/A":
        client_name_for_file = client_info["company_name"]
    elif client_info.get("representative_name") and client_info["representative_name"] != "N/A":
        client_name_for_file = client_info["representative_name"]
    elif client_id:
        client_name_for_file = client_id

    client_name_cleaned = "".join(c if c.isalnum() or c in ['-', '_'] else '_' for c in client_name_for_file.replace(" ", "_"))

    current_date_str = datetime.now().strftime("%Y%m%d")
    suggested_filename = f"Invoice_{invoice_number_cleaned}_{client_name_cleaned}_{current_date_str}.pdf"
    logging.info(f"Suggested filename: {suggested_filename}")

    return pdf_bytes, suggested_filename, full_context


if __name__ == '__main__':
    # This is a basic test stub.
    # To run this effectively, you need:
    # 1. `app_config.py` at the project root defining `TEMPLATES_DIR`.
    # 2. `proforma_invoice_utils.py` and `html_to_pdf_util.py` in the same directory or PYTHONPATH.
    # 3. Database schema initialized and accessible via CRUDs.
    # 4. Test data in the database (clients, companies, products).
    # 5. HTML templates in `TEMPLATES_DIR/<lang_code>/final_invoice_template.html`.

    print("Invoice Generation Logic Module")

    # Example: (This will likely fail without the full application context and DB setup)
    # dummy_client_id = "client_dummy_123"
    # dummy_company_id = "company_seller_abc"
    # dummy_lang = "en"
    # dummy_line_items = [
    #     {"product_id": 1, "quantity": 2, "unit_price": 50.0, "name": "Test Product A", "description": "Description for A"},
    #     {"product_id": 2, "quantity": 1, "unit_price": 120.0, "name": "Test Product B", "description": "Description for B"}
    # ]
    # dummy_additional_overrides = {
    #     "issue_date": "2024-03-15",
    #     "due_date": "2024-04-14",
    #     "tax_rate_percentage": 10.0, # Example: 10% tax
    #     "discount_rate_percentage": 5.0, # Example: 5% discount
    #     "invoice_notes": "This is a test invoice generated from standalone execution."
    # }

    # print(f"Attempting to generate PDF for client {dummy_client_id}...")
    # pdf_content, filename, context_used = generate_final_invoice_pdf(
    #     client_id=dummy_client_id,
    #     company_id=dummy_company_id,
    #     target_language_code=dummy_lang,
    #     line_items=dummy_line_items,
    #     additional_context_overrides=dummy_additional_overrides
    # )

    # if pdf_content:
    #     test_output_dir = "test_output"
    #     os.makedirs(test_output_dir, exist_ok=True)
    #     output_path = os.path.join(test_output_dir, filename if filename else "test_invoice.pdf")
    #     try:
    #         with open(output_path, 'wb') as f:
    #             f.write(pdf_content)
    #         print(f"Successfully generated test PDF: {output_path}")
    #     except Exception as e:
    #         print(f"Error saving test PDF: {e}")
    # else:
    #     print("Failed to generate test PDF.")
    #     if context_used:
    #         print("Context used (or error state):")
    #         # import json # Not great for complex objects, pprint might be better
    #         # print(json.dumps(context_used, indent=2, default=str)) # Default str for non-serializable
    #         import pprint
    #         pprint.pprint(context_used)

    logging.info("Please run tests or integrate into the main application to use generate_final_invoice_pdf.")
```
