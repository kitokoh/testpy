# -*- coding: utf-8 -*-
import sys
import os
import json
# import sqlite3 # Replaced by db_manager
import db as db_manager
from db import get_default_company # Added for fetching default company
from db import DATABASE_NAME as CENTRAL_DATABASE_NAME
import pandas as pd
from PyQt5.QtWidgets import QFrame
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QListWidget, QTreeWidget, QTreeWidgetItem, # Added QTreeWidget, QTreeWidgetItem
    QFileDialog, QMessageBox, QDialog, QFormLayout, QComboBox,
    QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QInputDialog, QSplitter,
    QCompleter, QTabWidget, QAction, QMenu, QToolBar, QGroupBox,
    QCheckBox, QDateEdit, QSpinBox, QStackedWidget, QListWidgetItem,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem, QGridLayout, QTextEdit
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QColor, QBrush, QPixmap
from PyQt5.QtCore import Qt, QUrl, QStandardPaths, QSettings, QDir, QDate, QTimer, QFile, QTextStream
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
from company_management import CompanyTabWidget # Added for Company Management
from datetime import datetime # Ensure datetime is explicitly imported if not already for populate_docx_template
from projectManagement import MainDashboard as ProjectManagementDashboard # Added for integration
from html_to_pdf_util import convert_html_to_pdf # For PDF generation from HTML

import sqlite3
import logging
import logging.handlers

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


def setup_logging():
    """Configures logging for the application."""
    log_file_name = "client_manager_app.log"
    log_format = "%(asctime)s - %(levelname)s - [%(module)s:%(lineno)d] - %(message)s"
    
    # Configure root logger
    logging.basicConfig(level=logging.DEBUG, format=log_format, stream=sys.stderr) # Basic config for console (stderr)

    # File Handler - Rotate through 3 files of 1MB each
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_name, maxBytes=1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO) # Log INFO and above to file
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console Handler - Only for ERROR and CRITICAL
    console_handler = logging.StreamHandler(sys.stderr) # Explicitly use stderr for errors
    console_handler.setLevel(logging.ERROR) # Log ERROR and CRITICAL to console
    console_handler.setFormatter(logging.Formatter(log_format))

    # Add handlers to the root logger
    # Check if handlers already exist to avoid duplication if this function is called multiple times
    # (though it should only be called once)
    root_logger = logging.getLogger()
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) and h.baseFilename.endswith(log_file_name) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)
    if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stderr for h in root_logger.handlers):
        # Remove basicConfig's default stream handler if it exists and we are adding our own stderr
        for handler in root_logger.handlers[:]: # Iterate over a copy
            if isinstance(handler, logging.StreamHandler) and handler.stream in (sys.stdout, sys.stderr) and handler.formatter._fmt == logging.BASIC_FORMAT:
                root_logger.removeHandler(handler)
        root_logger.addHandler(console_handler)

    logging.info("Logging configured.")

def load_stylesheet_global(app):
    """Loads the global stylesheet."""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    qss_file_path = os.path.join(script_dir, "style.qss")
    
    if not os.path.exists(qss_file_path):
        print(f"Stylesheet file not found: {qss_file_path}")
        # Create an empty style.qss if it doesn't exist to avoid crashing
        # In a real scenario, this might be handled differently (e.g., error message, default style)
        try:
            with open(qss_file_path, "w", encoding="utf-8") as f:
                f.write("/* Default empty stylesheet. Will be populated by the application. */")
            print(f"Created an empty default stylesheet: {qss_file_path}")
        except IOError as e:
            print(f"Error creating default stylesheet {qss_file_path}: {e}")
            return # Cannot proceed if stylesheet cannot be created or read

    file = QFile(qss_file_path)
    if file.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(file)
        stylesheet = stream.readAll()
        app.setStyleSheet(stylesheet)
        print(f"Stylesheet loaded successfully from {qss_file_path}")
        file.close()
    else:
        print(f"Failed to open stylesheet file: {qss_file_path}, Error: {file.errorString()}")

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
os.makedirs(os.path.join(APP_ROOT_DIR, "company_logos"), exist_ok=True) # Create company_logos directory

