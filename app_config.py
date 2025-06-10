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

def get_config_dir():
    config_dir_path = os.path.join(
        QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation),
        CONFIG_DIR_NAME
    )
    os.makedirs(config_dir_path, exist_ok=True)
    return config_dir_path

def get_config_file_path():
    return os.path.join(get_config_dir(), CONFIG_FILE_NAME)

def load_config():
    config_path = get_config_file_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading config: {e}. Using defaults.")

    return {
        "templates_dir": DEFAULT_TEMPLATES_DIR,
        "clients_dir": DEFAULT_CLIENTS_DIR,
        "language": "fr", # Default language
        "smtp_server": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "default_reminder_days": 30,
        "session_timeout_minutes": 30 # Default session timeout
    }

def save_config(config_data):
    try:
        config_path = get_config_file_path()
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        # Need to ensure QMessageBox can be shown if this is called early
        # For now, assuming it's called from a context where QApplication exists
        QMessageBox.warning(None, QCoreApplication.translate("app_config", "Erreur de Configuration"), QCoreApplication.translate("app_config", "Impossible d'enregistrer la configuration: {0}").format(e))

CONFIG = load_config()

# Create default directories based on loaded/default config
os.makedirs(CONFIG["templates_dir"], exist_ok=True)
os.makedirs(CONFIG["clients_dir"], exist_ok=True)
# Translations directory creation should be relative to APP_ROOT_DIR,
# and APP_ROOT_DIR in this file points to app_config.py's location.
# If main_window.py is in the same dir, this is fine.
# If main_window.py is in a parent dir, APP_ROOT_DIR logic might need adjustment
# or this specific makedirs call moved to main_window.py's main_app_entry_point.
# For now, let's assume app_config.py is at the project root.
os.makedirs(os.path.join(APP_ROOT_DIR, "translations"), exist_ok=True)
