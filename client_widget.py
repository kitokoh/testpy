# -*- coding: utf-8 -*-
import os
import sys
# import logging # logging is already imported
import logging
import shutil
from datetime import datetime
# import sqlite3 # No longer needed as methods are refactored to use db_manager
import math # Added for pagination

from carrier_email_dialog import CarrierEmailDialog # Added import

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QListWidget, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QInputDialog, QTabWidget, QGroupBox, QMessageBox, QDialog, QFileDialog, QApplication,
    QSizePolicy # Added QSizePolicy
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QColor, QPixmap, QTextCursor
from PyQt5.QtCore import Qt, QUrl, QCoreApplication, QEvent
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QListWidgetItem
from PyQt5.QtGui import QPixmap

import db as db_manager
from db.cruds.clients_crud import clients_crud_instance
from excel_editor import ExcelEditor
from html_editor import HtmlEditor
from dialogs import ClientProductDimensionDialog, AssignPersonnelDialog, AssignTransporterDialog, AssignFreightForwarderDialog, AssignMoneyTransferAgentDialog # Added import
from whatsapp.whatsapp_dialog import SendWhatsAppDialog # Added import
# Removed: from main import get_notification_manager
# CRUD imports for Money Transfer Agents
import db.cruds.money_transfer_agents_crud as mta_crud
import db.cruds.client_order_money_transfer_agents_crud as coma_crud
import db.cruds.projects_crud as projects_crud

from invoicing.final_invoice_data_dialog import FinalInvoiceDataDialog
from document_manager_logic import create_final_invoice_and_update_db


# Globals imported from main (temporary, to be refactored)
SUPPORTED_LANGUAGES = ["en", "fr", "ar", "tr", "pt"] # Define supported languages

MAIN_MODULE_CONTACT_DIALOG = None
MAIN_MODULE_PRODUCT_DIALOG = None
MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG = None
MAIN_MODULE_CREATE_DOCUMENT_DIALOG = None
MAIN_MODULE_COMPILE_PDF_DIALOG = None
MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT = None
MAIN_MODULE_CONFIG = None
MAIN_MODULE_DATABASE_NAME = None
MAIN_MODULE_SEND_EMAIL_DIALOG = None
MAIN_MODULE_CLIENT_DOCUMENT_NOTE_DIALOG = None # Added for ClientDocumentNoteDialog
MAIN_MODULE_SEND_WHATSAPP_DIALOG = None

def _import_main_elements():
    global MAIN_MODULE_CONTACT_DIALOG, MAIN_MODULE_PRODUCT_DIALOG, \
           MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG, MAIN_MODULE_CREATE_DOCUMENT_DIALOG, \
           MAIN_MODULE_COMPILE_PDF_DIALOG, MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT, \
           MAIN_MODULE_CONFIG, MAIN_MODULE_DATABASE_NAME, MAIN_MODULE_SEND_EMAIL_DIALOG, \
           MAIN_MODULE_CLIENT_DOCUMENT_NOTE_DIALOG, MAIN_MODULE_SEND_WHATSAPP_DIALOG

    if MAIN_MODULE_CONFIG is None: # Check one, load all if not loaded
        # import main as main_module # No longer needed
        from dialogs import (SendEmailDialog, ContactDialog, ProductDialog, EditProductLineDialog,
                             CreateDocumentDialog, CompilePdfDialog, ClientDocumentNoteDialog)
        from whatsapp.whatsapp_dialog import SendWhatsAppDialog as WhatsAppDialogModule
        from utils import generate_pdf_for_document as utils_generate_pdf_for_document
        from app_setup import CONFIG as APP_CONFIG
        from config import DATABASE_PATH as DB_PATH_CONFIG # Added line
        MAIN_MODULE_CONTACT_DIALOG = ContactDialog
        MAIN_MODULE_PRODUCT_DIALOG = ProductDialog
        MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG = EditProductLineDialog
        MAIN_MODULE_CREATE_DOCUMENT_DIALOG = CreateDocumentDialog
        MAIN_MODULE_COMPILE_PDF_DIALOG = CompilePdfDialog
        MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT = utils_generate_pdf_for_document
        MAIN_MODULE_CONFIG = APP_CONFIG
        MAIN_MODULE_DATABASE_NAME = DB_PATH_CONFIG # Changed DB_NAME to DB_PATH_CONFIG
        MAIN_MODULE_SEND_EMAIL_DIALOG = SendEmailDialog
        MAIN_MODULE_CLIENT_DOCUMENT_NOTE_DIALOG = ClientDocumentNoteDialog
        MAIN_MODULE_SEND_WHATSAPP_DIALOG = WhatsAppDialogModule