class ContactDialog(QDialog):
    def __init__(self, client_id=None, contact_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.contact_data = contact_data or {}
        if self.contact_data:
            self.setWindowTitle(self.tr("Modifier Contact"))
        else:
            self.setWindowTitle(self.tr("Ajouter Contact"))
        self.setMinimumSize(450, 380) # Adjusted height for header and button frame
        self.setup_ui()

    def _create_icon_label_widget(self, icon_name, label_text):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        icon_label = QLabel()
        icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16, 16))
        layout.addWidget(icon_label)
        layout.addWidget(QLabel(label_text))
        return widget
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self) # Changed to QVBoxLayout for header + form + button frame
        main_layout.setSpacing(15)

        # UI Enhancement: Header Added
        header_label = QLabel(self.tr("Ajouter Nouveau Contact") if not self.contact_data else self.tr("Modifier Détails Contact"))
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin-bottom: 10px; color: #333;")
        main_layout.addWidget(header_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(10, 0, 10, 0) # Add some horizontal margins to the form

        # Consistent padding for input widgets
        input_style = "QLineEdit, QCheckBox { padding: 3px; }"
        self.setStyleSheet(input_style) # Apply to dialog for all children
        
        # UI Enhancement: Icons Added
        self.name_input = QLineEdit(self.contact_data.get("name", ""))
        form_layout.addRow(self._create_icon_label_widget("user", self.tr("Nom complet:")), self.name_input)
        
        self.email_input = QLineEdit(self.contact_data.get("email", ""))
        form_layout.addRow(self._create_icon_label_widget("mail-message-new", self.tr("Email:")), self.email_input)
        
        self.phone_input = QLineEdit(self.contact_data.get("phone", ""))
        form_layout.addRow(self._create_icon_label_widget("phone", self.tr("Téléphone:")), self.phone_input)
        
        self.position_input = QLineEdit(self.contact_data.get("position", ""))
        form_layout.addRow(self._create_icon_label_widget("preferences-desktop-user", self.tr("Poste:")), self.position_input) # Using a generic user-related icon
        
        self.primary_check = QCheckBox(self.tr("Contact principal"))
        self.primary_check.setChecked(bool(self.contact_data.get("is_primary", 0)))
        # UI Enhancement: Visual Cue for Primary Contact
        self.primary_check.stateChanged.connect(self.update_primary_contact_visuals)
        form_layout.addRow(self._create_icon_label_widget("emblem-important", self.tr("Principal:")), self.primary_check) # Icon for primary status
        
        main_layout.addLayout(form_layout)
        main_layout.addStretch() # Add stretch before the button frame

        # UI Enhancement: Improved Button Grouping
        button_frame = QFrame(self)
        button_frame.setObjectName("buttonFrame") # For potential specific styling if needed
        button_frame.setStyleSheet("#buttonFrame { border-top: 1px solid #cccccc; padding-top: 10px; margin-top: 10px; }")
        button_frame_layout = QHBoxLayout(button_frame)
        button_frame_layout.setContentsMargins(0,0,0,0) # No margins for the layout within the frame

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText(self.tr("OK"))
        ok_button.setIcon(QIcon.fromTheme("dialog-ok-apply"))
        ok_button.setObjectName("primaryButton") # Apply primary button style
        # ok_button.setStyleSheet("background-color: #27ae60; color: white; padding: 5px 15px;") # Removed for global style


        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText(self.tr("Annuler"))
        cancel_button.setIcon(QIcon.fromTheme("dialog-cancel"))
        # cancel_button.setStyleSheet("padding: 5px 15px;") # Rely on global style

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        button_frame_layout.addWidget(button_box)
        main_layout.addWidget(button_frame)

        self.update_primary_contact_visuals(self.primary_check.checkState()) # Set initial visual state
        # UI Enhancements Applied

    def update_primary_contact_visuals(self, state):
        if state == Qt.Checked:
            self.name_input.setStyleSheet("background-color: #e6ffe6; padding: 3px;") # Light green
        else:
            self.name_input.setStyleSheet("padding: 3px;") # Revert to default padding style

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
        self.setMinimumSize(800, 500) # Increased size to accommodate preview
        self.setup_ui()
        
    def setup_ui(self):
        main_hbox_layout = QHBoxLayout(self) # Main layout is now QHBoxLayout

        # Left side (list and buttons)
        left_vbox_layout = QVBoxLayout()
        left_vbox_layout.setSpacing(10) # Good.

        self.template_list = QTreeWidget()
        self.template_list.setColumnCount(4)
        self.template_list.setHeaderLabels([self.tr("Name"), self.tr("Type"), self.tr("Language"), self.tr("Default Status")])

        header = self.template_list.header() # Get header for styling
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.template_list.setAlternatingRowColors(True) # Enable alternating row colors
        
        font = self.template_list.font()
        font.setPointSize(font.pointSize() + 1)
        self.template_list.setFont(font)
        left_vbox_layout.addWidget(self.template_list)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8) # Slightly tighter buttons

        self.add_btn = QPushButton(self.tr("Ajouter")) # Text updated
        self.add_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_btn.setToolTip(self.tr("Ajouter un nouveau modèle"))
        self.add_btn.setObjectName("primaryButton") # Style as primary
        self.add_btn.clicked.connect(self.add_template)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton(self.tr("Modifier")) # Text updated
        self.edit_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_btn.setToolTip(self.tr("Modifier le modèle sélectionné (ouvre le fichier externe)"))
        self.edit_btn.clicked.connect(self.edit_template)
        self.edit_btn.setEnabled(False)
        btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton(self.tr("Supprimer")) # Text updated
        self.delete_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.delete_btn.setToolTip(self.tr("Supprimer le modèle sélectionné"))
        self.delete_btn.setObjectName("dangerButton") # Style as danger
        self.delete_btn.clicked.connect(self.delete_template)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)
        
        self.default_btn = QPushButton(self.tr("Par Défaut")) # Text updated
        self.default_btn.setIcon(QIcon.fromTheme("emblem-default")) # Alternative: "star"
        self.default_btn.setToolTip(self.tr("Définir le modèle sélectionné comme modèle par défaut pour sa catégorie et langue"))
        self.default_btn.clicked.connect(self.set_default_template)
        self.default_btn.setEnabled(False)
        btn_layout.addWidget(self.default_btn)
        
        left_vbox_layout.addLayout(btn_layout)
        main_hbox_layout.addLayout(left_vbox_layout, 1)

        # Right side (preview area)
        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
        self.preview_area.setStyleSheet( # Updated stylesheet
            "QTextEdit {"
            "    border: 1px solid #cccccc;"
            "    background-color: #f9f9f9;"
            "    padding: 5px;"
            "}"
        )
        main_hbox_layout.addWidget(self.preview_area, 2)

        # Set overall dialog layout margins
        main_hbox_layout.setContentsMargins(15, 15, 15, 15) # More padding

        self.load_templates()
        self.template_list.currentItemChanged.connect(self.handle_tree_item_selection) # Changed signal

    def handle_tree_item_selection(self, current_item, previous_item):
        if current_item is not None and current_item.parent() is not None: # It's a child (template) item
            self.show_template_preview(current_item)
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
            self.default_btn.setEnabled(True)
        else: # It's a category item or selection cleared
            self.preview_area.clear()
            self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.default_btn.setEnabled(False)

    def show_template_preview(self, item):
        if not item: # Should be caught by handle_tree_item_selection, but good practice
            self.preview_area.clear()
            self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
            return

        template_id = item.data(0, Qt.UserRole) # Data is in column 0 for QTreeWidgetItems
        if template_id is None: # It's a category item or item without template_id
            self.preview_area.clear()
            self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
            return

        # conn = None # No longer needed here
        try:
            # conn = sqlite3.connect(DATABASE_NAME) # Replaced
            # cursor = conn.cursor() # Replaced
            # # Use base_file_name and language_code as per table structure, aliasing language_code to language for consistency with other methods if needed
            # cursor.execute("SELECT base_file_name, language_code FROM Templates WHERE template_id = ?", (template_id,)) # Replaced
            # result = cursor.fetchone() # Replaced
            details = db_manager.get_template_details_for_preview(template_id)

            if details:
                base_file_name = details['base_file_name']
                language_code = details['language_code']
                # template_file_path = os.path.join(CONFIG["templates_dir"], language_code, base_file_name) # Path construction remains the same

                # The rest of the path and file handling logic remains the same
                template_file_path = os.path.join(CONFIG["templates_dir"], language_code, base_file_name)
                self.preview_area.clear()
                if os.path.exists(template_file_path):
                    _, file_extension = os.path.splitext(template_file_path)
                    file_extension = file_extension.lower()

                    if file_extension == ".xlsx":
                        try:
                            df = pd.read_excel(template_file_path, sheet_name=0) # Read first sheet
                            # PREPEND CSS for basic styling
                            html_content = f"""
                            <style>
                                table {{ border-collapse: collapse; width: 95%; font-family: Arial, sans-serif; margin: 10px; }} /* Adjusted width and added margin */
                                th, td {{ border: 1px solid #cccccc; padding: 6px; text-align: left; }} /* Reduced padding slightly */
                                th {{ background-color: #e0e0e0; font-weight: bold; }} /* Slightly darker header, bold text */
                                td {{ text-align: right; }} /* Default text-align right for cells */
                                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                                tr:hover {{ background-color: #e6f7ff; }} /* Add a hover effect for rows */
                            </style>
                            {df.to_html(escape=False, index=False, border=0)}
                            """ # border=0 for df.to_html because CSS handles it
                            self.preview_area.setHtml(html_content)
                        except Exception as e:
                            self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Excel:\n{0}").format(str(e)))
                    elif file_extension == ".docx":
                        try:
                            doc = Document(template_file_path)
                            full_text = []
                            for para in doc.paragraphs:
                                full_text.append(para.text)
                            self.preview_area.setPlainText("\n".join(full_text))
                        except Exception as e:
                            self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Word:\n{0}").format(str(e)))
                    elif file_extension == ".html":
                        try:
                            with open(template_file_path, "r", encoding="utf-8") as f:
                                self.preview_area.setPlainText(f.read())
                        except Exception as e:
                            self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier HTML:\n{0}").format(str(e)))
                    else:
                        self.preview_area.setPlainText(self.tr("Aperçu non disponible pour ce type de fichier."))
                else:
                    self.preview_area.setPlainText(self.tr("Fichier modèle introuvable."))
            else:
                self.preview_area.setPlainText(self.tr("Détails du modèle non trouvés dans la base de données."))

        # except sqlite3.Error as e_db: # Replaced by db_manager's error handling (prints to console)
            # self.preview_area.setPlainText(self.tr("Erreur DB lors de la récupération des détails du modèle:\n{0}").format(str(e_db)))
        except Exception as e_general: # Catch any other unexpected errors, including those from db_manager if they are not caught by db_manager itself
            self.preview_area.setPlainText(self.tr("Une erreur est survenue lors de la récupération des détails du modèle:\n{0}").format(str(e_general)))
        # finally: # conn is no longer managed here
            # if conn:
                # conn.close()

    # def update_preview(self, current_item, previous_item): # Original currentItemChanged connection
    #     if not current_item:
    #         self.preview_area.clear()
    #         return
    #     template_id = current_item.data(Qt.UserRole)
    #     # TODO: Fetch template content based on ID and display it (Handled by show_template_preview now)
    #     # This will likely involve reading the template file
    #     # For now, just showing the ID as placeholder
    #     # self.preview_area.setText(f"Preview for Template ID: {template_id}\n\n(Content loading not yet implemented)")
    #     self.show_template_preview(current_item) # Call the new method if using currentItemChanged

    def load_templates(self):
        self.template_list.clear()
        self.preview_area.clear()
        self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))

        categories = db_manager.get_all_template_categories()
        if categories is None: categories = []

        if not categories:
            # Optionally, add a "General" category if none exist, or inform the user.
            # For now, we assume "General" is created by db.py's initialize_database.
            # If still no categories, the tree will be empty.
            # A message could be shown: self.template_list.addTopLevelItem(QTreeWidgetItem([self.tr("No categories found")]))
            pass

        for category_dict in categories:
            category_item = QTreeWidgetItem(self.template_list, [category_dict['category_name']])
            # Category items are not selectable for actions like edit/delete template
            # category_item.setFlags(category_item.flags() & ~Qt.ItemIsSelectable) # This makes them non-selectable by mouse click for currentItemChanged
            # Instead, we check item.parent() in handle_tree_item_selection

            templates_in_category = db_manager.get_templates_by_category_id(category_dict['category_id'])
            if templates_in_category is None: templates_in_category = []

            for template_dict in templates_in_category:
                template_name = template_dict['template_name']
                template_type = template_dict.get('template_type', 'N/A')
                language = template_dict['language_code']
                is_default = self.tr("Yes") if template_dict.get('is_default_for_type_lang') else self.tr("No")

                template_item = QTreeWidgetItem(category_item, [template_name, template_type, language, is_default])
                template_item.setData(0, Qt.UserRole, template_dict['template_id'])

        self.template_list.expandAll()
        # Ensure buttons are correctly disabled initially as no item is selected by default
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.default_btn.setEnabled(False)
            
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

        # Category Selection
        existing_categories = db_manager.get_all_template_categories()
        if existing_categories is None: existing_categories = [] # Handle case where db query fails

        category_display_list = [cat['category_name'] for cat in existing_categories]
        create_new_option = self.tr("[Create New Category...]")
        category_display_list.append(create_new_option)

        selected_category_name, ok = QInputDialog.getItem(self, self.tr("Select Template Category"),
                                                          self.tr("Category:"), category_display_list, 0, False)
        if not ok: return

        final_category_id = None
        if selected_category_name == create_new_option:
            new_category_text, ok_new = QInputDialog.getText(self, self.tr("New Category"), self.tr("Enter name for new category:"))
            if ok_new and new_category_text.strip():
                final_category_id = db_manager.add_template_category(new_category_text.strip())
                if not final_category_id:
                    QMessageBox.warning(self, self.tr("Error"), self.tr("Could not create or find category: {0}").format(new_category_text.strip()))
                    return
            else:
                return # User cancelled new category creation
        else:
            for cat in existing_categories:
                if cat['category_name'] == selected_category_name:
                    final_category_id = cat['category_id']
                    break
            if final_category_id is None:
                QMessageBox.critical(self, self.tr("Error"), self.tr("Selected category not found internally. Please ensure 'General' category exists or create a new one."))
                return

        # Language Selection (moved after category)
        languages = ["fr", "en", "ar", "tr", "pt"]
        lang, ok = QInputDialog.getItem(self, self.tr("Langue du Modèle"), self.tr("Sélectionnez la langue:"), languages, 0, False)
        if not ok: return
            
        target_dir = os.path.join(CONFIG["templates_dir"], lang)
        os.makedirs(target_dir, exist_ok=True)
        base_file_name = os.path.basename(file_path) 
        target_path = os.path.join(target_dir, base_file_name) 

        # Determine template_type based on file extension
        file_ext = os.path.splitext(base_file_name)[1].lower()
        template_type_for_db = "document_other" # Default
        if file_ext == ".xlsx":
            template_type_for_db = "document_excel"
        elif file_ext == ".docx":
            template_type_for_db = "document_word"
        elif file_ext == ".html":
            template_type_for_db = "document_html"

        template_metadata = {
            'template_name': name.strip(), # This is the user-provided name for the template
            'template_type': template_type_for_db,
            'language_code': lang,
            'base_file_name': base_file_name, # The actual file name
            'description': f"Modèle {name.strip()} en {lang} ({base_file_name})", # Basic description
            'category_id': final_category_id, # Use the determined category_id
            'is_default_for_type_lang': False # User-added templates are not default by default
            # 'raw_template_file_data': None, # Not storing file content in DB for this path
            # 'created_by_user_id': None # Add if user system is integrated here
        }
        # Ensure old 'category' text field is not accidentally passed if it was in template_metadata before
        template_metadata.pop('category', None)


        try:
            # First, copy the file
            shutil.copy(file_path, target_path)

            # Then, add metadata to database via db_manager
            new_template_id = db_manager.add_template(template_metadata)

            if new_template_id:
                self.load_templates() # Refresh list
                QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle ajouté avec succès."))
            else:
                # db_manager.add_template would print its own errors or return None on failure.
                # If new_template_id is None, it means there was an issue (e.g., unique constraint).
                # The db.py function might need adjustment to differentiate between "already exists" and "other error".
                # For now, assume if it's None, it's an error the user should know about.
                # If file was copied but DB entry failed, consider removing the copied file.
                if os.path.exists(target_path): # Check if file was copied before potential DB error
                     is_error_because_exists = False
                     # Check if a template with the same name, type, and language already exists
                     # This requires a way to query templates, e.g., get_templates_by_type_lang_name
                     # For simplicity, we'll assume add_template failing with None means either unique constraint or other DB error.
                     # A more robust check would be:
                     # existing_templates = db_manager.get_templates_by_type(template_type_for_db, language_code=lang)
                     # if existing_templates:
                     #    for tpl in existing_templates:
                     #        if tpl.get('template_name') == name.strip(): # and other unique fields if necessary
                     #            is_error_because_exists = True
                     #            break
                     # A direct check for unique constraint violation in db_manager.add_template would be better.
                     # For now, providing a generic message or trying to infer.
                     # A simple check: if a template with this name+type+lang exists, it's likely a unique conflict.

                     # Simplified check:
                     # This is not ideal as it re-queries. db_manager.add_template should ideally signal this.
                     # For now, we'll assume if add_template returns None, it's an issue.
                     # The user will get a generic DB error. A more specific "already exists" would need db.add_template to provide more info.
                     QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur lors de l'enregistrement du modèle dans la base de données. Un modèle avec des attributs similaires (nom, type, langue) existe peut-être déjà, ou une autre erreur de base de données s'est produite."))
                     # Consider removing the copied file if DB entry failed:
                     # os.remove(target_path)
                else: # File copy itself might have failed before DB
                    QMessageBox.critical(self, self.tr("Erreur Fichier"), self.tr("Erreur lors de la copie du fichier modèle."))

        except Exception as e: # Catch errors from shutil.copy or other unexpected issues
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout du modèle (fichier ou DB):\n{0}").format(str(e)))
            
    def edit_template(self): 
        current_item = self.template_list.currentItem()
        if not current_item or not current_item.parent(): # Check if it's a child item
            QMessageBox.warning(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un modèle (et non une catégorie) à modifier."))
            return
        template_id = current_item.data(0, Qt.UserRole)
        if template_id is None: return # Should not happen if parent check passed

        # conn = None # Replaced
        try:
            # conn = sqlite3.connect(DATABASE_NAME) # Replaced
            # cursor = conn.cursor() # Replaced
            # cursor.execute("SELECT file_name, language FROM Templates WHERE template_id = ?", (template_id,)) # Replaced
            # result = cursor.fetchone() # Replaced
            path_info = db_manager.get_template_path_info(template_id)
            if path_info:
                # path_info contains {'file_name': 'name.xlsx', 'language': 'fr'}
                template_file_path = os.path.join(CONFIG["templates_dir"], path_info['language'], path_info['file_name'])
                QDesktopServices.openUrl(QUrl.fromLocalFile(template_file_path))
            else:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer les informations du modèle pour l'édition."))
        # except sqlite3.Error as e: # Replaced by db_manager's error handling
            # QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur d'accès au modèle:\n{str(e)}"))
        except Exception as e:
             QMessageBox.warning(self, self.tr("Erreur"), self.tr("Erreur lors de l'ouverture du modèle:\n{0}").format(str(e)))
        # finally: # conn is no longer managed here
            # if conn: conn.close()
            
    def delete_template(self):
        current_item = self.template_list.currentItem()
        if not current_item or not current_item.parent(): # Check if it's a child item
            QMessageBox.warning(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un modèle (et non une catégorie) à supprimer."))
            return
        template_id = current_item.data(0, Qt.UserRole)
        if template_id is None: return

        reply = QMessageBox.question(
            self,
            self.tr("Confirmer Suppression"),
            self.tr("Êtes-vous sûr de vouloir supprimer ce modèle ?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # conn = None # Replaced
            try:
                # conn = sqlite3.connect(DATABASE_NAME) # Replaced
                # cursor = conn.cursor() # Replaced
                # cursor.execute("SELECT file_name, language FROM Templates WHERE template_id = ?", (template_id,)) # Replaced
                # result = cursor.fetchone() # Replaced
                # cursor.execute("DELETE FROM Templates WHERE template_id = ?", (template_id,)) # Replaced
                # conn.commit() # Replaced

                file_info = db_manager.delete_template_and_get_file_info(template_id)

                if file_info:
                    file_path_to_delete = os.path.join(CONFIG["templates_dir"], file_info['language'], file_info['file_name'])
                    if os.path.exists(file_path_to_delete):
                        os.remove(file_path_to_delete)
                    self.load_templates()
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle supprimé avec succès."))
                else:
                    # db_manager.delete_template_and_get_file_info would print its own error or if template not found.
                    QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur de suppression du modèle. Il est possible que le modèle n'ait pas été trouvé ou qu'une erreur de base de données se soit produite."))
            except Exception as e: 
                QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur de suppression du modèle:\n{0}").format(str(e)))
            # finally: # conn is no longer managed here
                # if conn: conn.close()
                
    def set_default_template(self):
        current_item = self.template_list.currentItem()
        if not current_item or not current_item.parent(): # Check if it's a child item
            QMessageBox.warning(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un modèle (et non une catégorie) à définir par défaut."))
            return
        template_id = current_item.data(0, Qt.UserRole)
        if template_id is None: return

        # conn = None # Replaced
        try:
            # conn = sqlite3.connect(DATABASE_NAME) # Replaced
            # cursor = conn.cursor() # Replaced
            # cursor.execute("SELECT template_name FROM Templates WHERE template_id = ?", (template_id,)) # Logic moved to db_manager
            # name_result = cursor.fetchone() # Logic moved
            # if not name_result: return # Logic moved
            # base_name = name_result[0] # Logic moved
            
            # cursor.execute("UPDATE Templates SET is_default_for_type_lang = 0 WHERE template_name = ?", (base_name,)) # Logic moved
            # cursor.execute("UPDATE Templates SET is_default_for_type_lang = 1 WHERE template_id = ?", (template_id,)) # Logic moved
            # conn.commit() # Logic moved

            success = db_manager.set_default_template_by_id(template_id)

            if success:
                self.load_templates()
                QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle défini comme modèle par défaut pour sa catégorie et langue."))
            else:
                # db_manager.set_default_template_by_id would print its own error or if template not found.
                 QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de mise à jour du modèle. Le modèle n'a peut-être pas été trouvé ou une erreur de base de données s'est produite."))
        # except sqlite3.Error as e: # Replaced by db_manager's error handling
            # QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de mise à jour du modèle:\n{str(e)}"))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la définition du modèle par défaut:\n{0}").format(str(e)))
        # finally: # conn is no longer managed here
            # if conn: conn.close()

class ProductDialog(QDialog):
    def __init__(self, client_id, product_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        # self.product_data = product_data or {} # Original single product data, not used for multi-line
        self.setWindowTitle(self.tr("Ajouter Produits au Client")) # Title for multi-line
        self.setMinimumSize(900, 800) # Adjusted for two-column layout
        self.client_info = db_manager.get_client_by_id(self.client_id) # Fetch client info
        # Refactor: Multi-line product entry
        self.setup_ui() # Sets up UI, including language filter combo
        self._set_initial_language_filter() # Sets default language
        self._filter_products_by_language_and_search() # Initial load based on default lang and empty search

    def _set_initial_language_filter(self):
        primary_language = None
        if self.client_info:
            client_langs = self.client_info.get('selected_languages')
            if client_langs: # This is expected to be a comma-separated string from DB
                primary_language = client_langs.split(',')[0].strip()

        if primary_language:
            for i in range(self.product_language_filter_combo.count()):
                if self.product_language_filter_combo.itemText(i) == primary_language:
                    self.product_language_filter_combo.setCurrentText(primary_language)
                    break
        # else: it will default to "All" or the first item in the combo

    def _load_existing_products(self):
        # This method's core logic has been moved to _filter_products_by_language_and_search
        # and is triggered by __init__ after initial setup.
        # This can be safely removed or left empty.
        pass

    def _filter_products_by_language_and_search(self):
        self.existing_products_list.clear()

        selected_language = self.product_language_filter_combo.currentText()
        if selected_language == self.tr("All"):
            language_code_for_db = None
        else:
            language_code_for_db = selected_language

        search_text = self.search_existing_product_input.text().lower()
        name_pattern_for_db = f"%{search_text}%" if search_text else None

        try:
            # Assuming get_all_products_for_selection can handle language_code=None and name_pattern=None
            products = db_manager.get_all_products_for_selection_filtered( # Changed to new function
                language_code=language_code_for_db,
                name_pattern=name_pattern_for_db
            )
            if products is None: products = []

            for product_data in products:
                # product_id = product_data.get('product_id')
                product_name = product_data.get('product_name', 'N/A')
                description = product_data.get('description', '')
                base_unit_price = product_data.get('base_unit_price', 0.0)
                # Ensure base_unit_price is not None before formatting
                if base_unit_price is None:
                    base_unit_price = 0.0

                # Create a more informative display string
                desc_snippet = (description[:30] + '...') if len(description) > 30 else description
                display_text = f"{product_name} (Desc: {desc_snippet}, Prix: {base_unit_price:.2f} €)"

                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, product_data) # Store the whole dictionary
                self.existing_products_list.addItem(item)
        except Exception as e:
            print(f"Error loading existing products: {e}")
            # Optionally, show a message to the user
            QMessageBox.warning(self, self.tr("Erreur Chargement Produits"),
                                self.tr("Impossible de charger la liste des produits existants:\n{0}").format(str(e)))

    def _filter_existing_products_list(self):
        search_text = self.search_existing_product_input.text().lower()
        for i in range(self.existing_products_list.count()):
            item = self.existing_products_list.item(i)
            product_data = item.data(Qt.UserRole)
            if product_data: # Check if data exists
                item_text = product_data.get('product_name', '').lower()
                item_description = product_data.get('description', '').lower()
                # Make search more comprehensive by checking name and description
                if search_text in item_text or search_text in item_description:
                    item.setHidden(False)
                else:
                    item.setHidden(True)
            else: # If no data, hide by default or handle as error
                item.setHidden(True)

    def _populate_form_from_selected_product(self, item):
        product_data = item.data(Qt.UserRole)
        if product_data:
            self.name_input.setText(product_data.get('product_name', ''))
            self.description_input.setPlainText(product_data.get('description', ''))

            base_price = product_data.get('base_unit_price', 0.0)
            try:
                self.unit_price_input.setValue(float(base_price))
            except (ValueError, TypeError):
                self.unit_price_input.setValue(0.0)

            self.quantity_input.setValue(1.0) # Default quantity for a selected product
            self.quantity_input.setFocus() # Set focus to quantity for quick input
            self._update_current_line_total_preview() # Update total preview based on populated data


    def _create_icon_label_widget(self, icon_name, label_text): # Helper for icons
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        icon_label = QLabel()
        icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16, 16))
        layout.addWidget(icon_label)
        layout.addWidget(QLabel(label_text))
        return widget

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # UI Enhancement: Header Added
        header_label = QLabel(self.tr("Ajouter Lignes de Produits"))
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin-bottom: 10px; color: #333;")
        main_layout.addWidget(header_label)

        # Two-column layout for search and form
        two_columns_layout = QHBoxLayout()

        # Left Column: Existing Product Search Group
        search_group_box = QGroupBox(self.tr("Rechercher Produit Existant"))
        search_layout = QVBoxLayout(search_group_box)

        # Language Filter for Products
        self.product_language_filter_label = QLabel(self.tr("Filtrer par langue:"))
        search_layout.addWidget(self.product_language_filter_label)
        self.product_language_filter_combo = QComboBox()
        self.product_language_filter_combo.addItems([self.tr("All"), "fr", "en", "ar", "tr", "pt"]) # TODO: Use global lang list if available
        self.product_language_filter_combo.currentTextChanged.connect(self._filter_products_by_language_and_search)
        search_layout.addWidget(self.product_language_filter_combo)

        self.search_existing_product_input = QLineEdit()
        self.search_existing_product_input.setPlaceholderText(self.tr("Tapez pour rechercher..."))
        self.search_existing_product_input.textChanged.connect(self._filter_products_by_language_and_search) # Changed connection
        search_layout.addWidget(self.search_existing_product_input)
        self.existing_products_list = QListWidget()
        self.existing_products_list.setMinimumHeight(150) # Increased height for better visibility in column
        self.existing_products_list.itemDoubleClicked.connect(self._populate_form_from_selected_product)
        search_layout.addWidget(self.existing_products_list)
        two_columns_layout.addWidget(search_group_box, 1) # Add to left, stretch factor 1

        # Right Column: Input Group for Current Product Line
        input_group_box = QGroupBox(self.tr("Détails de la Ligne de Produit Actuelle (ou Produit Sélectionné)"))
        form_layout = QFormLayout(input_group_box)
        form_layout.setSpacing(10)
        input_style = "QLineEdit, QTextEdit, QDoubleSpinBox { padding: 3px; }"
        self.setStyleSheet(input_style) # Apply to dialog
        self.name_input = QLineEdit()
        form_layout.addRow(self._create_icon_label_widget("package-x-generic", self.tr("Nom du Produit:")), self.name_input)
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(80) # Increased height for better visibility in column
        form_layout.addRow(self.tr("Description:"), self.description_input)
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0, 1000000)
        self.quantity_input.setValue(0.0)
        self.quantity_input.valueChanged.connect(self._update_current_line_total_preview)
        form_layout.addRow(self._create_icon_label_widget("format-list-numbered", self.tr("Quantité:")), self.quantity_input)
        self.unit_price_input = QDoubleSpinBox()
        self.unit_price_input.setRange(0, 10000000)
        self.unit_price_input.setPrefix("€ ")
        self.unit_price_input.setValue(0.0)
        self.unit_price_input.valueChanged.connect(self._update_current_line_total_preview)
        form_layout.addRow(self._create_icon_label_widget("cash", self.tr("Prix Unitaire:")), self.unit_price_input)
        current_line_total_title_label = QLabel(self.tr("Total Ligne Actuelle:"))
        self.current_line_total_label = QLabel("€ 0.00")
        font = self.current_line_total_label.font()
        font.setBold(True)
        self.current_line_total_label.setFont(font)
        form_layout.addRow(current_line_total_title_label, self.current_line_total_label)
        two_columns_layout.addWidget(input_group_box, 2) # Add to right, stretch factor 2 (more space for form)

        main_layout.addLayout(two_columns_layout) # Add the two-column section to the main vertical layout

        # "Add Line" Button (remains below the two columns)
        self.add_line_btn = QPushButton(self.tr("Ajouter Produit à la Liste"))
        self.add_line_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_line_btn.setObjectName("primaryButton") # Style as primary
        self.add_line_btn.clicked.connect(self._add_current_line_to_table)
        main_layout.addWidget(self.add_line_btn)

        # Table for Product Lines
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels([
            self.tr("Nom Produit"), self.tr("Description"), self.tr("Qté"),
            self.tr("Prix Unitaire"), self.tr("Total Ligne")
        ])
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.products_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.products_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.products_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.products_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        main_layout.addWidget(self.products_table)

        # "Remove Selected Line" Button
        self.remove_line_btn = QPushButton(self.tr("Supprimer Produit Sélectionné"))
        self.remove_line_btn.setIcon(QIcon.fromTheme("list-remove"))
        self.remove_line_btn.setStyleSheet("padding: 5px 10px;")
        self.remove_line_btn.clicked.connect(self._remove_selected_line_from_table)
        main_layout.addWidget(self.remove_line_btn)

        # Overall Total Price Label
        self.overall_total_label = QLabel(self.tr("Total Général: € 0.00"))
        font = self.overall_total_label.font()
        font.setPointSize(font.pointSize() + 3)
        font.setBold(True)
        self.overall_total_label.setFont(font)
        self.overall_total_label.setStyleSheet("color: #2c3e50; padding: 10px 0; margin-top: 5px;")
        self.overall_total_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self.overall_total_label)

        main_layout.addStretch()

        # UI Enhancement: Improved Button Grouping (OK/Cancel)
        button_frame = QFrame(self)
        button_frame.setObjectName("buttonFrame")
        button_frame.setStyleSheet("#buttonFrame { border-top: 1px solid #cccccc; padding-top: 10px; margin-top: 10px; }")
        button_frame_layout = QHBoxLayout(button_frame)
        button_frame_layout.setContentsMargins(0,0,0,0)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setText(self.tr("OK"))
        ok_button.setIcon(QIcon.fromTheme("dialog-ok-apply"))
        ok_button.setObjectName("primaryButton") # Apply primary button style
        # ok_button.setStyleSheet("background-color: #27ae60; color: white; padding: 5px 15px;")


        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText(self.tr("Annuler"))
        cancel_button.setIcon(QIcon.fromTheme("dialog-cancel"))
        # cancel_button.setStyleSheet("padding: 5px 15px;") # Rely on global style

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_frame_layout.addWidget(button_box)
        main_layout.addWidget(button_frame)
        # Refactor: Multi-line product entry and UI Enhancements Applied

    def _update_current_line_total_preview(self):
        # Bugfix: Handle potential NoneType in price/quantity calculations
        quantity = self.quantity_input.value()
        unit_price = self.unit_price_input.value()
        current_quantity = quantity if isinstance(quantity, (int, float)) else 0.0
        current_unit_price = unit_price if isinstance(unit_price, (int, float)) else 0.0
        line_total = current_quantity * current_unit_price
        self.current_line_total_label.setText(f"€ {line_total:.2f}")

    def _add_current_line_to_table(self):
        name = self.name_input.text().strip()
        description = self.description_input.toPlainText().strip()
        quantity = self.quantity_input.value()
        unit_price = self.unit_price_input.value()

        if not name:
            QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("Le nom du produit est requis."))
            self.name_input.setFocus()
            return
        if quantity <= 0:
            QMessageBox.warning(self, self.tr("Quantité Invalide"), self.tr("La quantité doit être supérieure à zéro."))
            self.quantity_input.setFocus()
            return

        line_total = quantity * unit_price

        row_position = self.products_table.rowCount()
        self.products_table.insertRow(row_position)

        name_item = QTableWidgetItem(name)
        # Store the selected language for this product line
        current_lang_code = self.product_language_filter_combo.currentText()
        if current_lang_code == self.tr("All"): # Use a default if "All" is selected
            current_lang_code = "fr" # Or get from client_info, or a global default
        name_item.setData(Qt.UserRole + 1, current_lang_code) # Store lang_code

        self.products_table.setItem(row_position, 0, name_item)
        self.products_table.setItem(row_position, 1, QTableWidgetItem(description))

        qty_item = QTableWidgetItem(f"{quantity:.2f}") # Format to 2 decimal places for consistency
        qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.products_table.setItem(row_position, 2, qty_item)

        price_item = QTableWidgetItem(f"€ {unit_price:.2f}")
        price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.products_table.setItem(row_position, 3, price_item)

        total_item = QTableWidgetItem(f"€ {line_total:.2f}")
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.products_table.setItem(row_position, 4, total_item)

        # Clear input fields for next entry
        self.name_input.clear()
        self.description_input.clear()
        self.quantity_input.setValue(0.0)
        self.unit_price_input.setValue(0.0)
        self._update_current_line_total_preview() # Reset preview label
        self._update_overall_total()
        self.name_input.setFocus()

    def _remove_selected_line_from_table(self):
        selected_rows = self.products_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, self.tr("Aucune Sélection"), self.tr("Veuillez sélectionner une ligne à supprimer."))
            return
        for index in sorted(selected_rows, reverse=True):
            self.products_table.removeRow(index.row())
        self._update_overall_total()

    def _update_overall_total(self):
        total_sum = 0.0
        for row in range(self.products_table.rowCount()):
            item = self.products_table.item(row, 4) # Column 4 is "Line Total"
            if item and item.text():
                try:
                    # Extract float from text like "€ 123.45"
                    value_str = item.text().replace("€", "").replace(",", ".").strip() # Handle comma as decimal sep if needed
                    total_sum += float(value_str)
                except ValueError:
                    print(f"Warning: Could not parse float from table cell: {item.text()}")
        self.overall_total_label.setText(self.tr("Total Général: € {0:.2f}").format(total_sum))

    def get_data(self):
        # Refactor: Multi-line product entry - returns a list of product dicts
        products_list = []
        for row in range(self.products_table.rowCount()):
            name = self.products_table.item(row, 0).text()
            description = self.products_table.item(row, 1).text()

            qty_str = self.products_table.item(row, 2).text().replace(",", ".")
            quantity = float(qty_str) if qty_str else 0.0

            unit_price_str = self.products_table.item(row, 3).text().replace("€", "").replace(",", ".").strip()
            unit_price = float(unit_price_str) if unit_price_str else 0.0

            line_total_str = self.products_table.item(row, 4).text().replace("€", "").replace(",", ".").strip()
            line_total = float(line_total_str) if line_total_str else 0.0

            # Retrieve the stored language code
            name_item = self.products_table.item(row, 0)
            language_code = name_item.data(Qt.UserRole + 1) if name_item else "fr" # Default 'fr' if not found

            products_list.append({
                "client_id": self.client_id, # This might be redundant if the caller already has client_id
                "name": name,
                "description": description,
                "quantity": quantity,
                "unit_price": unit_price, # This is the line item unit price
                "total_price": line_total,
                "language_code": language_code # Add language code to the returned data
            })
        return products_list

