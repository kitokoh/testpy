# -*- coding: utf-8 -*-
import logging_config # Initialize logging FIRST
import sys
import os
import json
# import sqlite3 # Replaced by db_manager
import db as db_manager
import icons_rc # Import the compiled resources
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
# Updated import for dialogs
from dialogs import (
    SettingsDialog, TemplateDialog, ContactDialog, ProductDialog,
    EditProductLineDialog, CreateDocumentDialog, CompilePdfDialog, EditClientDialog
)
from client_widget import ClientWidget # MOVED ClientWidget
from datetime import datetime # Ensure datetime is explicitly imported if not already for populate_docx_template
from projectManagement import MainDashboard as ProjectManagementDashboard # Added for integration
from html_to_pdf_util import convert_html_to_pdf # For PDF generation from HTML

import sqlite3
# import logging # Handled by logging_config
# import logging.handlers # Handled by logging_config

# APP_ROOT_DIR definition remains in main.py
if getattr(sys, 'frozen', False):
    APP_ROOT_DIR = sys._MEIPASS
else:
    APP_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Import utility functions and constants
from utils import (
    load_config, save_config, populate_docx_template, generate_pdf_for_document,
    TEMPLATES_SUBDIR, CLIENTS_SUBDIR # If still needed by main.py directly
)

# --- Configuration & Database ---
# DATABASE_NAME is imported as CENTRAL_DATABASE_NAME and then assigned
DATABASE_NAME = CENTRAL_DATABASE_NAME

# Default directories are calculated in main.py using APP_ROOT_DIR and then passed to load_config
DEFAULT_TEMPLATES_DIR = os.path.join(APP_ROOT_DIR, TEMPLATES_SUBDIR)
DEFAULT_CLIENTS_DIR = os.path.join(APP_ROOT_DIR, CLIENTS_SUBDIR)

# Constants for specific template names remain if they are logical to main.py's setup
SPEC_TECH_TEMPLATE_NAME = "specification_technique_template.xlsx"
PROFORMA_TEMPLATE_NAME = "proforma_template.xlsx"
CONTRAT_VENTE_TEMPLATE_NAME = "contrat_vente_template.xlsx"
PACKING_LISTE_TEMPLATE_NAME = "packing_liste_template.xlsx"

# Initialize the central database using db_manager
# This should be called once, early in the application startup.
if __name__ == "__main__" or not hasattr(db_manager, '_initialized_main_app'): # Ensure it runs once for the app
    db_manager.initialize_database()
    if __name__ != "__main__": # Avoid setting attribute during test runs if module is imported
        # Use a unique attribute name to avoid conflict if db_manager is imported elsewhere too
        db_manager._initialized_main_app = True

# setup_logging() function removed, logging_config.py handles this.
# Ensure logging_config.py is imported at the very top of this file.
logger = logging_config.get_logger(__name__)


def load_stylesheet_global(app):
    """Loads the global stylesheet."""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    qss_file_path = os.path.join(script_dir, "style.qss")
    
    if not os.path.exists(qss_file_path):
        logger.warning(f"Stylesheet file not found: {qss_file_path}")
        # Create an empty style.qss if it doesn't exist to avoid crashing
        try:
            with open(qss_file_path, "w", encoding="utf-8") as f:
                f.write("/* Default empty stylesheet. Will be populated by the application. */")
            logger.info(f"Created an empty default stylesheet: {qss_file_path}")
        except IOError as e:
            logger.error(f"Error creating default stylesheet {qss_file_path}: {e}", exc_info=True)
            return # Cannot proceed if stylesheet cannot be created or read

    file = QFile(qss_file_path)
    if file.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(file)
        stylesheet = stream.readAll()
        app.setStyleSheet(stylesheet)
        logger.info(f"Stylesheet loaded successfully from {qss_file_path}")
        file.close()
    else:
        logger.error(f"Failed to open stylesheet file: {qss_file_path}, Error: {file.errorString()}")

# CONFIG is now loaded using the function from utils.py, passing APP_ROOT_DIR, and default dir paths
CONFIG = load_config(APP_ROOT_DIR, DEFAULT_TEMPLATES_DIR, DEFAULT_CLIENTS_DIR)

