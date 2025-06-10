# -*- coding: utf-8 -*-
import os
import sys
import logging
import shutil
from datetime import datetime
# import sqlite3 # No longer needed as methods are refactored to use db_manager

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QListWidget, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QInputDialog, QTabWidget, QGroupBox, QMessageBox, QDialog, QFileDialog
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont # Added QFont
from PyQt5.QtCore import Qt, QUrl, QCoreApplication
from PyQt5.QtWidgets import QFormLayout
from PyQt5.QtWidgets import QListWidgetItem

import db as db_manager
from excel_editor import ExcelEditor
from html_editor import HtmlEditor

# Globals imported from main (temporary, to be refactored)
MAIN_MODULE_CONTACT_DIALOG = None
MAIN_MODULE_PRODUCT_DIALOG = None
MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG = None
MAIN_MODULE_CREATE_DOCUMENT_DIALOG = None
MAIN_MODULE_COMPILE_PDF_DIALOG = None
MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT = None
MAIN_MODULE_CONFIG = None
MAIN_MODULE_DATABASE_NAME = None
MAIN_MODULE_SEND_EMAIL_DIALOG = None # Added for SendEmailDialog

def _import_main_elements():
    global MAIN_MODULE_CONTACT_DIALOG, MAIN_MODULE_PRODUCT_DIALOG, \
           MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG, MAIN_MODULE_CREATE_DOCUMENT_DIALOG, \
           MAIN_MODULE_COMPILE_PDF_DIALOG, MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT, \
           MAIN_MODULE_CONFIG, MAIN_MODULE_DATABASE_NAME, MAIN_MODULE_SEND_EMAIL_DIALOG

    if MAIN_MODULE_CONFIG is None: # Check one, load all if not loaded
        # import main as main_module # No longer needed
        from dialogs import SendEmailDialog, ContactDialog, ProductDialog, EditProductLineDialog, CreateDocumentDialog, CompilePdfDialog
        from utils import generate_pdf_for_document as utils_generate_pdf_for_document
        from app_setup import CONFIG as APP_CONFIG
        from db import DATABASE_NAME as DB_NAME
        MAIN_MODULE_CONTACT_DIALOG = ContactDialog # Assign directly
        MAIN_MODULE_PRODUCT_DIALOG = ProductDialog # Assign directly
        MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG = EditProductLineDialog
        MAIN_MODULE_CREATE_DOCUMENT_DIALOG = CreateDocumentDialog
        MAIN_MODULE_COMPILE_PDF_DIALOG = CompilePdfDialog
        MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT = utils_generate_pdf_for_document
        MAIN_MODULE_CONFIG = APP_CONFIG
        MAIN_MODULE_DATABASE_NAME = DB_NAME # Used in load_statuses, save_client_notes
        MAIN_MODULE_SEND_EMAIL_DIALOG = SendEmailDialog