class EditProductLineDialog(QDialog):
    def __init__(self, product_data, parent=None):
        super().__init__(parent)
        self.product_data = product_data # Store the passed product data
        self.setWindowTitle(self.tr("Modifier Ligne de Produit"))
        self.setMinimumSize(450, 300) # Reasonable starting size
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self) # Main layout for the dialog

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Name Input
        self.name_input = QLineEdit(self.product_data.get('name', ''))
        form_layout.addRow(self.tr("Nom du Produit:"), self.name_input)

        # Description Input
        self.description_input = QTextEdit(self.product_data.get('description', ''))
        self.description_input.setFixedHeight(80)
        form_layout.addRow(self.tr("Description:"), self.description_input)

        # Quantity Input
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0.01, 1000000) # Min quantity 0.01
        self.quantity_input.setValue(float(self.product_data.get('quantity', 1.0)))
        form_layout.addRow(self.tr("Quantité:"), self.quantity_input)

        # Unit Price Input
        self.unit_price_input = QDoubleSpinBox()
        self.unit_price_input.setRange(0.00, 10000000)
        self.unit_price_input.setPrefix("€ ")
        self.unit_price_input.setDecimals(2) # Ensure two decimal places
        self.unit_price_input.setValue(float(self.product_data.get('unit_price', 0.0)))
        form_layout.addRow(self.tr("Prix Unitaire:"), self.unit_price_input)

        layout.addLayout(form_layout)
        layout.addStretch()

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK"))
        button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)
        self.setLayout(layout)

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "quantity": self.quantity_input.value(),
            "unit_price": self.unit_price_input.value(),
            "product_id": self.product_data.get('product_id'),
            "client_project_product_id": self.product_data.get('client_project_product_id')
        }