os.makedirs(CONFIG["templates_dir"], exist_ok=True)
os.makedirs(CONFIG["clients_dir"], exist_ok=True)
os.makedirs(os.path.join(APP_ROOT_DIR, "translations"), exist_ok=True) # Create translations directory
os.makedirs(os.path.join(APP_ROOT_DIR, "company_logos"), exist_ok=True) # Create company_logos directory

# --- Utility functions like get_config_dir, get_config_file_path, load_config, save_config, populate_docx_template MOVED to utils.py ---


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
        for title, attr_name, default_text, style_info in stat_items_data: # style renamed to style_info
            group = QGroupBox(title); group.setObjectName("statisticsGroup")
            group_layout = QVBoxLayout(group)
            label = QLabel(default_text) # Default text is data-like here (a number)
            label.setFont(QFont("Arial", 16, QFont.Bold)); label.setAlignment(Qt.AlignCenter)

            if attr_name == "urgent_label":
                label.setObjectName("urgentStatisticLabel")
            else:
                label.setObjectName("statisticValueLabel")

            # Inline style previously applied via 'style' variable is now removed.
            # Specific styling for urgent_label will be handled by QSS via its object name.
            # General styling for statisticValueLabel can also be in QSS.

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
            logger.error(f"Erreur de mise à jour des statistiques: {str(e)}", exc_info=True)
        # finally:
            # if conn: conn.close() # Old sqlite3 connection

class StatusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        status_name_for_delegate = index.data(Qt.UserRole) # This is the status name (text)
        bg_color_hex = "#95a5a6" # Default color
        icon_name = None

        if status_name_for_delegate:
            try:
                # Assuming status_type is 'Client' for this delegate context,
                # as this delegate is used in the client list.
                status_setting = db_manager.get_status_setting_by_name(status_name_for_delegate, 'Client')
                if status_setting:
                    if status_setting.get('color_hex'):
                        bg_color_hex = status_setting['color_hex']
                    if status_setting.get('icon_name'):
                        icon_name = status_setting['icon_name']
            except Exception as e:
                logger.warning(f"Error fetching status color/icon for delegate: {e}", exc_info=True)
                # Keep default color/no icon if error
        
        painter.save()

        # Draw background
        bg_qcolor = QColor(bg_color_hex)
        if option.state & QStyle.State_Selected:
            # If selected, use the view's selection color but perhaps blend or use a highlight border
            # For simplicity, let's use the QSS selection color directly.
            # The QListWidget::item:selected style in style.qss handles this.
            # However, since we are manually painting the background, we might need to
            # respect the selection state here or ensure QSS handles it over our paint.
            # A common approach is to let the default paint handle selection, then paint custom content.
            # For now, let's fill with status color, then let default selection paint over if needed.
            # Alternatively, if we want full control:
            painter.fillRect(option.rect, option.palette.highlight().color() if (option.state & QStyle.State_Selected) else bg_qcolor)
        else:
            painter.fillRect(option.rect, bg_qcolor)

        # Determine text color based on background lightness
        text_qcolor = QColor(Qt.black) 
        # Use the effective background color for lightness check (selection or custom)
        effective_bg_for_text = option.palette.highlight().color() if (option.state & QStyle.State_Selected) else bg_qcolor
        if effective_bg_for_text.lightnessF() < 0.5:
            text_qcolor = QColor(Qt.white)
        painter.setPen(text_qcolor)
        painter.setFont(option.font) # Use the font from the view/QSS

        # Icon and Text Drawing
        icon_size = 16 # Desired icon size
        left_padding = 5
        icon_text_spacing = 5

        text_rect = option.rect.adjusted(left_padding, 0, -5, 0) # Initial text rect with left padding

        if icon_name:
            icon = QIcon.fromTheme(icon_name) # Try to load from theme
            if not icon.isNull():
                icon_y_offset = (option.rect.height() - icon_size) // 2
                icon_rect = QRect(option.rect.left() + left_padding,
                                  option.rect.top() + icon_y_offset,
                                  icon_size, icon_size)
                icon.paint(painter, icon_rect, Qt.AlignCenter,
                           QIcon.Normal if (option.state & QStyle.State_Enabled) else QIcon.Disabled,
                           QIcon.On if (option.state & QStyle.State_Selected) else QIcon.Off) # Respect selection state for icon

                text_rect = option.rect.adjusted(left_padding + icon_size + icon_text_spacing, 0, -5, 0)

        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, index.data(Qt.DisplayRole)) 
        painter.restore()