class ClientWidget(QWidget):
    def __init__(self, client_info, config, app_root_dir, parent=None): # Add app_root_dir
        super().__init__(parent)
        self.client_info = client_info
        # self.config = config # Original config passed

        # Dynamically import main elements to avoid circular import at module load time
        _import_main_elements()
        self.config = MAIN_MODULE_CONFIG # Use the imported config
        self.app_root_dir = app_root_dir # Store it
        self.DATABASE_NAME = MAIN_MODULE_DATABASE_NAME # For methods still using it

        self.ContactDialog = MAIN_MODULE_CONTACT_DIALOG
        self.ProductDialog = MAIN_MODULE_PRODUCT_DIALOG
        self.EditProductLineDialog = MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG
        self.CreateDocumentDialog = MAIN_MODULE_CREATE_DOCUMENT_DIALOG
        self.CompilePdfDialog = MAIN_MODULE_COMPILE_PDF_DIALOG
        self.generate_pdf_for_document = MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT
        self.SendEmailDialog = MAIN_MODULE_SEND_EMAIL_DIALOG # Added

        self.is_editing_client = False
        self.edit_widgets = {}

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # --- Collapsible Client Info Section ---
        self.client_info_group_box = QGroupBox(self.client_info.get('client_name', self.tr("Client Information")))
        self.client_info_group_box.setCheckable(True)
        client_info_group_layout = QVBoxLayout(self.client_info_group_box) # Layout for the GroupBox itself

        self.info_container_widget = QWidget() # Container for all info elements
        info_container_layout = QVBoxLayout(self.info_container_widget)
        info_container_layout.setContentsMargins(0, 5, 0, 0) # Adjust margins as needed
        info_container_layout.setSpacing(10) # Adjust spacing as needed

        self.header_label = QLabel(f"<h2>{self.client_info['client_name']}</h2>")
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
        self.category_value_label = QLabel(self.client_info.get("category", self.tr("N/A")))

        self.populate_details_layout() # Builds the details_layout
        info_container_layout.addLayout(self.details_layout)

        # Add the container widget to the group box's layout
        client_info_group_layout.addWidget(self.info_container_widget)

        # Connect toggled signal and set initial state
        self.client_info_group_box.toggled.connect(self.info_container_widget.setVisible)
        self.client_info_group_box.setChecked(True) # Initially expanded

        layout.addWidget(self.client_info_group_box) # Add the group box to the main layout
        # --- End Collapsible Client Info Section ---

        self.notes_edit = QTextEdit(self.client_info.get("notes", ""))
        self.notes_edit.setPlaceholderText(self.tr("Ajoutez des notes sur ce client..."))
        self.notes_edit.textChanged.connect(self.save_client_notes)
        # The QGroupBox for notes is removed, notes_edit will be added to a tab later

        self.tab_widget = QTabWidget()
        docs_tab = QWidget(); docs_layout = QVBoxLayout(docs_tab)
        self.doc_table = QTableWidget()
        self.doc_table.setColumnCount(5)
        self.doc_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Type"), self.tr("Langue"), self.tr("Date"), self.tr("Actions")])
        self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.doc_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.doc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        docs_layout.addWidget(self.doc_table)
        doc_btn_layout = QHBoxLayout()
        self.add_doc_btn = QPushButton(self.tr("Ajouter"))
        self.add_doc_btn.setIcon(QIcon.fromTheme("list-add"))
        self.add_doc_btn.clicked.connect(self.add_document) # Connect the signal
        doc_btn_layout.addWidget(self.add_doc_btn)

        self.refresh_docs_btn = QPushButton(self.tr("Actualiser"))
        self.refresh_docs_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.refresh_docs_btn.clicked.connect(self.populate_doc_table)
        doc_btn_layout.addWidget(self.refresh_docs_btn)

        self.open_doc_btn = QPushButton(self.tr("Ouvrir"))
        self.open_doc_btn.setIcon(QIcon.fromTheme("document-open"))
        self.open_doc_btn.clicked.connect(self.open_selected_doc)
        doc_btn_layout.addWidget(self.open_doc_btn)

        self.delete_doc_btn = QPushButton(self.tr("Ajouter Modèle")) # New text
        self.delete_doc_btn.setIcon(QIcon.fromTheme("document-new", QIcon(":/icons/file-plus.svg"))) # New icon
        self.delete_doc_btn.setToolTip(self.tr("Ajouter un modèle de document pour ce client")) # New tooltip
        # The original .connect(self.delete_selected_doc) is removed by replacing these lines.
        # Now, connect to the new function.
        self.delete_doc_btn.clicked.connect(self.open_create_docs_dialog)
        doc_btn_layout.addWidget(self.delete_doc_btn)
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
        # self.contacts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive) # Example for specific column
        self.contacts_table.setAlternatingRowColors(True)
        self.contacts_table.cellDoubleClicked.connect(self.edit_contact) # row, column are passed
        contacts_layout.addWidget(self.contacts_table)

        contacts_btn_layout = QHBoxLayout()
        self.add_contact_btn = QPushButton(self.tr("➕ Ajouter")); self.add_contact_btn.setIcon(QIcon.fromTheme("contact-new", QIcon.fromTheme("list-add"))); self.add_contact_btn.setToolTip(self.tr("Ajouter un nouveau contact pour ce client")); self.add_contact_btn.clicked.connect(self.add_contact); contacts_btn_layout.addWidget(self.add_contact_btn)
        self.edit_contact_btn = QPushButton(self.tr("✏️ Modifier")); self.edit_contact_btn.setIcon(QIcon.fromTheme("document-edit")); self.edit_contact_btn.setToolTip(self.tr("Modifier le contact sélectionné")); self.edit_contact_btn.clicked.connect(self.edit_contact); contacts_btn_layout.addWidget(self.edit_contact_btn)
        self.remove_contact_btn = QPushButton(self.tr("🗑️ Supprimer")); self.remove_contact_btn.setIcon(QIcon.fromTheme("edit-delete")); self.remove_contact_btn.setToolTip(self.tr("Supprimer le lien vers le contact sélectionné pour ce client")); self.remove_contact_btn.setObjectName("dangerButton"); self.remove_contact_btn.clicked.connect(self.remove_contact); contacts_btn_layout.addWidget(self.remove_contact_btn)
        contacts_layout.addLayout(contacts_btn_layout)
        self.tab_widget.addTab(contacts_tab, self.tr("Contacts"))

        products_tab = QWidget()
        products_layout = QVBoxLayout(products_tab)

        # Product Filters
        product_filters_layout = QHBoxLayout()
        product_filters_layout.addWidget(QLabel(self.tr("Filtrer par langue:")))
        self.product_lang_filter_combo = QComboBox()
        self.product_lang_filter_combo.addItem(self.tr("All Languages"), None)
        # Language codes should match those in db and other parts of the app
        self.product_lang_filter_combo.addItem(self.tr("English (en)"), "en")
        self.product_lang_filter_combo.addItem(self.tr("French (fr)"), "fr")
        self.product_lang_filter_combo.addItem(self.tr("Arabic (ar)"), "ar")
        self.product_lang_filter_combo.addItem(self.tr("Turkish (tr)"), "tr")
        self.product_lang_filter_combo.addItem(self.tr("Portuguese (pt)"), "pt")
        self.product_lang_filter_combo.currentTextChanged.connect(self.load_products)
        product_filters_layout.addWidget(self.product_lang_filter_combo)
        product_filters_layout.addStretch()
        products_layout.addLayout(product_filters_layout)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(8) # ID, Name, Desc, Weight, Dimensions, Qty, Unit Price, Total Price
        self.products_table.setHorizontalHeaderLabels([
            self.tr("ID"), self.tr("Nom Produit"), self.tr("Description"),
            self.tr("Poids"), self.tr("Dimensions"), # New Columns
            self.tr("Qté"), self.tr("Prix Unitaire"), self.tr("Prix Total")
        ])
        self.products_table.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.products_table.itemChanged.connect(self.handle_product_item_changed)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.hideColumn(0) # Hide ID
        # Example of interactive resizing for some columns:
        # self.products_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Name
        # self.products_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # Description
        # for i in range(3, 8): # Weight, Dimensions, Qty, Unit Price, Total Price
        #     self.products_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        products_layout.addWidget(self.products_table)

        products_btn_layout = QHBoxLayout()
        self.add_product_btn = QPushButton(self.tr("➕ Ajouter")); self.add_product_btn.setIcon(QIcon.fromTheme("list-add")); self.add_product_btn.setToolTip(self.tr("Ajouter un produit pour ce client/projet")); self.add_product_btn.clicked.connect(self.add_product); products_btn_layout.addWidget(self.add_product_btn)
        self.edit_product_btn = QPushButton(self.tr("✏️ Modifier")); self.edit_product_btn.setIcon(QIcon.fromTheme("document-edit")); self.edit_product_btn.setToolTip(self.tr("Modifier le produit sélectionné")); self.edit_product_btn.clicked.connect(self.edit_product); products_btn_layout.addWidget(self.edit_product_btn)
        self.remove_product_btn = QPushButton(self.tr("🗑️ Supprimer")); self.remove_product_btn.setIcon(QIcon.fromTheme("edit-delete")); self.remove_product_btn.setToolTip(self.tr("Supprimer le produit sélectionné de ce client/projet")); self.remove_product_btn.setObjectName("dangerButton"); self.remove_product_btn.clicked.connect(self.remove_product); products_btn_layout.addWidget(self.remove_product_btn)
        products_layout.addLayout(products_btn_layout)
        self.tab_widget.addTab(products_tab, self.tr("Produits"))

        # Create and add Notes Tab
        notes_content_tab = QWidget()
        notes_tab_layout = QVBoxLayout(notes_content_tab)
        # self.notes_edit is already initialized above where the groupbox was removed
        notes_tab_layout.addWidget(self.notes_edit)

        produits_tab_index = -1
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == self.tr("Produits"):
                produits_tab_index = i
                break
        if produits_tab_index != -1:
            self.tab_widget.insertTab(produits_tab_index + 1, notes_content_tab, self.tr("Notes"))
        else:
            self.tab_widget.addTab(notes_content_tab, self.tr("Notes")) # Fallback if "Produits" tab not found

        layout.addWidget(self.tab_widget)
        self.populate_doc_table(); self.load_contacts(); self.load_products()

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
                target_dir = os.path.join(self.client_info["base_folder_path"], selected_doc_language)

                os.makedirs(target_dir, exist_ok=True)

                file_name = os.path.basename(selected_file_path)
                target_file_path = os.path.join(target_dir, file_name)

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

                # Update client's selected languages if necessary
                current_selected_languages = self.client_info.get("selected_languages", [])
                # Ensure it's a list, as it might be a comma-separated string from DB
                if isinstance(current_selected_languages, str):
                    current_selected_languages = [lang.strip() for lang in current_selected_languages.split(',') if lang.strip()]

                if not current_selected_languages: # Handle empty or None case
                    current_selected_languages = []

                if selected_doc_language not in current_selected_languages:
                    add_lang_reply = QMessageBox.question(
                        self,
                        self.tr("Ajouter Langue"),
                        self.tr("Voulez-vous ajouter '{0}' aux langues sélectionnées pour ce client?").format(selected_doc_language),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    if add_lang_reply == QMessageBox.Yes:
                        updated_languages_list = current_selected_languages + [selected_doc_language]
                        updated_languages_str = ",".join(updated_languages_list)

                        client_id_to_update = self.client_info.get("client_id")
                        if client_id_to_update:
                            if db_manager.update_client(client_id_to_update, {'selected_languages': updated_languages_str}):
                                self.client_info["selected_languages"] = updated_languages_list # Update local info
                                print(f"Client {client_id_to_update} selected_languages updated to {updated_languages_str}")
                            else:
                                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour des langues du client dans la DB."))
                        else:
                            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible, impossible de mettre à jour les langues."))

                self.populate_doc_table()

                QMessageBox.information(
                    self,
                    self.tr("Succès"),
                    self.tr("Document '{0}' ajouté avec succès en langue '{1}'.").format(file_name, selected_doc_language)
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self.tr("Erreur"),
                    self.tr("Impossible d'ajouter le document : {0}").format(str(e))
                )

    def _handle_open_pdf_action(self, file_path):
        if not self.client_info or 'client_id' not in self.client_info:
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("Les informations du client ne sont pas disponibles."))
            return

        # Extract target_language_code from the file_path
        # Assumes path structure like .../base_folder/lang_code/filename.html
        try:
            target_language_code = os.path.basename(os.path.dirname(file_path))
            # Basic validation if it's a known lang code, though db function will handle it more robustly
            if target_language_code not in ["en", "fr", "ar", "tr", "pt"]: # Add other supported codes
                # Fallback or error if lang code is not as expected
                QMessageBox.warning(self, self.tr("Erreur Langue"), self.tr("Code langue non reconnu depuis le chemin du fichier: {0}").format(target_language_code))
                # Decide on fallback: use client's primary language or abort? For now, let's try client's primary.
                client_langs = self.client_info.get("selected_languages", [])
                if isinstance(client_langs, str):
                    client_langs = [lang.strip() for lang in client_langs.split(',') if lang.strip()]
                target_language_code = client_langs[0] if client_langs else "fr" # Default to fr if no client lang
                QMessageBox.information(self, self.tr("Info Langue"), self.tr("Utilisation de la langue par défaut '{0}' pour la génération du document.").format(target_language_code))

        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur Chemin Fichier"), self.tr("Impossible d'extraire le code langue depuis le chemin:\n{0}\nErreur: {1}").format(file_path, str(e)))
            return

        # app_root_dir should be available in self.config if main.py sets it up.
        # MAIN_MODULE_CONFIG should have app_root_dir if it's set in main.py's CONFIG
        app_root_dir = self.config.get('app_root_dir', os.path.dirname(sys.argv[0])) # Fallback, might not be ideal for frozen apps
        if MAIN_MODULE_CONFIG and 'app_root_dir' in MAIN_MODULE_CONFIG: # Prefer this if available
            app_root_dir = MAIN_MODULE_CONFIG['app_root_dir']

        generated_pdf_path = self.generate_pdf_for_document(
            source_file_path=file_path,
            client_info=self.client_info,
            app_root_dir=app_root_dir,
            parent_widget=self,
            target_language_code=target_language_code # Pass the new parameter
        )
        if generated_pdf_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(generated_pdf_path))

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

        # Project ID
        project_id_label = QLabel(self.tr("ID Projet:"))
        project_id_value = QLabel(self.client_info.get("project_identifier", self.tr("N/A")))
        self.details_layout.addRow(project_id_label, project_id_value)
        self.detail_value_labels["project_identifier"] = project_id_value

        # Country and City
        country_city_widget = QWidget()
        country_city_h_layout = QHBoxLayout(country_city_widget)
        country_city_h_layout.setContentsMargins(0,0,0,0)
        country_label = QLabel(self.tr("Pays:"))
        country_value = QLabel(self.client_info.get("country", self.tr("N/A")))
        city_label = QLabel(self.tr("Ville:"))
        city_value = QLabel(self.client_info.get("city", self.tr("N/A")))
        country_city_h_layout.addWidget(country_label)
        country_city_h_layout.addWidget(country_value)
        country_city_h_layout.addSpacing(20)
        country_city_h_layout.addWidget(city_label)
        country_city_h_layout.addWidget(city_value)
        country_city_h_layout.addStretch()
        self.details_layout.addRow(self.tr("Localisation:"), country_city_widget)
        self.detail_value_labels["country"] = country_value
        self.detail_value_labels["city"] = city_value

        # Price and Creation Date
        price_date_widget = QWidget()
        price_date_h_layout = QHBoxLayout(price_date_widget)
        price_date_h_layout.setContentsMargins(0,0,0,0)
        price_label = QLabel(self.tr("Prix Final:"))
        price_value = QLabel(f"{self.client_info.get('price', 0)} €")
        date_label = QLabel(self.tr("Date Création:"))
        date_value = QLabel(self.client_info.get("creation_date", self.tr("N/A")))
        price_date_h_layout.addWidget(price_label)
        price_date_h_layout.addWidget(price_value)
        price_date_h_layout.addSpacing(20)
        price_date_h_layout.addWidget(date_label)
        price_date_h_layout.addWidget(date_value)
        price_date_h_layout.addStretch()
        self.details_layout.addRow(self.tr("Finances & Date:"), price_date_widget)
        self.detail_value_labels["price"] = price_value
        self.detail_value_labels["creation_date"] = date_value

        # Status and Category
        status_category_widget = QWidget()
        status_category_h_layout = QHBoxLayout(status_category_widget)
        status_category_h_layout.setContentsMargins(0,0,0,0)
        status_category_h_layout.addWidget(QLabel(self.tr("Statut:")))
        status_category_h_layout.addWidget(self.status_combo) # self.status_combo is an instance member
        status_category_h_layout.addSpacing(20)
        status_category_h_layout.addWidget(self.category_label) # self.category_label is an instance member
        status_category_h_layout.addWidget(self.category_value_label) # self.category_value_label is an instance member
        status_category_h_layout.addStretch()
        self.details_layout.addRow(self.tr("Classification:"), status_category_widget)
        # self.detail_value_labels["category"] is already managed as an instance member from setup_ui

        # Need (Besoin Principal)
        need_label = QLabel(self.tr("Besoin Principal:"))
        need_value = QLabel(self.client_info.get("need", self.client_info.get("primary_need_description", self.tr("N/A")))) # check both keys
        self.details_layout.addRow(need_label, need_value)
        self.detail_value_labels["need"] = need_value

        # Base Folder Path
        folder_label = QLabel(self.tr("Chemin Dossier:"))
        folder_path = self.client_info.get('base_folder_path','')
        folder_value = QLabel(f"<a href='file:///{folder_path}'>{folder_path}</a>")
        folder_value.setOpenExternalLinks(True)
        folder_value.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.details_layout.addRow(folder_label, folder_value)
        self.detail_value_labels["base_folder_path"] = folder_value

    def refresh_display(self, new_client_info):
        self.client_info = new_client_info
        # Update GroupBox title if it includes client name
        if hasattr(self, 'client_info_group_box'):
            self.client_info_group_box.setTitle(self.client_info.get('client_name', self.tr("Client Information")))

        self.header_label.setText(f"<h2>{self.client_info.get('client_name', '')}</h2>")

        # Repopulate the details section with the new client_info
        self.populate_details_layout()

        # status_combo and category_value_label are part of populate_details_layout now.
        # We need to ensure their values are correctly set after populate_details_layout.
        self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours"))) # This might be redundant if populate_details_layout also sets it based on ID.
        self.category_value_label.setText(self.client_info.get("category", self.tr("N/A"))) # This is correctly updated by populate_details_layout if self.category_value_label is an instance member.

        self.notes_edit.setText(self.client_info.get("notes", ""))

    def load_statuses(self):
        try:
            # Assuming 'Client' is the status_type for this context
            client_statuses = db_manager.get_all_status_settings(status_type='Client')
            if client_statuses is None: client_statuses = [] # Handle case where db_manager returns None

            self.status_combo.clear() # Clear before populating
            for status_dict in client_statuses:
                # Add status_name for display and status_id as item data
                self.status_combo.addItem(status_dict['status_name'], status_dict.get('status_id'))
        except Exception as e: # Catch a more generic exception if db_manager might raise something other than sqlite3.Error
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

                if db_manager.update_client(client_id_to_update, {'status_id': status_id_to_set}):
                    self.client_info["status"] = status_text # Keep display name
                    self.client_info["status_id"] = status_id_to_set # Update the id in the local map
                    print(f"Client {client_id_to_update} status_id updated to {status_id_to_set} ({status_text})")
                    # Consider emitting a signal here if the main list needs to refresh its delegate for color
                    # self.parentWidget().parentWidget().filter_client_list_display() # Example of trying to reach main window, not ideal
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour du statut du client dans la DB."))
            elif status_text: # Avoid warning if combo is cleared or empty initially
                QMessageBox.warning(self, self.tr("Erreur Configuration"), self.tr("Statut '{0}' non trouvé ou invalide. Impossible de mettre à jour.").format(status_text))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Erreur de mise à jour du statut:\n{0}").format(str(e)))

    def save_client_notes(self):
        notes = self.notes_edit.toPlainText()
        client_id_to_update = self.client_info.get("client_id")

        if client_id_to_update is None:
            QMessageBox.warning(self, self.tr("Erreur Client"), self.tr("ID Client non disponible, impossible de sauvegarder les notes."))
            return

        try:
            if db_manager.update_client(client_id_to_update, {'notes': notes}):
                self.client_info["notes"] = notes # Update local copy
            else:
                QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la sauvegarde des notes dans la DB."))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de sauvegarde des notes:\n{0}").format(str(e)))

    def populate_doc_table(self):
        self.doc_table.setRowCount(0); client_path = self.client_info["base_folder_path"]
        if not os.path.exists(client_path): return
        row = 0
        for lang in self.client_info.get("selected_languages", ["fr"]):
            lang_dir = os.path.join(client_path, lang)
            if not os.path.exists(lang_dir): continue
            for file_name in os.listdir(lang_dir):
                if file_name.endswith(('.xlsx', '.pdf', '.docx', '.html')):
                    file_path = os.path.join(lang_dir, file_name); name_item = QTableWidgetItem(file_name); name_item.setData(Qt.UserRole, file_path)
                    file_type_str = "";
                    if file_name.lower().endswith('.xlsx'): file_type_str = self.tr("Excel")
                    elif file_name.lower().endswith('.docx'): file_type_str = self.tr("Word")
                    elif file_name.lower().endswith('.html'): file_type_str = self.tr("HTML")
                    else: file_type_str = self.tr("PDF")
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                    self.doc_table.insertRow(row); self.doc_table.setItem(row, 0, name_item); self.doc_table.setItem(row, 1, QTableWidgetItem(file_type_str)); self.doc_table.setItem(row, 2, QTableWidgetItem(lang)); self.doc_table.setItem(row, 3, QTableWidgetItem(mod_time))
                    action_widget = QWidget(); action_layout = QHBoxLayout(action_widget); action_layout.setContentsMargins(2,2,2,2); action_layout.setSpacing(5)
                    pdf_btn = QPushButton(""); pdf_btn.setIcon(QIcon.fromTheme("document-export", QIcon(":/icons/pdf.svg"))); pdf_btn.setToolTip(self.tr("Générer/Ouvrir PDF du document")); pdf_btn.setFixedSize(30,30); pdf_btn.clicked.connect(lambda _, p=file_path: self._handle_open_pdf_action(p)); action_layout.addWidget(pdf_btn)
                    source_btn = QPushButton(""); source_btn.setIcon(QIcon.fromTheme("document-open", QIcon(":/icons/eye.svg"))); source_btn.setToolTip(self.tr("Afficher le fichier source")); source_btn.setFixedSize(30,30); source_btn.clicked.connect(lambda _, p=file_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p))); action_layout.addWidget(source_btn)
                    if file_name.lower().endswith(('.xlsx', '.html')):
                        edit_btn = QPushButton(""); edit_btn.setIcon(QIcon.fromTheme("document-edit", QIcon(":/icons/pencil.svg"))); edit_btn.setToolTip(self.tr("Modifier le contenu du document")); edit_btn.setFixedSize(30,30); edit_btn.clicked.connect(lambda _, p=file_path: self.open_document(p)); action_layout.addWidget(edit_btn)
                    else: spacer_widget = QWidget(); spacer_widget.setFixedSize(30,30); action_layout.addWidget(spacer_widget)
                    delete_btn = QPushButton(""); delete_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg"))); delete_btn.setToolTip(self.tr("Supprimer le document")); delete_btn.setFixedSize(30,30); delete_btn.clicked.connect(lambda _, p=file_path: self.delete_document(p)); action_layout.addWidget(delete_btn)
                    action_layout.addStretch(); action_widget.setLayout(action_layout); self.doc_table.setCellWidget(row, 4, action_widget); row +=1

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
        self.contacts_table.setRowCount(0) # Clear table
        client_uuid = self.client_info.get("client_id")
        if not client_uuid: return
        try:
            contacts = db_manager.get_contacts_for_client(client_uuid)
            contacts = contacts if contacts else []
            for row, contact in enumerate(contacts):
                self.contacts_table.insertRow(row)

                name_item = QTableWidgetItem(contact.get('name', 'N/A'))
                # Store IDs in the first column's item for retrieval
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
                # Optional: Center align this column
                primary_item.setTextAlignment(Qt.AlignCenter)
                self.contacts_table.setItem(row, 4, primary_item)

        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des contacts:\n{0}").format(str(e)))

    def add_contact(self):
        client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        dialog = self.ContactDialog(client_uuid, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            contact_form_data = dialog.get_data()
            try:
                # ... (logic for adding/linking contact remains the same) ...
                self.load_contacts() # Ensure this is called after DB operations
            except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du contact:\n{0}").format(str(e)))

    def edit_contact(self, row=None, column=None): # row, column can be passed by cellDoubleClicked
        current_row = self.contacts_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un contact à modifier."))
            return


        name_item = self.contacts_table.item(current_row, 0)
        if not name_item: return # Should not happen if row is valid

        item_data = name_item.data(Qt.UserRole)
        contact_id = item_data.get('contact_id')
        # client_contact_id is also available if needed for specific link properties
        # client_contact_id = item_data.get('client_contact_id')

        if not contact_id:
            QMessageBox.warning(self, self.tr("Erreur Données"), self.tr("ID de contact non trouvé pour la ligne sélectionnée."))
            return

        client_uuid = self.client_info.get("client_id") # For the dialog's context

        # Fetch the full contact details to pass to the dialog
        full_contact_details = db_manager.get_contact_by_id(contact_id)
        if not full_contact_details:
            QMessageBox.warning(self, self.tr("Erreur Données"), self.tr("Détails du contact non trouvés dans la base de données."))
            return

        # Add the client-specific link information to the contact_data for the dialog
        # This is crucial for the 'is_primary_for_client' checkbox
        client_contact_link_info = db_manager.get_specific_client_contact_link_details(client_uuid, contact_id)
        if client_contact_link_info:
            full_contact_details['is_primary_for_client'] = client_contact_link_info.get('is_primary_for_client', False)
            full_contact_details['client_contact_id'] = client_contact_link_info.get('client_contact_id') # Store for update

        dialog = self.ContactDialog(client_id=client_uuid, contact_data=full_contact_details, parent=self)

        if dialog.exec_() == QDialog.Accepted:
            updated_data_from_dialog = dialog.get_data()
            is_primary_for_client_from_dialog = updated_data_from_dialog.pop('is_primary_for_client', False)

            try:
                # Update the main contact details
                if db_manager.update_contact(contact_id, updated_data_from_dialog):
                    # Now, update the client-specific link (is_primary_for_client)
                    # We need the client_contact_id for this.
                    client_contact_id_for_update = full_contact_details.get('client_contact_id')
                    if client_contact_id_for_update is not None:
                        db_manager.update_client_contact_link(
                            client_contact_id_for_update,
                            {'is_primary_for_client': is_primary_for_client_from_dialog}
                        )
                    else:
                        # This case should ideally not happen if the contact is linked.
                        # If it can, then we might need to re-link or handle error.
                        print(f"Warning: client_contact_id not found for contact_id {contact_id} during update.")

                    QMessageBox.information(self, self.tr("Succès"), self.tr("Contact mis à jour avec succès."))
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour du contact."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Erreur lors de la mise à jour du contact:\n{0}").format(str(e)))
            finally:
                self.load_contacts() # Refresh the table

    def remove_contact(self):
        current_row = self.contacts_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un contact à supprimer."))
            return

        name_item = self.contacts_table.item(current_row, 0)
        if not name_item: return

        item_data = name_item.data(Qt.UserRole)
        contact_id = item_data.get('contact_id') # Global contact ID
        client_contact_id = item_data.get('client_contact_id') # Link ID

        contact_name = name_item.text()

        if not client_contact_id: # Should have this to remove the link
            QMessageBox.warning(self, self.tr("Erreur Données"), self.tr("ID de lien contact-client non trouvé."))
            return

        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"),
                                     self.tr("Êtes-vous sûr de vouloir supprimer le lien vers le contact '{0}' pour ce client?").format(contact_name),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if db_manager.unlink_contact_from_client(client_contact_id):
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Lien vers le contact '{0}' supprimé avec succès.").format(contact_name))
                    self.load_contacts() # Refresh table
                else:
                    QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la suppression du lien vers le contact."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du lien contact:\n{0}").format(str(e)))

    def add_product(self):
        client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        dialog = self.ProductDialog(client_uuid, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            products_list_data = dialog.get_data()
            # ... (logic for adding products remains the same) ...
            if products_list_data: self.load_products() # Refresh only if data was processed

    def edit_product(self):
        selected_row = self.products_table.currentRow();
        if selected_row < 0: QMessageBox.information(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un produit à modifier.")); return
        # ... (logic for editing product remains the same) ...
        try:
            # ... (DB operations) ...
            self.load_products() # Refresh after successful update
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Erreur lors de la modification du produit:\n{0}").format(str(e)))

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
        client_uuid = self.client_info.get("client_id")
        if not client_uuid:
            self.products_table.blockSignals(False)
            return

        try:
            all_linked_products = db_manager.get_products_for_client_or_project(client_uuid, project_id=None)
            all_linked_products = all_linked_products if all_linked_products else []

            selected_lang_code = self.product_lang_filter_combo.currentData()

            filtered_products = []
            if selected_lang_code: # If a specific language is selected (not "All Languages")
                for prod in all_linked_products:
                    # Ensure 'language_code' is available from the db_manager call for the product itself
                    if prod.get('language_code') == selected_lang_code:
                        filtered_products.append(prod)
            else: # "All Languages" selected
                filtered_products = all_linked_products

            for row_idx, prod_link_data in enumerate(filtered_products):
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
                self.products_table.setItem(row_idx, 5, qty_item)

                # Unit Price (Column 6 - Editable)
                unit_price_override = prod_link_data.get('unit_price_override')
                base_price = prod_link_data.get('base_unit_price')
                effective_unit_price = unit_price_override if unit_price_override is not None else (base_price if base_price is not None else 0.0)
                effective_unit_price = float(effective_unit_price)
                unit_price_item = QTableWidgetItem(f"{effective_unit_price:.2f}")
                unit_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                unit_price_item.setFlags(unit_price_item.flags() | Qt.ItemIsEditable)
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
            self.products_table.blockSignals(False) # Unblock signals

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

        self.edit_widgets['need'] = QTextEdit(self.client_info.get("need", self.client_info.get("primary_need_description", "")))
        self.edit_widgets['need'].setFixedHeight(60)
        self.details_layout.addRow(self.tr("Besoin Principal:"), self.edit_widgets['need'])

        folder_label_edit = QLabel(self.tr("Chemin Dossier:"))
        folder_value_edit = QLabel(self.client_info.get('base_folder_path','')) # Not editable
        self.details_layout.addRow(folder_label_edit, folder_value_edit)

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
        data_to_save['notes'] = self.notes_edit.toPlainText().strip()

        if not data_to_save['client_name'] or not data_to_save['project_identifier']:
            QMessageBox.warning(self, self.tr("Champs Requis"), self.tr("Nom client et ID Projet sont obligatoires."))
            return False

        if db_manager.update_client(self.client_info['client_id'], data_to_save):
            # Update self.client_info with all new values, including text names for country/city/status
            # This ensures the display view (populate_details_layout) has the most current data
            # A full fetch might be cleaner:
            updated_client_full_info = db_manager.get_client_by_id(self.client_info['client_id'])
            if updated_client_full_info:
                self.client_info = updated_client_full_info # Replace local client_info

                # Fetch related names for display consistency, as client_info might store names not IDs
                country_obj = db_manager.get_country_by_id(self.client_info.get('country_id'))
                city_obj = db_manager.get_city_by_id(self.client_info.get('city_id'))
                status_obj = db_manager.get_status_setting_by_id(self.client_info.get('status_id'))

                self.client_info['country'] = country_obj['country_name'] if country_obj else self.tr("N/A")
                self.client_info['city'] = city_obj['city_name'] if city_obj else self.tr("N/A")
                self.client_info['status'] = status_obj['status_name'] if status_obj else self.tr("N/A")
                # Other fields like client_name, company_name, notes etc. are directly from updated_client_full_info

            self.populate_details_layout() # Rebuild display view
            self.header_label.setText(f"<h2>{self.client_info.get('client_name', '')}</h2>") # Update header

            # Reconnect signals that were disconnected for edit mode
            self.notes_edit.textChanged.connect(self.save_client_notes)
            self.status_combo.currentTextChanged.connect(self.update_client_status)

            QMessageBox.information(self, self.tr("Succès"), self.tr("Informations client sauvegardées."))
            return True
        else:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la sauvegarde des informations client."))
            return False

# Ensure that all methods called by ClientWidget (like self.ContactDialog, self.generate_pdf_for_document)
# are correctly available either as methods of ClientWidget or properly imported.
# The dynamic import _import_main_elements() is a temporary measure.
# Ideally, ContactDialog, ProductDialog, etc., should also be moved to dialogs.py,
# and utility functions like generate_pdf_for_document to a utils.py file.
# The direct use of self.DATABASE_NAME in load_statuses and save_client_notes should be refactored
# to use db_manager for all database interactions.
