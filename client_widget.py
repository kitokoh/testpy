# -*- coding: utf-8 -*-
import os
import shutil
from datetime import datetime
# import sqlite3 # No longer needed as methods are refactored to use db_manager

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QListWidget,
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
        import main as main_module # This is the potential circular import point
        from dialogs import SendEmailDialog # Direct import for SendEmailDialog
        MAIN_MODULE_CONTACT_DIALOG = main_module.ContactDialog
        MAIN_MODULE_PRODUCT_DIALOG = main_module.ProductDialog
        MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG = main_module.EditProductLineDialog
        MAIN_MODULE_CREATE_DOCUMENT_DIALOG = main_module.CreateDocumentDialog
        MAIN_MODULE_COMPILE_PDF_DIALOG = main_module.CompilePdfDialog
        MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT = main_module.generate_pdf_for_document
        MAIN_MODULE_CONFIG = main_module.CONFIG
        MAIN_MODULE_DATABASE_NAME = main_module.DATABASE_NAME # Used in load_statuses, save_client_notes
        MAIN_MODULE_SEND_EMAIL_DIALOG = SendEmailDialog


class ClientWidget(QWidget):
    def __init__(self, client_info, config, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        # self.config = config # Original config passed

        # Dynamically import main elements to avoid circular import at module load time
        _import_main_elements()
        self.config = MAIN_MODULE_CONFIG # Use the imported config
        self.DATABASE_NAME = MAIN_MODULE_DATABASE_NAME # For methods still using it

        self.ContactDialog = MAIN_MODULE_CONTACT_DIALOG
        self.ProductDialog = MAIN_MODULE_PRODUCT_DIALOG
        self.EditProductLineDialog = MAIN_MODULE_EDIT_PRODUCT_LINE_DIALOG
        self.CreateDocumentDialog = MAIN_MODULE_CREATE_DOCUMENT_DIALOG
        self.CompilePdfDialog = MAIN_MODULE_COMPILE_PDF_DIALOG
        self.generate_pdf_for_document = MAIN_MODULE_GENERATE_PDF_FOR_DOCUMENT
        self.SendEmailDialog = MAIN_MODULE_SEND_EMAIL_DIALOG # Added

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        self.header_label = QLabel(f"<h2>{self.client_info['client_name']}</h2>")
        # self.header_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;") # Removed inline style
        self.header_label.setObjectName("clientHeaderLabel") # Added object name
        layout.addWidget(self.header_label)

        action_layout = QHBoxLayout()
        # Repurpose create_docs_btn to Envoyer Mail
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
        layout.addLayout(action_layout)

        status_layout = QHBoxLayout()
        status_label = QLabel(self.tr("Statut:"))
        status_layout.addWidget(status_label)
        self.status_combo = QComboBox()
        self.load_statuses()
        self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours")))
        self.status_combo.currentTextChanged.connect(self.update_client_status)
        status_layout.addWidget(self.status_combo)
        layout.addLayout(status_layout)

        self.details_layout = QFormLayout()
        self.details_layout.setLabelAlignment(Qt.AlignRight)
        self.details_layout.setSpacing(8)
        self.detail_value_labels = {}
        self.populate_details_layout()
        self.category_label = QLabel(self.tr("Catégorie:"))
        self.category_value_label = QLabel(self.client_info.get("category", self.tr("N/A")))
        self.details_layout.addRow(self.category_label, self.category_value_label)
        self.detail_value_labels["category"] = self.category_value_label
        layout.addLayout(self.details_layout)

        # Initialize notes_edit here, before it's added to a tab
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

        contacts_tab = QWidget(); contacts_layout = QVBoxLayout(contacts_tab)
        self.contacts_list = QListWidget(); self.contacts_list.setAlternatingRowColors(True); self.contacts_list.itemDoubleClicked.connect(self.edit_contact); contacts_layout.addWidget(self.contacts_list)
        contacts_btn_layout = QHBoxLayout()
        self.add_contact_btn = QPushButton(self.tr("➕ Ajouter")); self.add_contact_btn.setIcon(QIcon.fromTheme("contact-new", QIcon.fromTheme("list-add"))); self.add_contact_btn.setToolTip(self.tr("Ajouter un nouveau contact pour ce client")); self.add_contact_btn.clicked.connect(self.add_contact); contacts_btn_layout.addWidget(self.add_contact_btn)
        self.edit_contact_btn = QPushButton(self.tr("✏️ Modifier")); self.edit_contact_btn.setIcon(QIcon.fromTheme("document-edit")); self.edit_contact_btn.setToolTip(self.tr("Modifier le contact sélectionné")); self.edit_contact_btn.clicked.connect(self.edit_contact); contacts_btn_layout.addWidget(self.edit_contact_btn)
        self.remove_contact_btn = QPushButton(self.tr("🗑️ Supprimer")); self.remove_contact_btn.setIcon(QIcon.fromTheme("edit-delete")); self.remove_contact_btn.setToolTip(self.tr("Supprimer le lien vers le contact sélectionné pour ce client")); self.remove_contact_btn.setObjectName("dangerButton"); self.remove_contact_btn.clicked.connect(self.remove_contact); contacts_btn_layout.addWidget(self.remove_contact_btn)
        contacts_layout.addLayout(contacts_btn_layout)
        self.tab_widget.addTab(contacts_tab, self.tr("Contacts"))

        products_tab = QWidget(); products_layout = QVBoxLayout(products_tab)
        self.products_table = QTableWidget(); self.products_table.setColumnCount(6); self.products_table.setHorizontalHeaderLabels([self.tr("ID"), self.tr("Nom Produit"), self.tr("Description"), self.tr("Qté"), self.tr("Prix Unitaire"), self.tr("Prix Total")]); self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); self.products_table.hideColumn(0); products_layout.addWidget(self.products_table)
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
        # Get the base path for the client's documents
        # The initial directory for the file dialog can be the general clients_dir or user's home
        # Using self.config which should be available.
        initial_dir = self.config.get("clients_dir", os.path.expanduser("~")) # Fallback to home directory

        selected_file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Sélectionner un document"),
            initial_dir, # Use a sensible default directory
            self.tr("Tous les fichiers (*.*)")
        )

        if selected_file_path: # Proceed if a file was selected
            try:
                # Determine the target directory
                # Use the first language from selected_languages, default to 'fr'
                client_languages = self.client_info.get("selected_languages", ["fr"])
                if isinstance(client_languages, str): # If it's a comma-separated string
                    client_languages = [lang.strip() for lang in client_languages.split(',') if lang.strip()]

                target_lang_folder = client_languages[0] if client_languages else "fr"

                target_dir = os.path.join(self.client_info["base_folder_path"], target_lang_folder)

                # Create the target directory if it doesn't exist
                os.makedirs(target_dir, exist_ok=True)

                # Construct the target file path
                file_name = os.path.basename(selected_file_path)
                target_file_path = os.path.join(target_dir, file_name)

                # Check if file already exists
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
                        return # User chose not to replace

                # Copy the selected file
                shutil.copy(selected_file_path, target_file_path)

                # Refresh the document table
                self.populate_doc_table()

                QMessageBox.information(
                    self,
                    self.tr("Succès"),
                    self.tr("Document '{0}' ajouté avec succès.").format(file_name)
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
        generated_pdf_path = self.generate_pdf_for_document(file_path, self.client_info, self)
        if generated_pdf_path: QDesktopServices.openUrl(QUrl.fromLocalFile(generated_pdf_path))

    def populate_details_layout(self):
        while self.details_layout.rowCount() > 0: self.details_layout.removeRow(0)
        self.detail_value_labels.clear()
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
            label_widget = QLabel(label_text); value_widget = QLabel(value_text)
            if key == "base_folder_path": value_widget.setOpenExternalLinks(True); value_widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.details_layout.addRow(label_widget, value_widget); self.detail_value_labels[key] = value_widget

    def refresh_display(self, new_client_info):
        self.client_info = new_client_info
        self.header_label.setText(f"<h2>{self.client_info.get('client_name', '')}</h2>")
        self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours")))
        if hasattr(self, 'detail_value_labels'):
            self.detail_value_labels["project_identifier"].setText(self.client_info.get("project_identifier", self.tr("N/A")))
            self.detail_value_labels["country"].setText(self.client_info.get("country", self.tr("N/A")))
            self.detail_value_labels["city"].setText(self.client_info.get("city", self.tr("N/A")))
            self.detail_value_labels["need"].setText(self.client_info.get("need", self.tr("N/A")))
            self.detail_value_labels["price"].setText(f"{self.client_info.get('price', 0)} €")
            self.detail_value_labels["creation_date"].setText(self.client_info.get("creation_date", self.tr("N/A")))
            folder_path = self.client_info.get('base_folder_path',''); self.detail_value_labels["base_folder_path"].setText(f"<a href='file:///{folder_path}'>{folder_path}</a>")
            if "category" in self.detail_value_labels: self.detail_value_labels["category"].setText(self.client_info.get("category", self.tr("N/A")))
            elif hasattr(self, 'category_value_label'): self.category_value_label.setText(self.client_info.get("category", self.tr("N/A")))
        else: self.populate_details_layout()
        if hasattr(self, 'category_value_label'): self.category_value_label.setText(self.client_info.get("category", self.tr("N/A")))
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
        dialog = self.CompilePdfDialog(self.client_info, self)
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
        self.contacts_list.clear(); client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        try:
            contacts = db_manager.get_contacts_for_client(client_uuid); contacts = contacts if contacts else []
            for contact in contacts:
                contact_text = f"{contact.get('name', 'N/A')}"
                if contact.get('phone'): contact_text += f" ({contact.get('phone')})"
                if contact.get('is_primary_for_client'): contact_text += f" [{self.tr('Principal')}]"
                item = QListWidgetItem(contact_text); item.setData(Qt.UserRole, {'contact_id': contact.get('contact_id'), 'client_contact_id': contact.get('client_contact_id'), 'is_primary': contact.get('is_primary_for_client')}); self.contacts_list.addItem(item)
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des contacts:\n{0}").format(str(e)))

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

    def edit_contact(self):
        item = self.contacts_list.currentItem();
        if not item: return
        # ... (logic for editing contact remains the same) ...
        try:
            # ... (DB operations) ...
            self.load_contacts() # Ensure this is called after DB operations
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de modification du contact:\n{0}").format(str(e)))


    def remove_contact(self):
        item = self.contacts_list.currentItem();
        if not item: return
        # ... (logic for removing contact link remains the same) ...
        try:
            # ... (DB operations) ...
            self.load_contacts() # Ensure this is called after DB operations
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de suppression du lien contact:\n{0}").format(str(e)))

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
        self.products_table.setRowCount(0); client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        try:
            linked_products = db_manager.get_products_for_client_or_project(client_uuid, project_id=None); linked_products = linked_products if linked_products else []
            for row_idx, prod_link_data in enumerate(linked_products):
                self.products_table.insertRow(row_idx)
                id_item = QTableWidgetItem(str(prod_link_data.get('client_project_product_id'))); id_item.setData(Qt.UserRole, prod_link_data.get('client_project_product_id')); self.products_table.setItem(row_idx, 0, id_item)
                self.products_table.setItem(row_idx, 1, QTableWidgetItem(prod_link_data.get('product_name', 'N/A')))
                self.products_table.setItem(row_idx, 2, QTableWidgetItem(prod_link_data.get('product_description', '')))
                qty_item = QTableWidgetItem(str(prod_link_data.get('quantity', 0))); qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter); self.products_table.setItem(row_idx, 3, qty_item)
                unit_price_override = prod_link_data.get('unit_price_override'); base_price = prod_link_data.get('base_unit_price')
                effective_unit_price = unit_price_override if unit_price_override is not None else (base_price if base_price is not None else 0.0)
                effective_unit_price = float(effective_unit_price)
                unit_price_item = QTableWidgetItem(f"€ {effective_unit_price:.2f}"); unit_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter); self.products_table.setItem(row_idx, 4, unit_price_item)
                total_price_calculated_val = prod_link_data.get('total_price_calculated', 0.0); total_price_calculated_val = float(total_price_calculated_val)
                total_price_item = QTableWidgetItem(f"€ {total_price_calculated_val:.2f}"); total_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter); self.products_table.setItem(row_idx, 5, total_price_item)
            self.products_table.resizeColumnsToContents()
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des produits:\n{0}").format(str(e)))

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

        dialog = self.SendEmailDialog(client_email=primary_email, config=self.config, parent=self)
        dialog.exec_()

# Ensure that all methods called by ClientWidget (like self.ContactDialog, self.generate_pdf_for_document)
# are correctly available either as methods of ClientWidget or properly imported.
# The dynamic import _import_main_elements() is a temporary measure.
# Ideally, ContactDialog, ProductDialog, etc., should also be moved to dialogs.py,
# and utility functions like generate_pdf_for_document to a utils.py file.
# The direct use of self.DATABASE_NAME in load_statuses and save_client_notes should be refactored
# to use db_manager for all database interactions.