# db_context_extensions.py
from datetime import datetime

def format_currency_simple(amount, symbol="EUR"):
    if amount is None: return "N/A"
    return f"{symbol} {amount:.2f}"

def get_contacts_for_table(client_contacts, seller_personnel, client_company_name="N/A Client Company"):
    html_rows = ""
    # Simplified logic for now to ensure file creation
    html_rows += "<tr><td>Vendeur (Exemple)</td><td>Nom Vendeur</td><td>Role Vendeur</td><td>vendeur@example.com</td><td>+12345</td></tr>"
    if client_contacts:
        for contact in client_contacts:
            html_rows += f"<tr><td>Client</td><td>{contact.get('name', 'N/A')}</td><td>{contact.get('position', 'N/A')}</td><td>{contact.get('email', 'N/A')}</td><td>{contact.get('phone', 'N/A')}</td></tr>"
    if not html_rows:
        html_rows = '<tr><td colspan="5" style="text-align:center;">Aucun contact.</td></tr>'
    return html_rows

def get_dimensions_table_rows_html(dimensions_data):
    html_rows = ""
    if not dimensions_data:
        return '<tr><td colspan="4" style="text-align:center;">N/A</td></tr>'
    for dim in dimensions_data:
        html_rows += f"<tr><td>{dim.get('characteristic','N/A')}</td><td>{dim.get('value','N/A')}</td><td>{dim.get('unit','N/A')}</td><td>{dim.get('tolerance','N/A')}</td></tr>"
    return html_rows

def extend_document_context_with_new_template_data(context: dict, additional_context_from_main_db: dict, client_contacts_list: list, seller_personnel_list: list):
    if not context: context = {"doc": {}, "client": {}, "seller": {}, "project": {}, "products": [], "additional": {}}
    if not additional_context_from_main_db: additional_context_from_main_db = {}
    for key in ["doc", "client", "seller", "project", "products", "additional"]:
        if key not in context: context[key] = {}

    # Tech Spec Placeholders
    product_context_for_tech_spec = {}
    if context.get("products"): product_context_for_tech_spec = context["products"][0]

    context["doc"]["PRODUCT_NAME_TECH_SPEC"] = product_context_for_tech_spec.get("name", "N/A Produit")
    context["doc"]["PROJECT_ID_TECH_SPEC"] = context.get("project", {}).get("id", "N/A Projet")
    context["doc"]["DATE_TECH_SPEC"] = context.get("doc",{}).get("current_date", "N/A")
    context["doc"]["VERSION_TECH_SPEC"] = "1.0"
    context["doc"]["TECHNICAL_IMAGE_PATH_OR_EMBED"] = "path/to/default_image.png"
    context["doc"]["TECHNICAL_IMAGE_CAPTION"] = "Image du produit (par défaut)"
    simulated_dimensions = [{"characteristic": "Longeur", "value": "100", "unit": "cm", "tolerance": "1cm"}]
    context["doc"]["DIMENSIONS_TABLE_ROWS_TECH_SPEC"] = get_dimensions_table_rows_html(simulated_dimensions)
    context["doc"]["MATERIALS_GENERAL_OVERVIEW_TECH_SPEC"] = "Matériaux standards."
    context["doc"]["MATERIALS_CONDITIONS_DETAILED_LIST_TECH_SPEC"] = "<ul><li>Acier Inox</li></ul>"
    context["doc"]["PERFORMANCE_SPECS_TECH_SPEC"] = "Performance standard."
    context["doc"]["COMPLIANCE_STANDARDS_TECH_SPEC"] = "CE."
    context["doc"]["OPERATING_ENVIRONMENT_TECH_SPEC"] = "Intérieur."
    context["doc"]["MAINTENANCE_INFO_TECH_SPEC"] = "Standard."
    context["doc"]["NOTES_TECH_SPEC"] = "Aucune."

    # Contact Page Placeholders
    context["doc"]["PROJECT_NAME_CONTACT_PAGE"] = context.get("project", {}).get("name", "N/A Projet")
    context["doc"]["DATE_CONTACT_PAGE"] = context.get("doc",{}).get("current_date", "N/A")
    client_company_name_for_contact_page = context.get("client", {}).get("company_name", "N/A")
    context["doc"]["CONTACTS_TABLE_ROWS_CONTACT_PAGE"] = get_contacts_for_table(client_contacts_list, seller_personnel_list, client_company_name_for_contact_page)

    # General Fallbacks
    context["SELLER_LOGO_PATH"] = context.get("seller", {}).get("company_logo_path", "default_logo.png")
    context["SELLER_COMPANY_NAME"] = context.get("seller", {}).get("name", "Société Vendeuse")
    context["CLIENT_NAME"] = context.get("client", {}).get("contact_person_name", "Client")
    context["PROJECT_ID"] = context.get("project", {}).get("id", "PROJ-000")
    context["DATE"] = context.get("doc",{}).get("current_date", "2024-01-01")

    return context