class CreateDocumentDialog(QDialog):
    def __init__(self, client_info, config, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.config = config
        self.setWindowTitle(self.tr("Créer des Documents"))
        self.setMinimumSize(600, 500) # Adjusted size for new filters
        self._initial_load_complete = False # Flag for initial language setting
        self.setup_ui()

    def _create_icon_label_widget(self, icon_name, label_text): # Helper for icons
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        icon_label = QLabel()
        icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16, 16))
        layout.addWidget(icon_label)
        layout.addWidget(QLabel(label_text))
        return widget

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        header_label = QLabel(self.tr("Sélectionner Documents à Créer"))
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin-bottom: 10px; color: #333;")
        main_layout.addWidget(header_label)

        input_style = """
            QComboBox, QListWidget, QLineEdit { padding: 3px; }
            QListWidget::item:hover { background-color: #e6f7ff; }
        """
        self.setStyleSheet(input_style)

        # Filters and Search Layout
        filters_layout = QGridLayout()
        filters_layout.setSpacing(10)

        # Language Filter
        self.language_filter_label = QLabel(self.tr("Langue:"))
        self.language_filter_combo = QComboBox()
        self.language_filter_combo.addItems([self.tr("All"), "fr", "en", "ar", "tr", "pt"])
        # TODO: Set client's current language if desired, for now "All"
        self.language_filter_combo.setCurrentText(self.tr("All"))
        filters_layout.addWidget(self.language_filter_label, 0, 0)
        filters_layout.addWidget(self.language_filter_combo, 0, 1)

        # Extension Filter
        self.extension_filter_label = QLabel(self.tr("Extension:"))
        self.extension_filter_combo = QComboBox()
        self.extension_filter_combo.addItems([self.tr("All"), "HTML", "XLSX", "DOCX"])
        self.extension_filter_combo.setCurrentText("HTML") # Default to HTML
        filters_layout.addWidget(self.extension_filter_label, 0, 2)
        filters_layout.addWidget(self.extension_filter_combo, 0, 3)

        # Search Bar
        self.search_bar_label = QLabel(self.tr("Rechercher:"))
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(self.tr("Filtrer par nom..."))
        filters_layout.addWidget(self.search_bar_label, 1, 0)
        filters_layout.addWidget(self.search_bar, 1, 1, 1, 3) # Span search bar across 3 columns

        main_layout.addLayout(filters_layout)

        # Templates List
        templates_list_label = self._create_icon_label_widget("document-multiple", self.tr("Modèles disponibles:"))
        main_layout.addWidget(templates_list_label)
        self.templates_list = QListWidget()
        self.templates_list.setSelectionMode(QListWidget.MultiSelection)
        main_layout.addWidget(self.templates_list)

        # Connect signals for filters
        self.language_filter_combo.currentTextChanged.connect(self.load_templates)
        self.extension_filter_combo.currentTextChanged.connect(self.load_templates)
        self.search_bar.textChanged.connect(self.load_templates)
        
        self.load_templates() # Initial load
        main_layout.addStretch()

        # Button Grouping
        button_frame = QFrame(self)
        button_frame.setObjectName("buttonFrame")
        button_frame.setStyleSheet("#buttonFrame { border-top: 1px solid #cccccc; padding-top: 10px; margin-top: 10px; }")
        button_frame_layout = QHBoxLayout(button_frame)
        button_frame_layout.setContentsMargins(0,0,0,0)

        button_frame = QFrame(self)
        button_frame.setObjectName("buttonFrame")
        button_frame.setStyleSheet("#buttonFrame { border-top: 1px solid #cccccc; padding-top: 10px; margin-top: 10px; }")
        button_frame_layout = QHBoxLayout(button_frame)
        button_frame_layout.setContentsMargins(0,0,0,0)

        create_btn = QPushButton(self.tr("Créer Documents"))
        create_btn.setIcon(QIcon.fromTheme("document-new"))
        create_btn.setObjectName("primaryButton") # Apply primary button style
        create_btn.clicked.connect(self.create_documents)
        button_frame_layout.addWidget(create_btn) # Add directly to button_frame_layout

        cancel_btn = QPushButton(self.tr("Annuler"))
        cancel_btn.setIcon(QIcon.fromTheme("dialog-cancel"))
        # cancel_btn.setStyleSheet("padding: 5px 15px;") # Rely on global style
        cancel_btn.clicked.connect(self.reject)
        button_frame_layout.addWidget(cancel_btn) # Add directly to button_frame_layout
        
        main_layout.addWidget(button_frame)

    def load_templates(self):
        self.templates_list.clear()

        if not self._initial_load_complete:
            primary_language = None
            client_langs = self.client_info.get('selected_languages') # This is a list e.g. ['fr', 'en'] or a string "fr,en"
            if client_langs:
                if isinstance(client_langs, list) and client_langs:
                    primary_language = client_langs[0]
                elif isinstance(client_langs, str) and client_langs.strip():
                    primary_language = client_langs.split(',')[0].strip()

            if primary_language and self.language_filter_combo.currentText() == self.tr("All"):
                # Check if primary_language is a valid option in the combo
                for i in range(self.language_filter_combo.count()):
                    if self.language_filter_combo.itemText(i) == primary_language:
                        self.language_filter_combo.setCurrentText(primary_language)
                        break
            self._initial_load_complete = True

        selected_lang = self.language_filter_combo.currentText()
        selected_ext_display = self.extension_filter_combo.currentText()
        search_text = self.search_bar.text().lower()

        # Map display extension to actual extension
        ext_map = {
            "HTML": ".html",
            "XLSX": ".xlsx",
            "DOCX": ".docx"
        }
        selected_ext = ext_map.get(selected_ext_display) # Will be None if "All" or not found

        try:
            all_file_templates = db_manager.get_all_file_based_templates()
            if all_file_templates is None: all_file_templates = []

            filtered_templates = []
            for template_dict in all_file_templates:
                name = template_dict.get('template_name', 'N/A')
                lang_code = template_dict.get('language_code', 'N/A')
                base_file_name = template_dict.get('base_file_name', 'N/A')

                # Language filter
                if selected_lang != self.tr("All") and lang_code != selected_lang:
                    continue

                # Extension filter
                file_actual_ext = os.path.splitext(base_file_name)[1].lower()
                if selected_ext_display != self.tr("All"):
                    if not selected_ext or file_actual_ext != selected_ext:
                        continue

                # Search text filter (case-insensitive on template name)
                if search_text and search_text not in name.lower():
                    continue

                filtered_templates.append(template_dict)

            for template_dict in filtered_templates:
                name = template_dict.get('template_name', 'N/A')
                lang = template_dict.get('language_code', 'N/A')
                base_file_name = template_dict.get('base_file_name', 'N/A')

                item_text = f"{name} ({lang}) - {base_file_name}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, (name, lang, base_file_name)) # Store data for creation
                self.templates_list.addItem(item)

        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des modèles:\n{0}").format(str(e)))
            
    def create_documents(self):
        selected_items = self.templates_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("Aucun document sélectionné"), self.tr("Veuillez sélectionner au moins un document à créer."))
            return

        # Language for document creation is determined by the template itself (db_template_lang)
        # The self.lang_combo (client's general language pref) is removed from this dialog.
        # We use the language associated with the chosen template.

        created_files_count = 0
        
        for item in selected_items:
            db_template_name, db_template_lang, actual_template_filename = item.data(Qt.UserRole)

            # Determine target directory based on template's language
            target_dir_for_document = os.path.join(self.client_info["base_folder_path"], db_template_lang)
            os.makedirs(target_dir_for_document, exist_ok=True)
            
            if not actual_template_filename:
                print(f"Warning: No actual_template_filename for template '{db_template_name}' ({db_template_lang}). Skipping.")
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Nom de fichier manquant pour le modèle '{0}'. Impossible de créer.").format(db_template_name))
                continue

            template_file_found_abs = os.path.join(self.config["templates_dir"], db_template_lang, actual_template_filename)

            if os.path.exists(template_file_found_abs):
                target_path = os.path.join(target_dir_for_document, actual_template_filename) # Use target_dir_for_document
                try:
                    shutil.copy(template_file_found_abs, target_path)

                    if target_path.lower().endswith(".docx"):
                        populate_docx_template(target_path, self.client_info)
                        print(f"Populated DOCX: {target_path}")
                    elif target_path.lower().endswith(".html"):
                        with open(target_path, 'r', encoding='utf-8') as f:
                            template_content = f.read()
                        default_company_obj = db_manager.get_default_company()
                        default_company_id = default_company_obj['company_id'] if default_company_obj else None
                        if default_company_id is None:
                            QMessageBox.information(self, self.tr("Avertissement"), self.tr("Aucune société par défaut n'est définie. Les détails du vendeur peuvent être manquants dans les documents HTML."))
                        populated_content = HtmlEditor.populate_html_content(template_content, self.client_info, default_company_id)
                        with open(target_path, 'w', encoding='utf-8') as f:
                            f.write(populated_content)
                        print(f"Populated HTML: {target_path}")

                    created_files_count += 1
                except Exception as e_create:
                    print(f"Error processing template {actual_template_filename} for {db_template_name}: {e_create}")
                    QMessageBox.warning(self, self.tr("Erreur Création Document"), self.tr("Impossible de créer ou populer le document '{0}':\n{1}").format(actual_template_filename, e_create))
            else:
                print(f"Warning: Template file '{actual_template_filename}' for '{db_template_name}' ({db_template_lang}) not found at {template_file_found_abs}.")
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Fichier modèle '{0}' introuvable pour '{1}'.").format(actual_template_filename, db_template_name))

        if created_files_count > 0:
            QMessageBox.information(self, self.tr("Documents créés"), self.tr("{0} documents ont été créés avec succès.").format(created_files_count))
            self.accept()
        elif not selected_items: # No items were selected in the first place
             pass # Message already shown
        else: # Items were selected, but none could be created
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Aucun document n'a pu être créé. Vérifiez les erreurs précédentes."))

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
        compile_btn.setObjectName("primaryButton") # Apply primary button style
        compile_btn.clicked.connect(self.compile_pdf)
        action_layout.addWidget(compile_btn)
        
        cancel_btn = QPushButton(self.tr("Annuler"))
        cancel_btn.setIcon(QIcon.fromTheme("dialog-cancel"))
        # No specific style needed if global QPushButton style is sufficient
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
        
        self.header_label = QLabel(f"<h2>{self.client_info['client_name']}</h2>")
        self.header_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;") # Added margin-bottom
        layout.addWidget(self.header_label)
        
        action_layout = QHBoxLayout()
        
        self.create_docs_btn = QPushButton(self.tr("Créer Documents"))
        self.create_docs_btn.setIcon(QIcon.fromTheme("document-new"))
        self.create_docs_btn.setObjectName("primaryButton")
        self.create_docs_btn.clicked.connect(self.open_create_docs_dialog)
        action_layout.addWidget(self.create_docs_btn)
        
        self.compile_pdf_btn = QPushButton(self.tr("Compiler PDF"))
        self.compile_pdf_btn.setIcon(QIcon.fromTheme("document-export"))
        self.compile_pdf_btn.setProperty("primary", True) # Alternative way to mark as primary
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
        
        self.details_layout = QFormLayout()
        self.details_layout.setLabelAlignment(Qt.AlignRight)
        self.details_layout.setSpacing(8) # Added spacing for details

        # Store references to value labels for easy updating
        self.detail_value_labels = {}

        # Initial population
        self.populate_details_layout() # Call a method to populate for clarity

        # Add Category display
        self.category_label = QLabel(self.tr("Catégorie:"))
        self.category_value_label = QLabel(self.client_info.get("category", self.tr("N/A")))
        self.details_layout.addRow(self.category_label, self.category_value_label)
        self.detail_value_labels["category"] = self.category_value_label


        layout.addLayout(self.details_layout)
        
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
        self.add_contact_btn = QPushButton(self.tr("➕ Ajouter")) # Standardized text
        self.add_contact_btn.setIcon(QIcon.fromTheme("contact-new", QIcon.fromTheme("list-add")))
        self.add_contact_btn.setToolTip(self.tr("Ajouter un nouveau contact pour ce client"))
        self.add_contact_btn.clicked.connect(self.add_contact)
        contacts_btn_layout.addWidget(self.add_contact_btn)
        
        self.edit_contact_btn = QPushButton(self.tr("✏️ Modifier")) # Standardized text
        self.edit_contact_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_contact_btn.setToolTip(self.tr("Modifier le contact sélectionné"))
        self.edit_contact_btn.clicked.connect(self.edit_contact)
        contacts_btn_layout.addWidget(self.edit_contact_btn)
        
        self.remove_contact_btn = QPushButton(self.tr("🗑️ Supprimer")) # Standardized text
        self.remove_contact_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_contact_btn.setToolTip(self.tr("Supprimer le lien vers le contact sélectionné pour ce client"))
        self.remove_contact_btn.setObjectName("dangerButton") # Mark as danger
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
        self.add_product_btn = QPushButton(self.tr("➕ Ajouter")) # Standardized text
        self.add_product_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_product_btn.setToolTip(self.tr("Ajouter un produit pour ce client/projet"))
        self.add_product_btn.clicked.connect(self.add_product)
        products_btn_layout.addWidget(self.add_product_btn)
        
        self.edit_product_btn = QPushButton(self.tr("✏️ Modifier")) # Standardized text
        self.edit_product_btn.setIcon(QIcon.fromTheme("document-edit"))
        self.edit_product_btn.setToolTip(self.tr("Modifier le produit sélectionné"))
        self.edit_product_btn.clicked.connect(self.edit_product)
        products_btn_layout.addWidget(self.edit_product_btn)
        
        self.remove_product_btn = QPushButton(self.tr("🗑️ Supprimer")) # Standardized text
        self.remove_product_btn.setIcon(QIcon.fromTheme("edit-delete"))
        self.remove_product_btn.setToolTip(self.tr("Supprimer le produit sélectionné de ce client/projet"))
        self.remove_product_btn.setObjectName("dangerButton") # Mark as danger
        self.remove_product_btn.clicked.connect(self.remove_product)
        products_btn_layout.addWidget(self.remove_product_btn)
        
        products_layout.addLayout(products_btn_layout)
        self.tab_widget.addTab(products_tab, self.tr("Produits"))
        
        layout.addWidget(self.tab_widget)
        
        self.populate_doc_table()
        self.load_contacts()
        self.load_products()

    def _handle_open_pdf_action(self, file_path):
        print(f"Action: Open PDF for {file_path}")
        # This method will now call generate_pdf_for_document
        # client_info is available in self.client_info
        if not self.client_info or 'client_id' not in self.client_info:
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("Les informations du client ne sont pas disponibles."))
            return

        generated_pdf_path = generate_pdf_for_document(file_path, self.client_info, self)
        if generated_pdf_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(generated_pdf_path))
            # Optionally, refresh doc table if the PDF is saved in a way it should appear there
            # self.populate_doc_table()


    def populate_details_layout(self):
        # Clear existing rows from details_layout if any, before repopulating
        while self.details_layout.rowCount() > 0:
            self.details_layout.removeRow(0)

        self.detail_value_labels.clear() # Clear old references

        details_data_map = {
            "project_identifier": (self.tr("ID Projet:"), self.client_info.get("project_identifier", self.tr("N/A"))),
            "country": (self.tr("Pays:"), self.client_info.get("country", self.tr("N/A"))),
            "city": (self.tr("Ville:"), self.client_info.get("city", self.tr("N/A"))),
            "need": (self.tr("Besoin Principal:"), self.client_info.get("need", self.tr("N/A"))),
            "price": (self.tr("Prix Final:"), f"{self.client_info.get('price', 0)} €"),
            "creation_date": (self.tr("Date Création:"), self.client_info.get("creation_date", self.tr("N/A"))),
            "base_folder_path": (self.tr("Chemin Dossier:"), f"<a href='file:///{self.client_info.get('base_folder_path','')}'>{self.client_info.get('base_folder_path','')}</a>")
        }

        for key, (label_text, value_text) in details_data_map.items():
            label_widget = QLabel(label_text)
            value_widget = QLabel(value_text)
            if key == "base_folder_path": # Special handling for link
                value_widget.setOpenExternalLinks(True)
                value_widget.setTextInteractionFlags(Qt.TextBrowserInteraction)

            self.details_layout.addRow(label_widget, value_widget)
            self.detail_value_labels[key] = value_widget # Store reference to the value label

    def refresh_display(self, new_client_info):
        self.client_info = new_client_info # Update internal data store

        # Update header
        self.header_label.setText(f"<h2>{self.client_info.get('client_name', '')}</h2>")

        # Update status combo
        # Note: status_combo displays status name. self.client_info should have 'status' field with the name.
        self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours")))

        # Update details in the QFormLayout
        if hasattr(self, 'detail_value_labels'): # Check if labels were stored
            self.detail_value_labels["project_identifier"].setText(self.client_info.get("project_identifier", self.tr("N/A")))
            self.detail_value_labels["country"].setText(self.client_info.get("country", self.tr("N/A")))
            self.detail_value_labels["city"].setText(self.client_info.get("city", self.tr("N/A")))
            self.detail_value_labels["need"].setText(self.client_info.get("need", self.tr("N/A"))) # 'need' is 'primary_need_description' in some contexts
            self.detail_value_labels["price"].setText(f"{self.client_info.get('price', 0)} €")
            self.detail_value_labels["creation_date"].setText(self.client_info.get("creation_date", self.tr("N/A")))

            folder_path = self.client_info.get('base_folder_path','')
            self.detail_value_labels["base_folder_path"].setText(f"<a href='file:///{folder_path}'>{folder_path}</a>")

            # Update Category if the label exists
            if "category" in self.detail_value_labels:
                 self.detail_value_labels["category"].setText(self.client_info.get("category", self.tr("N/A")))
            elif hasattr(self, 'category_value_label'): # Fallback for direct attribute if detail_value_labels not fully populated yet
                 self.category_value_label.setText(self.client_info.get("category", self.tr("N/A")))

        else: # Fallback or if you choose to repopulate the whole layout
            self.populate_details_layout()
            # Explicitly update category here too if populate_details_layout doesn't handle it fully initially
            if hasattr(self, 'category_value_label'):
                 self.category_value_label.setText(self.client_info.get("category", self.tr("N/A")))


        # Update Notes
        self.notes_edit.setText(self.client_info.get("notes", ""))

        # Other elements like doc_table, contacts_list, products_table are refreshed by their own mechanisms typically.

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
        try:
            status_setting = db_manager.get_status_setting_by_name(status_text, 'Client')
            if status_setting and status_setting.get('status_id') is not None:
                status_id_to_set = status_setting['status_id']
                client_id_to_update = self.client_info["client_id"]

                if db_manager.update_client(client_id_to_update, {'status_id': status_id_to_set}):
                    self.client_info["status"] = status_text # Keep display name
                    self.client_info["status_id"] = status_id_to_set # Update the id in the local map
                    # Find the item in the main list and update its UserRole for the delegate
                    # This part is tricky as ClientWidget doesn't have direct access to DocumentManager.client_list_widget
                    # For now, we'll rely on a full refresh from DocumentManager if the list display needs immediate color change,
                    # or accept that the color might only update on next full load/filter.
                    # Consider emitting a signal if immediate update of list widget item is needed.
                    print(f"Client {client_id_to_update} status_id updated to {status_id_to_set} ({status_text})")
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour du statut du client dans la DB."))
            else:
                QMessageBox.warning(self, self.tr("Erreur Configuration"), self.tr("Statut '{0}' non trouvé ou invalide. Impossible de mettre à jour.").format(status_text))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Erreur de mise à jour du statut:\n{0}").format(str(e)))
            
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
                    action_layout.setContentsMargins(2, 2, 2, 2) # Small margins
                    action_layout.setSpacing(5) # Spacing between buttons

                    # Button 1: Ouvrir PDF (Placeholder)
                    pdf_btn = QPushButton("PDF") # Placeholder icon/text
                    pdf_btn.setIcon(QIcon.fromTheme("application-pdf", QIcon("📄"))) # Fallback icon
                    pdf_btn.setToolTip(self.tr("Ouvrir PDF du document"))
                    pdf_btn.setFixedSize(30, 30)
                    pdf_btn.clicked.connect(lambda _, p=file_path: self._handle_open_pdf_action(p))
                    action_layout.addWidget(pdf_btn)

                    # Button 2: Afficher Source
                    source_btn = QPushButton("👁️") # Placeholder icon/text
                    source_btn.setIcon(QIcon.fromTheme("document-properties", QIcon("👁️"))) # Fallback icon
                    source_btn.setToolTip(self.tr("Afficher le fichier source"))
                    source_btn.setFixedSize(30, 30)
                    source_btn.clicked.connect(lambda _, p=file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
                    action_layout.addWidget(source_btn)
                    
                    # Button 3: Modifier Contenu (only for Excel/HTML)
                    if file_name.lower().endswith(('.xlsx', '.html')):
                        edit_btn = QPushButton("✏️")
                        edit_btn.setIcon(QIcon.fromTheme("document-edit", QIcon("✏️"))) # Fallback icon
                        edit_btn.setToolTip(self.tr("Modifier le contenu du document"))
                        edit_btn.setFixedSize(30, 30)
                        edit_btn.clicked.connect(lambda _, p=file_path: self.open_document(p)) # open_document handles editor logic
                        action_layout.addWidget(edit_btn)
                    else:
                        # Add a spacer or disabled button if not editable to maintain layout consistency
                        spacer_widget = QWidget()
                        spacer_widget.setFixedSize(30,30)
                        action_layout.addWidget(spacer_widget)


                    # Button 4: Supprimer
                    delete_btn = QPushButton("🗑️")
                    delete_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon("🗑️"))) # Fallback icon
                    delete_btn.setToolTip(self.tr("Supprimer le document"))
                    delete_btn.setFixedSize(30, 30)
                    delete_btn.clicked.connect(lambda _, p=file_path: self.delete_document(p))
                    action_layout.addWidget(delete_btn)
                    
                    action_layout.addStretch() # Push buttons to the left if there's space
                    action_widget.setLayout(action_layout) # Set the layout on the widget
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
                    "client_id": self.client_info.get("client_id"), # Crucial for DB context
                    "Nom du client": self.client_info.get("client_name", ""), # Legacy key, keep for compatibility
                    "client_name": self.client_info.get("client_name", ""), # Preferred key
                    "company_name": self.client_info.get("company_name", ""),
                    "Besoin": self.client_info.get("need", ""), # 'need' is primary_need_description in client_info map
                    "primary_need_description": self.client_info.get("need", ""), # Explicitly map
                    "project_identifier": self.client_info.get("project_identifier", ""),
                    "country": self.client_info.get("country", ""), # This is country_name
                    "country_id": self.client_info.get("country_id"),
                    "city": self.client_info.get("city", ""), # This is city_name
                    "city_id": self.client_info.get("city_id"),
                    "price": self.client_info.get("price", 0), # raw_price
                    "status": self.client_info.get("status"), # status name
                    "status_id": self.client_info.get("status_id"),
                    "selected_languages": self.client_info.get("selected_languages"), # list
                    "notes": self.client_info.get("notes"),
                    "creation_date": self.client_info.get("creation_date"),
                    "category": self.client_info.get("category"),
                    "base_folder_path": self.client_info.get("base_folder_path")
                    # Add any other direct fields from client_info that get_document_context_data might use
                    # or that HtmlEditor might directly use for its own templating logic.
                }
                if file_path.lower().endswith('.xlsx'):
                    editor = ExcelEditor(file_path, parent=self)
                    if editor.exec_() == QDialog.Accepted:
                        expected_pdf_basename = os.path.splitext(os.path.basename(file_path))[0] + "_" + datetime.now().strftime('%Y%m%d') + ".pdf"
                        expected_pdf_path = os.path.join(os.path.dirname(file_path), expected_pdf_basename)
                        if os.path.exists(expected_pdf_path):
                            archive_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                            archive_pdf_name = os.path.splitext(expected_pdf_path)[0] + f"_archive_{archive_timestamp}.pdf"
                            try:
                                os.rename(expected_pdf_path, os.path.join(os.path.dirname(expected_pdf_path), archive_pdf_name))
                                print(f"Archived existing PDF to: {archive_pdf_name}")
                            except OSError as e_archive:
                                print(f"Error archiving PDF {expected_pdf_path}: {e_archive}")
                        generate_pdf_for_document(file_path, self.client_info, self) # This will show info message for XLSX
                    self.populate_doc_table()
                elif file_path.lower().endswith('.html'):
                    html_editor_dialog = HtmlEditor(file_path, client_data=editor_client_data, parent=self)
                    if html_editor_dialog.exec_() == QDialog.Accepted:
                        expected_pdf_basename = os.path.splitext(os.path.basename(file_path))[0] + "_" + datetime.now().strftime('%Y%m%d') + ".pdf"
                        expected_pdf_path = os.path.join(os.path.dirname(file_path), expected_pdf_basename)
                        if os.path.exists(expected_pdf_path):
                            archive_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                            archive_pdf_name = os.path.splitext(expected_pdf_path)[0] + f"_archive_{archive_timestamp}.pdf"
                            try:
                                os.rename(expected_pdf_path, os.path.join(os.path.dirname(expected_pdf_path), archive_pdf_name))
                                print(f"Archived existing PDF to: {archive_pdf_name}")
                            except OSError as e_archive:
                                print(f"Error archiving PDF {expected_pdf_path}: {e_archive}")
                        generated_pdf_path = generate_pdf_for_document(file_path, self.client_info, self)
                        if generated_pdf_path:
                             print(f"Updated PDF generated at: {generated_pdf_path}")
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

        dialog = ProductDialog(client_uuid, parent=self) # ProductDialog now supports multi-line
        if dialog.exec_() == QDialog.Accepted:
            products_list_data = dialog.get_data() # This is now a list of product dicts

            # Process list of products from dialog
            products_added_count = 0
            for product_item_data in products_list_data: # Use a different loop variable name
                try:
                    # Step 1: Find or Create Global Product
                    global_product = db_manager.get_product_by_name(product_item_data['name'])
                    global_product_id = None
                    current_base_unit_price = None # For checking if override is needed

                    if global_product:
                        global_product_id = global_product['product_id']
                        current_base_unit_price = global_product.get('base_unit_price')
                    else:
                        new_global_product_id = db_manager.add_product({
                            'product_name': product_item_data['name'],
                            'description': product_item_data['description'],
                            'base_unit_price': product_item_data['unit_price']
                        })
                        if new_global_product_id:
                            global_product_id = new_global_product_id
                            current_base_unit_price = product_item_data['unit_price']
                        else:
                            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer le produit global '{0}'.").format(product_item_data['name']))
                            continue # Skip to next product

                    # Step 2: Link Product to Client
                    if global_product_id:
                        unit_price_override_val = None
                        if current_base_unit_price is None or product_item_data['unit_price'] != current_base_unit_price:
                            unit_price_override_val = product_item_data['unit_price']

                        link_data = {
                            'client_id': client_uuid,
                            'project_id': None,
                            'product_id': global_product_id,
                            'quantity': product_item_data['quantity'],
                            'unit_price_override': unit_price_override_val
                        }
                        cpp_id = db_manager.add_product_to_client_or_project(link_data)
                        if cpp_id:
                            products_added_count +=1
                        else:
                            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de lier le produit '{0}' au client.").format(product_item_data['name']))
                except Exception as e:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du produit '{0}':\n{1}").format(product_item_data.get('name', 'Inconnu'), str(e)))

            if products_added_count > 0:
                self.load_products() # Refresh product list in ClientWidget only once after processing all
            if products_added_count < len(products_list_data) and len(products_list_data) > 0 : # Avoid message if list was empty
                 QMessageBox.information(self, self.tr("Information"), self.tr("Certains produits n'ont pas pu être ajoutés. Veuillez vérifier les messages d'erreur."))

    def edit_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un produit à modifier."))
            return

        cpp_id_item = self.products_table.item(selected_row, 0) # Hidden column with client_project_product_id
        if not cpp_id_item:
            QMessageBox.critical(self, self.tr("Erreur Données"), self.tr("ID du produit lié introuvable dans la table."))
            return
        client_project_product_id = cpp_id_item.data(Qt.UserRole)

        try:
            # Fetch complete details of the linked product, including global product info
            linked_product_details = db_manager.get_client_project_product_by_id(client_project_product_id)

            if not linked_product_details:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Détails du produit lié introuvables dans la base de données."))
                return

            # Prepare data for the EditProductLineDialog
            # The dialog expects 'name', 'description', 'quantity', 'unit_price', 'product_id', 'client_project_product_id'
            effective_unit_price = linked_product_details.get('unit_price_override', linked_product_details.get('base_unit_price', 0.0))

            dialog_data_for_edit = {
                "name": linked_product_details.get('product_name', ''),
                "description": linked_product_details.get('product_description', ''),
                "quantity": linked_product_details.get('quantity', 1.0),
                "unit_price": effective_unit_price, # This is the price shown and edited in the dialog
                "product_id": linked_product_details.get('product_id'),
                "client_project_product_id": client_project_product_id,
                # Store original base price for comparison later
                "original_base_unit_price": linked_product_details.get('base_unit_price', 0.0)
            }

            dialog = EditProductLineDialog(product_data=dialog_data_for_edit, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                updated_data_from_dialog = dialog.get_data()

                # 1. Update Global Product (Products table) if name, description, or base price logic dictates
                global_product_update_payload = {}
                if updated_data_from_dialog['name'] != linked_product_details.get('product_name'):
                    global_product_update_payload['product_name'] = updated_data_from_dialog['name']
                if updated_data_from_dialog['description'] != linked_product_details.get('product_description'):
                    global_product_update_payload['description'] = updated_data_from_dialog['description']

                # Logic for updating base_unit_price:
                # If name or description changed, consider the edited price as the new base price for this (potentially now distinct) product.
                if global_product_update_payload: # If name or description changed
                     global_product_update_payload['base_unit_price'] = updated_data_from_dialog['unit_price']

                if global_product_update_payload:
                    db_manager.update_product(updated_data_from_dialog['product_id'], global_product_update_payload)

                # 2. Update Linked Product (ClientProjectProducts table)
                # Determine unit_price_override based on the potentially updated global product's base_unit_price
                current_global_product_info = db_manager.get_product_by_id(updated_data_from_dialog['product_id'])
                current_global_base_price = current_global_product_info.get('base_unit_price', 0.0) if current_global_product_info else 0.0

                unit_price_override_val = None
                if float(updated_data_from_dialog['unit_price']) != float(current_global_base_price): # Compare as float
                    unit_price_override_val = updated_data_from_dialog['unit_price']

                link_update_payload = {
                    'quantity': updated_data_from_dialog['quantity'],
                    'unit_price_override': unit_price_override_val
                    # total_price_calculated will be handled by db_manager.update_client_project_product
                }

                if db_manager.update_client_project_product(client_project_product_id, link_update_payload):
                    self.load_products() # Refresh the table
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Ligne de produit mise à jour avec succès."))
                else:
                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour de la ligne de produit liée."))
            # Else (dialog cancelled), do nothing
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Erreur lors de la modification du produit:\n{0}").format(str(e)))
            print(f"Error in edit_product: {e}") # For debugging

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
                
                unit_price_override = prod_link_data.get('unit_price_override')
                base_price = prod_link_data.get('base_unit_price')

                if unit_price_override is not None:
                    effective_unit_price = unit_price_override
                elif base_price is not None:
                    effective_unit_price = base_price
                else:
                    effective_unit_price = 0.0

                effective_unit_price = float(effective_unit_price) if effective_unit_price is not None else 0.0
                unit_price_item = QTableWidgetItem(f"€ {effective_unit_price:.2f}")
                unit_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 4, unit_price_item)
                
                total_price_calculated_val = prod_link_data.get('total_price_calculated')
                if total_price_calculated_val is None:
                    total_price_calculated_val = 0.0
                total_price_item = QTableWidgetItem(f"€ {float(total_price_calculated_val):.2f}")
                total_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.products_table.setItem(row_idx, 5, total_price_item)
                
            self.products_table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des produits:\n{0}").format(str(e)))

