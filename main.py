# -*- coding: utf-8 -*-
import sys
import os
import json
# import sqlite3 # Replaced by db_manager
import db as db_manager
from db import DATABASE_NAME as CENTRAL_DATABASE_NAME
import pandas as pd
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QListWidget,
    QFileDialog, QMessageBox, QDialog, QFormLayout, QComboBox,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QInputDialog, QSplitter,
    QCompleter, QTabWidget, QAction, QMenu, QToolBar, QGroupBox,
    QCheckBox, QDateEdit, QSpinBox, QStackedWidget, QListWidgetItem,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QGridLayout
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QColor, QBrush, QPixmap
from PyQt5.QtCore import Qt, QUrl, QStandardPaths, QSettings, QDir, QDate, QTimer
from PyPDF2 import PdfWriter, PdfReader, PdfMerger
from reportlab.pdfgen import canvas
import io
from PyQt5.QtWidgets import QDoubleSpinBox
from PyQt5.QtCore import QTranslator, QLocale, QLibraryInfo, QCoreApplication # Added for translations
from excel_editor import ExcelEditor
from html_editor import HtmlEditor # Added import for HtmlEditor
from PyQt5.QtWidgets import QBoxLayout
from pagedegrde import generate_cover_page_logic, APP_CONFIG as PAGEDEGRDE_APP_CONFIG # For cover page
from docx import Document # Added for .docx support
from datetime import datetime # Ensure datetime is explicitly imported if not already for populate_docx_template
from projectManagement import MainDashboard as ProjectManagementDashboard # Added for integration
import sqlite3

# --- Configuration & Database ---
CONFIG_DIR_NAME = "ClientDocumentManager"
CONFIG_FILE_NAME = "config.json"
DATABASE_NAME = CENTRAL_DATABASE_NAME # Use the central DB name
TEMPLATES_SUBDIR = "templates"
CLIENTS_SUBDIR = "clients"
SPEC_TECH_TEMPLATE_NAME = "specification_technique_template.xlsx"
PROFORMA_TEMPLATE_NAME = "proforma_template.xlsx"
CONTRAT_VENTE_TEMPLATE_NAME = "contrat_vente_template.xlsx"
PACKING_LISTE_TEMPLATE_NAME = "packing_liste_template.xlsx"

if getattr(sys, 'frozen', False):
    APP_ROOT_DIR = sys._MEIPASS
else:
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

# init_database() function (and its call) is removed.
# DATABASE_NAME is now set from CENTRAL_DATABASE_NAME (imported from db.py) at the top.

# Initialize the central database using db_manager
# This should be called once, early in the application startup.
if __name__ == "__main__" or not hasattr(db_manager, '_initialized_main_app'): # Ensure it runs once for the app
    db_manager.initialize_database()
    if __name__ != "__main__": # Avoid setting attribute during test runs if module is imported
        # Use a unique attribute name to avoid conflict if db_manager is imported elsewhere too
        db_manager._initialized_main_app = True

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
        "language": "fr",
        "smtp_server": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password": "",
        "default_reminder_days": 30
    }

def save_config(config_data):
    try:
        config_path = get_config_file_path()
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        QMessageBox.warning(None, QCoreApplication.translate("main", "Erreur de Configuration"), QCoreApplication.translate("main", "Impossible d'enregistrer la configuration: {0}").format(e))

CONFIG = load_config()

os.makedirs(CONFIG["templates_dir"], exist_ok=True)
os.makedirs(CONFIG["clients_dir"], exist_ok=True)
os.makedirs(os.path.join(APP_ROOT_DIR, "translations"), exist_ok=True) # Create translations directory

class ContactDialog(QDialog):
    def __init__(self, client_id=None, contact_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.contact_data = contact_data or {}
        self.setWindowTitle(self.tr("Gestion des Contacts") if not contact_data else self.tr("Modifier Contact"))
        self.setWindowTitle(self.tr("Gestion des Modèles"))
        self.setMinimumSize(600, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit(self.contact_data.get("name", ""))
        layout.addRow(self.tr("Nom complet:"), self.name_input)
        
        self.email_input = QLineEdit(self.contact_data.get("email", ""))
        layout.addRow(self.tr("Email:"), self.email_input)
        
        self.phone_input = QLineEdit(self.contact_data.get("phone", ""))
        layout.addRow(self.tr("Téléphone:"), self.phone_input)
        
        self.position_input = QLineEdit(self.contact_data.get("position", ""))
        layout.addRow(self.tr("Poste:"), self.position_input)
        
        self.primary_check = QCheckBox(self.tr("Contact principal"))
        self.primary_check.setChecked(bool(self.contact_data.get("is_primary", 0)))
        layout.addRow(self.primary_check)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK"))
        button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "email": self.email_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "position": self.position_input.text().strip(),
            "is_primary": 1 if self.primary_check.isChecked() else 0
        }

class TemplateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestion des Modèles")
        self.setMinimumSize(600, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.template_list = QListWidget()
        self.template_list.itemDoubleClicked.connect(self.edit_template)
        layout.addWidget(self.template_list)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton(self.tr("Ajouter Modèle"))
        self.add_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_btn.clicked.connect(self.add_template)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton(self.tr("Modifier"))
        self.edit_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_btn.clicked.connect(self.edit_template)
        btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton(self.tr("Supprimer"))
        self.delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_btn.clicked.connect(self.delete_template)
        btn_layout.addWidget(self.delete_btn)
        
        self.default_btn = QPushButton(self.tr("Définir par Défaut"))
        self.default_btn.setIcon(QIcon.fromTheme("emblem-default"))
        self.default_btn.clicked.connect(self.set_default_template)
        btn_layout.addWidget(self.default_btn)
        
        layout.addLayout(btn_layout)
        self.load_templates()
        
    def load_templates(self):
        self.template_list.clear()
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT template_id, name, language, is_default FROM Templates ORDER BY name, language")
            for row in cursor.fetchall():
                item_text = f"{row[1]} ({row[2]})"
                if row[3]:
                    item_text += f" [{self.tr('Défaut')}]"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, row[0]) 
                self.template_list.addItem(item)
        except sqlite3.Error as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des modèles:\n{str(e)}"))
        finally:
            if conn: conn.close()
            
    def add_template(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Sélectionner un modèle"),
            CONFIG["templates_dir"],
            self.tr("Fichiers Modèles (*.xlsx *.docx *.html);;Fichiers Excel (*.xlsx);;Documents Word (*.docx);;Documents HTML (*.html);;Tous les fichiers (*)")
        )
        if not file_path: return
            
        name, ok = QInputDialog.getText(self, self.tr("Nom du Modèle"), self.tr("Entrez un nom pour ce modèle:"))
        if not ok or not name.strip(): return
            
        languages = ["fr", "en", "ar", "tr", "pt"]
        lang, ok = QInputDialog.getItem(self, self.tr("Langue du Modèle"), self.tr("Sélectionnez la langue:"), languages, 0, False)
        if not ok: return
            
        target_dir = os.path.join(CONFIG["templates_dir"], lang)
        os.makedirs(target_dir, exist_ok=True)
        base_file_name = os.path.basename(file_path) 
        target_path = os.path.join(target_dir, base_file_name) 
        conn = None
        try:
            shutil.copy(file_path, target_path)
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Templates (name, file_name, language, is_default) VALUES (?, ?, ?, 0)",
                (name.strip(), base_file_name, lang) 
            )
            conn.commit()
            self.load_templates()
            QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle ajouté avec succès."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout du modèle:\n{str(e)}"))
        finally:
            if conn: conn.close()
            
    def edit_template(self): 
        item = self.template_list.currentItem()
        if not item: return
        template_id = item.data(Qt.UserRole)
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT file_name, language FROM Templates WHERE template_id = ?", (template_id,))
            result = cursor.fetchone()
            if result:
                # Assuming result[1] is language folder and result[0] is filename
                # The path construction was: os.path.join(CONFIG["templates_dir"], result[1], result[0])
                # This seems incorrect if result[1] is language and result[0] is filename.
                # It should be: os.path.join(CONFIG["templates_dir"], result[1], result[0])
                # Let's verify the database schema or how it's populated.
                # From add_template: target_path = os.path.join(target_dir, base_file_name)
                # target_dir = os.path.join(CONFIG["templates_dir"], lang)
                # So, file_name in DB is just base_file_name. Language is separate.
                # Path should be os.path.join(CONFIG["templates_dir"], result[1] (language), result[0] (file_name))
                # The original code seems to have result[1] as language and result[0] as file_name.
                # This was an error in my reasoning, the original code `os.path.join(CONFIG["templates_dir"], result[1], result[0])`
                # is likely correct if result[1] is the language subfolder and result[0] is the filename.
                # However, the select statement is `SELECT file_name, language ...`
                # So result[0] is file_name, result[1] is language.
                # The path should be os.path.join(CONFIG["templates_dir"], result[1], result[0])
                template_file_path = os.path.join(CONFIG["templates_dir"], result[1], result[0])
                QDesktopServices.openUrl(QUrl.fromLocalFile(template_file_path))
        except sqlite3.Error as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur d'accès au modèle:\n{str(e)}"))
        finally:
            if conn: conn.close()
            
    def delete_template(self):
        item = self.template_list.currentItem()
        if not item: return
        template_id = item.data(Qt.UserRole)
        reply = QMessageBox.question(
            self,
            self.tr("Confirmer Suppression"),
            self.tr("Êtes-vous sûr de vouloir supprimer ce modèle ?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            conn = None
            try:
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT file_name, language FROM Templates WHERE template_id = ?", (template_id,))
                result = cursor.fetchone()
                cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,))
                conn.commit()
                if result:
                    file_path_to_delete = os.path.join(CONFIG["templates_dir"], result[1], result[0]) # lang, filename
                    if os.path.exists(file_path_to_delete): os.remove(file_path_to_delete)
                self.load_templates()
                QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle supprimé avec succès."))
            except Exception as e: 
                QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur de suppression du modèle:\n{str(e)}"))
            finally:
                if conn: conn.close()
                
    def set_default_template(self):
        item = self.template_list.currentItem()
        if not item: return
        template_id = item.data(Qt.UserRole)
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM Templates WHERE template_id = ?", (template_id,))
            name_result = cursor.fetchone()
            if not name_result: return
            base_name = name_result[0] 
            
            cursor.execute("UPDATE Templates SET is_default = 0 WHERE name = ?", (base_name,))
            cursor.execute("UPDATE Templates SET is_default = 1 WHERE template_id = ?", (template_id,))
            conn.commit()
            self.load_templates()
            QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle défini comme modèle par défaut pour sa catégorie et langue."))
        except sqlite3.Error as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de mise à jour du modèle:\n{str(e)}"))
        finally:
            if conn: conn.close()

class ProductDialog(QDialog):
    def __init__(self, client_id, product_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.product_data = product_data or {}
        self.setWindowTitle(self.tr("Ajouter Produit") if not self.product_data else self.tr("Modifier Produit"))
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)

        self.name_input = QLineEdit(self.product_data.get("name", ""))
        layout.addRow(self.tr("Nom du Produit:"), self.name_input)

        self.description_input = QTextEdit(self.product_data.get("description", ""))
        self.description_input.setFixedHeight(80)
        layout.addRow(self.tr("Description:"), self.description_input)

        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0, 1000000)
        self.quantity_input.setValue(self.product_data.get("quantity", 0))
        self.quantity_input.valueChanged.connect(self.update_total_price)
        layout.addRow(self.tr("Quantité:"), self.quantity_input)

        self.unit_price_input = QDoubleSpinBox()
        self.unit_price_input.setRange(0, 10000000)
        self.unit_price_input.setPrefix("€ ") # Currency might need localization if app supports multiple currencies
        self.unit_price_input.setValue(self.product_data.get("unit_price", 0))
        self.unit_price_input.valueChanged.connect(self.update_total_price)
        layout.addRow(self.tr("Prix Unitaire:"), self.unit_price_input)
        
        total_price_title_label = QLabel(self.tr("Prix Total:"))
        self.total_price_label = QLabel("€ 0.00") # Currency might need localization
        self.total_price_label.setStyleSheet("font-weight: bold;")
        layout.addRow(total_price_title_label, self.total_price_label)

        if self.product_data:
            self.update_total_price()

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK"))
        button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def update_total_price(self):
        quantity = self.quantity_input.value()
        unit_price = self.unit_price_input.value()
        total = quantity * unit_price
        self.total_price_label.setText(f"€ {total:.2f}")

    def get_data(self):
        return {
            "client_id": self.client_id,
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "quantity": self.quantity_input.value(),
            "unit_price": self.unit_price_input.value(),
            "total_price": self.quantity_input.value() * self.unit_price_input.value()
        }

