# Placeholder for data fetching and management (e.g., API interactions)

import typing
from typing import Optional, List, Dict

# Expected API: GET /api/mobile/context/ids
def get_client_and_company_ids_from_api() -> Dict[str, str]:
    """
    Fetches mock client and company IDs.
    Simulates an API call.
    """
    print("API CALL: get_client_and_company_ids_from_api()")
    return {'client_id': 'mock_client_123', 'company_id': 'mock_company_abc'}

# Expected API: POST /api/mobile/context/document_data (Payload: {client_id, company_id, ...})
def get_document_context_data_from_api(
    client_id: str,
    company_id: str,
    target_language_code: str,
    selected_products_with_qty: list,
    additional_doc_context: Optional[dict] = None
) -> Optional[dict]:
    """
    Fetches mock document context data.
    Simulates an API call.
    """
    print(f"API CALL: get_document_context_data_from_api() with params: client_id={client_id}, company_id={company_id}, lang={target_language_code}, products_count={len(selected_products_with_qty)}, additional_context_keys={list(additional_doc_context.keys()) if additional_doc_context else []}")
    return {
        'client': {'name': 'Mock Client', 'client_id': client_id},
        'company': {'name': 'Mock Company', 'company_id': company_id},
        'products_data': selected_products_with_qty,
        'language': target_language_code,
        'doc_specific_country_selection': additional_doc_context.get('doc_specific_country_selection') if additional_doc_context else None,
        # Add other necessary mock context data based on what templates might expect
    }

# Expected API: GET /api/mobile/products?lang={language_code}&search={name_pattern}
def get_all_products_for_selection_from_api(language_code: str, name_pattern: Optional[str] = None) -> List[Dict]:
    """
    Fetches a list of mock products.
    Simulates an API call.
    """
    print(f"API CALL: get_all_products_for_selection_from_api() with lang={language_code}, search='{name_pattern or ''}'")
    products = [
        {'product_id': 'prod_1', 'product_name': 'Mock Product 1', 'price': 100, 'description': 'Description for product 1'},
        {'product_id': 'prod_2', 'product_name': 'Mock Product 2', 'price': 200, 'description': 'Description for product 2'},
        {'product_id': 'prod_3', 'product_name': 'Another Mock Product', 'price': 150, 'description': 'Description for another product'}
    ]
    if name_pattern:
        return [p for p in products if name_pattern.lower() in p['product_name'].lower()]
    return products

# Expected API: GET /api/mobile/countries
def get_all_countries_from_api() -> List[Dict]:
    """
    Fetches a list of mock countries.
    Simulates an API call.
    """
    print("API CALL: get_all_countries_from_api()")
    return [
        {'country_id': 'C1', 'country_name': 'MockCountry1', 'currency': 'MCK1'},
        {'country_id': 'C2', 'country_name': 'MockCountry2', 'currency': 'MCK2'}
    ]

# Expected API: GET /api/mobile/templates?category={category_name}
def get_document_templates_from_api(category_name: Optional[str] = None) -> List[Dict]:
    """
    Fetches a list of mock document templates.
    Simulates an API call.
    """
    print(f"API CALL: get_document_templates_from_api() with category='{category_name or ''}'")
    return [
        {'template_id': 'tpl_1', 'template_name': 'Mock Proforma Invoice Template', 'language_code': 'en', 'category': 'invoice', 'base_file_name': 'proforma_invoice_en.html'},
        {'template_id': 'tpl_2', 'template_name': 'Mock Sales Contract Template', 'language_code': 'en', 'category': 'contract', 'base_file_name': 'sales_contract_en.html'},
        {'template_id': 'tpl_fr_1', 'template_name': 'Facture Proforma Maquette', 'language_code': 'fr', 'category': 'invoice', 'base_file_name': 'proforma_invoice_fr.html'}
    ]

# Expected API: GET /api/mobile/templates/{template_id}/content
def get_template_content_from_api(template_id: str) -> Optional[str]:
    """
    Fetches mock HTML content for a given template ID.
    Simulates an API call.
    """
    print(f"API CALL: get_template_content_from_api() for template_id: {template_id}")
    # Example content, can be expanded or made more dynamic if needed for testing
    if template_id == "tpl_1":
      return f"<h1>Mock Proforma Invoice Content for {template_id}</h1><p>Client: {{ client.name }}</p><p>Company: {{ company.name }}</p>"
    elif template_id == "tpl_2":
      return f"<h1>Mock Sales Contract Content for {template_id}</h1><p>This contract is between {{ company.name }} and {{ client.name }}.</p>"
    elif template_id == "tpl_fr_1":
      return f"<h1>Facture Proforma Maquette pour {template_id}</h1><p>Client: {{ client.name }}</p><p>Société: {{ company.name }}</p>"
    return f"<html><body>Default Mock Template Content for {template_id}: {{ client.name }}</body></html>"

def get_mobile_temp_dir() -> str:
    """
    Returns a temporary directory path suitable for mobile platforms.
    Placeholder - actual implementation would depend on the mobile OS.
    """
    # For now, using a sub-directory in the current working directory.
    # On a real mobile device, this would use OS-specific APIs.
    temp_dir_name = "mobile_temp_docs"
    if not os.path.exists(temp_dir_name):
        try:
            os.makedirs(temp_dir_name)
        except OSError as e:
            print(f"Could not create temp directory {temp_dir_name}: {e}")
            return "." # Fallback to current directory
    return temp_dir_name

def get_mobile_templates_dir() -> str:
    """
    Returns a templates directory path for mobile.
    Placeholder - In a real mobile app, templates might be bundled or pre-fetched.
    """
    # This is a placeholder. On mobile, templates might not be in a "directory"
    # in the same way as a desktop app. They might be bundled assets or fetched on demand.
    print("INFO: Using placeholder for mobile templates directory.")
    return "mock_mobile_templates" # Or perhaps an object that knows how to fetch them.

# Need to import os for get_mobile_temp_dir
import os

# Expected API: POST /api/mobile/pdf/convert (Payload: {html_content, base_url})
def convert_html_to_pdf_api(html_content: str, base_url: Optional[str] = None) -> Optional[bytes]:
    """
    Converts HTML content to PDF using a mock API call.
    """
    print(f"API CALL: convert_html_to_pdf_api() with base_url='{base_url}'")
    # Simple mock PDF content. A real PDF is a complex binary format.
    # This is just a placeholder to simulate receiving bytes.
    pdf_bytes = b"%PDF-1.4\n%mock PDF content for first 100 chars of html: " + html_content[:100].encode('utf-8') + b"\n%EOF"
    return pdf_bytes

# Expected API: GET /api/mobile/languages
def get_languages_from_api() -> List[Dict]:
    """
    Fetches a list of mock languages.
    Simulates an API call.
    """
    print("API CALL: get_languages_from_api()")
    return [
        {'code': 'en', 'name': 'English'},
        {'code': 'fr', 'name': 'French'},
        {'code': 'es', 'name': 'Spanish'}
    ]