class EditClientDialog(QDialog):
    def __init__(self, client_info, config, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.config = config
        # Ensure db_manager is accessible, e.g., self.db_manager = db_manager
        # or call db_manager functions directly if it's globally imported and initialized
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(self.tr("Modifier Client"))
        self.setMinimumSize(500, 430) # Adjusted minimum size for spacing
        layout = QFormLayout(self)
        layout.setSpacing(10) # Added spacing

        # Client Name
        self.client_name_input = QLineEdit(self.client_info.get('client_name', ''))
        layout.addRow(self.tr("Nom Client:"), self.client_name_input)

        # Company Name
        self.company_name_input = QLineEdit(self.client_info.get('company_name', ''))
        layout.addRow(self.tr("Nom Entreprise:"), self.company_name_input)

        # Client Need (primary_need_description)
        self.client_need_input = QLineEdit(self.client_info.get('primary_need_description', self.client_info.get('need',''))) # Fallback to 'need' if 'primary_need_description' is missing
        layout.addRow(self.tr("Besoin Client:"), self.client_need_input)

        # Project ID (project_identifier)
        self.project_id_input_field = QLineEdit(self.client_info.get('project_identifier', ''))
        layout.addRow(self.tr("ID Projet:"), self.project_id_input_field)

        # Price (final_price_input)
        self.final_price_input = QDoubleSpinBox()
        self.final_price_input.setPrefix("€ ")
        self.final_price_input.setRange(0, 10000000)
        self.final_price_input.setValue(float(self.client_info.get('price', 0.0)))
        self.final_price_input.setReadOnly(True) # Make read-only
        price_info_label = QLabel(self.tr("Le prix final est calculé à partir des produits et n'est pas modifiable ici."))
        price_info_label.setStyleSheet("font-style: italic; font-size: 9pt; color: grey;")
        price_layout = QHBoxLayout()
        price_layout.addWidget(self.final_price_input)
        price_layout.addWidget(price_info_label)
        layout.addRow(self.tr("Prix Final:"), price_layout)

        # Status (status_select_combo)
        self.status_select_combo = QComboBox()
        self.populate_statuses() # New method to populate statuses
        current_status_id = self.client_info.get('status_id')
        if current_status_id is not None:
            index = self.status_select_combo.findData(current_status_id)
            if index >= 0:
                self.status_select_combo.setCurrentIndex(index)
        layout.addRow(self.tr("Statut Client:"), self.status_select_combo)

        # Category
        self.category_input = QLineEdit(self.client_info.get('category', ''))
        layout.addRow(self.tr("Catégorie:"), self.category_input)

        # Notes
        self.notes_edit = QTextEdit(self.client_info.get('notes', ''))
        self.notes_edit.setPlaceholderText(self.tr("Ajoutez des notes sur ce client..."))
        self.notes_edit.setFixedHeight(80) # Set a reasonable height for notes
        layout.addRow(self.tr("Notes:"), self.notes_edit)

        # Country (country_select_combo)
        self.country_select_combo = QComboBox()
        self.country_select_combo.setEditable(True)
        self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.populate_countries() # Populate with all countries
        # Set current selection for country
        current_country_id = self.client_info.get('country_id')
        if current_country_id is not None:
            index = self.country_select_combo.findData(current_country_id)
            if index >= 0:
                self.country_select_combo.setCurrentIndex(index)
            else: # Fallback if ID not in combo, try by name
                current_country_name = self.client_info.get('country')
                if current_country_name:
                    index_name = self.country_select_combo.findText(current_country_name)
                    if index_name >=0:
                         self.country_select_combo.setCurrentIndex(index_name)
        self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country_edit)
        layout.addRow(self.tr("Pays Client:"), self.country_select_combo)

        # City (city_select_combo)
        self.city_select_combo = QComboBox()
        self.city_select_combo.setEditable(True)
        self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        # Initial population of cities based on current country
        self.load_cities_for_country_edit(self.country_select_combo.currentText())
        # Set current selection for city
        current_city_id = self.client_info.get('city_id')
        if current_city_id is not None:
            index = self.city_select_combo.findData(current_city_id)
            if index >= 0:
                self.city_select_combo.setCurrentIndex(index)
            else: # Fallback if ID not in combo, try by name
                current_city_name = self.client_info.get('city')
                if current_city_name:
                    index_name = self.city_select_combo.findText(current_city_name)
                    if index_name >= 0:
                        self.city_select_combo.setCurrentIndex(index_name)

        layout.addRow(self.tr("Ville Client:"), self.city_select_combo)

        # Languages (language_select_combo)
        self.language_select_combo = QComboBox()
        self.lang_display_to_codes_map = {
            self.tr("Français uniquement (fr)"): ["fr"],
            self.tr("Arabe uniquement (ar)"): ["ar"],
            self.tr("Turc uniquement (tr)"): ["tr"],
            self.tr("Toutes les langues (fr, ar, tr)"): ["fr", "ar", "tr"]
        }
        self.language_select_combo.addItems(list(self.lang_display_to_codes_map.keys()))
        # Set current selection for languages
        current_lang_codes = self.client_info.get('selected_languages', ['fr']) # Default to ['fr']
        if not isinstance(current_lang_codes, list): # Ensure it's a list
             current_lang_codes = [code.strip() for code in str(current_lang_codes).split(',') if code.strip()]

        # Find the display string that matches the current_lang_codes list
        selected_display_string = None
        for display_string, codes_list in self.lang_display_to_codes_map.items():
            if sorted(codes_list) == sorted(current_lang_codes):
                selected_display_string = display_string
                break
        if selected_display_string:
            self.language_select_combo.setCurrentText(selected_display_string)
        else: # Fallback to French if no exact match
            self.language_select_combo.setCurrentText(self.tr("Français uniquement (fr)"))
        layout.addRow(self.tr("Langues:"), self.language_select_combo)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK"))
        button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def populate_statuses(self):
        self.status_select_combo.clear()
        try:
            statuses = db_manager.get_all_status_settings(status_type='Client')
            if statuses is None: statuses = []
            for status_dict in statuses:
                self.status_select_combo.addItem(status_dict['status_name'], status_dict.get('status_id'))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des statuts client:\n{0}").format(str(e)))

    def populate_countries(self):
        self.country_select_combo.clear()
        try:
            countries = db_manager.get_all_countries()
            if countries is None: countries = []
            for country_dict in countries:
                self.country_select_combo.addItem(country_dict['country_name'], country_dict.get('country_id'))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des pays:\n{0}").format(str(e)))


    def load_cities_for_country_edit(self, country_name_str):
        self.city_select_combo.clear()
        if not country_name_str:
            return

        selected_country_id = self.country_select_combo.currentData()

        if selected_country_id is None:
            country_obj_by_name = db_manager.get_country_by_name(country_name_str)
            if country_obj_by_name:
                selected_country_id = country_obj_by_name['country_id']
            else:
                return # No valid country selected or found

        try:
            cities = db_manager.get_all_cities(country_id=selected_country_id)
            if cities is None: cities = []
            for city_dict in cities:
                self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id'))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:\n{0}").format(str(e)))

    def get_data(self) -> dict:
        data = {}
        data['client_name'] = self.client_name_input.text().strip()
        data['company_name'] = self.company_name_input.text().strip()
        data['primary_need_description'] = self.client_need_input.text().strip()
        data['project_identifier'] = self.project_id_input_field.text().strip()
        data['price'] = self.final_price_input.value() # Although read-only, get current value

        # Status ID
        data['status_id'] = self.status_select_combo.currentData()

        # Category
        data['category'] = self.category_input.text().strip()

        # Notes
        data['notes'] = self.notes_edit.toPlainText().strip()

        # Country ID
        country_id = self.country_select_combo.currentData()
        if country_id is None: # Handle case where user typed a new country not in DB
            country_name = self.country_select_combo.currentText().strip()
            if country_name: # Try to get by name if text is present
                country_obj = db_manager.get_country_by_name(country_name)
                if country_obj:
                    country_id = country_obj['country_id']
                # else: Consider adding the new country or error, for now, it will be None
        data['country_id'] = country_id

        # City ID
        city_id = self.city_select_combo.currentData()
        if city_id is None: # Handle case where user typed a new city not in DB
            city_name = self.city_select_combo.currentText().strip()
            # Ensure country_id is valid before trying to fetch/add city by name
            if city_name and data.get('country_id') is not None:
                city_obj = db_manager.get_city_by_name_and_country_id(city_name, data['country_id'])
                if city_obj:
                    city_id = city_obj['city_id']
                # else: Consider adding new city or error, for now, it will be None
        data['city_id'] = city_id

        # Selected Languages (comma-separated string of codes)
        selected_lang_display_text = self.language_select_combo.currentText()
        lang_codes_list = self.lang_display_to_codes_map.get(selected_lang_display_text, ["fr"])
        data['selected_languages'] = ",".join(lang_codes_list)

        return data

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
        creation_form_layout.setSpacing(10) # Added spacing
        
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
        self.final_price_input.setReadOnly(True) # Set to read-only
        creation_form_layout.addRow(self.tr("Prix Final:"), self.final_price_input)
        price_info_label = QLabel(self.tr("Le prix final est calculé automatiquement à partir des produits ajoutés."))
        price_info_label.setStyleSheet("font-style: italic; font-size: 9pt; color: grey;") # Optional: style the label
        creation_form_layout.addRow("", price_info_label) # Add info label below price input, span if needed or adjust layout
        self.language_select_combo = QComboBox() 
        self.language_select_combo.addItems([self.tr("Français uniquement (fr)"), self.tr("Arabe uniquement (ar)"), self.tr("Turc uniquement (tr)"), self.tr("Toutes les langues (fr, ar, tr)")])
        creation_form_layout.addRow(self.tr("Langues:"), self.language_select_combo)
        self.create_client_button = QPushButton(self.tr("Créer Client")); self.create_client_button.setIcon(QIcon.fromTheme("list-add"))
        self.create_client_button.setObjectName("primaryButton") # Use object name for global styling
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

            # START of new dialog sequence
            # At this point, actual_new_client_id and ui_map_data are available.
            # Dialog sequence logic verified

            # 1. Contact Dialog
            contact_dialog = ContactDialog(client_id=actual_new_client_id, parent=self)
            if contact_dialog.exec_() == QDialog.Accepted:
                contact_form_data = contact_dialog.get_data()
                try:
                    existing_contact = db_manager.get_contact_by_email(contact_form_data['email'])
                    contact_id_to_link = None
                    if existing_contact:
                        contact_id_to_link = existing_contact['contact_id']
                        update_data = {k: v for k, v in contact_form_data.items() if k in ['name', 'phone', 'position'] and v != existing_contact.get(k)}
                        if update_data: db_manager.update_contact(contact_id_to_link, update_data)
                    else:
                        new_contact_id = db_manager.add_contact({
                            'name': contact_form_data['name'], 'email': contact_form_data['email'],
                            'phone': contact_form_data['phone'], 'position': contact_form_data['position']
                        })
                        if new_contact_id:
                            contact_id_to_link = new_contact_id
                        else:
                            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer le nouveau contact global lors de la création du client."))

                    if contact_id_to_link:
                        if contact_form_data['is_primary']:
                            client_contacts = db_manager.get_contacts_for_client(actual_new_client_id)
                            if client_contacts:
                                for cc in client_contacts:
                                    if cc['is_primary_for_client'] and cc.get('client_contact_id'): # Ensure client_contact_id exists
                                        db_manager.update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})

                        link_id = db_manager.link_contact_to_client(
                            actual_new_client_id, contact_id_to_link,
                            is_primary=contact_form_data['is_primary']
                        )
                        if not link_id:
                             QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de lier le contact au client (le lien existe peut-être déjà)."))
                except Exception as e_contact_save:
                    QMessageBox.critical(self, self.tr("Erreur Sauvegarde Contact"), self.tr("Une erreur est survenue lors de la sauvegarde du contact : {0}").format(str(e_contact_save)))

                # 2. Product Dialog
                product_dialog = ProductDialog(client_id=actual_new_client_id, parent=self)
                if product_dialog.exec_() == QDialog.Accepted:
                    products_list_data = product_dialog.get_data() # Now a list
                    # Process list of products from dialog
                    for product_item_data in products_list_data:
                        try:
                            global_product = db_manager.get_product_by_name(product_item_data['name'])
                            global_product_id = None
                            current_base_unit_price = None

                            if global_product:
                                global_product_id = global_product['product_id']
                                current_base_unit_price = global_product.get('base_unit_price')
                            else:
                                new_global_product_id = db_manager.add_product({
                                    'product_name': product_item_data['name'],
                                    'description': product_item_data['description'],
                                    'base_unit_price': product_item_data['unit_price'], # Use dialog price as base for new global product
                                    'language_code': product_item_data.get('language_code', 'fr') # Added language code
                                })
                                if new_global_product_id:
                                    global_product_id = new_global_product_id
                                    current_base_unit_price = product_item_data['unit_price']
                                else:
                                    # Error message from add_product (e.g. IntegrityError) will be printed to console from db.py
                                    QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer le produit global '{0}' (lang: {1}). Vérifiez que le nom n'est pas déjà utilisé pour cette langue ou si un prix de base est manquant.").format(product_item_data['name'], product_item_data.get('language_code', 'fr')))
                                    continue # Skip to next product in list

                            if global_product_id:
                                unit_price_override_val = None
                                # If the price in dialog differs from base, or if it's a new product (current_base_unit_price was just set from item)
                                # or if global product had no base price (should not happen ideally)
                                if current_base_unit_price is None or product_item_data['unit_price'] != current_base_unit_price:
                                    unit_price_override_val = product_item_data['unit_price']

                                link_data = {
                                    'client_id': actual_new_client_id,
                                    'project_id': None,
                                    'product_id': global_product_id,
                                    'quantity': product_item_data['quantity'],
                                    'unit_price_override': unit_price_override_val # This can be None
                                }
                                cpp_id = db_manager.add_product_to_client_or_project(link_data)
                                if not cpp_id:
                                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de lier le produit '{0}' au client.").format(product_item_data['name']))
                        except Exception as e_product_save:
                            QMessageBox.critical(self, self.tr("Erreur Sauvegarde Produit"), self.tr("Une erreur est survenue lors de la sauvegarde du produit '{0}': {1}").format(product_item_data.get('name', 'Inconnu'), str(e_product_save)))

                    # 3. Create Document Dialog
                    # Ensure ui_map_data is available and correctly structured for client_info
                    if ui_map_data:
                        # After ProductDialog, calculate and update price
                        linked_products = db_manager.get_products_for_client_or_project(client_id=actual_new_client_id, project_id=None)
                        if linked_products is None: linked_products = []

                        calculated_total_sum = sum(p.get('total_price_calculated', 0.0) for p in linked_products if p.get('total_price_calculated') is not None)

                        db_manager.update_client(actual_new_client_id, {'price': calculated_total_sum})

                        # Update ui_map_data and self.clients_data_map for immediate UI consistency
                        ui_map_data['price'] = calculated_total_sum
                        if actual_new_client_id in self.clients_data_map:
                             self.clients_data_map[actual_new_client_id]['price'] = calculated_total_sum

                        # Refresh client list display to reflect new price potentially if it's shown there
                        # self.add_client_to_list_widget might need to be called again or the item updated
                        # For now, the list widget primarily shows name and status color.
                        # The critical part is that clients_data_map is updated before open_client_tab_by_id.

                        create_document_dialog = CreateDocumentDialog(client_info=ui_map_data, config=self.config, parent=self)
                        if create_document_dialog.exec_() == QDialog.Accepted:
                            # All dialogs completed successfully
                            print("CreateDocumentDialog accepted, all dialogs in sequence complete.")
                        else:
                            print("CreateDocumentDialog cancelled.")
                    else:
                        QMessageBox.warning(self, self.tr("Erreur Données Client"),
                                            self.tr("Les données du client (ui_map_data) ne sont pas disponibles pour la création de documents."))
                else:
                    print("ProductDialog cancelled.")
                    # If ProductDialog is cancelled, we should still calculate the price based on any products
                    # that might have been added if the dialog allowed partial additions before cancel.
                    # However, current ProductDialog only returns data on Accept.
                    # So, if cancelled, linked_products would be empty or from a previous state.
                    # For safety, recalculate and update price even if ProductDialog is cancelled,
                    # based on whatever products are linked to the client at this stage.
                    if actual_new_client_id and ui_map_data: # Ensure client and map exist
                        linked_products_on_cancel = db_manager.get_products_for_client_or_project(client_id=actual_new_client_id, project_id=None)
                        if linked_products_on_cancel is None: linked_products_on_cancel = []
                        calculated_total_sum_on_cancel = sum(p.get('total_price_calculated', 0.0) for p in linked_products_on_cancel if p.get('total_price_calculated') is not None)
                        db_manager.update_client(actual_new_client_id, {'price': calculated_total_sum_on_cancel})
                        ui_map_data['price'] = calculated_total_sum_on_cancel
                        if actual_new_client_id in self.clients_data_map:
                             self.clients_data_map[actual_new_client_id]['price'] = calculated_total_sum_on_cancel

            else:
                print("ContactDialog cancelled.")
                # Similar to above, if ContactDialog is cancelled, calculate price based on current state.
                if actual_new_client_id and ui_map_data:
                    linked_products_on_contact_cancel = db_manager.get_products_for_client_or_project(client_id=actual_new_client_id, project_id=None)
                    if linked_products_on_contact_cancel is None: linked_products_on_contact_cancel = []
                    calculated_total_sum_on_contact_cancel = sum(p.get('total_price_calculated', 0.0) for p in linked_products_on_contact_cancel if p.get('total_price_calculated') is not None)
                    db_manager.update_client(actual_new_client_id, {'price': calculated_total_sum_on_contact_cancel})
                    ui_map_data['price'] = calculated_total_sum_on_contact_cancel
                    if actual_new_client_id in self.clients_data_map:
                         self.clients_data_map[actual_new_client_id]['price'] = calculated_total_sum_on_contact_cancel


            # END of new dialog sequence
            
            # Ensure client_dict_from_db and ui_map_data are refreshed with the latest price before opening tab
            # This is important if the tab display relies on the price from these maps.
            # The price calculation logic has already updated ui_map_data and self.clients_data_map.
            # The call to self.add_client_to_list_widget uses ui_map_data.
            # The call to self.open_client_tab_by_id uses self.clients_data_map.
            # So, the price should be correctly reflected if these maps are the source of truth for those UI elements.

            QMessageBox.information(self, self.tr("Client Créé"),
                                    self.tr("Client {0} créé avec succès (ID Interne: {1}).").format(client_name_val, actual_new_client_id))
            self.open_client_tab_by_id(actual_new_client_id) # Open the new client's tab
            self.stats_widget.update_stats() # Refresh statistics

        except sqlite3.IntegrityError as e_sqlite_integrity:
            logging.error(f"Database integrity error during client creation: {client_name_val}", exc_info=True)
            error_msg = str(e_sqlite_integrity).lower()
            user_message = self.tr("Erreur de base de données lors de la création du client.")
            if "unique constraint failed: clients.project_identifier" in error_msg:
                user_message = self.tr("L'ID de Projet '{0}' existe déjà. Veuillez en choisir un autre.").format(project_identifier_val)
            elif "unique constraint failed: clients.default_base_folder_path" in error_msg:
                 user_message = self.tr("Un client avec un nom ou un chemin de dossier résultant similaire existe déjà. Veuillez modifier le nom du client ou l'ID de projet.")
            # Add more specific checks if other UNIQUE constraints are relevant

            QMessageBox.critical(self, self.tr("Erreur de Données"), user_message)
            # No rollback needed here as db_manager.add_client should not have committed if IntegrityError occurred on its own transaction.
            # If add_client doesn't manage its own transaction, this assumption is wrong.
            # Assuming add_client is robust and handles its own atomicity for the client record itself.
            # The project/tasks are separate transactions usually.

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
        edit_action = menu.addAction(self.tr("Modifier Client")); edit_action.triggered.connect(lambda: self.open_edit_client_dialog(client_id_val))
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
            
    def open_edit_client_dialog(self, client_id):
        current_client_data = self.clients_data_map.get(client_id)
        if not current_client_data:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Client non trouvé."))
            return

        dialog = EditClientDialog(current_client_data, self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            updated_form_data = dialog.get_data()

            # Prepare data for DB update. Keys should match DB columns.
            data_for_db_update = {
                'client_name': updated_form_data.get('client_name'),
                'company_name': updated_form_data.get('company_name'),
                'primary_need_description': updated_form_data.get('primary_need_description'),
                'project_identifier': updated_form_data.get('project_identifier'),
                'country_id': updated_form_data.get('country_id'),
                'city_id': updated_form_data.get('city_id'),
                # 'price': updated_form_data.get('price'), # Price is read-only in dialog, not updated directly
                'selected_languages': updated_form_data.get('selected_languages'),
                'status_id': updated_form_data.get('status_id'),
                'notes': updated_form_data.get('notes'),
                'category': updated_form_data.get('category')
                # default_base_folder_path is not part of this dialog's update scope.
                # price is handled by product updates.
            }

            # Filter out any keys with None values if db_manager.update_client expects only non-null fields for update
            # However, it's usually fine to pass None to set a field to NULL if the DB allows it.
            # For now, assume db_manager.update_client handles None values appropriately.

            success = db_manager.update_client(client_id, data_for_db_update)

            if success:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Client mis à jour avec succès."))

                # Refresh data and UI
                self.load_clients_from_db() # Refreshes map and list widget FIRST

                # Update the open tab if it's the one being edited
                tab_refreshed = False
                for i in range(self.client_tabs_widget.count()):
                    tab_widget = self.client_tabs_widget.widget(i)
                    if hasattr(tab_widget, 'client_info') and tab_widget.client_info.get("client_id") == client_id:
                        if hasattr(tab_widget, 'refresh_display'):
                            updated_client_data_for_tab = self.clients_data_map.get(client_id)
                            if updated_client_data_for_tab:
                                tab_widget.refresh_display(updated_client_data_for_tab)
                                self.client_tabs_widget.setTabText(i, updated_client_data_for_tab.get('client_name', 'Client'))
                                tab_refreshed = True
                        break

                self.stats_widget.update_stats()
            else:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("Échec de la mise à jour du client."))

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

        # Company Details Tab
        self.company_tab = CompanyTabWidget(self) # Create instance of CompanyTabWidget
        tabs_widget.addTab(self.company_tab, self.tr("Company Details")) # Add it as a tab
        
        dialog_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_settings_button = dialog_button_box.button(QDialogButtonBox.Ok)
        ok_settings_button.setText(self.tr("OK"))
        ok_settings_button.setObjectName("primaryButton")

        cancel_settings_button = dialog_button_box.button(QDialogButtonBox.Cancel)
        cancel_settings_button.setText(self.tr("Annuler"))
        # Standard cancel button styling will apply from global stylesheet

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


