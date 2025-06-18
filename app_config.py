# -*- coding: utf-8 -*-
import sys
import os
import json
from PyQt5.QtCore import QStandardPaths, QCoreApplication # For get_config_dir and save_config message
from PyQt5.QtWidgets import QMessageBox # For save_config message

# --- Configuration Constants & Paths ---
CONFIG_DIR_NAME = "ClientDocumentManager"
CONFIG_FILE_NAME = "config.json"
# DATABASE_NAME is handled by db.py (CENTRAL_DATABASE_NAME)
TEMPLATES_SUBDIR = "templates"
CLIENTS_SUBDIR = "clients"

# Template file names (used by main_app_entry_point in main_window.py for default template creation)
SPEC_TECH_TEMPLATE_NAME = "specification_technique_template.xlsx"
PROFORMA_TEMPLATE_NAME = "proforma_template.xlsx"
CONTRAT_VENTE_TEMPLATE_NAME = "contrat_vente_template.xlsx"
PACKING_LISTE_TEMPLATE_NAME = "packing_liste_template.xlsx"

if getattr(sys, 'frozen', False):
    APP_ROOT_DIR = sys._MEIPASS
else:
    # Assuming app_config.py is at the root of the project or alongside main_window.py
    APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_TEMPLATES_DIR = os.path.join(APP_ROOT_DIR, TEMPLATES_SUBDIR)
DEFAULT_CLIENTS_DIR = os.path.join(APP_ROOT_DIR, CLIENTS_SUBDIR)