class CreateDocumentDialog(QDialog):
    def __init__(self, client_info, config, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.config = config
        self.setWindowTitle(self.tr("Créer des Documents"))
        self.setMinimumSize(600, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Langue sélection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(self.tr("Langue:")))
        self.lang_combo = QComboBox()
        # Assuming selected_languages are codes like "fr", "ar". If they are full names, this needs adjustment.
        self.lang_combo.addItems(self.client_info.get("selected_languages", ["fr"]))
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)
        
        # Liste des templates
        self.templates_list = QListWidget()
        self.templates_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(QLabel(self.tr("Sélectionnez les documents à créer:")))
        layout.addWidget(self.templates_list)
        
        self.load_templates()
        
        # Boutons
        btn_layout = QHBoxLayout()
        create_btn = QPushButton(self.tr("Créer Documents"))
        create_btn.setIcon(QIcon.fromTheme("document-new"))
        create_btn.clicked.connect(self.create_documents)
        btn_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton(self.tr("Annuler"))
        cancel_btn.setIcon(QIcon.fromTheme("dialog-cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
    def load_templates(self):
        self.templates_list.clear()
        # conn = None # Old sqlite3
        try:
            # conn = sqlite3.connect(DATABASE_NAME) # Old sqlite3
            # cursor = conn.cursor() # Old sqlite3
            # cursor.execute("SELECT name, language, file_name FROM Templates ORDER BY name, language") # Old SQL
            # for name, lang, file_name_db in cursor.fetchall(): # Old iteration

            # New logic using db_manager
            # Fetches templates that have a base_file_name, suitable for document generation.
            all_file_templates = db_manager.get_all_file_based_templates()
            if all_file_templates is None: all_file_templates = []

            for template_dict in all_file_templates:
                name = template_dict.get('template_name', 'N/A')
                lang = template_dict.get('language_code', 'N/A')
                base_file_name = template_dict.get('base_file_name', 'N/A')

                item_text = f"{name} ({lang}) - {base_file_name}"
                item = QListWidgetItem(item_text)
                # Store the necessary info for when the document is created
                item.setData(Qt.UserRole, (name, lang, base_file_name))
                self.templates_list.addItem(item)

        except Exception as e: # Catch generic db_manager errors or other issues
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des modèles:\n{0}").format(str(e)))
        # finally:
            # if conn: conn.close() # Old sqlite3
            
    def create_documents(self):
        selected_items = self.templates_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("Aucun document sélectionné"), self.tr("Veuillez sélectionner au moins un document à créer."))
            return
            
        lang = self.lang_combo.currentText() # This gives the language code directly if items are codes
        target_dir = os.path.join(self.client_info["base_folder_path"], lang)
        os.makedirs(target_dir, exist_ok=True)
        
        created_files = []
        
        for item in selected_items:
            db_template_name, db_template_lang, actual_template_filename = item.data(Qt.UserRole)
            
            if not actual_template_filename:
                print(f"Warning: No actual_template_filename for template '{db_template_name}' ({db_template_lang}). Skipping.")
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Nom de fichier manquant pour le modèle '{0}'. Impossible de créer.").format(db_template_name))
                continue

            template_file_found_abs = os.path.join(self.config["templates_dir"], db_template_lang, actual_template_filename)

            if os.path.exists(template_file_found_abs):
                target_path = os.path.join(target_dir, actual_template_filename)
                shutil.copy(template_file_found_abs, target_path)

                if target_path.lower().endswith(".docx"):
                    try:
                        populate_docx_template(target_path, self.client_info)
                        print(f"Populated DOCX: {target_path}")
                    except Exception as e_pop:
                        print(f"Error populating DOCX template {target_path}: {e_pop}")
                        QMessageBox.warning(self, self.tr("Erreur DOCX"), self.tr("Impossible de populer le modèle Word '{0}':\n{1}").format(os.path.basename(target_path), e_pop))
                elif target_path.lower().endswith(".html"):
                    try:
                        with open(target_path, 'r', encoding='utf-8') as f:
                            template_content = f.read()
                        populated_content = HtmlEditor.populate_html_content(template_content, self.client_info)
                        with open(target_path, 'w', encoding='utf-8') as f:
                            f.write(populated_content)
                        print(f"Populated HTML: {target_path}")
                    except Exception as e_html_pop:
                        print(f"Error populating HTML template {target_path}: {e_html_pop}")
                        QMessageBox.warning(self, self.tr("Erreur HTML"), self.tr("Impossible de populer le modèle HTML '{0}':\n{1}").format(os.path.basename(target_path), e_html_pop))

                created_files.append(target_path)
            else:
                print(f"Warning: Template file '{actual_template_filename}' for '{db_template_name}' ({db_template_lang}) not found at {template_file_found_abs}.")
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Fichier modèle '{0}' introuvable pour '{1}'.").format(actual_template_filename, db_template_name))

        if created_files:
            QMessageBox.information(self, self.tr("Documents créés"), self.tr("{0} documents ont été créés avec succès.").format(len(created_files)))
            self.accept()
        else:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Aucun document n'a pu être créé."))

class CompilePdfDialog(QDialog):
    def __init__(self, client_info, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.setWindowTitle(self.tr("Compiler des PDF"))
        self.setMinimumSize(700, 500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(self.tr("Sélectionnez les PDF à compiler:")))
        self.pdf_list = QTableWidget()
        self.pdf_list.setColumnCount(4)
        self.pdf_list.setHorizontalHeaderLabels([
            self.tr("Sélection"), self.tr("Nom du fichier"),
            self.tr("Chemin"), self.tr("Pages (ex: 1-3,5)")
        ])
        self.pdf_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.pdf_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.pdf_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton(self.tr("Ajouter PDF"))
        add_btn.setIcon(QIcon.fromTheme("list-add"))
        add_btn.clicked.connect(self.add_pdf)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton(self.tr("Supprimer"))
        remove_btn.setIcon(QIcon.fromTheme("edit-delete"))
        remove_btn.clicked.connect(self.remove_selected)
        btn_layout.addWidget(remove_btn)
        
        move_up_btn = QPushButton(self.tr("Monter"))
        move_up_btn.setIcon(QIcon.fromTheme("go-up"))
        move_up_btn.clicked.connect(self.move_up)
        btn_layout.addWidget(move_up_btn)
        
        move_down_btn = QPushButton(self.tr("Descendre"))
        move_down_btn.setIcon(QIcon.fromTheme("go-down"))
        move_down_btn.clicked.connect(self.move_down)
        btn_layout.addWidget(move_down_btn)
        
        layout.addLayout(btn_layout)
        
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel(self.tr("Nom du fichier compilé:")))
        self.output_name = QLineEdit(f"{self.tr('compilation')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        options_layout.addWidget(self.output_name)
        layout.addLayout(options_layout)
        
        action_layout = QHBoxLayout()
        compile_btn = QPushButton(self.tr("Compiler PDF"))
        compile_btn.setIcon(QIcon.fromTheme("document-export"))
        compile_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        compile_btn.clicked.connect(self.compile_pdf)
        action_layout.addWidget(compile_btn)
        
        cancel_btn = QPushButton(self.tr("Annuler"))
        cancel_btn.setIcon(QIcon.fromTheme("dialog-cancel"))
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)
        
        layout.addLayout(action_layout)
        
        self.load_existing_pdfs()
        
    def load_existing_pdfs(self):
        client_dir = self.client_info["base_folder_path"]
        pdf_files = []
        
        for root, dirs, files in os.walk(client_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        self.pdf_list.setRowCount(len(pdf_files))
        
        for i, file_path in enumerate(pdf_files):
            chk = QCheckBox()
            chk.setChecked(True)
            self.pdf_list.setCellWidget(i, 0, chk)
            self.pdf_list.setItem(i, 1, QTableWidgetItem(os.path.basename(file_path)))
            self.pdf_list.setItem(i, 2, QTableWidgetItem(file_path))
            pages_edit = QLineEdit("all") # "all" might be better to not translate, or handle translation if it's user input for logic
            pages_edit.setPlaceholderText(self.tr("all ou 1-3,5"))
            self.pdf_list.setCellWidget(i, 3, pages_edit)
    
    def add_pdf(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Sélectionner des PDF"), "", self.tr("Fichiers PDF (*.pdf)"))
        if not file_paths:
            return
            
        current_row_count = self.pdf_list.rowCount()
        self.pdf_list.setRowCount(current_row_count + len(file_paths))
        
        for i, file_path in enumerate(file_paths):
            row = current_row_count + i
            chk = QCheckBox()
            chk.setChecked(True)
            self.pdf_list.setCellWidget(row, 0, chk)
            self.pdf_list.setItem(row, 1, QTableWidgetItem(os.path.basename(file_path)))
            self.pdf_list.setItem(row, 2, QTableWidgetItem(file_path))
            pages_edit = QLineEdit("all")
            pages_edit.setPlaceholderText(self.tr("all ou 1-3,5"))
            self.pdf_list.setCellWidget(row, 3, pages_edit)
    
    def remove_selected(self):
        selected_rows = set(index.row() for index in self.pdf_list.selectedIndexes())
        for row in sorted(selected_rows, reverse=True):
            self.pdf_list.removeRow(row)
    
    def move_up(self):
        current_row = self.pdf_list.currentRow()
        if current_row > 0:
            self.swap_rows(current_row, current_row - 1)
            self.pdf_list.setCurrentCell(current_row - 1, 0)
    
    def move_down(self):
        current_row = self.pdf_list.currentRow()
        if current_row < self.pdf_list.rowCount() - 1:
            self.swap_rows(current_row, current_row + 1)
            self.pdf_list.setCurrentCell(current_row + 1, 0)
    
    def swap_rows(self, row1, row2):
        for col in range(self.pdf_list.columnCount()):
            item1 = self.pdf_list.takeItem(row1, col)
            item2 = self.pdf_list.takeItem(row2, col)
            
            self.pdf_list.setItem(row1, col, item2)
            self.pdf_list.setItem(row2, col, item1)
            
        # Swap des widgets
        widget1 = self.pdf_list.cellWidget(row1, 0)
        widget3 = self.pdf_list.cellWidget(row1, 3)
        widget2 = self.pdf_list.cellWidget(row2, 0)
        widget4 = self.pdf_list.cellWidget(row2, 3)
        
        self.pdf_list.setCellWidget(row1, 0, widget2)
        self.pdf_list.setCellWidget(row1, 3, widget4)
        self.pdf_list.setCellWidget(row2, 0, widget1)
        self.pdf_list.setCellWidget(row2, 3, widget3)
    
    def compile_pdf(self):
        merger = PdfMerger()
        output_name = self.output_name.text().strip()
        if not output_name:
            QMessageBox.warning(self, self.tr("Nom manquant"), self.tr("Veuillez spécifier un nom de fichier pour la compilation."))
            return
            
        if not output_name.lower().endswith('.pdf'):
            output_name += '.pdf'
            
        output_path = os.path.join(self.client_info["base_folder_path"], output_name)
        
        cover_path = self.create_cover_page()
        if cover_path:
            merger.append(cover_path)
        
        for row in range(self.pdf_list.rowCount()):
            chk = self.pdf_list.cellWidget(row, 0)
            if chk and chk.isChecked():
                file_path = self.pdf_list.item(row, 2).text()
                pages_spec = self.pdf_list.cellWidget(row, 3).text().strip()
                
                try:
                    if pages_spec.lower() == "all" or not pages_spec: # "all" might not need translation if it's a keyword for logic
                        merger.append(file_path)
                    else:
                        pages = []
                        for part in pages_spec.split(','):
                            if '-' in part:
                                start, end = part.split('-')
                                pages.extend(range(int(start), int(end)+1)) # Assuming page numbers are universal
                            else:
                                pages.append(int(part))
                        merger.append(file_path, pages=[p-1 for p in pages]) # PyPDF2 pages are 0-indexed
                except Exception as e:
                    QMessageBox.warning(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout de {0}:\n{1}").format(os.path.basename(file_path), str(e)))
        
        try:
            with open(output_path, 'wb') as f:
                merger.write(f)
            
            if cover_path and os.path.exists(cover_path):
                os.remove(cover_path)
                
            QMessageBox.information(self, self.tr("Compilation réussie"), self.tr("Le PDF compilé a été sauvegardé dans:\n{0}").format(output_path))
            
            self.offer_download_or_email(output_path)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la compilation du PDF:\n{0}").format(str(e)))
    
    def create_cover_page(self):
        # Many strings here are for PDF content, might need careful consideration if they should be app-translatable
        # or document-language specific. For now, assuming they are part of the document's content language.
        # If some are UI-related (e.g. default author if not found), they could be tr().
        config_dict = {
            'title': self.tr("Compilation de Documents - Projet: {0}").format(self.client_info.get('project_identifier', self.tr('N/A'))),
            'subtitle': self.tr("Client: {0}").format(self.client_info.get('client_name', self.tr('N/A'))),
            'author': self.client_info.get('company_name', PAGEDEGRDE_APP_CONFIG.get('default_institution', self.tr('Votre Entreprise'))),
            'institution': "",
            'department': "",
            'doc_type': self.tr("Compilation de Documents"),
            'date': datetime.now().strftime('%d/%m/%Y %H:%M'), # Date format might need localization
            'version': "1.0",

            'font_name': PAGEDEGRDE_APP_CONFIG.get('default_font', 'Helvetica'),
            'font_size_title': 20,
            'font_size_subtitle': 16,
            'font_size_author': 10,
            'text_color': PAGEDEGRDE_APP_CONFIG.get('default_text_color', '#000000'),

            'template_style': 'Moderne',
            'show_horizontal_line': True,
            'line_y_position_mm': 140,

            'logo_data': None,
            'logo_width_mm': 40,
            'logo_height_mm': 40,
            'logo_x_mm': 25,
            'logo_y_mm': 297 - 25 - 40,

            'margin_top': 25,
            'margin_bottom': 25,
            'margin_left': 20,
            'margin_right': 20,

            'footer_text': self.tr("Document compilé le {0}").format(datetime.now().strftime('%d/%m/%Y')) # Date format
        }

        logo_path = os.path.join(APP_ROOT_DIR, "logo.png")
        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f_logo:
                    config_dict['logo_data'] = f_logo.read()
            except Exception as e_logo:
                print(self.tr("Erreur chargement logo.png: {0}").format(e_logo))

        try:
            pdf_bytes = generate_cover_page_logic(config_dict)
            base_temp_dir = self.client_info.get("base_folder_path", QDir.tempPath())
            temp_cover_filename = f"cover_page_generated_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.pdf" # Filename not user-facing
            temp_cover_path = os.path.join(base_temp_dir, temp_cover_filename)

            with open(temp_cover_path, "wb") as f:
                f.write(pdf_bytes)
            return temp_cover_path

        except Exception as e:
            print(self.tr("Erreur lors de la génération de la page de garde via pagedegrde: {0}").format(e))
            QMessageBox.warning(self, self.tr("Erreur Page de Garde"), self.tr("Impossible de générer la page de garde personnalisée: {0}").format(e))
            return None

    def offer_download_or_email(self, pdf_path):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self.tr("Compilation réussie"))
        msg_box.setText(self.tr("Le PDF compilé a été sauvegardé dans:\n{0}").format(pdf_path))
        
        download_btn = msg_box.addButton(self.tr("Télécharger"), QMessageBox.ActionRole)
        email_btn = msg_box.addButton(self.tr("Envoyer par email"), QMessageBox.ActionRole)
        close_btn = msg_box.addButton(self.tr("Fermer"), QMessageBox.RejectRole) # Standard button, might be translated by Qt
        
        msg_box.exec_()
        
        if msg_box.clickedButton() == download_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        elif msg_box.clickedButton() == email_btn:
            self.send_email(pdf_path)
    
    def send_email(self, pdf_path):
        primary_email = None
        # conn = None # Old sqlite3
        try:
            # conn = sqlite3.connect(DATABASE_NAME) # Old sqlite3
            # cursor = conn.cursor() # Old sqlite3
            # cursor.execute("SELECT email FROM Contacts WHERE client_id = ? AND is_primary = 1",
            #               (self.client_info["client_id"],)) # Old: client_id was on Contacts table
            # result = cursor.fetchone() # Old sqlite3
            # if result: # Old sqlite3
            #     primary_email = result[0] # Old sqlite3

            # New logic using db_manager
            # self.client_info["client_id"] should be the client_uuid
            client_uuid = self.client_info.get("client_id")
            if client_uuid:
                contacts_for_client = db_manager.get_contacts_for_client(client_uuid)
                if contacts_for_client:
                    for contact in contacts_for_client:
                        if contact.get('is_primary_for_client'): # This field comes from ClientContacts join
                            primary_email = contact.get('email')
                            break # Found primary, no need to check further

        except Exception as e: # Catch generic db_manager or other errors
            print(self.tr("Erreur DB recherche email: {0}").format(str(e)))
        # finally:
            # if conn: conn.close() # Old sqlite3
        
        email, ok = QInputDialog.getText(
            self, 
            self.tr("Envoyer par email"),
            self.tr("Adresse email du destinataire:"),
            text=primary_email or ""
        )
        
        if not ok or not email.strip():
            return
            
        config = load_config()
        if not config.get("smtp_server") or not config.get("smtp_user"):
            QMessageBox.warning(self, self.tr("Configuration manquante"), self.tr("Veuillez configurer les paramètres SMTP dans les paramètres de l'application."))
            return
            
        msg = MIMEMultipart()
        msg['From'] = config["smtp_user"]
        msg['To'] = email
        # Subject and body content are email content, not UI, so direct tr() might be too simple.
        # These might need a more complex templating system if they need to be multilingual based on recipient preference.
        # For now, translating as if it's for the user sending the email.
        msg['Subject'] = self.tr("Documents compilés - {0}").format(self.client_info['client_name'])
        
        body = self.tr("Bonjour,\n\nVeuillez trouver ci-joint les documents compilés pour le projet {0}.\n\nCordialement,\nVotre équipe").format(self.client_info['project_identifier'])
        msg.attach(MIMEText(body, 'plain'))
        
        with open(pdf_path, 'rb') as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
        msg.attach(part)
        
        try:
            server = smtplib.SMTP(config["smtp_server"], config.get("smtp_port", 587))
            if config.get("smtp_port", 587) == 587:
                server.starttls()
            server.login(config["smtp_user"], config["smtp_password"])
            server.send_message(msg)
            server.quit()
            QMessageBox.information(self, self.tr("Email envoyé"), self.tr("Le document a été envoyé avec succès."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur d'envoi"), self.tr("Erreur lors de l'envoi de l'email:\n{0}").format(str(e)))

class ClientWidget(QWidget):
    def __init__(self, client_info, config, parent=None): 
        super().__init__(parent)
        self.client_info = client_info
        self.config = config 
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        header = QLabel(f"<h2>{self.client_info['client_name']}</h2>") # Client name is data, not UI text
        header.setStyleSheet("color: #2c3e50;") 
        layout.addWidget(header)
        
        action_layout = QHBoxLayout()
        
        self.create_docs_btn = QPushButton(self.tr("Créer Documents"))
        self.create_docs_btn.setIcon(QIcon.fromTheme("document-new"))
        self.create_docs_btn.setStyleSheet("background-color: #3498db; color: white;")
        self.create_docs_btn.clicked.connect(self.open_create_docs_dialog)
        action_layout.addWidget(self.create_docs_btn)
        
        self.compile_pdf_btn = QPushButton(self.tr("Compiler PDF"))
        self.compile_pdf_btn.setIcon(QIcon.fromTheme("document-export"))
        self.compile_pdf_btn.setStyleSheet("background-color: #27ae60; color: white;")
        self.compile_pdf_btn.clicked.connect(self.open_compile_pdf_dialog)
        action_layout.addWidget(self.compile_pdf_btn)
        
        layout.addLayout(action_layout)
        
        status_layout = QHBoxLayout()
        status_label = QLabel(self.tr("Statut:"))
        status_layout.addWidget(status_label)
        self.status_combo = QComboBox()
        self.load_statuses() # Statuses themselves are data, but "En cours" default might need thought
        self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours"))) # Default status
        self.status_combo.currentTextChanged.connect(self.update_client_status)
        status_layout.addWidget(self.status_combo)
        layout.addLayout(status_layout)
        
        details_layout = QFormLayout()
        details_layout.setLabelAlignment(Qt.AlignRight)
        # Labels are UI text, values are data
        details_data = [
            (self.tr("ID Projet:"), self.client_info.get("project_identifier", self.tr("N/A"))),
            (self.tr("Pays:"), self.client_info.get("country", self.tr("N/A"))),
            (self.tr("Ville:"), self.client_info.get("city", self.tr("N/A"))),
            (self.tr("Besoin Principal:"), self.client_info.get("need", self.tr("N/A"))),
            (self.tr("Prix Final:"), f"{self.client_info.get('price', 0)} €"), # Currency format
            (self.tr("Date Création:"), self.client_info.get("creation_date", self.tr("N/A"))),
            (self.tr("Chemin Dossier:"), f"<a href='file:///{self.client_info['base_folder_path']}'>{self.client_info['base_folder_path']}</a>")
        ]
        for label_text, value_text in details_data:
            label_widget = QLabel(label_text)
            value_widget = QLabel(value_text)
            value_widget.setOpenExternalLinks(True)
            value_widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
            details_layout.addRow(label_widget, value_widget)
        layout.addLayout(details_layout)
        
        notes_group = QGroupBox(self.tr("Notes"))
        notes_layout = QVBoxLayout(notes_group)
        self.notes_edit = QTextEdit(self.client_info.get("notes", ""))
        self.notes_edit.setPlaceholderText(self.tr("Ajoutez des notes sur ce client..."))
        self.notes_edit.textChanged.connect(self.save_client_notes) 
        notes_layout.addWidget(self.notes_edit)
        layout.addWidget(notes_group)
        
        self.tab_widget = QTabWidget()
        
        docs_tab = QWidget()
        docs_layout = QVBoxLayout(docs_tab)
        
        self.doc_table = QTableWidget()
        self.doc_table.setColumnCount(5)
        self.doc_table.setHorizontalHeaderLabels([
            self.tr("Nom"), self.tr("Type"), self.tr("Langue"),
            self.tr("Date"), self.tr("Actions")
        ])
        self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.doc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.doc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        docs_layout.addWidget(self.doc_table)
        
        doc_btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton(self.tr("Actualiser"))
        refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_btn.clicked.connect(self.populate_doc_table)
        doc_btn_layout.addWidget(refresh_btn)
        
        open_btn = QPushButton(self.tr("Ouvrir"))
        open_btn.setIcon(QIcon.fromTheme("document-open"))
        open_btn.clicked.connect(self.open_selected_doc)
        doc_btn_layout.addWidget(open_btn)
        
        delete_btn = QPushButton(self.tr("Supprimer"))
        delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
        delete_btn.clicked.connect(self.delete_selected_doc)
        doc_btn_layout.addWidget(delete_btn)
        
        docs_layout.addLayout(doc_btn_layout)
        self.tab_widget.addTab(docs_tab, self.tr("Documents"))
        
        contacts_tab = QWidget()
        contacts_layout = QVBoxLayout(contacts_tab)
        self.contacts_list = QListWidget()
        self.contacts_list.setAlternatingRowColors(True)
        self.contacts_list.itemDoubleClicked.connect(self.edit_contact)
        contacts_layout.addWidget(self.contacts_list)
        
        contacts_btn_layout = QHBoxLayout()
        self.add_contact_btn = QPushButton(self.tr("Ajouter Contact"))
        self.add_contact_btn.setIcon(QIcon.fromTheme("contact-new"))
        self.add_contact_btn.clicked.connect(self.add_contact)
        contacts_btn_layout.addWidget(self.add_contact_btn)
        
        self.edit_contact_btn = QPushButton(self.tr("Modifier Contact"))
        self.edit_contact_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_contact_btn.clicked.connect(self.edit_contact)
        contacts_btn_layout.addWidget(self.edit_contact_btn)
        
        self.remove_contact_btn = QPushButton(self.tr("Supprimer Contact"))
        self.remove_contact_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_contact_btn.clicked.connect(self.remove_contact)
        contacts_btn_layout.addWidget(self.remove_contact_btn)
        
        contacts_layout.addLayout(contacts_btn_layout)
        self.tab_widget.addTab(contacts_tab, self.tr("Contacts"))

        products_tab = QWidget()
        products_layout = QVBoxLayout(products_tab)
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6) # Adjusted for ID
        self.products_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Nom Produit"), self.tr("Description"),
            self.tr("Qté"), self.tr("Prix Unitaire"), self.tr("Prix Total")
        ])
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.hideColumn(0) # Hide ID column by default
        products_layout.addWidget(self.products_table)
        
        products_btn_layout = QHBoxLayout()
        self.add_product_btn = QPushButton(self.tr("Ajouter Produit"))
        self.add_product_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_product_btn.clicked.connect(self.add_product)
        products_btn_layout.addWidget(self.add_product_btn)
        
        self.edit_product_btn = QPushButton(self.tr("Modifier Produit"))
        self.edit_product_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_product_btn.clicked.connect(self.edit_product)
        products_btn_layout.addWidget(self.edit_product_btn)
        
        self.remove_product_btn = QPushButton(self.tr("Supprimer Produit"))
        self.remove_product_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_product_btn.clicked.connect(self.remove_product)
        products_btn_layout.addWidget(self.remove_product_btn)
        
        products_layout.addLayout(products_btn_layout)
        self.tab_widget.addTab(products_tab, self.tr("Produits"))
        
        layout.addWidget(self.tab_widget)
        
        self.populate_doc_table()
        self.load_contacts()
        self.load_products()

    def load_statuses(self):
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT status_name FROM StatusSettings")
            for status_row in cursor.fetchall(): 
                # Potentially translate status_row[0] if they are meant to be translated in UI
                # For now, assuming status names from DB are either keys or already in target language
                self.status_combo.addItem(status_row[0])
        except sqlite3.Error as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des statuts:\n{0}").format(str(e)))
        finally:
            if conn: conn.close()
            
    def update_client_status(self, status_text): 
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE Clients SET status = ? WHERE client_id = ?", (status_text, self.client_info["client_id"]))
            conn.commit()
            self.client_info["status"] = status_text 
        except sqlite3.Error as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de mise à jour du statut:\n{0}").format(str(e)))
        finally:
            if conn: conn.close()
            
    def save_client_notes(self): 
        notes = self.notes_edit.toPlainText()
        conn = None
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE Clients SET notes = ? WHERE client_id = ?", (notes, self.client_info["client_id"]))
            conn.commit()
            self.client_info["notes"] = notes 
        except sqlite3.Error as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de sauvegarde des notes:\n{0}").format(str(e)))
        finally:
            if conn: conn.close()
            
    def populate_doc_table(self):
        self.doc_table.setRowCount(0)
        client_path = self.client_info["base_folder_path"] 
        if not os.path.exists(client_path):
            return
            
        row = 0
        for lang in self.client_info.get("selected_languages", ["fr"]):
            lang_dir = os.path.join(client_path, lang)
            if not os.path.exists(lang_dir):
                continue
                
            for file_name in os.listdir(lang_dir):
                if file_name.endswith(('.xlsx', '.pdf', '.docx', '.html')):
                    file_path = os.path.join(lang_dir, file_name)
                    name_item = QTableWidgetItem(file_name)
                    name_item.setData(Qt.UserRole, file_path)

                    file_type_str = ""
                    if file_name.lower().endswith('.xlsx'):
                        file_type_str = self.tr("Excel")
                    elif file_name.lower().endswith('.docx'):
                        file_type_str = self.tr("Word")
                    elif file_name.lower().endswith('.html'):
                        file_type_str = self.tr("HTML")
                    else:
                        file_type_str = self.tr("PDF")
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M') # Date format maybe locale specific
                    
                    self.doc_table.insertRow(row)
                    self.doc_table.setItem(row, 0, name_item)
                    self.doc_table.setItem(row, 1, QTableWidgetItem(file_type_str))
                    self.doc_table.setItem(row, 2, QTableWidgetItem(lang)) # lang code, not UI text
                    self.doc_table.setItem(row, 3, QTableWidgetItem(mod_time))
                    
                    action_widget = QWidget()
                    action_layout = QHBoxLayout(action_widget)
                    action_layout.setContentsMargins(0, 0, 0, 0)
                    
                    open_btn_i = QPushButton()
                    open_btn_i.setIcon(QIcon.fromTheme("document-open"))
                    open_btn_i.setToolTip(self.tr("Ouvrir"))
                    open_btn_i.setFixedSize(30, 30)
                    open_btn_i.clicked.connect(lambda _, p=file_path: self.open_document(p))
                    action_layout.addWidget(open_btn_i)
                    
                    if file_name.endswith('.xlsx') or file_name.endswith('.html'): # Allow edit for HTML too
                        edit_btn_i = QPushButton()
                        edit_btn_i.setIcon(QIcon.fromTheme("document-edit"))
                        edit_btn_i.setToolTip(self.tr("Éditer"))
                        edit_btn_i.setFixedSize(30, 30)
                        # For Excel, open_document handles ExcelEditor. For HTML, it handles HtmlEditor.
                        edit_btn_i.clicked.connect(lambda _, p=file_path: self.open_document(p))
                        action_layout.addWidget(edit_btn_i)
                    
                    delete_btn_i = QPushButton()
                    delete_btn_i.setIcon(QIcon.fromTheme("edit-delete"))
                    delete_btn_i.setToolTip(self.tr("Supprimer"))
                    delete_btn_i.setFixedSize(30, 30)
                    delete_btn_i.clicked.connect(lambda _, p=file_path: self.delete_document(p))
                    action_layout.addWidget(delete_btn_i)
                    
                    self.doc_table.setCellWidget(row, 4, action_widget)
                    row += 1

    def open_create_docs_dialog(self):
        dialog = CreateDocumentDialog(self.client_info, self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.populate_doc_table()
            
    def open_compile_pdf_dialog(self):
        dialog = CompilePdfDialog(self.client_info, self)
        dialog.exec_()
            
    def open_selected_doc(self):
        selected_row = self.doc_table.currentRow()
        if selected_row >= 0:
            file_path_item = self.doc_table.item(selected_row, 0) # Name item stores path in UserRole
            if file_path_item:
                file_path = file_path_item.data(Qt.UserRole)
                if file_path and os.path.exists(file_path):
                    self.open_document(file_path)
                
    def delete_selected_doc(self):
        selected_row = self.doc_table.currentRow()
        if selected_row >= 0:
            file_path_item = self.doc_table.item(selected_row, 0) # Name item stores path
            if file_path_item:
                file_path = file_path_item.data(Qt.UserRole)
                if file_path and os.path.exists(file_path):
                    self.delete_document(file_path)
                
    def open_document(self, file_path):
        if os.path.exists(file_path):
            try:
                # Data passed to editors is data, not UI text.
                editor_client_data = {
                    "Nom du client": self.client_info.get("client_name", ""),
                    "Besoin": self.client_info.get("need", ""),
                    "price": self.client_info.get("price", 0),
                    "project_identifier": self.client_info.get("project_identifier", ""),
                    "company_name": self.client_info.get("company_name", ""),
                    "country": self.client_info.get("country", ""),
                    "city": self.client_info.get("city", ""),
                }
                if file_path.lower().endswith('.xlsx'):
                    editor = ExcelEditor(file_path, client_data=editor_client_data, parent=self)
                    editor.exec_()
                    self.populate_doc_table()
                elif file_path.lower().endswith('.html'):
                    html_editor_dialog = HtmlEditor(file_path, client_data=editor_client_data, parent=self)
                    html_editor_dialog.exec_()
                    self.populate_doc_table()
                elif file_path.lower().endswith(('.docx', '.pdf')):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                else:
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur Ouverture Fichier"), self.tr("Impossible d'ouvrir le fichier:\n{0}").format(str(e)))
        else:
            QMessageBox.warning(self, self.tr("Fichier Introuvable"), self.tr("Le fichier n'existe plus."))
            self.populate_doc_table()
            
    def delete_document(self, file_path):
        if not os.path.exists(file_path):
            return
            
        reply = QMessageBox.question(
            self, 
            self.tr("Confirmer la suppression"),
            self.tr("Êtes-vous sûr de vouloir supprimer le fichier {0} ?").format(os.path.basename(file_path)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                self.populate_doc_table()
                QMessageBox.information(self, self.tr("Fichier supprimé"), self.tr("Le fichier a été supprimé avec succès."))
            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de supprimer le fichier:\n{0}").format(str(e)))
    
    def load_contacts(self):
        self.contacts_list.clear()
        client_uuid = self.client_info.get("client_id")
        if not client_uuid: return

        try:
            # db_manager.get_contacts_for_client returns list of dicts with contact details
            # and ClientContacts fields like is_primary_for_client, client_contact_id
            contacts = db_manager.get_contacts_for_client(client_uuid)
            if contacts is None: contacts = []

            for contact in contacts:
                contact_text = f"{contact.get('name', 'N/A')}"
                if contact.get('phone'): contact_text += f" ({contact.get('phone')})"
                if contact.get('is_primary_for_client'): contact_text += f" [{self.tr('Principal')}]"

                item = QListWidgetItem(contact_text)
                # Store both contact_id (from Contacts table) and client_contact_id (from ClientContacts link table)
                item.setData(Qt.UserRole, {'contact_id': contact.get('contact_id'),
                                           'client_contact_id': contact.get('client_contact_id'),
                                           'is_primary': contact.get('is_primary_for_client')})
                self.contacts_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des contacts:\n{0}").format(str(e)))
            
    def add_contact(self):
        client_uuid = self.client_info.get("client_id")
        if not client_uuid: return

        dialog = ContactDialog(client_uuid, parent=self) # Pass client_id for context if needed by dialog
        if dialog.exec_() == QDialog.Accepted:
            contact_form_data = dialog.get_data() # name, email, phone, position, is_primary

            try:
                # Step 1: Add or get existing contact from global Contacts table
                # Check if contact with this email already exists
                existing_contact = db_manager.get_contact_by_email(contact_form_data['email'])
                contact_id_to_link = None

                if existing_contact:
                    contact_id_to_link = existing_contact['contact_id']
                    # Optionally, update existing contact's details if they differ (name, phone, position)
                    update_data = {k: v for k, v in contact_form_data.items() if k in ['name', 'phone', 'position'] and v != existing_contact.get(k)}
                    if update_data : db_manager.update_contact(contact_id_to_link, update_data)
                else:
                    new_contact_id = db_manager.add_contact({
                        'name': contact_form_data['name'], 'email': contact_form_data['email'],
                        'phone': contact_form_data['phone'], 'position': contact_form_data['position']
                    })
                    if new_contact_id:
                        contact_id_to_link = new_contact_id
                    else:
                        QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer le nouveau contact global."))
                        return

                # Step 2: Link contact to client in ClientContacts
                if contact_id_to_link:
                    if contact_form_data['is_primary']:
                        # Unset other primary contacts for this client
                        client_contacts = db_manager.get_contacts_for_client(client_uuid)
                        if client_contacts:
                            for cc in client_contacts:
                                if cc['is_primary_for_client']:
                                    db_manager.update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})

                    link_id = db_manager.link_contact_to_client(
                        client_uuid, contact_id_to_link,
                        is_primary=contact_form_data['is_primary']
                    )
                    if link_id:
                        self.load_contacts()
                    else:
                        QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de lier le contact au client. Le lien existe peut-être déjà."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du contact:\n{0}").format(str(e)))
                
    def edit_contact(self):
        item = self.contacts_list.currentItem()
        if not item: return

        item_data = item.data(Qt.UserRole)
        contact_id = item_data.get('contact_id')
        client_contact_id = item_data.get('client_contact_id') # ID of the link
        # is_currently_primary = item_data.get('is_primary')

        client_uuid = self.client_info.get("client_id")
        if not contact_id or not client_uuid: return

        try:
            contact_details = db_manager.get_contact_by_id(contact_id)
            if contact_details:
                # Need to also fetch is_primary status for this specific client-contact link
                current_link_info = None
                client_contacts_for_client = db_manager.get_contacts_for_client(client_uuid)
                if client_contacts_for_client:
                    for cc_link in client_contacts_for_client:
                        if cc_link['contact_id'] == contact_id:
                            current_link_info = cc_link
                            break

                is_primary_for_this_client = current_link_info['is_primary_for_client'] if current_link_info else False

                dialog_data = {
                    "name": contact_details.get('name'), "email": contact_details.get('email'),
                    "phone": contact_details.get('phone'), "position": contact_details.get('position'),
                    "is_primary": is_primary_for_this_client
                }

                dialog = ContactDialog(client_uuid, dialog_data, parent=self)
                if dialog.exec_() == QDialog.Accepted:
                    new_form_data = dialog.get_data()

                    # Update global contact details
                    db_manager.update_contact(contact_id, {
                        'name': new_form_data['name'], 'email': new_form_data['email'],
                        'phone': new_form_data['phone'], 'position': new_form_data['position']
                    })

                    # Update is_primary status for this client link
                    if new_form_data['is_primary'] and not is_primary_for_this_client:
                        # Unset other primary contacts for this client
                        if client_contacts_for_client: # re-fetch or use from above
                            for cc in client_contacts_for_client:
                                if cc['contact_id'] != contact_id and cc['is_primary_for_client']:
                                    db_manager.update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})
                        db_manager.update_client_contact_link(client_contact_id, {'is_primary_for_client': True})
                    elif not new_form_data['is_primary'] and is_primary_for_this_client:
                        db_manager.update_client_contact_link(client_contact_id, {'is_primary_for_client': False})

                    self.load_contacts()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de modification du contact:\n{0}").format(str(e)))
            
    def remove_contact(self): # This should unlink contact from client. Optionally delete global contact if not linked elsewhere.
        item = self.contacts_list.currentItem()
        if not item: return

        item_data = item.data(Qt.UserRole)
        contact_id = item_data.get('contact_id')
        client_contact_id = item_data.get('client_contact_id')
        client_uuid = self.client_info.get("client_id")

        if not client_contact_id or not client_uuid or not contact_id: return

        contact_name = db_manager.get_contact_by_id(contact_id)['name'] if db_manager.get_contact_by_id(contact_id) else "Inconnu"

        reply = QMessageBox.question(self, self.tr("Confirmer Suppression Lien"),
                                     self.tr("Êtes-vous sûr de vouloir supprimer le lien vers ce contact ({0}) pour ce client ?\nLe contact global ne sera pas supprimé.").format(contact_name),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                unlinked = db_manager.unlink_contact_from_client(client_uuid, contact_id) # Uses client_id and contact_id
                if unlinked:
                    self.load_contacts()
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du lien contact-client."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du lien contact:\n{0}").format(str(e)))
                
    def add_product(self):
        client_uuid = self.client_info.get("client_id")
        if not client_uuid: return

        # ProductDialog collects name, desc, qty, unit_price.
        # These will be used to first find/create a global product, then link it.
        dialog = ProductDialog(client_uuid, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            form_data = dialog.get_data() # Contains name, description, quantity, unit_price

            try:
                # Step 1: Find or Create Global Product
                # For simplicity, we'll assume product_name is unique for finding.
                # A more robust solution might involve a product selection dialog from global products.
                global_product = db_manager.get_product_by_name(form_data['name']) # Needs get_product_by_name
                global_product_id = None

                if global_product:
                    global_product_id = global_product['product_id']
                    # Optionally update global product's description or base_unit_price if form_data differs significantly
                    # For now, we use the existing global product's base price if no override.
                else:
                    new_global_product_id = db_manager.add_product({
                        'product_name': form_data['name'],
                        'description': form_data['description'],
                        'base_unit_price': form_data['unit_price'] # Use dialog unit_price as base if new
                        # 'category', 'unit_of_measure' could be added to ProductDialog if needed
                    })
                    if new_global_product_id:
                        global_product_id = new_global_product_id
                    else:
                        QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer le produit global."))
                        return

                # Step 2: Link Product to Client (via ClientProjectProducts, project_id=None for client-general)
                if global_product_id:
                    link_data = {
                        'client_id': client_uuid,
                        'project_id': None, # Assuming client-level product for now
                        'product_id': global_product_id,
                        'quantity': form_data['quantity'],
                        # unit_price_override will be form_data['unit_price'] if it's different from global base, else None
                        'unit_price_override': form_data['unit_price']
                                              if not global_product or form_data['unit_price'] != global_product.get('base_unit_price')
                                              else None
                    }
                    # add_product_to_client_or_project calculates total_price
                    cpp_id = db_manager.add_product_to_client_or_project(link_data)
                    if cpp_id:
                        self.load_products()
                    else:
                        QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de lier le produit au client."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du produit:\n{0}").format(str(e)))

    def edit_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row < 0: return
        
        # Assuming the hidden ID column (0) stores client_project_product_id
        cpp_id_item = self.products_table.item(selected_row, 0)
        if not cpp_id_item: return
        client_project_product_id = cpp_id_item.data(Qt.UserRole) # This ID is for ClientProjectProducts table

        client_uuid = self.client_info.get("client_id")

        try:
            # Fetch the current linked product details (quantity, price_override)
            # get_products_for_client_or_project returns a list, we need the specific one by cpp_id
            # This requires a new function: db_manager.get_client_project_product_by_id(cpp_id)
            linked_product_details = db_manager.get_client_project_product_by_id(client_project_product_id)

            if linked_product_details:
                # ProductDialog expects 'name', 'description', 'quantity', 'unit_price'
                # 'name' and 'description' come from the global Product table (joined in linked_product_details)
                # 'quantity' comes from ClientProjectProducts
                # 'unit_price' for dialog should be the effective price (override or base)
                effective_unit_price = linked_product_details.get('unit_price_override', linked_product_details.get('base_unit_price'))

                dialog_data = {
                    "name": linked_product_details.get('product_name', ''), # From joined Products table
                    "description": linked_product_details.get('product_description', ''), # From joined Products table
                    "quantity": linked_product_details.get('quantity', 0),
                    "unit_price": effective_unit_price
                }

                dialog = ProductDialog(client_uuid, dialog_data, parent=self)
                if dialog.exec_() == QDialog.Accepted:
                    form_data = dialog.get_data()

                    update_link_data = {
                        'quantity': form_data['quantity'],
                        'unit_price_override': form_data['unit_price']
                                              if form_data['unit_price'] != linked_product_details.get('base_unit_price')
                                              else None
                        # total_price_calculated will be handled by db_manager.update_client_project_product
                    }
                    # Note: If product name/description from dialog differs, it implies editing the global product.
                    # This might need db_manager.update_product(linked_product_details['product_id'], {...})
                    # For now, focusing on quantity/price_override for the link.
                    if form_data['name'] != linked_product_details.get('product_name') or \
                       form_data['description'] != linked_product_details.get('product_description'):
                        db_manager.update_product(linked_product_details['product_id'], {
                            'product_name': form_data['name'],
                            'description': form_data['description']
                            # Base price update could also be considered here if dialog unit_price is meant to update it
                        })


                    if db_manager.update_client_project_product(client_project_product_id, update_link_data):
                        self.load_products()
                    else:
                        QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour du produit lié."))
            else:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Détails du produit lié introuvables."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de modification du produit:\n{0}").format(str(e)))

    def remove_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row < 0: return
        
        cpp_id_item = self.products_table.item(selected_row, 0)
        if not cpp_id_item: return
        client_project_product_id = cpp_id_item.data(Qt.UserRole) # This is client_project_product_id

        product_name_item = self.products_table.item(selected_row, 1)
        product_name = product_name_item.text() if product_name_item else self.tr("Inconnu")
        
        reply = QMessageBox.question(
            self, 
            self.tr("Confirmer Suppression"),
            self.tr("Êtes-vous sûr de vouloir supprimer le produit '{0}' de ce client/projet?").format(product_name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if db_manager.remove_product_from_client_or_project(client_project_product_id):
                    self.load_products()
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du produit lié."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du produit lié:\n{0}").format(str(e)))

    def load_products(self):
        self.products_table.setRowCount(0)
        client_uuid = self.client_info.get("client_id")
        if not client_uuid: return

        try:
            # Get products linked to this client (project_id=None for client-general products)
            # This returns a list of dicts, with joined info from Products table
            linked_products = db_manager.get_products_for_client_or_project(client_uuid, project_id=None)
            if linked_products is None: linked_products = []
            
            for row_idx, prod_link_data in enumerate(linked_products):
                self.products_table.insertRow(row_idx)
                
                # Store client_project_product_id for edit/delete
                id_item = QTableWidgetItem(str(prod_link_data.get('client_project_product_id')))
                id_item.setData(Qt.UserRole, prod_link_data.get('client_project_product_id'))
                self.products_table.setItem(row_idx, 0, id_item)
                
                self.products_table.setItem(row_idx, 1, QTableWidgetItem(prod_link_data.get('product_name', 'N/A')))
                self.products_table.setItem(row_idx, 2, QTableWidgetItem(prod_link_data.get('product_description', '')))
                
                qty_item = QTableWidgetItem(str(prod_link_data.get('quantity', 0)))
                qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 3, qty_item)
                
                effective_unit_price = prod_link_data.get('unit_price_override', prod_link_data.get('base_unit_price', 0.0))
                unit_price_item = QTableWidgetItem(f"€ {effective_unit_price:.2f}")
                unit_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 4, unit_price_item)
                
                total_price_item = QTableWidgetItem(f"€ {prod_link_data.get('total_price_calculated', 0.0):.2f}")
                total_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 5, total_price_item)
                
            self.products_table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des produits:\n{0}").format(str(e)))