def generate_pdf_for_document(source_file_path: str, client_info: dict, parent_widget=None) -> str | None:
    """
    Generates a PDF for a given source document (HTML, XLSX, DOCX).
    For HTML, it converts the content to PDF.
    For XLSX/DOCX, it informs the user that direct conversion is not supported.
    """
    if not client_info or 'client_id' not in client_info:
        QMessageBox.warning(parent_widget, QCoreApplication.translate("generate_pdf", "Erreur Client"),
                            QCoreApplication.translate("generate_pdf", "ID Client manquant. Impossible de générer le PDF."))
        return None

    client_name = client_info.get('client_name', 'UnknownClient')
    file_name, file_ext = os.path.splitext(os.path.basename(source_file_path))
    current_date_str = datetime.now().strftime("%Y%m%d")
    output_pdf_filename = f"{file_name}_{current_date_str}.pdf"
    output_pdf_path = os.path.join(os.path.dirname(source_file_path), output_pdf_filename)

    if file_ext.lower() == '.html':
        try:
            with open(source_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            default_company_obj = db_manager.get_default_company()
            default_company_id = default_company_obj['company_id'] if default_company_obj else None
            if not default_company_id:
                 QMessageBox.information(parent_widget, QCoreApplication.translate("generate_pdf", "Avertissement"),
                                        QCoreApplication.translate("generate_pdf", "Aucune société par défaut n'est définie. Les détails du vendeur peuvent être manquants."))

            # Use HtmlEditor's static method for populating content
            # Ensure client_info passed here is comprehensive enough for populate_html_content
            processed_html = HtmlEditor.populate_html_content(html_content, client_info, default_company_id)

            # Use the utility function for conversion
            # base_url could be the directory of the source_file_path for relative assets
            base_url = QUrl.fromLocalFile(os.path.dirname(source_file_path)).toString()
            pdf_bytes = convert_html_to_pdf(processed_html, base_url=base_url)

            if pdf_bytes:
                with open(output_pdf_path, 'wb') as f_pdf:
                    f_pdf.write(pdf_bytes)
                QMessageBox.information(parent_widget, QCoreApplication.translate("generate_pdf", "Succès PDF"),
                                        QCoreApplication.translate("generate_pdf", "PDF généré avec succès:\n{0}").format(output_pdf_path))
                return output_pdf_path
            else:
                QMessageBox.warning(parent_widget, QCoreApplication.translate("generate_pdf", "Erreur PDF"),
                                    QCoreApplication.translate("generate_pdf", "La conversion HTML en PDF a échoué. Le contenu PDF résultant était vide."))
                return None
        except Exception as e:
            QMessageBox.critical(parent_widget, QCoreApplication.translate("generate_pdf", "Erreur HTML vers PDF"),
                                 QCoreApplication.translate("generate_pdf", "Erreur lors de la génération du PDF à partir du HTML:\n{0}").format(str(e)))
            return None
    elif file_ext.lower() in ['.xlsx', '.docx']:
        QMessageBox.information(parent_widget, QCoreApplication.translate("generate_pdf", "Fonctionnalité non disponible"),
                                QCoreApplication.translate("generate_pdf", "La génération PDF directe pour les fichiers {0} n'est pas supportée.\nVeuillez utiliser la fonction 'Enregistrer sous PDF' ou 'Exporter vers PDF' de l'application correspondante.").format(file_ext.upper()))
        return None
    else:
        QMessageBox.warning(parent_widget, QCoreApplication.translate("generate_pdf", "Type de fichier non supporté"),
                            QCoreApplication.translate("generate_pdf", "La génération PDF n'est pas supportée pour les fichiers de type '{0}'.").format(file_ext))
        return None


def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Determine language for translations
    language_code = CONFIG.get("language", QLocale.system().name().split('_')[0]) # Default to system or 'en' if system locale is odd

    app = QApplication(sys.argv)
    app.setApplicationName("ClientDocManager")
    app.setStyle("Fusion")

    # Set a default font (example: Segoe UI for Windows, fallback to a common sans-serif)
    default_font = QFont("Segoe UI", 9) # Adjust size as needed
    if sys.platform != "win32": # Basic platform check for font
        default_font = QFont("Arial", 10) # Or "Helvetica", "DejaVu Sans" etc.
    app.setFont(default_font)

    # Basic global stylesheet
    app.setStyleSheet("""
        QWidget {
            /* General spacing and font settings for all widgets if needed */
        }
        QPushButton {
            padding: 6px 12px;
            border: 1px solid #cccccc;
            border-radius: 4px;
            background-color: #f8f9fa; /* Light gray, good for general buttons */
            min-width: 80px; /* Ensure buttons have a decent minimum width */
        }
        QPushButton:hover {
            background-color: #e9ecef;
            border-color: #adb5bd;
        }
        QPushButton:pressed {
            background-color: #dee2e6;
            border-color: #adb5bd;
        }
        QPushButton:disabled {
            background-color: #e9ecef;
            color: #6c757d;
            border-color: #ced4da;
        }
        QPushButton#primaryButton, QPushButton[primary="true"] { /* Selector for primary buttons */
            background-color: #007bff; /* Blue */
            color: white;
            border-color: #007bff;
        }
        QPushButton#primaryButton:hover, QPushButton[primary="true"]:hover {
            background-color: #0069d9;
            border-color: #0062cc;
        }
        QPushButton#primaryButton:pressed, QPushButton[primary="true"]:pressed {
            background-color: #005cbf;
            border-color: #005cbf;
        }
        QPushButton#dangerButton, QPushButton[danger="true"] { /* Selector for danger buttons */
            background-color: #dc3545; /* Red */
            color: white;
            border-color: #dc3545;
        }
        QPushButton#dangerButton:hover, QPushButton[danger="true"]:hover {
            background-color: #c82333;
            border-color: #bd2130;
        }
        QPushButton#dangerButton:pressed, QPushButton[danger="true"]:pressed {
            background-color: #b21f2d;
            border-color: #b21f2d;
        }
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            padding: 5px;
            border: 1px solid #ced4da;
            border-radius: 4px;
        }
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #80bdff; /* Light blue, common focus indicator */
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ced4da;
            border-radius: 4px;
            margin-top: 10px;
            padding: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 3px 0 3px;
            left: 10px;
            background-color: transparent;
        }
        QTabWidget::pane {
            border-top: 1px solid #ced4da;
            padding: 10px;
        }
        QTabBar::tab {
            padding: 8px 15px;
            border: 1px solid #ced4da;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            background-color: #e9ecef;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            border-color: #ced4da;
        }
        QTabBar::tab:hover:!selected {
            background-color: #f8f9fa;
        }
        QTableWidget {
            border: 1px solid #dee2e6;
            gridline-color: #dee2e6;
            alternate-background-color: #f8f9fa; /* For alternating rows */
        }
        QHeaderView::section {
            background-color: #e9ecef; /* Slightly darker than table row hover for distinction */
            padding: 4px;
            border: 1px solid #dee2e6;
            font-weight: bold;
        }
        QListWidget {
            border: 1px solid #ced4da;
            border-radius: 4px;
        }
        QListWidget::item {
            padding: 5px;
        }
        QListWidget::item:alternate {
            background-color: #f8f9fa; /* For alternating rows if enabled */
        }
        QListWidget::item:hover {
            background-color: #e9ecef;
        }
        QListWidget::item:selected {
            background-color: #007bff; /* Blue for selection */
            color: white;
        }
    """)

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

    # Ensure "General" category exists for default templates
    general_category_id = db_manager.add_template_category("General", "General purpose templates")
    if general_category_id is None:
        print("CRITICAL ERROR: Could not create or find the 'General' template category. Default templates may not be added correctly.")
        # Allowing continuation, db_manager.add_default_template_if_not_exists should ideally handle
        # a missing category_id gracefully if it's designed to take category_name.
        # However, the task implies add_default_template_if_not_exists now expects category_id.
        # If general_category_id is None here, and add_default_template_if_not_exists *requires* a valid ID,
        # then the template addition will fail.
        # For this implementation, we are proceeding with the assumption that add_default_template_if_not_exists
        # was updated in step 2 to expect 'category_id'.
    
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
            created_file_on_disk = False
            if not os.path.exists(template_full_path):
                try:
                    df_content.to_excel(template_full_path, index=False)
                    print(f"Created default template file: {template_full_path}")
                    created_file_on_disk = True
                except Exception as e:
                    print(f"Erreur création template file {template_file_name} pour {lang_code}: {str(e)}")

            # Regardless of whether it was just created or already existed, try to register in DB
            # Determine template name and type from filename for registration
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
                'template_type': 'document_excel', # Assuming all these defaults are Excel
                'language_code': lang_code,
                'base_file_name': template_file_name,
                'description': f"Modèle Excel par défaut pour {template_name_for_db} en {lang_code}.",
                'category_id': general_category_id, # Use the fetched/created ID
                'is_default_for_type_lang': True
            }
            # Ensure 'category' (text) is not in metadata if add_default_template_if_not_exists strictly expects category_id
            template_metadata.pop('category', None)

            db_template_id = db_manager.add_default_template_if_not_exists(template_metadata)
            if db_template_id:
                if created_file_on_disk:
                    print(f"Successfully registered new default template '{template_name_for_db}' ({lang_code}) in DB with ID: {db_template_id}")
                # else: # File already existed, but ensure it's in DB
                    # print(f"Ensured default template '{template_name_for_db}' ({lang_code}) is registered in DB with ID: {db_template_id}")
            # else: # Error during DB registration
                # print(f"Failed to register default template '{template_name_for_db}' ({lang_code}) in DB.")



    # HTML Templates Metadata and Registration
    DEFAULT_HTML_TEMPLATES_METADATA = [
        {
            "base_file_name": "technical_specifications_template.html",
            "template_type": "HTML_TECH_SPECS",
            "display_name_fr": "Spécifications Techniques (HTML)",
            "description_fr": "Modèle HTML pour les spécifications techniques détaillées d'un produit ou projet.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "contact_page_template.html",
            "template_type": "HTML_CONTACT_PAGE",
            "display_name_fr": "Page de Contacts (HTML)",
            "description_fr": "Modèle HTML pour une page listant les contacts clés d'un projet.",
            "category_name": "Documents HTML",
        },

        {
            "base_file_name": "proforma_invoice_template.html",
            "template_type": "HTML_PROFORMA",
            "display_name_fr": "Facture Proforma (HTML)",
            "description_fr": "Modèle HTML pour la génération de factures proforma.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "packing_list_template.html",
            "template_type": "HTML_PACKING_LIST",
            "display_name_fr": "Liste de Colisage (HTML)",
            "description_fr": "Modèle HTML pour les listes de colisage.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "sales_contract_template.html",
            "template_type": "HTML_SALES_CONTRACT",
            "display_name_fr": "Contrat de Vente (HTML)",
            "description_fr": "Modèle HTML pour les contrats de vente.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "warranty_document_template.html",
            "template_type": "HTML_WARRANTY",
            "display_name_fr": "Document de Garantie (HTML)",
            "description_fr": "Modèle HTML pour les documents de garantie.",
            "category_name": "Documents HTML",
        },
        {
            "base_file_name": "cover_page_template.html",
            "template_type": "HTML_COVER_PAGE",
            "display_name_fr": "Page de Garde (HTML)",
            "description_fr": "Modèle HTML pour les pages de garde de documents.",
            "category_name": "Documents HTML",
        },
    ]

    HTML_TEMPLATE_CONTENTS = {
    "technical_specifications_template.html": '<!DOCTYPE html>\n<html lang="fr">\n<head>\n    <meta charset="UTF-8">\n    <title>SPECIFICATIONS TECHNIQUES - {{PRODUCT_NAME_TECH_SPEC}}</title>\n    <style>\n        body {\n            font-family: "Segoe UI", Arial, sans-serif;\n            margin: 0;\n            padding: 0;\n            background-color: #f4f7fc;\n            color: #333;\n            font-size: 10pt;\n        }\n        .page {\n            width: 210mm;\n            min-height: 297mm;\n            padding: 20mm;\n            margin: 10mm auto;\n            background-color: #fff;\n            box-shadow: 0 0 15px rgba(0,0,0,0.1);\n            page-break-after: always;\n            box-sizing: border-box;\n        }\n        .page:last-child {\n            page-break-after: avoid;\n        }\n        .header-container-tech {\n            display: flex;\n            justify-content: space-between;\n            align-items: flex-start;\n            border-bottom: 2px solid #3498db; /* Technical Blue */\n            padding-bottom: 15px;\n            margin-bottom: 25px;\n        }\n        .logo-tech {\n            max-width: 160px;\n            max-height: 70px;\n            object-fit: contain;\n        }\n        .document-title-tech {\n            text-align: right;\n        }\n        .document-title-tech h1 {\n            font-size: 20pt;\n            color: #3498db;\n            margin: 0 0 5px 0;\n            font-weight: 600;\n        }\n        .document-title-tech p {\n            font-size: 9pt;\n            color: #555;\n            margin: 2px 0;\n        }\n        .section-tech {\n            margin-bottom: 20px;\n        }\n        .section-tech h2 {\n            font-size: 14pt;\n            color: #2980b9; /* Darker Technical Blue */\n            border-bottom: 1px solid #aed6f1;\n            padding-bottom: 6px;\n            margin-top: 0; /* For first section on a page */\n            margin-bottom: 15px;\n            font-weight: 500;\n        }\n        .section-tech h3 {\n            font-size: 12pt;\n            color: #2c3e50;\n            margin-top: 15px;\n            margin-bottom: 8px;\n            font-weight: 500;\n        }\n        .section-tech p, .section-tech ul, .section-tech table {\n            font-size: 9.5pt;\n            line-height: 1.6;\n            margin-bottom: 10px;\n        }\n        .section-tech ul {\n            padding-left: 20px;\n            list-style-type: disc;\n        }\n        .section-tech li {\n            margin-bottom: 5px;\n        }\n        .tech-image-container {\n            text-align: center;\n            margin-bottom: 20px;\n            border: 1px solid #e0e0e0;\n            padding: 15px;\n            background-color: #f9f9f9;\n        }\n        .tech-image-container img {\n            max-width: 100%;\n            max-height: 400px; /* Adjust as needed */\n            object-fit: contain;\n            border: 1px solid #ccc;\n        }\n        .dimensions-table {\n            width: 100%;\n            border-collapse: collapse;\n        }\n        .dimensions-table th, .dimensions-table td {\n            border: 1px solid #bdc3c7; /* Gray borders */\n            padding: 8px 10px;\n            text-align: left;\n        }\n        .dimensions-table th {\n            background-color: #ecf0f1; /* Light Gray Blue */\n            font-weight: 500;\n        }\n        .footer-tech {\n            border-top: 1px solid #3498db;\n            padding-top: 10px;\n            margin-top: 30px;\n            text-align: center;\n            font-size: 8.5pt;\n            color: #777;\n        }\n        .page-number::before {\n            content: "Page " counter(page);\n        }\n        @page {\n            counter-increment: page;\n        }\n    </style>\n</head>\n<body>\n    <!-- Page 1: Image and Dimensions -->\n    <div class="page">\n        <div class="header-container-tech">\n            <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-tech">\n            <div class="document-title-tech">\n                <h1>SPECIFICATIONS TECHNIQUES</h1>\n                <p>Produit: {{PRODUCT_NAME_TECH_SPEC}}</p>\n                <p>Référence Projet: {{PROJECT_ID_TECH_SPEC}}</p>\n                <p>Date: {{DATE_TECH_SPEC}} | Version: {{VERSION_TECH_SPEC}}</p>\n            </div>\n        </div>\n\n        <div class="section-tech">\n            <h2>Aperçu Technique et Dimensions</h2>\n            <div class="tech-image-container">\n                <img src="{{TECHNICAL_IMAGE_PATH_OR_EMBED}}" alt="Image Technique du Produit">\n                <p><em>{{TECHNICAL_IMAGE_CAPTION}}</em></p>\n            </div>\n            <h3>Dimensions Principales</h3>\n            <table class="dimensions-table">\n                <thead>\n                    <tr>\n                        <th>Caractéristique</th>\n                        <th>Valeur</th>\n                        <th>Unité</th>\n                        <th>Tolérance</th>\n                    </tr>\n                </thead>\n                <tbody>\n                    {{DIMENSIONS_TABLE_ROWS_TECH_SPEC}}\n                </tbody>\n            </table>\n        </div>\n        <div class="footer-tech">\n            <span class="page-number"></span> | {{SELLER_COMPANY_NAME}} - Confidentiel\n        </div>\n    </div>\n\n    <!-- Page 2: Material Conditions and Performance -->\n    <div class="page">\n        <div class="header-container-tech" style="border-bottom:none; margin-bottom:5px;">\n             <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-tech" style="max-height:40px;">\n             <div class="document-title-tech" style="padding-top:10px;">\n                <p style="font-size:11pt; color:#3498db; font-weight:500;">SPECIFICATIONS TECHNIQUES - {{PRODUCT_NAME_TECH_SPEC}} (Suite)</p>\n            </div>\n        </div>\n        <div class="section-tech">\n            <h2>Conditions sur les Matériaux</h2>\n            <p>{{MATERIALS_GENERAL_OVERVIEW_TECH_SPEC}}</p>\n            {{MATERIALS_CONDITIONS_DETAILED_LIST_TECH_SPEC}}\n        </div>\n        <div class="section-tech">\n            <h2>Performances et Caractéristiques Opérationnelles</h2>\n            {{PERFORMANCE_SPECS_TECH_SPEC}}\n        </div>\n        <div class="footer-tech">\n             <span class="page-number"></span> | {{SELLER_COMPANY_NAME}} - Confidentiel\n        </div>\n    </div>\n\n    <!-- Page 3: Compliance, Environment, Maintenance, Notes -->\n    <div class="page">\n        <div class="header-container-tech" style="border-bottom:none; margin-bottom:5px;">\n             <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-tech" style="max-height:40px;">\n             <div class="document-title-tech" style="padding-top:10px;">\n                <p style="font-size:11pt; color:#3498db; font-weight:500;">SPECIFICATIONS TECHNIQUES - {{PRODUCT_NAME_TECH_SPEC}} (Suite)</p>\n            </div>\n        </div>\n        <div class="section-tech">\n            <h2>Conformité et Standards</h2>\n            {{COMPLIANCE_STANDARDS_TECH_SPEC}}\n        </div>\n        <div class="section-tech">\n            <h2>Environnement d\'\'\'Utilisation</h2>\n            {{OPERATING_ENVIRONMENT_TECH_SPEC}}\n        </div>\n        <div class="section-tech">\n            <h2>Maintenance et Entretien</h2>\n            {{MAINTENANCE_INFO_TECH_SPEC}}\n        </div>\n        <div class="section-tech">\n            <h2>Notes Complémentaires</h2>\n            <p>{{NOTES_TECH_SPEC}}</p>\n        </div>\n        <div class="footer-tech">\n             <span class="page-number"></span> | {{SELLER_COMPANY_NAME}} - Confidentiel\n        </div>\n    </div>\n</body>\n</html>\n',
    "contact_page_template.html": '<!DOCTYPE html>\n<html lang="fr">\n<head>\n    <meta charset="UTF-8">\n    <title>PAGE DE CONTACTS - Projet {{PROJECT_ID}}</title>\n    <style>\n        body {\n            font-family: "Segoe UI", Arial, sans-serif;\n            margin: 0;\n            padding: 0;\n            background-color: #f4f7fc;\n            color: #333;\n            font-size: 10pt;\n        }\n        .page {\n            width: 210mm;\n            min-height: 297mm;\n            padding: 20mm;\n            margin: 10mm auto;\n            background-color: #fff;\n            box-shadow: 0 0 15px rgba(0,0,0,0.1);\n            box-sizing: border-box;\n        }\n        .header-container-contact {\n            display: flex;\n            justify-content: space-between;\n            align-items: flex-start;\n            border-bottom: 2px solid #28a745; /* Green accent */\n            padding-bottom: 15px;\n            margin-bottom: 25px;\n        }\n        .logo-contact {\n            max-width: 160px;\n            max-height: 70px;\n            object-fit: contain;\n        }\n        .document-title-contact {\n            text-align: right;\n        }\n        .document-title-contact h1 {\n            font-size: 20pt;\n            color: #28a745;\n            margin: 0 0 5px 0;\n            font-weight: 600;\n        }\n        .document-title-contact p {\n            font-size: 9pt;\n            color: #555;\n            margin: 2px 0;\n        }\n        .intro-contact {\n            margin-bottom: 20px;\n            font-size: 11pt;\n            text-align: center;\n        }\n        .contacts-table {\n            width: 100%;\n            border-collapse: collapse;\n            margin-top: 15px;\n        }\n        .contacts-table th, .contacts-table td {\n            border: 1px solid #dee2e6;\n            padding: 10px 12px;\n            text-align: left;\n            font-size: 9.5pt;\n            vertical-align: top;\n        }\n        .contacts-table th {\n            background-color: #28a745; /* Green accent */\n            color: #fff;\n            font-weight: 500;\n            text-transform: uppercase;\n        }\n        .contacts-table tr:nth-child(even) {\n            background-color: #f8f9fa;\n        }\n        .contacts-table td a {\n            color: #007bff;\n            text-decoration: none;\n        }\n        .contacts-table td a:hover {\n            text-decoration: underline;\n        }\n        .footer-contact {\n            border-top: 1px solid #28a745;\n            padding-top: 10px;\n            margin-top: 30px;\n            text-align: center;\n            font-size: 8.5pt;\n            color: #777;\n        }\n    </style>\n</head>\n<body>\n    <div class="page">\n        <div class="header-container-contact">\n            <img src="{{SELLER_LOGO_PATH}}" alt="Logo Entreprise" class="logo-contact">\n            <div class="document-title-contact">\n                <h1>PAGE DE CONTACTS</h1>\n                <p>Projet: {{PROJECT_ID}} - {{PROJECT_NAME_CONTACT_PAGE}}</p>\n                <p>Date d\'\'\'impression: {{DATE_CONTACT_PAGE}}</p>\n            </div>\n        </div>\n\n        <div class="intro-contact">\n            <p>Voici la liste des principaux intervenants et contacts pour le projet <strong>{{PROJECT_NAME_CONTACT_PAGE}}</strong>.</p>\n        </div>\n\n        <table class="contacts-table">\n            <thead>\n                <tr>\n                    <th style="width:25%;">Rôle / Organisation</th>\n                    <th style="width:20%;">Nom du Contact</th>\n                    <th style="width:20%;">Fonction / Titre</th>\n                    <th style="width:20%;">Email</th>\n                    <th style="width:15%;">Téléphone</th>\n                </tr>\n            </thead>\n            <tbody>\n                {{CONTACTS_TABLE_ROWS_CONTACT_PAGE}}\n            </tbody>\n        </table>\n        \n        <div class="footer-contact">\n            <p>{{SELLER_COMPANY_NAME}} - Facilitant la communication pour votre projet.</p>\n        </div>\n    </div>\n</body>\n</html>\n',

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
                {{PRODUCTS_TABLE_ROWS}}
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
                {{PACKING_LIST_ITEMS}}
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
    # templates_root_dir is already defined above for Excel templates, can reuse
    
    print("\n--- Starting HTML Template File Creation & Registration ---") # Updated print
    html_category_id = db_manager.add_template_category("Documents HTML", "Modèles de documents basés sur HTML.")
    if html_category_id is None:
        print("CRITICAL ERROR: Could not create or find the 'Documents HTML' category. HTML templates may not be added correctly.")

    # Logic to create HTML files on disk
    for html_meta_for_file_creation in DEFAULT_HTML_TEMPLATES_METADATA:
        base_fn = html_meta_for_file_creation['base_file_name']
        if base_fn in HTML_TEMPLATE_CONTENTS:
            html_content_to_write = HTML_TEMPLATE_CONTENTS[base_fn]
            for lang_code_for_file in html_template_languages:
                lang_specific_template_dir = os.path.join(templates_root_dir, lang_code_for_file)
                os.makedirs(lang_specific_template_dir, exist_ok=True)

                template_file_full_path = os.path.join(lang_specific_template_dir, base_fn)

                if not os.path.exists(template_file_full_path):
                    try:
                        # Replace LANGUAGE_CODE placeholder for the specific language file
                        # This makes the <html lang="..."> attribute correct per file
                        # Other placeholders {{PLACEHOLDER}} are for runtime population by HtmlEditor
                        # Note: The main.py placeholders are like {{CLIENT_NAME}}, db.py context uses client.name
                        # The render_html_template function (from html_to_pdf_util) will handle the context mapping.
                        # Here, we only replace the {{LANGUAGE_CODE}} specific to the file instance.
                        lang_specific_content = html_content_to_write.replace("{{LANGUAGE_CODE}}", lang_code_for_file)

                        # Adjustments for Proforma Invoice product rows
                        if base_fn == "proforma_invoice_template.html":
                            lang_specific_content = lang_specific_content.replace(
                                "<tbody>\n                {{PRODUCTS_TABLE_ROWS}}\n                <!-- Example Row (to be replaced by HtmlEditor):",
                                "<tbody>\n                {{doc.products_table_rows}} <!-- Populated by db.py -->\n                <!-- Example Row (to be replaced by HtmlEditor):"
                            )
                        # Adjustments for Packing List items (if similar pattern)
                        elif base_fn == "packing_list_template.html":
                             lang_specific_content = lang_specific_content.replace(
                                "<tbody>\n                {{PACKING_LIST_ITEMS}}\n                <!-- Example Row:",
                                "<tbody>\n                {{doc.packing_list_items}} <!-- Populated by db.py -->\n                <!-- Example Row:"
                            )

                        with open(template_file_full_path, "w", encoding="utf-8") as f:
                            f.write(lang_specific_content)
                        print(f"CREATED Default HTML Template File: {template_file_full_path}")
                    except IOError as e_io:
                        print(f"ERROR creating HTML template file {template_file_full_path}: {e_io}")
                # else: # File already exists
                    # print(f"SKIP existing HTML Template File: {template_file_full_path}")

    # Original logic for DB registration (should now find the files created above)
    for html_meta in DEFAULT_HTML_TEMPLATES_METADATA:
        for lang_code in html_template_languages:
            template_file_path = os.path.join(templates_root_dir, lang_code, html_meta['base_file_name'])
            
            if os.path.exists(template_file_path): # Check again, in case creation failed
                db_template_name = f"{html_meta['display_name_fr']} ({lang_code.upper()})" # Keep display name consistent
                
                template_data_for_db = {
                    'template_name': db_template_name,
                    'template_type': html_meta['template_type'],
                    'language_code': lang_code,
                    'base_file_name': html_meta['base_file_name'],
                    'description': html_meta['description_fr'],
                    # category_id is preferred if html_category_id is valid
                    'category_id': html_category_id if html_category_id else None,
                    # Fallback to category_name if ID is None, add_default_template_if_not_exists should handle this
                    'category_name': html_meta['category_name'] if not html_category_id else None,
                    'is_default_for_type_lang': True if lang_code == 'fr' else False # Default French ones
                }
                # Clean up None values from dict to avoid passing them if not desired by add_default_template_if_not_exists
                template_data_for_db = {k:v for k,v in template_data_for_db.items() if v is not None}

                template_id = db_manager.add_default_template_if_not_exists(template_data_for_db)
                if template_id:
                    print(f"DB REGISTRATION SUCCESS: HTML Template '{db_template_name}' (Type: {html_meta['template_type']}, Lang: {lang_code}). DB ID: {template_id}")
                # else: # add_default_template_if_not_exists now handles "already exists" by returning existing ID, or None for other errors.
                    # print(f"DB REGISTRATION INFO: HTML Template '{db_template_name}' (Type: {html_meta['template_type']}, Lang: {lang_code}) may already exist or error during registration.")
            else:
                # This message means the file wasn't found for DB registration, which is an issue if it was supposed to be created.
                print(f"DB REGISTRATION SKIP: HTML Template file not found at '{template_file_path}'. Cannot register.")
    print("--- HTML Template File Creation & Registration Finished ---") # Updated print
       
    main_window = DocumentManager() 
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