class DocumentManager(QMainWindow):
    def __init__(self, app_root_dir): # Add app_root_dir parameter
        super().__init__()
        self.app_root_dir = app_root_dir # Store it
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
        
        form_group_box = QGroupBox(self.tr("Ajouter un Nouveau Client"))
        form_vbox_layout = QVBoxLayout(form_group_box) # Main layout for the group box

        # Create a container widget for the form elements
        self.form_container_widget = QWidget()
        creation_form_layout = QFormLayout(self.form_container_widget) # Set layout on the container
        creation_form_layout.setLabelAlignment(Qt.AlignRight)
        creation_form_layout.setSpacing(10)
        
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
        price_info_label.setObjectName("priceInfoLabel") # Used existing QSS rule
        creation_form_layout.addRow("", price_info_label) # Add info label below price input, span if needed or adjust layout
        self.language_select_combo = QComboBox()
        self.language_select_combo.addItems([
            self.tr("English only (en)"),
            self.tr("French only (fr)"),
            self.tr("Arabic only (ar)"),
            self.tr("Turkish only (tr)"),
            self.tr("Portuguese only (pt)"),
            self.tr("All supported languages (en, fr, ar, tr, pt)")
        ])
        creation_form_layout.addRow(self.tr("Langues:"), self.language_select_combo)
        self.create_client_button = QPushButton(self.tr("Créer Client")); self.create_client_button.setIcon(QIcon(":/icons/user-plus.svg"))
        self.create_client_button.setObjectName("primaryButton") # Use object name for global styling
        self.create_client_button.clicked.connect(self.execute_create_client) 
        creation_form_layout.addRow(self.create_client_button)

        # Add the container widget (with creation_form_layout) to the group box's layout
        form_vbox_layout.addWidget(self.form_container_widget)

        form_group_box.setCheckable(True)
        form_group_box.toggled.connect(self.form_container_widget.setVisible)
        form_group_box.setChecked(False) # Initially collapsed

        left_layout.addWidget(form_group_box)
        content_layout.addWidget(left_panel, 1)
        
        self.client_tabs_widget = QTabWidget(); self.client_tabs_widget.setTabsClosable(True) 
        self.client_tabs_widget.tabCloseRequested.connect(self.close_client_tab) 
        content_layout.addWidget(self.client_tabs_widget, 2)

        # self.main_area_stack.addWidget(self.documents_page_widget) # Add original content as first page
        # Correction: self.documents_page_widget is already added to the stack in setup_ui_main.
        # This line is redundant if setup_ui_main is called before this part of the code.
        # Ensure self.documents_page_widget is correctly added to the stack if it's not already.
        # If main_layout.addWidget(self.main_area_stack) is the structure, then
        # self.main_area_stack.addWidget(self.documents_page_widget) happens within setup_ui_main.

        self.main_area_stack.addWidget(self.documents_page_widget) # Add original content as first page
        # PM widget instantiated in __init__ and added to stack there

        self.load_countries_into_combo() 
        
    def create_actions_main(self): 
        self.settings_action = QAction(QIcon(":/icons/settings.svg"), self.tr("Paramètres"), self); self.settings_action.triggered.connect(self.open_settings_dialog)
        self.template_action = QAction(QIcon(":/icons/document.svg"), self.tr("Gérer les Modèles"), self); self.template_action.triggered.connect(self.open_template_manager_dialog) # Example icon
        self.status_action = QAction(self.tr("Gérer les Statuts"), self); self.status_action.triggered.connect(self.open_status_manager_dialog) # No icon change requested
        self.exit_action = QAction(self.tr("Quitter"), self); self.exit_action.setShortcut("Ctrl+Q"); self.exit_action.triggered.connect(self.close)
        
        # Action for Project Management
        self.project_management_action = QAction(QIcon(":/icons/preferences-system.svg"), self.tr("Gestion de Projet"), self)
        self.project_management_action.triggered.connect(self.show_project_management_view)

        # Action to go back to Documents view (optional, but good for navigation)
        self.documents_view_action = QAction(QIcon(":/icons/folder-documents.svg"), self.tr("Gestion Documents"), self)
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
                    logger.error("db_manager.add_country returned None during new country addition.")

            except Exception as e: # Catch any other unexpected exceptions during the process
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue lors de l'ajout du pays:\n{0}").format(str(e)))
                logger.error("Unexpected error in add_new_country_dialog", exc_info=True)
                
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
                    logger.error("db_manager.add_city returned None during new city addition.")

            except Exception as e: # Catch any other unexpected exceptions
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue lors de l'ajout de la ville:\n{0}").format(str(e)))
                logger.error("Unexpected error in add_new_city_dialog", exc_info=True)
                
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
            self.tr("English only (en)"): ["en"],
            self.tr("French only (fr)"): ["fr"],
            self.tr("Arabic only (ar)"): ["ar"],
            self.tr("Turkish only (tr)"): ["tr"],
            self.tr("Portuguese only (pt)"): ["pt"],
            self.tr("All supported languages (en, fr, ar, tr, pt)"): ["en", "fr", "ar", "tr", "pt"]
        }
        selected_langs_list = lang_map_from_display.get(lang_option_text, ["en"]) # Default to "en" if somehow not found
        
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
                                logger.info("CreateDocumentDialog accepted, all dialogs in sequence complete.")
                        else:
                                logger.info("CreateDocumentDialog cancelled.")
                    else:
                        QMessageBox.warning(self, self.tr("Erreur Données Client"),
                                            self.tr("Les données du client (ui_map_data) ne sont pas disponibles pour la création de documents."))
                            logger.warning("ui_map_data not available for CreateDocumentDialog.")
                else:
                        logger.info("ProductDialog cancelled.")
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
                    logger.info("ContactDialog cancelled.")
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
            logger.error(f"OS error during client folder creation for {client_name_val}", exc_info=True)
            # Rollback: If client was added to DB but folder creation failed, delete client from DB
            if actual_new_client_id:
                 db_manager.delete_client(actual_new_client_id) # This will also cascade-delete related Project and Tasks if FKs are set up correctly
                 logger.info(f"Rolled back client creation (ID: {actual_new_client_id}) due to folder creation error.")
                 QMessageBox.information(self, self.tr("Rollback"), self.tr("Le client a été retiré de la base de données suite à l'erreur de création de dossier."))
        except Exception as e_db: # Catch other potential errors from db_manager calls or logic
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur s'est produite lors de la création du client, du projet ou des tâches:\n{0}").format(str(e_db)))
            logger.error(f"Unexpected error during client/project/task creation for {client_name_val}", exc_info=True)
            # Rollback: If client or project was added before a subsequent error
            if new_project_id_central_db and db_manager.get_project_by_id(new_project_id_central_db):
                db_manager.delete_project(new_project_id_central_db) # Cascade delete tasks
                logger.info(f"Rolled back project creation (ID: {new_project_id_central_db}) due to error.")
            if actual_new_client_id and db_manager.get_client_by_id(actual_new_client_id):
                 db_manager.delete_client(actual_new_client_id)
                 logger.info(f"Rolled back client creation (ID: {actual_new_client_id}) due to subsequent error.")
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
            logger.error(self.tr("Erreur chargement statuts pour filtre: {0}").format(str(e)), exc_info=True)
            
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
                
        client_detail_widget = ClientWidget(client_data_to_show, self.config, self.app_root_dir, parent=self) # Add self.app_root_dir
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
                logger.warning("Archive status 'Archivé' not found in DB settings.")
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
                logger.info(f"Client {client_id_val} archived successfully.")
            else:
                QMessageBox.critical(self, self.tr("Erreur DB"),
                                     self.tr("Erreur d'archivage du client. Vérifiez les logs."))
                logger.error(f"Failed to archive client {client_id_val} in DB.")

        except Exception as e: # Catch generic db_manager errors or other issues
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'archivage du client:\n{0}").format(str(e)))
            logger.error(f"Error during client archival process for {client_id_val}", exc_info=True)
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
                    logger.error(f"Failed to delete client {client_id_val} from DB.")

            # except sqlite3.Error as e: QMessageBox.critical(self, "Erreur DB", f"Erreur DB suppression client:\n{str(e)}") # Old sqlite3 error
            except OSError as e_os:
                QMessageBox.critical(self, self.tr("Erreur Dossier"),
                                     self.tr("Le client a été supprimé de la base de données, mais une erreur est survenue lors de la suppression de son dossier:\n{0}").format(str(e_os)))
                logger.error(f"OS error deleting folder for client {client_id_val}", exc_info=True)
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
                 logger.error(f"Generic error deleting client {client_id_val}", exc_info=True)
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
                            logger.warning(f"Could not parse creation_date '{creation_date_str}' for client {client.get('client_id')}: {ve}")
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
            logger.error(f"Erreur vérification clients anciens: {str(e)}", exc_info=True)
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
            save_config(self.config) # utils.save_config - uses print currently
            os.makedirs(self.config["templates_dir"], exist_ok=True) 
            os.makedirs(self.config["clients_dir"], exist_ok=True)
            QMessageBox.information(self, self.tr("Paramètres Sauvegardés"), self.tr("Nouveaux paramètres enregistrés."))
            logger.info("Settings updated and saved.")
            
    def open_template_manager_dialog(self): TemplateDialog(self).exec_() 
        
    def open_status_manager_dialog(self): 
        QMessageBox.information(self, "Gestion des Statuts", "Fonctionnalité de gestion des statuts personnalisés à implémenter (e.g., via un nouveau QDialog).")
            
    def closeEvent(self, event): 
        save_config(self.config) 
        super().closeEvent(event)