# --- DOCX Population Logic ---
def populate_docx_template(docx_path, client_data):
    """
    Populates a .docx template with client data using placeholders.
    Placeholders should be in the format {{PLACEHOLDER_NAME}}.
    """
    try:
        document = Document(docx_path)

        placeholders = {
            "{{CLIENT_NAME}}": client_data.get('client_name', ''),
            "{{PROJECT_ID}}": client_data.get('project_identifier', ''),
            "{{COMPANY_NAME}}": client_data.get('company_name', ''),
            "{{NEED}}": client_data.get('need', ''),
            "{{COUNTRY}}": client_data.get('country', ''),
            "{{CITY}}": client_data.get('city', ''),
            "{{PRICE}}": str(client_data.get('price', 0)),
            "{{DATE}}": datetime.now().strftime('%Y-%m-%d'),
            # Add more placeholders as needed for other client_info fields:
            "{{STATUS}}": client_data.get('status', ''),
            "{{SELECTED_LANGUAGES}}": ", ".join(client_data.get('selected_languages', [])),
            "{{NOTES}}": client_data.get('notes', ''),
            "{{CREATION_DATE}}": client_data.get('creation_date', ''),
            "{{CATEGORY}}": client_data.get('category', ''),
            "{{PRIMARY_CONTACT_NAME}}": "", # Needs logic to fetch primary contact
        }

        # Placeholder for primary contact details - requires DB lookup or richer client_data
        # This is a simplified example; a real version might fetch primary contact name, email, phone
        # For now, we'll leave it to be manually filled or expanded later.

        # Replace in paragraphs
        for para in document.paragraphs:
            for key, value in placeholders.items():
                if key in para.text:
                    # Basic text replacement.
                    # This is a simplified version. For complex documents with formatting within placeholders,
                    # a run-by-run replacement is needed.
                    new_text = para.text.replace(key, value)
                    if para.text != new_text:
                         para.text = new_text # Assign back if changed

        # Replace in tables
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for key, value in placeholders.items():
                            if key in para.text:
                                new_text = para.text.replace(key, value)
                                if para.text != new_text:
                                    para.text = new_text

        # Consider headers/footers if necessary (more complex)
        # for section in document.sections:
        #     for header_footer_type in [section.header, section.footer, section.first_page_header, section.first_page_footer]:
        #         if header_footer_type:
        #             for para in header_footer_type.paragraphs:
        #                 # ... replacement logic ...
        #             for table in header_footer_type.tables:
        #                 # ... replacement logic ...

        document.save(docx_path)
        print(f"DOCX template populated: {docx_path}")

    except Exception as e:
        print(f"Error populating DOCX template {docx_path}: {e}")
        # Re-raise or handle more gracefully depending on desired behavior
        raise


class StatisticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self); layout.setContentsMargins(10, 5, 10, 5)
        # Titles are UI text, values are data
        stat_items_data = [ 
            (self.tr("Clients Totaux"), "total_label", "0", None),
            (self.tr("Valeur Totale"), "value_label", "0 €", None), # Currency format
            (self.tr("Projets en Cours"), "ongoing_label", "0", None),
            (self.tr("Projets Urgents"), "urgent_label", "0", "color: #e74c3c;")
        ]
        for title, attr_name, default_text, style in stat_items_data: 
            group = QGroupBox(title); group_layout = QVBoxLayout(group) 
            label = QLabel(default_text) # Default text is data-like here (a number)
            label.setFont(QFont("Arial", 16, QFont.Bold)); label.setAlignment(Qt.AlignCenter)
            if style: label.setStyleSheet(style)
            setattr(self, attr_name, label) 
            group_layout.addWidget(label); layout.addWidget(group)
        
    def update_stats(self):
        # conn = None # Old sqlite3 connection
        try:
            # conn = sqlite3.connect(DATABASE_NAME) # Old sqlite3 connection
            # cursor = conn.cursor() # Old sqlite3 connection
            
            all_clients = db_manager.get_all_clients()
            if all_clients is None: all_clients = []

            total_clients = len(all_clients)
            self.total_label.setText(str(total_clients))
            
            total_val = sum(c.get('price', 0) for c in all_clients if c.get('price') is not None)
            self.value_label.setText(f"{total_val:,.2f} €")
            
            status_en_cours_obj = db_manager.get_status_setting_by_name('En cours', 'Client')
            status_en_cours_id = status_en_cours_obj['status_id'] if status_en_cours_obj else None

            status_urgent_obj = db_manager.get_status_setting_by_name('Urgent', 'Client')
            status_urgent_id = status_urgent_obj['status_id'] if status_urgent_obj else None

            ongoing_count = 0
            if status_en_cours_id is not None:
                ongoing_count = sum(1 for c in all_clients if c.get('status_id') == status_en_cours_id)
            self.ongoing_label.setText(str(ongoing_count))
            
            urgent_count = 0
            if status_urgent_id is not None:
                urgent_count = sum(1 for c in all_clients if c.get('status_id') == status_urgent_id)
            self.urgent_label.setText(str(urgent_count))

            # Old SQL queries:
            # cursor.execute("SELECT COUNT(*) FROM Clients"); total_clients = cursor.fetchone()[0]
            # cursor.execute("SELECT SUM(price) FROM Clients"); total_val = cursor.fetchone()[0] or 0
            # cursor.execute("SELECT COUNT(*) FROM Clients WHERE status = 'En cours'"); ongoing_count = cursor.fetchone()[0]
            # cursor.execute("SELECT COUNT(*) FROM Clients WHERE status = 'Urgent'"); urgent_count = cursor.fetchone()[0]

        except Exception as e: # Catch generic db_manager errors or other issues
            print(f"Erreur de mise à jour des statistiques: {str(e)}")
        # finally:
            # if conn: conn.close() # Old sqlite3 connection

class StatusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        status_name_for_delegate = index.data(Qt.UserRole) # This is the status name (text)
        bg_color_hex = "#95a5a6" # Default color

        if status_name_for_delegate:
            try:
                # Assuming status_type is 'Client' for this delegate context,
                # as this delegate is used in the client list.
                status_setting = db_manager.get_status_setting_by_name(status_name_for_delegate, 'Client')
                if status_setting and status_setting.get('color_hex'):
                    bg_color_hex = status_setting['color_hex']
            except Exception as e:
                print(f"Error fetching status color for delegate: {e}")
                # Keep default color if error
        
        painter.save()
        painter.fillRect(option.rect, QColor(bg_color_hex))
        
        bg_qcolor = QColor(bg_color_hex)
        text_qcolor = QColor(Qt.black) 
        if bg_qcolor.lightnessF() < 0.5: 
            text_qcolor = QColor(Qt.white)
        painter.setPen(text_qcolor)

        text_rect = option.rect.adjusted(5, 0, -5, 0) 
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, index.data(Qt.DisplayRole)) 
        painter.restore()

class DocumentManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.tr("Gestionnaire de Documents Client")); self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon.fromTheme("folder-documents"))
        
        self.config = CONFIG 
        self.clients_data_map = {} 
        # self.project_management_widget_instance = None # Placeholder for PM widget
        # No longer just a placeholder, will be instantiated after setup_ui_main
        
        self.setup_ui_main() # This now sets up the QStackedWidget and documents_page_widget

        # Instantiate ProjectManagementDashboard here so it's ready
        # Passing None for current_user. main.py will need its own auth to pass a real user.
        self.project_management_widget_instance = ProjectManagementDashboard(parent=self, current_user=None)
        self.main_area_stack.addWidget(self.project_management_widget_instance)

        # Set initial view to documents
        self.main_area_stack.setCurrentWidget(self.documents_page_widget)

        self.create_actions_main() 
        self.create_menus_main() 
        self.load_clients_from_db()
        self.stats_widget.update_stats() 
        
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_old_clients_routine) 
        self.check_timer.start(3600000) # Interval in ms, not user-facing text
        
    def setup_ui_main(self): 
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); main_layout.setContentsMargins(10,10,10,10); main_layout.setSpacing(10)
        
        self.stats_widget = StatisticsWidget(); main_layout.addWidget(self.stats_widget)

        # Create QStackedWidget for main content area
        self.main_area_stack = QStackedWidget()
        main_layout.addWidget(self.main_area_stack)

        # Original content page (documents view)
        self.documents_page_widget = QWidget()
        content_layout = QHBoxLayout(self.documents_page_widget) # This QHBoxLayout is now for the documents page
        
        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel); left_layout.setContentsMargins(5,5,5,5)
        filter_search_layout = QHBoxLayout() 
        self.status_filter_combo = QComboBox(); self.status_filter_combo.addItem(self.tr("Tous les statuts"))
        self.load_statuses_into_filter_combo() # Loads data, check if any default items need tr
        self.status_filter_combo.currentIndexChanged.connect(self.filter_client_list_display) 
        filter_search_layout.addWidget(QLabel(self.tr("Filtrer par statut:")))
        filter_search_layout.addWidget(self.status_filter_combo)
        self.search_input_field = QLineEdit(); self.search_input_field.setPlaceholderText(self.tr("Rechercher client..."))
        self.search_input_field.textChanged.connect(self.filter_client_list_display) 
        filter_search_layout.addWidget(self.search_input_field); left_layout.addLayout(filter_search_layout)
        
        self.client_list_widget = QListWidget(); self.client_list_widget.setAlternatingRowColors(True) 
        self.client_list_widget.setItemDelegate(StatusDelegate(self.client_list_widget))
        self.client_list_widget.itemClicked.connect(self.handle_client_list_click) 
        self.client_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.client_list_widget.customContextMenuRequested.connect(self.show_client_context_menu)
        left_layout.addWidget(self.client_list_widget)
        
        form_group_box = QGroupBox(self.tr("Ajouter un Nouveau Client")); form_vbox_layout = QVBoxLayout(form_group_box)
        creation_form_layout = QFormLayout(); creation_form_layout.setLabelAlignment(Qt.AlignRight) 
        
        self.client_name_input = QLineEdit(); self.client_name_input.setPlaceholderText(self.tr("Nom du client"))
        creation_form_layout.addRow(self.tr("Nom Client:"), self.client_name_input)
        self.company_name_input = QLineEdit(); self.company_name_input.setPlaceholderText(self.tr("Nom entreprise (optionnel)"))
        creation_form_layout.addRow(self.tr("Nom Entreprise:"), self.company_name_input)
        self.client_need_input = QLineEdit(); self.client_need_input.setPlaceholderText(self.tr("Besoin principal du client"))
        creation_form_layout.addRow(self.tr("Besoin Client:"), self.client_need_input)
        
        country_hbox_layout = QHBoxLayout(); self.country_select_combo = QComboBox() 
        self.country_select_combo.setEditable(True); self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country) 
        country_hbox_layout.addWidget(self.country_select_combo)
        self.add_country_button = QPushButton("+"); self.add_country_button.setFixedSize(30,30) 
        self.add_country_button.setToolTip(self.tr("Ajouter un nouveau pays"))
        self.add_country_button.clicked.connect(self.add_new_country_dialog) 
        country_hbox_layout.addWidget(self.add_country_button); creation_form_layout.addRow(self.tr("Pays Client:"), country_hbox_layout)
        
        city_hbox_layout = QHBoxLayout(); self.city_select_combo = QComboBox() 
        self.city_select_combo.setEditable(True); self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        city_hbox_layout.addWidget(self.city_select_combo)
        self.add_city_button = QPushButton("+"); self.add_city_button.setFixedSize(30,30) 
        self.add_city_button.setToolTip(self.tr("Ajouter une nouvelle ville"))
        self.add_city_button.clicked.connect(self.add_new_city_dialog) 
        city_hbox_layout.addWidget(self.add_city_button); creation_form_layout.addRow(self.tr("Ville Client:"), city_hbox_layout)
        
        self.project_id_input_field = QLineEdit(); self.project_id_input_field.setPlaceholderText(self.tr("Identifiant unique du projet"))
        creation_form_layout.addRow(self.tr("ID Projet:"), self.project_id_input_field)
        self.final_price_input = QDoubleSpinBox(); self.final_price_input.setPrefix("€ ") 
        self.final_price_input.setRange(0, 10000000); self.final_price_input.setValue(0)
        creation_form_layout.addRow(self.tr("Prix Final:"), self.final_price_input)
        self.language_select_combo = QComboBox() 
        self.language_select_combo.addItems([self.tr("Français uniquement (fr)"), self.tr("Arabe uniquement (ar)"), self.tr("Turc uniquement (tr)"), self.tr("Toutes les langues (fr, ar, tr)")])
        creation_form_layout.addRow(self.tr("Langues:"), self.language_select_combo)
        self.create_client_button = QPushButton(self.tr("Créer Client")); self.create_client_button.setIcon(QIcon.fromTheme("list-add"))
        self.create_client_button.setStyleSheet("QPushButton { background-color: #27ae60; color: white; font-weight: bold; padding: 10px; border-radius: 5px; } QPushButton:hover { background-color: #2ecc71; }")
        self.create_client_button.clicked.connect(self.execute_create_client) 
        creation_form_layout.addRow(self.create_client_button)
        form_vbox_layout.addLayout(creation_form_layout); left_layout.addWidget(form_group_box)
        content_layout.addWidget(left_panel, 1)
        
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True) 
        self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab) 
        content_layout.addWidget(self.client_tabs_widget, 2)

        self.main_area_stack.addWidget(self.documents_page_widget) # Add original content as first page
        # PM widget instantiated in __init__ and added to stack there

        self.load_countries_into_combo() 
        
    def create_actions_main(self): 
        self.settings_action = QAction(self.tr("Paramètres"), self); self.settings_action.triggered.connect(self.open_settings_dialog)
        self.template_action = QAction(self.tr("Gérer les Modèles"), self); self.template_action.triggered.connect(self.open_template_manager_dialog)
        self.status_action = QAction(self.tr("Gérer les Statuts"), self); self.status_action.triggered.connect(self.open_status_manager_dialog)
        self.exit_action = QAction(self.tr("Quitter"), self); self.exit_action.setShortcut("Ctrl+Q"); self.exit_action.triggered.connect(self.close)
        
        # Action for Project Management
        self.project_management_action = QAction(QIcon.fromTheme("preferences-system"), self.tr("Gestion de Projet"), self) # Added icon
        self.project_management_action.triggered.connect(self.show_project_management_view)

        # Action to go back to Documents view (optional, but good for navigation)
        self.documents_view_action = QAction(QIcon.fromTheme("folder-documents"), self.tr("Gestion Documents"), self)
        self.documents_view_action.triggered.connect(self.show_documents_view)

    def create_menus_main(self): 
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu(self.tr("Fichier"))
        file_menu.addAction(self.settings_action); file_menu.addAction(self.template_action); file_menu.addAction(self.status_action)
        file_menu.addSeparator(); file_menu.addAction(self.exit_action)

        # Modules Menu
        modules_menu = menu_bar.addMenu(self.tr("Modules"))
        modules_menu.addAction(self.documents_view_action) # Action to switch to Documents
        modules_menu.addAction(self.project_management_action) # Action to switch to Project Management

        help_menu = menu_bar.addMenu(self.tr("Aide"))
        about_action = QAction(self.tr("À propos"), self); about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_project_management_view(self):
        # Instantiate on first click if not already done, or could be done in __init__
        # if self.project_management_widget_instance is None: # Instance is now created in __init__
            # Passing None for current_user as main.py doesn't have its own login currently
            # self.project_management_widget_instance = ProjectManagementDashboard(parent=self, current_user=None)
            # self.main_area_stack.addWidget(self.project_management_widget_instance)

        self.main_area_stack.setCurrentWidget(self.project_management_widget_instance)

    def show_documents_view(self): # Method to switch back to the document view
        self.main_area_stack.setCurrentWidget(self.documents_page_widget)
        
    def show_about_dialog(self): 
        QMessageBox.about(self, self.tr("À propos"), self.tr("<b>Gestionnaire de Documents Client</b><br><br>Version 4.0<br>Application de gestion de documents clients avec templates Excel.<br><br>Développé par Saadiya Management (Concept)"))
        
    def load_countries_into_combo(self):
        self.country_select_combo.clear()
        try:
            countries = db_manager.get_all_countries()
            if countries is None: countries = []
            for country_dict in countries:
                self.country_select_combo.addItem(country_dict['country_name'], country_dict.get('country_id')) # Store ID
        except Exception as e: # More generic exception catch
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des pays:\n{0}").format(str(e)))
            
    def load_cities_for_country(self, country_name_str): # country_name_str is the displayed text
        self.city_select_combo.clear()
        if not country_name_str:
            return

        selected_country_id = self.country_select_combo.currentData() # Get ID from combo item's data

        if selected_country_id is None: # Fallback if ID not found (e.g. user typed custom country)
            # Try to get country by name if ID is not available (e.g., user typed a new country name)
            country_obj_by_name = db_manager.get_country_by_name(country_name_str)
            if country_obj_by_name:
                selected_country_id = country_obj_by_name['country_id']
            else:
                # If country_name_str is from an editable combo box and not in DB, do nothing.
                return

        try:
            cities = db_manager.get_all_cities(country_id=selected_country_id)
            if cities is None: cities = []
            for city_dict in cities:
                self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id')) # Store ID
        except Exception as e: # More generic exception catch
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:\n{0}").format(str(e)))
            
    def add_new_country_dialog(self):
        country_text, ok = QInputDialog.getText(self, self.tr("Nouveau Pays"), self.tr("Entrez le nom du nouveau pays:"))
        if ok and country_text.strip():
            try:
                country_name_to_add = country_text.strip()
                # db_manager.add_country returns the country_id (int) or None
                returned_country_id = db_manager.add_country({'country_name': country_name_to_add})

                if returned_country_id is not None:
                    # Country was successfully added or already existed and its ID was returned.
                    self.load_countries_into_combo() # Refresh the combo box
                    # Find the country by text to select it.
                    # The combo box items store country_id in UserRole, but findText works on display text.
                    index = self.country_select_combo.findText(country_name_to_add)
                    if index >= 0:
                        self.country_select_combo.setCurrentIndex(index)
                    # Check if the country was pre-existing by trying to get it by name again
                    # This is a bit redundant as add_country now handles the "already exists" case by returning its ID.
                    # We can simplify the user message.
                    # If we reach here, it means add_country gave us an ID.
                    # We don't need to explicitly show "Pays Existant" unless add_country itself printed it.
                    # The main goal is that the combo is updated and the correct item is selected.
                else:
                    # This case means db_manager.add_country returned None, indicating an unexpected error.
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du pays. La fonction add_country a retourné None. Vérifiez les logs."))

            except Exception as e: # Catch any other unexpected exceptions during the process
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue lors de l'ajout du pays:\n{0}").format(str(e)))
                
    def add_new_city_dialog(self):
        current_country_name = self.country_select_combo.currentText()
        current_country_id = self.country_select_combo.currentData()

        if not current_country_id:
            QMessageBox.warning(self, self.tr("Pays Requis"), self.tr("Veuillez d'abord sélectionner un pays valide.")); return

        city_text, ok = QInputDialog.getText(self, self.tr("Nouvelle Ville"), self.tr("Entrez le nom de la nouvelle ville pour {0}:").format(current_country_name))
        if ok and city_text.strip():
            try:
                city_name_to_add = city_text.strip()
                city_data = {'country_id': current_country_id, 'city_name': city_name_to_add}

                returned_city_id = db_manager.add_city(city_data)

                if returned_city_id is not None:
                    # City was successfully added or already existed and its ID was returned.
                    self.load_cities_for_country(current_country_name) # Refresh the city combo for the current country
                    index = self.city_select_combo.findText(city_name_to_add)
                    if index >= 0:
                        self.city_select_combo.setCurrentIndex(index)
                    # No need for an explicit "Ville Existante" message here,
                    # as db.add_city now handles returning the ID of an existing city or a new one.
                    # If an ID is returned, the operation was successful from the main.py perspective.
                else:
                    # This means db_manager.add_city returned None, indicating an issue like missing country_id/city_name or a DB error.
                    # The db.add_city function itself prints specific errors for missing fields.
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout de la ville. La fonction add_city a retourné None. Vérifiez les logs."))

            except Exception as e: # Catch any other unexpected exceptions
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue lors de l'ajout de la ville:\n{0}").format(str(e)))
                
    def generate_new_client_id(self):
        # This function is no longer used to generate primary client IDs as db_manager.add_client handles UUID generation.
        # It can be removed or repurposed if a different kind of human-readable ID is needed elsewhere.
        # For now, it's effectively dead code if client_id is always the UUID.
        return f"LEGACY_ID_FORMAT_UNUSED_{int(datetime.now().timestamp())}"
                
    def execute_create_client(self): 
        client_name_val = self.client_name_input.text().strip() 
        company_name_val = self.company_name_input.text().strip()
        need_val = self.client_need_input.text().strip()

        country_id_val = self.country_select_combo.currentData() # This is country_id (int)
        country_name_for_folder = self.country_select_combo.currentText().strip() # For folder name consistency
        city_id_val = self.city_select_combo.currentData() # This is city_id (int)

        project_identifier_val = self.project_id_input_field.text().strip() # This is the TEXT project_identifier
        price_val = self.final_price_input.value()
        lang_option_text = self.language_select_combo.currentText()
        
        if not client_name_val or not country_id_val or not project_identifier_val:
            QMessageBox.warning(self, self.tr("Champs Requis"), self.tr("Nom client, Pays et ID Projet sont obligatoires.")); return
            
        lang_map_from_display = {
            self.tr("Français uniquement (fr)"): ["fr"], self.tr("Arabe uniquement (ar)"): ["ar"],
            self.tr("Turc uniquement (tr)"): ["tr"], self.tr("Toutes les langues (fr, ar, tr)"): ["fr", "ar", "tr"]
        }
        selected_langs_list = lang_map_from_display.get(lang_option_text, ["fr"])
        
        folder_name_str = f"{client_name_val}_{country_name_for_folder}_{project_identifier_val}".replace(" ", "_").replace("/", "-")
        base_folder_full_path = os.path.join(self.config["clients_dir"], folder_name_str) 
        
        # Check for existing folder path (which should be unique due to DB constraint on default_base_folder_path)
        if os.path.exists(base_folder_full_path):
            # It's possible the folder exists but the DB entry doesn't, or vice-versa if there was a past issue.
            # The DB check for unique default_base_folder_path in add_client is the more critical one.
            QMessageBox.warning(self, self.tr("Dossier Existant"),
                                self.tr("Un dossier client avec un chemin similaire existe déjà. Veuillez vérifier les détails ou choisir un ID Projet différent."))
            return

        # Determine default status_id for new clients
        default_status_name = "En cours" # Or fetch from a config/default setting
        status_setting_obj = db_manager.get_status_setting_by_name(default_status_name, 'Client')
        if not status_setting_obj or not status_setting_obj.get('status_id'):
            QMessageBox.critical(self, self.tr("Erreur Configuration"),
                                 self.tr("Statut par défaut '{0}' non trouvé pour les clients. Veuillez configurer les statuts.").format(default_status_name))
            return
        default_status_id = status_setting_obj['status_id']

        # Prepare data for db_manager.add_client
        client_data_for_db = {
            'client_name': client_name_val,
            'company_name': company_name_val if company_name_val else None,
            'primary_need_description': need_val,
            'project_identifier': project_identifier_val, # This is the TEXT field
            'country_id': country_id_val,
            'city_id': city_id_val if city_id_val else None,
            'default_base_folder_path': base_folder_full_path,
            'selected_languages': ",".join(selected_langs_list), # Stored as comma-separated string
            'price': price_val,
            'status_id': default_status_id,
            'category': 'Standard', # Default category or could be a form field
            'notes': '', # Default empty notes
            # 'created_by_user_id': self.get_current_user_id(), # TODO: Implement user tracking if available
        }

        actual_new_client_id = None # This will be the UUID returned by add_client
        new_project_id_central_db = None # This will be the UUID returned by add_project

        try:
            actual_new_client_id = db_manager.add_client(client_data_for_db)
            if not actual_new_client_id:
                # db_manager.add_client should ideally raise specific exceptions or return error codes
                # For now, assume unique constraint on project_identifier or default_base_folder_path failed
                QMessageBox.critical(self, self.tr("Erreur DB"),
                                     self.tr("Impossible de créer le client. L'ID de projet ou le chemin du dossier existe peut-être déjà, ou autre erreur de contrainte DB."))
                return

            # Create client directory structure
            os.makedirs(base_folder_full_path, exist_ok=True)
            for lang_code in selected_langs_list:
                os.makedirs(os.path.join(base_folder_full_path, lang_code), exist_ok=True)

            # --- Create associated project and tasks in the central database (app_data.db) ---
            project_status_planning_obj = db_manager.get_status_setting_by_name("Planning", "Project")
            project_status_id_for_pm = project_status_planning_obj['status_id'] if project_status_planning_obj else None

            if not project_status_id_for_pm:
                 QMessageBox.warning(self, self.tr("Erreur Configuration Projet"),
                                     self.tr("Statut de projet par défaut 'Planning' non trouvé. Le projet ne sera pas créé avec un statut initial."))

            project_data_for_db = {
                'client_id': actual_new_client_id, # Link to the newly created client
                'project_name': f"Projet pour {client_name_val}", # Default project name
                'description': f"Projet pour client: {client_name_val}. Besoin initial: {need_val}",
                'start_date': datetime.now().strftime("%Y-%m-%d"),
                'deadline_date': (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"), # Default deadline
                'budget': 0.0, # Default budget
                'status_id': project_status_id_for_pm, # Can be None if not found
                'priority': 1 # Default priority (e.g., 0=Low, 1=Medium, 2=High)
                # 'manager_team_member_id': self.get_current_user_id(), # TODO: Assign project manager if applicable
            }
            new_project_id_central_db = db_manager.add_project(project_data_for_db)

            if new_project_id_central_db:
                QMessageBox.information(self, self.tr("Projet Créé (Central DB)"),
                                        self.tr("Un projet associé a été créé dans la base de données centrale pour {0}.").format(client_name_val))

                # Add standard tasks for the new project
                task_status_todo_obj = db_manager.get_status_setting_by_name("To Do", "Task")
                task_status_id_for_todo = task_status_todo_obj['status_id'] if task_status_todo_obj else None

                if not task_status_id_for_todo:
                    QMessageBox.warning(self, self.tr("Erreur Configuration Tâche"),
                                        self.tr("Statut de tâche par défaut 'To Do' non trouvé. Les tâches standard ne seront pas créées avec un statut initial."))

                standard_tasks = [
                    {"name": "Initial Client Consultation & Needs Assessment", "description": "Understand client requirements, objectives, target markets, and budget.", "priority_val": 2, "deadline_days": 3},
                    {"name": "Market Research & Analysis", "description": "Research target international markets, including competition, regulations, and cultural nuances.", "priority_val": 1, "deadline_days": 7},
                    # ... (add other standard tasks as before) ...
                    {"name": "Post-Sales Follow-up & Support", "description": "Follow up with the client after delivery.", "priority_val": 1, "deadline_days": 60}
                ]

                for task_item in standard_tasks:
                    task_deadline = (datetime.now() + timedelta(days=task_item["deadline_days"])).strftime("%Y-%m-%d")
                    db_manager.add_task({
                        'project_id': new_project_id_central_db,
                        'task_name': task_item["name"],
                        'description': task_item["description"],
                        'status_id': task_status_id_for_todo, # Can be None
                        'priority': task_item["priority_val"],
                        'due_date': task_deadline
                        # 'assignee_team_member_id': None, # TODO: Assign tasks if logic exists
                    })
                QMessageBox.information(self, self.tr("Tâches Créées (Central DB)"),
                                        self.tr("Des tâches standard ont été ajoutées au projet pour {0}.").format(client_name_val))
            else:
                QMessageBox.warning(self, self.tr("Erreur DB Projet"),
                                    self.tr("Le client a été créé, mais la création du projet associé dans la base de données centrale a échoué."))

            # --- Update UI ---
            # Reload client from DB to get all fields correctly for the UI map, including generated UUID and timestamps
            client_dict_from_db = db_manager.get_client_by_id(actual_new_client_id)
            if client_dict_from_db:
                # Fetch related names for UI display (Country, City, Status)
                country_obj = db_manager.get_country_by_id(client_dict_from_db.get('country_id')) if client_dict_from_db.get('country_id') else None
                city_obj = db_manager.get_city_by_id(client_dict_from_db.get('city_id')) if client_dict_from_db.get('city_id') else None
                status_obj = db_manager.get_status_setting_by_id(client_dict_from_db.get('status_id')) if client_dict_from_db.get('status_id') else None

                ui_map_data = {
                    "client_id": client_dict_from_db.get('client_id'), # UUID
                    "client_name": client_dict_from_db.get('client_name'),
                    "company_name": client_dict_from_db.get('company_name'),
                    "need": client_dict_from_db.get('primary_need_description'),
                    "country": country_obj['country_name'] if country_obj else "N/A",
                    "country_id": client_dict_from_db.get('country_id'),
                    "city": city_obj['city_name'] if city_obj else "N/A",
                    "city_id": client_dict_from_db.get('city_id'),
                    "project_identifier": client_dict_from_db.get('project_identifier'), # The text ID
                    "base_folder_path": client_dict_from_db.get('default_base_folder_path'),
                    "selected_languages": client_dict_from_db.get('selected_languages','').split(',') if client_dict_from_db.get('selected_languages') else [],
                    "price": client_dict_from_db.get('price'),
                    "notes": client_dict_from_db.get('notes'),
                    "status": status_obj['status_name'] if status_obj else "N/A",
                    "status_id": client_dict_from_db.get('status_id'),
                    "creation_date": client_dict_from_db.get('created_at','').split("T")[0] if client_dict_from_db.get('created_at') else "N/A", # Format date part
                    "category": client_dict_from_db.get('category')
                }
                self.clients_data_map[actual_new_client_id] = ui_map_data
                self.add_client_to_list_widget(ui_map_data) # Update client list display
            
            # Clear input fields
            self.client_name_input.clear(); self.company_name_input.clear(); self.client_need_input.clear()
            self.project_id_input_field.clear(); self.final_price_input.setValue(0)
            # Optionally reset country/city/language combos to default
            
            QMessageBox.information(self, self.tr("Client Créé"),
                                    self.tr("Client {0} créé avec succès (ID Interne: {1}).").format(client_name_val, actual_new_client_id))
            self.open_client_tab_by_id(actual_new_client_id) # Open the new client's tab
            self.stats_widget.update_stats() # Refresh statistics

        except OSError as e_os:
            QMessageBox.critical(self, self.tr("Erreur Dossier"), self.tr("Erreur de création du dossier client:\n{0}").format(str(e_os)))
            # Rollback: If client was added to DB but folder creation failed, delete client from DB
            if actual_new_client_id:
                 db_manager.delete_client(actual_new_client_id) # This will also cascade-delete related Project and Tasks if FKs are set up correctly
                 QMessageBox.information(self, self.tr("Rollback"), self.tr("Le client a été retiré de la base de données suite à l'erreur de création de dossier."))
        except Exception as e_db: # Catch other potential errors from db_manager calls or logic
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur s'est produite lors de la création du client, du projet ou des tâches:\n{0}").format(str(e_db)))
            # Rollback: If client or project was added before a subsequent error
            if new_project_id_central_db and db_manager.get_project_by_id(new_project_id_central_db):
                db_manager.delete_project(new_project_id_central_db) # Cascade delete tasks
            if actual_new_client_id and db_manager.get_client_by_id(actual_new_client_id):
                 db_manager.delete_client(actual_new_client_id)
                 QMessageBox.information(self, self.tr("Rollback"), self.tr("Le client et le projet associé (si créé) ont été retirés de la base de données suite à l'erreur."))
            
    def load_clients_from_db(self):
        self.clients_data_map.clear()
        self.client_list_widget.clear()
        try:
            all_clients_dicts = db_manager.get_all_clients()
            if all_clients_dicts is None: all_clients_dicts = []

            all_clients_dicts.sort(key=lambda c: c.get('client_name', ''))

            for client_data in all_clients_dicts:
                country_name = "N/A"
                if client_data.get('country_id'):
                    country_obj = db_manager.get_country_by_id(client_data['country_id'])
                    if country_obj: country_name = country_obj['country_name']

                city_name = "N/A"
                if client_data.get('city_id'):
                    city_obj = db_manager.get_city_by_id(client_data['city_id'])
                    if city_obj: city_name = city_obj['city_name']

                status_name = "N/A"
                status_id_val = client_data.get('status_id')
                if status_id_val:
                    status_obj = db_manager.get_status_setting_by_id(status_id_val)
                    if status_obj: status_name = status_obj['status_name']

                adapted_client_dict = {
                    "client_id": client_data.get('client_id'),
                    "client_name": client_data.get('client_name'),
                    "company_name": client_data.get('company_name'),
                    "need": client_data.get('primary_need_description'),
                    "country": country_name,
                    "country_id": client_data.get('country_id'),
                    "city": city_name,
                    "city_id": client_data.get('city_id'),
                    "project_identifier": client_data.get('project_identifier'),
                    "base_folder_path": client_data.get('default_base_folder_path'),
                    "selected_languages": client_data.get('selected_languages', '').split(',') if client_data.get('selected_languages') else ['fr'],
                    "price": client_data.get('price', 0),
                    "notes": client_data.get('notes'),
                    "status": status_name,
                    "status_id": status_id_val,
                    "creation_date": client_data.get('created_at', '').split('T')[0] if client_data.get('created_at') else "N/A",
                    "category": client_data.get('category', 'Standard')
                }
                self.clients_data_map[adapted_client_dict["client_id"]] = adapted_client_dict
                self.add_client_to_list_widget(adapted_client_dict)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des clients:\n{0}").format(str(e)))
            
    def add_client_to_list_widget(self, client_dict_data): 
        item = QListWidgetItem(client_dict_data["client_name"])
        item.setData(Qt.UserRole, client_dict_data.get("status", "N/A"))  # Status name for StatusDelegate
        item.setData(Qt.UserRole + 1, client_dict_data["client_id"]) 
        self.client_list_widget.addItem(item)
            
    def filter_client_list_display(self): 
        search_term = self.search_input_field.text().lower() 
        selected_status_id = self.status_filter_combo.currentData() # This will be status_id or None

        self.client_list_widget.clear()
        for client_id_key, client_data_val in self.clients_data_map.items(): 
            if selected_status_id is not None:
                if client_data_val.get("status_id") != selected_status_id:
                    continue

            if search_term and not (search_term in client_data_val.get("client_name","").lower() or \
                                   search_term in client_data_val.get("project_identifier","").lower() or \
                                   search_term in client_data_val.get("company_name","").lower()): 
                continue
            self.add_client_to_list_widget(client_data_val)
            
    def load_statuses_into_filter_combo(self): 
        current_selection_data = self.status_filter_combo.currentData()
        self.status_filter_combo.clear()
        self.status_filter_combo.addItem(self.tr("Tous les statuts"), None) # UserData for "All" is None
        try:
            # Only load 'Client' type statuses for this combo
            client_statuses = db_manager.get_all_status_settings(status_type='Client')
            if client_statuses is None: client_statuses = []
            for status_dict in client_statuses:
                self.status_filter_combo.addItem(status_dict['status_name'], status_dict.get('status_id'))

            index = self.status_filter_combo.findData(current_selection_data)
            if index != -1:
                self.status_filter_combo.setCurrentIndex(index)
            # If not found by ID (e.g. "Tous les statuts" was selected), it defaults to index 0 ("Tous les statuts")

        except Exception as e: # More generic error catch
            print(self.tr("Erreur chargement statuts pour filtre: {0}").format(str(e)))
            
    def handle_client_list_click(self, item): 
        client_id_val = item.data(Qt.UserRole + 1) 
        if client_id_val: self.open_client_tab_by_id(client_id_val)
        
    def open_client_tab_by_id(self, client_id_to_open): 
        client_data_to_show = self.clients_data_map.get(client_id_to_open) 
        if not client_data_to_show: return

        for i in range(self.client_tabs_widget.count()):
            tab_widget_ref = self.client_tabs_widget.widget(i) 
            if hasattr(tab_widget_ref, 'client_info') and tab_widget_ref.client_info["client_id"] == client_id_to_open:
                self.client_tabs_widget.setCurrentIndex(i); return
                
        client_detail_widget = ClientWidget(client_data_to_show, self.config, self) 
        tab_idx = self.client_tabs_widget.addTab(client_detail_widget, client_data_to_show["client_name"]) 
        self.client_tabs_widget.setCurrentIndex(tab_idx)
            
    def close_client_tab(self, index): 
        widget_to_close = self.client_tabs_widget.widget(index) 
        if widget_to_close: widget_to_close.deleteLater()
        self.client_tabs_widget.removeTab(index)
        
    def show_client_context_menu(self, pos):
        list_item = self.client_list_widget.itemAt(pos) 
        if not list_item: return
        client_id_val = list_item.data(Qt.UserRole + 1) 
        client_name_val = self.clients_data_map[client_id_val]["client_name"] if client_id_val in self.clients_data_map else self.tr("N/A")

        menu = QMenu()
        open_action = menu.addAction(self.tr("Ouvrir Fiche Client")); open_action.triggered.connect(lambda: self.open_client_tab_by_id(client_id_val))
        open_folder_action = menu.addAction(self.tr("Ouvrir Dossier Client")); open_folder_action.triggered.connect(lambda: self.open_client_folder_fs(client_id_val))
        menu.addSeparator()
        archive_action = menu.addAction(self.tr("Archiver Client")); archive_action.triggered.connect(lambda: self.set_client_status_archived(client_id_val))
        delete_action = menu.addAction(self.tr("Supprimer Client")); delete_action.triggered.connect(lambda: self.delete_client_permanently(client_id_val))
        menu.exec_(self.client_list_widget.mapToGlobal(pos))
        
    def open_client_folder_fs(self, client_id_val): 
        if client_id_val in self.clients_data_map:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.clients_data_map[client_id_val]["base_folder_path"]))
            
    def set_client_status_archived(self, client_id_val): 
        if client_id_val not in self.clients_data_map: return
        # conn = None # Old sqlite3
        try:
            # conn = sqlite3.connect(DATABASE_NAME) # Old sqlite3
            # cursor = conn.cursor() # Old sqlite3
            # cursor.execute("UPDATE Clients SET status = 'Archivé' WHERE client_id = ?", (client_id_val,)) # Old sqlite3
            # conn.commit() # Old sqlite3

            status_archived_obj = db_manager.get_status_setting_by_name('Archivé', 'Client')
            if not status_archived_obj:
                QMessageBox.critical(self, self.tr("Erreur Configuration"),
                                     self.tr("Statut 'Archivé' non trouvé. Veuillez configurer les statuts."))
                return

            archived_status_id = status_archived_obj['status_id']
            updated = db_manager.update_client(client_id_val, {'status_id': archived_status_id})

            if updated:
                self.clients_data_map[client_id_val]["status"] = "Archivé" # Keep UI display name consistent
                self.clients_data_map[client_id_val]["status_id"] = archived_status_id # Update status_id in local map
                self.filter_client_list_display()
                for i in range(self.client_tabs_widget.count()):
                    tab_w = self.client_tabs_widget.widget(i)
                    if hasattr(tab_w, 'client_info') and tab_w.client_info["client_id"] == client_id_val:
                        tab_w.status_combo.setCurrentText("Archivé")
                        break
                self.stats_widget.update_stats()
                QMessageBox.information(self, self.tr("Client Archivé"),
                                        self.tr("Le client '{0}' a été archivé.").format(self.clients_data_map[client_id_val]['client_name']))
            else:
                QMessageBox.critical(self, self.tr("Erreur DB"),
                                     self.tr("Erreur d'archivage du client. Vérifiez les logs."))

        except Exception as e: # Catch generic db_manager errors or other issues
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'archivage du client:\n{0}").format(str(e)))
        # finally:
            # if conn: conn.close() # Old sqlite3
            
    def delete_client_permanently(self, client_id_val): 
        if client_id_val not in self.clients_data_map: return
        client_name_val = self.clients_data_map[client_id_val]['client_name']
        client_folder_path = self.clients_data_map[client_id_val]["base_folder_path"]

        reply = QMessageBox.question(
            self,
            self.tr("Confirmer Suppression"),
            self.tr("Supprimer '{0}'?\nCeci supprimera le client de la base de données (les contacts liés seront détachés mais pas supprimés globalement) et son dossier de fichiers (si possible).\nCette action est irréversible.").format(client_name_val),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # conn = None # Old sqlite3
            try:
                # conn = sqlite3.connect(DATABASE_NAME) # Old sqlite3
                # cursor = conn.cursor() # Old sqlite3
                # cursor.execute("DELETE FROM Clients WHERE client_id = ?", (client_id_val,)) # Old sqlite3
                # cursor.execute("DELETE FROM Contacts WHERE client_id = ?", (client_id_val,)) # Old, and incorrect schema assumption
                # conn.commit() # Old sqlite3

                deleted_from_db = db_manager.delete_client(client_id_val)
                
                if deleted_from_db:
                    if os.path.exists(client_folder_path):
                        shutil.rmtree(client_folder_path, ignore_errors=True)

                    del self.clients_data_map[client_id_val]
                    self.filter_client_list_display()
                    for i in range(self.client_tabs_widget.count()):
                        if hasattr(self.client_tabs_widget.widget(i), 'client_info') and \
                           self.client_tabs_widget.widget(i).client_info["client_id"] == client_id_val:
                            self.close_client_tab(i); break
                    self.stats_widget.update_stats()
                    QMessageBox.information(self, self.tr("Client Supprimé"),
                                            self.tr("Client '{0}' supprimé avec succès.").format(client_name_val))
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"),
                                         self.tr("Erreur lors de la suppression du client de la base de données. Le dossier n'a pas été supprimé."))

            # except sqlite3.Error as e: QMessageBox.critical(self, "Erreur DB", f"Erreur DB suppression client:\n{str(e)}") # Old sqlite3 error
            except OSError as e_os:
                QMessageBox.critical(self, self.tr("Erreur Dossier"),
                                     self.tr("Le client a été supprimé de la base de données, mais une erreur est survenue lors de la suppression de son dossier:\n{0}").format(str(e_os)))
                # Update UI anyway as DB deletion was successful before OS error
                del self.clients_data_map[client_id_val]
                self.filter_client_list_display()
                for i in range(self.client_tabs_widget.count()):
                    if hasattr(self.client_tabs_widget.widget(i), 'client_info') and \
                       self.client_tabs_widget.widget(i).client_info["client_id"] == client_id_val:
                        self.close_client_tab(i); break
                self.stats_widget.update_stats()
            except Exception as e_db: # Catch generic db_manager errors or other issues
                 QMessageBox.critical(self, self.tr("Erreur DB"),
                                      self.tr("Erreur lors de la suppression du client:\n{0}").format(str(e_db)))
            # finally:
                # if conn: conn.close() # Old sqlite3
                
    def check_old_clients_routine(self): 
        # conn = None # Old sqlite3
        try:
            # conn = sqlite3.connect(DATABASE_NAME) # Old sqlite3
            # cursor = conn.cursor() # Old sqlite3
            reminder_days_val = self.config.get("default_reminder_days", 30) 

            # Fetch status IDs for 'Archivé' and 'Complété'
            s_archived_obj = db_manager.get_status_setting_by_name('Archivé', 'Client')
            s_archived_id = s_archived_obj['status_id'] if s_archived_obj else -1 # Use an invalid ID if not found to avoid matching None

            s_complete_obj = db_manager.get_status_setting_by_name('Complété', 'Client')
            s_complete_id = s_complete_obj['status_id'] if s_complete_obj else -2 # Use another invalid ID

            all_clients = db_manager.get_all_clients()
            if all_clients is None: all_clients = []

            old_clients_to_notify = []
            cutoff_date = datetime.now() - timedelta(days=reminder_days_val)

            for client in all_clients:
                if client.get('status_id') not in [s_archived_id, s_complete_id]:
                    creation_date_str = client.get('created_at') # Format 'YYYY-MM-DDTHH:MM:SS.ffffffZ' or similar
                    if creation_date_str:
                        try:
                            # Attempt to parse with common ISO formats, handling potential 'Z'
                            if 'T' in creation_date_str and '.' in creation_date_str: # More precise format
                                client_creation_date = datetime.fromisoformat(creation_date_str.split('.')[0]) # Remove microseconds for simplicity
                            elif 'T' in creation_date_str: # Format like 'YYYY-MM-DDTHH:MM:SS'
                                 client_creation_date = datetime.fromisoformat(creation_date_str.replace('Z', ''))
                            else: # Simpler date format like 'YYYY-MM-DD'
                                client_creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d")

                            if client_creation_date <= cutoff_date:
                                old_clients_to_notify.append({
                                    'client_id': client.get('client_id'),
                                    'client_name': client.get('client_name'),
                                    'creation_date_str': client_creation_date.strftime("%Y-%m-%d") # For display
                                })
                        except ValueError as ve:
                            print(f"Could not parse creation_date '{creation_date_str}' for client {client.get('client_id')}: {ve}")
                            continue # Skip this client if date is unparseable

            # Old SQL query:
            # cursor.execute(f"SELECT client_id, client_name, creation_date FROM Clients WHERE status NOT IN ('Archivé', 'Complété') AND date(creation_date) <= date('now', '-{reminder_days_val} days')")
            # old_clients_list = cursor.fetchall()

            if old_clients_to_notify:
                client_names_str = "\n".join([f"- {c['client_name']} (créé le {c['creation_date_str']})" for c in old_clients_to_notify])
                reply = QMessageBox.question(
                    self,
                    self.tr("Clients Anciens Actifs"),
                    self.tr("Les clients suivants sont actifs depuis plus de {0} jours:\n{1}\n\nVoulez-vous les archiver?").format(reminder_days_val, client_names_str),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    for c_info in old_clients_to_notify:
                        self.set_client_status_archived(c_info['client_id']) # This method now uses db_manager

        except Exception as e: # Catch generic db_manager or other errors
            print(f"Erreur vérification clients anciens: {str(e)}")
        # finally:
            # if conn: conn.close() # Old sqlite3
            
    def open_settings_dialog(self): 
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            new_conf = dialog.get_config() 
            self.config.update(new_conf)
            save_config(self.config) 
            os.makedirs(self.config["templates_dir"], exist_ok=True) 
            os.makedirs(self.config["clients_dir"], exist_ok=True)
            QMessageBox.information(self, "Paramètres Sauvegardés", "Nouveaux paramètres enregistrés.")
            
    def open_template_manager_dialog(self): TemplateDialog(self).exec_() 
        
    def open_status_manager_dialog(self): 
        QMessageBox.information(self, "Gestion des Statuts", "Fonctionnalité de gestion des statuts personnalisés à implémenter (e.g., via un nouveau QDialog).")
            
    def closeEvent(self, event): 
        save_config(self.config) 
        super().closeEvent(event)

class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None): 
        super().__init__(parent)
        self.setWindowTitle(self.tr("Paramètres de l'Application")); self.setMinimumSize(500, 400)
        self.current_config_data = current_config 
        self.setup_ui_settings() 
        
    def setup_ui_settings(self): 
        layout = QVBoxLayout(self); tabs_widget = QTabWidget(); layout.addWidget(tabs_widget) 
        
        general_tab_widget = QWidget(); general_form_layout = QFormLayout(general_tab_widget) 
        self.templates_dir_input = QLineEdit(self.current_config_data["templates_dir"]) 
        templates_browse_btn = QPushButton(self.tr("Parcourir...")); templates_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.templates_dir_input, self.tr("Sélectionner dossier modèles")))
        templates_dir_layout = QHBoxLayout(); templates_dir_layout.addWidget(self.templates_dir_input); templates_dir_layout.addWidget(templates_browse_btn) 
        general_form_layout.addRow(self.tr("Dossier des Modèles:"), templates_dir_layout)
        
        self.clients_dir_input = QLineEdit(self.current_config_data["clients_dir"]) 
        clients_browse_btn = QPushButton(self.tr("Parcourir...")); clients_browse_btn.clicked.connect(lambda: self.browse_directory_for_input(self.clients_dir_input, self.tr("Sélectionner dossier clients")))
        clients_dir_layout = QHBoxLayout(); clients_dir_layout.addWidget(self.clients_dir_input); clients_dir_layout.addWidget(clients_browse_btn) 
        general_form_layout.addRow(self.tr("Dossier des Clients:"), clients_dir_layout)

        self.interface_lang_combo = QComboBox()
        # Supported languages: French, English, Arabic, Turkish, Portuguese
        self.lang_display_to_code = {
            self.tr("Français (fr)"): "fr",
            self.tr("English (en)"): "en",
            self.tr("العربية (ar)"): "ar",
            self.tr("Türkçe (tr)"): "tr",
            self.tr("Português (pt)"): "pt"
        }
        self.interface_lang_combo.addItems(list(self.lang_display_to_code.keys()))

        current_lang_code = self.current_config_data.get("language", "fr") # Default to 'fr' if not set
        
        # Find the display text for the current language code to set the combo box
        # This creates a reverse mapping from code to display text for initial setting
        code_to_display_text = {code: display for display, code in self.lang_display_to_code.items()}

        current_display_text = code_to_display_text.get(current_lang_code)
        if current_display_text:
            self.interface_lang_combo.setCurrentText(current_display_text)
        else:
            # Fallback if current_lang_code from config isn't in our map (e.g. old config value)
            # Set to French display text by default
            french_display_text = code_to_display_text.get("fr", list(self.lang_display_to_code.keys())[0]) # Get "Français (fr)" or first item
            self.interface_lang_combo.setCurrentText(french_display_text)

        general_form_layout.addRow(self.tr("Langue Interface (redémarrage requis):"), self.interface_lang_combo)
        
        self.reminder_days_spinbox = QSpinBox(); self.reminder_days_spinbox.setRange(1, 365) 
        self.reminder_days_spinbox.setValue(self.current_config_data.get("default_reminder_days", 30))
        general_form_layout.addRow(self.tr("Jours avant rappel client ancien:"), self.reminder_days_spinbox)
        tabs_widget.addTab(general_tab_widget, self.tr("Général"))
        
        email_tab_widget = QWidget(); email_form_layout = QFormLayout(email_tab_widget) 
        self.smtp_server_input_field = QLineEdit(self.current_config_data.get("smtp_server", "")) 
        email_form_layout.addRow(self.tr("Serveur SMTP:"), self.smtp_server_input_field)
        self.smtp_port_spinbox = QSpinBox(); self.smtp_port_spinbox.setRange(1, 65535) 
        self.smtp_port_spinbox.setValue(self.current_config_data.get("smtp_port", 587))
        email_form_layout.addRow(self.tr("Port SMTP:"), self.smtp_port_spinbox)
        self.smtp_user_input_field = QLineEdit(self.current_config_data.get("smtp_user", "")) 
        email_form_layout.addRow(self.tr("Utilisateur SMTP:"), self.smtp_user_input_field)
        self.smtp_pass_input_field = QLineEdit(self.current_config_data.get("smtp_password", "")) 
        self.smtp_pass_input_field.setEchoMode(QLineEdit.Password)
        email_form_layout.addRow(self.tr("Mot de passe SMTP:"), self.smtp_pass_input_field)
        tabs_widget.addTab(email_tab_widget, self.tr("Email"))
        
        dialog_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog_button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK"))
        dialog_button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        dialog_button_box.accepted.connect(self.accept); dialog_button_box.rejected.connect(self.reject)
        layout.addWidget(dialog_button_box)
        
    def browse_directory_for_input(self, line_edit_target, dialog_title):
        dir_path = QFileDialog.getExistingDirectory(self, dialog_title, line_edit_target.text())
        if dir_path: line_edit_target.setText(dir_path)
            
    def get_config(self):
        # Get the current display text from combo box and map it back to language code
        selected_lang_display_text = self.interface_lang_combo.currentText()
        language_code = self.lang_display_to_code.get(selected_lang_display_text, "fr") # Default to fr if something goes wrong
        return {
            "templates_dir": self.templates_dir_input.text(), "clients_dir": self.clients_dir_input.text(),
            "language": language_code,
            "default_reminder_days": self.reminder_days_spinbox.value(),
            "smtp_server": self.smtp_server_input_field.text(), "smtp_port": self.smtp_port_spinbox.value(),
            "smtp_user": self.smtp_user_input_field.text(), "smtp_password": self.smtp_pass_input_field.text()
        }

