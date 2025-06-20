# -*- coding: utf-8 -*-
import sys
import os
import json
import logging
import logging.handlers
import shutil
import pandas as pd
from PyQt5.QtCore import QFile, QTextStream # QStandardPaths, QLocale, QLibraryInfo removed
# from PyQt5.QtGui import QFont # Removed as QFont is not used here
# Assuming db_manager and other necessary utils will be imported if functions using them are moved.
from config import DATABASE_NAME as CENTRAL_DATABASE_NAME # For DATABASE_NAME
from utils import load_config # save_config removed as it's not used here

# --- Global Constants and Configurations ---
if getattr(sys, 'frozen', False):
    APP_ROOT_DIR = sys._MEIPASS
else:
    APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_TEMPLATES_DIR = os.path.join(APP_ROOT_DIR, "templates") # Standardized subdir name
DEFAULT_CLIENTS_DIR = os.path.join(APP_ROOT_DIR, "clients")   # Standardized subdir name
LOGO_SUBDIR = "company_logos"

DATABASE_NAME = CENTRAL_DATABASE_NAME

# CONFIG loading logic
CONFIG = load_config(APP_ROOT_DIR, DEFAULT_TEMPLATES_DIR, DEFAULT_CLIENTS_DIR)

# Ensure directories exist after CONFIG is loaded
os.makedirs(CONFIG["templates_dir"], exist_ok=True)
os.makedirs(CONFIG["clients_dir"], exist_ok=True)
# These were in main.py's global scope after config loading, seem appropriate here.
os.makedirs(os.path.join(APP_ROOT_DIR, "translations"), exist_ok=True)
os.makedirs(os.path.join(APP_ROOT_DIR, LOGO_SUBDIR), exist_ok=True)

SPEC_TECH_TEMPLATE_NAME = "specification_technique_template.xlsx"
PROFORMA_TEMPLATE_NAME = "proforma_template.xlsx"
CONTRAT_VENTE_TEMPLATE_NAME = "contrat_vente_template.xlsx"
PACKING_LISTE_TEMPLATE_NAME = "packing_liste_template.xlsx"

# --- Utility Functions ---
def setup_logging():
    """Configures logging for the application."""
    log_file_name = "client_manager_app.log"
    log_format = "%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s"

    logging.basicConfig(level=logging.DEBUG, format=log_format, stream=sys.stderr)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file_name, maxBytes=1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(logging.Formatter(log_format))

    root_logger = logging.getLogger()
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) and h.baseFilename.endswith(log_file_name) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stderr for h in root_logger.handlers):
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and handler.stream in (sys.stdout, sys.stderr) and handler.formatter._fmt == logging.BASIC_FORMAT:
                root_logger.removeHandler(handler)
        root_logger.addHandler(console_handler)

    logging.info("Logging configured.")

def get_app_config():
    """Returns the global CONFIG object."""
    return CONFIG

def load_stylesheet_global(app):
    """Loads the global stylesheet."""
    # Assuming APP_ROOT_DIR is defined in this module (app_setup.py)
    # If style.qss is at the same level as main.py/app_setup.py, APP_ROOT_DIR is correct.
    # If app_setup.py is in a subdirectory, APP_ROOT_DIR might need adjustment for this function
    # or style.qss path needs to be relative to the project root.
    # For now, assuming app_setup.py is at the root.
    qss_file_path = os.path.join(APP_ROOT_DIR, "style.qss")

    if not os.path.exists(qss_file_path):
        logging.warning(f"Stylesheet file not found: {qss_file_path}. Creating a default one.")
        try:
            with open(qss_file_path, "w", encoding="utf-8") as f:
                f.write("/* Default empty stylesheet. Will be populated by the application or user. */")
            logging.info(f"Created an empty default stylesheet: {qss_file_path}")
        except IOError as e:
            logging.error(f"Error creating default stylesheet {qss_file_path}: {e}")
            return

    file = QFile(qss_file_path)
    if file.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(file)
        stylesheet = stream.readAll()
        app.setStyleSheet(stylesheet)
        logging.info(f"Stylesheet loaded successfully from {qss_file_path}")
        file.close()
    else:
        logging.error(f"Failed to open stylesheet file: {qss_file_path}, Error: {file.errorString()}")

