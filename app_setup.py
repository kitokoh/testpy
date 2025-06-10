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
import db as db_manager # For initialize_default_templates
from db import DATABASE_NAME as CENTRAL_DATABASE_NAME # For DATABASE_NAME
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
    general_category_id = db_manager.add_template_category("General", "General purpose templates")
    if general_category_id is None:
        logging.error("CRITICAL ERROR: Could not create or find the 'General' template category. Default Excel templates may not be added correctly to DB.")

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

            if general_category_id is not None: # Only attempt DB registration if category exists
                template_name_for_db = "Unknown Template"
                if template_file_name == SPEC_TECH_TEMPLATE_NAME:
                    template_name_for_db = "Spécification Technique (Défaut)"
                elif template_file_name == PROFORMA_TEMPLATE_NAME:
                    template_name_for_db = "Proforma (Défaut)"
                elif template_file_name == CONTRAT_VENTE_TEMPLATE_NAME:
                    template_name_for_db = "Contrat de Vente (Défaut)"
                elif template_file_name == PACKING_LISTE_TEMPLATE_NAME:
                    template_name_for_db = "Packing Liste (Défaut)"

                template_metadata = {
                    'template_name': template_name_for_db,
                    'template_type': 'document_excel',
                    'language_code': lang_code,
                    'base_file_name': template_file_name,
                    'description': f"Modèle Excel par défaut pour {template_name_for_db} en {lang_code}.",
                    'category_id': general_category_id,
                    'is_default_for_type_lang': True if lang_code == 'fr' else False # Default French ones
                }
                db_template_id = db_manager.add_default_template_if_not_exists(template_metadata)
                if db_template_id and created_file_on_disk:
                    logging.info(f"Registered new Excel template '{template_name_for_db}' ({lang_code}) in DB. ID: {db_template_id}")
                elif not db_template_id:
                    logging.warning(f"Failed to register Excel template '{template_name_for_db}' ({lang_code}) in DB.")
            # else: (general_category_id is None) - error already logged

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
    ]

    HTML_TEMPLATE_CONTENTS = {
        "technical_specifications_template.html": '<!DOCTYPE html>\\n<html lang="{{LANGUAGE_CODE}}">...</html>', # Content truncated for brevity
        "contact_page_template.html": '<!DOCTYPE html>\\n<html lang="{{LANGUAGE_CODE}}">...</html>',
        "proforma_invoice_template.html": '<!DOCTYPE html>\\n<html lang="{{LANGUAGE_CODE}}">...</html>',
        "packing_list_template.html": '<!DOCTYPE html>\\n<html lang="{{LANGUAGE_CODE}}">...</html>',
        "sales_contract_template.html": '<!DOCTYPE html>\\n<html lang="{{LANGUAGE_CODE}}">...</html>',
        "warranty_document_template.html": '<!DOCTYPE html>\\n<html lang="{{LANGUAGE_CODE}}">...</html>',
        "cover_page_template.html": '<!DOCTYPE html>\\n<html lang="{{LANGUAGE_CODE}}">...</html>',
        # Actual full content should be here. For this refactoring step, I'm using placeholders.
        # The real content is very long and was provided in the previous main.py listing.
        # NOTE: For the actual implementation, the full HTML content strings from the original main.py must be used here.
    }
    # Populate HTML_TEMPLATE_CONTENTS with the actual long strings from main.py
    # This is a placeholder for the actual content.
    HTML_TEMPLATE_CONTENTS = {
    "technical_specifications_template.html": '<!DOCTYPE html>\\n<html lang="fr">\\n<head>\\n    <meta charset="UTF-8">\\n    <title>SPECIFICATIONS TECHNIQUES - {{PRODUCT_NAME_TECH_SPEC}}</title>\\n    <style>\\n        body {\\n            font-family: "Segoe UI", Arial, sans-serif;\\n            margin: 0;\\n            padding: 0;\\n            background-color: #f4f7fc;\\n            color: #333;\\n            font-size: 10pt;\\n        }\\n        .page {\\n            width: 210mm;\\n            min-height: 297mm;\\n            padding: 20mm;\\n            margin: 10mm auto;\\n            background-color: #fff;\\n            box-shadow: 0 0 15px rgba(0,0,0,0.1);\\n            page-break-after: always;\\n            box-sizing: border-box;\\n        }\\n        .page:last-child {\\n            page-break-after: avoid;\\n        }\\n        .header-container-tech {\\n            display: flex;\\n            justify-content: space-between;\\n            align-items: flex-start;\\n            border-bottom: 2px solid #3498db; /* Technical Blue */\\n            padding-bottom: 15px;\\n            margin-bottom: 25px;\\n        }\\n        .logo-tech {\\n            max-width: 160px;\\n            max-height: 70px;\\n            object-fit: contain;\\n        }\\n        .document-title-tech {\\n            text-align: right;\\n        }\\n        .document-title-tech h1 {\\n            font-size: 20pt;\\n            color: #3498db;\\n            margin: 0 0 5px 0;\\n            font-weight: 600;\\n        }\\n        .document-title-tech p {\\n            font-size: 9pt;\\n            color: #555;\\n            margin: 2px 0;\\n        }\\n        .section-tech {\\n            margin-bottom: 20px;\\n        }\\n        .section-tech h2 {\\n            font-size: 14pt;\\n            color: #2980b9; /* Darker Technical Blue */\\n            border-bottom: 1px solid #aed6f1;\\n            padding-bottom: 6px;\\n            margin-top: 0; /* For first section on a page */\\n            margin-bottom: 15px;\\n            font-weight: 500;\\n        }\\n        .section-tech h3 {\\n            font-size: 12pt;\\n            color: #2c3e50;\\n            margin-top: 15px;\\n            margin-bottom: 8px;\\n            font-weight: 500;\\n        }\\n        .section-tech p, .section-tech ul, .section-tech table {\\n            font-size: 9.5pt;\\n            line-height: 1.6;\\n            margin-bottom: 10px;\\n        }\\n        .section-tech ul {\\n            padding-left: 20px;\\n            list-style-type: disc;\\n        }\\n        .section-tech li {\\n            margin-bottom: 5px;\\n        }\\n        .tech-image-container {\\n            text-align: center;\\n            margin-bottom: 20px;\\n            border: 1px solid #e0e0e0;\\n            padding: 15px;\\n            background-color: #f9f9f9;\\n        }\\n        .tech-image-container img {\\n            max-width: 100%;\\n            max-height: 400px; /* Adjust as needed */\\n            object-fit: contain;\\n            border: 1px solid #ccc;\\n        }\\n        .dimensions-table {\\n            width: 100%;\\n            border-collapse: collapse;\\n        }\\n        .dimensions-table th, .dimensions-table td {\\n            border: 1px solid #bdc3c7; /* Gray borders */\\n            padding: 8px 10px;\\n            text-align: left;\\n        }\\n        .dimensions-table th {\\n            background-color: #ecf0f1; /* Light Gray Blue */\\n            font-weight: 500;\\n        }\\n        .footer-tech {\\n            border-top: 1px solid #3498db;\\n            padding-top: 10px;\\n            margin-top: 30px;\\n            text-align: center;\\n            font-size: 8.5pt;\\n            color: #777;\\n        }\\n        .page-number::before {\\n            content: "Page " counter(page);\\n        }\\n        @page {\\n            counter-increment: page;\\n        }\\n    </style>\\n</head>\\n<body>\\n    <!-- Page 1: Image and Dimensions -->\\n    <div class="page">\\n        <div class="header-container-tech">\\n            <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-tech">\\n            <div class="document-title-tech">\\n                <h1>SPECIFICATIONS TECHNIQUES</h1>\\n                <p>Produit: {{PRODUCT_NAME_TECH_SPEC}}</p>\\n                <p>Référence Projet: {{PROJECT_ID_TECH_SPEC}}</p>\\n                <p>Date: {{DATE_TECH_SPEC}} | Version: {{VERSION_TECH_SPEC}}</p>\\n            </div>\\n        </div>\\n\\n        <div class="section-tech">\\n            <h2>Aperçu Technique et Dimensions</h2>\\n            <div class="tech-image-container">\\n                <img src="{{TECHNICAL_IMAGE_PATH_OR_EMBED}}" alt="Image Technique du Produit">\\n                <p><em>{{TECHNICAL_IMAGE_CAPTION}}</em></p>\\n            </div>\\n            <h3>Dimensions Principales</h3>\\n            <table class="dimensions-table">\\n                <thead>\\n                    <tr>\\n                        <th>Caractéristique</th>\\n                        <th>Valeur</th>\\n                        <th>Unité</th>\\n                        <th>Tolérance</th>\\n                    </tr>\\n                </thead>\\n                <tbody>\\n                    {{DIMENSIONS_TABLE_ROWS_TECH_SPEC}}\\n                </tbody>\\n            </table>\\n        </div>\\n        <div class="footer-tech">\\n            <span class="page-number"></span> | {{SELLER_COMPANY_NAME}} - Confidentiel\\n        </div>\\n    </div>\\n\\n    <!-- Page 2: Material Conditions and Performance -->\\n    <div class="page">\\n        <div class="header-container-tech" style="border-bottom:none; margin-bottom:5px;">\\n             <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-tech" style="max-height:40px;">\\n             <div class="document-title-tech" style="padding-top:10px;">\\n                <p style="font-size:11pt; color:#3498db; font-weight:500;">SPECIFICATIONS TECHNIQUES - {{PRODUCT_NAME_TECH_SPEC}} (Suite)</p>\\n            </div>\\n        </div>\\n        <div class="section-tech">\\n            <h2>Conditions sur les Matériaux</h2>\\n            <p>{{MATERIALS_GENERAL_OVERVIEW_TECH_SPEC}}</p>\\n            {{MATERIALS_CONDITIONS_DETAILED_LIST_TECH_SPEC}}\\n        </div>\\n        <div class="section-tech">\\n            <h2>Performances et Caractéristiques Opérationnelles</h2>\\n            {{PERFORMANCE_SPECS_TECH_SPEC}}\\n        </div>\\n        <div class="footer-tech">\\n             <span class="page-number"></span> | {{SELLER_COMPANY_NAME}} - Confidentiel\\n        </div>\\n    </div>\\n\\n    <!-- Page 3: Compliance, Environment, Maintenance, Notes -->\\n    <div class="page">\\n        <div class="header-container-tech" style="border-bottom:none; margin-bottom:5px;">\\n             <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-tech" style="max-height:40px;">\\n             <div class="document-title-tech" style="padding-top:10px;">\\n                <p style="font-size:11pt; color:#3498db; font-weight:500;">SPECIFICATIONS TECHNIQUES - {{PRODUCT_NAME_TECH_SPEC}} (Suite)</p>\\n            </div>\\n        </div>\\n        <div class="section-tech">\\n            <h2>Conformité et Standards</h2>\\n            {{COMPLIANCE_STANDARDS_TECH_SPEC}}\\n        </div>\\n        <div class="section-tech">\\n            <h2>Environnement d\'\'\'Utilisation</h2>\\n            {{OPERATING_ENVIRONMENT_TECH_SPEC}}\\n        </div>\\n        <div class="section-tech">\\n            <h2>Maintenance et Entretien</h2>\\n            {{MAINTENANCE_INFO_TECH_SPEC}}\\n        </div>\\n        <div class="section-tech">\\n            <h2>Notes Complémentaires</h2>\\n            <p>{{NOTES_TECH_SPEC}}</p>\\n        </div>\\n        <div class="footer-tech">\\n             <span class="page-number"></span> | {{SELLER_COMPANY_NAME}} - Confidentiel\\n        </div>\\n    </div>\\n</body>\\n</html>\\n',
    "contact_page_template.html": '<!DOCTYPE html>\\n<html lang="fr">\\n<head>\\n    <meta charset="UTF-8">\\n    <title>PAGE DE CONTACTS - Projet {{PROJECT_ID}}</title>\\n    <style>\\n        body {\\n            font-family: "Segoe UI", Arial, sans-serif;\\n            margin: 0;\\n            padding: 0;\\n            background-color: #f4f7fc;\\n            color: #333;\\n            font-size: 10pt;\\n        }\\n        .page {\\n            width: 210mm;\\n            min-height: 297mm;\\n            padding: 20mm;\\n            margin: 10mm auto;\\n            background-color: #fff;\\n            box-shadow: 0 0 15px rgba(0,0,0,0.1);\\n            box-sizing: border-box;\\n        }\\n        .header-container-contact {\\n            display: flex;\\n            justify-content: space-between;\\n            align-items: flex-start;\\n            border-bottom: 2px solid #28a745; /* Green accent */\\n            padding-bottom: 15px;\\n            margin-bottom: 25px;\\n        }\\n        .logo-contact {\\n            max-width: 160px;\\n            max-height: 70px;\\n            object-fit: contain;\\n        }\\n        .document-title-contact {\\n            text-align: right;\\n        }\\n        .document-title-contact h1 {\\n            font-size: 20pt;\\n            color: #28a745;\\n            margin: 0 0 5px 0;\\n            font-weight: 600;\\n        }\\n        .document-title-contact p {\\n            font-size: 9pt;\\n            color: #555;\\n            margin: 2px 0;\\n        }\\n        .intro-contact {\\n            margin-bottom: 20px;\\n            font-size: 11pt;\\n            text-align: center;\\n        }\\n        .contacts-table {\\n            width: 100%;\\n            border-collapse: collapse;\\n            margin-top: 15px;\\n        }\\n        .contacts-table th, .contacts-table td {\\n            border: 1px solid #dee2e6;\\n            padding: 10px 12px;\\n            text-align: left;\\n            font-size: 9.5pt;\\n            vertical-align: top;\\n        }\\n        .contacts-table th {\\n            background-color: #28a745; /* Green accent */\\n            color: #fff;\\n            font-weight: 500;\\n            text-transform: uppercase;\\n        }\\n        .contacts-table tr:nth-child(even) {\\n            background-color: #f8f9fa;\\n        }\\n        .contacts-table td a {\\n            color: #007bff;\\n            text-decoration: none;\\n        }\\n        .contacts-table td a:hover {\\n            text-decoration: underline;\\n        }\\n        .footer-contact {\\n            border-top: 1px solid #28a745;\\n            padding-top: 10px;\\n            margin-top: 30px;\\n            text-align: center;\\n            font-size: 8.5pt;\\n            color: #777;\\n        }\\n    </style>\\n</head>\\n<body>\\n    <div class="page">\\n        <div class="header-container-contact">\\n            <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-contact">\\n            <div class="document-title-contact">\\n                <h1>PAGE DE CONTACTS</h1>\\n                <p>Projet: {{PROJECT_ID}} - {{PROJECT_NAME_CONTACT_PAGE}}</p>\\n                <p>Date d\'\'\'impression: {{DATE_CONTACT_PAGE}}</p>\\n            </div>\\n        </div>\\n\\n        <div class="intro-contact">\\n            <p>Voici la liste des principaux intervenants et contacts pour le projet <strong>{{PROJECT_NAME_CONTACT_PAGE}}</strong>.</p>\\n        </div>\\n\\n        <table class="contacts-table">\\n            <thead>\\n                <tr>\\n                    <th style="width:25%;">Rôle / Organisation</th>\\n                    <th style="width:20%;">Nom du Contact</th>\\n                    <th style="width:20%;">Fonction / Titre</th>\\n                    <th style="width:20%;">Email</th>\\n                    <th style="width:15%;">Téléphone</th>\\n                </tr>\\n            </thead>\\n            <tbody>\\n                {{CONTACTS_TABLE_ROWS_CONTACT_PAGE}}\\n            </tbody>\\n        </table>\\n        \\n        <div class="footer-contact">\\n            <p>{{SELLER_COMPANY_NAME}} - Facilitant la communication pour votre projet.</p>\\n        </div>\\n    </div>\\n</body>\\n</html>\\n',
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
    <title>{{doc.document_title}} - Cover Page</title> <!-- Adjusted placeholder -->
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; margin: 0; padding: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; background-color: #f0f4f8; color: #333; text-align: center; }
        .cover-container { width: 80%; max-width: 800px; background-color: #fff; padding: 50px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); border-top: 10px solid #005ea5; }
        .logo { max-width: 200px; max-height: 100px; margin-bottom: 30px; }
        h1 { font-size: 2.8em; color: #005ea5; margin-bottom: 15px; text-transform: uppercase; }
        h2 { font-size: 1.8em; color: #555; margin-bottom: 25px; font-weight: normal; }
        .meta-info { margin-top: 40px; margin-bottom: 40px; }
        .meta-info p { font-size: 1.1em; margin: 8px 0; }
        .meta-info strong { color: #005ea5; }
        .prepared-for, .prepared-by { margin-top: 30px; }
        .footer { margin-top: 50px; font-size: 0.9em; color: #777; }
    </style>
</head>
<body>
    <div class="cover-container">
        <img src="{{seller_company_logo_path}}" alt="Company Logo" class="logo"> <!-- Adjusted placeholder -->

        <h1>{{doc.document_title}}</h1> <!-- Adjusted placeholder -->
        {{#if doc.document_subtitle}}
        <h2>{{doc.document_subtitle}}</h2> <!-- Adjusted placeholder -->
        {{/if}}

        <div class="meta-info">
            <p><strong>Client:</strong> {{client_name}} ({{client_company_name}})</p> <!-- Adjusted placeholder -->
            <p><strong>Project ID:</strong> {{project_id}}</p> <!-- Adjusted placeholder -->
            <p><strong>Date:</strong> {{date}}</p> <!-- Adjusted placeholder -->
            {{#if doc.document_version}}
            <p><strong>Version:</strong> {{doc.document_version}}</p> <!-- Adjusted placeholder -->
            {{/if}}
        </div>

        <div class="prepared-for">
            <p><em>Prepared for:</em></p>
            <p>{{client_name}}</p> <!-- Adjusted placeholder -->
            <p>{{client_full_address}}</p> <!-- Adjusted placeholder -->
        </div>

        <div class="prepared-by">
            <p><em>Prepared by:</em></p>
            <p><strong>{{seller_company_name}}</strong></p> <!-- Adjusted placeholder -->
            <p>{{seller_full_address}}</p> <!-- Adjusted placeholder -->
            <p>Contact: {{seller_company_email}} | {{seller_company_phone}}</p> <!-- Adjusted placeholder -->
        </div>

        <div class="footer">
            <p>This document is confidential and intended solely for the use of the individual or entity to whom it is addressed.</p>
            <p>&copy; {{current_year}} {{seller_company_name}}</p> <!-- Adjusted placeholder -->
        </div>
    </div>
</body>
</html>"""
}


    html_template_languages = ["fr", "en", "ar", "tr", "pt"]

    logging.info("Processing HTML templates...")
    html_category_id = db_manager.add_template_category("Documents HTML", "Modèles de documents basés sur HTML.")
    if html_category_id is None:
        logging.error("CRITICAL ERROR: Could not create or find 'Documents HTML' category. HTML templates may not be added correctly to DB.")

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

            if html_category_id is not None: # Only register if category exists
                db_template_name = f"{html_meta['display_name_fr']} ({lang_code.upper()})"
                # Determine if this template should be default for its type and language
                is_default = False # Default to False
                if html_meta['base_file_name'] == "packing_list_template.html":
                    if lang_code in ['en', 'fr', 'ar', 'tr']:
                        is_default = True
                    # For other languages of packing_list_template.html, it remains False unless explicitly set by other logic
                else:
                    # Existing logic for other templates (e.g., French default)
                    is_default = True if lang_code == 'fr' else False

                template_data_for_db = {
                    'template_name': db_template_name, 'template_type': html_meta['template_type'],
                    'language_code': lang_code, 'base_file_name': html_meta['base_file_name'],
                    'description': html_meta['description_fr'], 'category_id': html_category_id,
                    'is_default_for_type_lang': is_default
                }
                db_html_template_id = db_manager.add_default_template_if_not_exists(template_data_for_db)
                if db_html_template_id and created_file_on_disk_html:
                    logging.info(f"Registered new HTML template '{db_template_name}' ({lang_code}) in DB. ID: {db_html_template_id}")
                elif not db_html_template_id:
                     logging.warning(f"Failed to register HTML template '{db_template_name}' ({lang_code}) in DB.")
            # else: (html_category_id is None) - error already logged

    # --- Default Email Templates ---
    logging.info("Processing Email templates...")
    email_category_obj = db_manager.get_template_category_by_name("Modèles Email")
    email_category_id = email_category_obj['category_id'] if email_category_obj else None

    if email_category_id is None:
        logging.error("CRITICAL ERROR: 'Modèles Email' category not found. Cannot register default email templates.")
    else:
        # Full email template data here (from main.py)
        default_email_templates_data = [
            {
                "name_key": "EMAIL_GREETING",
                "display_name_prefix": {"fr": "Salutation Générale", "en": "General Greeting", "ar": "تحية عامة", "tr": "Genel Selamlama", "pt": "Saudação Geral"},
                "subject": {
                    "fr": "Un message de {{seller.company_name}}", "en": "A message from {{seller.company_name}}",
                    "ar": "رسالة من {{seller.company_name}}", "tr": "{{seller.company_name}} firmasından bir mesaj",
                    "pt": "Uma mensagem de {{seller.company_name}}"
                },
                "html_content": {
                    "fr": "<p>Cher/Chère {{client.contact_person_name}},</p><p>Merci pour votre intérêt pour nos services.</p><p>Cordialement,</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>",
                    "en": "<p>Dear {{client.contact_person_name}},</p><p>Thank you for your interest in our services.</p><p>Sincerely,</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>",
                    "ar": "<p>عزيزي/عزيزتي {{client.contact_person_name}}،</p><p>شكراً لاهتمامك بخدماتنا.</p><p>مع خالص التقدير،</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>",
                    "tr": "<p>Sayın {{client.contact_person_name}},</p><p>Hizmetlerimize gösterdiğiniz ilgi için teşekkür ederiz.</p><p>Saygılarımla,</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>",
                    "pt": "<p>Prezado(a) {{client.contact_person_name}},</p><p>Obrigado pelo seu interesse em nossos serviços.</p><p>Atenciosamente,</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>"
                },
                "txt_content": {
                    "fr": "Cher/Chère {{client.contact_person_name}},\\n\\nMerci pour votre intérêt pour nos services.\\n\\nCordialement,\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}",
                    "en": "Dear {{client.contact_person_name}},\\n\\nThank you for your interest in our services.\\n\\nSincerely,\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}",
                    "ar": "عزيزي/عزيزتي {{client.contact_person_name}}،\\n\\nشكراً لاهتمامك بخدماتنا.\\n\\nمع خالص التقدير،\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}",
                    "tr": "Sayın {{client.contact_person_name}},\\n\\nHizmetlerimize gösterdiğiniz ilgi için teşekkür ederiz.\\n\\nSaygılarımla,\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}",
                    "pt": "Prezado(a) {{client.contact_person_name}},\\n\\nObrigado pelo seu interesse em nossos serviços.\\n\\nAtenciosamente,\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}"
                },
                "description_html": {
                    "fr": "Modèle HTML de salutation générale.", "en": "General greeting HTML template.",
                    "ar": "قالب HTML للتحية العامة.", "tr": "Genel selamlama HTML şablonu.",
                    "pt": "Modelo HTML de saudação geral."
                },
                "description_txt": {
                    "fr": "Modèle TXT de salutation générale.", "en": "General greeting TXT template.",
                    "ar": "قالب TXT للتحية العامة.", "tr": "Genel selamlama TXT şablonu.",
                    "pt": "Modelo TXT de saudação geral."
                }
            },
            {
                "name_key": "EMAIL_FOLLOWUP",
                "display_name_prefix": {"fr": "Suivi de Discussion", "en": "Discussion Follow-up", "ar": "متابعة المناقشة", "tr": "Görüşme Takibi", "pt": "Acompanhamento da Discussão"},
                "subject": {
                    "fr": "Suivi concernant {{project.name}}", "en": "Following up regarding {{project.name}}",
                    "ar": "متابعة بخصوص {{project.name}}", "tr": "{{project.name}} hakkında takip",
                    "pt": "Acompanhamento sobre {{project.name}}"
                },
                "html_content": {
                    "fr": "<p>Cher/Chère {{client.contact_person_name}},</p><p>Ceci est un email de suivi concernant notre récente discussion sur {{project.name}}.</p><p>N'hésitez pas à nous contacter pour toute question.</p><p>Cordialement,</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>",
                    "en": "<p>Dear {{client.contact_person_name}},</p><p>This is a follow-up email regarding our recent discussion about {{project.name}}.</p><p>Please feel free to contact us with any questions.</p><p>Sincerely,</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>",
                    "ar": "<p>عزيزي/عزيزتي {{client.contact_person_name}}،</p><p>هذه رسالة متابعة بخصوص مناقشتنا الأخيرة حول {{project.name}}.</p><p>لا تتردد في الاتصال بنا لأية أسئلة.</p><p>مع خالص التقدير،</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>",
                    "tr": "<p>Sayın {{client.contact_person_name}},</p><p>{{project.name}} hakkındaki son görüşmemizle ilgili bir takip e-postasıdır.</p><p>Herhangi bir sorunuz olursa lütfen bizimle iletişime geçmekten çekinmeyin.</p><p>Saygılarımla,</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>",
                    "pt": "<p>Prezado(a) {{client.contact_person_name}},</p><p>Este é um e-mail de acompanhamento sobre nossa recente discussão sobre {{project.name}}.</p><p>Sinta-se à vontade para entrar em contato conosco com qualquer dúvida.</p><p>Atenciosamente,</p><p>{{seller.personnel.representative_name}}<br>{{seller.company_name}}</p>"
                },
                "txt_content": {
                    "fr": "Cher/Chère {{client.contact_person_name}},\\n\\nCeci est un email de suivi concernant notre récente discussion sur {{project.name}}.\\n\\nN'hésitez pas à nous contacter pour toute question.\\n\\nCordialement,\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}",
                    "en": "Dear {{client.contact_person_name}},\\n\\nThis is a follow-up email regarding our recent discussion about {{project.name}}.\\n\\nPlease feel free to contact us with any questions.\\n\\nSincerely,\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}",
                    "ar": "عزيزي/عزيزتي {{client.contact_person_name}}،\\n\\nهذه رسالة متابعة بخصوص مناقشتنا الأخيرة حول {{project.name}}.\\n\\nلا تتردد في الاتصال بنا لأية أسئلة.\\n\\nمع خالص التقدير،\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}",
                    "tr": "Sayın {{client.contact_person_name}},\\n\\n{{project.name}} hakkındaki son görüşmemizle ilgili bir takip e-postasıdır.\\n\\nHerhangi bir sorunuz olursa lütfen bizimle iletişime geçmekten çekinmeyin.\\n\\nSaygılarımla,\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}",
                    "pt": "Prezado(a) {{client.contact_person_name}},\\n\\nEste é um e-mail de acompanhamento sobre nossa recente discussão sobre {{project.name}}.\\n\\nSinta-se à vontade para entrar em contato conosco com qualquer dúvida.\\n\\nAtenciosamente,\\n{{seller.personnel.representative_name}}\\n{{seller.company_name}}"
                },
                "description_html": {
                    "fr": "Modèle HTML de suivi de discussion.", "en": "Discussion follow-up HTML template.",
                    "ar": "قالب HTML لمتابعة المناقشة.", "tr": "Görüşme takibi HTML şablonu.",
                    "pt": "Modelo HTML de acompanhamento da discussão."
                },
                "description_txt": {
                    "fr": "Modèle TXT de suivi de discussion.", "en": "Discussion follow-up TXT template.",
                    "ar": "قالب TXT لمتابعة المناقشة.", "tr": "Görüşme takibi TXT şablonu.",
                    "pt": "Modelo TXT de acompanhamento da discussão."
                }
            }
        ]


        for lang_code in html_template_languages: # Reuse same list as HTML
            lang_specific_template_dir = os.path.join(templates_root_dir, lang_code)
            os.makedirs(lang_specific_template_dir, exist_ok=True)

            for template_set in default_email_templates_data:
                name_key = template_set['name_key']
                display_name_prefix = template_set['display_name_prefix'].get(lang_code, template_set['display_name_prefix'].get('en', name_key))
                subject_content = template_set['subject'].get(lang_code, template_set['subject'].get('en', f"Message from {{{{seller.company_name}}}}"))

                # HTML Email Part
                base_file_name_html = f"{name_key.lower()}_{lang_code}.html"
                full_path_html = os.path.join(lang_specific_template_dir, base_file_name_html)
                html_content_str = template_set['html_content'].get(lang_code, template_set['html_content'].get('en', "<p>Default HTML content.</p>"))
                description_html_str = template_set['description_html'].get(lang_code, template_set['description_html'].get('en', "Default HTML email template."))
                created_email_html_file = False
                if not os.path.exists(full_path_html):
                    try:
                        with open(full_path_html, "w", encoding="utf-8") as f_html: f_html.write(html_content_str)
                        logging.info(f"Created Email HTML template: {full_path_html}")
                        created_email_html_file = True
                    except IOError as e: logging.error(f"Error creating email HTML file {full_path_html}: {e}")

                db_email_html_id = db_manager.add_default_template_if_not_exists({
                    'template_name': f"{display_name_prefix} (HTML) {lang_code.upper()}", 'template_type': 'EMAIL_BODY_HTML',
                    'language_code': lang_code, 'base_file_name': base_file_name_html,
                    'email_subject_template': subject_content, 'description': description_html_str,
                    'category_id': email_category_id, 'is_default_for_type_lang': False
                })
                if db_email_html_id and created_email_html_file: logging.info(f"Registered new Email HTML template '{base_file_name_html}' in DB.")
                elif not db_email_html_id: logging.warning(f"Failed to register Email HTML template '{base_file_name_html}' in DB.")


                # TXT Email Part
                base_file_name_txt = f"{name_key.lower()}_{lang_code}.txt"
                full_path_txt = os.path.join(lang_specific_template_dir, base_file_name_txt)
                txt_content_str = template_set['txt_content'].get(lang_code, template_set['txt_content'].get('en', "Default TXT content."))
                description_txt_str = template_set['description_txt'].get(lang_code, template_set['description_txt'].get('en', "Default TXT email template."))
                created_email_txt_file = False
                if not os.path.exists(full_path_txt):
                    try:
                        with open(full_path_txt, "w", encoding="utf-8") as f_txt: f_txt.write(txt_content_str)
                        logging.info(f"Created Email TXT template: {full_path_txt}")
                        created_email_txt_file = True
                    except IOError as e: logging.error(f"Error creating email TXT file {full_path_txt}: {e}")

                db_email_txt_id = db_manager.add_default_template_if_not_exists({
                    'template_name': f"{display_name_prefix} (TXT) {lang_code.upper()}", 'template_type': 'EMAIL_BODY_TXT',
                    'language_code': lang_code, 'base_file_name': base_file_name_txt,
                    'email_subject_template': subject_content, 'description': description_txt_str,
                    'category_id': email_category_id, 'is_default_for_type_lang': False
                })
                if db_email_txt_id and created_email_txt_file: logging.info(f"Registered new Email TXT template '{base_file_name_txt}' in DB.")
                elif not db_email_txt_id: logging.warning(f"Failed to register Email TXT template '{base_file_name_txt}' in DB.")

    logging.info("Default template initialization finished.")

# Example of how this might be called by main.py after app object creation
# if __name__ == "__main__": # Or rather, in main.py
# setup_logging() # Call early
# initialize_default_templates(CONFIG, APP_ROOT_DIR)