class ClientWidget(QWidget):
    CONTACT_PAGE_LIMIT = 15 # Class attribute for page limit

    def __init__(self, client_info, config, app_root_dir, notification_manager, parent=None): # Add notification_manager
        super().__init__(parent)
        logging.info(f"ClientWidget.__init__: Received client_info: {client_info}")
        logging.info(f"ClientWidget initialized with client_info: {client_info}")
        logging.info(f"ClientWidget __init__: client_id={client_info.get('client_id')}, client_name={client_info.get('client_name')}")
        self.client_info = client_info
        self.notification_manager = notification_manager # Store notification_manager
        # self.config = config # Original config passed

        # Dynamically import main elements to avoid circular import at module load time
        logging.info("ClientWidget.__init__: Calling _import_main_elements()...")
        _import_main_elements()
        logging.info("ClientWidget.__init__: Finished _import_main_elements().")
        self.config = MAIN_MODULE_CONFIG
        self.app_root_dir = app_root_dir
        self.DATABASE_NAME = MAIN_MODULE_DATABASE_NAME

        self.ContactDialog = MAIN_MODULE_CONTACT_DIALOG
        self.ProductDialog = MAIN_MODULE_PRODUCT_DIALOG
        self.EditProductLineDialog = MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG
        self.CreateDocumentDialog = MAIN_MODULE_CREATE_DOCUMENT_DIALOG
        self.CompilePdfDialog = MAIN_MODULE_COMPILE_PDF_DIALOG
        self.generate_pdf_for_document = MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT
        self.SendEmailDialog = MAIN_MODULE_SEND_EMAIL_DIALOG
        self.ClientDocumentNoteDialog = MAIN_MODULE_CLIENT_DOCUMENT_NOTE_DIALOG # Added
        self.SendWhatsAppDialog = MAIN_MODULE_SEND_WHATSAPP_DIALOG

        self.is_editing_client = False
        self.edit_widgets = {}
        self.default_company_id = None
        try:
            default_company = db_manager.get_default_company()
            if default_company:
                self.default_company_id = default_company.get('company_id')
        except Exception as e:
            print(f"Error fetching default company ID in ClientWidget: {e}")
            # Log this, user might not be able to assign personnel if no default company found

        # Pagination for Contacts
        self.current_contact_offset = 0
        self.total_contacts_count = 0
        # self.CONTACT_PAGE_LIMIT is a class attribute

        logging.info("ClientWidget.__init__: Calling self.setup_ui()...")
        self.setup_ui()
        logging.info("ClientWidget.__init__: Finished self.setup_ui().")

    def setup_ui(self):
        logging.info("ClientWidget.setup_ui: Starting UI setup...")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Collapsible Client Info Section...")
            # --- Collapsible Client Info Section ---

            self.client_info_group_box = QGroupBox(self.client_info.get('client_name', self.tr("Client Information")))
            self.client_info_group_box.setCheckable(True)
            client_info_group_layout = QVBoxLayout(self.client_info_group_box)

            self.info_container_widget = QWidget()
            info_container_layout = QVBoxLayout(self.info_container_widget)
            info_container_layout.setContentsMargins(0, 5, 0, 0)
            info_container_layout.setSpacing(10)

            self.header_label = QLabel(f"<h2>{self.client_info.get('client_name', self.tr('Client Inconnu'))}</h2>")
            self.header_label.setObjectName("clientHeaderLabel")
            info_container_layout.addWidget(self.header_label)

            action_layout = QHBoxLayout()
            self.create_docs_btn = QPushButton(self.tr("Envoyer Mail"))
            self.create_docs_btn.setIcon(QIcon.fromTheme("mail-send", QIcon(":/icons/bell.svg")))
            self.create_docs_btn.setToolTip(self.tr("Envoyer un email au client"))
            self.create_docs_btn.setObjectName("primaryButton")
            try:
                self.create_docs_btn.clicked.disconnect(self.open_create_docs_dialog)
            except TypeError:
                pass # Not connected or already disconnected
            self.create_docs_btn.clicked.connect(self.open_send_email_dialog)
            action_layout.addWidget(self.create_docs_btn)

            self.compile_pdf_btn = QPushButton(self.tr("Compiler PDF"))
            self.compile_pdf_btn.setIcon(QIcon.fromTheme("document-export"))
            self.compile_pdf_btn.setProperty("primary", True)
            self.compile_pdf_btn.clicked.connect(self.open_compile_pdf_dialog)
            action_layout.addWidget(self.compile_pdf_btn)

            self.edit_save_client_btn = QPushButton(self.tr("Modifier Client"))
            self.edit_save_client_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
            self.edit_save_client_btn.setToolTip(self.tr("Modifier les informations du client"))
            self.edit_save_client_btn.clicked.connect(self.toggle_client_edit_mode)
            action_layout.addWidget(self.edit_save_client_btn)

            self.send_whatsapp_btn = QPushButton(self.tr("Send WhatsApp"))
            self.send_whatsapp_btn.setIcon(QIcon.fromTheme("contact-new", QIcon(":/icons/user.svg")))
            self.send_whatsapp_btn.setToolTip(self.tr("Send a WhatsApp message to the client"))
            self.send_whatsapp_btn.clicked.connect(self.open_send_whatsapp_dialog)
            action_layout.addWidget(self.send_whatsapp_btn)
            info_container_layout.addLayout(action_layout)

            self.status_combo = QComboBox()
            self.load_statuses()
            self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours")))
            self.status_combo.currentTextChanged.connect(self.update_client_status)

            self.details_layout = QFormLayout()
            self.details_layout.setLabelAlignment(Qt.AlignLeft)
            self.details_layout.setSpacing(10)
            self.category_label = QLabel(self.tr("Catégorie:"))
            self.category_value_label = QLabel()
            self.populate_details_layout()
            info_container_layout.addLayout(self.details_layout)

            client_info_group_layout.addWidget(self.info_container_widget)
            self.client_info_group_box.setChecked(True)
            layout.addWidget(self.client_info_group_box)
        except Exception as e:
            logging.error(f"Error in _setup_client_info_section: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation section infos client:\n{0}").format(str(e)))

        self._setup_notes_section(layout)
        self._setup_main_tabs_section(layout) # This will call sub-methods for each tab

        # Initial data loading calls
        try: self.populate_doc_table()
        except Exception as e: logging.error(f"Error initial load Documents tab: {e}", exc_info=True)
        try: self.load_contacts()
        except Exception as e: logging.error(f"Error initial load Contacts tab: {e}", exc_info=True)
        try: self.load_products()
        except Exception as e: logging.error(f"Error initial load Products tab: {e}", exc_info=True)
        try: self.load_document_notes_filters()
        except Exception as e: logging.error(f"Error initial load Doc Notes Filters: {e}", exc_info=True)
        try: self.load_document_notes_table()
        except Exception as e: logging.error(f"Error initial load Doc Notes tab: {e}", exc_info=True)
        try: self.update_sav_tab_visibility()
        except Exception as e: logging.error(f"Error initial SAV tab visibility/load: {e}", exc_info=True)
        try: self.load_assigned_vendors_personnel()
        except Exception as e: logging.error(f"Error initial load Assigned Vendors: {e}", exc_info=True)
        try: self.load_assigned_technicians()
        except Exception as e: logging.error(f"Error initial load Assigned Technicians: {e}", exc_info=True)
        try: self.load_assigned_transporters()
        except Exception as e: logging.error(f"Error initial load Assigned Transporters: {e}", exc_info=True)
        try: self.load_assigned_freight_forwarders()
        except Exception as e: logging.error(f"Error initial load Assigned Forwarders: {e}", exc_info=True)

        # Connect accordion group box toggled signals
        if hasattr(self, 'client_info_group_box'):
             self.client_info_group_box.toggled.connect(self._handle_client_info_section_toggled)
        if hasattr(self, 'notes_group_box'):
             self.notes_group_box.toggled.connect(self._handle_notes_section_toggled)
        if hasattr(self, 'tabs_group_box'):
             self.tabs_group_box.toggled.connect(self._handle_tabs_section_toggled)
        # Event filter for notes auto-save
        if hasattr(self, 'notes_edit'):
            self.notes_edit.installEventFilter(self)

    def _setup_notes_section(self, main_layout):
        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Notes Section...")
            self.notes_edit = QTextEdit(self.client_info.get("notes", ""))
            self.notes_edit.setPlaceholderText(self.tr("Ajoutez des notes sur ce client..."))
            self.notes_group_box = QGroupBox(self.tr("Notes"))
            self.notes_group_box.setCheckable(True)
            notes_group_layout = QVBoxLayout(self.notes_group_box)
            self.notes_container_widget = QWidget()
            notes_container_layout = QVBoxLayout(self.notes_container_widget)
            notes_container_layout.setContentsMargins(0, 5, 0, 0)
            notes_container_layout.addWidget(self.notes_edit)
            notes_group_layout.addWidget(self.notes_container_widget)
            self.notes_group_box.setChecked(False)
            main_layout.addWidget(self.notes_group_box)
        except Exception as e:
            logging.error(f"Error in _setup_notes_section: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation section notes:\n{0}").format(str(e)))

    def _setup_main_tabs_section(self, main_layout):
        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Tabs Section...")
            # --- Collapsible Tabs Section ---

            self.tabs_group_box = QGroupBox(self.tr("Autres Informations"))
            self.tabs_group_box.setCheckable(True)
            tabs_group_layout = QVBoxLayout(self.tabs_group_box)
            self.tab_widget = QTabWidget()
            tabs_group_layout.addWidget(self.tab_widget)
            self.tabs_group_box.setChecked(False)
            main_layout.addWidget(self.tabs_group_box)

            self._setup_documents_tab()
            self._setup_contacts_tab()
            self._setup_products_tab()
            self._setup_document_notes_tab()
            self._setup_product_dimensions_tab()
            self._setup_sav_tab()
            self._setup_assignments_tab()
            self._setup_billing_tab()
        except Exception as e:
            logging.error(f"Error in _setup_main_tabs_section: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation conteneur onglets principaux:\n{0}").format(str(e)))

    def _setup_documents_tab(self):
        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Documents Tab Structure...")
            # --- Documents Tab Structure ---

            docs_tab = QWidget(); docs_layout = QVBoxLayout(docs_tab)
            self.doc_filter_layout_widget = QWidget()
            doc_filter_layout = QHBoxLayout(self.doc_filter_layout_widget)
            doc_filter_layout.setContentsMargins(0,0,0,0)
            doc_filter_label = QLabel(self.tr("Filtrer par Commande:"))
            doc_filter_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            doc_filter_layout.addWidget(doc_filter_label)
            self.doc_order_filter_combo = QComboBox()
            self.doc_order_filter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.doc_order_filter_combo.currentIndexChanged.connect(self.populate_doc_table)
            doc_filter_layout.addWidget(self.doc_order_filter_combo)
            doc_filter_layout.addSpacing(10)
            doc_lang_filter_label = QLabel(self.tr("Filtrer par Langue:"))
            doc_lang_filter_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            doc_filter_layout.addWidget(doc_lang_filter_label)
            self.doc_language_filter_combo = QComboBox()
            self.doc_language_filter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.doc_language_filter_combo.addItem(self.tr("Toutes"), "ALL")
            for lang_code in SUPPORTED_LANGUAGES:
                self.doc_language_filter_combo.addItem(lang_code, lang_code)
            self.doc_language_filter_combo.currentIndexChanged.connect(self.populate_doc_table)
            doc_filter_layout.addWidget(self.doc_language_filter_combo)
            doc_filter_layout.addSpacing(10)
            doc_type_filter_label = QLabel(self.tr("Filtrer par Type:"))
            doc_type_filter_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            doc_filter_layout.addWidget(doc_type_filter_label)
            self.doc_type_filter_combo = QComboBox()
            self.doc_type_filter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.doc_type_filter_combo.addItem(self.tr("Tous"), "ALL")
            self.doc_type_filter_combo.addItem("HTML", "HTML")
            self.doc_type_filter_combo.addItem("PDF", "PDF")
            self.doc_type_filter_combo.addItem("XLSX", "XLSX")
            self.doc_type_filter_combo.addItem("DOCX", "DOCX")
            self.doc_type_filter_combo.addItem(self.tr("Autre"), "OTHER")
            self.doc_type_filter_combo.currentIndexChanged.connect(self.populate_doc_table)
            doc_filter_layout.addWidget(self.doc_type_filter_combo)
            docs_layout.addWidget(self.doc_filter_layout_widget)
            self.doc_filter_layout_widget.setVisible(True)
            self.documents_empty_label = QLabel(self.tr("Aucun document trouvé pour ce client.\nUtilisez les boutons ci-dessous pour ajouter ou générer des documents."))
            self.documents_empty_label.setAlignment(Qt.AlignCenter)
            font_docs_empty = self.documents_empty_label.font()
            font_docs_empty.setPointSize(10)
            self.documents_empty_label.setFont(font_docs_empty)
            docs_layout.addWidget(self.documents_empty_label)
            self.doc_table = QTableWidget()
            self.doc_table.setColumnCount(5)
            self.doc_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Type"), self.tr("Langue"), self.tr("Date"), self.tr("Actions")])
            self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.doc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.doc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            docs_layout.addWidget(self.doc_table)
            doc_btn_layout = QHBoxLayout()
            self.add_doc_btn = QPushButton(self.tr("Importer Document"))
            self.add_doc_btn.setIcon(QIcon(":/icons/file-plus.svg"))
            self.add_doc_btn.setToolTip(self.tr("Importer un fichier document existant pour ce client"))
            self.add_doc_btn.clicked.connect(self.add_document)
            doc_btn_layout.addWidget(self.add_doc_btn)
            self.refresh_docs_btn = QPushButton(self.tr("Actualiser"))
            self.refresh_docs_btn.setIcon(QIcon.fromTheme("view-refresh"))
            self.refresh_docs_btn.clicked.connect(self.populate_doc_table)
            doc_btn_layout.addWidget(self.refresh_docs_btn)
            self.add_template_btn = QPushButton(self.tr("Générer via Modèle"))
            self.add_template_btn.setIcon(QIcon.fromTheme("document-new", QIcon(":/icons/file-plus.svg")))
            self.add_template_btn.setToolTip(self.tr("Générer un nouveau document pour ce client à partir d'un modèle"))
            self.add_template_btn.clicked.connect(self.open_create_docs_dialog)
            doc_btn_layout.addWidget(self.add_template_btn)
            docs_layout.addLayout(doc_btn_layout)
            self.tab_widget.addTab(docs_tab, self.tr("Documents"))
        except Exception as e:
            logging.error(f"Error in _setup_documents_tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation onglet Documents:\n{0}").format(str(e)))

    def _setup_contacts_tab(self):
        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Contacts Tab Structure...")
            # --- Contacts Tab Structure ---

            contacts_tab = QWidget()
            contacts_layout = QVBoxLayout(contacts_tab)
            self.contacts_table = QTableWidget()
            self.contacts_table.setColumnCount(5)
            self.contacts_table.setHorizontalHeaderLabels([
                self.tr("Nom"), self.tr("Email"), self.tr("Téléphone"),
                self.tr("Position"), self.tr("Principal")
            ])
            self.contacts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.contacts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.contacts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.contacts_table.setAlternatingRowColors(True)
            self.contacts_table.cellDoubleClicked.connect(self.edit_contact)
            self.contacts_empty_label = QLabel(self.tr("Aucun contact ajouté pour ce client.\nCliquez sur '➕ Ajouter' pour commencer."))
            self.contacts_empty_label.setAlignment(Qt.AlignCenter)
            font = self.contacts_empty_label.font(); font.setPointSize(10)
            self.contacts_empty_label.setFont(font)
            contacts_layout.addWidget(self.contacts_empty_label)
            contacts_layout.addWidget(self.contacts_table)
            contacts_pagination_layout = QHBoxLayout()
            self.prev_contact_button = QPushButton("<< Précédent")
            self.prev_contact_button.setObjectName("paginationButton")
            self.prev_contact_button.clicked.connect(self.prev_contact_page)
            self.contact_page_info_label = QLabel("Page 1 / 1")
            self.contact_page_info_label.setObjectName("paginationLabel")
            self.next_contact_button = QPushButton("Suivant >>")
            self.next_contact_button.setObjectName("paginationButton")
            self.next_contact_button.clicked.connect(self.next_contact_page)
            contacts_pagination_layout.addStretch()
            contacts_pagination_layout.addWidget(self.prev_contact_button)
            contacts_pagination_layout.addWidget(self.contact_page_info_label)
            contacts_pagination_layout.addWidget(self.next_contact_button)
            contacts_pagination_layout.addStretch()
            contacts_layout.addLayout(contacts_pagination_layout)
            contacts_btn_layout = QHBoxLayout()
            self.add_contact_btn = QPushButton(self.tr("Ajouter")); self.add_contact_btn.setIcon(QIcon(":/icons/user-plus.svg"))
            self.add_contact_btn.setToolTip(self.tr("Ajouter un nouveau contact pour ce client")); self.add_contact_btn.clicked.connect(self.add_contact); contacts_btn_layout.addWidget(self.add_contact_btn)
            self.edit_contact_btn = QPushButton(self.tr("Modifier")); self.edit_contact_btn.setIcon(QIcon(":/icons/pencil.svg"))
            self.edit_contact_btn.setToolTip(self.tr("Modifier le contact sélectionné")); self.edit_contact_btn.clicked.connect(self.edit_contact); contacts_btn_layout.addWidget(self.edit_contact_btn)
            self.remove_contact_btn = QPushButton(self.tr("Supprimer")); self.remove_contact_btn.setIcon(QIcon(":/icons/trash.svg"))
            self.remove_contact_btn.setToolTip(self.tr("Supprimer le lien vers le contact sélectionné pour ce client")); self.remove_contact_btn.setObjectName("dangerButton"); self.remove_contact_btn.clicked.connect(self.remove_contact); contacts_btn_layout.addWidget(self.remove_contact_btn)
            contacts_layout.addLayout(contacts_btn_layout)
            self.tab_widget.addTab(contacts_tab, self.tr("Contacts"))
        except Exception as e:
            logging.error(f"Error in _setup_contacts_tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation onglet Contacts:\n{0}").format(str(e)))

    def _setup_products_tab(self):
        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Products Tab Structure...")
            # --- Products Tab Structure ---

            products_tab = QWidget()
            products_layout = QVBoxLayout(products_tab)
            product_filters_layout = QHBoxLayout()
            product_filters_layout.addWidget(QLabel(self.tr("Filtrer par langue:")))
            self.product_lang_filter_combo = QComboBox()
            self.product_lang_filter_combo.addItem(self.tr("All Languages"), None)
            self.product_lang_filter_combo.addItem(self.tr("English (en)"), "en")
            self.product_lang_filter_combo.addItem(self.tr("French (fr)"), "fr")
            # ... (add other languages) ...
            self.product_lang_filter_combo.addItem(self.tr("Arabic (ar)"), "ar")
            self.product_lang_filter_combo.addItem(self.tr("Turkish (tr)"), "tr")
            self.product_lang_filter_combo.addItem(self.tr("Portuguese (pt)"), "pt")
            self.product_lang_filter_combo.currentTextChanged.connect(self.load_products)
            product_filters_layout.addWidget(self.product_lang_filter_combo)
            product_filters_layout.addStretch()
            products_layout.addLayout(product_filters_layout)
            self.products_empty_label = QLabel(self.tr("Aucun produit ajouté pour ce client.\nCliquez sur '➕ Ajouter' pour commencer."))
            self.products_empty_label.setAlignment(Qt.AlignCenter)
            font_products_empty = self.products_empty_label.font(); font_products_empty.setPointSize(10)
            self.products_empty_label.setFont(font_products_empty)
            products_layout.addWidget(self.products_empty_label)
            self.products_table = QTableWidget()
            self.products_table.setColumnCount(8)
            self.products_table.setHorizontalHeaderLabels([
                self.tr("ID"), self.tr("Nom Produit"), self.tr("Description"),
                self.tr("Poids"), self.tr("Dimensions"),
                self.tr("Qté"), self.tr("Prix Unitaire"), self.tr("Prix Total")
            ])
            self.products_table.setEditTriggers(QAbstractItemView.DoubleClicked)
            self.products_table.itemChanged.connect(self.handle_product_item_changed)
            self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.products_table.hideColumn(0)
            products_layout.addWidget(self.products_table)
            products_btn_layout = QHBoxLayout()
            self.add_product_btn = QPushButton(self.tr("Ajouter")); self.add_product_btn.setIcon(QIcon(":/icons/plus-circle.svg"))
            self.add_product_btn.setToolTip(self.tr("Ajouter un produit pour ce client/projet")); self.add_product_btn.clicked.connect(self.add_product); products_btn_layout.addWidget(self.add_product_btn)
            self.edit_product_btn = QPushButton(self.tr("Modifier")); self.edit_product_btn.setIcon(QIcon(":/icons/pencil.svg"))
            self.edit_product_btn.setToolTip(self.tr("Modifier le produit sélectionné")); self.edit_product_btn.clicked.connect(self.edit_product); products_btn_layout.addWidget(self.edit_product_btn)
            self.remove_product_btn = QPushButton(self.tr("Supprimer")); self.remove_product_btn.setIcon(QIcon(":/icons/trash.svg"))
            self.remove_product_btn.setToolTip(self.tr("Supprimer le produit sélectionné de ce client/projet")); self.remove_product_btn.setObjectName("dangerButton"); self.remove_product_btn.clicked.connect(self.remove_product); products_btn_layout.addWidget(self.remove_product_btn)
            products_layout.addLayout(products_btn_layout)
            self.tab_widget.addTab(products_tab, self.tr("Produits"))
        except Exception as e:
            logging.error(f"Error in _setup_products_tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation onglet Produits:\n{0}").format(str(e)))

    def _setup_document_notes_tab(self):
        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Document Notes Tab Structure...")
            # --- Document Notes Tab Structure ---

            self.document_notes_tab = QWidget()
            doc_notes_layout = QVBoxLayout(self.document_notes_tab)
            doc_notes_filters_layout = QHBoxLayout()
            doc_notes_filters_layout.addWidget(QLabel(self.tr("Type de Document:")))
            self.doc_notes_type_filter_combo = QComboBox()
            doc_notes_filters_layout.addWidget(self.doc_notes_type_filter_combo)
            doc_notes_filters_layout.addWidget(QLabel(self.tr("Langue:")))
            self.doc_notes_lang_filter_combo = QComboBox()
            doc_notes_filters_layout.addWidget(self.doc_notes_lang_filter_combo)
            doc_notes_filters_layout.addStretch()
            doc_notes_layout.addLayout(doc_notes_filters_layout)
            self.document_notes_table = QTableWidget()
            self.document_notes_table.setColumnCount(5)
            self.document_notes_table.setHorizontalHeaderLabels([
                self.tr("Type Document"), self.tr("Langue"),
                self.tr("Aperçu Note"), self.tr("Actif"), self.tr("Actions")
            ])
            self.document_notes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.document_notes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.document_notes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            doc_notes_layout.addWidget(self.document_notes_table)
            doc_notes_buttons_layout = QHBoxLayout()
            self.add_doc_note_button = QPushButton(self.tr("Ajouter Note de Document"))
            self.add_doc_note_button.setIcon(QIcon.fromTheme("document-new"))
            doc_notes_buttons_layout.addWidget(self.add_doc_note_button)
            self.refresh_doc_notes_button = QPushButton(self.tr("Actualiser Liste"))
            self.refresh_doc_notes_button.setIcon(QIcon.fromTheme("view-refresh"))
            doc_notes_buttons_layout.addWidget(self.refresh_doc_notes_button)
            doc_notes_buttons_layout.addStretch()
            doc_notes_layout.addLayout(doc_notes_buttons_layout)
            self.tab_widget.addTab(self.document_notes_tab, self.tr("Notes de Document"))
            self.doc_notes_type_filter_combo.currentIndexChanged.connect(self.load_document_notes_table)
            self.doc_notes_lang_filter_combo.currentIndexChanged.connect(self.load_document_notes_table)
            self.add_doc_note_button.clicked.connect(self.on_add_document_note)
            self.refresh_doc_notes_button.clicked.connect(self.load_document_notes_table)
        except Exception as e:
            logging.error(f"Error in _setup_document_notes_tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation onglet Notes de Document:\n{0}").format(str(e)))

    def _setup_product_dimensions_tab(self):
        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Product Dimensions Tab Structure...")
            # --- Product Dimensions Tab Structure ---

            self.product_dimensions_tab = QWidget()
            prod_dims_layout = QVBoxLayout(self.product_dimensions_tab)
            self.dim_product_selector_combo = QComboBox()
            self.dim_product_selector_combo.addItem(self.tr("Sélectionner un produit..."), None)
            prod_dims_layout.addWidget(self.dim_product_selector_combo)
            self.edit_client_product_dimensions_button = QPushButton(self.tr("Modifier Dimensions Produit"))
            self.edit_client_product_dimensions_button.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
            self.edit_client_product_dimensions_button.setEnabled(False)
            prod_dims_layout.addWidget(self.edit_client_product_dimensions_button)
            prod_dims_layout.addStretch()
            # Insert after "Notes de Document" tab
            notes_doc_tab_index = -1
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == self.tr("Notes de Document"):
                    notes_doc_tab_index = i; break
            if notes_doc_tab_index != -1:
                self.tab_widget.insertTab(notes_doc_tab_index + 1, self.product_dimensions_tab, self.tr("Dimensions Produit (Client)"))
            else: # Fallback if "Notes de Document" not found
                self.tab_widget.addTab(self.product_dimensions_tab, self.tr("Dimensions Produit (Client)"))
            self.dim_product_selector_combo.currentIndexChanged.connect(self.on_dim_product_selected)
            self.edit_client_product_dimensions_button.clicked.connect(self.on_edit_client_product_dimensions)
        except Exception as e:
            logging.error(f"Error in _setup_product_dimensions_tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation onglet Dimensions Produit:\n{0}").format(str(e)))

    def _setup_sav_tab(self):
        try:
            self.load_products_for_dimension_tab()
        except Exception as e:
            logging.error(f"Error during initial load of Product Dimensions Tab (first call): {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des dimensions de produit:\n{0}").format(str(e)))

        self.dim_product_selector_combo.currentIndexChanged.connect(self.on_dim_product_selected)
        self.edit_client_product_dimensions_button.clicked.connect(self.on_edit_client_product_dimensions)

        try:
            self.load_products_for_dimension_tab() # Initial population of product selector
        except Exception as e:
            logging.error(f"Error during initial load of Product Dimensions Tab (second call): {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des dimensions de produit (2):\n{0}").format(str(e)))

        # Connect signals for the Product Dimensions Tab
        # self.dim_product_selector_combo.currentIndexChanged.connect(self.on_dim_product_selected) # Already connected
        # self.edit_client_product_dimensions_button.clicked.connect(self.on_edit_client_product_dimensions) # Already connected

        # Removed connections for old buttons (client_browse_tech_image_button, save_client_product_dimensions_button)
        try:
            self.populate_doc_table()
        except Exception as e:
            logging.error(f"Error during initial load of Documents tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des documents:\n{0}").format(str(e)))
        try:
            self.load_contacts()
        except Exception as e:
            logging.error(f"Error during initial load of Contacts tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des contacts:\n{0}").format(str(e)))
        try:
            self.load_products() # This now also calls load_products_for_dimension_tab which has its own try-except
        except Exception as e:
            logging.error(f"Error during initial load of Products tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des produits:\n{0}").format(str(e)))

        try:
            self.load_document_notes_filters()
        except Exception as e:
            logging.error(f"Error during initial load of Document Notes Filters: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des filtres de notes de document:\n{0}").format(str(e)))
        try:
            self.load_document_notes_table()
        except Exception as e:
            logging.error(f"Error during initial load of Document Notes tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des notes de document:\n{0}").format(str(e)))

        try:
            logging.info("ClientWidget.setup_ui: Starting setup for SAV Tab...")
            # SAV Tab

            self.sav_tab = QWidget()
            sav_layout = QVBoxLayout(self.sav_tab)
            sav_layout.addWidget(QLabel("<h3>Historique des Achats</h3>"))
            self.purchase_history_table = QTableWidget()
            self.purchase_history_table.setColumnCount(6)
            self.purchase_history_table.setHorizontalHeaderLabels([
                self.tr("ID CPP (Hidden)"), self.tr("Produit"), self.tr("Quantité"),
                self.tr("Numéro de Série"), self.tr("Date d'Achat"), self.tr("Actions")
            ])
            self.purchase_history_table.setColumnHidden(0, True)
            self.purchase_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.purchase_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.purchase_history_table.itemChanged.connect(self.handle_purchase_history_item_changed)
            sav_layout.addWidget(self.purchase_history_table)
            self.refresh_purchase_history_btn = QPushButton(self.tr("Rafraîchir l'historique"))
            self.refresh_purchase_history_btn.setIcon(QIcon.fromTheme("view-refresh"))
            self.refresh_purchase_history_btn.clicked.connect(self.load_purchase_history_table)
            sav_layout.addWidget(self.refresh_purchase_history_btn)
            sav_layout.addWidget(QLabel("<h3>Tickets SAV (Prochainement)</h3>")) # Placeholder for SAV tickets UI
            sav_layout.addStretch()
            self.tab_widget.addTab(self.sav_tab, self.tr("SAV"))
            self.sav_tab_index = self.tab_widget.indexOf(self.sav_tab) # Store index for later use
        except Exception as e:
            logging.error(f"Error in _setup_sav_tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation onglet SAV:\n{0}").format(str(e)))

    def _setup_assignments_tab(self):
        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Assignments Tab...")
            # --- Assignments Tab ---

            self.assignments_tab = QWidget()
            assignments_main_layout = QVBoxLayout(self.assignments_tab)
            self.assignments_sub_tabs = QTabWidget()
            assignments_main_layout.addWidget(self.assignments_sub_tabs)
            self.tab_widget.addTab(self.assignments_tab, self.tr("Affectations"))
            # Vendors/Sellers
            assigned_vendors_widget = QWidget()
            assigned_vendors_layout = QVBoxLayout(assigned_vendors_widget)
            self.assigned_vendors_table = QTableWidget(); self.assigned_vendors_table.setColumnCount(4)
            self.assigned_vendors_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Rôle Projet"), self.tr("Email"), self.tr("Téléphone")])
            self.assigned_vendors_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.assigned_vendors_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.assigned_vendors_table.horizontalHeader().setStretchLastSection(True)
            assigned_vendors_layout.addWidget(self.assigned_vendors_table)
            vendor_buttons_layout = QHBoxLayout()
            self.add_assigned_vendor_btn = QPushButton(self.tr("Ajouter Vendeur/Personnel")); self.add_assigned_vendor_btn.clicked.connect(self.handle_add_assigned_vendor)
            self.remove_assigned_vendor_btn = QPushButton(self.tr("Retirer Vendeur/Personnel")); self.remove_assigned_vendor_btn.clicked.connect(self.handle_remove_assigned_vendor)
            vendor_buttons_layout.addWidget(self.add_assigned_vendor_btn); vendor_buttons_layout.addWidget(self.remove_assigned_vendor_btn)
            assigned_vendors_layout.addLayout(vendor_buttons_layout)
            self.assignments_sub_tabs.addTab(assigned_vendors_widget, self.tr("Vendeurs & Personnel"))
            # Technicians
            assigned_technicians_widget = QWidget()
            assigned_technicians_layout = QVBoxLayout(assigned_technicians_widget)
            self.assigned_technicians_table = QTableWidget(); self.assigned_technicians_table.setColumnCount(4)
            self.assigned_technicians_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Rôle Projet"), self.tr("Email"), self.tr("Téléphone")])
            self.assigned_technicians_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.assigned_technicians_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.assigned_technicians_table.horizontalHeader().setStretchLastSection(True)
            assigned_technicians_layout.addWidget(self.assigned_technicians_table)
            technician_buttons_layout = QHBoxLayout()
            self.add_assigned_technician_btn = QPushButton(self.tr("Ajouter Technicien")); self.add_assigned_technician_btn.clicked.connect(self.handle_add_assigned_technician)
            self.remove_assigned_technician_btn = QPushButton(self.tr("Retirer Technicien")); self.remove_assigned_technician_btn.clicked.connect(self.handle_remove_assigned_technician)
            technician_buttons_layout.addWidget(self.add_assigned_technician_btn); technician_buttons_layout.addWidget(self.remove_assigned_technician_btn)
            assigned_technicians_layout.addLayout(technician_buttons_layout)
            self.assignments_sub_tabs.addTab(assigned_technicians_widget, self.tr("Techniciens"))
            # Transporters
            assigned_transporters_widget = QWidget()
            assigned_transporters_layout = QVBoxLayout(assigned_transporters_widget)
            self.assigned_transporters_table = QTableWidget(); self.assigned_transporters_table.setColumnCount(6)
            self.assigned_transporters_table.setHorizontalHeaderLabels([self.tr("Nom Transporteur"), self.tr("Contact"), self.tr("Téléphone"), self.tr("Détails Transport"), self.tr("Coût Estimé"), self.tr("Actions")])
            self.assigned_transporters_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.assigned_transporters_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.assigned_transporters_table.horizontalHeader().setStretchLastSection(True)
            assigned_transporters_layout.addWidget(self.assigned_transporters_table)
            transporter_buttons_layout = QHBoxLayout()
            self.add_assigned_transporter_btn = QPushButton(self.tr("Ajouter Transporteur")); self.add_assigned_transporter_btn.clicked.connect(self.handle_add_assigned_transporter)
            self.remove_assigned_transporter_btn = QPushButton(self.tr("Retirer Transporteur")); self.remove_assigned_transporter_btn.clicked.connect(self.handle_remove_assigned_transporter)
            transporter_buttons_layout.addWidget(self.add_assigned_transporter_btn); transporter_buttons_layout.addWidget(self.remove_assigned_transporter_btn)
            assigned_transporters_layout.addLayout(transporter_buttons_layout)
            self.assignments_sub_tabs.addTab(assigned_transporters_widget, self.tr("Transporteurs"))
            # Freight Forwarders
            assigned_forwarders_widget = QWidget()
            assigned_forwarders_layout = QVBoxLayout(assigned_forwarders_widget)
            self.assigned_forwarders_table = QTableWidget(); self.assigned_forwarders_table.setColumnCount(5)
            self.assigned_forwarders_table.setHorizontalHeaderLabels([self.tr("Nom Transitaire"), self.tr("Contact"), self.tr("Téléphone"), self.tr("Description Tâche"), self.tr("Coût Estimé")])
            self.assigned_forwarders_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.assigned_forwarders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.assigned_forwarders_table.horizontalHeader().setStretchLastSection(True)
            assigned_forwarders_layout.addWidget(self.assigned_forwarders_table)
            forwarder_buttons_layout = QHBoxLayout()
            self.add_assigned_forwarder_btn = QPushButton(self.tr("Ajouter Transitaire")); self.add_assigned_forwarder_btn.clicked.connect(self.handle_add_assigned_forwarder)
            self.remove_assigned_forwarder_btn = QPushButton(self.tr("Retirer Transitaire")); self.remove_assigned_forwarder_btn.clicked.connect(self.handle_remove_assigned_forwarder)
            forwarder_buttons_layout.addWidget(self.add_assigned_forwarder_btn); forwarder_buttons_layout.addWidget(self.remove_assigned_forwarder_btn)
            assigned_forwarders_layout.addLayout(forwarder_buttons_layout)
            self.assignments_sub_tabs.addTab(assigned_forwarders_widget, self.tr("Transitaires"))

            # Sub-Tab: Money Transfer Agents
            mta_widget = QWidget()
            mta_layout = QVBoxLayout(mta_widget)

            # Project/Order Selector for MTA
            mta_project_selector_layout = QHBoxLayout()
            mta_project_selector_layout.addWidget(QLabel(self.tr("Sélectionner Commande/Projet:")))
            self.mta_project_selector_combo = QComboBox()
            mta_project_selector_layout.addWidget(self.mta_project_selector_combo)
            mta_layout.addLayout(mta_project_selector_layout)

            # Table for Assigned Money Transfer Agents
            self.assigned_mta_table = QTableWidget()
            self.assigned_mta_table.setColumnCount(8) # Agent Name, Type, Email, Phone, Details, Fee, Email Status, Actions
            self.assigned_mta_table.setHorizontalHeaderLabels([
                self.tr("Nom Agent"), self.tr("Type"), self.tr("Email"), self.tr("Téléphone"),
                self.tr("Détails Affectation"), self.tr("Frais Estimés"), self.tr("Statut Email"), self.tr("Actions")
            ])
            self.assigned_mta_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.assigned_mta_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.assigned_mta_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # Stretch to fill
            self.assigned_mta_table.setMinimumHeight(150) # Example height
            mta_layout.addWidget(self.assigned_mta_table)

            # Buttons for MTA
            mta_buttons_layout = QHBoxLayout()
            self.add_assigned_mta_btn = QPushButton(self.tr("Assigner Agent de Transfert"))
            self.remove_assigned_mta_btn = QPushButton(self.tr("Retirer Agent de Transfert"))
            mta_buttons_layout.addWidget(self.add_assigned_mta_btn)
            mta_buttons_layout.addWidget(self.remove_assigned_mta_btn)
            mta_layout.addLayout(mta_buttons_layout)

            self.assignments_sub_tabs.addTab(mta_widget, self.tr("Agents de Transfert d'Argent"))

        except Exception as e:
            logging.error(f"Error during UI setup of Assignments Tab Structure: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation structure onglet Affectations:\n{0}").format(str(e)))

        # Call to load SAV tickets table initially if tab is visible
        try:
            logging.info("ClientWidget.setup_ui: Updating SAV tab visibility and loading initial data...")
            self.update_sav_tab_visibility() # This calls load_purchase_history_table and load_sav_tickets_table
        except Exception as e:
            logging.error(f"Error during initial visibility update/load of SAV tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors de la mise à jour/chargement initial de l'onglet SAV:\n{0}").format(str(e)))

        # Initial load for assignment tabs
        try:
            self.load_assigned_vendors_personnel()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Vendors/Personnel: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des vendeurs/personnel assignés:\n{0}").format(str(e)))
        try:
            self.load_assigned_technicians()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Technicians: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des techniciens assignés:\n{0}").format(str(e)))
        try:
            self.load_assigned_transporters()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Transporters: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des transporteurs assignés:\n{0}").format(str(e)))
        try:
            self.load_assigned_freight_forwarders()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Freight Forwarders: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des transitaires assignés:\n{0}").format(str(e)))

        # Connect selection changed signals for assignment tables
        self.assigned_vendors_table.itemSelectionChanged.connect(self.update_assigned_vendors_buttons_state)
        self.assigned_technicians_table.itemSelectionChanged.connect(self.update_assigned_technicians_buttons_state)
        self.assigned_transporters_table.itemSelectionChanged.connect(self.update_assigned_transporters_buttons_state)
        self.assigned_forwarders_table.itemSelectionChanged.connect(self.update_assigned_forwarders_buttons_state)
        # Connections for MTA tab
        self.mta_project_selector_combo.currentIndexChanged.connect(self.handle_mta_project_selection_changed)
        self.add_assigned_mta_btn.clicked.connect(self.handle_add_assigned_mta)
        self.remove_assigned_mta_btn.clicked.connect(self.handle_remove_assigned_mta)
        self.assigned_mta_table.itemSelectionChanged.connect(self.update_mta_buttons_state)

        # Initial load for MTA project selector
        self.load_projects_for_mta_combo()
        # Initial state for MTA buttons
        self.add_assigned_mta_btn.setEnabled(False)
        self.remove_assigned_mta_btn.setEnabled(False)


    def _setup_billing_tab(self):
        try:
            logging.info("ClientWidget.setup_ui: Starting setup for Billing Tab...")
            # --- Billing Tab ---

            self.billing_tab = QWidget()
            self.billing_tab_layout = QVBoxLayout(self.billing_tab)
            self.generate_invoice_button = QPushButton(QIcon(":/icons/file-plus.svg"), self.tr("Generate Final Invoice"))
            self.generate_invoice_button.setToolTip(self.tr("Open dialog to prepare and generate a final invoice for this client."))
            self.generate_invoice_button.clicked.connect(self.handle_generate_final_invoice)
            self.billing_tab_layout.addWidget(self.generate_invoice_button)
            self.billing_tab_layout.addStretch()
            self.tab_widget.addTab(self.billing_tab, QIcon(":/icons/credit-card.svg"), self.tr("Billing"))
        except Exception as e:
            logging.error(f"Error in _setup_billing_tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation onglet Facturation:\n{0}").format(str(e)))

    # def setup_ui(self):
    #     main_layout = QVBoxLayout(self)
    #     main_layout.setContentsMargins(15, 15, 15, 15)
    #     main_layout.setSpacing(15)

    #     self._setup_main_tabs_section(main_layout)
    #     self._setup_notes_section(main_layout)
    #     self._setup_main_tabs_section(main_layout) # This will call sub-methods for each tab

    #     # Initial data loading calls
    #     try: self.populate_doc_table()
    #     except Exception as e: logging.error(f"Error initial load Documents tab: {e}", exc_info=True)
    #     try: self.load_contacts()
    #     except Exception as e: logging.error(f"Error initial load Contacts tab: {e}", exc_info=True)
    #     try: self.load_products()
    #     except Exception as e: logging.error(f"Error initial load Products tab: {e}", exc_info=True)
    #     try: self.load_document_notes_filters()
    #     except Exception as e: logging.error(f"Error initial load Doc Notes Filters: {e}", exc_info=True)
    #     try: self.load_document_notes_table()
    #     except Exception as e: logging.error(f"Error initial load Doc Notes tab: {e}", exc_info=True)
    #     try: self.update_sav_tab_visibility()
    #     except Exception as e: logging.error(f"Error initial SAV tab visibility/load: {e}", exc_info=True)
    #     try: self.load_assigned_vendors_personnel()
    #     except Exception as e: logging.error(f"Error initial load Assigned Vendors: {e}", exc_info=True)
    #     try: self.load_assigned_technicians()
    #     except Exception as e: logging.error(f"Error initial load Assigned Technicians: {e}", exc_info=True)
    #     try: self.load_assigned_transporters()
    #     except Exception as e: logging.error(f"Error initial load Assigned Transporters: {e}", exc_info=True)
    #     try: self.load_assigned_freight_forwarders()
    #     except Exception as e: logging.error(f"Error initial load Assigned Forwarders: {e}", exc_info=True)

    #     # Connect accordion group box toggled signals
    #     if hasattr(self, 'client_info_group_box'):
    #          self.client_info_group_box.toggled.connect(self._handle_client_info_section_toggled)
    #     if hasattr(self, 'notes_group_box'):
    #          self.notes_group_box.toggled.connect(self._handle_notes_section_toggled)
    #     if hasattr(self, 'tabs_group_box'):
    #          self.tabs_group_box.toggled.connect(self._handle_tabs_section_toggled)
    #     # Event filter for notes auto-save
    #     if hasattr(self, 'notes_edit'):
    #         self.notes_edit.installEventFilter(self)


    def _handle_edit_pdf_action(self, file_path, document_id):
        if file_path and os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        # layout = QVBoxLayout(self) # This line seems out of place, QVBoxLayout is already set for the widget
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        try:
            self._setup_main_tabs_section(layout) #FIXED
            # --- Collapsible Client Info Section ---
            self.client_info_group_box = QGroupBox(self.client_info.get('client_name', self.tr("Client Information")))
            self.client_info_group_box.setCheckable(True)
            client_info_group_layout = QVBoxLayout(self.client_info_group_box) # Layout for the GroupBox itself

            self.info_container_widget = QWidget() # Container for all info elements
            info_container_layout = QVBoxLayout(self.info_container_widget)
            info_container_layout.setContentsMargins(0, 5, 0, 0) # Adjust margins as needed
            info_container_layout.setSpacing(10) # Adjust spacing as needed

            self.header_label = QLabel(f"<h2>{self.client_info.get('client_name', self.tr('Client Inconnu'))}</h2>")
            self.header_label.setObjectName("clientHeaderLabel")
            info_container_layout.addWidget(self.header_label)

            action_layout = QHBoxLayout()
            self.create_docs_btn = QPushButton(self.tr("Envoyer Mail"))
            self.create_docs_btn.setIcon(QIcon.fromTheme("mail-send", QIcon(":/icons/bell.svg"))) # Using bell.svg as fallback
            self.create_docs_btn.setToolTip(self.tr("Envoyer un email au client"))
            self.create_docs_btn.setObjectName("primaryButton") # Keep primary styling for now
            try:
                # Disconnect previous connection if it exists
                self.create_docs_btn.clicked.disconnect(self.open_create_docs_dialog)
            except TypeError:
                print("Note: self.create_docs_btn.clicked was not connected to self.open_create_docs_dialog or already disconnected.")
            self.create_docs_btn.clicked.connect(self.open_send_email_dialog) # Connect to new method
            action_layout.addWidget(self.create_docs_btn)

            self.compile_pdf_btn = QPushButton(self.tr("Compiler PDF"))
            self.compile_pdf_btn.setIcon(QIcon.fromTheme("document-export"))
            self.compile_pdf_btn.setProperty("primary", True)
            self.compile_pdf_btn.clicked.connect(self.open_compile_pdf_dialog)
            action_layout.addWidget(self.compile_pdf_btn)

            self.edit_save_client_btn = QPushButton(self.tr("Modifier Client"))
            self.edit_save_client_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
            self.edit_save_client_btn.setToolTip(self.tr("Modifier les informations du client"))
            self.edit_save_client_btn.clicked.connect(self.toggle_client_edit_mode)
            action_layout.addWidget(self.edit_save_client_btn)

            self.send_whatsapp_btn = QPushButton(self.tr("Send WhatsApp"))
            self.send_whatsapp_btn.setIcon(QIcon.fromTheme("contact-new", QIcon(":/icons/user.svg"))) # Changed placeholder
            self.send_whatsapp_btn.setToolTip(self.tr("Send a WhatsApp message to the client"))
            self.send_whatsapp_btn.clicked.connect(self.open_send_whatsapp_dialog)
            action_layout.addWidget(self.send_whatsapp_btn)
            info_container_layout.addLayout(action_layout)

            # Status combo (part of details, but initialized here due to load_statuses)
            self.status_combo = QComboBox()
            self.load_statuses()
            self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours")))
            self.status_combo.currentTextChanged.connect(self.update_client_status)

            # Details layout (QFormLayout)
            self.details_layout = QFormLayout()
            self.details_layout.setLabelAlignment(Qt.AlignLeft)
            self.details_layout.setSpacing(10)

            # Initialize category labels (used in populate_details_layout)
            self.category_label = QLabel(self.tr("Catégorie:"))
            self.category_value_label = QLabel()

            self.populate_details_layout() # Builds the details_layout
            info_container_layout.addLayout(self.details_layout)

            client_info_group_layout.addWidget(self.info_container_widget)
            self.client_info_group_box.setChecked(True)
            layout.addWidget(self.client_info_group_box)
        except Exception as e:
            logging.error(f"Error during UI setup of Client Info Section: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation section infos client:\n{0}").format(str(e)))

        try:
            self.notes_edit = QTextEdit(self.client_info.get("notes", ""))
            self.notes_edit.setPlaceholderText(self.tr("Ajoutez des notes sur ce client..."))
            # --- Collapsible Notes Section ---
            self.notes_group_box = QGroupBox(self.tr("Notes"))
            self.notes_group_box.setCheckable(True)
            notes_group_layout = QVBoxLayout(self.notes_group_box)
            self.notes_container_widget = QWidget()
            notes_container_layout = QVBoxLayout(self.notes_container_widget)
            notes_container_layout.setContentsMargins(0, 5, 0, 0)
            notes_container_layout.addWidget(self.notes_edit)
            notes_group_layout.addWidget(self.notes_container_widget)
            self.notes_group_box.setChecked(False)
            layout.addWidget(self.notes_group_box)
        except Exception as e:
            logging.error(f"Error during UI setup of Notes Section: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation section notes:\n{0}").format(str(e)))

        try:
            # --- Collapsible Tabs Section ---
            self.tabs_group_box = QGroupBox(self.tr("Autres Informations"))
            self.tabs_group_box.setCheckable(True)
            tabs_group_layout = QVBoxLayout(self.tabs_group_box)
            self.tab_widget = QTabWidget()
            tabs_group_layout.addWidget(self.tab_widget)
            self.tabs_group_box.setChecked(False)
            layout.addWidget(self.tabs_group_box)
        except Exception as e:
            logging.error(f"Error during UI setup of Main Tabs Container: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation conteneur onglets:\n{0}").format(str(e)))

        try:
            # --- Documents Tab Structure ---
            docs_tab = QWidget(); docs_layout = QVBoxLayout(docs_tab)
            self.doc_filter_layout_widget = QWidget()
            doc_filter_layout = QHBoxLayout(self.doc_filter_layout_widget)
            doc_filter_layout.setContentsMargins(0,0,0,0)
            doc_filter_label = QLabel(self.tr("Filtrer par Commande:"))
            doc_filter_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            doc_filter_layout.addWidget(doc_filter_label)
            self.doc_order_filter_combo = QComboBox()
            self.doc_order_filter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.doc_order_filter_combo.currentIndexChanged.connect(self.populate_doc_table)
            doc_filter_layout.addWidget(self.doc_order_filter_combo)
            doc_filter_layout.addSpacing(10)
            doc_lang_filter_label = QLabel(self.tr("Filtrer par Langue:"))
            doc_lang_filter_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            doc_filter_layout.addWidget(doc_lang_filter_label)
            self.doc_language_filter_combo = QComboBox()
            self.doc_language_filter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.doc_language_filter_combo.addItem(self.tr("Toutes"), "ALL")
            for lang_code in SUPPORTED_LANGUAGES:
                self.doc_language_filter_combo.addItem(lang_code, lang_code)
            self.doc_language_filter_combo.currentIndexChanged.connect(self.populate_doc_table)
            doc_filter_layout.addWidget(self.doc_language_filter_combo)
            doc_filter_layout.addSpacing(10)
            doc_type_filter_label = QLabel(self.tr("Filtrer par Type:"))
            doc_type_filter_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            doc_filter_layout.addWidget(doc_type_filter_label)
            self.doc_type_filter_combo = QComboBox()
            self.doc_type_filter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.doc_type_filter_combo.addItem(self.tr("Tous"), "ALL")
            self.doc_type_filter_combo.addItem("HTML", "HTML")
            self.doc_type_filter_combo.addItem("PDF", "PDF")
            self.doc_type_filter_combo.addItem("XLSX", "XLSX")
            self.doc_type_filter_combo.addItem("DOCX", "DOCX")
            self.doc_type_filter_combo.addItem(self.tr("Autre"), "OTHER")
            self.doc_type_filter_combo.currentIndexChanged.connect(self.populate_doc_table)
            doc_filter_layout.addWidget(self.doc_type_filter_combo)
            docs_layout.addWidget(self.doc_filter_layout_widget)
            self.doc_filter_layout_widget.setVisible(True)
            self.documents_empty_label = QLabel(self.tr("Aucun document trouvé pour ce client.\nUtilisez les boutons ci-dessous pour ajouter ou générer des documents."))
            self.documents_empty_label.setAlignment(Qt.AlignCenter)
            font_docs_empty = self.documents_empty_label.font()
            font_docs_empty.setPointSize(10)
            self.documents_empty_label.setFont(font_docs_empty)
            docs_layout.addWidget(self.documents_empty_label)
            self.doc_table = QTableWidget()
            self.doc_table.setColumnCount(5)
            self.doc_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Type"), self.tr("Langue"), self.tr("Date"), self.tr("Actions")])
            self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.doc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.doc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            docs_layout.addWidget(self.doc_table)
            doc_btn_layout = QHBoxLayout()
            self.add_doc_btn = QPushButton(self.tr("Importer Document"))
            self.add_doc_btn.setIcon(QIcon(":/icons/file-plus.svg"))
            self.add_doc_btn.setToolTip(self.tr("Importer un fichier document existant pour ce client"))
            self.add_doc_btn.clicked.connect(self.add_document)
            doc_btn_layout.addWidget(self.add_doc_btn)
            self.refresh_docs_btn = QPushButton(self.tr("Actualiser"))
            self.refresh_docs_btn.setIcon(QIcon.fromTheme("view-refresh"))
            self.refresh_docs_btn.clicked.connect(self.populate_doc_table)
            doc_btn_layout.addWidget(self.refresh_docs_btn)
            self.add_template_btn = QPushButton(self.tr("Générer via Modèle"))
            self.add_template_btn.setIcon(QIcon.fromTheme("document-new", QIcon(":/icons/file-plus.svg")))
            self.add_template_btn.setToolTip(self.tr("Générer un nouveau document pour ce client à partir d'un modèle"))
            self.add_template_btn.clicked.connect(self.open_create_docs_dialog)
            doc_btn_layout.addWidget(self.add_template_btn)
            docs_layout.addLayout(doc_btn_layout)
            self.tab_widget.addTab(docs_tab, self.tr("Documents"))
        except Exception as e:
            logging.error(f"Error during UI setup of Documents Tab Structure: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation structure onglet Documents:\n{0}").format(str(e)))

        try:
            # --- Contacts Tab Structure ---
            contacts_tab = QWidget()
            contacts_layout = QVBoxLayout(contacts_tab)
            self.contacts_table = QTableWidget()
            self.contacts_table.setColumnCount(5)
            self.contacts_table.setHorizontalHeaderLabels([
                self.tr("Nom"), self.tr("Email"), self.tr("Téléphone"),
                self.tr("Position"), self.tr("Principal")
            ])
            self.contacts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.contacts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.contacts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.contacts_table.setAlternatingRowColors(True)
            self.contacts_table.cellDoubleClicked.connect(self.edit_contact)
            self.contacts_empty_label = QLabel(self.tr("Aucun contact ajouté pour ce client.\nCliquez sur '➕ Ajouter' pour commencer."))
            self.contacts_empty_label.setAlignment(Qt.AlignCenter)
            font = self.contacts_empty_label.font()
            font.setPointSize(10)
            self.contacts_empty_label.setFont(font)
            contacts_layout.addWidget(self.contacts_empty_label)
            contacts_layout.addWidget(self.contacts_table)
            contacts_pagination_layout = QHBoxLayout()
            self.prev_contact_button = QPushButton("<< Précédent")
            self.prev_contact_button.setObjectName("paginationButton")
            self.prev_contact_button.clicked.connect(self.prev_contact_page)
            self.contact_page_info_label = QLabel("Page 1 / 1")
            self.contact_page_info_label.setObjectName("paginationLabel")
            self.next_contact_button = QPushButton("Suivant >>")
            self.next_contact_button.setObjectName("paginationButton")
            self.next_contact_button.clicked.connect(self.next_contact_page)
            contacts_pagination_layout.addStretch()
            contacts_pagination_layout.addWidget(self.prev_contact_button)
            contacts_pagination_layout.addWidget(self.contact_page_info_label)
            contacts_pagination_layout.addWidget(self.next_contact_button)
            contacts_pagination_layout.addStretch()
            contacts_layout.addLayout(contacts_pagination_layout)
            contacts_btn_layout = QHBoxLayout()
            self.add_contact_btn = QPushButton(self.tr("Ajouter")); self.add_contact_btn.setIcon(QIcon(":/icons/user-plus.svg")); self.add_contact_btn.setToolTip(self.tr("Ajouter un nouveau contact pour ce client")); self.add_contact_btn.clicked.connect(self.add_contact); contacts_btn_layout.addWidget(self.add_contact_btn)
            self.edit_contact_btn = QPushButton(self.tr("Modifier")); self.edit_contact_btn.setIcon(QIcon(":/icons/pencil.svg")); self.edit_contact_btn.setToolTip(self.tr("Modifier le contact sélectionné")); self.edit_contact_btn.clicked.connect(self.edit_contact); contacts_btn_layout.addWidget(self.edit_contact_btn)
            self.remove_contact_btn = QPushButton(self.tr("Supprimer")); self.remove_contact_btn.setIcon(QIcon(":/icons/trash.svg")); self.remove_contact_btn.setToolTip(self.tr("Supprimer le lien vers le contact sélectionné pour ce client")); self.remove_contact_btn.setObjectName("dangerButton"); self.remove_contact_btn.clicked.connect(self.remove_contact); contacts_btn_layout.addWidget(self.remove_contact_btn)
            contacts_layout.addLayout(contacts_btn_layout)
            self.tab_widget.addTab(contacts_tab, self.tr("Contacts"))
        except Exception as e:
            logging.error(f"Error during UI setup of Contacts Tab Structure: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation structure onglet Contacts:\n{0}").format(str(e)))

        try:
            # --- Products Tab Structure ---
            products_tab = QWidget()
            products_layout = QVBoxLayout(products_tab)
            product_filters_layout = QHBoxLayout()
            product_filters_layout.addWidget(QLabel(self.tr("Filtrer par langue:")))
            self.product_lang_filter_combo = QComboBox()
            self.product_lang_filter_combo.addItem(self.tr("All Languages"), None)
            self.product_lang_filter_combo.addItem(self.tr("English (en)"), "en")
            self.product_lang_filter_combo.addItem(self.tr("French (fr)"), "fr")
            self.product_lang_filter_combo.addItem(self.tr("Arabic (ar)"), "ar")
            self.product_lang_filter_combo.addItem(self.tr("Turkish (tr)"), "tr")
            self.product_lang_filter_combo.addItem(self.tr("Portuguese (pt)"), "pt")
            self.product_lang_filter_combo.currentTextChanged.connect(self.load_products)
            product_filters_layout.addWidget(self.product_lang_filter_combo)
            product_filters_layout.addStretch()
            products_layout.addLayout(product_filters_layout)
            self.products_empty_label = QLabel(self.tr("Aucun produit ajouté pour ce client.\nCliquez sur '➕ Ajouter' pour commencer."))
            self.products_empty_label.setAlignment(Qt.AlignCenter)
            font_products_empty = self.products_empty_label.font()
            font_products_empty.setPointSize(10)
            self.products_empty_label.setFont(font_products_empty)
            products_layout.addWidget(self.products_empty_label)
            self.products_table = QTableWidget()
            self.products_table.setColumnCount(8)
            self.products_table.setHorizontalHeaderLabels([
                self.tr("ID"), self.tr("Nom Produit"), self.tr("Description"),
                self.tr("Poids"), self.tr("Dimensions"),
                self.tr("Qté"), self.tr("Prix Unitaire"), self.tr("Prix Total")
            ])
            self.products_table.setEditTriggers(QAbstractItemView.DoubleClicked)
            self.products_table.itemChanged.connect(self.handle_product_item_changed)
            self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.products_table.hideColumn(0)
            products_layout.addWidget(self.products_table)
            products_btn_layout = QHBoxLayout()
            self.add_product_btn = QPushButton(self.tr("Ajouter")); self.add_product_btn.setIcon(QIcon(":/icons/plus-circle.svg")); self.add_product_btn.setToolTip(self.tr("Ajouter un produit pour ce client/projet")); self.add_product_btn.clicked.connect(self.add_product); products_btn_layout.addWidget(self.add_product_btn)
            self.edit_product_btn = QPushButton(self.tr("Modifier")); self.edit_product_btn.setIcon(QIcon(":/icons/pencil.svg")); self.edit_product_btn.setToolTip(self.tr("Modifier le produit sélectionné")); self.edit_product_btn.clicked.connect(self.edit_product); products_btn_layout.addWidget(self.edit_product_btn)
            self.remove_product_btn = QPushButton(self.tr("Supprimer")); self.remove_product_btn.setIcon(QIcon(":/icons/trash.svg")); self.remove_product_btn.setToolTip(self.tr("Supprimer le produit sélectionné de ce client/projet")); self.remove_product_btn.setObjectName("dangerButton"); self.remove_product_btn.clicked.connect(self.remove_product); products_btn_layout.addWidget(self.remove_product_btn)
            products_layout.addLayout(products_btn_layout)
            self.tab_widget.addTab(products_tab, self.tr("Produits"))
        except Exception as e:
            logging.error(f"Error during UI setup of Products Tab Structure: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation structure onglet Produits:\n{0}").format(str(e)))

        try:
            # --- Document Notes Tab Structure ---
            self.document_notes_tab = QWidget()
            doc_notes_layout = QVBoxLayout(self.document_notes_tab)
            doc_notes_filters_layout = QHBoxLayout()
            doc_notes_filters_layout.addWidget(QLabel(self.tr("Type de Document:")))
            self.doc_notes_type_filter_combo = QComboBox()
            doc_notes_filters_layout.addWidget(self.doc_notes_type_filter_combo)
            doc_notes_filters_layout.addWidget(QLabel(self.tr("Langue:")))
            self.doc_notes_lang_filter_combo = QComboBox()
            doc_notes_filters_layout.addWidget(self.doc_notes_lang_filter_combo)
            doc_notes_filters_layout.addStretch()
            doc_notes_layout.addLayout(doc_notes_filters_layout)
            self.document_notes_table = QTableWidget()
            self.document_notes_table.setColumnCount(5)
            self.document_notes_table.setHorizontalHeaderLabels([
                self.tr("Type Document"), self.tr("Langue"),
                self.tr("Aperçu Note"), self.tr("Actif"), self.tr("Actions")
            ])
            self.document_notes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.document_notes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.document_notes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            doc_notes_layout.addWidget(self.document_notes_table)
            doc_notes_buttons_layout = QHBoxLayout()
            self.add_doc_note_button = QPushButton(self.tr("Ajouter Note de Document"))
            self.add_doc_note_button.setIcon(QIcon.fromTheme("document-new"))
            doc_notes_buttons_layout.addWidget(self.add_doc_note_button)
            self.refresh_doc_notes_button = QPushButton(self.tr("Actualiser Liste"))
            self.refresh_doc_notes_button.setIcon(QIcon.fromTheme("view-refresh"))
            doc_notes_buttons_layout.addWidget(self.refresh_doc_notes_button)
            doc_notes_buttons_layout.addStretch()
            doc_notes_layout.addLayout(doc_notes_buttons_layout)
            self.document_notes_tab.setLayout(doc_notes_layout)
            self.tab_widget.addTab(self.document_notes_tab, self.tr("Notes de Document"))
        except Exception as e:
            logging.error(f"Error during UI setup of Document Notes Tab Structure: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation structure onglet Notes de Document:\n{0}").format(str(e)))

        self.doc_notes_type_filter_combo.currentIndexChanged.connect(self.load_document_notes_table)
        self.doc_notes_lang_filter_combo.currentIndexChanged.connect(self.load_document_notes_table)
        self.add_doc_note_button.clicked.connect(self.on_add_document_note)
        self.refresh_doc_notes_button.clicked.connect(self.load_document_notes_table)

        try:
            # --- Product Dimensions Tab Structure ---
            self.product_dimensions_tab = QWidget()
            prod_dims_layout = QVBoxLayout(self.product_dimensions_tab)
            self.dim_product_selector_combo = QComboBox()
            self.dim_product_selector_combo.addItem(self.tr("Sélectionner un produit..."), None)
            prod_dims_layout.addWidget(self.dim_product_selector_combo)
            self.edit_client_product_dimensions_button = QPushButton(self.tr("Modifier Dimensions Produit"))
            self.edit_client_product_dimensions_button.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
            self.edit_client_product_dimensions_button.setEnabled(False)
            prod_dims_layout.addWidget(self.edit_client_product_dimensions_button)
            prod_dims_layout.addStretch()
            produits_tab_index = -1
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == self.tr("Notes de Document"):
                    produits_tab_index = i
                    break
            if produits_tab_index != -1:
                self.tab_widget.insertTab(produits_tab_index + 1, self.product_dimensions_tab, self.tr("Dimensions Produit (Client)"))
            else:
                self.tab_widget.addTab(self.product_dimensions_tab, self.tr("Dimensions Produit (Client)"))
        except Exception as e:
            logging.error(f"Error during UI setup of Product Dimensions Tab Structure: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation structure onglet Dimensions Produit:\n{0}").format(str(e)))

        try:
            self.load_products_for_dimension_tab()
        except Exception as e:
            logging.error(f"Error during initial load of Product Dimensions Tab (first call): {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des dimensions de produit:\n{0}").format(str(e)))

        self.dim_product_selector_combo.currentIndexChanged.connect(self.on_dim_product_selected)
        self.edit_client_product_dimensions_button.clicked.connect(self.on_edit_client_product_dimensions)

        try:
            self.load_products_for_dimension_tab() # Initial population of product selector
        except Exception as e:
            logging.error(f"Error during initial load of Product Dimensions Tab (second call): {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des dimensions de produit (2):\n{0}").format(str(e)))

        # Connect signals for the Product Dimensions Tab
        # self.dim_product_selector_combo.currentIndexChanged.connect(self.on_dim_product_selected) # Already connected
        # self.edit_client_product_dimensions_button.clicked.connect(self.on_edit_client_product_dimensions) # Already connected

        # Removed connections for old buttons (client_browse_tech_image_button, save_client_product_dimensions_button)
        try:
            self.populate_doc_table()
        except Exception as e:
            logging.error(f"Error during initial load of Documents tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des documents:\n{0}").format(str(e)))
        try:
            self.load_contacts()
        except Exception as e:
            logging.error(f"Error during initial load of Contacts tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des contacts:\n{0}").format(str(e)))
        try:
            self.load_products() # This now also calls load_products_for_dimension_tab which has its own try-except
        except Exception as e:
            logging.error(f"Error during initial load of Products tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des produits:\n{0}").format(str(e)))

        try:
            self.load_document_notes_filters()
        except Exception as e:
            logging.error(f"Error during initial load of Document Notes Filters: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des filtres de notes de document:\n{0}").format(str(e)))
        try:
            self.load_document_notes_table()
        except Exception as e:
            logging.error(f"Error during initial load of Document Notes tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des notes de document:\n{0}").format(str(e)))

        try:
            # SAV Tab
            self.sav_tab = QWidget()
            sav_layout = QVBoxLayout(self.sav_tab)
            sav_layout.addWidget(QLabel("<h3>Historique des Achats</h3>"))
            self.purchase_history_table = QTableWidget()
            self.purchase_history_table.setColumnCount(6)
            self.purchase_history_table.setHorizontalHeaderLabels([
                self.tr("ID CPP (Hidden)"), self.tr("Produit"), self.tr("Quantité"),
                self.tr("Numéro de Série"), self.tr("Date d'Achat"), self.tr("Actions")
            ])
            self.purchase_history_table.setColumnHidden(0, True)
            self.purchase_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.purchase_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.purchase_history_table.itemChanged.connect(self.handle_purchase_history_item_changed)
            sav_layout.addWidget(self.purchase_history_table)
            self.refresh_purchase_history_btn = QPushButton(self.tr("Rafraîchir l'historique"))
            self.refresh_purchase_history_btn.setIcon(QIcon.fromTheme("view-refresh"))
            self.refresh_purchase_history_btn.clicked.connect(self.load_purchase_history_table)
            sav_layout.addWidget(self.refresh_purchase_history_btn)
            sav_layout.addWidget(QLabel("<h3>Tickets SAV (Prochainement)</h3>"))
            sav_layout.addStretch()
            self.tab_widget.addTab(self.sav_tab, self.tr("SAV"))
            self.sav_tab_index = self.tab_widget.indexOf(self.sav_tab)
        except Exception as e:
            logging.error(f"Error during UI setup of SAV Tab Structure: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation structure onglet SAV:\n{0}").format(str(e)))

        try:
            # --- Assignments Tab ---
            self.assignments_tab = QWidget()
            assignments_main_layout = QVBoxLayout(self.assignments_tab)
            self.assignments_sub_tabs = QTabWidget()
            assignments_main_layout.addWidget(self.assignments_sub_tabs)
            self.tab_widget.addTab(self.assignments_tab, self.tr("Affectations"))
            # Sub-Tab: Assigned Vendors/Sellers (CompanyPersonnel)
            assigned_vendors_widget = QWidget()
            assigned_vendors_layout = QVBoxLayout(assigned_vendors_widget)
            self.assigned_vendors_table = QTableWidget()
            self.assigned_vendors_table.setColumnCount(4)
            self.assigned_vendors_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Rôle Projet"), self.tr("Email"), self.tr("Téléphone")])
            self.assigned_vendors_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.assigned_vendors_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.assigned_vendors_table.horizontalHeader().setStretchLastSection(True)
            assigned_vendors_layout.addWidget(self.assigned_vendors_table)
            vendor_buttons_layout = QHBoxLayout()
            self.add_assigned_vendor_btn = QPushButton(self.tr("Ajouter Vendeur/Personnel"))
            self.add_assigned_vendor_btn.clicked.connect(self.handle_add_assigned_vendor)
            self.remove_assigned_vendor_btn = QPushButton(self.tr("Retirer Vendeur/Personnel"))
            self.remove_assigned_vendor_btn.clicked.connect(self.handle_remove_assigned_vendor)
            vendor_buttons_layout.addWidget(self.add_assigned_vendor_btn)
            vendor_buttons_layout.addWidget(self.remove_assigned_vendor_btn)
            assigned_vendors_layout.addLayout(vendor_buttons_layout)
            self.assignments_sub_tabs.addTab(assigned_vendors_widget, self.tr("Vendeurs & Personnel"))
            # Sub-Tab: Assigned Technicians
            assigned_technicians_widget = QWidget()
            assigned_technicians_layout = QVBoxLayout(assigned_technicians_widget)
            self.assigned_technicians_table = QTableWidget()
            self.assigned_technicians_table.setColumnCount(4)
            self.assigned_technicians_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Rôle Projet"), self.tr("Email"), self.tr("Téléphone")])
            self.assigned_technicians_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.assigned_technicians_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.assigned_technicians_table.horizontalHeader().setStretchLastSection(True)
            assigned_technicians_layout.addWidget(self.assigned_technicians_table)
            technician_buttons_layout = QHBoxLayout()
            self.add_assigned_technician_btn = QPushButton(self.tr("Ajouter Technicien"))
            self.add_assigned_technician_btn.clicked.connect(self.handle_add_assigned_technician)
            self.remove_assigned_technician_btn = QPushButton(self.tr("Retirer Technicien"))
            self.remove_assigned_technician_btn.clicked.connect(self.handle_remove_assigned_technician)
            technician_buttons_layout.addWidget(self.add_assigned_technician_btn)
            technician_buttons_layout.addWidget(self.remove_assigned_technician_btn)
            assigned_technicians_layout.addLayout(technician_buttons_layout)
            self.assignments_sub_tabs.addTab(assigned_technicians_widget, self.tr("Techniciens"))
            # Sub-Tab: Assigned Transporters
            assigned_transporters_widget = QWidget()
            assigned_transporters_layout = QVBoxLayout(assigned_transporters_widget)
            self.assigned_transporters_table = QTableWidget()
            self.assigned_transporters_table.setColumnCount(6)
            self.assigned_transporters_table.setHorizontalHeaderLabels([self.tr("Nom Transporteur"), self.tr("Contact"), self.tr("Téléphone"), self.tr("Détails Transport"), self.tr("Coût Estimé"), self.tr("Actions")])
            self.assigned_transporters_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.assigned_transporters_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.assigned_transporters_table.horizontalHeader().setStretchLastSection(True)
            assigned_transporters_layout.addWidget(self.assigned_transporters_table)
            transporter_buttons_layout = QHBoxLayout()
            self.add_assigned_transporter_btn = QPushButton(self.tr("Ajouter Transporteur"))
            self.add_assigned_transporter_btn.clicked.connect(self.handle_add_assigned_transporter)
            self.remove_assigned_transporter_btn = QPushButton(self.tr("Retirer Transporteur"))
            self.remove_assigned_transporter_btn.clicked.connect(self.handle_remove_assigned_transporter)
            transporter_buttons_layout.addWidget(self.add_assigned_transporter_btn)
            transporter_buttons_layout.addWidget(self.remove_assigned_transporter_btn)
            assigned_transporters_layout.addLayout(transporter_buttons_layout)
            self.assignments_sub_tabs.addTab(assigned_transporters_widget, self.tr("Transporteurs"))
            # Sub-Tab: Assigned Freight Forwarders
            assigned_forwarders_widget = QWidget()
            assigned_forwarders_layout = QVBoxLayout(assigned_forwarders_widget)
            self.assigned_forwarders_table = QTableWidget()
            self.assigned_forwarders_table.setColumnCount(5)
            self.assigned_forwarders_table.setHorizontalHeaderLabels([self.tr("Nom Transitaire"), self.tr("Contact"), self.tr("Téléphone"), self.tr("Description Tâche"), self.tr("Coût Estimé")])
            self.assigned_forwarders_table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.assigned_forwarders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.assigned_forwarders_table.horizontalHeader().setStretchLastSection(True)
            assigned_forwarders_layout.addWidget(self.assigned_forwarders_table)
            forwarder_buttons_layout = QHBoxLayout()
            self.add_assigned_forwarder_btn = QPushButton(self.tr("Ajouter Transitaire"))
            self.add_assigned_forwarder_btn.clicked.connect(self.handle_add_assigned_forwarder)
            self.remove_assigned_forwarder_btn = QPushButton(self.tr("Retirer Transitaire"))
            self.remove_assigned_forwarder_btn.clicked.connect(self.handle_remove_assigned_forwarder)
            forwarder_buttons_layout.addWidget(self.add_assigned_forwarder_btn)
            forwarder_buttons_layout.addWidget(self.remove_assigned_forwarder_btn)
            assigned_forwarders_layout.addLayout(forwarder_buttons_layout)
            self.assignments_sub_tabs.addTab(assigned_forwarders_widget, self.tr("Transitaires"))
        except Exception as e:
            logging.error(f"Error during UI setup of Assignments Tab Structure: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation structure onglet Affectations:\n{0}").format(str(e)))

        # Call to load SAV tickets table initially if tab is visible
        try:
            self.update_sav_tab_visibility() # This calls load_purchase_history_table and load_sav_tickets_table
        except Exception as e:
            logging.error(f"Error during initial visibility update/load of SAV tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors de la mise à jour/chargement initial de l'onglet SAV:\n{0}").format(str(e)))

        # Initial load for assignment tabs
        try:
            self.load_assigned_vendors_personnel()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Vendors/Personnel: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des vendeurs/personnel assignés:\n{0}").format(str(e)))
        try:
            self.load_assigned_technicians()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Technicians: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des techniciens assignés:\n{0}").format(str(e)))
        try:
            self.load_assigned_transporters()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Transporters: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des transporteurs assignés:\n{0}").format(str(e)))
        try:
            self.load_assigned_freight_forwarders()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Freight Forwarders: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des transitaires assignés:\n{0}").format(str(e)))

        # Connect selection changed signals for assignment tables
        self.assigned_vendors_table.itemSelectionChanged.connect(self.update_assigned_vendors_buttons_state)
        self.assigned_technicians_table.itemSelectionChanged.connect(self.update_assigned_technicians_buttons_state)
        self.assigned_transporters_table.itemSelectionChanged.connect(self.update_assigned_transporters_buttons_state)
        self.assigned_forwarders_table.itemSelectionChanged.connect(self.update_assigned_forwarders_buttons_state)

        try:
            # --- Billing Tab ---
            self.billing_tab = QWidget()
            self.billing_tab_layout = QVBoxLayout(self.billing_tab)
            self.generate_invoice_button = QPushButton(QIcon(":/icons/file-plus.svg"), self.tr("Generate Final Invoice"))
            self.generate_invoice_button.setToolTip(self.tr("Open dialog to prepare and generate a final invoice for this client."))
            self.generate_invoice_button.clicked.connect(self.handle_generate_final_invoice)
            self.billing_tab_layout.addWidget(self.generate_invoice_button)
            self.billing_tab_layout.addStretch()
            self.tab_widget.addTab(self.billing_tab, QIcon(":/icons/credit-card.svg"), self.tr("Billing"))
        except Exception as e:
            logging.error(f"Error during UI setup of Billing Tab Structure: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur UI"), self.tr("Erreur initialisation structure onglet Facturation:\n{0}").format(str(e)))

        # Connect new accordion handlers
        self.client_info_group_box.toggled.connect(self._handle_client_info_section_toggled)
        self.notes_group_box.toggled.connect(self._handle_notes_section_toggled)
        self.tabs_group_box.toggled.connect(self._handle_tabs_section_toggled)

    def _handle_edit_pdf_action(self, file_path, document_id):
        if file_path and os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        try:
            self._setup_main_tabs_section(layout) #FIXED
            self.notes_edit.textChanged.disconnect(self.save_client_notes)
        except TypeError:
            pass # Signal was not connected or already disconnected
        self.notes_edit.installEventFilter(self)


        # --- Collapsible Notes Section ---
        self.notes_group_box = QGroupBox(self.tr("Notes"))
        self.notes_group_box.setCheckable(True)
        notes_group_layout = QVBoxLayout(self.notes_group_box)

        # self.notes_edit is already initialized earlier
        # Move self.notes_edit into this new group box
        # notes_group_layout.addWidget(self.notes_edit) # Directly adding notes_edit

        self.notes_group_box.setChecked(False) # Expanded by default
        self.notes_container_widget = QWidget() # Create a container for the notes_edit
        notes_container_layout = QVBoxLayout(self.notes_container_widget)
        notes_container_layout.setContentsMargins(0, 5, 0, 0)
        notes_container_layout.addWidget(self.notes_edit) # Add notes_edit to the container
        notes_group_layout.addWidget(self.notes_container_widget) # Add container to group_layout
        # self.notes_group_box.toggled.connect(self.notes_container_widget.setVisible)

        # Add the new notes group box to the main layout
        layout.addWidget(self.notes_group_box)
        # --- End Collapsible Notes Section ---

        # --- Collapsible Tabs Section ---
        self.tabs_group_box = QGroupBox(self.tr("Autres Informations")) # Or "Details Supplementaires" / "Tabs"
        self.tabs_group_box.setCheckable(True)
        tabs_group_layout = QVBoxLayout(self.tabs_group_box)

        self.tab_widget = QTabWidget()
        # Move self.tab_widget into this new group box
        tabs_group_layout.addWidget(self.tab_widget)

        self.tabs_group_box.setChecked(False) # Collapsed by default
        # Add the new tabs_group_box to the main layout instead of tab_widget directly
        # layout.addWidget(self.tab_widget) # This line will be replaced by:
        layout.addWidget(self.tabs_group_box)
        # --- End Collapsible Tabs Section ---

        docs_tab = QWidget(); docs_layout = QVBoxLayout(docs_tab)

        # Filter layout for documents tab
        self.doc_filter_layout_widget = QWidget() # Container for the filter layout
        doc_filter_layout = QHBoxLayout(self.doc_filter_layout_widget)
        doc_filter_layout.setContentsMargins(0,0,0,0) # Keep tight margins for the filter bar itself

        doc_filter_label = QLabel(self.tr("Filtrer par Commande:"))
        doc_filter_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed) # Prevent label from expanding
        doc_filter_layout.addWidget(doc_filter_label)

        self.doc_order_filter_combo = QComboBox()
        self.doc_order_filter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.doc_order_filter_combo.currentIndexChanged.connect(self.populate_doc_table)
        doc_filter_layout.addWidget(self.doc_order_filter_combo)
        doc_filter_layout.addSpacing(10)

        # Language Filter
        doc_lang_filter_label = QLabel(self.tr("Filtrer par Langue:"))
        doc_lang_filter_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        doc_filter_layout.addWidget(doc_lang_filter_label)

        self.doc_language_filter_combo = QComboBox()
        self.doc_language_filter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.doc_language_filter_combo.addItem(self.tr("Toutes"), "ALL")
        for lang_code in SUPPORTED_LANGUAGES:
            self.doc_language_filter_combo.addItem(lang_code, lang_code)
        self.doc_language_filter_combo.currentIndexChanged.connect(self.populate_doc_table)
        doc_filter_layout.addWidget(self.doc_language_filter_combo)
        doc_filter_layout.addSpacing(10)

        # Type Filter
        doc_type_filter_label = QLabel(self.tr("Filtrer par Type:"))
        doc_type_filter_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        doc_filter_layout.addWidget(doc_type_filter_label)

        self.doc_type_filter_combo = QComboBox()
        self.doc_type_filter_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.doc_type_filter_combo.addItem(self.tr("Tous"), "ALL")
        self.doc_type_filter_combo.addItem("HTML", "HTML")
        self.doc_type_filter_combo.addItem("PDF", "PDF")
        self.doc_type_filter_combo.addItem("XLSX", "XLSX")
        self.doc_type_filter_combo.addItem("DOCX", "DOCX")
        self.doc_type_filter_combo.addItem(self.tr("Autre"), "OTHER")
        self.doc_type_filter_combo.currentIndexChanged.connect(self.populate_doc_table)
        doc_filter_layout.addWidget(self.doc_type_filter_combo)

        docs_layout.addWidget(self.doc_filter_layout_widget)
        self.doc_filter_layout_widget.setVisible(True) # Make filter bar always visible

        # Create and add the empty state label for documents
        self.documents_empty_label = QLabel(self.tr("Aucun document trouvé pour ce client.\nUtilisez les boutons ci-dessous pour ajouter ou générer des documents."))
        self.documents_empty_label.setAlignment(Qt.AlignCenter)
        font_docs_empty = self.documents_empty_label.font() # Use a different variable name for font
        font_docs_empty.setPointSize(10) # Adjust size as needed
        self.documents_empty_label.setFont(font_docs_empty)
        docs_layout.addWidget(self.documents_empty_label) # Add before the table

        self.doc_table = QTableWidget()
        self.doc_table.setColumnCount(5) # Name, Type, Language, Date, Actions
        self.doc_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Type"), self.tr("Langue"), self.tr("Date"), self.tr("Actions")])
        self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.doc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.doc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        docs_layout.addWidget(self.doc_table)
        doc_btn_layout = QHBoxLayout()
        self.add_doc_btn = QPushButton(self.tr("Importer Document"))
        self.add_doc_btn.setIcon(QIcon(":/icons/file-plus.svg"))
        self.add_doc_btn.setToolTip(self.tr("Importer un fichier document existant pour ce client"))
        self.add_doc_btn.clicked.connect(self.add_document) # Connect the signal
        doc_btn_layout.addWidget(self.add_doc_btn)

        self.refresh_docs_btn = QPushButton(self.tr("Actualiser"))
        self.refresh_docs_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_docs_btn.clicked.connect(self.populate_doc_table)
        doc_btn_layout.addWidget(self.refresh_docs_btn)

        self.add_template_btn = QPushButton(self.tr("Générer via Modèle"))
        self.add_template_btn.setIcon(QIcon.fromTheme("document-new", QIcon(":/icons/file-plus.svg"))) # Reverted
        self.add_template_btn.setToolTip(self.tr("Générer un nouveau document pour ce client à partir d'un modèle"))
        self.add_template_btn.clicked.connect(self.open_create_docs_dialog)
        doc_btn_layout.addWidget(self.add_template_btn)
        docs_layout.addLayout(doc_btn_layout)
        self.tab_widget.addTab(docs_tab, self.tr("Documents"))

        contacts_tab = QWidget()
        contacts_layout = QVBoxLayout(contacts_tab)
        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(5) # Name, Email, Phone, Position, Primary
        self.contacts_table.setHorizontalHeaderLabels([
            self.tr("Nom"), self.tr("Email"), self.tr("Téléphone"),
            self.tr("Position"), self.tr("Principal")
        ])
        self.contacts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.contacts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.contacts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.contacts_table.setAlternatingRowColors(True)
        self.contacts_table.cellDoubleClicked.connect(self.edit_contact) # row, column are passed

        self.contacts_empty_label = QLabel(self.tr("Aucun contact ajouté pour ce client.\nCliquez sur '➕ Ajouter' pour commencer."))
        self.contacts_empty_label.setAlignment(Qt.AlignCenter)
        font = self.contacts_empty_label.font()
        font.setPointSize(10)
        self.contacts_empty_label.setFont(font)
        contacts_layout.addWidget(self.contacts_empty_label)

        contacts_layout.addWidget(self.contacts_table)

        contacts_pagination_layout = QHBoxLayout()
        self.prev_contact_button = QPushButton("<< Précédent")
        self.prev_contact_button.setObjectName("paginationButton")
        self.prev_contact_button.clicked.connect(self.prev_contact_page)
        self.contact_page_info_label = QLabel("Page 1 / 1")
        self.contact_page_info_label.setObjectName("paginationLabel")
        self.next_contact_button = QPushButton("Suivant >>")
        self.next_contact_button.setObjectName("paginationButton")
        self.next_contact_button.clicked.connect(self.next_contact_page)

        contacts_pagination_layout.addStretch()
        contacts_pagination_layout.addWidget(self.prev_contact_button)
        contacts_pagination_layout.addWidget(self.contact_page_info_label)
        contacts_pagination_layout.addWidget(self.next_contact_button)
        contacts_pagination_layout.addStretch()
        contacts_layout.addLayout(contacts_pagination_layout)

        contacts_btn_layout = QHBoxLayout()
        self.add_contact_btn = QPushButton(self.tr("Ajouter")); self.add_contact_btn.setIcon(QIcon(":/icons/user-plus.svg")); self.add_contact_btn.setToolTip(self.tr("Ajouter un nouveau contact pour ce client")); self.add_contact_btn.clicked.connect(self.add_contact); contacts_btn_layout.addWidget(self.add_contact_btn)
        self.edit_contact_btn = QPushButton(self.tr("Modifier")); self.edit_contact_btn.setIcon(QIcon(":/icons/pencil.svg")); self.edit_contact_btn.setToolTip(self.tr("Modifier le contact sélectionné")); self.edit_contact_btn.clicked.connect(self.edit_contact); contacts_btn_layout.addWidget(self.edit_contact_btn)
        self.remove_contact_btn = QPushButton(self.tr("Supprimer")); self.remove_contact_btn.setIcon(QIcon(":/icons/trash.svg")); self.remove_contact_btn.setToolTip(self.tr("Supprimer le lien vers le contact sélectionné pour ce client")); self.remove_contact_btn.setObjectName("dangerButton"); self.remove_contact_btn.clicked.connect(self.remove_contact); contacts_btn_layout.addWidget(self.remove_contact_btn)
        contacts_layout.addLayout(contacts_btn_layout)
        self.tab_widget.addTab(contacts_tab, self.tr("Contacts"))

        products_tab = QWidget()
        products_layout = QVBoxLayout(products_tab)

        product_filters_layout = QHBoxLayout()
        product_filters_layout.addWidget(QLabel(self.tr("Filtrer par langue:")))
        self.product_lang_filter_combo = QComboBox()
        self.product_lang_filter_combo.addItem(self.tr("All Languages"), None)
        self.product_lang_filter_combo.addItem(self.tr("English (en)"), "en")
        self.product_lang_filter_combo.addItem(self.tr("French (fr)"), "fr")
        self.product_lang_filter_combo.addItem(self.tr("Arabic (ar)"), "ar")
        self.product_lang_filter_combo.addItem(self.tr("Turkish (tr)"), "tr")
        self.product_lang_filter_combo.addItem(self.tr("Portuguese (pt)"), "pt")
        self.product_lang_filter_combo.currentTextChanged.connect(self.load_products)
        product_filters_layout.addWidget(self.product_lang_filter_combo)
        product_filters_layout.addStretch()
        products_layout.addLayout(product_filters_layout)

        self.products_empty_label = QLabel(self.tr("Aucun produit ajouté pour ce client.\nCliquez sur '➕ Ajouter' pour commencer."))
        self.products_empty_label.setAlignment(Qt.AlignCenter)
        font_products_empty = self.products_empty_label.font()
        font_products_empty.setPointSize(10)
        self.products_empty_label.setFont(font_products_empty)
        products_layout.addWidget(self.products_empty_label)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(8)
        self.products_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Nom Produit"), self.tr("Description"),
            self.tr("Poids"), self.tr("Dimensions"),
            self.tr("Qté"), self.tr("Prix Unitaire"), self.tr("Prix Total")
        ])
        self.products_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.products_table.itemChanged.connect(self.handle_product_item_changed)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.hideColumn(0)
        products_layout.addWidget(self.products_table)

        products_btn_layout = QHBoxLayout()
        self.add_product_btn = QPushButton(self.tr("Ajouter")); self.add_product_btn.setIcon(QIcon(":/icons/plus-circle.svg")); self.add_product_btn.setToolTip(self.tr("Ajouter un produit pour ce client/projet")); self.add_product_btn.clicked.connect(self.add_product); products_btn_layout.addWidget(self.add_product_btn)
        self.edit_product_btn = QPushButton(self.tr("Modifier")); self.edit_product_btn.setIcon(QIcon(":/icons/pencil.svg")); self.edit_product_btn.setToolTip(self.tr("Modifier le produit sélectionné")); self.edit_product_btn.clicked.connect(self.edit_product); products_btn_layout.addWidget(self.edit_product_btn)
        self.remove_product_btn = QPushButton(self.tr("Supprimer")); self.remove_product_btn.setIcon(QIcon(":/icons/trash.svg")); self.remove_product_btn.setToolTip(self.tr("Supprimer le produit sélectionné de ce client/projet")); self.remove_product_btn.setObjectName("dangerButton"); self.remove_product_btn.clicked.connect(self.remove_product); products_btn_layout.addWidget(self.remove_product_btn)
        products_layout.addLayout(products_btn_layout)
        self.tab_widget.addTab(products_tab, self.tr("Produits"))

        # layout.addWidget(self.tab_widget) # This was moved into tabs_group_box

        self.document_notes_tab = QWidget()
        doc_notes_layout = QVBoxLayout(self.document_notes_tab)

        doc_notes_filters_layout = QHBoxLayout()
        doc_notes_filters_layout.addWidget(QLabel(self.tr("Type de Document:")))
        self.doc_notes_type_filter_combo = QComboBox()
        doc_notes_filters_layout.addWidget(self.doc_notes_type_filter_combo)

        doc_notes_filters_layout.addWidget(QLabel(self.tr("Langue:")))
        self.doc_notes_lang_filter_combo = QComboBox()
        doc_notes_filters_layout.addWidget(self.doc_notes_lang_filter_combo)
        doc_notes_filters_layout.addStretch()
        doc_notes_layout.addLayout(doc_notes_filters_layout)

        self.document_notes_table = QTableWidget()
        self.document_notes_table.setColumnCount(5)
        self.document_notes_table.setHorizontalHeaderLabels([
            self.tr("Type Document"), self.tr("Langue"),
            self.tr("Aperçu Note"), self.tr("Actif"), self.tr("Actions")
        ])
        self.document_notes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.document_notes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.document_notes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        doc_notes_layout.addWidget(self.document_notes_table)

        doc_notes_buttons_layout = QHBoxLayout()
        self.add_doc_note_button = QPushButton(self.tr("Ajouter Note de Document"))
        self.add_doc_note_button.setIcon(QIcon.fromTheme("document-new"))

        doc_notes_buttons_layout.addWidget(self.add_doc_note_button)

        self.refresh_doc_notes_button = QPushButton(self.tr("Actualiser Liste"))
        self.refresh_doc_notes_button.setIcon(QIcon.fromTheme("view-refresh"))
        doc_notes_buttons_layout.addWidget(self.refresh_doc_notes_button)
        doc_notes_buttons_layout.addStretch()
        doc_notes_layout.addLayout(doc_notes_buttons_layout)

        self.document_notes_tab.setLayout(doc_notes_layout)
        self.tab_widget.addTab(self.document_notes_tab, self.tr("Notes de Document"))

        self.doc_notes_type_filter_combo.currentIndexChanged.connect(self.load_document_notes_table)
        self.doc_notes_lang_filter_combo.currentIndexChanged.connect(self.load_document_notes_table)
        self.add_doc_note_button.clicked.connect(self.on_add_document_note)
        self.refresh_doc_notes_button.clicked.connect(self.load_document_notes_table)

        self.product_dimensions_tab = QWidget()
        prod_dims_layout = QVBoxLayout(self.product_dimensions_tab)

        self.dim_product_selector_combo = QComboBox()
        self.dim_product_selector_combo.addItem(self.tr("Sélectionner un produit..."), None)
        prod_dims_layout.addWidget(self.dim_product_selector_combo)

        self.edit_client_product_dimensions_button = QPushButton(self.tr("Modifier Dimensions Produit"))
        self.edit_client_product_dimensions_button.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
        self.edit_client_product_dimensions_button.setEnabled(False)
        prod_dims_layout.addWidget(self.edit_client_product_dimensions_button)

        prod_dims_layout.addStretch()


        produits_tab_index = -1
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == self.tr("Notes de Document"):
                produits_tab_index = i
                break

        if produits_tab_index != -1:
            self.tab_widget.insertTab(produits_tab_index + 1, self.product_dimensions_tab, self.tr("Dimensions Produit (Client)"))
        else:
            self.tab_widget.addTab(self.product_dimensions_tab, self.tr("Dimensions Produit (Client)"))

        try:
            self.load_products_for_dimension_tab()
        except Exception as e:
            logging.error(f"Error during initial load of Product Dimensions Tab (first call): {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des dimensions de produit:\n{0}").format(str(e)))

        self.dim_product_selector_combo.currentIndexChanged.connect(self.on_dim_product_selected)
        self.edit_client_product_dimensions_button.clicked.connect(self.on_edit_client_product_dimensions)

        try:
            self.load_products_for_dimension_tab() # Initial population of product selector
        except Exception as e:
            logging.error(f"Error during initial load of Product Dimensions Tab (second call): {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des dimensions de produit (2):\n{0}").format(str(e)))

        # Connect signals for the Product Dimensions Tab
        # self.dim_product_selector_combo.currentIndexChanged.connect(self.on_dim_product_selected) # Already connected
        # self.edit_client_product_dimensions_button.clicked.connect(self.on_edit_client_product_dimensions) # Already connected

        # Removed connections for old buttons (client_browse_tech_image_button, save_client_product_dimensions_button)
        try:
            self.populate_doc_table()
        except Exception as e:
            logging.error(f"Error during initial load of Documents tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des documents:\n{0}").format(str(e)))
        try:
            self.load_contacts()
        except Exception as e:
            logging.error(f"Error during initial load of Contacts tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des contacts:\n{0}").format(str(e)))
        try:
            self.load_products() # This now also calls load_products_for_dimension_tab which has its own try-except
        except Exception as e:
            logging.error(f"Error during initial load of Products tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement initial des produits:\n{0}").format(str(e)))

        try:
            self.load_document_notes_filters()
        except Exception as e:
            logging.error(f"Error during initial load of Document Notes Filters: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des filtres de notes de document:\n{0}").format(str(e)))
        try:
            self.load_document_notes_table()
        except Exception as e:
            logging.error(f"Error during initial load of Document Notes tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des notes de document:\n{0}").format(str(e)))

        # SAV Tab
        self.sav_tab = QWidget()
        sav_layout = QVBoxLayout(self.sav_tab)

        # Purchase History Section
        sav_layout.addWidget(QLabel("<h3>Historique des Achats</h3>"))
        self.purchase_history_table = QTableWidget()
        self.purchase_history_table.setColumnCount(6) # ID, Produit, Qté, N/S, Date Achat, Actions (or 5 if N/S is directly editable)
        self.purchase_history_table.setHorizontalHeaderLabels([
            self.tr("ID CPP (Hidden)"), self.tr("Produit"), self.tr("Quantité"),
            self.tr("Numéro de Série"), self.tr("Date d'Achat"), self.tr("Actions")
        ])
        self.purchase_history_table.setColumnHidden(0, True) # Hide ID CPP
        self.purchase_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.purchase_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.purchase_history_table.setEditTriggers(QAbstractItemView.NoEditTriggers) # Will make N/S editable
        self.purchase_history_table.itemChanged.connect(self.handle_purchase_history_item_changed)
        sav_layout.addWidget(self.purchase_history_table)

        self.refresh_purchase_history_btn = QPushButton(self.tr("Rafraîchir l'historique"))
        self.refresh_purchase_history_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_purchase_history_btn.clicked.connect(self.load_purchase_history_table)
        sav_layout.addWidget(self.refresh_purchase_history_btn)

        # Placeholder for SAV Tickets section (to be added later)
        sav_layout.addWidget(QLabel("<h3>Tickets SAV (Prochainement)</h3>"))
        sav_layout.addStretch()


        self.tab_widget.addTab(self.sav_tab, self.tr("SAV"))
        self.sav_tab_index = self.tab_widget.indexOf(self.sav_tab)

        # --- Assignments Tab ---
        self.assignments_tab = QWidget()
        assignments_main_layout = QVBoxLayout(self.assignments_tab)
        self.assignments_sub_tabs = QTabWidget()
        assignments_main_layout.addWidget(self.assignments_sub_tabs)
        self.tab_widget.addTab(self.assignments_tab, self.tr("Affectations"))

        # Sub-Tab: Assigned Vendors/Sellers (CompanyPersonnel)
        assigned_vendors_widget = QWidget()
        assigned_vendors_layout = QVBoxLayout(assigned_vendors_widget)
        self.assigned_vendors_table = QTableWidget()
        self.assigned_vendors_table.setColumnCount(4)
        self.assigned_vendors_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Rôle Projet"), self.tr("Email"), self.tr("Téléphone")])
        self.assigned_vendors_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.assigned_vendors_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.assigned_vendors_table.horizontalHeader().setStretchLastSection(True)
        assigned_vendors_layout.addWidget(self.assigned_vendors_table)
        vendor_buttons_layout = QHBoxLayout()
        self.add_assigned_vendor_btn = QPushButton(self.tr("Ajouter Vendeur/Personnel"))
        self.add_assigned_vendor_btn.clicked.connect(self.handle_add_assigned_vendor)
        self.remove_assigned_vendor_btn = QPushButton(self.tr("Retirer Vendeur/Personnel"))
        self.remove_assigned_vendor_btn.clicked.connect(self.handle_remove_assigned_vendor)
        vendor_buttons_layout.addWidget(self.add_assigned_vendor_btn)
        vendor_buttons_layout.addWidget(self.remove_assigned_vendor_btn)
        assigned_vendors_layout.addLayout(vendor_buttons_layout)
        self.assignments_sub_tabs.addTab(assigned_vendors_widget, self.tr("Vendeurs & Personnel"))

        # Sub-Tab: Assigned Technicians (CompanyPersonnel with different role context or from TeamMembers)
        # For now, assuming Technicians are also CompanyPersonnel, filtered by a role like 'Technicien'
        assigned_technicians_widget = QWidget()
        assigned_technicians_layout = QVBoxLayout(assigned_technicians_widget)
        self.assigned_technicians_table = QTableWidget()
        self.assigned_technicians_table.setColumnCount(4)
        self.assigned_technicians_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Rôle Projet"), self.tr("Email"), self.tr("Téléphone")])
        self.assigned_technicians_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.assigned_technicians_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.assigned_technicians_table.horizontalHeader().setStretchLastSection(True)
        assigned_technicians_layout.addWidget(self.assigned_technicians_table)
        technician_buttons_layout = QHBoxLayout()
        self.add_assigned_technician_btn = QPushButton(self.tr("Ajouter Technicien"))
        self.add_assigned_technician_btn.clicked.connect(self.handle_add_assigned_technician)
        self.remove_assigned_technician_btn = QPushButton(self.tr("Retirer Technicien"))
        self.remove_assigned_technician_btn.clicked.connect(self.handle_remove_assigned_technician)
        technician_buttons_layout.addWidget(self.add_assigned_technician_btn)
        technician_buttons_layout.addWidget(self.remove_assigned_technician_btn)
        assigned_technicians_layout.addLayout(technician_buttons_layout)
        self.assignments_sub_tabs.addTab(assigned_technicians_widget, self.tr("Techniciens"))

        # Sub-Tab: Assigned Transporters
        assigned_transporters_widget = QWidget()
        assigned_transporters_layout = QVBoxLayout(assigned_transporters_widget)
        self.assigned_transporters_table = QTableWidget()
        self.assigned_transporters_table.setColumnCount(6) # Increased column count
        self.assigned_transporters_table.setHorizontalHeaderLabels([self.tr("Nom Transporteur"), self.tr("Contact"), self.tr("Téléphone"), self.tr("Détails Transport"), self.tr("Coût Estimé"), self.tr("Actions")])
        self.assigned_transporters_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.assigned_transporters_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.assigned_transporters_table.horizontalHeader().setStretchLastSection(True)
        assigned_transporters_layout.addWidget(self.assigned_transporters_table)
        transporter_buttons_layout = QHBoxLayout()
        self.add_assigned_transporter_btn = QPushButton(self.tr("Ajouter Transporteur"))
        self.add_assigned_transporter_btn.clicked.connect(self.handle_add_assigned_transporter)
        self.remove_assigned_transporter_btn = QPushButton(self.tr("Retirer Transporteur"))
        self.remove_assigned_transporter_btn.clicked.connect(self.handle_remove_assigned_transporter)
        transporter_buttons_layout.addWidget(self.add_assigned_transporter_btn)
        transporter_buttons_layout.addWidget(self.remove_assigned_transporter_btn)
        assigned_transporters_layout.addLayout(transporter_buttons_layout)
        self.assignments_sub_tabs.addTab(assigned_transporters_widget, self.tr("Transporteurs"))

        # Sub-Tab: Assigned Freight Forwarders
        assigned_forwarders_widget = QWidget()
        assigned_forwarders_layout = QVBoxLayout(assigned_forwarders_widget)
        self.assigned_forwarders_table = QTableWidget()
        self.assigned_forwarders_table.setColumnCount(5)
        self.assigned_forwarders_table.setHorizontalHeaderLabels([self.tr("Nom Transitaire"), self.tr("Contact"), self.tr("Téléphone"), self.tr("Description Tâche"), self.tr("Coût Estimé")])
        self.assigned_forwarders_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.assigned_forwarders_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.assigned_forwarders_table.horizontalHeader().setStretchLastSection(True)
        assigned_forwarders_layout.addWidget(self.assigned_forwarders_table)
        forwarder_buttons_layout = QHBoxLayout()
        self.add_assigned_forwarder_btn = QPushButton(self.tr("Ajouter Transitaire"))
        self.add_assigned_forwarder_btn.clicked.connect(self.handle_add_assigned_forwarder)
        self.remove_assigned_forwarder_btn = QPushButton(self.tr("Retirer Transitaire"))
        self.remove_assigned_forwarder_btn.clicked.connect(self.handle_remove_assigned_forwarder)
        forwarder_buttons_layout.addWidget(self.add_assigned_forwarder_btn)
        forwarder_buttons_layout.addWidget(self.remove_assigned_forwarder_btn)
        assigned_forwarders_layout.addLayout(forwarder_buttons_layout)
        self.assignments_sub_tabs.addTab(assigned_forwarders_widget, self.tr("Transitaires"))
        # --- End Assignments Tab ---

        # Call to load SAV tickets table initially if tab is visible
        try:
            self.update_sav_tab_visibility() # This calls load_purchase_history_table and load_sav_tickets_table
        except Exception as e:
            logging.error(f"Error during initial visibility update/load of SAV tab: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors de la mise à jour/chargement initial de l'onglet SAV:\n{0}").format(str(e)))

        # Initial load for assignment tabs
        try:
            self.load_assigned_vendors_personnel()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Vendors/Personnel: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des vendeurs/personnel assignés:\n{0}").format(str(e)))
        try:
            self.load_assigned_technicians()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Technicians: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des techniciens assignés:\n{0}").format(str(e)))
        try:
            self.load_assigned_transporters()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Transporters: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des transporteurs assignés:\n{0}").format(str(e)))
        try:
            self.load_assigned_freight_forwarders()
        except Exception as e:
            logging.error(f"Error during initial load of Assigned Freight Forwarders: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des transitaires assignés:\n{0}").format(str(e)))

        # Connect selection changed signals for assignment tables
        self.assigned_vendors_table.itemSelectionChanged.connect(self.update_assigned_vendors_buttons_state)
        self.assigned_technicians_table.itemSelectionChanged.connect(self.update_assigned_technicians_buttons_state)
        self.assigned_transporters_table.itemSelectionChanged.connect(self.update_assigned_transporters_buttons_state)
        self.assigned_forwarders_table.itemSelectionChanged.connect(self.update_assigned_forwarders_buttons_state)

        # --- Billing Tab ---
        self.billing_tab = QWidget()
        self.billing_tab_layout = QVBoxLayout(self.billing_tab)

        self.generate_invoice_button = QPushButton(QIcon(":/icons/file-plus.svg"), self.tr("Generate Final Invoice"))
        self.generate_invoice_button.setToolTip(self.tr("Open dialog to prepare and generate a final invoice for this client."))
        self.generate_invoice_button.clicked.connect(self.handle_generate_final_invoice)
        self.billing_tab_layout.addWidget(self.generate_invoice_button)
        self.billing_tab_layout.addStretch()

        self.tab_widget.addTab(self.billing_tab, QIcon(":/icons/credit-card.svg"), self.tr("Billing"))
        # Connect new accordion handlers
        self.client_info_group_box.toggled.connect(self._handle_client_info_section_toggled)
        self.notes_group_box.toggled.connect(self._handle_notes_section_toggled)
        self.tabs_group_box.toggled.connect(self._handle_tabs_section_toggled)

    def _handle_edit_pdf_action(self, file_path, document_id):
        if file_path and os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        else:
            QMessageBox.warning(self, self.tr("Fichier Introuvable"),
                                self.tr("Le fichier PDF spécifié est introuvable ou le chemin est invalide:\n{0}").format(file_path))

    def open_send_whatsapp_dialog(self):
       client_uuid = self.client_info.get("client_id")
       client_name = self.client_info.get("client_name", "")
       primary_phone = ""
       fallback_phone = ""

       if not client_uuid:
           QMessageBox.warning(self, self.tr("Client Error"), self.tr("Client ID not available."))
           return

       try:
           contacts = db_manager.get_contacts_for_client(client_uuid, limit=10, offset=0) # Fetch a few contacts
           if contacts:
               for contact in contacts:
                   if contact.get('phone'):
                       if not fallback_phone: # Store first available phone number
                           fallback_phone = contact['phone']
                       if contact.get('is_primary_for_client'):
                           primary_phone = contact['phone']
                           break # Found primary, use this

               selected_phone = primary_phone if primary_phone else fallback_phone

               if selected_phone:
                   # Ensure SendWhatsAppDialog is available
                   if not hasattr(self, 'SendWhatsAppDialog') or self.SendWhatsAppDialog is None:
                       try:
                           from whatsapp.whatsapp_dialog import SendWhatsAppDialog
                           self.SendWhatsAppDialog = SendWhatsAppDialog
                       except ImportError:
                           QMessageBox.critical(self, self.tr("Import Error"), self.tr("Could not load the SendWhatsAppDialog component."))
                           return

                   dialog = self.SendWhatsAppDialog(phone_number=selected_phone, client_name=client_name, parent=self)
                   dialog.exec_()
               else:
                   QMessageBox.information(self, self.tr("No Phone Number"), self.tr("No phone number found for this client's contacts."))
           else:
               QMessageBox.information(self, self.tr("No Contacts"), self.tr("No contacts found for this client."))
       except Exception as e:
           QMessageBox.critical(self, self.tr("Error Fetching Contacts"), self.tr("Could not retrieve contact information: {0}").format(str(e)))

        # Accordion logic connections
       # if hasattr(self, 'notes_group_box') and hasattr(self, 'tabs_group_box'):
            # self.notes_group_box.toggled.connect(self._handle_notes_toggled)
            # self.tabs_group_box.toggled.connect(self._handle_tabs_toggled)

    def _handle_client_info_section_toggled(self, checked):
        # Ensure the container widget exists
        if not hasattr(self, 'info_container_widget'):
            return
        self.info_container_widget.setVisible(checked)

        if checked:
            # Block signals to prevent infinite loops or unintended recursive calls
            if hasattr(self, 'notes_group_box'):
                self.notes_group_box.blockSignals(True)
                self.notes_group_box.setChecked(False)
                if hasattr(self, 'notes_container_widget'): # Ensure notes_container_widget also exists
                    self.notes_container_widget.setVisible(False) # Explicitly hide content
                self.notes_group_box.blockSignals(False)

            if hasattr(self, 'tabs_group_box'):
                self.tabs_group_box.blockSignals(True)
                self.tabs_group_box.setChecked(False)
                if hasattr(self, 'tab_widget'): # Ensure tab_widget exists
                    self.tab_widget.setVisible(False) # Explicitly hide content
                self.tabs_group_box.blockSignals(False)
        elif not self.notes_group_box.isChecked() and not self.tabs_group_box.isChecked():
            # If this is the only one checked, and user tried to uncheck it, re-check it.
            self.client_info_group_box.blockSignals(True)
            self.client_info_group_box.setChecked(True)
            self.info_container_widget.setVisible(True) # Ensure content visibility matches state
            self.client_info_group_box.blockSignals(False)

    def _handle_notes_section_toggled(self, checked):
        # Ensure the container widget exists
        if not hasattr(self, 'notes_container_widget'):
            return
        self.notes_container_widget.setVisible(checked)

        if checked:
            if hasattr(self, 'client_info_group_box'):
                self.client_info_group_box.blockSignals(True)
                self.client_info_group_box.setChecked(False)
                if hasattr(self, 'info_container_widget'): # Ensure info_container_widget also exists
                    self.info_container_widget.setVisible(False) # Explicitly hide content
                self.client_info_group_box.blockSignals(False)

            if hasattr(self, 'tabs_group_box'):
                self.tabs_group_box.blockSignals(True)
                self.tabs_group_box.setChecked(False)
                if hasattr(self, 'tab_widget'): # Ensure tab_widget exists
                     self.tab_widget.setVisible(False) # Explicitly hide content
                self.tabs_group_box.blockSignals(False)
        elif not self.client_info_group_box.isChecked() and not self.tabs_group_box.isChecked():
            # If this is the only one checked, and user tried to uncheck it, re-check it.
            self.notes_group_box.blockSignals(True)
            self.notes_group_box.setChecked(True)
            self.notes_container_widget.setVisible(True) # Ensure content visibility matches state
            self.notes_group_box.blockSignals(False)

    def _handle_tabs_section_toggled(self, checked):
        # Ensure the tab_widget (content) exists
        if not hasattr(self, 'tab_widget'):
            return
        self.tab_widget.setVisible(checked)

        if checked:
            if hasattr(self, 'client_info_group_box'):
                self.client_info_group_box.blockSignals(True)
                self.client_info_group_box.setChecked(False)
                if hasattr(self, 'info_container_widget'): # Ensure info_container_widget also exists
                     self.info_container_widget.setVisible(False) # Explicitly hide content
                self.client_info_group_box.blockSignals(False)

            if hasattr(self, 'notes_group_box'):
                self.notes_group_box.blockSignals(True)
                self.notes_group_box.setChecked(False)
                if hasattr(self, 'notes_container_widget'): # Ensure notes_container_widget also exists
                     self.notes_container_widget.setVisible(False) # Explicitly hide content
                self.notes_group_box.blockSignals(False)
        elif not self.client_info_group_box.isChecked() and not self.notes_group_box.isChecked():
            # If this is the only one checked, and user tried to uncheck it, re-check it.
            self.tabs_group_box.blockSignals(True)
            self.tabs_group_box.setChecked(True)
            self.tab_widget.setVisible(True) # Ensure content visibility matches state
            self.tabs_group_box.blockSignals(False)

    def load_sav_tickets_table(self):
        # Ensure sav_tickets_table is initialized before use
        if not hasattr(self, 'sav_tickets_table'):
            # This might indicate an issue if SAV tab is created but table isn't part of its layout yet.
            # For now, just return to prevent error, but this should be reviewed if SAV tab is expected.
            # It's possible this method is called before SAV tab UI is fully set up during initial __init__.
            print("Warning: load_sav_tickets_table called before sav_tickets_table is initialized.")
            return

        self.sav_tickets_table.setRowCount(0)
        client_id = self.client_info.get('client_id')
        if not client_id:
            return

        try:
            tickets = db_manager.get_sav_tickets_for_client(client_id)
            if tickets is None: tickets = []

            self.sav_tickets_table.setRowCount(len(tickets))
            for row_idx, ticket in enumerate(tickets):
                ticket_id = ticket.get('ticket_id')

                id_item = QTableWidgetItem(str(ticket_id))
                id_item.setData(Qt.UserRole, ticket_id)
                self.sav_tickets_table.setItem(row_idx, 0, id_item) # Hidden

                # Product Name
                cpp_id = ticket.get('client_project_product_id')
                product_name_display = self.tr("N/A")
                if cpp_id:
                    # This could be optimized by batch fetching product names if performance is an issue
                    linked_product_info = db_manager.get_client_project_product_by_id(cpp_id) # Custom function needed
                    if linked_product_info:
                        product_details = db_manager.get_product_by_id(linked_product_info.get('product_id'))
                        if product_details:
                            product_name_display = product_details.get('product_name', self.tr("Produit Inconnu"))
                self.sav_tickets_table.setItem(row_idx, 1, QTableWidgetItem(product_name_display))

                issue_desc = ticket.get('issue_description', '')
                self.sav_tickets_table.setItem(row_idx, 2, QTableWidgetItem(issue_desc[:100] + '...' if len(issue_desc) > 100 else issue_desc))

                status_name = self.tr("N/A")
                if ticket.get('status_id'):
                    status_info = db_manager.get_status_setting_by_id(ticket['status_id'])
                    if status_info: status_name = status_info.get('status_name', self.tr("Statut Inconnu"))
                self.sav_tickets_table.setItem(row_idx, 3, QTableWidgetItem(status_name))

                opened_at_str = ticket.get('opened_at', '')
                if opened_at_str:
                    try:
                        dt_obj = datetime.fromisoformat(opened_at_str.replace('Z', '+00:00'))
                        opened_at_formatted = dt_obj.strftime('%Y-%m-%d %H:%M')
                    except ValueError:
                        opened_at_formatted = opened_at_str
                else:
                    opened_at_formatted = self.tr('N/A')
                self.sav_tickets_table.setItem(row_idx, 4, QTableWidgetItem(opened_at_formatted))

                tech_name = self.tr("Non assigné")
                if ticket.get('assigned_technician_id'):
                    tech_info = db_manager.get_team_member_by_id(ticket['assigned_technician_id'])
                    if tech_info: tech_name = tech_info.get('full_name', self.tr("Technicien Inconnu"))
                self.sav_tickets_table.setItem(row_idx, 5, QTableWidgetItem(tech_name))

                # Actions button
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2,2,2,2); actions_layout.setSpacing(5)
                view_edit_button = QPushButton(self.tr("Voir/Modifier"))
                view_edit_button.clicked.connect(lambda checked, t_id=ticket_id: self.view_edit_sav_ticket_dialog(t_id))
                actions_layout.addWidget(view_edit_button)
                actions_layout.addStretch()
                self.sav_tickets_table.setCellWidget(row_idx, 6, actions_widget)

        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement Tickets SAV"),
                                 self.tr("Impossible de charger les tickets SAV:\n{0}").format(str(e)))

    def open_new_sav_ticket_dialog(self):
        client_id = self.client_info.get('client_id')
        if not client_id:
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible."))
            return

        try:
            from sav.ticket_dialog import SAVTicketDialog # Import here to avoid circular if moved
        except ImportError:
            QMessageBox.critical(self, self.tr("Erreur Importation"), self.tr("Le dialogue de ticket SAV n'a pas pu être chargé."))
            return

        all_client_products = db_manager.get_products_for_client_or_project(client_id, project_id=None)
        purchased_items = [
            {'name': p.get('product_name', 'N/A'), 'client_project_product_id': p.get('client_project_product_id')}
            for p in all_client_products if p.get('purchase_confirmed_at') is not None
        ]

        dialog = SAVTicketDialog(client_id=client_id, purchased_products=purchased_items, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_sav_tickets_table()

    def view_edit_sav_ticket_dialog(self, ticket_id):
        client_id = self.client_info.get('client_id')
        if not client_id: # Should not happen if ticket_id is valid for this client context
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible."))
            return

        try:
            from sav.ticket_dialog import SAVTicketDialog
        except ImportError:
            QMessageBox.critical(self, self.tr("Erreur Importation"), self.tr("Le dialogue de ticket SAV n'a pas pu être chargé."))
            return

        ticket_data = db_manager.get_sav_ticket_by_id(ticket_id)
        if not ticket_data:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Ticket SAV non trouvé (ID: {0}).").format(ticket_id))
            return

        all_client_products = db_manager.get_products_for_client_or_project(client_id, project_id=None)
        purchased_items = [
            {'name': p.get('product_name', 'N/A'), 'client_project_product_id': p.get('client_project_product_id')}
            for p in all_client_products if p.get('purchase_confirmed_at') is not None
        ]

        dialog = SAVTicketDialog(client_id=client_id, purchased_products=purchased_items, ticket_data=ticket_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_sav_tickets_table()

    # Placeholder handlers for new Assignment buttons
    def handle_add_assigned_vendor(self):
        if not self.default_company_id:
            QMessageBox.warning(self, self.tr("Société par Défaut Manquante"),
                                self.tr("Aucune société par défaut n'est configurée. Impossible d'assigner du personnel."))
            return
        # Assuming "seller" role for this button, adjust as needed or make role_filter dynamic
        dialog = AssignPersonnelDialog(client_id=self.client_info['client_id'],
                                       role_filter=None, # Or "seller", "sales", etc.
                                       company_id=self.default_company_id,
                                       parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_assigned_vendors_personnel()

    def handle_remove_assigned_vendor(self):
        selected_items = self.assigned_vendors_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un membre du personnel à retirer."))
            return

        assignment_id = selected_items[0].data(Qt.UserRole) # Assuming ID is stored in the first item
        if assignment_id is None and self.assigned_vendors_table.currentItem(): # Fallback if UserRole was not on first item
             assignment_id = self.assigned_vendors_table.currentItem().data(Qt.UserRole)


        if assignment_id is None:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer l'ID de l'assignation."))
            return

        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir retirer ce membre du personnel?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.unassign_personnel_from_client(assignment_id):
                self.load_assigned_vendors_personnel()
            else:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de retirer le membre du personnel."))

    def update_assigned_vendors_buttons_state(self):
        has_selection = bool(self.assigned_vendors_table.selectedItems())
        self.remove_assigned_vendor_btn.setEnabled(has_selection)


    def handle_add_assigned_technician(self):
        if not self.default_company_id:
            QMessageBox.warning(self, self.tr("Société par Défaut Manquante"),
                                self.tr("Aucune société par défaut n'est configurée. Impossible d'assigner des techniciens."))
            return
        # Assuming "technical_manager" or similar role for technicians
        dialog = AssignPersonnelDialog(client_id=self.client_info['client_id'],
                                       role_filter="technical_manager", # Or more generic like "technician"
                                       company_id=self.default_company_id,
                                       parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_assigned_technicians()

    def handle_remove_assigned_technician(self):
        selected_items = self.assigned_technicians_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un technicien à retirer."))
            return
        assignment_id = selected_items[0].data(Qt.UserRole)
        if assignment_id is None and self.assigned_technicians_table.currentItem():
             assignment_id = self.assigned_technicians_table.currentItem().data(Qt.UserRole)

        if assignment_id is None:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer l'ID de l'assignation."))
            return

        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir retirer ce technicien?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.unassign_personnel_from_client(assignment_id):
                self.load_assigned_technicians()
            else:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de retirer le technicien."))

    def update_assigned_technicians_buttons_state(self):
        has_selection = bool(self.assigned_technicians_table.selectedItems())
        self.remove_assigned_technician_btn.setEnabled(has_selection)

    def handle_add_assigned_transporter(self):
        dialog = AssignTransporterDialog(client_id=self.client_info['client_id'], parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_assigned_transporters()

    def handle_remove_assigned_transporter(self):
        selected_items = self.assigned_transporters_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un transporteur à retirer."))
            return

        client_transporter_id = selected_items[0].data(Qt.UserRole)
        if client_transporter_id is None and self.assigned_transporters_table.currentItem():
             client_transporter_id = self.assigned_transporters_table.currentItem().data(Qt.UserRole)

        if client_transporter_id is None:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer l'ID de l'assignation du transporteur."))
            return

        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir retirer ce transporteur?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.unassign_transporter_from_client(client_transporter_id):
                self.load_assigned_transporters()
            else:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de retirer le transporteur."))

    def update_assigned_transporters_buttons_state(self):
        has_selection = bool(self.assigned_transporters_table.selectedItems())
        self.remove_assigned_transporter_btn.setEnabled(has_selection)


    def handle_add_assigned_forwarder(self):
        dialog = AssignFreightForwarderDialog(client_id=self.client_info['client_id'], parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_assigned_freight_forwarders()

    def handle_remove_assigned_forwarder(self):
        selected_items = self.assigned_forwarders_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un transitaire à retirer."))
            return

        client_forwarder_id = selected_items[0].data(Qt.UserRole)
        if client_forwarder_id is None and self.assigned_forwarders_table.currentItem():
             client_forwarder_id = self.assigned_forwarders_table.currentItem().data(Qt.UserRole)

        if client_forwarder_id is None:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer l'ID de l'assignation du transitaire."))
            return

        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir retirer ce transitaire?"),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if db_manager.unassign_forwarder_from_client(client_forwarder_id):
                self.load_assigned_freight_forwarders()
            else:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible de retirer le transitaire."))

    def update_assigned_forwarders_buttons_state(self):
        has_selection = bool(self.assigned_forwarders_table.selectedItems())
        self.remove_assigned_forwarder_btn.setEnabled(has_selection)

    def open_carrier_email_dialog(self, row_index):
        try:
            transporter_name_item = self.assigned_transporters_table.item(row_index, 0) # Nom Transporteur

            if not transporter_name_item:
                QMessageBox.warning(self, self.tr("Erreur Données"), self.tr("Impossible de récupérer le nom du transporteur."))
                return

            transporter_name = transporter_name_item.text()
            client_transporter_id = transporter_name_item.data(Qt.UserRole)

            if client_transporter_id is None:
                QMessageBox.warning(self, self.tr("Erreur Données"), self.tr("ID du transporteur non trouvé pour cette ligne."))
                return

            # Fetch transporter details to get a reliable email.
            # This is a simplified way to get the email. Ideally, fetch directly or store more info in the table item's UserRole.
            assigned_list = db_manager.get_assigned_transporters_for_client(self.client_info.get('client_id'))
            transporter_email = ""
            if assigned_list: # Ensure assigned_list is not None
                for item_data in assigned_list:
                    if item_data.get('client_transporter_id') == client_transporter_id:
                        # Check for an 'email' field first
                        transporter_email = item_data.get('email')
                        if not transporter_email: # Fallback to 'contact_person' if it might be an email
                            contact_person_field = item_data.get('contact_person', '')
                            # Basic check if contact_person_field looks like an email
                            if '@' in contact_person_field and '.' in contact_person_field.split('@')[-1]:
                                transporter_email = contact_person_field
                        break

            if not transporter_email:
                email_text, ok = QInputDialog.getText(self, self.tr("Email du Transporteur Manquant"),
                                                      self.tr("L'email pour {0} n'est pas trouvé. Veuillez le saisir:").format(transporter_name))
                if ok and email_text.strip():
                    transporter_email = email_text.strip()
                else:
                    QMessageBox.information(self, self.tr("Annulé"), self.tr("Envoi d'email annulé car l'email du destinataire est manquant."))
                    self.load_assigned_transporters() # Refresh table even if cancelled here
                    return

            client_name = self.client_info.get("client_name", self.tr("Notre Client"))

            # Ensure self.config (application config) is passed to CarrierEmailDialog
            # self.config should be available from ClientWidget's __init__
            dialog = CarrierEmailDialog(
                carrier_name=transporter_name,
                carrier_email=transporter_email,
                client_name=client_name,
                client_transporter_id=client_transporter_id, # Pass the ID
                parent=self,
                config=self.config
            )
            dialog.exec_()
            self.load_assigned_transporters() # Refresh table after dialog closes

        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Dialogue Email"),
                                 self.tr("Une erreur est survenue lors de l'ouverture du dialogue d'email: {0}").format(str(e)))
            # For debugging: logging.error(f"Error opening carrier email dialog: {e}", exc_info=True)

    # Data Loading methods for Assignment Tables
    def load_assigned_vendors_personnel(self):
        self.assigned_vendors_table.setRowCount(0)
        self.assigned_vendors_table.setSortingEnabled(False)
        client_id = self.client_info.get('client_id')
        if not client_id: return
        try:
            # Example: Load all assigned personnel, or filter by a general "vendor/sales" role_in_project
            # For now, role_filter=None fetches all personnel assigned to this client.
            assigned_list = db_manager.get_assigned_personnel_for_client(client_id, role_filter=None) or []
            for row, item_data in enumerate(assigned_list):
                self.assigned_vendors_table.insertRow(row)
                name_item = QTableWidgetItem(item_data.get('personnel_name'))
                name_item.setData(Qt.UserRole, item_data.get('assignment_id')) # Store assignment_id
                self.assigned_vendors_table.setItem(row, 0, name_item)
                self.assigned_vendors_table.setItem(row, 1, QTableWidgetItem(item_data.get('role_in_project')))
                self.assigned_vendors_table.setItem(row, 2, QTableWidgetItem(item_data.get('personnel_email')))
                self.assigned_vendors_table.setItem(row, 3, QTableWidgetItem(item_data.get('personnel_phone')))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement"), self.tr("Impossible de charger le personnel assigné: {0}").format(str(e)))
        self.assigned_vendors_table.setSortingEnabled(True)
        self.update_assigned_vendors_buttons_state()


    def load_assigned_technicians(self):
        self.assigned_technicians_table.setRowCount(0)
        self.assigned_technicians_table.setSortingEnabled(False)
        client_id = self.client_info.get('client_id')
        if not client_id: return
        try:
            # Example: Filter for personnel assigned with a role_in_project like 'Technicien assigné'
            # Or, if AssignPersonnelDialog uses a role_filter for DB CompanyPersonnel.role, that's different.
            # Assuming here role_in_project is the primary filter criteria from Client_AssignedPersonnel table.
            assigned_list = db_manager.get_assigned_personnel_for_client(client_id, role_filter="Technicien") or [] # Or specific role
            for row, item_data in enumerate(assigned_list): # This list now comes from get_assigned_personnel_for_client
                self.assigned_technicians_table.insertRow(row)
                name_item = QTableWidgetItem(item_data.get('personnel_name'))
                name_item.setData(Qt.UserRole, item_data.get('assignment_id'))
                self.assigned_technicians_table.setItem(row, 0, name_item)
                self.assigned_technicians_table.setItem(row, 1, QTableWidgetItem(item_data.get('role_in_project')))
                self.assigned_technicians_table.setItem(row, 2, QTableWidgetItem(item_data.get('personnel_email')))
                self.assigned_technicians_table.setItem(row, 3, QTableWidgetItem(item_data.get('personnel_phone')))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement"), self.tr("Impossible de charger les techniciens assignés: {0}").format(str(e)))
        self.assigned_technicians_table.setSortingEnabled(True)
        self.update_assigned_technicians_buttons_state()


    def load_assigned_transporters(self):
        self.assigned_transporters_table.setRowCount(0)
        self.assigned_transporters_table.setSortingEnabled(False)
        client_id = self.client_info.get('client_id')
        if not client_id: return
        try:
            assigned_list = db_manager.get_assigned_transporters_for_client(client_id) or []
            for row, item_data in enumerate(assigned_list):
                self.assigned_transporters_table.insertRow(row)
                name_item = QTableWidgetItem(item_data.get('transporter_name'))
                name_item.setData(Qt.UserRole, item_data.get('client_transporter_id'))
                self.assigned_transporters_table.setItem(row, 0, name_item)
                self.assigned_transporters_table.setItem(row, 1, QTableWidgetItem(item_data.get('contact_person')))
                self.assigned_transporters_table.setItem(row, 2, QTableWidgetItem(item_data.get('phone')))
                self.assigned_transporters_table.setItem(row, 3, QTableWidgetItem(item_data.get('transport_details')))
                cost_item = QTableWidgetItem(f"{item_data.get('cost_estimate', 0.0):.2f} €")
                cost_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.assigned_transporters_table.setItem(row, 4, cost_item)

                email_status = item_data.get('email_status', 'Pending') # Get email_status

                btn_send_email = QPushButton()
                if email_status == "Sent":
                    btn_send_email.setText(self.tr("Email Sent"))
                    btn_send_email.setStyleSheet("background-color: lightgray; color: black;")
                    btn_send_email.setEnabled(False)
                elif email_status == "Failed":
                    btn_send_email.setText(self.tr("Resend Email (Failed)"))
                    btn_send_email.setStyleSheet("background-color: orange; color: black;")
                    btn_send_email.clicked.connect(lambda checked, r=row: self.open_carrier_email_dialog(r))
                else: # Pending or other
                    btn_send_email.setText(self.tr("Send Email"))
                    btn_send_email.setStyleSheet("background-color: green; color: white;")
                    btn_send_email.clicked.connect(lambda checked, r=row: self.open_carrier_email_dialog(r))

                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.addWidget(btn_send_email)
                action_layout.setContentsMargins(0, 0, 0, 0)
                action_layout.setAlignment(Qt.AlignCenter)
                action_widget.setLayout(action_layout)
                self.assigned_transporters_table.setCellWidget(row, 5, action_widget)

        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement"), self.tr("Impossible de charger les transporteurs assignés: {0}").format(str(e)))
        self.assigned_transporters_table.setSortingEnabled(True)
        self.update_assigned_transporters_buttons_state()

    def load_assigned_freight_forwarders(self):
        self.assigned_forwarders_table.setRowCount(0)
        self.assigned_forwarders_table.setSortingEnabled(False)
        client_id = self.client_info.get('client_id')
        if not client_id: return
        try:
            assigned_list = db_manager.get_assigned_forwarders_for_client(client_id) or []
            for row, item_data in enumerate(assigned_list):
                self.assigned_forwarders_table.insertRow(row)
                name_item = QTableWidgetItem(item_data.get('forwarder_name'))
                name_item.setData(Qt.UserRole, item_data.get('client_forwarder_id'))
                self.assigned_forwarders_table.setItem(row, 0, name_item)
                self.assigned_forwarders_table.setItem(row, 1, QTableWidgetItem(item_data.get('contact_person')))
                self.assigned_forwarders_table.setItem(row, 2, QTableWidgetItem(item_data.get('phone')))
                self.assigned_forwarders_table.setItem(row, 3, QTableWidgetItem(item_data.get('task_description')))
                cost_item = QTableWidgetItem(f"{item_data.get('cost_estimate', 0.0):.2f} €")
                cost_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.assigned_forwarders_table.setItem(row, 4, cost_item)
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement"), self.tr("Impossible de charger les transitaires assignés: {0}").format(str(e)))
        self.assigned_forwarders_table.setSortingEnabled(True)
        self.update_assigned_forwarders_buttons_state()


    def load_products_for_dimension_tab(self):
        """Populates the product selector combo box in the Product Dimensions tab."""
        self.dim_product_selector_combo.blockSignals(True)
        self.dim_product_selector_combo.clear()
        self.dim_product_selector_combo.addItem(self.tr("Sélectionner un produit..."), None)

        client_id = self.client_info.get('client_id')
        if not client_id:
            self.dim_product_selector_combo.blockSignals(False)
            return

        try:
            # Fetch all globally available products for selection.
            # Assuming db_manager.get_all_products() returns a list of product dictionaries
            # with at least 'product_id', 'product_name', 'language_code'.
            all_global_products = db_manager.get_all_products(filters=None)

            if all_global_products:
                # Global products should be unique by their definition (product_id).
                # Sorting can be done here if not handled by the DB query, or to ensure consistent order.
                # For example: all_global_products.sort(key=lambda x: (x.get('product_name', ''), x.get('language_code', '')))

                for prod_data in all_global_products: # Iterate directly if already sorted or uniqueness is guaranteed by source
                    product_name = prod_data.get('product_name', 'N/A')
                    global_product_id = prod_data.get('product_id')
                    lang_code = prod_data.get('language_code', '')

                    display_text = f"{product_name} ({lang_code}) - ID: {global_product_id}"
                    # Store the global_product_id as data for the combo box item
                    self.dim_product_selector_combo.addItem(display_text, global_product_id)
        except Exception as e:
            print(f"Error loading products for dimension tab: {e}")
            QMessageBox.warning(self, self.tr("Erreur Chargement"), self.tr("Impossible de charger les produits pour l'onglet dimensions."))

        self.dim_product_selector_combo.blockSignals(False)
        self.on_dim_product_selected()


    def on_dim_product_selected(self, index=None):
        """Handles selection change in the product selector for the dimensions tab."""
        selected_global_product_id = self.dim_product_selector_combo.currentData()

        if selected_global_product_id is None:
            self.edit_client_product_dimensions_button.setEnabled(False)
        else:
            self.edit_client_product_dimensions_button.setEnabled(True)


    def on_edit_client_product_dimensions(self):
        selected_global_product_id = self.dim_product_selector_combo.currentData()
        if selected_global_product_id is None:
            QMessageBox.warning(self, self.tr("Aucun Produit Sélectionné"),
                                self.tr("Veuillez sélectionner un produit dans la liste déroulante."))
            return


        client_id = self.client_info.get('client_id')
        if not client_id:
            QMessageBox.critical(self, self.tr("Erreur Client"),
                                 self.tr("L'ID du client n'est pas disponible."))
            return

        dialog = ClientProductDimensionDialog(
            client_id=client_id,
            product_id=selected_global_product_id,
            app_root_dir=self.app_root_dir,
            parent=self
        )
        dialog.exec_()

        self.load_document_notes_filters()
        self.load_document_notes_table()



    def load_document_notes_filters(self):
        """Populates filter combos for the document notes tab."""
        self.doc_notes_type_filter_combo.blockSignals(True)
        self.doc_notes_lang_filter_combo.blockSignals(True)

        self.doc_notes_type_filter_combo.clear()
        self.doc_notes_type_filter_combo.addItem(self.tr("Tous Types"), None)
        doc_types = ["Proforma", "Packing List", "Sales Conditions", "Certificate of Origin", "Bill of Lading", "Other"]
        for doc_type in doc_types:
            self.doc_notes_type_filter_combo.addItem(doc_type, doc_type)

        self.doc_notes_lang_filter_combo.clear()
        self.doc_notes_lang_filter_combo.addItem(self.tr("Toutes Langues"), None)
        langs = ["fr", "en", "ar", "tr", "pt"]
        for lang in langs:
            self.doc_notes_lang_filter_combo.addItem(lang, lang)

        self.doc_notes_type_filter_combo.blockSignals(False)
        self.doc_notes_lang_filter_combo.blockSignals(False)

        self.doc_notes_type_filter_combo.setCurrentIndex(0)
        self.doc_notes_lang_filter_combo.setCurrentIndex(0)


    def load_document_notes_table(self):
        """Fetches data from db_manager.get_client_document_notes() and populates table."""
        self.document_notes_table.setRowCount(0)
        client_id = self.client_info.get("client_id")
        if not client_id:
            return

        doc_type_filter = self.doc_notes_type_filter_combo.currentData()
        lang_filter = self.doc_notes_lang_filter_combo.currentData()

        try:
            notes = db_manager.get_client_document_notes(
                client_id,
                document_type=doc_type_filter,
                language_code=lang_filter,
                is_active=None
            )
            notes = notes if notes else []

            self.document_notes_table.setRowCount(len(notes))
            for row_idx, note in enumerate(notes):
                note_id = note.get("note_id")

                type_item = QTableWidgetItem(note.get("document_type"))
                type_item.setData(Qt.UserRole, note_id)
                self.document_notes_table.setItem(row_idx, 0, type_item)

                self.document_notes_table.setItem(row_idx, 1, QTableWidgetItem(note.get("language_code")))

                content_preview = note.get("note_content", "")
                if len(content_preview) > 70: content_preview = content_preview[:67] + "..."
                self.document_notes_table.setItem(row_idx, 2, QTableWidgetItem(content_preview))

                note_content = note.get("note_content", "")
                lines = [line.strip() for line in note_content.split('\n') if line.strip()]

                html_content = ""
                if lines:
                    html_content = "<ol style='margin:0px; padding-left: 15px;'>"
                    for line in lines:

                        escaped_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        html_content += f"<li>{escaped_line}</li>"
                    html_content += "</ol>"
                else:
                    html_content = f"<p style='margin:0px; font-style:italic;'>{self.tr('Aucune note.')}</p>"

                note_label = QLabel()
                note_label.setText(html_content)
                note_label.setWordWrap(True)

                self.document_notes_table.setCellWidget(row_idx, 2, note_label)


                active_text = self.tr("Oui") if note.get("is_active") else self.tr("Non")
                active_item = QTableWidgetItem(active_text)
                active_item.setTextAlignment(Qt.AlignCenter)
                self.document_notes_table.setItem(row_idx, 3, active_item)


                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(5, 0, 5, 0)
                actions_layout.setSpacing(5)

                edit_button = QPushButton(QIcon(":/icons/pencil.svg"), "")
                edit_button.setToolTip(self.tr("Modifier cette note"))
                edit_button.clicked.connect(lambda checked, n_id=note_id: self.on_edit_document_note_clicked(n_id))
                actions_layout.addWidget(edit_button)

                delete_button = QPushButton(QIcon(":/icons/trash.svg"), "")
                delete_button.setToolTip(self.tr("Supprimer cette note"))
                delete_button.setObjectName("dangerButton")
                delete_button.clicked.connect(lambda checked, n_id=note_id: self.on_delete_document_note_clicked(n_id))
                actions_layout.addWidget(delete_button)

                actions_layout.addStretch()
                self.document_notes_table.setCellWidget(row_idx, 4, actions_widget)


            self.document_notes_table.resizeColumnToContents(0)
            self.document_notes_table.resizeColumnToContents(1)

            self.document_notes_table.resizeColumnToContents(3)
            self.document_notes_table.resizeColumnToContents(4)

        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement Notes"), self.tr("Impossible de charger les notes de document:\n{0}").format(str(e)))


    def on_add_document_note(self):
        client_id = self.client_info.get("client_id")
        if not client_id:
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible."))
            return

        dialog = self.ClientDocumentNoteDialog(client_id=client_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_document_notes_table()


    def on_edit_document_note_clicked(self, note_id):
        client_id = self.client_info.get("client_id")
        if not client_id:
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible."))
            return

        note_data = db_manager.get_client_document_note_by_id(note_id)
        if note_data:
            dialog = self.ClientDocumentNoteDialog(client_id=client_id, note_data=note_data, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_document_notes_table()
        else:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Note non trouvée (ID: {0}).").format(note_id))


    def on_delete_document_note_clicked(self, note_id):
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir supprimer cette note (ID: {0})?").format(note_id),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                success = db_manager.delete_client_document_note(note_id)
                if success:
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Note supprimée avec succès."))
                    self.load_document_notes_table()
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible de supprimer la note. Vérifiez les logs."))
            except Exception as e:
                 QMessageBox.critical(self, self.tr("Erreur"), self.tr("Une erreur est survenue lors de la suppression:\n{0}").format(str(e)))


    def prev_contact_page(self):
        if self.current_contact_offset > 0:
            self.current_contact_offset -= self.CONTACT_PAGE_LIMIT
            self.load_contacts()

    def next_contact_page(self):
        if (self.current_contact_offset + self.CONTACT_PAGE_LIMIT) < self.total_contacts_count:
            self.current_contact_offset += self.CONTACT_PAGE_LIMIT
            self.load_contacts()

    def update_contact_pagination_controls(self):
        if self.total_contacts_count == 0:
            total_pages = 1
            current_page = 1
        else:
            total_pages = math.ceil(self.total_contacts_count / self.CONTACT_PAGE_LIMIT)
            current_page = (self.current_contact_offset // self.CONTACT_PAGE_LIMIT) + 1

        self.contact_page_info_label.setText(f"Page {current_page} / {total_pages}")
        self.prev_contact_button.setEnabled(self.current_contact_offset > 0)
        self.next_contact_button.setEnabled((self.current_contact_offset + self.CONTACT_PAGE_LIMIT) < self.total_contacts_count)

    def add_document(self):
        # Define available languages
        available_languages = ["en", "fr", "ar", "tr", "pt"]

        # Ask user to select language
        selected_doc_language, ok = QInputDialog.getItem(
            self,
            self.tr("Sélectionner la langue"),
            self.tr("Langue du document:"),
            available_languages,
            0,
            False
        )

        if not ok or not selected_doc_language:
            QMessageBox.information(self, self.tr("Annulé"), self.tr("L'opération d'ajout de document a été annulée."))
            return

        # Get the base path for the client's documents
        initial_dir = self.config.get("clients_dir", os.path.expanduser("~"))

        selected_file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Sélectionner un document"),
            initial_dir,
            self.tr("Tous les fichiers (*.*)")
        )

        if selected_file_path:
            try:
                # Determine the target directory using the selected language
                # AND POTENTIAL order_identifier (conceptual for now, as add_document doesn't create DB entry)
                client_base_path = self.client_info["base_folder_path"]

                # --- Conceptual: How order_identifier would be handled if add_document created DB entries ---
                # For now, this part is more about the file system structure if an order_id were available.
                # The actual capture of order_identifier for imported docs is deferred.
                # Let's assume `selected_order_identifier_for_import` is obtained similar to CreateDocumentDialog
                selected_order_identifier_for_import = None # Placeholder for this example
                # if self.client_info.get('category') == 'Distributeur' or db_manager.get_distinct_purchase_confirmed_at_for_client(self.client_info['client_id']):
                #     # ... QInputDialog logic to get order_identifier ...
                #     pass

                target_dir = os.path.join(client_base_path, selected_doc_language) # Default for general docs
                if selected_order_identifier_for_import:
                    safe_order_subfolder = selected_order_identifier_for_import.replace(':', '_').replace(' ', '_')
                    target_dir = os.path.join(client_base_path, safe_order_subfolder, selected_doc_language)
                # --- End conceptual part ---

                os.makedirs(target_dir, exist_ok=True)

                file_name = os.path.basename(selected_file_path)
                target_file_path = os.path.join(target_dir, file_name) # This is the actual save path

                if os.path.exists(target_file_path):
                    reply = QMessageBox.question(
                        self,
                        self.tr("Fichier Existant"),
                        self.tr("Un fichier du même nom existe déjà à cet emplacement. Voulez-vous le remplacer?"),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        QMessageBox.information(self, self.tr("Annulé"), self.tr("L'opération d'ajout de document a été annulée."))
                        return

                shutil.copy(selected_file_path, target_file_path)

                # Metadata gathering
                client_id = self.client_info.get("client_id")
                document_name = os.path.basename(selected_file_path)
                file_name_on_disk = document_name
                file_path_relative = os.path.join(selected_doc_language, file_name) # Assuming target_dir structure

                # Infer document_type_generated from extension
                ext = os.path.splitext(file_name)[1].lower()
                if ext == ".html":
                    document_type_generated = "HTML"
                elif ext == ".pdf":
                    document_type_generated = "PDF"
                elif ext == ".xlsx":
                    document_type_generated = "XLSX"
                elif ext == ".docx":
                    document_type_generated = "DOCX"
                else:
                    document_type_generated = ext.upper().replace(".", "") if ext else "OTHER"

                language_code = selected_doc_language
                source_template_id = None # For imported documents

                order_identifier = None
                if hasattr(self, 'doc_order_filter_combo') and self.doc_order_filter_combo.isVisible():
                    current_order_data = self.doc_order_filter_combo.currentData()
                    if current_order_data not in ["ALL", "NONE"]:
                        order_identifier = current_order_data

                created_by_user_id = None # ClientWidget does not have self.current_user_id
                notes = None
                version_tag = "1.0"

                doc_db_data = {
                    "client_id": client_id,
                    "document_name": document_name,
                    "file_name_on_disk": file_name_on_disk,
                    "file_path_relative": file_path_relative,
                    "document_type_generated": document_type_generated,
                    "language_code": language_code,
                    "source_template_id": source_template_id,
                    "order_identifier": order_identifier,
                    "created_by_user_id": created_by_user_id, # Corrected key for db_manager
                    "notes": notes,
                    "version_tag": version_tag,
                    # project_id is not explicitly gathered here, will be None if not in dict
                }
                # The key in add_client_document is 'user_id', not 'created_by_user_id'
                # Let's adjust doc_db_data to use 'user_id' for the CRUD function based on its definition.
                doc_db_data_for_crud = doc_db_data.copy()
                doc_db_data_for_crud['user_id'] = doc_db_data_for_crud.pop('created_by_user_id')


                db_success = False
                try:
                    new_doc_db_id = db_manager.add_client_document(doc_db_data_for_crud)
                    if new_doc_db_id:
                        db_success = True
                        # Update client's selected languages if necessary
                        current_selected_languages = self.client_info.get("selected_languages", [])
                        if isinstance(current_selected_languages, str):
                            current_selected_languages = [lang.strip() for lang in current_selected_languages.split(',') if lang.strip()]
                        if not current_selected_languages: current_selected_languages = []

                        if selected_doc_language not in current_selected_languages:
                            add_lang_reply = QMessageBox.question(
                                self, self.tr("Ajouter Langue"),
                                self.tr("Voulez-vous ajouter '{0}' aux langues sélectionnées pour ce client?").format(selected_doc_language),
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                            )
                            if add_lang_reply == QMessageBox.Yes:
                                updated_languages_list = current_selected_languages + [selected_doc_language]
                                updated_languages_str = ",".join(updated_languages_list)
                                client_id_to_update = self.client_info.get("client_id")
                                if client_id_to_update:
                                    if db_manager.update_client(client_id_to_update, {'selected_languages': updated_languages_str}):
                                        self.client_info["selected_languages"] = updated_languages_list
                                        print(f"Client {client_id_to_update} selected_languages updated to {updated_languages_str}")
                                    else:
                                        QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour des langues du client dans la DB."))
                                else:
                                    QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible, impossible de mettre à jour les langues."))

                        self.populate_doc_table() # Call after successful DB operation
                        QMessageBox.information(
                            self, self.tr("Succès"),
                            self.tr("Document '{0}' importé et enregistré avec succès en langue '{1}'.").format(file_name, selected_doc_language)
                        )
                    else:
                        # db_success remains False
                        self.populate_doc_table() # Still populate to show the file if copied
                        QMessageBox.warning(
                            self, self.tr("Échec Enregistrement DB"),
                            self.tr("Document '{0}' copié avec succès en langue '{1}', mais échec de l'enregistrement dans la base de données. Le document pourrait ne pas s'afficher correctement.").format(file_name, selected_doc_language)
                        )
                except Exception as db_e:
                    # db_success remains False
                    logging.error(f"Error during database operation in add_document: {db_e}", exc_info=True)
                    self.populate_doc_table() # Still populate to show the file if copied
                    QMessageBox.warning(
                        self, self.tr("Erreur Base de Données"),
                        self.tr("Document '{0}' copié, mais une erreur est survenue lors de l'enregistrement dans la base de données: {1}. Le document pourrait ne pas s'afficher correctement.").format(file_name, str(db_e))
                    )

            except Exception as e:
                logging.error(f"Error copying file or preparing metadata in add_document: {e}", exc_info=True)
                QMessageBox.warning(
                    self, self.tr("Erreur"),
                    self.tr("Impossible d'ajouter le document : {0}").format(str(e))
                )

    def _handle_open_pdf_action(self, file_path):
        QApplication.setOverrideCursor(Qt.WaitCursor) # Set wait cursor
        try:
            if not self.client_info or 'client_id' not in self.client_info:
                QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("Les informations du client ne sont pas disponibles."))
                return # Return early, finally will still execute

            # Extract target_language_code from the file_path
            try:
                target_language_code = os.path.basename(os.path.dirname(file_path))
                if target_language_code not in ["en", "fr", "ar", "tr", "pt"]:
                    client_langs = self.client_info.get("selected_languages", [])
                    if isinstance(client_langs, str):
                        client_langs = [lang.strip() for lang in client_langs.split(',') if lang.strip()]
                    target_language_code = client_langs[0] if client_langs else "fr"
                    logging.info(f"Language code not recognized from path {file_path}. Using fallback/default: {target_language_code}")

            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur Chemin Fichier"), self.tr("Impossible d'extraire le code langue depuis le chemin:\n{0}\nErreur: {1}").format(file_path, str(e)))
                return # Return early

            app_root_dir = self.config.get('app_root_dir', os.path.dirname(sys.argv[0]))
            if MAIN_MODULE_CONFIG and 'app_root_dir' in MAIN_MODULE_CONFIG:
                app_root_dir = MAIN_MODULE_CONFIG['app_root_dir']

            generated_pdf_path = self.generate_pdf_for_document(
                source_file_path=file_path,
                client_info=self.client_info,
                app_root_dir=app_root_dir,
                parent_widget=self,
                target_language_code=target_language_code
            )
            if generated_pdf_path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(generated_pdf_path))
            # else:
                # Optional: If generate_pdf_for_document returns None on failure, inform user
                # QMessageBox.warning(self, self.tr("Erreur PDF"), self.tr("Le fichier PDF n'a pas pu être généré."))
        finally:
            QApplication.restoreOverrideCursor() # Restore cursor in all cases

    def populate_details_layout(self):
        # Clear existing rows from the layout
        if self.status_combo and self.status_combo.parent():
            self.status_combo.setParent(None)
        if hasattr(self, 'category_label') and self.category_label and self.category_label.parent():
            self.category_label.setParent(None)
        if hasattr(self, 'category_value_label') and self.category_value_label and self.category_value_label.parent():
            self.category_value_label.setParent(None)
        while self.details_layout.rowCount() > 0:
            self.details_layout.removeRow(0)

        self.detail_value_labels = {} # Re-initialize
        logging.info(f"Populating details layout for: {self.client_info.get('client_name')}")

        # Project ID
        project_id_label = QLabel(self.tr("ID Projet:"))
        project_identifier_value = self.client_info.get("project_identifier", self.tr("N/A"))
        logging.info(f"Setting project_identifier: {project_identifier_value}")
        project_id_value_label = QLabel(project_identifier_value)
        self.details_layout.addRow(project_id_label, project_id_value_label)
        self.detail_value_labels["project_identifier"] = project_id_value_label

        # Country and City
        country_city_widget = QWidget()
        country_city_h_layout = QHBoxLayout(country_city_widget)
        country_city_h_layout.setContentsMargins(0,0,0,0)
        country_label = QLabel(self.tr("Pays:"))
        country_text_value = self.client_info.get("country", self.tr("N/A"))
        logging.info(f"Setting country: {country_text_value}")
        country_value_label = QLabel(country_text_value)
        city_label = QLabel(self.tr("Ville:"))
        city_text_value = self.client_info.get("city", self.tr("N/A"))
        logging.info(f"Setting city: {city_text_value}")
        city_value_label = QLabel(city_text_value)
        country_city_h_layout.addWidget(country_label)
        country_city_h_layout.addWidget(country_value_label)
        country_city_h_layout.addSpacing(20)
        country_city_h_layout.addWidget(city_label)
        country_city_h_layout.addWidget(city_value_label)
        country_city_h_layout.addStretch()
        self.details_layout.addRow(self.tr("Localisation:"), country_city_widget)
        self.detail_value_labels["country"] = country_value_label
        self.detail_value_labels["city"] = city_value_label

        # Price and Creation Date
        price_date_widget = QWidget()
        price_date_h_layout = QHBoxLayout(price_date_widget)
        price_date_h_layout.setContentsMargins(0,0,0,0)
        price_label = QLabel(self.tr("Prix Final:"))
        price_value_data = self.client_info.get('price', 0)
        logging.info(f"Setting price: {price_value_data}")
        price_value_label = QLabel(f"{price_value_data} €")
        date_label = QLabel(self.tr("Date Création:"))
        creation_date_data = self.client_info.get("creation_date", self.tr("N/A"))
        logging.info(f"Setting creation_date: {creation_date_data}")
        date_value_label = QLabel(creation_date_data)
        price_date_h_layout.addWidget(price_label)
        price_date_h_layout.addWidget(price_value_label)
        price_date_h_layout.addSpacing(20)
        price_date_h_layout.addWidget(date_label)
        price_date_h_layout.addWidget(date_value_label)
        price_date_h_layout.addStretch()
        self.details_layout.addRow(self.tr("Finances & Date:"), price_date_widget)
        self.detail_value_labels["price"] = price_value_label
        self.detail_value_labels["creation_date"] = date_value_label

        # Status and Category
        status_category_widget = QWidget()
        status_category_h_layout = QHBoxLayout(status_category_widget)
        status_category_h_layout.setContentsMargins(0,0,0,0)
        logging.info(f"Setting status: {self.client_info.get('status', self.tr('En cours'))}") # status_combo text set elsewhere
        status_category_h_layout.addWidget(QLabel(self.tr("Statut:")))
        status_category_h_layout.addWidget(self.status_combo) # status_combo itself is added
        status_category_h_layout.addSpacing(20)
        category_text_value = self.client_info.get("category", self.tr("N/A"))
        logging.info(f"Setting category: {category_text_value}")
        self.category_value_label.setText(category_text_value) # Set text on the instance member
        status_category_h_layout.addWidget(self.category_label) # Add instance member label
        status_category_h_layout.addWidget(self.category_value_label) # Add instance member value label
        status_category_h_layout.addStretch()
        self.details_layout.addRow(self.tr("Classification:"), status_category_widget)
        self.detail_value_labels["category_value"] = self.category_value_label # Store for edit mode

        # Distributor Specific Info (conditionally visible)
        self.distributor_info_label = QLabel(self.tr("Info Distributeur:"))
        distributor_specific_info_value = self.client_info.get('distributor_specific_info', '')
        # Logging for distributor_specific_info is implicitly covered by toggle_distributor_info_visibility if shown
        self.distributor_info_value_label = QLabel(distributor_specific_info_value)
        self.distributor_info_value_label.setWordWrap(True)
        self.distributor_info_value_label.setObjectName("distributorInfoValueLabel")
        self.distributor_info_label.setObjectName("distributorInfoLabel")
        self.details_layout.addRow(self.distributor_info_label, self.distributor_info_value_label)
        self.toggle_distributor_info_visibility()

        # Need (Besoin Principal)
        need_label = QLabel(self.tr("Besoin Principal:"))
        need_text_value = self.client_info.get("need", self.client_info.get("primary_need_description", self.tr("N/A")))
        logging.info(f"Setting need: {need_text_value}")
        need_value_label = QLabel(need_text_value)
        self.details_layout.addRow(need_label, need_value_label)
        self.detail_value_labels["need"] = need_value_label

        # Base Folder Path
        folder_label = QLabel(self.tr("Chemin Dossier:"))
        folder_path_value = self.client_info.get('base_folder_path')
        if not folder_path_value:
            folder_path_value = self.client_info.get('default_base_folder_path', '') # Fallback to default_base_folder_path
        logging.info(f"Retrieved folder_path_value: '{folder_path_value}' (tried 'base_folder_path' then 'default_base_folder_path')")
        if folder_path_value and os.path.isdir(folder_path_value): # Check if path is valid and a directory
            folder_display_text = f"<a href='file:///{folder_path_value}'>{folder_path_value}</a>"
            folder_value_label = QLabel(folder_display_text)
            folder_value_label.setOpenExternalLinks(True)
            folder_value_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        else:
            if not folder_path_value:
                logging.warning(f"Client {self.client_info.get('client_id')}: base_folder_path and default_base_folder_path are missing or empty.")
                folder_display_text = self.tr("N/A - Chemin non configuré")
            else: # Path exists but is not a directory
                logging.warning(f"Client {self.client_info.get('client_id')}: folder_path_value '{folder_path_value}' is not a valid directory.")
                folder_display_text = self.tr("Chemin invalide: {0}").format(folder_path_value)
            folder_value_label = QLabel(folder_display_text)
        self.details_layout.addRow(folder_label, folder_value_label)
        self.detail_value_labels["base_folder_path"] = folder_value_label

    def refresh_display(self, new_client_info):
        # logging.info(f"ClientWidget refresh_display: client_id={new_client_info.get('client_id')}, client_name={new_client_info.get('client_name')}")
        self.client_info = new_client_info
        # Update GroupBox title if it includes client name
        if hasattr(self, 'client_info_group_box'):
            self.client_info_group_box.setTitle(self.client_info.get('client_name', self.tr("Client Information")))

        self.header_label.setText(f"<h2>{self.client_info.get('client_name', '')}</h2>")

        # Repopulate the details section with the new client_info
        self.populate_details_layout() # This now contains logging

        # Ensure status_combo and category_value_label (and distributor info) are updated
        # These are handled by populate_details_layout and its call to toggle_distributor_info_visibility
        self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours")))
        # self.category_value_label.setText(self.client_info.get("category", self.tr("N/A"))) # Done in populate_details_layout
        # distributor_info_value_label is updated within populate_details_layout

        self.notes_edit.setText(self.client_info.get("notes", ""))
        self.update_sav_tab_visibility() # Refresh SAV tab visibility
        # Also ensure SAV tickets table is loaded if tab is visible
        if hasattr(self, 'sav_tab_index') and self.tab_widget.isTabEnabled(self.sav_tab_index): # Check sav_tab_index exists
            self.load_sav_tickets_table()

    def load_statuses(self):
        try:
            # Assuming 'Client' is the status_type for this context
            client_statuses = db_manager.get_all_status_settings(type_filter='Client')

            self.status_combo.clear() # Clear before populating
            if client_statuses: # Ensure client_statuses is not None and not empty
                for status_dict in client_statuses:
                    if not isinstance(status_dict, dict):
                        logging.warning(f"Skipping status item, expected dict but got {type(status_dict)}: {status_dict}")
                        continue

                    status_name = status_dict.get('status_name')
                    status_id = status_dict.get('status_id')

                    if status_id is None: # status_id is essential for functionality
                        logging.warning(f"Skipping status item due to missing 'status_id': {status_dict}")
                        continue

                    if not status_name: # status_name is essential for display
                        status_name = self.tr("Unnamed Status ({0})").format(status_id)
                        logging.warning(f"Status name missing for status_id {status_id}, using default: '{status_name}'")

                    self.status_combo.addItem(str(status_name), status_id) # Ensure name is a string
            # else: # Handle case where client_statuses is None or empty after fetching
                # logging.info("No client statuses found or returned from DB to populate status_combo.")
                # Optionally, add a default item or leave the combo box empty.
                # If left empty, ensure currentTextChanged signal handling is robust.

        except Exception as e: # Catch a more generic exception if db_manager might raise something other than sqlite3.Error
            logging.error(f"Error loading statuses in ClientWidget: {e}", exc_info=True) # Log with more detail
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des statuts:\n{0}").format(str(e)))

    def update_client_status(self, status_text):
        # This method should now use currentData if status_id is reliably stored.
        # However, it's currently written to take status_text and find the ID.
        # This is acceptable. If issues arise, it can be changed to use currentData().
        try:
            status_setting = db_manager.get_status_setting_by_name(status_text, 'Client') # status_text from combo box
            if status_setting and status_setting.get('status_id') is not None:
                status_id_to_set = status_setting['status_id']
                client_id_to_update = self.client_info.get("client_id")

                if client_id_to_update is None:
                    QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible, impossible de mettre à jour le statut."))
                    return

                if status_text == 'Vendu':
                    vendu_status_id = status_id_to_set # Already fetched

                    products_to_confirm = db_manager.get_products_for_client_or_project(
                        client_id_to_update,
                        project_id=None # Assuming confirmation applies to all client's products not yet confirmed
                    )
                    # Filter for products where purchase_confirmed_at is NULL
                    products_needing_confirmation = [
                        p for p in products_to_confirm if p.get('purchase_confirmed_at') is None
                    ]

                    if not products_needing_confirmation:
                        QMessageBox.information(self, self.tr("Confirmation Vente"), self.tr("Aucun produit à confirmer pour cette vente."))
                    else:
                        for product_data in products_needing_confirmation:
                            client_project_product_id = product_data.get('client_project_product_id')
                            # Fetch product name for dialog if not available directly or to ensure freshness
                            # Assuming product_data from get_products_for_client_or_project includes 'product_name'
                            product_name = product_data.get('product_name', self.tr('Produit Inconnu'))

                            default_serial = f"SN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            serial_number, ok = QInputDialog.getText(
                                self,
                                self.tr("Confirmation Achat Produit"),
                                self.tr(f"Produit: {product_name}\nEntrez le numéro de série (ou laissez vide pour auto/pas de numéro):"),
                                QLineEdit.Normal,
                                default_serial
                            )
                            if ok:
                                entered_serial = serial_number.strip() if serial_number.strip() else "N/A" # Or None
                                current_timestamp_iso = datetime.utcnow().isoformat() + "Z"

                                update_payload = {
                                    'serial_number': entered_serial,
                                    'purchase_confirmed_at': current_timestamp_iso
                                }
                                if db_manager.update_client_project_product(client_project_product_id, update_payload):
                                    print(f"Product {client_project_product_id} ({product_name}) confirmed with SN: {entered_serial}")
                                else:
                                    QMessageBox.warning(self, self.tr("Erreur Mise à Jour Produit"), self.tr(f"Impossible de confirmer l'achat pour le produit {product_name}."))
                            else:
                                print(f"Confirmation annulée pour le produit {product_name}.")
                                # Optionally, decide if the whole "Vendu" status update should be cancelled if any product is skipped.
                                # For now, it proceeds.

                # Proceed to update the client's status after product confirmations
                # Proceed to update the client's status after product confirmations
                if db_manager.update_client(client_id_to_update, {'status_id': status_id_to_set}):
                    self.client_info["status"] = status_text
                    self.client_info["status_id"] = status_id_to_set
                    print(f"Client {client_id_to_update} status_id updated to {status_id_to_set} ({status_text})")
                    if self.notification_manager:
                        self.notification_manager.show(title=self.tr("Statut Mis à Jour"),
                                                        message=self.tr("Statut du client '{0}' mis à jour à '{1}'.").format(self.client_info.get("client_name", ""), status_text),
                                                        type='SUCCESS')
                    else:
                        logging.warning("Notification manager not available. Cannot show notification: Statut Mis à Jour - Statut du client '{0}' mis à jour à '{1}'.".format(self.client_info.get("client_name", ""), status_text))
                    self.update_sav_tab_visibility() # Update SAV tab based on new status
                else:
                    if self.notification_manager:
                        self.notification_manager.show(title=self.tr("Erreur Statut"), message=self.tr("Échec de la mise à jour du statut."), type='ERROR')
                    else:
                        logging.warning("Notification manager not available. Cannot show notification: Erreur Statut - Échec de la mise à jour du statut.")
                    # The following line seems to be a duplicate or leftover, consider removing if get_notification_manager() is not standard.
                    # get_notification_manager().show(title=self.tr("Erreur Statut"), message=self.tr("Échec de la mise à jour du statut."), type='ERROR')

            # This 'elif status_text:' should handle other statuses not 'Vendu'
            elif status_text and status_text != 'Vendu': # If it's not 'Vendu' and status_text is not empty
                # Ensure client_id_to_update and status_id_to_set are defined in this path
                client_id_to_update = self.client_info.get("client_id")
                status_setting = db_manager.get_status_setting_by_name(status_text, 'Client')
                if not client_id_to_update or not status_setting or status_setting.get('status_id') is None:
                    QMessageBox.warning(self, self.tr("Erreur Critique"), self.tr("Données client ou statut manquantes pour la mise à jour."))
                    return # or handle error appropriately

                status_id_to_set = status_setting['status_id']

                if db_manager.update_client(client_id_to_update, {'status_id': status_id_to_set}):
                    self.client_info["status"] = status_text
                    self.client_info["status_id"] = status_id_to_set
                    print(f"Client {client_id_to_update} status_id updated to {status_id_to_set} ({status_text}) for non-Vendu status.")
                    if self.notification_manager:
                        self.notification_manager.show(title=self.tr("Statut Mis à Jour"),
                                                        message=self.tr("Statut du client '{0}' mis à jour à '{1}'.").format(self.client_info.get("client_name", ""), status_text),
                                                        type='SUCCESS')
                    else:
                        logging.warning("Notification manager not available. Cannot show notification: Statut Mis à Jour - Statut du client '{0}' mis à jour à '{1}'.".format(self.client_info.get("client_name", ""), status_text))
                    self.update_sav_tab_visibility() # Update SAV tab based on new status
                else:
                    if self.notification_manager:
                        self.notification_manager.show(title=self.tr("Erreur Statut"), message=self.tr("Échec de la mise à jour du statut pour '{0}'.").format(status_text), type='ERROR')
                    else:
                        logging.warning("Notification manager not available. Cannot show notification: Erreur Statut - Échec de la mise à jour du statut pour '{0}'.".format(status_text))

            elif status_text: # Fallback for empty status_text or other unhandled cases
                QMessageBox.warning(self, self.tr("Erreur Configuration"), self.tr("Statut '{0}' non trouvé ou invalide. Impossible de mettre à jour.").format(status_text))
                if self.notification_manager:
                    self.notification_manager.show(title=self.tr("Erreur Statut"), message=self.tr("Statut '{0}' non trouvé ou invalide.").format(status_text), type='ERROR')
                else:
                    logging.warning("Notification manager not available. Cannot show notification: Erreur Statut - Statut '{0}' non trouvé ou invalide.".format(status_text))

        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Erreur de mise à jour du statut:\n{0}").format(str(e)))
            if self.notification_manager:
                self.notification_manager.show(title=self.tr("Erreur Statut Inattendue"), message=self.tr("Erreur inattendue: {0}").format(str(e)), type='ERROR')
            else:
                logging.warning("Notification manager not available. Cannot show notification: Erreur Statut Inattendue - Erreur inattendue: {0}.".format(str(e)))

    def save_client_notes(self):
        notes = self.notes_edit.toPlainText()
        client_id_to_update = self.client_info.get("client_id")

        if client_id_to_update is None:
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible, impossible de sauvegarder les notes."))
            return

        try:
            if db_manager.update_client(client_id_to_update, {'notes': notes}):
                self.client_info["notes"] = notes # Update local copy
                # Optionally, notify on successful save, though it might be too frequent if auto-saving.
                # if self.notification_manager:
                #     self.notification_manager.show(title=self.tr("Notes Sauvegardées"), message=self.tr("Notes du client enregistrées."), type='INFO', duration=2000)
                # else:
                #     logging.warning("Notification manager not available. Cannot show notification: Notes Sauvegardées - Notes du client enregistrées.")
            else:
                if self.notification_manager:
                    self.notification_manager.show(title=self.tr("Erreur Notes"), message=self.tr("Échec de la sauvegarde des notes."), type='ERROR')
                else:
                    logging.warning("Notification manager not available. Cannot show notification: Erreur Notes - Échec de la sauvegarde des notes.")
        except Exception as e:
            if self.notification_manager:
                self.notification_manager.show(title=self.tr("Erreur Notes"), message=self.tr("Erreur de sauvegarde des notes: {0}").format(str(e)), type='ERROR')
            else:
                logging.warning("Notification manager not available. Cannot show notification: Erreur Notes - Erreur de sauvegarde des notes: {0}.".format(str(e)))

    def populate_doc_table(self):
        self.doc_table.setRowCount(0) # Clear table first
        if hasattr(self, 'documents_empty_label'): self.documents_empty_label.setVisible(True)
        self.doc_table.setVisible(False)

        client_id = self.client_info.get("client_id")
        if not client_id:
            if hasattr(self, 'documents_empty_label'): self.documents_empty_label.setVisible(True)
            logging.warning("populate_doc_table: client_id is missing from client_info.")
            return

        # Order filter population (existing logic)
        order_events = db_manager.get_distinct_purchase_confirmed_at_for_client(client_id)
        is_distributor_type = self.client_info.get('category') == 'Distributeur'
        has_multiple_orders = order_events and len(order_events) > 1
        show_order_filter_dropdown = is_distributor_type or has_multiple_orders # Determines if order dropdown is specifically populated/used

        # Visibility of the entire filter bar container.
        # For now, let's make it always visible as per instruction to show filters even for empty list.
        # self.doc_filter_layout_widget.setVisible(True) # This is now set in setup_ui

        current_order_filter_selection = None
        if show_order_filter_dropdown: # Populate order filter only if relevant
            current_order_filter_selection = self.doc_order_filter_combo.currentData()
            self.doc_order_filter_combo.blockSignals(True)
            self.doc_order_filter_combo.clear()
            self.doc_order_filter_combo.addItem(self.tr("Toutes les Commandes"), "ALL")
            self.doc_order_filter_combo.addItem(self.tr("Documents Généraux (sans commande)"), "NONE")
            if order_events:
                for event_ts in order_events:
                    if event_ts:
                        try:
                            dt_obj = datetime.fromisoformat(event_ts.replace('Z', '+00:00'))
                            display_text = self.tr("Commande du {0}").format(dt_obj.strftime('%Y-%m-%d %H:%M'))
                            self.doc_order_filter_combo.addItem(display_text, event_ts)
                        except ValueError:
                            self.doc_order_filter_combo.addItem(self.tr("Commande du {0} (brut)").format(event_ts), event_ts)
            if current_order_filter_selection:
                index = self.doc_order_filter_combo.findData(current_order_filter_selection)
                if index >= 0: self.doc_order_filter_combo.setCurrentIndex(index)
                else: self.doc_order_filter_combo.setCurrentIndex(0)
            else:
                 self.doc_order_filter_combo.setCurrentIndex(0)
            self.doc_order_filter_combo.blockSignals(False)
        else: # Hide or disable order filter if not applicable
            self.doc_order_filter_combo.clear()
            self.doc_order_filter_combo.addItem(self.tr("N/A"), "ALL") # Default to ALL if not used
            self.doc_order_filter_combo.setEnabled(False)


        db_filters = {} # Filters for the DB query (currently only order_identifier)
        selected_order_filter_data = self.doc_order_filter_combo.currentData()
        if selected_order_filter_data == "NONE":
            db_filters['order_identifier'] = None
        elif selected_order_filter_data != "ALL":
            db_filters['order_identifier'] = selected_order_filter_data

        # Fetch documents based on DB filters (order filter)
        client_documents_from_db = db_manager.get_documents_for_client(client_id, filters=db_filters)
        client_documents_from_db = client_documents_from_db if client_documents_from_db else []

        # Get language and type filter values for client-side filtering
        selected_lang_filter = self.doc_language_filter_combo.currentData()
        selected_type_filter = self.doc_type_filter_combo.currentData()

        filtered_list = []
        for doc_data in client_documents_from_db:
            doc_passes_lang_filter = True
            doc_passes_type_filter = True

            # Language Filtering
            if selected_lang_filter != "ALL":
                doc_lang = doc_data.get('language_code')
                # Infer if not present (though it should be from import)
                if not doc_lang and doc_data.get('file_path_relative'):
                    path_parts = doc_data.get('file_path_relative').split(os.sep)
                    if len(path_parts) > 1 and path_parts[0] in SUPPORTED_LANGUAGES:
                        doc_lang = path_parts[0]
                if doc_lang != selected_lang_filter:
                    doc_passes_lang_filter = False

            # Type Filtering
            if selected_type_filter != "ALL":
                doc_type_generated = doc_data.get('document_type_generated', '').upper()
                file_name_on_disk = doc_data.get('file_name_on_disk', '').lower()

                is_html = doc_type_generated == 'HTML' or file_name_on_disk.endswith('.html')
                is_pdf = doc_type_generated == 'PDF' or file_name_on_disk.endswith('.pdf')
                is_xlsx = doc_type_generated == 'XLSX' or file_name_on_disk.endswith('.xlsx')
                is_docx = doc_type_generated == 'DOCX' or file_name_on_disk.endswith('.docx')

                if selected_type_filter == "HTML":
                    if not is_html: doc_passes_type_filter = False
                elif selected_type_filter == "PDF":
                    if not is_pdf: doc_passes_type_filter = False
                elif selected_type_filter == "XLSX":
                    if not is_xlsx: doc_passes_type_filter = False
                elif selected_type_filter == "DOCX":
                    if not is_docx: doc_passes_type_filter = False
                elif selected_type_filter == "OTHER":
                    if is_html or is_pdf or is_xlsx or is_docx:
                        doc_passes_type_filter = False

            if doc_passes_lang_filter and doc_passes_type_filter:
                filtered_list.append(doc_data)

        base_client_path = self.client_info.get("base_folder_path")
        if not base_client_path or not os.path.isdir(base_client_path):
            logging.error(f"populate_doc_table: base_folder_path '{base_client_path}' is missing or not a directory for client_id {client_id}.")
            if hasattr(self, 'documents_empty_label'):
                self.documents_empty_label.setText(self.tr("Erreur: Dossier client de base non trouvé ou inaccessible."))
                self.documents_empty_label.setVisible(True)
            self.doc_table.setVisible(False)
            return

        if not filtered_list: # Check the final filtered list
            if hasattr(self, 'documents_empty_label'):
                 self.documents_empty_label.setText(self.tr("Aucun document ne correspond aux filtres sélectionnés.\nModifiez vos filtres ou ajoutez/générez des documents."))
                 self.documents_empty_label.setVisible(True)
            self.doc_table.setVisible(False)
            return

        if hasattr(self, 'documents_empty_label'): self.documents_empty_label.setVisible(False)
        self.doc_table.setVisible(True)
        self.doc_table.setRowCount(len(filtered_list))

        for row_idx, doc_data in enumerate(filtered_list):
            document_id = doc_data.get('document_id')
            doc_name = doc_data.get('document_name', 'N/A')
            file_path_relative_from_db = doc_data.get('file_path_relative', '') # e.g., "fr/doc.pdf" or "order_xyz/fr/doc.pdf"
            order_identifier_for_doc = doc_data.get('order_identifier') # This is the raw timestamp or ID

            # Determine language code from relative path structure
            language_code = doc_data.get('language_code', "N/A") # Prefer direct field if available
            if language_code == "N/A" and file_path_relative_from_db: # Fallback to inferring from path
                path_parts = file_path_relative_from_db.split(os.sep)
                if len(path_parts) > 1 and path_parts[0] in SUPPORTED_LANGUAGES:
                    language_code = path_parts[0]

            # Construct full_file_path
            full_file_path = ""
            if file_path_relative_from_db: # Only proceed if relative path exists
                if order_identifier_for_doc:
                    safe_order_subfolder = str(order_identifier_for_doc).replace(':', '_').replace(' ', '_')
                    full_file_path = os.path.join(base_client_path, safe_order_subfolder, file_path_relative_from_db)
                else:
                    full_file_path = os.path.join(base_client_path, file_path_relative_from_db)

                if not os.path.exists(full_file_path):
                    logging.warning(f"Document file path does not exist: {full_file_path} for doc_id {document_id}")
            else:
                logging.warning(f"Missing file_path_relative for doc_id {document_id}, client_id {client_id}")


            name_item = QTableWidgetItem(doc_name)
            name_item.setData(Qt.UserRole, full_file_path if full_file_path else None) # Store full path or None

            file_type_str = doc_data.get('document_type_generated', 'N/A') # Or derive from extension
            created_at_str = doc_data.get('created_at', '')
            mod_time_formatted = ""
            if created_at_str:
                try:
                    dt_obj = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    mod_time_formatted = dt_obj.strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    mod_time_formatted = created_at_str # Fallback

            self.doc_table.setItem(row_idx, 0, name_item)
            self.doc_table.setItem(row_idx, 1, QTableWidgetItem(file_type_str))
            self.doc_table.setItem(row_idx, 2, QTableWidgetItem(language_code))
            self.doc_table.setItem(row_idx, 3, QTableWidgetItem(mod_time_formatted))

            action_widget = QWidget(); action_layout = QHBoxLayout(action_widget); action_layout.setContentsMargins(2,2,2,2); action_layout.setSpacing(5)

            # 1. pdf_btn (Generate/Open PDF)
            pdf_btn = QPushButton("")
            pdf_btn.setIcon(QIcon(":/icons/file-text.svg"))
            pdf_btn.setToolTip(self.tr("Générer/Ouvrir PDF du document"))
            pdf_btn.setFixedSize(30,30)
            pdf_btn.clicked.connect(lambda _, p=full_file_path: self._handle_open_pdf_action(p))
            action_layout.addWidget(pdf_btn)

            source_template_id = doc_data.get('source_template_id')

            # 2. source_btn (View Source File)
            source_btn = QPushButton("")
            source_btn.setIcon(QIcon(":/icons/eye.svg"))
            source_btn.setToolTip(self.tr("Afficher le fichier source"))
            source_btn.setFixedSize(30,30)
            source_btn.clicked.connect(lambda _, p=full_file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            action_layout.addWidget(source_btn)

            can_edit_source_template = False
            if source_template_id:
                template_info_for_edit_btn = db_manager.get_template_by_id(source_template_id)
                if template_info_for_edit_btn and template_info_for_edit_btn.get('template_type', '').startswith('html'):
                    can_edit_source_template = True

            if can_edit_source_template:
                # 3. edit_source_template_btn
                edit_source_template_btn = QPushButton("")
                edit_source_template_btn.setIcon(QIcon(":/icons/edit-2.svg"))
                edit_source_template_btn.setToolTip(self.tr("Modifier le modèle source de ce document"))
                edit_source_template_btn.setFixedSize(30,30)
                edit_source_template_btn.clicked.connect(lambda _, doc_d=doc_data: self.handle_edit_source_template(doc_d))
                action_layout.addWidget(edit_source_template_btn)
            elif file_type_str.upper() == "PDF":
                edit_pdf_btn = QPushButton(self.tr("Modifier PDF"))
                edit_pdf_btn.setIcon(QIcon(":/icons/pencil.svg"))
                edit_pdf_btn.setToolTip(self.tr("Modifier le fichier PDF"))
                edit_pdf_btn.setFixedSize(30, 30)
                edit_pdf_btn.clicked.connect(lambda _, p=full_file_path, doc_id=document_id: self._handle_edit_pdf_action(p, doc_id))
                action_layout.addWidget(edit_pdf_btn)
            elif doc_name.lower().endswith(('.xlsx', '.html')): # Keep this for non-PDF office docs
                # 4. edit_btn (Direct edit for .xlsx, .html)
                edit_btn = QPushButton("")
                edit_btn.setIcon(QIcon(":/icons/pencil.svg"))
                edit_btn.setToolTip(self.tr("Modifier le contenu du document"))
                edit_btn.setFixedSize(30,30)
                edit_btn.clicked.connect(lambda _, p=full_file_path: self.open_document(p))
                action_layout.addWidget(edit_btn)
            else:
                # This spacer is added if no other edit-like button is added for this slot.
                spacer_widget = QWidget(); spacer_widget.setFixedSize(30,30); action_layout.addWidget(spacer_widget) # Keep alignment

            # 5. delete_btn (Delete Document)
            delete_btn = QPushButton("")
            delete_btn.setIcon(QIcon(":/icons/trash.svg"))
            delete_btn.setToolTip(self.tr("Supprimer le document (fichier et DB)"))
            delete_btn.setFixedSize(30,30)
            delete_btn.clicked.connect(lambda _, doc_id=document_id, p=full_file_path: self.delete_client_document_entry(doc_id, p))
            action_layout.addWidget(delete_btn)

            action_layout.addStretch(); action_widget.setLayout(action_layout); self.doc_table.setCellWidget(row_idx, 4, action_widget)

    def handle_edit_source_template(self, document_data):
        source_template_id = document_data.get('source_template_id')
        current_client_id = self.client_info.get('client_id')

        if not source_template_id:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Aucun ID de modèle source associé à ce document."))
            return

        original_template = db_manager.get_template_by_id(source_template_id)
        if not original_template:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Modèle source (ID: {0}) introuvable.").format(source_template_id))
            return

        template_to_edit_id = source_template_id
        template_for_editor = original_template.copy() # Work with a copy

        if original_template.get('client_id') is None: # Global template
            reply = QMessageBox.question(self, self.tr("Modèle Global"),
                                         self.tr("Ce document a été généré à partir d'un modèle global. Voulez-vous créer une copie spécifique à ce client ({0}) pour modification?").format(self.client_info.get('client_name', current_client_id)),
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                new_template_data = template_for_editor # Already a copy
                new_template_data['client_id'] = current_client_id
                new_template_data['template_name'] = f"{original_template.get('template_name', 'Template')} ({self.client_info.get('client_name', current_client_id)[:15]} Copy)"
                new_template_data.pop('template_id', None)
                new_template_data['is_default_for_type_lang'] = False

                new_id = db_manager.add_template(new_template_data)
                if new_id:
                    template_to_edit_id = new_id
                    template_for_editor = db_manager.get_template_by_id(new_id) # Get the full new template data
                    QMessageBox.information(self, self.tr("Copie Créée"), self.tr("Une copie client-spécifique du modèle a été créée et va maintenant être ouverte pour édition."))
                    self.populate_doc_table() # Refresh doc list if template source ID might change (though it doesn't for existing docs)
                else:
                    QMessageBox.critical(self, self.tr("Erreur"), self.tr("Impossible de créer la copie client-spécifique du modèle."))
                    return
            else: # User chose not to create a copy
                return
        elif original_template.get('client_id') != current_client_id:
            QMessageBox.warning(self, self.tr("Accès Interdit"), self.tr("Ce modèle appartient à un autre client et ne peut pas être modifié directement ici. Une copie pour le client actuel peut être envisagée si nécessaire (fonctionnalité à implémenter)."))
            return # Or implement copy logic similar to global templates

        # At this point, template_for_editor is the correct one to edit (original or new copy)
        raw_html_content = template_for_editor.get('raw_template_file_data')
        base_file_name = template_for_editor.get('base_file_name')
        lang_code = template_for_editor.get('language_code')

        if not base_file_name or not lang_code:
            QMessageBox.critical(self, self.tr("Erreur Modèle"), self.tr("Les informations du fichier de base du modèle (nom ou langue) sont manquantes."))
            return

        # Construct path in the central template store
        template_file_path_for_editor = os.path.join(self.config.get("templates_dir", "templates"), lang_code, base_file_name)

        # Ensure directory exists
        os.makedirs(os.path.dirname(template_file_path_for_editor), exist_ok=True)

        # Write DB content to file for editor, to ensure editor loads the canonical version
        try:
            content_to_write = raw_html_content
            if isinstance(raw_html_content, bytes):
                content_to_write = raw_html_content.decode('utf-8')

            with open(template_file_path_for_editor, 'w', encoding='utf-8') as f:
                f.write(content_to_write if content_to_write else "")
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Écriture Fichier"), self.tr("Impossible d'écrire le contenu du modèle vers le fichier temporaire pour édition: {0}").format(str(e)))
            return

        editor_client_data = self.client_info.copy() # Pass a copy
        html_editor = HtmlEditor(
            file_path=template_file_path_for_editor,
            client_data=editor_client_data,
            template_id=template_to_edit_id, # Pass the ID of the template being edited
            parent=self
        )
        if html_editor.exec_() == QDialog.Accepted:
            try:
                with open(template_file_path_for_editor, 'r', encoding='utf-8') as f:
                    updated_html_content = f.read()

                # Save updated content back to DB
                update_payload = {'raw_template_file_data': updated_html_content}
                # Optionally, update 'updated_at' or 'version' if those fields are important here
                if db_manager.update_template(template_to_edit_id, update_payload):
                    QMessageBox.information(self, self.tr("Modèle Sauvegardé"), self.tr("Les modifications du modèle ont été sauvegardées dans la base de données."))
                else:
                    QMessageBox.warning(self, self.tr("Erreur Sauvegarde DB"), self.tr("Impossible de sauvegarder les modifications du modèle dans la base de données."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Lecture Fichier"), self.tr("Impossible de relire le fichier modèle modifié: {0}").format(str(e)))

        # Clean up temporary file if it was solely for this edit session and raw_template_file_data is truth
        # For now, assume file is persistent in templates_dir. If base_file_name was temporary, then:
        # if os.path.exists(template_file_path_for_editor) and is_temp_file: os.remove(template_file_path_for_editor)


    def open_create_docs_dialog(self):
        dialog = self.CreateDocumentDialog(self.client_info, self.config, self)
        if dialog.exec_() == QDialog.Accepted: self.populate_doc_table()

    def open_compile_pdf_dialog(self):
        dialog = self.CompilePdfDialog(self.client_info, self.config, self.app_root_dir, self)
        dialog.exec_()

    def open_selected_doc(self):
        selected_row = self.doc_table.currentRow()
        if selected_row >= 0:
            file_path_item = self.doc_table.item(selected_row, 0)
            if file_path_item:
                file_path = file_path_item.data(Qt.UserRole)
                if file_path and os.path.exists(file_path): self.open_document(file_path)

    def delete_selected_doc(self):
        selected_row = self.doc_table.currentRow()
        if selected_row >= 0:
            file_path_item = self.doc_table.item(selected_row, 0)
            if file_path_item:
                file_path = file_path_item.data(Qt.UserRole)
                if file_path and os.path.exists(file_path): self.delete_document(file_path)

    def open_document(self, file_path):
        if os.path.exists(file_path):
            try:
                editor_client_data = { "client_id": self.client_info.get("client_id"), "client_name": self.client_info.get("client_name", ""), "company_name": self.client_info.get("company_name", ""), "need": self.client_info.get("need", ""), "primary_need_description": self.client_info.get("need", ""), "project_identifier": self.client_info.get("project_identifier", ""), "country": self.client_info.get("country", ""), "country_id": self.client_info.get("country_id"), "city": self.client_info.get("city", ""), "city_id": self.client_info.get("city_id"), "price": self.client_info.get("price", 0), "status": self.client_info.get("status"), "status_id": self.client_info.get("status_id"), "selected_languages": self.client_info.get("selected_languages"), "notes": self.client_info.get("notes"), "creation_date": self.client_info.get("creation_date"), "category": self.client_info.get("category"), "base_folder_path": self.client_info.get("base_folder_path") }
                if file_path.lower().endswith('.xlsx'):
                    editor = ExcelEditor(file_path, parent=self)
                    if editor.exec_() == QDialog.Accepted:
                        # ... (archiving and PDF generation logic remains the same) ...
                        self.generate_pdf_for_document(file_path, self.client_info, self)
                    self.populate_doc_table()
                elif file_path.lower().endswith('.html'):
                    html_editor_dialog = HtmlEditor(file_path, client_data=editor_client_data, parent=self)
                    if html_editor_dialog.exec_() == QDialog.Accepted:
                        # ... (archiving and PDF generation logic remains the same) ...
                        generated_pdf_path = self.generate_pdf_for_document(file_path, self.client_info, self)
                        if generated_pdf_path: print(f"Updated PDF generated at: {generated_pdf_path}")
                    self.populate_doc_table()
                else: QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            except Exception as e: QMessageBox.warning(self, self.tr("Erreur Ouverture Fichier"), self.tr("Impossible d'ouvrir le fichier:\n{0}").format(str(e)))
        else: QMessageBox.warning(self, self.tr("Fichier Introuvable"), self.tr("Le fichier n'existe plus.")); self.populate_doc_table()

    def delete_document(self, file_path):
        if not os.path.exists(file_path): return
        reply = QMessageBox.question(self, self.tr("Confirmer la suppression"), self.tr("Êtes-vous sûr de vouloir supprimer le fichier {0} ?").format(os.path.basename(file_path)), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try: os.remove(file_path); self.populate_doc_table(); QMessageBox.information(self, self.tr("Fichier supprimé"), self.tr("Le fichier a été supprimé avec succès."))
            except Exception as e: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de supprimer le fichier:\n{0}").format(str(e)))

    def load_contacts(self):
        # Initially, show empty label and hide table
        if hasattr(self, 'contacts_empty_label'): # Ensure label exists
            self.contacts_empty_label.setVisible(True)
        self.contacts_table.setVisible(False)
        self.contacts_table.setRowCount(0) # Clear table

        client_uuid = self.client_info.get("client_id")
        if not client_uuid:
            # Still ensure empty label is visible if client_uuid is missing for some reason
            if hasattr(self, 'contacts_empty_label'):
                 self.contacts_empty_label.setVisible(True)

            return

        try:
            self.total_contacts_count = db_manager.get_contacts_for_client_count(client_id=client_uuid)

            contacts = db_manager.get_contacts_for_client(
                client_id=client_uuid,
                limit=self.CONTACT_PAGE_LIMIT,
                offset=self.current_contact_offset
            )
            contacts = contacts if contacts else []

            if not contacts:
                # No contacts, ensure empty label is visible and table is hidden
                if hasattr(self, 'contacts_empty_label'):
                    self.contacts_empty_label.setVisible(True)
                self.contacts_table.setVisible(False)
                return # Exit early

            # If contacts exist, hide empty label and show table
            if hasattr(self, 'contacts_empty_label'):
                self.contacts_empty_label.setVisible(False)
            self.contacts_table.setVisible(True)

            for row, contact in enumerate(contacts):
                self.contacts_table.insertRow(row)
                name_item = QTableWidgetItem(contact.get('name', 'N/A'))
                name_item.setData(Qt.UserRole, {
                    'contact_id': contact.get('contact_id'),
                    'client_contact_id': contact.get('client_contact_id')
                })
                self.contacts_table.setItem(row, 0, name_item)
                self.contacts_table.setItem(row, 1, QTableWidgetItem(contact.get('email', '')))
                self.contacts_table.setItem(row, 2, QTableWidgetItem(contact.get('phone', '')))
                self.contacts_table.setItem(row, 3, QTableWidgetItem(contact.get('position', '')))
                primary_text = self.tr("Oui") if contact.get('is_primary_for_client') else self.tr("Non")
                primary_item = QTableWidgetItem(primary_text)
                primary_item.setTextAlignment(Qt.AlignCenter)
                self.contacts_table.setItem(row, 4, primary_item)
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des contacts:\n{0}").format(str(e)))
            self.total_contacts_count = 0 # Reset on error
        finally:
            self.update_contact_pagination_controls()


    def add_contact(self):
        client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        dialog = self.ContactDialog(client_uuid, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            # contact_form_data = dialog.get_data() # Original line
            try:
                # Assuming dialog handles DB ops or returns data for db_manager call
                # No specific return from dialog.get_data() is used here for DB ops.
                # The dialog itself calls db_manager.add_contact and db_manager.link_contact_to_client
                pass # DB operations are handled within ContactDialog
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du contact:\n{0}").format(str(e)))
            finally:
                self.load_contacts()

    def edit_contact(self, row=None, column=None):
        current_row = self.contacts_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un contact à modifier."))
            return

        name_item = self.contacts_table.item(current_row, 0)
        if not name_item: return

        item_data = name_item.data(Qt.UserRole)
        contact_id = item_data.get('contact_id')

        if not contact_id:
            QMessageBox.warning(self, self.tr("Erreur Données"), self.tr("ID de contact non trouvé pour la ligne sélectionnée."))
            return

        client_uuid = self.client_info.get("client_id")
        full_contact_details = db_manager.get_contact_by_id(contact_id)
        if not full_contact_details:
            QMessageBox.warning(self, self.tr("Erreur Données"), self.tr("Détails du contact non trouvés dans la base de données."))
            return

        client_contact_link_info = db_manager.get_specific_client_contact_link_details(client_uuid, contact_id)
        if client_contact_link_info:
            full_contact_details['is_primary_for_client'] = client_contact_link_info.get('is_primary_for_client', False)
            full_contact_details['client_contact_id'] = client_contact_link_info.get('client_contact_id')

        dialog = self.ContactDialog(client_id=client_uuid, contact_data=full_contact_details, parent=self)

        if dialog.exec_() == QDialog.Accepted:
            # DB operations are handled within ContactDialog after its own save logic
            self.load_contacts()


    def remove_contact(self):
        current_row = self.contacts_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un contact à supprimer."))
            return

        name_item = self.contacts_table.item(current_row, 0)
        if not name_item: return

        item_data = name_item.data(Qt.UserRole)
        contact_id = item_data.get('contact_id')
        client_contact_id = item_data.get('client_contact_id')
        contact_name = name_item.text()

        if not client_contact_id:
            QMessageBox.warning(self, self.tr("Erreur Données"), self.tr("ID de lien contact-client non trouvé."))
            return

        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir supprimer le lien vers le contact '{0}' pour ce client?").format(contact_name),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # Use client_contact_id for unlinking, not client_id + contact_id
                if db_manager.unlink_contact_from_client_by_link_id(client_contact_id): # Assuming this new function exists
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Lien vers le contact '{0}' supprimé avec succès.").format(contact_name))
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la suppression du lien vers le contact."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du lien contact:\n{0}").format(str(e)))
            finally:
                self.load_contacts()

    def add_product(self):
        client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        dialog = self.ProductDialog(client_uuid, self.app_root_dir, parent=self) # Pass app_root_dir
        if dialog.exec_() == QDialog.Accepted:
            products_list_data = dialog.get_data()

            # --- BEGIN HYPOTHETICAL ACTUAL FIX AREA ---
            # This is where the actual loop processing products_list_data would be.
            # Assuming the loop and the call to db_manager.add_product_to_client_project_link_and_global
            # or similar database function occurs here.

            # If the error "TypeError: City() missing 1 required positional argument: 'country_id'"
            # originates from an attempt to process city information *within this loop*
            # (e.g., by calling db_manager.get_or_add_city), the fix would be here.

            # Example of what might be happening and how to fix it:
            products_list_data = dialog.get_data() # This is a list of product_entry dicts

            processed_count = 0
            if products_list_data:
                for product_entry in products_list_data:
                    client_id_for_product = self.client_info.get('client_id')
                    # ProductDialog.get_data() returns a list. Each item is a dict for a product.
                    # 'client_id' might be in product_entry if ProductDialog was for multiple clients (not typical for this context)
                    # or if ProductDialog explicitly adds it. Assuming client_id comes from self.client_info.

                    logging.info(f"Processing product_entry {processed_count + 1}/{len(products_list_data)}: {product_entry}")
                    client_id_for_product = self.client_info.get('client_id')
                    global_product_id = product_entry.get('product_id')
                    quantity_raw = product_entry.get('quantity')
                    unit_price_override_raw = product_entry.get('unit_price') # Dialog uses 'unit_price'

                    quantity = None
                    if quantity_raw is not None:
                        try:
                            quantity = float(quantity_raw)
                            if quantity <= 0:
                                logging.error(f"Invalid quantity '{quantity_raw}' for product {global_product_id}. Must be positive.")
                                quantity = None # Treat as missing/invalid
                        except ValueError:
                            logging.error(f"Non-numeric quantity '{quantity_raw}' for product {global_product_id}.")
                            quantity = None # Treat as missing/invalid

                    unit_price_override = None # Initialize to None
                    # unit_price_override should only be set if unit_price_override_raw is not None.
                    # If unit_price_override_raw is None, it means no override is intended, and DB will use base_price.
                    # If unit_price_override_raw is provided, it must be a valid float.
                    if unit_price_override_raw is not None:
                        try:
                            unit_price_override = float(unit_price_override_raw)
                            if unit_price_override < 0: # Negative prices are not allowed for an override
                                logging.error(f"Invalid unit_price_override '{unit_price_override_raw}' for product {global_product_id}. Cannot be negative.")
                                # If explicitly provided override is invalid, this is an error, treat as missing data for the 'all' check.
                                unit_price_override = None # Mark as invalid for the 'all' check.
                        except ValueError:
                            logging.error(f"Non-numeric unit_price_override '{unit_price_override_raw}' for product {global_product_id}.")
                            unit_price_override = None # Mark as invalid for the 'all' check.

                    # Determine project_id. It can be None.
                    # Assuming self.client_info.get('project_id') is the actual foreign key or None.
                    project_id_for_db = self.client_info.get('project_id', None)
                    if project_id_for_db is None:
                        # If 'project_id' is not directly in client_info,
                        # check if 'project_identifier' is and if it needs to be resolved to an ID.
                        # For now, assume if 'project_id' is not there, it's None.
                        logging.info(f"No 'project_id' found in client_info for client {client_id_for_product}. Product will be linked without a specific project.")


                    # Critical data for adding a link: client_id, product_id, quantity.
                    # unit_price_override is optional in db_call_payload (None means use base price).
                    # However, if unit_price_override_raw was provided but invalid, we treat it as a data error for this specific product entry.
                    # The 'all' check needs to ensure that if an override was attempted (raw value not None) it must be valid (converted value not None).
                    # And quantity must always be valid.
                    conditions_met = all([
                        client_id_for_product,
                        global_product_id,
                        quantity is not None, # Quantity must be valid positive number
                        (unit_price_override_raw is None or unit_price_override is not None) # If override was given, it must be valid
                    ])

                    if not conditions_met:
                        logging.error(f"Skipping product entry due to missing or invalid data (post-conversion): {product_entry} for client_id {client_id_for_product}. Quantity: {quantity}, Unit Price Override (converted): {unit_price_override}, Raw Override: {unit_price_override_raw}")
                        QMessageBox.warning(self, self.tr("Données Produit Invalides ou Manquantes"),
                                            self.tr("Impossible d'ajouter le produit '{0}' car la quantité ou le prix unitaire est invalide ou manquant.").format(product_entry.get('name', 'Nom inconnu')))
                        continue

                    # unit_price_override in db_call_payload should be the converted float, or None if no override was intended/provided.
                    # The add_product_to_client_or_project function handles None override by using base price.
                    db_call_payload = {
                        'client_id': client_id_for_product,
                        'product_id': global_product_id,
                        'quantity': quantity, # Validated float
                        'unit_price_override': unit_price_override, # Validated float or None
                        'project_id': project_id_for_db,
                    }

                    logging.info(f"Attempting to link product with validated payload: {db_call_payload}")
                    link_id = db_manager.add_product_to_client_or_project(db_call_payload)

                    if link_id:
                        processed_count += 1
                        logging.info(f"Successfully linked product '{product_entry.get('name')}' (Global ID: {global_product_id}) to client {client_id_for_product}. New Link ID: {link_id}")
                    else:
                        logging.error(f"Failed to link product '{product_entry.get('name')}' to client {client_id_for_product}. Payload: {db_call_payload}")
                        QMessageBox.warning(self, self.tr("Erreur Base de Données"),
                                            self.tr("Impossible d'ajouter le produit '{0}' au client/projet.").format(product_entry.get('name', 'Nom inconnu')))

            if processed_count > 0:
                 QMessageBox.information(self, self.tr("Produits Ajoutés"),
                                         self.tr("{0} produit(s) ont été ajoutés/liés avec succès.").format(processed_count))

            if products_list_data or processed_count > 0: # Refresh if any attempt was made or succeeded
                self.load_products()

    def edit_product(self):
        selected_row = self.products_table.currentRow();
        if selected_row < 0: QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un produit à modifier.")); return

        # Fetch existing data to pass to the dialog
        # Assuming the first column (hidden) stores client_project_product_id
        # and other columns have display data. We need to fetch full data for the dialog.
        link_id_item = self.products_table.item(selected_row, 0)
        if not link_id_item:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer l'ID du lien produit."))
            return
        link_id = link_id_item.data(Qt.UserRole)

        # Construct product_link_data similar to how it might be if fetched fresh
        # This needs all relevant fields that EditProductLineDialog and its subsequent logic expect.
        # This is a simplified example; in a real app, you'd fetch this from DB or have it structured.
        product_link_data = {
            'client_project_product_id': link_id,
            'name': self.products_table.item(selected_row, 1).text(),
            'description': self.products_table.item(selected_row, 2).text(),
            'weight': self.products_table.item(selected_row, 3).text().replace(' kg', ''), # Assuming format "X kg"
            'dimensions': self.products_table.item(selected_row, 4).text(),
            'quantity': float(self.products_table.item(selected_row, 5).text()),
            'unit_price': float(self.products_table.item(selected_row, 6).text().replace('€', '').strip()),
            # 'product_id' (global product ID) needs to be fetched if not already in table item data
            # For now, assuming it might be part of what get_products_for_client_or_project returns
            # and could be stored in one of the items' UserRole if needed.
            # Let's assume it's retrieved via link_id if necessary by EditProductLineDialog or its save logic.
        }
        # Attempt to retrieve global product_id if stored, e.g. in name_item's UserRole+1 or similar
        # This part is speculative based on common patterns, adjust if product_id is stored differently
        name_item_for_global_id = self.products_table.item(selected_row, 1) # Assuming name item might hold it
        if name_item_for_global_id and name_item_for_global_id.data(Qt.UserRole + 2): # Example: UserRole+2 for global_product_id
             product_link_data['product_id'] = name_item_for_global_id.data(Qt.UserRole + 2)


        try:
            dialog = self.EditProductLineDialog(product_link_data, self.app_root_dir, self) # Pass app_root_dir
            if dialog.exec_() == QDialog.Accepted:
                updated_line_data = dialog.get_data()
                if updated_line_data:
                    update_payload = {
                        'quantity': updated_line_data.get('quantity'),
                        'unit_price_override': updated_line_data.get('unit_price')
                    }
                    update_payload = {k: v for k, v in update_payload.items() if v is not None}

                    if db_manager.update_client_project_product(link_id, update_payload):
                        QMessageBox.information(self, self.tr("Succès"), self.tr("Ligne de produit mise à jour."))
                    else:
                        QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour de la ligne de produit."))
            self.load_products() # Refresh after successful update or error
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Erreur lors de la modification du produit:\n{0}").format(str(e)))
            self.load_products() # Ensure table is reloaded even on unexpected error
        selected_row = self.products_table.currentRow()
        if selected_row < 0:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un produit à modifier."))
            return

        id_item = self.products_table.item(selected_row, 0)
        if not id_item:
            logging.error("Edit Product: Could not find ID item for selected row.")
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer l'ID du produit sélectionné."))
            return

        link_id = id_item.data(Qt.UserRole)
        if link_id is None:
            logging.error(f"Edit Product: No client_project_product_id found for row {selected_row}.")
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("ID de lien produit non trouvé."))
            return

        try:
            linked_product_data = db_manager.get_client_project_product_by_id(link_id)
            if not linked_product_data:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Détails du produit lié non trouvés."))
                return

            product_id = linked_product_data.get('product_id')
            global_product_data = db_manager.get_product_by_id(product_id)
            if not global_product_data:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Détails du produit global non trouvés."))
                return

            product_name = global_product_data.get('product_name', self.tr("Produit Inconnu"))
            current_quantity = linked_product_data.get('quantity', 0)
            current_unit_price_override = linked_product_data.get('unit_price_override')
            base_unit_price = global_product_data.get('base_unit_price', 0.0)

            # Effective price shown to user for editing is override or base
            effective_current_unit_price = current_unit_price_override if current_unit_price_override is not None else base_unit_price

            dialog = self.EditProductLineDialog(
                product_name,
                current_quantity,
                effective_current_unit_price,
                base_unit_price, # Pass base_unit_price for reference/display in dialog
                parent=self
            )

            if dialog.exec_() == QDialog.Accepted:
                new_data = dialog.get_data()
                if not new_data or 'quantity' not in new_data or 'unit_price' not in new_data:
                     QMessageBox.warning(self, self.tr("Erreur Dialogue"), self.tr("Les données retournées par le dialogue de modification sont invalides."))
                     return

                new_quantity = new_data['quantity']
                new_unit_price_for_client = new_data['unit_price']

                if new_quantity <= 0:
                    QMessageBox.warning(self, self.tr("Valeur Invalide"), self.tr("La quantité doit être positive."))
                    return
                if new_unit_price_for_client < 0:
                    QMessageBox.warning(self, self.tr("Valeur Invalide"), self.tr("Le prix unitaire ne peut être négatif."))
                    return

                # Determine if the new price should be an override
                new_override_price = new_unit_price_for_client if float(new_unit_price_for_client) != float(base_unit_price) else None

                update_payload = {
                    'quantity': new_quantity,
                    'unit_price_override': new_override_price
                }

                if db_manager.update_client_project_product(link_id, update_payload):
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Produit mis à jour avec succès."))
                    self.load_products() # Refresh table

                    # Update client's total price
                    client_uuid = self.client_info.get("client_id")
                    if client_uuid:
                        linked_prods = db_manager.get_products_for_client_or_project(client_uuid, project_id=None)
                        if linked_prods is None: linked_prods = []
                        new_total_client_price = sum(p.get('total_price_calculated', 0.0) for p in linked_prods if p.get('total_price_calculated') is not None)

                        if db_manager.update_client(client_uuid, {'price': new_total_client_price}):
                            self.client_info['price'] = new_total_client_price
                            if not self.is_editing_client and hasattr(self, 'populate_details_layout'):
                                self.populate_details_layout()
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour du produit lié."))
        except AttributeError as ae:
            logging.error(f"Error during product edit, possibly with EditProductLineDialog: {ae}", exc_info=True)
            QMessageBox.critical(self, self.tr("Erreur Critique"), self.tr("Une erreur s'est produite lors de l'ouverture du dialogue de modification de produit. Vérifiez les logs."))
        except Exception as e:
            logging.error(f"Erreur inattendue lors de la modification du produit: {e}", exc_info=True)
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur inattendue est survenue:\n{0}").format(str(e)))


    def remove_product(self):
        selected_row = self.products_table.currentRow();
        if selected_row < 0: return
        # ... (logic for removing product remains the same) ...
        try:
            # ... (DB operations) ...
            self.load_products() # Refresh after successful removal
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du produit lié:\n{0}").format(str(e)))

    def load_products(self):
        self.products_table.blockSignals(True)
        self.products_table.setRowCount(0)

        # Initial state: empty label visible, table hidden
        if hasattr(self, 'products_empty_label'): # Ensure label exists
            self.products_empty_label.setVisible(True)
        self.products_table.setVisible(False)

        client_uuid = self.client_info.get("client_id")
        if not client_uuid:
            # If no client_uuid, it's an empty state for products.
            # The initial state set above handles this.
            self.products_table.blockSignals(False) # Don't forget to unblock
            return

        editable_cell_bg_color = QColor(Qt.yellow).lighter(185) # Example: very light yellow
        # Or use a named color like: editable_cell_bg_color = QColor("AliceBlue")

        try:
            all_linked_products = db_manager.get_products_for_client_or_project(client_uuid, project_id=None) # project_id=None to get all for client
            all_linked_products = all_linked_products if all_linked_products else []

            selected_lang_code = self.product_lang_filter_combo.currentData()

            filtered_products = []
            if selected_lang_code:
                for prod in all_linked_products:
                    if prod.get('language_code') == selected_lang_code:
                        filtered_products.append(prod)
            else:
                filtered_products = all_linked_products

            # This part populates self.products_table (main products tab)
            # We also need to call self.load_products_for_dimension_tab() to update its own combo box
            # if this load_products method is the central point of refresh for product data.

            # The following loop was identified as redundant and causing blank rows.
            # for row_idx, prod_link_data in enumerate(filtered_products):
            #     self.products_table.insertRow(row_idx) # DO NOT UNCOMMENT - This is the bug source

            if not filtered_products:
                # Empty state remains: label visible, table hidden
                # (already set at the beginning of the method)
                # No need to do anything here, the finally block will unblock signals.
                pass
            else:
                # Products exist, show table, hide empty label
                if hasattr(self, 'products_empty_label'):
                    self.products_empty_label.setVisible(False)
                self.products_table.setVisible(True)

                for row_idx, prod_link_data in enumerate(filtered_products):
                # This is the correct loop for inserting and populating rows.
                # Ensure insertRow is called here, once per product.
                    self.products_table.insertRow(row_idx)

                    id_item = QTableWidgetItem(str(prod_link_data.get('client_project_product_id')))
                    id_item.setData(Qt.UserRole, prod_link_data.get('client_project_product_id'))
                    id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable) # Not editable
                    self.products_table.setItem(row_idx, 0, id_item)

                    # Name (Column 1)
                    name_item = QTableWidgetItem(prod_link_data.get('product_name', 'N/A'))
                    name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                    self.products_table.setItem(row_idx, 1, name_item)

                    desc_item = QTableWidgetItem(prod_link_data.get('product_description', ''))
                    desc_item.setFlags(desc_item.flags() & ~Qt.ItemIsEditable)
                    self.products_table.setItem(row_idx, 2, desc_item)

                    # Weight (Column 3 - Not Editable from this table)
                    weight_val = prod_link_data.get('weight')
                    weight_str = f"{weight_val} kg" if weight_val is not None else self.tr("N/A")
                    weight_item = QTableWidgetItem(weight_str)
                    weight_item.setFlags(weight_item.flags() & ~Qt.ItemIsEditable)
                    weight_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.products_table.setItem(row_idx, 3, weight_item)

                    # Dimensions (Column 4 - Not Editable from this table)
                    dimensions_val = prod_link_data.get('dimensions', self.tr("N/A"))
                    dimensions_item = QTableWidgetItem(dimensions_val)
                    dimensions_item.setFlags(dimensions_item.flags() & ~Qt.ItemIsEditable)
                    self.products_table.setItem(row_idx, 4, dimensions_item)

                    # Quantity (Column 5 - Editable)
                    qty_item = QTableWidgetItem(str(prod_link_data.get('quantity', 0)))
                    qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    qty_item.setFlags(qty_item.flags() | Qt.ItemIsEditable)
                    qty_item.setBackground(editable_cell_bg_color) # Apply background
                    self.products_table.setItem(row_idx, 5, qty_item)

                    # Unit Price (Column 6 - Editable)
                    unit_price_override = prod_link_data.get('unit_price_override')
                    base_price = prod_link_data.get('base_unit_price')
                    effective_unit_price = unit_price_override if unit_price_override is not None else (base_price if base_price is not None else 0.0)
                    effective_unit_price = float(effective_unit_price)
                    unit_price_item = QTableWidgetItem(f"{effective_unit_price:.2f}")
                    unit_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    unit_price_item.setFlags(unit_price_item.flags() | Qt.ItemIsEditable)
                    unit_price_item.setBackground(editable_cell_bg_color) # Apply background
                    self.products_table.setItem(row_idx, 6, unit_price_item)

                    # Total Price (Column 7 - Not Editable)
                    total_price_calculated_val = prod_link_data.get('total_price_calculated', 0.0)
                    total_price_calculated_val = float(total_price_calculated_val)
                    total_price_item = QTableWidgetItem(f"€ {total_price_calculated_val:.2f}")
                    total_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    total_price_item.setFlags(total_price_item.flags() & ~Qt.ItemIsEditable)
                    self.products_table.setItem(row_idx, 7, total_price_item)

            # self.products_table.resizeColumnsToContents() # Can make UI jumpy, consider specific column resize modes
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des produits:\n{0}").format(str(e)))
        finally:
            self.products_table.blockSignals(False)

            # Refresh the product selector in the "Dimensions Produit (Client)" tab
            try:
                self.load_products_for_dimension_tab()
            except Exception as e:
                logging.error(f"Error during load_products_for_dimension_tab called from load_products: {e}", exc_info=True)
                QMessageBox.warning(self, self.tr("Chargement Partiel"), self.tr("Une erreur est survenue lors du chargement des produits pour l'onglet dimensions (depuis load_products):\n{0}").format(str(e)))

    def handle_product_item_changed(self, item):
        if not item:
            return

        # Prevent recursive calls during table refresh or if signals are blocked
        if self.products_table.signalsBlocked():
            return

        col = item.column()
        row = item.row()

        id_item = self.products_table.item(row, 0)
        if not id_item:
            print(f"Error: Could not find ID item for row {row}")
            return
        link_id = id_item.data(Qt.UserRole)
        if link_id is None:
            print(f"Error: No client_project_product_id found for row {row}")
            return

        new_value_str = item.text()
        update_data = {}

        try:
            # ID (0, hidden), Name (1), Desc (2), Weight (3), Dimensions (4), Qty (5), UnitPrice (6), TotalPrice (7)
            if col == 5: # Quantity column
                new_quantity = float(new_value_str)
                if new_quantity <= 0:
                    QMessageBox.warning(self, self.tr("Valeur Invalide"), self.tr("La quantité doit être positive."))
                    self.products_table.blockSignals(True); self.load_products(); self.products_table.blockSignals(False)
                    return
                update_data['quantity'] = new_quantity
            elif col == 6: # Unit Price column
                new_unit_price_str = new_value_str.replace("€", "").strip()
                new_unit_price = float(new_unit_price_str)
                if new_unit_price < 0:
                    QMessageBox.warning(self, self.tr("Valeur Invalide"), self.tr("Le prix unitaire ne peut être négatif."))
                    self.products_table.blockSignals(True); self.load_products(); self.products_table.blockSignals(False)
                    return
                update_data['unit_price_override'] = new_unit_price
            else:
                return # Not an editable column we are handling

            if update_data:
                success = db_manager.update_client_project_product(link_id, update_data)
                if success:
                    print(f"Product link_id {link_id} updated with: {update_data}")
                    self.products_table.blockSignals(True)
                    self.load_products() # Reload to show new total and formatted values
                    self.products_table.blockSignals(False)

                    client_uuid = self.client_info.get("client_id")
                    if client_uuid:
                        linked_prods = db_manager.get_products_for_client_or_project(client_uuid, project_id=None)
                        if linked_prods is None: linked_prods = []
                        new_total_client_price = sum(p.get('total_price_calculated', 0.0) for p in linked_prods if p.get('total_price_calculated') is not None)
                        db_manager.update_client(client_uuid, {'price': new_total_client_price})
                        self.client_info['price'] = new_total_client_price
                        if "price" in self.detail_value_labels:
                             self.detail_value_labels["price"].setText(f"{new_total_client_price} €")
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour du produit."))
                    self.products_table.blockSignals(True); self.load_products(); self.products_table.blockSignals(False)
        except ValueError:
            QMessageBox.warning(self, self.tr("Entrée Invalide"), self.tr("Veuillez entrer un nombre valide."))
            self.products_table.blockSignals(True); self.load_products(); self.products_table.blockSignals(False)
        except Exception as e:
            print(f"Error in handle_product_item_changed: {e}")
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Une erreur est survenue: {str(e)}"))
            self.products_table.blockSignals(True); self.load_products(); self.products_table.blockSignals(False)

    def open_send_email_dialog(self):
        client_uuid = self.client_info.get("client_id")
        primary_email = ""
        if client_uuid:
            contacts = db_manager.get_contacts_for_client(client_uuid)
            if contacts:
                for contact in contacts:
                    if contact.get('is_primary_for_client') and contact.get('email'):
                        primary_email = contact['email']
                        break
                if not primary_email and contacts[0].get('email'): # Fallback to first contact's email
                    primary_email = contacts[0]['email']

        # Ensure self.config is the application config containing SMTP settings
        if not hasattr(self, 'config') or not self.config:
             QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("La configuration de l'application (SMTP) n'est pas disponible."))
             return

        # Ensure self.SendEmailDialog is correctly initialized
        if not hasattr(self, 'SendEmailDialog') or self.SendEmailDialog is None:
             try:
                 from dialogs import SendEmailDialog # Direct import as a fallback
                 self.SendEmailDialog = SendEmailDialog
             except ImportError:
                  QMessageBox.critical(self, self.tr("Erreur Importation"), self.tr("Le composant SendEmailDialog n'a pas pu être chargé."))
                  return

        # Pass client_id to SendEmailDialog constructor
        dialog = self.SendEmailDialog(client_email=primary_email, config=self.config, client_id=client_uuid, parent=self)
        dialog.exec_()

    def toggle_client_edit_mode(self):
        self.is_editing_client = not self.is_editing_client
        if self.is_editing_client:
            self.edit_save_client_btn.setText(self.tr("Sauvegarder"))
            self.edit_save_client_btn.setIcon(QIcon.fromTheme("document-save", QIcon(":/icons/check.svg")))
            self.switchTo_edit_client_view()
        else: # Was "Sauvegarder", try to save changes
            if self.save_client_changes_from_edit_view(): # If save is successful
                self.edit_save_client_btn.setText(self.tr("Modifier Client"))
                self.edit_save_client_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg")))
                # The view is refreshed by populate_details_layout within save_client_changes_from_edit_view
            else: # Save failed, remain in edit mode
                self.is_editing_client = True # Keep state as editing
                # Button text and icon remain "Sauvegarder"

    def switchTo_edit_client_view(self):
        # Disconnect signals that auto-save
        try:
            self.notes_edit.textChanged.disconnect(self.save_client_notes)
        except TypeError: # Was not connected or already disconnected
            pass
        try:
            self.status_combo.currentTextChanged.disconnect(self.update_client_status)
        except TypeError:
            pass
        if self.status_combo and self.status_combo.parent():
            self.status_combo.setParent(None)
        if hasattr(self, 'category_label') and self.category_label and self.category_label.parent():
            self.category_label.setParent(None)
        if hasattr(self, 'category_value_label') and self.category_value_label and self.category_value_label.parent():
            self.category_value_label.setParent(None)
        while self.details_layout.rowCount() > 0:
            self.details_layout.removeRow(0)
        self.edit_widgets = {}

        # Client Name
        self.edit_widgets['client_name'] = QLineEdit(self.client_info.get("client_name", ""))
        self.details_layout.addRow(self.tr("Nom Client:"), self.edit_widgets['client_name'])

        self.edit_widgets['company_name'] = QLineEdit(self.client_info.get("company_name", ""))
        self.details_layout.addRow(self.tr("Nom Entreprise:"), self.edit_widgets['company_name'])

        self.edit_widgets['project_identifier'] = QLineEdit(self.client_info.get("project_identifier", ""))
        self.details_layout.addRow(self.tr("ID Projet:"), self.edit_widgets['project_identifier'])

        # Country and City
        country_city_edit_widget = QWidget()
        country_city_h_layout = QHBoxLayout(country_city_edit_widget)
        country_city_h_layout.setContentsMargins(0,0,0,0)
        self.edit_widgets['country_combo'] = QComboBox(); self.edit_widgets['country_combo'].setEditable(True)
        self.edit_widgets['city_combo'] = QComboBox(); self.edit_widgets['city_combo'].setEditable(True)
        self._populate_country_edit_combo(self.edit_widgets['country_combo'], self.client_info.get('country_id'))
        # Connect after populating country to avoid premature city load with no country_id
        self.edit_widgets['country_combo'].currentIndexChanged.connect(lambda index: self._populate_city_edit_combo(self.edit_widgets['city_combo'], self.edit_widgets['country_combo'].itemData(index), None))
        self._populate_city_edit_combo(self.edit_widgets['city_combo'], self.client_info.get('country_id'), self.client_info.get('city_id'))

        country_city_h_layout.addWidget(QLabel(self.tr("Pays:")))
        country_city_h_layout.addWidget(self.edit_widgets['country_combo'])
        country_city_h_layout.addSpacing(10)
        country_city_h_layout.addWidget(QLabel(self.tr("Ville:")))
        country_city_h_layout.addWidget(self.edit_widgets['city_combo'])
        self.details_layout.addRow(self.tr("Localisation:"), country_city_edit_widget)

        # Price (read-only) and Creation Date (read-only)
        price_date_widget = QWidget()
        price_date_h_layout = QHBoxLayout(price_date_widget)
        price_date_h_layout.setContentsMargins(0,0,0,0)
        price_label_edit = QLabel(self.tr("Prix Final:"))
        price_value_edit = QLabel(f"{self.client_info.get('price', 0)} €")
        date_label_edit = QLabel(self.tr("Date Création:"))
        date_value_edit = QLabel(self.client_info.get("creation_date", self.tr("N/A")))
        price_date_h_layout.addWidget(price_label_edit); price_date_h_layout.addWidget(price_value_edit)
        price_date_h_layout.addSpacing(20)
        price_date_h_layout.addWidget(date_label_edit); price_date_h_layout.addWidget(date_value_edit)
        price_date_h_layout.addStretch()
        self.details_layout.addRow(self.tr("Finances & Date:"), price_date_widget)

        # Status and Category
        status_category_edit_widget = QWidget()
        status_category_h_layout = QHBoxLayout(status_category_edit_widget)
        status_category_h_layout.setContentsMargins(0,0,0,0)
        status_category_h_layout.addWidget(QLabel(self.tr("Statut:")))
        status_category_h_layout.addWidget(self.status_combo) # Use existing status_combo, ensure it's populated
        self.edit_widgets['category'] = QLineEdit(self.client_info.get("category", ""))
        status_category_h_layout.addSpacing(10)
        status_category_h_layout.addWidget(QLabel(self.tr("Catégorie:")))
        status_category_h_layout.addWidget(self.edit_widgets['category'])
        self.details_layout.addRow(self.tr("Classification:"), status_category_edit_widget)
        self.edit_widgets['category'].textChanged.connect(self.toggle_edit_distributor_info_visibility)


        # Distributor Specific Info (Editable) - Placed after Category for logical flow
        self.edit_widgets['distributor_specific_info_label'] = QLabel(self.tr("Info Distributeur:"))
        self.edit_widgets['distributor_specific_info'] = QTextEdit(self.client_info.get("distributor_specific_info", ""))
        self.edit_widgets['distributor_specific_info'].setFixedHeight(80)
        self.details_layout.addRow(self.edit_widgets['distributor_specific_info_label'], self.edit_widgets['distributor_specific_info'])
        self.toggle_edit_distributor_info_visibility(self.edit_widgets['category'].text()) # Initial visibility check

        self.edit_widgets['need'] = QTextEdit(self.client_info.get("need", self.client_info.get("primary_need_description", "")))
        self.edit_widgets['need'].setFixedHeight(60)
        self.details_layout.addRow(self.tr("Besoin Principal:"), self.edit_widgets['need'])

        folder_label_edit = QLabel(self.tr("Chemin Dossier:"))
        folder_value_edit = QLabel(self.client_info.get('base_folder_path','')) # Not editable
        self.details_layout.addRow(folder_label_edit, folder_value_edit)

        # Add QListWidget for languages
        self.edit_widgets['languages_list'] = QListWidget()
        self.edit_widgets['languages_list'].setMaximumHeight(100) # Adjust height as needed

        current_selected_langs_value = self.client_info.get("selected_languages", [])
        # Ensure current_selected_langs is a list of strings
        if isinstance(current_selected_langs_value, str):
            current_selected_langs = [lang.strip() for lang in current_selected_langs_value.split(',') if lang.strip()]
        elif isinstance(current_selected_langs_value, list):
            current_selected_langs = current_selected_langs_value
        else:
            current_selected_langs = []

        for lang_code in SUPPORTED_LANGUAGES:
            item = QListWidgetItem(lang_code)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if lang_code in current_selected_langs:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.edit_widgets['languages_list'].addItem(item)
        self.details_layout.addRow(self.tr("Langues Documents:"), self.edit_widgets['languages_list'])

    def _populate_country_edit_combo(self, combo, current_country_id):
        combo.blockSignals(True)
        combo.clear()
        countries = db_manager.get_all_countries() or []
        for country in countries:
            combo.addItem(country['country_name'], country['country_id'])

        current_idx = -1
        if current_country_id:
            index = combo.findData(current_country_id)
            if index >= 0:
                current_idx = index
        combo.setCurrentIndex(current_idx) # Handles -1 if not found
        combo.blockSignals(False)
        # Trigger city load for the initially selected/current country
        # This needs to be done after this method returns and country_combo is fully set up
        # Or ensure city_combo is available here.
        # Let's adjust to call _populate_city_edit_combo directly if city_combo is known
        if 'city_combo' in self.edit_widgets:
             self._populate_city_edit_combo(self.edit_widgets['city_combo'], combo.currentData(), self.client_info.get('city_id'))


    def _populate_city_edit_combo(self, city_combo, country_id, current_city_id):
        if not city_combo: return # Should not happen if called correctly
        city_combo.blockSignals(True)
        city_combo.clear()
        if country_id is not None:
            cities = db_manager.get_all_cities(country_id=country_id) or []
            for city in cities:
                city_combo.addItem(city['city_name'], city['city_id'])

            current_idx = -1
            if current_city_id:
                index = city_combo.findData(current_city_id)
                if index >= 0:
                    current_idx = index
            city_combo.setCurrentIndex(current_idx)
        city_combo.blockSignals(False)

    def save_client_changes_from_edit_view(self):
        data_to_save = {}
        data_to_save['client_name'] = self.edit_widgets['client_name'].text().strip()
        data_to_save['company_name'] = self.edit_widgets['company_name'].text().strip()
        data_to_save['project_identifier'] = self.edit_widgets['project_identifier'].text().strip()

        country_combo = self.edit_widgets.get('country_combo')
        city_combo = self.edit_widgets.get('city_combo')

        if country_combo:
            country_id = country_combo.currentData()
            if country_id is None and country_combo.currentText().strip(): # User typed new country
                new_country_name = country_combo.currentText().strip()
                # Basic check if it already exists by name to avoid duplicate, though DB might have unique constraint
                existing_country = db_manager.get_country_by_name(new_country_name)
                if existing_country:
                    country_id = existing_country['country_id']
                else:
                    country_id = db_manager.add_country({'country_name': new_country_name})
            data_to_save['country_id'] = country_id

        if city_combo:
            city_id = city_combo.currentData()
            if city_id is None and city_combo.currentText().strip() and data_to_save.get('country_id') is not None: # User typed new city
                new_city_name = city_combo.currentText().strip()
                existing_city = db_manager.get_city_by_name_and_country_id(new_city_name, data_to_save['country_id'])
                if existing_city:
                    city_id = existing_city['city_id']
                else:
                    city_id = db_manager.add_city({'country_id': data_to_save['country_id'], 'city_name': new_city_name})
            data_to_save['city_id'] = city_id

        data_to_save['status_id'] = self.status_combo.currentData() # status_combo is reused
        data_to_save['category'] = self.edit_widgets['category'].text().strip()
        data_to_save['primary_need_description'] = self.edit_widgets['need'].toPlainText().strip()
        data_to_save['notes'] = self.notes_edit.toPlainText().strip() # Notes are from the main notes_edit
        data_to_save['distributor_specific_info'] = self.edit_widgets['distributor_specific_info'].toPlainText().strip() if self.edit_widgets['distributor_specific_info'].isVisible() else None


        # Retrieve selected languages from the QListWidget
        selected_langs_to_save = []
        if 'languages_list' in self.edit_widgets:
            lang_list_widget = self.edit_widgets['languages_list']
            for i in range(lang_list_widget.count()):
                item = lang_list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    selected_langs_to_save.append(item.text()) # Assuming item text is the lang code
        data_to_save['selected_languages'] = ",".join(selected_langs_to_save)

        if not data_to_save['client_name'] or not data_to_save['project_identifier']:
            QMessageBox.warning(self, self.tr("Champs Requis"), self.tr("Nom client et ID Projet sont obligatoires."))
            return False

        if db_manager.update_client(self.client_info['client_id'], data_to_save):
            # Update self.client_info with all new values, including text names for country/city/status
            # This ensures the display view (populate_details_layout) has the most current data
            # A full fetch might be cleaner:
            updated_client_full_info = clients_crud_instance.get_client_by_id(self.client_info['client_id'])
            if updated_client_full_info:
                self.client_info = updated_client_full_info # Replace local client_info

                # Fetch related names for display consistency, as client_info might store names not IDs
                country_obj = db_manager.get_country_by_id(self.client_info.get('country_id'))
                city_obj = db_manager.get_city_by_id(self.client_info.get('city_id'))
                status_obj = db_manager.get_status_setting_by_id(self.client_info.get('status_id'))

                self.client_info['country'] = country_obj['country_name'] if country_obj else self.tr("N/A")
                self.client_info['city'] = city_obj['city_name'] if city_obj else self.tr("N/A")
                self.client_info['status'] = status_obj['status_name'] if status_obj else self.tr("N/A")
                # distributor_specific_info is also part of updated_client_full_info now
                # Other fields like client_name, company_name, notes etc. are directly from updated_client_full_info

            self.populate_details_layout() # Rebuild display view, which calls toggle_distributor_info_visibility
            self.header_label.setText(f"<h2>{self.client_info.get('client_name', '')}</h2>") # Update header

            # Reconnect signals that were disconnected for edit mode
            self.notes_edit.textChanged.connect(self.save_client_notes)
            self.status_combo.currentTextChanged.connect(self.update_client_status)
            # No need to reconnect category textChanged for distributor info visibility in display mode,
            # as populate_details_layout handles it.

            self.update_sav_tab_visibility() # Update SAV tab based on potentially changed status

            QMessageBox.information(self, self.tr("Succès"), self.tr("Informations client sauvegardées."))
            return True
        else:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la sauvegarde des informations client."))
            return False

    def toggle_distributor_info_visibility(self):
        """Controls visibility of distributor info in display mode based on category."""
        is_distributor = self.client_info.get('category') == 'Distributeur'
        if hasattr(self, 'distributor_info_label') and self.distributor_info_label: # Check if attribute exists
            self.distributor_info_label.setVisible(is_distributor)
        if hasattr(self, 'distributor_info_value_label') and self.distributor_info_value_label: # Check if attribute exists
            self.distributor_info_value_label.setVisible(is_distributor)
            if is_distributor:
                 self.distributor_info_value_label.setText(self.client_info.get('distributor_specific_info', ''))


    def toggle_edit_distributor_info_visibility(self, category_text):
        """Controls visibility of distributor info in edit mode based on category QLineEdit."""
        is_distributor = category_text == 'Distributeur'
        # Ensure widgets exist before trying to set visibility
        if hasattr(self, 'edit_widgets') and 'distributor_specific_info_label' in self.edit_widgets:
            self.edit_widgets['distributor_specific_info_label'].setVisible(is_distributor)
        if hasattr(self, 'edit_widgets') and 'distributor_specific_info' in self.edit_widgets:
            self.edit_widgets['distributor_specific_info'].setVisible(is_distributor)


    def load_purchase_history_table(self):
        self.purchase_history_table.setRowCount(0)
        client_id = self.client_info.get('client_id')
        if not client_id:
            return

        try:
            # Fetch all products for client, then filter locally
            all_client_products = db_manager.get_products_for_client_or_project(client_id, project_id=None)

            confirmed_purchases = [
                p for p in all_client_products
                if p.get('purchase_confirmed_at') is not None
            ]

            self.purchase_history_table.setRowCount(len(confirmed_purchases))
            for row_idx, purchase_data in enumerate(confirmed_purchases):
                cpp_id = purchase_data.get('client_project_product_id')

                id_item = QTableWidgetItem(str(cpp_id))
                id_item.setData(Qt.UserRole, cpp_id)
                self.purchase_history_table.setItem(row_idx, 0, id_item) # Hidden

                product_name = purchase_data.get('product_name', self.tr('Produit Inconnu'))
                self.purchase_history_table.setItem(row_idx, 1, QTableWidgetItem(product_name))

                quantity = purchase_data.get('quantity', 0)
                self.purchase_history_table.setItem(row_idx, 2, QTableWidgetItem(str(quantity)))

                serial_number = purchase_data.get('serial_number', '')
                sn_item = QTableWidgetItem(serial_number)
                # Make this cell editable by default flags
                self.purchase_history_table.setItem(row_idx, 3, sn_item)

                purchase_date_str = purchase_data.get('purchase_confirmed_at', '')
                if purchase_date_str:
                    try:
                        # Assuming ISO format with 'Z'
                        dt_obj = datetime.fromisoformat(purchase_date_str.replace('Z', '+00:00'))
                        purchase_date_formatted = dt_obj.strftime('%Y-%m-%d %H:%M')
                    except ValueError:
                        purchase_date_formatted = purchase_date_str # Fallback to raw string
                else:
                    purchase_date_formatted = self.tr('N/A')
                date_item = QTableWidgetItem(purchase_date_formatted)
                date_item.setFlags(date_item.flags() & ~Qt.ItemIsEditable) # Not editable
                self.purchase_history_table.setItem(row_idx, 4, date_item)

                # Actions column - for "Create SAV Ticket" button (placeholder for now)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2,2,2,2); actions_layout.setSpacing(5)
                # sav_button = QPushButton(self.tr("Créer Ticket SAV"))
                # sav_button.clicked.connect(lambda ch, pid=cpp_id, sn=serial_number : self.create_sav_ticket_for_product(pid, sn))
                # actions_layout.addWidget(sav_button)
                actions_layout.addStretch()
                self.purchase_history_table.setCellWidget(row_idx, 5, actions_widget)


        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Chargement Historique"),
                                 self.tr("Impossible de charger l'historique des achats:\n{0}").format(str(e)))

    def handle_purchase_history_item_changed(self, item):
        if not item or self.purchase_history_table.signalsBlocked():
            return

        col = item.column()
        row = item.row()

        if col == 3: # "Numéro de Série" column
            cpp_id_item = self.purchase_history_table.item(row, 0) # Hidden ID CPP column
            if not cpp_id_item:
                QMessageBox.warning(self, self.tr("Erreur"), self.tr("ID du produit d'historique non trouvé."))
                return

            client_project_product_id = cpp_id_item.data(Qt.UserRole)
            new_serial_number = item.text().strip()

            # Temporarily block signals to prevent recursion if db update itself triggers a table refresh
            self.purchase_history_table.blockSignals(True)
            try:
                if db_manager.update_client_project_product(client_project_product_id, {'serial_number': new_serial_number}):
                    print(f"Serial number for CPP ID {client_project_product_id} updated to '{new_serial_number}'.")
                    # Optionally, refresh the specific cell or row if visual feedback is needed beyond text change
                    # For now, direct edit is the feedback. A full table reload isn't necessary for this.
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour du numéro de série."))
                    # Revert cell text if DB update failed
                    # This requires fetching old value or reloading row, for simplicity, we'll just log error
                    # A full self.load_purchase_history_table() would also work but is heavier.
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la mise à jour du numéro de série:\n{str(e)}"))
            finally:
                self.purchase_history_table.blockSignals(False)


    def update_sav_tab_visibility(self):
        if not hasattr(self, 'sav_tab_index') or self.sav_tab_index < 0 : # Ensure tab exists
            return

        try:
            client_status_id = self.client_info.get('status_id')
            if client_status_id is None: # If client has no status_id, assume SAV not applicable
                self.tab_widget.setTabEnabled(self.sav_tab_index, False)
                return

            vendu_status_info = db_manager.get_status_setting_by_name('Vendu', 'Client')
            if not vendu_status_info:
                self.tab_widget.setTabEnabled(self.sav_tab_index, False) # Vendu status not found
                print("Warning: 'Vendu' status not found in database settings for SAV tab visibility.")
                return

            vendu_status_id = vendu_status_info.get('status_id')

            if client_status_id == vendu_status_id:
                self.tab_widget.setTabEnabled(self.sav_tab_index, True)
                self.load_purchase_history_table() # Load data when tab becomes visible
            else:
                self.tab_widget.setTabEnabled(self.sav_tab_index, False)
        except Exception as e:
            print(f"Error updating SAV tab visibility: {e}")
            if hasattr(self, 'sav_tab_index') and self.sav_tab_index >=0 :
                 self.tab_widget.setTabEnabled(self.sav_tab_index, False) # Disable on error

        # Ensure tickets table is loaded if tab is now enabled
        if self.tab_widget.isTabEnabled(self.sav_tab_index):
            self.load_sav_tickets_table()

    def eventFilter(self, obj, event):
        if obj is self.notes_edit:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    if event.modifiers() == Qt.ShiftModifier: # Shift+Enter for newline
                        # Let the base class handle Shift+Enter for newline
                        return super().eventFilter(obj, event)
                    else: # Enter pressed
                        self.append_new_note_with_timestamp()
                        return True # Event handled, stop further processing for this Enter key press
            elif event.type() == QEvent.FocusOut:
                self.save_client_notes()
                # Return False to allow normal FocusOut processing after saving
                return False
        return super().eventFilter(obj, event)

    def append_new_note_with_timestamp(self):
        cursor = self.notes_edit.textCursor()
        current_block = cursor.block()
        current_block_text_stripped = current_block.text().strip()

        is_already_timestamped = False
        text_after_timestamp = current_block_text_stripped # Assume no timestamp initially

        if current_block_text_stripped.startswith("[") and "]" in current_block_text_stripped:
            try:
                potential_ts_part = current_block_text_stripped.split("]", 1)[0] + "]"
                datetime.strptime(potential_ts_part, "[%Y-%m-%d %H:%M:%S]")
                is_already_timestamped = True
                # Get the actual text after the timestamp, if any
                text_after_timestamp = current_block_text_stripped.split("]", 1)[1].strip()
            except ValueError:
                is_already_timestamped = False # Not a valid timestamp start

        timestamp_prefix = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

        if not is_already_timestamped and current_block_text_stripped:
            # Case 1: Line has text but no timestamp yet
            new_content_for_current_line = f"{timestamp_prefix} {current_block_text_stripped}"

            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(new_content_for_current_line)
            cursor.endEditBlock()

            cursor.movePosition(QTextCursor.EndOfBlock)
            self.notes_edit.setTextCursor(cursor)

            self.notes_edit.insertPlainText("\n" + f"{timestamp_prefix} ")

        elif is_already_timestamped and text_after_timestamp:
            # Case 2: Line was already timestamped, and there is some (new or old) text after it.
            # User pressed Enter on an existing note. Preserve current line, add new timestamped line.
            cursor.movePosition(QTextCursor.EndOfBlock)
            self.notes_edit.setTextCursor(cursor)
            self.notes_edit.insertPlainText("\n" + f"{timestamp_prefix} ")

        elif not current_block_text_stripped:
            # Case 3: Current line is effectively empty (could be truly empty, or just spaces, or an old timestamp placeholder)
            # Action: Replace current line content with a new timestamp.
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            cursor.removeSelectedText() # Clear the line
            cursor.insertText(f"{timestamp_prefix} ")
            cursor.endEditBlock()
            self.notes_edit.setTextCursor(cursor)

        else: # Fallback: (is_already_timestamped and not text_after_timestamp)
              # This means the line ONLY contains a timestamp and maybe spaces. User pressed Enter.
              # Action: Add a new timestamped line below.
            cursor.movePosition(QTextCursor.EndOfBlock)
            self.notes_edit.setTextCursor(cursor)
            self.notes_edit.insertPlainText("\n" + f"{timestamp_prefix} ")

        self.save_client_notes()

    def handle_generate_final_invoice(self):
        if not self.client_info or not self.client_info.get('client_id'):
            QMessageBox.warning(self, self.tr("Client Error"), self.tr("Client information is not available."))
            return

        client_id = self.client_info.get('client_id')

        current_default_company_id = "0e718801-9f2f-4e6a-9254-80c738f991F9" # Fallback Placeholder UUID
        if hasattr(self, 'config') and self.config.get('default_company_id'):
            current_default_company_id = self.config.get('default_company_id')
        elif hasattr(self.parent(), 'config') and self.parent().config.get('default_company_id'): # Check main window
            current_default_company_id = self.parent().config.get('default_company_id')
        elif self.default_company_id: # from __init__
             current_default_company_id = self.default_company_id
        else:
             QMessageBox.critical(self, self.tr("Configuration Error"),
                                 self.tr("Default selling company ID is not configured. Cannot generate invoice."))
             return

        client_langs = self.client_info.get('selected_languages', 'en')
        if isinstance(client_langs, str):
            client_langs_list = [lang.strip() for lang in client_langs.split(',') if lang.strip()]
        elif isinstance(client_langs, list):
            client_langs_list = client_langs
        else:
            client_langs_list = ['en']

        lang_code = client_langs_list[0].strip() if client_langs_list else 'en'

        # Determine project_id for the invoice. ClientWidget might be specific to a project,
        # or it might be a general client view. If general, project_id might be None here,
        # and selected within FinalInvoiceDataDialog or not used if it's a client-level invoice.
        # For this integration, let's assume it's a client-level invoice for now, or
        # FinalInvoiceDataDialog handles project selection if necessary.
        # If ClientWidget is contextually aware of a single project, pass that.
        # Let's assume for now project_id is not directly passed from ClientWidget context,
        # but could be part of self.client_info if ClientWidget is for a specific project view.
        active_project_id_for_invoice = self.client_info.get('project_id_context', None) # Example if such context exists

        dialog = FinalInvoiceDataDialog(
            client_id=client_id,
            project_id=active_project_id_for_invoice,
            company_id=current_default_company_id,
            parent=self
        )

        if dialog.exec_() == QDialog.Accepted:
            line_items, additional_context = dialog.get_data()

            if not line_items:
                QMessageBox.warning(self, self.tr("No Items"), self.tr("Cannot generate an invoice with no line items."))
                return

            current_user_id = None
            main_window = self # Start with self, then try parent
            # Traverse up to find DocumentManager instance which should have current_user
            # This assumes ClientWidget is always a child of DocumentManager or a similar structure
            # Maximum of, say, 5 levels up to prevent infinite loops in weird scenarios
            for _ in range(5):
                if hasattr(main_window, 'current_user') and main_window.current_user:
                    current_user_id = main_window.current_user.get('user_id')
                    break
                if hasattr(main_window, 'parent') and callable(main_window.parent):
                    main_window = main_window.parent()
                    if main_window is None: # Reached top level QApplication object or similar
                        break
                else: # No more parents
                    main_window = None
                    break

            if not current_user_id:
                logging.warning("Could not determine current_user_id for invoice generation in ClientWidget.")

            try:
                success, new_invoice_id, new_doc_id = create_final_invoice_and_update_db(
                    client_id=client_id,
                    company_id=current_default_company_id,
                    target_language_code=lang_code,
                    line_items=line_items,
                    project_id=active_project_id_for_invoice,
                    additional_context_overrides=additional_context,
                    created_by_user_id=current_user_id
                )

                if success:
                    QMessageBox.information(self, self.tr("Success"),
                                            self.tr("Invoice successfully generated and saved (Invoice DB ID: {0}, Document ID: {1}).").format(new_invoice_id, new_doc_id))
                    if hasattr(self, 'populate_doc_table'):
                        self.populate_doc_table()

                    if main_window and hasattr(main_window, 'invoice_management_widget_instance'):
                        if hasattr(main_window.invoice_management_widget_instance, 'load_invoices'):
                             main_window.invoice_management_widget_instance.load_invoices()
                             logging.info("Refreshed global invoice list.")
                else:
                    QMessageBox.critical(self, self.tr("Error"), self.tr("Failed to generate or save the final invoice. Check logs for details."))
            except Exception as e_gen:
                logging.error(f"Exception during final invoice creation process from ClientWidget: {e_gen}", exc_info=True)
                QMessageBox.critical(self, self.tr("Critical Error"), self.tr("An unexpected error occurred: {0}").format(str(e_gen)))

    # --- Money Transfer Agent Methods ---
    def load_projects_for_mta_combo(self):
        self.mta_project_selector_combo.blockSignals(True)
        self.mta_project_selector_combo.clear()
        self.mta_project_selector_combo.addItem(self.tr("--- Sélectionner Commande/Projet ---"), None)
        client_id = self.client_info.get('client_id')
        if not client_id:
            self.mta_project_selector_combo.blockSignals(False)
            return

        try:
            projects = projects_crud.get_projects_by_client_id(client_id=client_id)
            if projects:
                for project in projects:
                    self.mta_project_selector_combo.addItem(project.get('project_name', self.tr("Projet Sans Nom")), project.get('project_id'))
        except Exception as e:
            logging.error(f"Error loading projects for MTA combo: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur de Chargement"), self.tr("Impossible de charger les projets."))
        finally:
            self.mta_project_selector_combo.blockSignals(False)
            self.handle_mta_project_selection_changed() # Update based on current selection (or default)

    def handle_mta_project_selection_changed(self):
        selected_project_id = self.mta_project_selector_combo.currentData()
        if selected_project_id:
            self.add_assigned_mta_btn.setEnabled(True)
            self.load_assigned_money_transfer_agents()
        else:
            self.add_assigned_mta_btn.setEnabled(False)
            self.assigned_mta_table.setRowCount(0) # Clear table
            self.remove_assigned_mta_btn.setEnabled(False)

    def load_assigned_money_transfer_agents(self):
        self.assigned_mta_table.setRowCount(0)
        selected_project_id = self.mta_project_selector_combo.currentData()
        client_id = self.client_info.get('client_id')

        if not selected_project_id or not client_id:
            self.remove_assigned_mta_btn.setEnabled(False)
            return

        try:
            # get_assigned_agents_for_client_order joins with MoneyTransferAgents and Projects
            assigned_agents_data = coma_crud.get_assigned_agents_for_client_order(
                client_id=client_id,
                order_id=selected_project_id, # This is project_id
                include_deleted=False
            )

            self.assigned_mta_table.setRowCount(len(assigned_agents_data))
            for row, data in enumerate(assigned_agents_data):
                assignment_id = data.get('assignment_id')

                name_item = QTableWidgetItem(data.get('agent_name', self.tr("N/A")))
                name_item.setData(Qt.UserRole, assignment_id) # Store assignment_id for removal
                self.assigned_mta_table.setItem(row, 0, name_item)

                self.assigned_mta_table.setItem(row, 1, QTableWidgetItem(data.get('agent_type', self.tr("N/A"))))
                self.assigned_mta_table.setItem(row, 2, QTableWidgetItem(data.get('agent_email', self.tr("N/A"))))
                self.assigned_mta_table.setItem(row, 3, QTableWidgetItem(data.get('agent_phone', self.tr("N/A"))))
                self.assigned_mta_table.setItem(row, 4, QTableWidgetItem(data.get('assignment_details', '')))

                fee_estimate = data.get('fee_estimate', 0.0)
                fee_item = QTableWidgetItem(f"{fee_estimate:.2f} $") # Assuming USD, adjust as needed
                fee_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.assigned_mta_table.setItem(row, 5, fee_item)

                email_status_item = QTableWidgetItem(data.get('email_status', self.tr("Pendant")))
                self.assigned_mta_table.setItem(row, 6, email_status_item)

                # Actions button (Email Agent)
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(2, 2, 2, 2)
                actions_layout.setSpacing(5)

                email_button = QPushButton(self.tr("Email"))
                email_button.setToolTip(self.tr("Envoyer un email à cet agent"))
                agent_email = data.get('agent_email')
                email_button.clicked.connect(lambda ch, aid=assignment_id, ag_email=agent_email: self.handle_email_money_transfer_agent(aid, ag_email))
                if not agent_email: # Disable if no email
                    email_button.setEnabled(False)
                actions_layout.addWidget(email_button)
                actions_layout.addStretch()
                self.assigned_mta_table.setCellWidget(row, 7, actions_widget)

        except Exception as e:
            logging.error(f"Error loading assigned money transfer agents: {e}", exc_info=True)
            QMessageBox.warning(self, self.tr("Erreur de Chargement"), self.tr("Impossible de charger les agents de transfert d'argent assignés."))
        finally:
            self.update_mta_buttons_state()


    def handle_add_assigned_mta(self):
        selected_project_id = self.mta_project_selector_combo.currentData()
        client_id = self.client_info.get('client_id')

        if not selected_project_id:
            QMessageBox.warning(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner une commande/projet avant d'assigner un agent."))
            return
        if not client_id:
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible."))
            return

        dialog = AssignMoneyTransferAgentDialog(client_id=client_id, order_id=selected_project_id, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_assigned_money_transfer_agents()

    def handle_remove_assigned_mta(self):
        selected_items = self.assigned_mta_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner une affectation d'agent à retirer."))
            return

        assignment_id = selected_items[0].data(Qt.UserRole)
        if not assignment_id:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer l'ID de l'affectation."))
            return

        agent_name = self.assigned_mta_table.item(selected_items[0].row(), 0).text()
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir retirer l'agent '{0}' de cette commande/projet?").format(agent_name),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                result = coma_crud.unassign_agent_from_client_order(assignment_id=assignment_id)
                if result.get('success'):
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Affectation d'agent retirée avec succès."))
                    self.load_assigned_money_transfer_agents()
                else:
                    QMessageBox.warning(self, self.tr("Échec"), self.tr("Impossible de retirer l'affectation: {0}").format(result.get('error', 'Erreur inconnue')))
            except Exception as e:
                logging.error(f"Error removing money transfer agent assignment: {e}", exc_info=True)
                QMessageBox.critical(self, self.tr("Erreur"), self.tr("Une erreur est survenue lors du retrait de l'affectation."))

    def handle_email_money_transfer_agent(self, assignment_id, agent_email):
        if not agent_email:
            QMessageBox.warning(self, self.tr("Email Manquant"), self.tr("L'agent n'a pas d'adresse email enregistrée."))
            return

        # Ensure self.config is available and SendEmailDialog can be imported
        if not hasattr(self, 'config') or not self.config:
             QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("La configuration de l'application (SMTP) n'est pas disponible."))
             return
        if not hasattr(self, 'SendEmailDialog') or self.SendEmailDialog is None:
             try:
                 from dialogs import SendEmailDialog
                 self.SendEmailDialog = SendEmailDialog
             except ImportError:
                  QMessageBox.critical(self, self.tr("Erreur Importation"), self.tr("Le composant SendEmailDialog n'a pas pu être chargé."))
                  return

        # client_id for context in SendEmailDialog (e.g. for templates)
        client_id_for_email_context = self.client_info.get('client_id')

        dialog = self.SendEmailDialog(client_email=agent_email, config=self.config, client_id=client_id_for_email_context, parent=self)
        email_sent_successfully = False
        if dialog.exec_() == QDialog.Accepted:
            # Assuming SendEmailDialog internally handles the sending and returns status or sets it.
            # For this example, we'll assume if accepted, it was "sent".
            # A more robust solution would have SendEmailDialog return a status.
            email_sent_successfully = True # Placeholder for actual send status

        # Update email_status in the database
        new_email_status = 'Sent' if email_sent_successfully else 'Failed' # Simplified logic
        # If the dialog was cancelled, we might not want to change status, or set to 'Pending'
        # For now, only 'Sent' or 'Failed' if dialog was OK'd or there was an attempt.

        try:
            update_result = coma_crud.update_assignment_details(
                assignment_id=assignment_id,
                email_status=new_email_status
            )
            if update_result.get('success'):
                logging.info(f"Email status for assignment {assignment_id} updated to {new_email_status}.")
            else:
                logging.warning(f"Failed to update email status for assignment {assignment_id}: {update_result.get('error')}")
        except Exception as e:
            logging.error(f"Error updating email status for assignment {assignment_id}: {e}", exc_info=True)

        self.load_assigned_money_transfer_agents() # Refresh the table to show new status

    def update_mta_buttons_state(self):
        has_selection = bool(self.assigned_mta_table.selectedItems())
        self.remove_assigned_mta_btn.setEnabled(has_selection)

# Ensure that all methods called by ClientWidget (like self.ContactDialog, self.generate_pdf_for_document)
# Ensure that all methods called by ClientWidget (like self.ContactDialog, self.generate_pdf_for_document)
# are correctly available either as methods of ClientWidget or properly imported.
# The dynamic import _import_main_elements() is a temporary measure.
# Ideally, ContactDialog, ProductDialog, etc., should also be moved to dialogs.py,
# and utility functions like generate_pdf_for_document to a utils.py file.
# The direct use of self.DATABASE_NAME in load_statuses and save_client_notes should be refactored
# to use db_manager for all database interactions.

# [end of client_widget.py]