# --- Default Template Initialization ---
def initialize_default_templates(config, app_root_dir):
    """
    Initializes default Excel, HTML, and email templates.
    config: The application's configuration dictionary.
    app_root_dir: The root directory of the application.
    """
    logging.info("Starting default template initialization...")

    # --- Default Excel Templates ---
    templates_root_dir = config["templates_dir"]
    all_supported_template_langs = ["fr", "en", "ar", "tr", "pt"]

    # Ensure "General" category exists for default templates
    # db_manager must be imported or passed as an argument if this function is to use it.
    # For now, assuming db_manager is imported in app_setup.py
    # general_category_id = db_manager.add_template_category("General", "General purpose templates") # DB seeding call removed
    # if general_category_id is None:
    #     logging.error("CRITICAL ERROR: Could not create or find the 'General' template category. Default Excel templates may not be added correctly to DB.")
    # Seeding of categories is now handled by db.seed_initial_data

    default_excel_templates_data = {
        SPEC_TECH_TEMPLATE_NAME: pd.DataFrame({'Section': ["Info Client", "Détails Tech"], 'Champ': ["Nom:", "Exigence:"], 'Valeur': ["{NOM_CLIENT}", ""]}),
        PROFORMA_TEMPLATE_NAME: pd.DataFrame({'Article': ["Produit A"], 'Qté': [1], 'PU': [10.0], 'Total': [10.0]}),
        CONTRAT_VENTE_TEMPLATE_NAME: pd.DataFrame({'Clause': ["Objet"], 'Description': ["Vente de ..."]}),
        PACKING_LISTE_TEMPLATE_NAME: pd.DataFrame({'Colis': [1], 'Contenu': ["Marchandise X"], 'Poids': [5.0]})
    }

    logging.info("Processing Excel templates...")
    for lang_code in all_supported_template_langs:
        lang_specific_dir = os.path.join(templates_root_dir, lang_code)
        os.makedirs(lang_specific_dir, exist_ok=True)
        for template_file_name, df_content in default_excel_templates_data.items():
            template_full_path = os.path.join(lang_specific_dir, template_file_name)
            created_file_on_disk = False
            if not os.path.exists(template_full_path):
                try:
                    df_content.to_excel(template_full_path, index=False)
                    logging.info(f"Created default Excel template file: {template_full_path}")
                    created_file_on_disk = True
                except Exception as e:
                    logging.error(f"Error creating Excel template file {template_file_name} for {lang_code}: {str(e)}")

            # DB registration for Excel templates removed. This is now handled by db.seed_initial_data if these templates are to be seeded.
            # The file creation part above is preserved.
            if created_file_on_disk:
                 logging.info(f"Excel template file '{template_file_name}' for {lang_code} ensured on disk.")
            else:
                 logging.info(f"Excel template file '{template_file_name}' for {lang_code} already exists on disk or failed to create.")


    # --- HTML Templates ---
    DEFAULT_HTML_TEMPLATES_METADATA = [
        {
            "base_file_name": "technical_specifications_template.html", "template_type": "HTML_TECH_SPECS",
            "display_name_fr": "Spécifications Techniques (HTML)", "description_fr": "Modèle HTML pour les spécifications techniques détaillées d'un produit ou projet.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "contact_page_template.html", "template_type": "HTML_CONTACT_PAGE",
            "display_name_fr": "Page de Contacts (HTML)", "description_fr": "Modèle HTML pour une page listant les contacts clés d'un projet.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "proforma_invoice_template.html", "template_type": "HTML_PROFORMA",
            "display_name_fr": "Facture Proforma (HTML)", "description_fr": "Modèle HTML pour la génération de factures proforma.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "packing_list_template.html", "template_type": "HTML_PACKING_LIST",
            "display_name_fr": "Liste de Colisage (HTML)", "description_fr": "Modèle HTML pour les listes de colisage.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "sales_contract_template.html", "template_type": "HTML_SALES_CONTRACT",
            "display_name_fr": "Contrat de Vente (HTML)", "description_fr": "Modèle HTML pour les contrats de vente.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "warranty_document_template.html", "template_type": "HTML_WARRANTY",
            "display_name_fr": "Document de Garantie (HTML)", "description_fr": "Modèle HTML pour les documents de garantie.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "cover_page_template.html", "template_type": "HTML_COVER_PAGE",
            "display_name_fr": "Page de Garde (HTML)", "description_fr": "Modèle HTML pour les pages de garde de documents.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "product_images_template.html", "template_type": "HTML_PRODUCT_IMAGES", # template_type can be specific
            "display_name_fr": "Affichage Images Produit (HTML)", "description_fr": "Modèle HTML pour afficher les images des produits, leur nom et code.",
            "category_name": "Documents HTML", # Ou une autre catégorie si souhaité, ex: "Utilitaires Produit"
        },
    ]

    # This is the single, definitive assignment for HTML_TEMPLATE_CONTENTS
    HTML_TEMPLATE_CONTENTS = {
        "technical_specifications_template.html": """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>SPECIFICATIONS TECHNIQUES - {{PRODUCT_NAME_TECH_SPEC}}</title>
    <style>
        body {
            font-family: "Segoe UI", Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f7fc;
            color: #333;
            font-size: 10pt;
        }
        .page {
            width: 210mm;
            min-height: 297mm;
            padding: 20mm;
            margin: 10mm auto;
            background-color: #fff;
            box-shadow: 0 0 15px rgba(0,0,0,0.1);
            page-break-after: always;
            box-sizing: border-box;
        }
        .page:last-child {
            page-break-after: avoid;
        }
        .header-container-tech {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #3498db; /* Technical Blue */
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        .logo-tech {
            max-width: 160px;
            max-height: 70px;
            object-fit: contain;
        }
        .document-title-tech {
            text-align: right;
        }
        .document-title-tech h1 {
            font-size: 20pt;
            color: #3498db;
            margin: 0 0 5px 0;
            font-weight: 600;
        }
        .document-title-tech p {
            font-size: 9pt;
            color: #555;
            margin: 2px 0;
        }
        .section-tech {
            margin-bottom: 20px;
        }
        .section-tech h2 {
            font-size: 14pt;
            color: #2980b9; /* Darker Technical Blue */
            border-bottom: 1px solid #aed6f1;
            padding-bottom: 6px;
            margin-top: 0; /* For first section on a page */
            margin-bottom: 15px;
            font-weight: 500;
        }
        .section-tech h3 {
            font-size: 12pt;
            color: #2c3e50;
            margin-top: 15px;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .section-tech p, .section-tech ul, .section-tech table {
            font-size: 9.5pt;
            line-height: 1.6;
            margin-bottom: 10px;
        }
        .section-tech ul {
            padding-left: 20px;
            list-style-type: disc;
        }
        .section-tech li {
            margin-bottom: 5px;
        }
        .tech-image-container {
            text-align: center;
            margin-bottom: 20px;
            border: 1px solid #e0e0e0;
            padding: 15px;
            background-color: #f9f9f9;
        }
        .tech-image-container img {
            max-width: 100%;
            max-height: 400px; /* Adjust as needed */
            object-fit: contain;
            border: 1px solid #ccc;
        }
        .dimensions-table {
            width: 100%;
            border-collapse: collapse;
        }
        .dimensions-table th, .dimensions-table td {
            border: 1px solid #bdc3c7; /* Gray borders */
            padding: 8px 10px;
            text-align: left;
        }
        .dimensions-table th {
            background-color: #ecf0f1; /* Light Gray Blue */
            font-weight: 500;
        }
        .footer-tech {
            border-top: 1px solid #3498db;
            padding-top: 10px;
            margin-top: 30px;
            text-align: center;
            font-size: 8.5pt;
            color: #777;
        }
        .page-number::before {
            content: "Page " counter(page);
        }
        @page {
            counter-increment: page;
        }
    </style>
</head>
<body>
    <!-- Page 1: Image and Dimensions -->
    <div class="page">
        <div class="header-container-tech">
            <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-tech">
            <div class="document-title-tech">
                <h1>SPECIFICATIONS TECHNIQUES</h1>
                <p>Produit: {{PRODUCT_NAME_TECH_SPEC}}</p>
                <p>Référence Projet: {{PROJECT_ID_TECH_SPEC}}</p>
                <p>Date: {{DATE_TECH_SPEC}} | Version: {{VERSION_TECH_SPEC}}</p>
            </div>
        </div>

        <div class="section-tech">
            <h2>Aperçu Technique et Dimensions</h2>
            <div class="tech-image-container">
                <img src="{{TECHNICAL_IMAGE_PATH_OR_EMBED}}" alt="Image Technique du Produit">
                <p><em>{{TECHNICAL_IMAGE_CAPTION}}</em></p>
            </div>
            <h3>Dimensions Principales</h3>
            <table class="dimensions-table">
                <thead>
                    <tr>
                        <th>Caractéristique</th>
                        <th>Valeur</th>
                        <th>Unité</th>
                        <th>Tolérance</th>
                    </tr>
                </thead>
                <tbody>
                    {{DIMENSIONS_TABLE_ROWS_TECH_SPEC}}
                </tbody>
            </table>
        </div>
        <div class="footer-tech">
            <span class="page-number"></span> | {{SELLER_COMPANY_NAME}} - Confidentiel
        </div>
    </div>

    <!-- Page 2: Material Conditions and Performance -->
    <div class="page">
        <div class="header-container-tech" style="border-bottom:none; margin-bottom:5px;">
             <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-tech" style="max-height:40px;">
             <div class="document-title-tech" style="padding-top:10px;">
                <p style="font-size:11pt; color:#3498db; font-weight:500;">SPECIFICATIONS TECHNIQUES - {{PRODUCT_NAME_TECH_SPEC}} (Suite)</p>
            </div>
        </div>
        <div class="section-tech">
            <h2>Conditions sur les Matériaux</h2>
            <p>{{MATERIALS_GENERAL_OVERVIEW_TECH_SPEC}}</p>
            {{MATERIALS_CONDITIONS_DETAILED_LIST_TECH_SPEC}}
        </div>
        <div class="section-tech">
            <h2>Performances et Caractéristiques Opérationnelles</h2>
            {{PERFORMANCE_SPECS_TECH_SPEC}}
        </div>
        <div class="footer-tech">
             <span class="page-number"></span> | {{SELLER_COMPANY_NAME}} - Confidentiel
        </div>
    </div>

    <!-- Page 3: Compliance, Environment, Maintenance, Notes -->
    <div class="page">
        <div class="header-container-tech" style="border-bottom:none; margin-bottom:5px;">
             <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-tech" style="max-height:40px;">
             <div class="document-title-tech" style="padding-top:10px;">
                <p style="font-size:11pt; color:#3498db; font-weight:500;">SPECIFICATIONS TECHNIQUES - {{PRODUCT_NAME_TECH_SPEC}} (Suite)</p>
            </div>
        </div>
        <div class="section-tech">
            <h2>Conformité et Standards</h2>
            {{COMPLIANCE_STANDARDS_TECH_SPEC}}
        </div>
        <div class="section-tech">
            <h2>Environnement d\'Utilisation</h2>
            {{OPERATING_ENVIRONMENT_TECH_SPEC}}
        </div>
        <div class="section-tech">
            <h2>Maintenance et Entretien</h2>
            {{MAINTENANCE_INFO_TECH_SPEC}}
        </div>
        <div class="section-tech">
            <h2>Notes Complémentaires</h2>
            <p>{{NOTES_TECH_SPEC}}</p>
        </div>
        <div class="footer-tech">
             <span class="page-number"></span> | {{SELLER_COMPANY_NAME}} - Confidentiel
        </div>
    </div>
</body>
</html>
""",
    "contact_page_template.html": """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>PAGE DE CONTACTS - Projet {{PROJECT_ID}}</title>
    <style>
        body {
            font-family: "Segoe UI", Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f7fc;
            color: #333;
            font-size: 10pt;
        }
        .page {
            width: 210mm;
            min-height: 297mm;
            padding: 20mm;
            margin: 10mm auto;
            background-color: #fff;
            box-shadow: 0 0 15px rgba(0,0,0,0.1);
            box-sizing: border-box;
        }
        .header-container-contact {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #28a745; /* Green accent */
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        .logo-contact {
            max-width: 160px;
            max-height: 70px;
            object-fit: contain;
        }
        .document-title-contact {
            text-align: right;
        }
        .document-title-contact h1 {
            font-size: 20pt;
            color: #28a745;
            margin: 0 0 5px 0;
            font-weight: 600;
        }
        .document-title-contact p {
            font-size: 9pt;
            color: #555;
            margin: 2px 0;
        }
        .intro-contact {
            margin-bottom: 20px;
            font-size: 11pt;
            text-align: center;
        }
        .contacts-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .contacts-table th, .contacts-table td {
            border: 1px solid #dee2e6;
            padding: 10px 12px;
            text-align: left;
            font-size: 9.5pt;
            vertical-align: top;
        }
        .contacts-table th {
            background-color: #28a745; /* Green accent */
            color: #fff;
            font-weight: 500;
            text-transform: uppercase;
        }
        .contacts-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        .contacts-table td a {
            color: #007bff;
            text-decoration: none;
        }
        .contacts-table td a:hover {
            text-decoration: underline;
        }
        .footer-contact {
            border-top: 1px solid #28a745;
            padding-top: 10px;
            margin-top: 30px;
            text-align: center;
            font-size: 8.5pt;
            color: #777;
        }
    </style>
</head>
<body>
    <div class="page">
        <div class="header-container-contact">
            <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-contact">
            <div class="document-title-contact">
                <h1>PAGE DE CONTACTS</h1>
                <p>Projet: {{PROJECT_ID}} - {{PROJECT_NAME_CONTACT_PAGE}}</p>
                <p>Date d'impression: {{DATE_CONTACT_PAGE}}</p>
            </div>
        </div>

        <div class="intro-contact">
            <p>Voici la liste des principaux intervenants et contacts pour le projet <strong>{{PROJECT_NAME_CONTACT_PAGE}}</strong>.</p>
        </div>

        <table class="contacts-table">
            <thead>
                <tr>
                    <th style="width:25%;">Rôle / Organisation</th>
                    <th style="width:20%;">Nom du Contact</th>
                    <th style="width:20%;">Fonction / Titre</th>
                    <th style="width:20%;">Email</th>
                    <th style="width:15%;">Téléphone</th>
                </tr>
            </thead>
            <tbody>
                {{CONTACTS_TABLE_ROWS_CONTACT_PAGE}}
            </tbody>
        </table>

        <div class="footer-contact">
            <p>{{SELLER_COMPANY_NAME}} - Facilitant la communication pour votre projet.</p>
        </div>
    </div>
</body>
</html>
""",
    "proforma_invoice_template.html": """<!DOCTYPE html>
<html lang="{{LANGUAGE_CODE}}">
<head>
    <meta charset="UTF-8">
    <title>Proforma Invoice</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
        .container { width: 90%; margin: auto; }
        .header, .footer { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #444; }
        .details-section { display: flex; justify-content: space-between; margin-bottom: 30px; }
        .company-details, .client-details { width: 48%; padding: 10px; background-color: #f9f9f9; border: 1px solid #eee; }
        .invoice-meta { clear: both; margin-bottom: 20px; background-color: #f9f9f9; padding: 15px; border: 1px solid #eee; }
        .invoice-meta p { margin: 5px 0; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.05); }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #e9e9e9; font-weight: bold; }
        .total-section { text-align: right; margin-top: 20px; padding-right:10px;}
        .total-section h3 { color: #555; }
        .footer p { font-size: 0.9em; color: #777; }
        .logo { max-width: 150px; max-height: 70px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{{SELLER_LOGO_PATH}}" alt="Company Logo" class="logo" />
            <h1>PROFORMA INVOICE</h1>
        </div>

        <div class="details-section">
            <div class="company-details">
                <h3>From:</h3>
                <p><strong>{{SELLER_COMPANY_NAME}}</strong></p>
                <p>{{SELLER_ADDRESS_LINE1}}</p>
                <p>{{SELLER_CITY_ZIP_COUNTRY}}</p>
                <p>Phone: {{SELLER_PHONE}}</p>
                <p>Email: {{SELLER_EMAIL}}</p>
                <p>VAT ID: {{SELLER_VAT_ID}}</p>
            </div>

            <div class="client-details">
                <h3>To:</h3>
                <p><strong>{{CLIENT_NAME}}</strong></p>
                <p>{{CLIENT_ADDRESS_LINE1}}</p>
                <p>{{CLIENT_CITY_ZIP_COUNTRY}}</p>
                <p>Contact: {{PRIMARY_CONTACT_NAME}}</p>
                <p>Email: {{PRIMARY_CONTACT_EMAIL}}</p>
                <p>VAT ID: {{CLIENT_VAT_ID}}</p>
            </div>
        </div>

        <div class="invoice-meta">
            <p><strong>Proforma Invoice No:</strong> {{PROFORMA_ID}}</p>
            <p><strong>Date:</strong> {{DATE}}</p>
            <p><strong>Project ID:</strong> {{PROJECT_ID}}</p>
            <p><strong>Payment Terms:</strong> {{PAYMENT_TERMS}}</p>
            <p><strong>Delivery Terms:</strong> {{DELIVERY_TERMS}}</p>
        </div>

        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Item Description</th>
                    <th>Quantity</th>
                    <th>Unit Price</th>
                    <th>Total Price</th>
                </tr>
            </thead>
            <tbody>
                {{doc.products_table_rows}} <!-- Populated by db.py -->
                <!-- Example Row (to be replaced by HtmlEditor):
                <tr>
                    <td>1</td>
                    <td>Product A</td>
                    <td>2</td>
                    <td>€100.00</td>
                    <td>€200.00</td>
                </tr>
                -->
            </tbody>
        </table>

        <div class="total-section">
            <p>Subtotal: {{SUBTOTAL_AMOUNT}}</p>
            <p>Discount ({{DISCOUNT_RATE}}%): {{DISCOUNT_AMOUNT}}</p>
            <p>VAT ({{VAT_RATE}}%): {{VAT_AMOUNT}}</p>
            <h3><strong>Total Amount Due: {{GRAND_TOTAL_AMOUNT}}</strong></h3>
        </div>

        <div class="footer">
            <p>Bank Details: {{BANK_NAME}}, Account: {{BANK_ACCOUNT_NUMBER}}, Swift/BIC: {{BANK_SWIFT_BIC}}</p>
            <p>This is a proforma invoice and is not a demand for payment.</p>
            <p>Thank you for your business!</p>
        </div>
    </div>
</body>
</html>""",
    "packing_list_template.html": """<!DOCTYPE html>
<html lang="{{LANGUAGE_CODE}}">
<head>
    <meta charset="UTF-8">
    <title>Packing List</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
        .container { width: 90%; margin: auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #444; }
        .details-section { display: flex; justify-content: space-between; margin-bottom: 30px; }
        .shipper-details, .consignee-details, .notify-party-details { width: 32%; padding: 10px; background-color: #f9f9f9; border: 1px solid #eee; }
        .shipment-info { clear: both; margin-bottom: 20px; background-color: #f9f9f9; padding: 15px; border: 1px solid #eee;}
        .shipment-info p { margin: 5px 0; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.05); }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #e9e9e9; font-weight: bold; }
        .totals-summary { margin-top: 20px; padding: 10px; background-color: #f9f9f9; border: 1px solid #eee; }
        .footer { text-align: center; margin-top: 30px; font-size: 0.9em; color: #777; }
        .logo { max-width: 150px; max-height: 70px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{{SELLER_LOGO_PATH}}" alt="Company Logo" class="logo" />
            <h1>PACKING LIST</h1>
        </div>

        <div class.details-section">
            <div class="shipper-details">
                <h3>Shipper/Exporter:</h3>
                <p><strong>{{SELLER_COMPANY_NAME}}</strong></p>
                <p>{{SELLER_ADDRESS_LINE1}}</p>
                <p>{{SELLER_CITY_ZIP_COUNTRY}}</p>
                <p>Phone: {{SELLER_PHONE}}</p>
            </div>

            <div class="consignee-details">
                <h3>Consignee:</h3>
                <p><strong>{{CLIENT_NAME}}</strong></p>
                <p>{{CLIENT_ADDRESS_LINE1}}</p>
                <p>{{CLIENT_CITY_ZIP_COUNTRY}}</p>
                <p>Contact: {{PRIMARY_CONTACT_NAME}}</p>
            </div>

            <div class="notify-party-details">
                <h3>Notify Party:</h3>
                <p>{{NOTIFY_PARTY_NAME}}</p>
                <p>{{NOTIFY_PARTY_ADDRESS}}</p>
            </div>
        </div>

        <div class="shipment-info">
            <p><strong>Packing List No:</strong> {{PACKING_LIST_ID}}</p>
            <p><strong>Date:</strong> {{DATE}}</p>
            <p><strong>Invoice No:</strong> {{INVOICE_ID}}</p>
            <p><strong>Project ID:</strong> {{PROJECT_ID}}</p>
            <p><strong>Vessel/Flight No:</strong> {{VESSEL_FLIGHT_NO}}</p>
            <p><strong>Port of Loading:</strong> {{PORT_OF_LOADING}}</p>
            <p><strong>Port of Discharge:</strong> {{PORT_OF_DISCHARGE}}</p>
            <p><strong>Final Destination:</strong> {{FINAL_DESTINATION_COUNTRY}}</p>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Mark & Nos.</th>
                    <th>Description of Goods</th>
                    <th>No. of Packages</th>
                    <th>Type of Packages</th>
                    <th>Net Weight (kg)</th>
                    <th>Gross Weight (kg)</th>
                    <th>Dimensions (LxWxH cm)</th>
                </tr>
            </thead>
            <tbody>
                {{doc.packing_list_items}} <!-- Populated by db.py -->
                <!-- Example Row:
                <tr>
                    <td>CS/NO. 1-10</td>
                    <td>Product Alpha - Model X</td>
                    <td>10</td>
                    <td>Cartons</td>
                    <td>100.00</td>
                    <td>110.00</td>
                    <td>50x40x30</td>
                </tr>
                -->
            </tbody>
        </table>

        <div class="totals-summary">
            <p><strong>Total Number of Packages:</strong> {{TOTAL_PACKAGES}}</p>
            <p><strong>Total Net Weight:</strong> {{TOTAL_NET_WEIGHT}} kg</p>
            <p><strong>Total Gross Weight:</strong> {{TOTAL_GROSS_WEIGHT}} kg</p>
            <p><strong>Total Volume:</strong> {{TOTAL_VOLUME_CBM}} CBM</p>
        </div>

        <div class="footer">
            <p>Exporter's Signature: _________________________</p>
            <p>Date: {{DATE}}</p>
        </div>
    </div>
</body>
</html>""",
    "sales_contract_template.html": """<!DOCTYPE html>
<html lang="{{LANGUAGE_CODE}}">
<head>
    <meta charset="UTF-8">
    <title>Sales Contract</title>
    <style>
        body { font-family: 'Times New Roman', Times, serif; margin: 40px; line-height: 1.6; color: #000; }
        .container { width: 85%; margin: auto; }
        .header { text-align: center; margin-bottom: 40px; }
        .contract-title { font-size: 24px; font-weight: bold; }
        .party-details { margin-bottom: 30px; overflow: auto; }
        .seller-details, .buyer-details { width: 48%; float: left; padding: 10px; }
        .buyer-details { float: right; }
        .article { margin-bottom: 20px; }
        .article h3 { font-size: 16px; margin-bottom: 5px; }
        .signatures { margin-top: 50px; overflow: auto; }
        .signature-block { width: 45%; float: left; margin-top:30px;}
        .signature-block p { margin-bottom: 40px; }
        .footer { text-align: center; margin-top: 50px; font-size: 0.8em; color: #555; }
        .logo { max-width: 120px; max-height: 60px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{{SELLER_LOGO_PATH}}" alt="Company Logo" class="logo" />
            <p class="contract-title">SALES CONTRACT</p>
            <p>Contract No: {{CONTRACT_ID}}</p>
            <p>Date: {{DATE}}</p>
        </div>

        <div class="party-details">
            <div class="seller-details">
                <h4>The Seller:</h4>
                <p><strong>{{SELLER_COMPANY_NAME}}</strong></p>
                <p>Address: {{SELLER_FULL_ADDRESS}}</p>
                <p>Represented by: {{SELLER_REPRESENTATIVE_NAME}}, {{SELLER_REPRESENTATIVE_TITLE}}</p>
            </div>
            <div class="buyer-details">
                <h4>The Buyer:</h4>
                <p><strong>{{CLIENT_NAME}}</strong> ({{CLIENT_COMPANY_NAME}})</p>
                <p>Address: {{CLIENT_FULL_ADDRESS}}</p>
                <p>Represented by: {{PRIMARY_CONTACT_NAME}}, {{PRIMARY_CONTACT_POSITION}}</p>
            </div>
        </div>

        <div class="article">
            <h3>Article 1: Subject of the Contract</h3>
            <p>The Seller agrees to sell and the Buyer agrees to buy the goods specified in Annex 1 ("The Goods") attached hereto and forming an integral part of this Contract.</p>
        </div>

        <div class="article">
            <h3>Article 2: Price and Total Value</h3>
            <p>The unit prices of the Goods are specified in {{CURRENCY_CODE}} as per Annex 1. The total value of this Contract is {{CURRENCY_CODE}} {{GRAND_TOTAL_AMOUNT}} ({{GRAND_TOTAL_AMOUNT_WORDS}}).</p>
        </div>

        <div class="article">
            <h3>Article 3: Terms of Payment</h3>
            <p>{{PAYMENT_TERMS_DETAIL}} (e.g., 30% advance payment, 70% upon shipment via Letter of Credit, etc.)</p>
        </div>

        <div class="article">
            <h3>Article 4: Delivery Terms</h3>
            <p>Delivery shall be made {{INCOTERMS}} {{NAMED_PLACE_OF_DELIVERY}} as per Incoterms 2020. Estimated date of shipment: {{ESTIMATED_SHIPMENT_DATE}}.</p>
        </div>

        <div class="article">
            <h3>Article 5: Packing and Marking</h3>
            <p>The Goods shall be packed in {{PACKING_TYPE_DESCRIPTION}}, suitable for international shipment and ensuring their safety during transit. Markings as per Buyer's instructions / Standard export markings.</p>
        </div>

        <div class="article">
            <h3>Article 6: Warranty</h3>
            <p>The Seller warrants that the Goods are new, unused, and conform to the specifications agreed upon for a period of {{WARRANTY_PERIOD_MONTHS}} months from the date of {{WARRANTY_START_CONDITION e.g., arrival at destination/installation}}.</p>
        </div>

        <div class="article">
            <h3>Article 7: Inspection</h3>
            <p>{{INSPECTION_CLAUSE_DETAIL}} (e.g., Inspection by Buyer's representative before shipment at Seller's premises / Inspection by {{INSPECTION_AGENCY_NAME}} at port of loading.)</p>
        </div>

        <div class="article">
            <h3>Article 8: Force Majeure</h3>
            <p>Neither party shall be liable for any failure or delay in performing their obligations under this Contract if such failure or delay is due to Force Majeure events...</p>
        </div>

        <div class="article">
            <h3>Article 9: Applicable Law and Dispute Resolution</h3>
            <p>This Contract shall be governed by and construed in accordance with the laws of {{JURISDICTION_COUNTRY_NAME}}. Any dispute arising out of or in connection with this Contract shall be settled by arbitration in {{ARBITRATION_LOCATION}} under the rules of {{ARBITRATION_RULES_BODY}}.</p>
        </div>

        <div class="article">
            <h3>Article 10: Entire Agreement</h3>
            <p>This Contract, including any Annexes, constitutes the entire agreement between the parties and supersedes all prior negotiations, understandings, and agreements, whether written or oral.</p>
        </div>

        <div class="signatures">
            <div class="signature-block">
                <p><strong>For the Seller:</strong></p>
                <p>_________________________</p>
                <p>{{SELLER_COMPANY_NAME}}</p>
                <p>Name: {{SELLER_REPRESENTATIVE_NAME}}</p>
                <p>Title: {{SELLER_REPRESENTATIVE_TITLE}}</p>
            </div>
            <div class="signature-block" style="float:right;">
                <p><strong>For the Buyer:</strong></p>
                <p>_________________________</p>
                <p>{{CLIENT_COMPANY_NAME}}</p>
                <p>Name: {{PRIMARY_CONTACT_NAME}}</p>
                <p>Title: {{PRIMARY_CONTACT_POSITION}}</p>
            </div>
        </div>

        <div class="footer">
            <p>Annex 1: Specification and Price of Goods (to be attached)</p>
        </div>
    </div>
</body>
</html>""",
    "warranty_document_template.html": """<!DOCTYPE html>
<html lang="{{LANGUAGE_CODE}}">
<head>
    <meta charset="UTF-8">
    <title>Warranty Certificate</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; color: #333; }
        .container { width: 80%; margin: auto; border: 2px solid #0056b3; padding: 30px; }
        .header { text-align: center; margin-bottom: 25px; }
        .header h1 { color: #0056b3; }
        .warranty-details p, .product-details p, .terms p { margin: 8px 0; line-height: 1.5; }
        .section-title { font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #0056b3; border-bottom: 1px solid #eee; padding-bottom: 5px;}
        .footer { text-align: center; margin-top: 40px; font-size: 0.9em; }
        .company-signature { margin-top: 30px;}
        .logo { max-width: 140px; max-height: 60px; margin-bottom: 10px;}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{{SELLER_LOGO_PATH}}" alt="Company Logo" class="logo" />
            <h1>WARRANTY CERTIFICATE</h1>
        </div>

        <div class="warranty-details">
            <p><strong>Certificate No:</strong> {{WARRANTY_CERTIFICATE_ID}}</p>
            <p><strong>Date of Issue:</strong> {{DATE}}</p>
            <p><strong>Issued By (Warrantor):</strong> {{SELLER_COMPANY_NAME}}</p>
            <p>Address: {{SELLER_FULL_ADDRESS}}</p>
        </div>

        <div class="product-details">
            <h3 class="section-title">Product Information</h3>
            <p><strong>Product Name/Description:</strong> {{PRODUCT_NAME_WARRANTY}}</p>
            <p><strong>Model No:</strong> {{PRODUCT_MODEL_WARRANTY}}</p>
            <p><strong>Serial No(s):</strong> {{PRODUCT_SERIAL_NUMBERS_WARRANTY}}</p>
            <p><strong>Date of Purchase/Supply:</strong> {{PURCHASE_SUPPLY_DATE}}</p>
            <p><strong>Original Invoice No:</strong> {{ORIGINAL_INVOICE_ID_WARRANTY}}</p>
        </div>

        <div class="beneficiary-details">
            <h3 class="section-title">Beneficiary Information</h3>
            <p><strong>Beneficiary (Owner):</strong> {{CLIENT_NAME}} ({{CLIENT_COMPANY_NAME}})</p>
            <p>Address: {{CLIENT_FULL_ADDRESS}}</p>
        </div>

        <div class="terms">
            <h3 class="section-title">Warranty Terms and Conditions</h3>
            <p><strong>Warranty Period:</strong> This product is warranted against defects in materials and workmanship for a period of <strong>{{WARRANTY_PERIOD_TEXT}}</strong> (e.g., twelve (12) months) from the date of {{WARRANTY_START_POINT_TEXT}} (e.g., original purchase / installation).</p>

            <p><strong>Coverage:</strong> During the warranty period, {{SELLER_COMPANY_NAME}} will repair or replace, at its option, any part found to be defective due to improper workmanship or materials, free of charge. This warranty covers {{WARRANTY_COVERAGE_DETAILS}}.</p>

            <p><strong>Exclusions:</strong> This warranty does not cover:
                <ul>
                    <li>Damage resulting from accident, misuse, abuse, neglect, or improper installation or maintenance.</li>
                    <li>Normal wear and tear, or cosmetic damage.</li>
                    <li>Products whose serial numbers have been altered, defaced, or removed.</li>
                    <li>Damage caused by use of non-original spare parts or accessories.</li>
                    <li>{{OTHER_EXCLUSIONS_LIST}}</li>
                </ul>
            </p>

            <p><strong>Claim Procedure:</strong> To make a warranty claim, please contact {{SELLER_COMPANY_NAME}} or an authorized service center at {{WARRANTY_CLAIM_CONTACT_INFO}}, providing proof of purchase and a description of the defect. {{WARRANTY_CLAIM_PROCEDURE_DETAIL}}</p>

            <p><strong>Limitation of Liability:</strong> The liability of {{SELLER_COMPANY_NAME}} under this warranty is limited to the repair or replacement of defective parts. {{SELLER_COMPANY_NAME}} shall not be liable for any incidental or consequential damages.</p>

            <p>This warranty gives you specific legal rights, and you may also have other rights which vary from country to country.</p>
        </div>

        <div class="company-signature">
            <p>For and on behalf of <strong>{{SELLER_COMPANY_NAME}}</strong></p>
            <br><br>
            <p>_________________________</p>
            <p>Authorized Signature</p>
            <p>Name: {{SELLER_AUTHORIZED_SIGNATORY_NAME}}</p>
            <p>Title: {{SELLER_AUTHORIZED_SIGNATORY_TITLE}}</p>
        </div>

        <div class="footer">
            <p>&copy; {{CURRENT_YEAR}} {{SELLER_COMPANY_NAME}}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>""",
    "cover_page_template.html": """<!DOCTYPE html>
<html lang="{{LANGUAGE_CODE}}">
<head>
    <meta charset="UTF-8">
    <title>{{doc.document_title}} - {{ lang.cover_page_title_suffix }}</title>
    <style>
        body { font-family: 'Roboto', Arial, sans-serif; margin: 0; padding: 20mm; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: calc(100vh - 40mm); background-color: #eef2f7; color: #333; text-align: center; }
        .cover-container { width: 100%; max-width: 820px; background-color: #fff; padding: 50px 60px; box-shadow: 0 8px 20px rgba(0,0,0,0.08); border-top: 8px solid #3498db; border-radius: 8px; }
        .logo { max-width: 180px; max-height: 75px; margin-bottom: 35px; object-fit: contain; }
        h1 { font-size: 2.6em; color: #3498db; margin-bottom: 15px; font-weight: 500; text-transform: uppercase; }
        h2 { font-size: 1.6em; color: #718096; margin-bottom: 30px; font-weight: 300; }
        .meta-info { margin-top: 35px; margin-bottom: 35px; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; padding: 20px 0; }
        .meta-info p { font-size: 1em; margin: 10px 0; line-height: 1.6; }
        .meta-info strong { color: #3498db; font-weight: 500; }
        .details-section { display: flex; justify-content: space-between; margin-top: 35px; text-align: left; }
        .details-column { width: 48%; }
        .details-column h4 { font-size: 1.1em; color: #2d3748; margin-bottom: 12px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; font-weight: 500; }
        .details-column p { font-size: 0.95em; line-height: 1.5; margin-bottom: 6px; }
        .footer { margin-top: 45px; font-size: 0.85em; color: #a0aec0; }
        .footer p { margin: 5px 0; }
    </style>
</head>
<body>
    <div class="cover-container">
        <img src="{{ seller_company_logo_path }}" alt="{{ lang.cover_logo_alt_text }}" class="logo" />
        <h1>{{ doc.document_title }}</h1>
        {{#if doc.document_subtitle}}
        <h2>{{ doc.document_subtitle }}</h2>
        {{/if}}
        <div class="meta-info">
            <p><strong>{{ lang.cover_client_label }}:</strong> {{ client_name }} {{#if client_company_name}}({{client_company_name}}){{/if}}</p>
            <p><strong>{{ lang.cover_project_id_label }}:</strong> {{ project_id }}</p>
            <p><strong>{{ lang.cover_date_label }}:</strong> {{ date }}</p>
            {{#if doc.document_version}}
            <p><strong>{{ lang.cover_version_label }}:</strong> {{ doc.document_version }}</p>
            {{/if}}
        </div>
        <div class="details-section">
            <div class="details-column">
                <h4>{{ lang.cover_prepared_for_title }}</h4>
                <p>{{ client_name }}</p>
                <p>{{ client_full_address }}</p>
            </div>
            <div class="details-column">
                <h4>{{ lang.cover_prepared_by_title }}</h4>
                <p><strong>{{ seller_company_name }}</strong></p>
                <p>{{ seller_full_address }}</p>
                <p>{{ lang.cover_contact_label }}: {{ seller_company_email }} | {{ seller_company_phone }}</p>
            </div>
        </div>
        <div class="footer">
            <p>{{ lang.cover_footer_confidential }}</p>
            <p>&copy; {{ current_year }} {{ seller_company_name }}</p>
        </div>
    </div>
</body>
</html>""",
        "product_images_template.html": """<!DOCTYPE html>
<html lang="{{LANGUAGE_CODE}}">
<head>
    <meta charset="UTF-8">
    <title>{{ lang.product_images_title }} - {{ client_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
        .product-grid { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
        .product-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; width: 200px; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
        .product-card img { max-width: 100%; height: auto; max-height: 150px; margin-bottom: 10px; border-radius: 4px; }
        .product-card h3 { font-size: 1.1em; margin: 10px 0 5px 0; color: #0056b3; }
        .product-card p { font-size: 0.9em; margin: 5px 0; }
    </style>
</head>
<body>
    <h1>{{ lang.product_images_header }}</h1>
    <p><strong>{{ lang.client_label }}:</strong> {{ client_name }}</p>
    {{#if project_name}}
    <p><strong>{{ lang.project_label }}:</strong> {{ project_name }}</p>
    {{/if}}
    <hr>
    <div class="product-grid">
        {{#each products}}
        <div class="product-card">
            {{#if main_image_path}}
            <img src="{{ main_image_path }}" alt="{{ name }}">
            {{else}}
            <p><em>{{ ../lang.no_image_available }}</em></p>
            {{/if}}
            <h3>{{ name }}</h3>
            <p><strong>{{ ../lang.code_label }}:</strong> {{ code }}</p>
        </div>
        {{else}}
        <p>{{ ../lang.no_products_to_display }}</p>
        {{/each}}
    </div>
</body>
</html>"""
}


    html_template_languages = ["fr", "en", "ar", "tr", "pt"]

    logging.info("Processing HTML templates (file creation only)...")
    # html_category_id = db_manager.add_template_category("Documents HTML", "Modèles de documents basés sur HTML.") # DB seeding call removed
    # if html_category_id is None:
    #     logging.error("CRITICAL ERROR: Could not create or find 'Documents HTML' category. HTML templates may not be added correctly to DB.")
    # Seeding of categories is now handled by db.seed_initial_data

    for html_meta in DEFAULT_HTML_TEMPLATES_METADATA:
        base_fn = html_meta['base_file_name']
        html_content_to_write = HTML_TEMPLATE_CONTENTS.get(base_fn, f"<p>Default content for {base_fn}</p>") # Fallback
        for lang_code in html_template_languages:
            lang_specific_template_dir = os.path.join(templates_root_dir, lang_code)
            os.makedirs(lang_specific_template_dir, exist_ok=True)
            template_file_full_path = os.path.join(lang_specific_template_dir, base_fn)
            created_file_on_disk_html = False

            if not os.path.exists(template_file_full_path):
                try:
                    lang_specific_content = html_content_to_write.replace("{{LANGUAGE_CODE}}", lang_code)
                    if base_fn == "cover_page_template.html" and lang_code == 'ar':
                        # Ensure RTL direction for Arabic cover page
                        lang_specific_content = lang_specific_content.replace('<html lang="ar">', '<html lang="ar" dir="rtl">', 1)

                    # Placeholder adjustments for proforma and packing list
                    if base_fn == "proforma_invoice_template.html":
                        lang_specific_content = lang_specific_content.replace(
                            "<tbody>\\n                {{PRODUCTS_TABLE_ROWS}}\\n                <!-- Example Row (to be replaced by HtmlEditor):",
                            "<tbody>\\n                {{doc.products_table_rows}} <!-- Populated by db.py -->\\n                <!-- Example Row (to be replaced by HtmlEditor):"
                        )
                    elif base_fn == "packing_list_template.html":
                         lang_specific_content = lang_specific_content.replace(
                            "<tbody>\\n                {{PACKING_LIST_ITEMS}}\\n                <!-- Example Row:",
                            "<tbody>\\n                {{doc.packing_list_items}} <!-- Populated by db.py -->\\n                <!-- Example Row:"
                        )
                    with open(template_file_full_path, "w", encoding="utf-8") as f:
                        f.write(lang_specific_content)
                    logging.info(f"Created HTML template file: {template_file_full_path}")
                    created_file_on_disk_html = True
                except IOError as e_io:
                    logging.error(f"Error creating HTML template file {template_file_full_path}: {e_io}")

            # DB registration for HTML templates removed. This is now handled by db.seed_initial_data if these templates are to be seeded.
            # The file creation part above is preserved.
            if created_file_on_disk_html:
                logging.info(f"HTML template file '{base_fn}' for {lang_code} ensured on disk.")
            else:
                logging.info(f"HTML template file '{base_fn}' for {lang_code} already exists on disk or failed to create.")

    # --- Default Email Templates ---
    # Email template DB registration and file creation logic is removed from here.
    # db.seed_initial_data now handles email template DB records,
    # and db.add_default_template_if_not_exists reads content from 'email_template_designs'
    # if the file exists there, storing it in raw_template_file_data.
    # app_setup.py should not be responsible for creating email template files in 'templates_root_dir/lang_code/'
    # if their content is meant to be sourced from 'email_template_designs' and stored in DB.
    logging.info("Skipping Email template file creation and DB registration in app_setup.py.")
    logging.info("Email template records are seeded by db.seed_initial_data, and content is loaded from 'email_template_designs' into the DB.")

    # Removed: Old logic for default_email_templates_data and loops creating files and DB entries.
    # The following code block related to default_email_templates_data was removed:
    # email_category_obj = db_manager.get_template_category_by_name("Modèles Email")
    # email_category_id = email_category_obj['category_id'] if email_category_obj else None
    # ... (and the entire loop processing default_email_templates_data) ...

    logging.info("Default template initialization finished.")
# Example of how this might be called by main.py after app object creation
# if __name__ == "__main__": # Or rather, in main.py
#     setup_logging() # Call early
#     initialize_default_templates(CONFIG, APP_ROOT_DIR)