def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Determine language for translations
    language_code = CONFIG.get("language", QLocale.system().name().split('_')[0]) # Default to system or 'en' if system locale is odd

    app = QApplication(sys.argv)
    app.setApplicationName("ClientDocManager")
    app.setStyle("Fusion")

    # Setup translations
    translator = QTranslator()
    translation_path = os.path.join(APP_ROOT_DIR, "translations", f"app_{language_code}.qm")
    if translator.load(translation_path):
        app.installTranslator(translator)
    else:
        print(f"Failed to load custom translation for {language_code} from {translation_path}")
        # Fallback or load default internal strings if needed

    qt_translator = QTranslator()
    qt_translation_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qt_translator.load(QLocale(language_code), "qtbase", "_", qt_translation_path):
        app.installTranslator(qt_translator)
    else:
        print(f"Failed to load Qt base translations for {language_code} from {qt_translation_path}")

    # Create new template directories and copy French templates
    TARGET_LANGS_TO_POPULATE = ["en", "pt"] # Only populate these new ones
    SOURCE_LANG_DIR_CODE = "fr"
    base_templates_dir = CONFIG["templates_dir"]
    source_lang_full_path = os.path.join(base_templates_dir, SOURCE_LANG_DIR_CODE)

    if os.path.exists(source_lang_full_path):
        for target_lang_code in TARGET_LANGS_TO_POPULATE:
            target_lang_dir_path = os.path.join(base_templates_dir, target_lang_code)
            os.makedirs(target_lang_dir_path, exist_ok=True)

            for filename in os.listdir(source_lang_full_path):
                source_file = os.path.join(source_lang_full_path, filename)
                destination_file = os.path.join(target_lang_dir_path, filename)
                if os.path.isfile(source_file): # Ensure it's a file
                    # Copy only if the destination file doesn't already exist for these specific target languages
                    # For 'ar' and 'tr', we assume they might have been populated by previous logic or manually
                    if not os.path.exists(destination_file):
                        try:
                            shutil.copy2(source_file, destination_file)
                            print(f"Copied '{filename}' to '{target_lang_code}' directory.")
                        except Exception as e:
                            print(f"Error copying '{filename}' to '{target_lang_code}': {e}")
    else:
        print(f"Source French template directory '{source_lang_full_path}' does not exist. Cannot copy templates.")


    templates_root_dir = CONFIG["templates_dir"]
    # Update default_langs to include all supported languages for initial template check/creation
    # The original default_langs was ["fr", "ar", "tr"]. Now it should be all languages supported by TemplateDialog.
    # This part ensures that if any default Excel/Word templates are missing for *any* language dir, they are created.
    # This might be redundant if the copying above already populates "en" and "pt" and if "ar", "tr" are expected to be handled.
    # However, this ensures that at least the basic structure (empty files or from default_templates_data) exists.
    all_supported_template_langs = ["fr", "en", "ar", "tr", "pt"]
    
    default_templates_data = {
        SPEC_TECH_TEMPLATE_NAME: pd.DataFrame({'Section': ["Info Client", "Détails Tech"], 'Champ': ["Nom:", "Exigence:"], 'Valeur': ["{NOM_CLIENT}", ""]}),
        PROFORMA_TEMPLATE_NAME: pd.DataFrame({'Article': ["Produit A"], 'Qté': [1], 'PU': [10.0], 'Total': [10.0]}),
        CONTRAT_VENTE_TEMPLATE_NAME: pd.DataFrame({'Clause': ["Objet"], 'Description': ["Vente de ..."]}),
        PACKING_LISTE_TEMPLATE_NAME: pd.DataFrame({'Colis': [1], 'Contenu': ["Marchandise X"], 'Poids': [5.0]})
    }

    for lang_code in all_supported_template_langs:
        lang_specific_dir = os.path.join(templates_root_dir, lang_code)
        os.makedirs(lang_specific_dir, exist_ok=True)
        for template_file_name, df_content in default_templates_data.items(): 
            template_full_path = os.path.join(lang_specific_dir, template_file_name) 
            if not os.path.exists(template_full_path):
                try:
                    df_content.to_excel(template_full_path, index=False)
                except Exception as e: print(f"Erreur création template {template_file_name} pour {lang_code}: {str(e)}")
    
    main_window = DocumentManager() 
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()