def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Determine language for translations
    language_code = CONFIG.get("language", QLocale.system().name().split('_')[0]) # Default to system or 'en' if system locale is odd

# PDF Generation Logic (generate_pdf_for_document) MOVED to utils.py

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

    # Load global stylesheet from style.qss
    load_stylesheet_global(app)

    # Basic global stylesheet
    app.setStyleSheet("""
        QWidget {
            # /* General spacing and font settings for all widgets if needed */
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
            # color: white;
        # }
    # """)

    # Setup translations
    translator = QTranslator()
    translation_path = os.path.join(APP_ROOT_DIR, "translations", f"app_{language_code}.qm")
    if translator.load(translation_path):
        app.installTranslator(translator)
        logger.info(f"Loaded custom translation for {language_code} from {translation_path}")
    else:
        logger.warning(f"Failed to load custom translation for {language_code} from {translation_path}")
        # Fallback or load default internal strings if needed

    qt_translator = QTranslator()
    qt_translation_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qt_translator.load(QLocale(language_code), "qtbase", "_", qt_translation_path):
        app.installTranslator(qt_translator)
        logger.info(f"Loaded Qt base translations for {language_code} from {qt_translation_path}")
    else:
        logger.warning(f"Failed to load Qt base translations for {language_code} from {qt_translation_path}")

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
                            logger.info(f"Copied '{filename}' to '{target_lang_code}' directory.")
                        except Exception as e:
                            logger.error(f"Error copying '{filename}' to '{target_lang_code}': {e}", exc_info=True)
    else:
        logger.warning(f"Source French template directory '{source_lang_full_path}' does not exist. Cannot copy templates.")


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
        logger.critical("CRITICAL ERROR: Could not create or find the 'General' template category. Default templates may not be added correctly.")
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
                    logger.info(f"Created default template file: {template_full_path}")
                    created_file_on_disk = True
                except Exception as e:
                    logger.error(f"Erreur création template file {template_file_name} pour {lang_code}: {str(e)}", exc_info=True)

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
                    logger.info(f"Successfully registered new default template '{template_name_for_db}' ({lang_code}) in DB with ID: {db_template_id}")
                # else: # File already existed, but ensure it's in DB
                    # logger.info(f"Ensured default template '{template_name_for_db}' ({lang_code}) is registered in DB with ID: {db_template_id}") # Too verbose
            # else: # Error during DB registration
                # logger.warning(f"Failed to register default template '{template_name_for_db}' ({lang_code}) in DB. It might already exist with different metadata or another issue occurred.")



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
    
    logger.info("\n--- Starting HTML Template File Creation & Registration ---") # Updated print
    html_category_id = db_manager.add_template_category("Documents HTML", "Modèles de documents basés sur HTML.")
    if html_category_id is None:
        logger.critical("CRITICAL ERROR: Could not create or find the 'Documents HTML' category. HTML templates may not be added correctly.")

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
                        logger.info(f"CREATED Default HTML Template File: {template_file_full_path}")
                    except IOError as e_io:
                        logger.error(f"ERROR creating HTML template file {template_file_full_path}: {e_io}", exc_info=True)
                # else: # File already exists
                    # logger.debug(f"SKIP existing HTML Template File: {template_file_full_path}") # Too verbose for info

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
                    logger.info(f"DB REGISTRATION SUCCESS: HTML Template '{db_template_name}' (Type: {html_meta['template_type']}, Lang: {lang_code}). DB ID: {template_id}")
                # else: # add_default_template_if_not_exists now handles "already exists" by returning existing ID, or None for other errors.
                    # logger.warning(f"DB REGISTRATION INFO: HTML Template '{db_template_name}' (Type: {html_meta['template_type']}, Lang: {lang_code}) may already exist or error during registration.") # Still a bit verbose
            else:
                # This message means the file wasn't found for DB registration, which is an issue if it was supposed to be created.
                logger.warning(f"DB REGISTRATION SKIP: HTML Template file not found at '{template_file_path}'. Cannot register.")
    logger.info("--- HTML Template File Creation & Registration Finished ---")

    # --- Default Email Templates Setup ---
    logger.info("\n--- Starting Default Email Template File Creation & Registration ---")
    email_category_obj = db_manager.get_template_category_by_name("Modèles Email")
    email_category_id = email_category_obj['category_id'] if email_category_obj else None

    if email_category_id is None:
        logger.critical("CRITICAL ERROR: 'Modèles Email' category not found. Cannot register default email templates.")
    else:
        logger.info(f"Found 'Modèles Email' category with ID: {email_category_id}")

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
                    "fr": "Cher/Chère {{client.contact_person_name}},\n\nMerci pour votre intérêt pour nos services.\n\nCordialement,\n{{seller.personnel.representative_name}}\n{{seller.company_name}}",
                    "en": "Dear {{client.contact_person_name}},\n\nThank you for your interest in our services.\n\nSincerely,\n{{seller.personnel.representative_name}}\n{{seller.company_name}}",
                    "ar": "عزيزي/عزيزتي {{client.contact_person_name}}،\n\nشكراً لاهتمامك بخدماتنا.\n\nمع خالص التقدير،\n{{seller.personnel.representative_name}}\n{{seller.company_name}}",
                    "tr": "Sayın {{client.contact_person_name}},\n\nHizmetlerimize gösterdiğiniz ilgi için teşekkür ederiz.\n\nSaygılarımla,\n{{seller.personnel.representative_name}}\n{{seller.company_name}}",
                    "pt": "Prezado(a) {{client.contact_person_name}},\n\nObrigado pelo seu interesse em nossos serviços.\n\nAtenciosamente,\n{{seller.personnel.representative_name}}\n{{seller.company_name}}"
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
                    "fr": "Cher/Chère {{client.contact_person_name}},\n\nCeci est un email de suivi concernant notre récente discussion sur {{project.name}}.\n\nN'hésitez pas à nous contacter pour toute question.\n\nCordialement,\n{{seller.personnel.representative_name}}\n{{seller.company_name}}",
                    "en": "Dear {{client.contact_person_name}},\n\nThis is a follow-up email regarding our recent discussion about {{project.name}}.\n\nPlease feel free to contact us with any questions.\n\nSincerely,\n{{seller.personnel.representative_name}}\n{{seller.company_name}}",
                    "ar": "عزيزي/عزيزتي {{client.contact_person_name}}،\n\nهذه رسالة متابعة بخصوص مناقشتنا الأخيرة حول {{project.name}}.\n\nلا تتردد في الاتصال بنا لأية أسئلة.\n\nمع خالص التقدير،\n{{seller.personnel.representative_name}}\n{{seller.company_name}}",
                    "tr": "Sayın {{client.contact_person_name}},\n\n{{project.name}} hakkındaki son görüşmemizle ilgili bir takip e-postasıdır.\n\nHerhangi bir sorunuz olursa lütfen bizimle iletişime geçmekten çekinmeyin.\n\nSaygılarımla,\n{{seller.personnel.representative_name}}\n{{seller.company_name}}",
                    "pt": "Prezado(a) {{client.contact_person_name}},\n\nEste é um e-mail de acompanhamento sobre nossa recente discussão sobre {{project.name}}.\n\nSinta-se à vontade para entrar em contato conosco com qualquer dúvida.\n\nAtenciosamente,\n{{seller.personnel.representative_name}}\n{{seller.company_name}}"
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

        target_languages = ["fr", "en", "ar", "tr", "pt"] # Same as all_supported_template_langs

        for lang_code in target_languages:
            lang_specific_template_dir = os.path.join(CONFIG["templates_dir"], lang_code)
            os.makedirs(lang_specific_template_dir, exist_ok=True)

            for template_set in default_email_templates_data:
                name_key = template_set['name_key']

                # Determine display name prefix (fallback to English if specific language not found)
                display_name_prefix = template_set['display_name_prefix'].get(lang_code, template_set['display_name_prefix'].get('en', name_key))

                # Common subject for HTML and TXT version of a template set and language
                subject_content = template_set['subject'].get(lang_code, template_set['subject'].get('en', f"Message from {{{{seller.company_name}}}}"))

                # Process HTML version
                base_file_name_html = f"{name_key.lower()}_{lang_code}.html"
                full_path_html = os.path.join(lang_specific_template_dir, base_file_name_html)
                html_content_str = template_set['html_content'].get(lang_code, template_set['html_content'].get('en', "<p>Default HTML content.</p>"))
                description_html_str = template_set['description_html'].get(lang_code, template_set['description_html'].get('en', "Default HTML email template."))

                if not os.path.exists(full_path_html):
                    try:
                        with open(full_path_html, "w", encoding="utf-8") as f_html:
                            f_html.write(html_content_str)
                        logger.info(f"CREATED Default Email Template File (HTML): {full_path_html}")
                    except IOError as e_io_html:
                        logger.error(f"ERROR creating HTML email template file {full_path_html}: {e_io_html}", exc_info=True)
                        continue # Skip DB registration if file creation failed

                template_name_html_db = f"{display_name_prefix} (HTML) {lang_code.upper()}"
                db_manager.add_default_template_if_not_exists({
                    'template_name': template_name_html_db,
                    'template_type': 'EMAIL_BODY_HTML',
                    'language_code': lang_code,
                    'base_file_name': base_file_name_html,
                    'email_subject_template': subject_content,
                    'description': description_html_str,
                    'category_id': email_category_id,
                    'is_default_for_type_lang': False # Typically, users will set their own defaults
                })

                # Process TXT version
                base_file_name_txt = f"{name_key.lower()}_{lang_code}.txt"
                full_path_txt = os.path.join(lang_specific_template_dir, base_file_name_txt)
                txt_content_str = template_set['txt_content'].get(lang_code, template_set['txt_content'].get('en', "Default TXT content."))
                description_txt_str = template_set['description_txt'].get(lang_code, template_set['description_txt'].get('en', "Default TXT email template."))

                if not os.path.exists(full_path_txt):
                    try:
                        with open(full_path_txt, "w", encoding="utf-8") as f_txt:
                            f_txt.write(txt_content_str)
                        logger.info(f"CREATED Default Email Template File (TXT): {full_path_txt}")
                    except IOError as e_io_txt:
                        logger.error(f"ERROR creating TXT email template file {full_path_txt}: {e_io_txt}", exc_info=True)
                        continue # Skip DB registration

                template_name_txt_db = f"{display_name_prefix} (TXT) {lang_code.upper()}"
                db_manager.add_default_template_if_not_exists({
                    'template_name': template_name_txt_db,
                    'template_type': 'EMAIL_BODY_TXT',
                    'language_code': lang_code,
                    'base_file_name': base_file_name_txt,
                    'email_subject_template': subject_content, # Same subject for HTML/TXT pair
                    'description': description_txt_str,
                    'category_id': email_category_id,
                    'is_default_for_type_lang': False
                })
        logger.info("--- Default Email Template File Creation & Registration Finished ---")
       
    # APP_ROOT_DIR is defined globally in main.py
    main_window = DocumentManager(APP_ROOT_DIR) # Pass APP_ROOT_DIR
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    # setup_logging() # Removed, logging_config.py handles this by being imported.
    logger.info("Application starting...")
    main()
    logger.info("Application finished.")
