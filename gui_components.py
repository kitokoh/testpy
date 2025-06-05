# -*- coding: utf-8 -*-
import sys
import os
import json
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QTextEdit,
    QListWidget, QFileDialog, QMessageBox, QDialog, QFormLayout, QComboBox,
    QDialogButtonBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QInputDialog, QGroupBox, QCheckBox, QListWidgetItem, QDoubleSpinBox
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QColor
from PyQt5.QtCore import Qt, QUrl, QDir, QCoreApplication

from app_config import CONFIG, APP_ROOT_DIR, load_config

# Imports from other project files
import db as db_manager # Assuming db.py is accessible
from excel_editor import ExcelEditor
from html_editor import HtmlEditor
from pagedegrde import generate_cover_page_logic, APP_CONFIG as PAGEDEGRDE_APP_CONFIG
from docx import Document # For populate_docx_template

# Imports from main_window.py (or a future config.py if we make one)
# These will be resolved once main_window.py is created and these vars are defined there.
# from main_window import CONFIG, APP_ROOT_DIR, DATABASE_NAME, load_config # load_config for CompilePdfDialog.send_email
# DATABASE_NAME might be better accessed via db_manager if possible, or CONFIG.
# For now, assume direct import.

# PyPDF2 for CompilePdfDialog
from PyPDF2 import PdfMerger

class ContactDialog(QDialog):
    def __init__(self, client_id=None, contact_data=None, parent=None):
        super().__init__(parent)
        # self.client_id = client_id # Not directly used if contact_data has all info
        self.contact_data = contact_data or {}
        self.setWindowTitle(self.tr("Gestion des Contacts") if not contact_data else self.tr("Modifier Contact"))
        self.setMinimumSize(400, 250) # Adjusted size
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
    def __init__(self, parent=None): # Removed config from constructor, will use global CONFIG
        super().__init__(parent)
        self.setWindowTitle(self.tr("Gestion des Modèles"))
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
        try:
            # Using db_manager instead of direct sqlite3
            all_templates = db_manager.get_all_templates_with_details() # Assumes this function exists and provides needed fields
            if all_templates is None: all_templates = []
            for template_data in all_templates:
                # Adjust based on actual fields from get_all_templates_with_details
                item_text = f"{template_data.get('template_name', 'N/A')} ({template_data.get('language_code', 'N/A')})"
                if template_data.get('is_default'): # Field name might be 'is_default_for_category_language'
                    item_text += f" [{self.tr('Défaut')}]"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, template_data.get('template_id'))
                self.template_list.addItem(item)
        except Exception as e: # Catch generic db_manager errors
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des modèles:
{0}").format(str(e)))

    def add_template(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Sélectionner un modèle"), CONFIG["templates_dir"],
            self.tr("Fichiers Modèles (*.xlsx *.docx *.html);;Fichiers Excel (*.xlsx);;Documents Word (*.docx);;Documents HTML (*.html);;Tous les fichiers (*)")
        )
        if not file_path: return
        name, ok = QInputDialog.getText(self, self.tr("Nom du Modèle"), self.tr("Entrez un nom pour ce modèle:"))
        if not ok or not name.strip(): return
        languages = ["fr", "en", "ar", "tr", "pt"] # These should ideally come from a central config or db
        lang, ok = QInputDialog.getItem(self, self.tr("Langue du Modèle"), self.tr("Sélectionnez la langue:"), languages, 0, False)
        if not ok: return

        target_dir = os.path.join(CONFIG["templates_dir"], lang)
        os.makedirs(target_dir, exist_ok=True)
        base_file_name = os.path.basename(file_path)
        target_path = os.path.join(target_dir, base_file_name)
        try:
            shutil.copy(file_path, target_path)
            # db_manager.add_template should handle the DB insertion
            # It needs: name, base_file_name, lang, type (Excel, Word, HTML), is_default (false initially)
            file_ext = os.path.splitext(base_file_name)[1].lower()
            doc_type = "Excel" # Default
            if file_ext == ".docx": doc_type = "Word"
            elif file_ext == ".html": doc_type = "HTML"

            template_data = {
                'template_name': name.strip(),
                'base_file_name': base_file_name,
                'language_code': lang,
                'document_type': doc_type,
                'description': '', # Optional: add a field for description
                'is_default_for_category_language': False
            }
            new_id = db_manager.add_template(template_data) # Assumes this function exists
            if new_id:
                self.load_templates()
                QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle ajouté avec succès."))
            else:
                QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout du modèle à la DB."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout du modèle:
{0}").format(str(e)))

    def edit_template(self):
        item = self.template_list.currentItem()
        if not item: return
        template_id = item.data(Qt.UserRole)
        try:
            template_details = db_manager.get_template_by_id(template_id) # Assumes this function exists
            if template_details:
                template_file_path = os.path.join(CONFIG["templates_dir"], template_details.get('language_code'), template_details.get('base_file_name'))
                QDesktopServices.openUrl(QUrl.fromLocalFile(template_file_path))
        except Exception as e: # Catch generic db_manager errors
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur d'accès au modèle:
{0}").format(str(e)))

    def delete_template(self):
        item = self.template_list.currentItem()
        if not item: return
        template_id = item.data(Qt.UserRole)
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"), self.tr("Êtes-vous sûr de vouloir supprimer ce modèle ?"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                template_details = db_manager.get_template_by_id(template_id)
                deleted_from_db = db_manager.delete_template(template_id) # Assumes this function exists
                if deleted_from_db and template_details:
                    file_path_to_delete = os.path.join(CONFIG["templates_dir"], template_details.get('language_code'), template_details.get('base_file_name'))
                    if os.path.exists(file_path_to_delete): os.remove(file_path_to_delete)
                    self.load_templates()
                    QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle supprimé avec succès."))
                elif not template_details:
                     QMessageBox.warning(self, self.tr("Erreur"), self.tr("Modèle non trouvé dans la DB."))
                else: # Not deleted from DB
                     QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur de suppression du modèle de la DB."))
            except Exception as e:
                QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur de suppression du modèle:
{0}").format(str(e)))

    def set_default_template(self):
        item = self.template_list.currentItem()
        if not item: return
        template_id = item.data(Qt.UserRole)
        try:
            # db_manager.set_default_template should handle logic:
            # 1. Get the template's name (category) and language.
            # 2. Set is_default=0 for all other templates of the same name and language.
            # 3. Set is_default=1 for the selected template_id.
            success = db_manager.set_default_template_for_category_language(template_id) # Assumes this function exists
            if success:
                self.load_templates()
                QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle défini comme modèle par défaut pour sa catégorie et langue."))
            else:
                QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de mise à jour du modèle par défaut."))
        except Exception as e: # Catch generic db_manager errors
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de mise à jour du modèle:
{0}").format(str(e)))

class ProductDialog(QDialog):
    def __init__(self, client_id, product_data=None, parent=None): # client_id might not be needed if product_data is self-sufficient for editing
        super().__init__(parent)
        # self.client_id = client_id # Store if needed for linking new products
        self.product_data = product_data or {} # For editing existing linked product
        self.setWindowTitle(self.tr("Ajouter Produit") if not self.product_data.get('client_project_product_id') else self.tr("Modifier Produit"))
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.name_input = QLineEdit(self.product_data.get("product_name", "")) # Global product name
        layout.addRow(self.tr("Nom du Produit:"), self.name_input)
        self.description_input = QTextEdit(self.product_data.get("product_description", "")) # Global product desc
        self.description_input.setFixedHeight(80)
        layout.addRow(self.tr("Description:"), self.description_input)
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0, 1000000)
        self.quantity_input.setValue(self.product_data.get("quantity", 0)) # From ClientProjectProducts
        self.quantity_input.valueChanged.connect(self.update_total_price)
        layout.addRow(self.tr("Quantité:"), self.quantity_input)

        # Effective unit price (override or base)
        effective_unit_price = self.product_data.get('unit_price_override', self.product_data.get('base_unit_price', 0.0))
        self.unit_price_input = QDoubleSpinBox()
        self.unit_price_input.setRange(0, 10000000)
        self.unit_price_input.setPrefix("€ ")
        self.unit_price_input.setValue(effective_unit_price)
        self.unit_price_input.valueChanged.connect(self.update_total_price)
        layout.addRow(self.tr("Prix Unitaire:"), self.unit_price_input)

        total_price_title_label = QLabel(self.tr("Prix Total:"))
        self.total_price_label = QLabel("€ 0.00")
        self.total_price_label.setStyleSheet("font-weight: bold;")
        layout.addRow(total_price_title_label, self.total_price_label)
        self.update_total_price() # Initial calculation
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
        # Returns data for both global product and the link
        return {
            # Global product fields (for add/update global product)
            "product_name": self.name_input.text().strip(),
            "product_description": self.description_input.toPlainText().strip(),
            # Link fields (for ClientProjectProducts)
            "quantity": self.quantity_input.value(),
            "unit_price_for_dialog": self.unit_price_input.value(), # This is the price user set in dialog
            # "total_price": self.quantity_input.value() * self.unit_price_input.value() # Calculated, not stored directly here
        }

class CreateDocumentDialog(QDialog):
    def __init__(self, client_info, parent=None): # Removed config, uses global CONFIG
        super().__init__(parent)
        self.client_info = client_info
        self.setWindowTitle(self.tr("Créer des Documents"))
        self.setMinimumSize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(self.tr("Langue:")))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(self.client_info.get("selected_languages", ["fr"]))
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)
        self.templates_list = QListWidget()
        self.templates_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(QLabel(self.tr("Sélectionnez les documents à créer:")))
        layout.addWidget(self.templates_list)
        self.load_templates_for_creation() # Renamed to avoid conflict
        btn_layout = QHBoxLayout()
        create_btn = QPushButton(self.tr("Créer Documents"))
        create_btn.setIcon(QIcon.fromTheme("document-new"))
        create_btn.clicked.connect(self.create_documents_from_selection) # Renamed
        btn_layout.addWidget(create_btn)
        cancel_btn = QPushButton(self.tr("Annuler"))
        cancel_btn.setIcon(QIcon.fromTheme("dialog-cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def load_templates_for_creation(self):
        self.templates_list.clear()
        try:
            # Fetch templates suitable for document generation (e.g., those with base_file_name)
            # db_manager.get_all_file_based_templates() or similar is needed
            all_file_templates = db_manager.get_all_file_based_templates() # Assumed function
            if all_file_templates is None: all_file_templates = []
            for template_dict in all_file_templates:
                name = template_dict.get('template_name', 'N/A')
                lang = template_dict.get('language_code', 'N/A')
                base_file_name = template_dict.get('base_file_name', 'N/A')
                item_text = f"{name} ({lang}) - {base_file_name}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, (name, lang, base_file_name)) # Store data for creation
                self.templates_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des modèles:
{0}").format(str(e)))

    def create_documents_from_selection(self): # Renamed
        selected_items = self.templates_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, self.tr("Aucun document sélectionné"), self.tr("Veuillez sélectionner au moins un document à créer."))
            return
        lang = self.lang_combo.currentText()
        target_dir = os.path.join(self.client_info["base_folder_path"], lang)
        os.makedirs(target_dir, exist_ok=True)
        created_files = []
        for item in selected_items:
            db_template_name, db_template_lang, actual_template_filename = item.data(Qt.UserRole)
            if not actual_template_filename:
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Nom de fichier manquant pour le modèle '{0}'. Impossible de créer.").format(db_template_name))
                continue
            template_file_found_abs = os.path.join(CONFIG["templates_dir"], db_template_lang, actual_template_filename)
            if os.path.exists(template_file_found_abs):
                target_path = os.path.join(target_dir, actual_template_filename)
                shutil.copy(template_file_found_abs, target_path)
                if target_path.lower().endswith(".docx"):
                    try:
                        populate_docx_template(target_path, self.client_info) # Defined below
                    except Exception as e_pop:
                        QMessageBox.warning(self, self.tr("Erreur DOCX"), self.tr("Impossible de populer le modèle Word '{0}':
{1}").format(os.path.basename(target_path), e_pop))
                elif target_path.lower().endswith(".html"):
                    try:
                        with open(target_path, 'r', encoding='utf-8') as f: template_content = f.read()
                        populated_content = HtmlEditor.populate_html_content(template_content, self.client_info)
                        with open(target_path, 'w', encoding='utf-8') as f: f.write(populated_content)
                    except Exception as e_html_pop:
                        QMessageBox.warning(self, self.tr("Erreur HTML"), self.tr("Impossible de populer le modèle HTML '{0}':
{1}").format(os.path.basename(target_path), e_html_pop))
                created_files.append(target_path)
            else:
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
        self.pdf_list.setHorizontalHeaderLabels([self.tr("Sélection"), self.tr("Nom du fichier"), self.tr("Chemin"), self.tr("Pages (ex: 1-3,5)")])
        self.pdf_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.pdf_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.pdf_list)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton(self.tr("Ajouter PDF")); add_btn.setIcon(QIcon.fromTheme("list-add")); add_btn.clicked.connect(self.add_pdf_to_list); btn_layout.addWidget(add_btn)
        remove_btn = QPushButton(self.tr("Supprimer")); remove_btn.setIcon(QIcon.fromTheme("edit-delete")); remove_btn.clicked.connect(self.remove_selected_pdf); btn_layout.addWidget(remove_btn)
        move_up_btn = QPushButton(self.tr("Monter")); move_up_btn.setIcon(QIcon.fromTheme("go-up")); move_up_btn.clicked.connect(self.move_pdf_up); btn_layout.addWidget(move_up_btn)
        move_down_btn = QPushButton(self.tr("Descendre")); move_down_btn.setIcon(QIcon.fromTheme("go-down")); move_down_btn.clicked.connect(self.move_pdf_down); btn_layout.addWidget(move_down_btn)
        layout.addLayout(btn_layout)
        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel(self.tr("Nom du fichier compilé:")))
        self.output_name_edit = QLineEdit(f"{self.tr('compilation')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf") # Renamed
        options_layout.addWidget(self.output_name_edit)
        layout.addLayout(options_layout)
        action_layout = QHBoxLayout()
        compile_btn = QPushButton(self.tr("Compiler PDF")); compile_btn.setIcon(QIcon.fromTheme("document-export")); compile_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;"); compile_btn.clicked.connect(self.execute_compile_pdf); action_layout.addWidget(compile_btn)
        cancel_btn = QPushButton(self.tr("Annuler")); cancel_btn.setIcon(QIcon.fromTheme("dialog-cancel")); cancel_btn.clicked.connect(self.reject); action_layout.addWidget(cancel_btn)
        layout.addLayout(action_layout)
        self.load_existing_pdfs_for_client() # Renamed

    def load_existing_pdfs_for_client(self): # Renamed
        client_dir = self.client_info["base_folder_path"]
        pdf_files = []
        for root, _, files in os.walk(client_dir):
            for file in files:
                if file.lower().endswith('.pdf'): pdf_files.append(os.path.join(root, file))
        self.pdf_list.setRowCount(len(pdf_files))
        for i, file_path in enumerate(pdf_files):
            chk = QCheckBox(); chk.setChecked(True); self.pdf_list.setCellWidget(i, 0, chk)
            self.pdf_list.setItem(i, 1, QTableWidgetItem(os.path.basename(file_path)))
            self.pdf_list.setItem(i, 2, QTableWidgetItem(file_path))
            pages_edit = QLineEdit("all"); pages_edit.setPlaceholderText(self.tr("all ou 1-3,5")); self.pdf_list.setCellWidget(i, 3, pages_edit)

    def add_pdf_to_list(self): # Renamed
        file_paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Sélectionner des PDF"), "", self.tr("Fichiers PDF (*.pdf)"))
        if not file_paths: return
        current_row_count = self.pdf_list.rowCount()
        self.pdf_list.setRowCount(current_row_count + len(file_paths))
        for i, file_path in enumerate(file_paths):
            row = current_row_count + i
            chk = QCheckBox(); chk.setChecked(True); self.pdf_list.setCellWidget(row, 0, chk)
            self.pdf_list.setItem(row, 1, QTableWidgetItem(os.path.basename(file_path)))
            self.pdf_list.setItem(row, 2, QTableWidgetItem(file_path))
            pages_edit = QLineEdit("all"); pages_edit.setPlaceholderText(self.tr("all ou 1-3,5")); self.pdf_list.setCellWidget(row, 3, pages_edit)

    def remove_selected_pdf(self): # Renamed
        selected_rows = set(index.row() for index in self.pdf_list.selectedIndexes())
        for row in sorted(selected_rows, reverse=True): self.pdf_list.removeRow(row)

    def move_pdf_up(self): # Renamed
        current_row = self.pdf_list.currentRow()
        if current_row > 0: self.swap_pdf_rows(current_row, current_row - 1); self.pdf_list.setCurrentCell(current_row - 1, 0) # Renamed

    def move_pdf_down(self): # Renamed
        current_row = self.pdf_list.currentRow()
        if current_row < self.pdf_list.rowCount() - 1: self.swap_pdf_rows(current_row, current_row + 1); self.pdf_list.setCurrentCell(current_row + 1, 0) # Renamed

    def swap_pdf_rows(self, row1, row2): # Renamed
        for col in range(self.pdf_list.columnCount()):
            item1 = self.pdf_list.takeItem(row1, col); item2 = self.pdf_list.takeItem(row2, col)
            self.pdf_list.setItem(row1, col, item2); self.pdf_list.setItem(row2, col, item1)
        widget1_chk = self.pdf_list.cellWidget(row1, 0); widget1_pages = self.pdf_list.cellWidget(row1, 3)
        widget2_chk = self.pdf_list.cellWidget(row2, 0); widget2_pages = self.pdf_list.cellWidget(row2, 3)
        self.pdf_list.setCellWidget(row1, 0, widget2_chk); self.pdf_list.setCellWidget(row1, 3, widget2_pages)
        self.pdf_list.setCellWidget(row2, 0, widget1_chk); self.pdf_list.setCellWidget(row2, 3, widget1_pages)

    def execute_compile_pdf(self): # Renamed
        merger = PdfMerger()
        output_name = self.output_name_edit.text().strip()
        if not output_name: QMessageBox.warning(self, self.tr("Nom manquant"), self.tr("Veuillez spécifier un nom de fichier pour la compilation.")); return
        if not output_name.lower().endswith('.pdf'): output_name += '.pdf'
        output_path = os.path.join(self.client_info["base_folder_path"], output_name)
        cover_path = self.generate_cover_page_pdf() # Renamed
        if cover_path: merger.append(cover_path)
        for row in range(self.pdf_list.rowCount()):
            chk = self.pdf_list.cellWidget(row, 0)
            if chk and chk.isChecked():
                file_path = self.pdf_list.item(row, 2).text()
                pages_spec = self.pdf_list.cellWidget(row, 3).text().strip()
                try:
                    if pages_spec.lower() == "all" or not pages_spec: merger.append(file_path)
                    else:
                        pages = []
                        for part in pages_spec.split(','):
                            if '-' in part: start, end = part.split('-'); pages.extend(range(int(start), int(end)+1))
                            else: pages.append(int(part))
                        merger.append(file_path, pages=[p-1 for p in pages])
                except Exception as e: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout de {0}:
{1}").format(os.path.basename(file_path), str(e)))
        try:
            with open(output_path, 'wb') as f: merger.write(f)
            if cover_path and os.path.exists(cover_path): os.remove(cover_path)
            self.offer_download_or_email_compiled_pdf(output_path) # Renamed
            self.accept()
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la compilation du PDF:
{0}").format(str(e)))

    def generate_cover_page_pdf(self): # Renamed
        config_dict = {
            'title': self.tr("Compilation de Documents - Projet: {0}").format(self.client_info.get('project_identifier', self.tr('N/A'))),
            'subtitle': self.tr("Client: {0}").format(self.client_info.get('client_name', self.tr('N/A'))),
            'author': self.client_info.get('company_name', PAGEDEGRDE_APP_CONFIG.get('default_institution', self.tr('Votre Entreprise'))),
            'date': datetime.now().strftime('%d/%m/%Y %H:%M'), 'doc_type': self.tr("Compilation de Documents"),
            # ... other fields from original ...
            'font_name': PAGEDEGRDE_APP_CONFIG.get('default_font', 'Helvetica'), 'logo_data': None,
             'footer_text': self.tr("Document compilé le {0}").format(datetime.now().strftime('%d/%m/%Y'))
        }
        logo_path = os.path.join(APP_ROOT_DIR, "logo.png") # APP_ROOT_DIR from main_window
        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f_logo: config_dict['logo_data'] = f_logo.read()
            except Exception as e_logo: print(self.tr("Erreur chargement logo.png: {0}").format(e_logo))
        try:
            pdf_bytes = generate_cover_page_logic(config_dict)
            base_temp_dir = self.client_info.get("base_folder_path", QDir.tempPath()) # QDir from QtCore
            temp_cover_filename = f"cover_page_generated_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.pdf"
            temp_cover_path = os.path.join(base_temp_dir, temp_cover_filename)
            with open(temp_cover_path, "wb") as f: f.write(pdf_bytes)
            return temp_cover_path
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur Page de Garde"), self.tr("Impossible de générer la page de garde: {0}").format(e)) # Simplified message
            return None

    def offer_download_or_email_compiled_pdf(self, pdf_path): # Renamed
        msg_box = QMessageBox(self); msg_box.setWindowTitle(self.tr("Compilation réussie"))
        msg_box.setText(self.tr("Le PDF compilé a été sauvegardé dans:
{0}").format(pdf_path))
        download_btn = msg_box.addButton(self.tr("Télécharger"), QMessageBox.ActionRole)
        email_btn = msg_box.addButton(self.tr("Envoyer par email"), QMessageBox.ActionRole)
        msg_box.addButton(self.tr("Fermer"), QMessageBox.RejectRole)
        msg_box.exec_()
        if msg_box.clickedButton() == download_btn: QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        elif msg_box.clickedButton() == email_btn: self.send_compiled_pdf_by_email(pdf_path) # Renamed

    def send_compiled_pdf_by_email(self, pdf_path): # Renamed
        primary_email = None
        client_uuid = self.client_info.get("client_id")
        if client_uuid:
            contacts_for_client = db_manager.get_contacts_for_client(client_uuid)
            if contacts_for_client:
                for contact in contacts_for_client:
                    if contact.get('is_primary_for_client'): primary_email = contact.get('email'); break
        email, ok = QInputDialog.getText(self, self.tr("Envoyer par email"), self.tr("Adresse email du destinataire:"), text=primary_email or "")
        if not ok or not email.strip(): return
        # Uses global load_config() which is a placeholder here, will be imported from main_window
        # This is a known issue to be resolved by import adjustments.
        current_app_config = load_config()
        if not current_app_config.get("smtp_server") or not current_app_config.get("smtp_user"):
            QMessageBox.warning(self, self.tr("Configuration manquante"), self.tr("Veuillez configurer les paramètres SMTP.")) # Simplified
            return
        msg = MIMEMultipart(); msg['From'] = current_app_config["smtp_user"]; msg['To'] = email
        msg['Subject'] = self.tr("Documents compilés - {0}").format(self.client_info['client_name'])
        body = self.tr("Bonjour,

Veuillez trouver ci-joint les documents compilés pour le projet {0}.

Cordialement,
Votre équipe").format(self.client_info.get('project_identifier', 'N/A'))
        msg.attach(MIMEText(body, 'plain'))
        with open(pdf_path, 'rb') as f: part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
        msg.attach(part)
        try:
            server = smtplib.SMTP(current_app_config["smtp_server"], current_app_config.get("smtp_port", 587))
            if current_app_config.get("smtp_port", 587) == 587: server.starttls()
            server.login(current_app_config["smtp_user"], current_app_config["smtp_password"])
            server.send_message(msg); server.quit()
            QMessageBox.information(self, self.tr("Email envoyé"), self.tr("Le document a été envoyé avec succès."))
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur d'envoi"), self.tr("Erreur lors de l'envoi de l'email:
{0}").format(str(e)))

class ClientWidget(QWidget):
    def __init__(self, client_info, parent_config, main_window_ref=None): # parent_config is CONFIG from main_window
        super().__init__(main_window_ref) # main_window_ref is the DocumentManager instance
        self.client_info = client_info
        self.config = parent_config # Use the passed config
        self.main_window = main_window_ref # Store reference to main window for callbacks if needed
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(15, 15, 15, 15); layout.setSpacing(15)
        header = QLabel(f"<h2>{self.client_info['client_name']}</h2>"); header.setStyleSheet("color: #2c3e50;")
        layout.addWidget(header)
        action_layout = QHBoxLayout()
        self.create_docs_btn = QPushButton(self.tr("Créer Documents")); self.create_docs_btn.setIcon(QIcon.fromTheme("document-new")); self.create_docs_btn.setStyleSheet("background-color: #3498db; color: white;"); self.create_docs_btn.clicked.connect(self.open_create_docs_dialog_for_client) # Renamed
        action_layout.addWidget(self.create_docs_btn)
        self.compile_pdf_btn = QPushButton(self.tr("Compiler PDF")); self.compile_pdf_btn.setIcon(QIcon.fromTheme("document-export")); self.compile_pdf_btn.setStyleSheet("background-color: #27ae60; color: white;"); self.compile_pdf_btn.clicked.connect(self.open_compile_pdf_dialog_for_client) # Renamed
        action_layout.addWidget(self.compile_pdf_btn)
        layout.addLayout(action_layout)
        status_layout = QHBoxLayout(); status_label = QLabel(self.tr("Statut:")); status_layout.addWidget(status_label)
        self.status_combo = QComboBox()
        self.load_client_statuses_for_combo() # Renamed
        self.status_combo.setCurrentText(self.client_info.get("status", self.tr("En cours")))
        self.status_combo.currentTextChanged.connect(self.update_client_status_in_db) # Renamed
        status_layout.addWidget(self.status_combo); layout.addLayout(status_layout)
        details_layout = QFormLayout(); details_layout.setLabelAlignment(Qt.AlignRight)
        details_data = [
            (self.tr("ID Projet:"), self.client_info.get("project_identifier", self.tr("N/A"))),
            (self.tr("Pays:"), self.client_info.get("country", self.tr("N/A"))),
            (self.tr("Ville:"), self.client_info.get("city", self.tr("N/A"))),
            (self.tr("Besoin Principal:"), self.client_info.get("need", self.tr("N/A"))),
            (self.tr("Prix Final:"), f"{self.client_info.get('price', 0)} €"),
            (self.tr("Date Création:"), self.client_info.get("creation_date", self.tr("N/A"))),
            (self.tr("Chemin Dossier:"), f"<a href='file:///{self.client_info['base_folder_path']}'>{self.client_info['base_folder_path']}</a>")
        ]
        for label_text, value_text in details_data:
            label_widget = QLabel(label_text); value_widget = QLabel(value_text)
            value_widget.setOpenExternalLinks(True); value_widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
            details_layout.addRow(label_widget, value_widget)
        layout.addLayout(details_layout)
        notes_group = QGroupBox(self.tr("Notes")); notes_layout = QVBoxLayout(notes_group)
        self.notes_edit = QTextEdit(self.client_info.get("notes", ""))
        self.notes_edit.setPlaceholderText(self.tr("Ajoutez des notes sur ce client..."))
        self.notes_edit.textChanged.connect(self.save_client_notes_to_db) # Renamed
        notes_layout.addWidget(self.notes_edit); layout.addWidget(notes_group)
        self.tab_widget = QTabWidget()
        docs_tab = QWidget(); docs_layout = QVBoxLayout(docs_tab)
        self.doc_table = QTableWidget(); self.doc_table.setColumnCount(5)
        self.doc_table.setHorizontalHeaderLabels([self.tr("Nom"), self.tr("Type"), self.tr("Langue"), self.tr("Date"), self.tr("Actions")])
        self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.doc_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.doc_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        docs_layout.addWidget(self.doc_table)
        doc_btn_layout = QHBoxLayout()
        refresh_btn = QPushButton(self.tr("Actualiser")); refresh_btn.setIcon(QIcon.fromTheme("view-refresh")); refresh_btn.clicked.connect(self.populate_doc_table_for_client) # Renamed
        doc_btn_layout.addWidget(refresh_btn)
        # Removed Open and Delete buttons here, actions are in cell widgets
        docs_layout.addLayout(doc_btn_layout); self.tab_widget.addTab(docs_tab, self.tr("Documents"))

        contacts_tab = QWidget(); contacts_layout = QVBoxLayout(contacts_tab)
        self.contacts_list = QListWidget(); self.contacts_list.setAlternatingRowColors(True); self.contacts_list.itemDoubleClicked.connect(self.edit_client_contact) # Renamed
        contacts_layout.addWidget(self.contacts_list)
        contacts_btn_layout = QHBoxLayout()
        self.add_contact_btn = QPushButton(self.tr("Ajouter Contact")); self.add_contact_btn.setIcon(QIcon.fromTheme("contact-new")); self.add_contact_btn.clicked.connect(self.add_new_client_contact) # Renamed
        contacts_btn_layout.addWidget(self.add_contact_btn)
        self.edit_contact_btn = QPushButton(self.tr("Modifier Contact")); self.edit_contact_btn.setIcon(QIcon.fromTheme("document-edit")); self.edit_contact_btn.clicked.connect(self.edit_client_contact) # Renamed
        contacts_btn_layout.addWidget(self.edit_contact_btn)
        self.remove_contact_btn = QPushButton(self.tr("Supprimer Contact")); self.remove_contact_btn.setIcon(QIcon.fromTheme("edit-delete")); self.remove_contact_btn.clicked.connect(self.remove_client_contact_link) # Renamed
        contacts_btn_layout.addWidget(self.remove_contact_btn)
        contacts_layout.addLayout(contacts_btn_layout); self.tab_widget.addTab(contacts_tab, self.tr("Contacts"))

        products_tab = QWidget(); products_layout = QVBoxLayout(products_tab)
        self.products_table = QTableWidget(); self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels([self.tr("ID"), self.tr("Nom Produit"), self.tr("Description"), self.tr("Qté"), self.tr("Prix Unitaire"), self.tr("Prix Total")])
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.products_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Name column stretch
        self.products_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # Description column stretch
        self.products_table.hideColumn(0)
        products_layout.addWidget(self.products_table)
        products_btn_layout = QHBoxLayout()
        self.add_product_btn = QPushButton(self.tr("Ajouter Produit")); self.add_product_btn.setIcon(QIcon.fromTheme("list-add")); self.add_product_btn.clicked.connect(self.add_product_to_client) # Renamed
        products_btn_layout.addWidget(self.add_product_btn)
        self.edit_product_btn = QPushButton(self.tr("Modifier Produit")); self.edit_product_btn.setIcon(QIcon.fromTheme("document-edit")); self.edit_product_btn.clicked.connect(self.edit_linked_client_product) # Renamed
        products_btn_layout.addWidget(self.edit_product_btn)
        self.remove_product_btn = QPushButton(self.tr("Supprimer Produit")); self.remove_product_btn.setIcon(QIcon.fromTheme("edit-delete")); self.remove_product_btn.clicked.connect(self.remove_linked_client_product) # Renamed
        products_btn_layout.addWidget(self.remove_product_btn)
        products_layout.addLayout(products_btn_layout); self.tab_widget.addTab(products_tab, self.tr("Produits"))

        layout.addWidget(self.tab_widget)
        self.populate_doc_table_for_client() # Renamed
        self.load_contacts_for_client() # Renamed
        self.load_products_for_client() # Renamed

    def load_client_statuses_for_combo(self): # Renamed
        self.status_combo.clear()
        try:
            # Assuming db_manager.get_all_status_settings filters by type 'Client' or similar
            client_statuses = db_manager.get_all_status_settings(status_type='Client') # Assumed parameter
            if client_statuses is None: client_statuses = []
            for status_dict in client_statuses:
                self.status_combo.addItem(status_dict['status_name'], status_dict.get('status_id'))
        except Exception as e: # Catch generic db_manager error
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des statuts:
{0}").format(str(e)))

    def update_client_status_in_db(self, status_text): # Renamed
        status_id = self.status_combo.currentData()
        if status_id is None: return # Should not happen if combo is populated correctly

        try:
            updated = db_manager.update_client(self.client_info["client_id"], {'status_id': status_id})
            if updated:
                self.client_info["status"] = status_text # Update local cache for display
                self.client_info["status_id"] = status_id
                # Refresh client list in main window if main_window reference is available
                if self.main_window and hasattr(self.main_window, 'filter_client_list_display'):
                    self.main_window.filter_client_list_display()
                if self.main_window and hasattr(self.main_window, 'stats_widget'):
                    self.main_window.stats_widget.update_stats()
            else:
                 QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec de la mise à jour du statut."))
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de mise à jour du statut:
{0}").format(str(e)))

    def save_client_notes_to_db(self): # Renamed
        notes = self.notes_edit.toPlainText()
        try:
            updated = db_manager.update_client(self.client_info["client_id"], {'notes': notes})
            if updated: self.client_info["notes"] = notes
            # else: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Échec sauvegarde des notes.")) # Optional feedback
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de sauvegarde des notes:
{0}").format(str(e)))

    def populate_doc_table_for_client(self): # Renamed
        self.doc_table.setRowCount(0)
        client_path = self.client_info["base_folder_path"]
        if not os.path.exists(client_path): return
        row = 0
        for lang_code_folder in self.client_info.get("selected_languages", ["fr"]):
            lang_dir = os.path.join(client_path, lang_code_folder)
            if not os.path.exists(lang_dir): continue
            for file_name in os.listdir(lang_dir):
                if file_name.lower().endswith(('.xlsx', '.pdf', '.docx', '.html')):
                    file_path = os.path.join(lang_dir, file_name)
                    name_item = QTableWidgetItem(file_name); name_item.setData(Qt.UserRole, file_path)
                    file_type_str = os.path.splitext(file_name)[1][1:].upper() # XLSX, PDF etc.
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')
                    self.doc_table.insertRow(row)
                    self.doc_table.setItem(row, 0, name_item)
                    self.doc_table.setItem(row, 1, QTableWidgetItem(file_type_str))
                    self.doc_table.setItem(row, 2, QTableWidgetItem(lang_code_folder))
                    self.doc_table.setItem(row, 3, QTableWidgetItem(mod_time))
                    action_widget = QWidget(); action_layout = QHBoxLayout(action_widget); action_layout.setContentsMargins(0,0,0,0); action_layout.setSpacing(5)
                    open_btn_i = QPushButton(); open_btn_i.setIcon(QIcon.fromTheme("document-open")); open_btn_i.setToolTip(self.tr("Ouvrir")); open_btn_i.setFixedSize(28,28); open_btn_i.clicked.connect(lambda _, p=file_path: self.open_document_for_client(p)); action_layout.addWidget(open_btn_i) # Renamed
                    if file_name.lower().endswith('.xlsx') or file_name.lower().endswith('.html'):
                        edit_btn_i = QPushButton(); edit_btn_i.setIcon(QIcon.fromTheme("document-edit")); edit_btn_i.setToolTip(self.tr("Éditer")); edit_btn_i.setFixedSize(28,28); edit_btn_i.clicked.connect(lambda _, p=file_path: self.open_document_for_client(p, edit_mode=True)); action_layout.addWidget(edit_btn_i) # Added edit_mode
                    delete_btn_i = QPushButton(); delete_btn_i.setIcon(QIcon.fromTheme("edit-delete")); delete_btn_i.setToolTip(self.tr("Supprimer")); delete_btn_i.setFixedSize(28,28); delete_btn_i.clicked.connect(lambda _, p=file_path: self.delete_document_for_client(p)); action_layout.addWidget(delete_btn_i) # Renamed
                    self.doc_table.setCellWidget(row, 4, action_widget)
                    row += 1
        self.doc_table.resizeColumnsToContents()


    def open_create_docs_dialog_for_client(self): # Renamed
        dialog = CreateDocumentDialog(self.client_info, self) # Uses global CONFIG
        if dialog.exec_() == QDialog.Accepted: self.populate_doc_table_for_client()

    def open_compile_pdf_dialog_for_client(self): # Renamed
        dialog = CompilePdfDialog(self.client_info, self)
        dialog.exec_() # Result handling (refresh) is done by CompilePdfDialog itself via accept()

    def open_document_for_client(self, file_path, edit_mode=False): # Renamed, added edit_mode
        if os.path.exists(file_path):
            try:
                editor_client_data = { # Data for populating templates/editors
                    "Nom du client": self.client_info.get("client_name", ""), "Besoin": self.client_info.get("need", ""),
                    "price": self.client_info.get("price", 0), "project_identifier": self.client_info.get("project_identifier", ""),
                    "company_name": self.client_info.get("company_name", ""), "country": self.client_info.get("country", ""),
                    "city": self.client_info.get("city", ""),
                }
                if file_path.lower().endswith('.xlsx') and edit_mode:
                    editor = ExcelEditor(file_path, client_data=editor_client_data, parent=self)
                    if editor.exec_() == QDialog.Accepted: self.populate_doc_table_for_client()
                elif file_path.lower().endswith('.html') and edit_mode:
                    html_editor_dialog = HtmlEditor(file_path, client_data=editor_client_data, parent=self)
                    if html_editor_dialog.exec_() == QDialog.Accepted: self.populate_doc_table_for_client()
                else: # Default open for PDF, DOCX, or non-edit mode for XLSX/HTML
                    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
            except Exception as e: QMessageBox.warning(self, self.tr("Erreur Ouverture Fichier"), self.tr("Impossible d'ouvrir/éditer le fichier:
{0}").format(str(e)))
        else:
            QMessageBox.warning(self, self.tr("Fichier Introuvable"), self.tr("Le fichier n'existe plus.")); self.populate_doc_table_for_client()

    def delete_document_for_client(self, file_path): # Renamed
        if not os.path.exists(file_path): return
        reply = QMessageBox.question(self, self.tr("Confirmer la suppression"), self.tr("Supprimer le fichier {0} ?").format(os.path.basename(file_path)), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path); self.populate_doc_table_for_client()
                QMessageBox.information(self, self.tr("Fichier supprimé"), self.tr("Le fichier a été supprimé.")) # Simplified
            except Exception as e: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de supprimer le fichier:
{0}").format(str(e)))

    def load_contacts_for_client(self): # Renamed
        self.contacts_list.clear()
        client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        try:
            contacts = db_manager.get_contacts_for_client(client_uuid)
            if contacts is None: contacts = []
            for contact in contacts:
                contact_text = f"{contact.get('name', 'N/A')}"
                if contact.get('email'): contact_text += f" <{contact.get('email')}>" # Added email
                if contact.get('phone'): contact_text += f" ({contact.get('phone')})"
                if contact.get('is_primary_for_client'): contact_text += f" [{self.tr('Principal')}]"
                item = QListWidgetItem(contact_text)
                item.setData(Qt.UserRole, {'contact_id': contact.get('contact_id'), 'client_contact_id': contact.get('client_contact_id')})
                self.contacts_list.addItem(item)
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur chargement contacts:
{0}").format(str(e)))

    def add_new_client_contact(self): # Renamed
        client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        dialog = ContactDialog(parent=self) # client_id not passed to dialog, it's for linking
        if dialog.exec_() == QDialog.Accepted:
            contact_form_data = dialog.get_data()
            try:
                existing_contact = db_manager.get_contact_by_email(contact_form_data['email'])
                contact_id_to_link = None
                if existing_contact:
                    contact_id_to_link = existing_contact['contact_id']
                    update_data = {k: v for k, v in contact_form_data.items() if k in ['name', 'phone', 'position'] and v != existing_contact.get(k)}
                    if update_data : db_manager.update_contact(contact_id_to_link, update_data)
                else:
                    new_contact_id = db_manager.add_contact({'name': contact_form_data['name'], 'email': contact_form_data['email'], 'phone': contact_form_data['phone'], 'position': contact_form_data['position']})
                    if new_contact_id: contact_id_to_link = new_contact_id
                    else: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer contact global.")); return
                if contact_id_to_link:
                    if contact_form_data['is_primary']: # Handle unsetting other primaries
                        client_contacts = db_manager.get_contacts_for_client(client_uuid)
                        if client_contacts:
                            for cc in client_contacts:
                                if cc['is_primary_for_client']: db_manager.update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})
                    link_id = db_manager.link_contact_to_client(client_uuid, contact_id_to_link, is_primary=contact_form_data['is_primary'])
                    if link_id: self.load_contacts_for_client()
                    else: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de lier contact au client (lien existe peut-être).")) # Simplified
            except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du contact:
{0}").format(str(e)))

    def edit_client_contact(self): # Renamed
        item = self.contacts_list.currentItem();
        if not item: return
        item_data = item.data(Qt.UserRole) # Contains contact_id and client_contact_id
        contact_id = item_data.get('contact_id')
        client_contact_id = item_data.get('client_contact_id')
        client_uuid = self.client_info.get("client_id")
        if not contact_id or not client_uuid: return
        try:
            contact_details = db_manager.get_contact_by_id(contact_id)
            if contact_details:
                current_link_info = db_manager.get_client_contact_link_details(client_contact_id) # Needs this function
                is_primary_for_this_client = current_link_info.get('is_primary_for_client', False) if current_link_info else False
                dialog_data = {"name": contact_details.get('name'), "email": contact_details.get('email'), "phone": contact_details.get('phone'), "position": contact_details.get('position'), "is_primary": is_primary_for_this_client}
                dialog = ContactDialog(contact_data=dialog_data, parent=self) # Pass contact_data for editing
                if dialog.exec_() == QDialog.Accepted:
                    new_form_data = dialog.get_data()
                    db_manager.update_contact(contact_id, {'name': new_form_data['name'], 'email': new_form_data['email'], 'phone': new_form_data['phone'], 'position': new_form_data['position']})
                    if new_form_data['is_primary'] != is_primary_for_this_client: # Primary status changed
                        if new_form_data['is_primary']: # Became primary
                            client_contacts = db_manager.get_contacts_for_client(client_uuid)
                            if client_contacts:
                                for cc in client_contacts: # Unset other primaries
                                    if cc['contact_id'] != contact_id and cc['is_primary_for_client']:
                                        db_manager.update_client_contact_link(cc['client_contact_id'], {'is_primary_for_client': False})
                        db_manager.update_client_contact_link(client_contact_id, {'is_primary_for_client': new_form_data['is_primary']})
                    self.load_contacts_for_client()
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur modification contact:
{0}").format(str(e)))

    def remove_client_contact_link(self): # Renamed
        item = self.contacts_list.currentItem();
        if not item: return
        item_data = item.data(Qt.UserRole); contact_id = item_data.get('contact_id')
        client_uuid = self.client_info.get("client_id")
        if not contact_id or not client_uuid: return
        contact_name = db_manager.get_contact_by_id(contact_id)['name'] if db_manager.get_contact_by_id(contact_id) else "Inconnu"
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression Lien"), self.tr("Supprimer lien vers {0} pour ce client ?
(Contact global non supprimé).").format(contact_name), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                unlinked = db_manager.unlink_contact_from_client(client_uuid, contact_id)
                if unlinked: self.load_contacts_for_client()
                else: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur suppression lien contact-client."))
            except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur suppression lien contact:
{0}").format(str(e)))

    def add_product_to_client(self): # Renamed
        client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        dialog = ProductDialog(client_uuid, parent=self) # client_uuid passed for context
        if dialog.exec_() == QDialog.Accepted:
            form_data = dialog.get_data() # name, desc, qty, unit_price_for_dialog
            try:
                global_product = db_manager.get_product_by_name(form_data['product_name'])
                global_product_id = None
                if global_product:
                    global_product_id = global_product['product_id']
                    # Optionally update global product if form_data['product_description'] differs
                else:
                    new_global_product_id = db_manager.add_product({'product_name': form_data['product_name'], 'description': form_data['product_description'], 'base_unit_price': form_data['unit_price_for_dialog']})
                    if new_global_product_id: global_product_id = new_global_product_id
                    else: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de créer produit global.")); return
                if global_product_id:
                    # Determine if unit_price_for_dialog is an override
                    base_price = global_product['base_unit_price'] if global_product else form_data['unit_price_for_dialog']
                    price_override = form_data['unit_price_for_dialog'] if form_data['unit_price_for_dialog'] != base_price else None

                    link_data = {'client_id': client_uuid, 'project_id': None, 'product_id': global_product_id, 'quantity': form_data['quantity'], 'unit_price_override': price_override}
                    cpp_id = db_manager.add_product_to_client_or_project(link_data)
                    if cpp_id: self.load_products_for_client()
                    else: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de lier produit au client."))
            except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur d'ajout du produit:
{0}").format(str(e)))

    def edit_linked_client_product(self): # Renamed
        selected_row = self.products_table.currentRow();
        if selected_row < 0: return
        cpp_id_item = self.products_table.item(selected_row, 0) # Hidden ID column
        if not cpp_id_item: return
        client_project_product_id = cpp_id_item.data(Qt.UserRole)
        client_uuid = self.client_info.get("client_id")
        try:
            linked_product_details = db_manager.get_client_project_product_by_id(client_project_product_id) # Needs this function
            if linked_product_details:
                # Data for ProductDialog: product_name, product_description, quantity, unit_price_override, base_unit_price
                dialog = ProductDialog(client_uuid, product_data=linked_product_details, parent=self)
                if dialog.exec_() == QDialog.Accepted:
                    form_data = dialog.get_data() # name, desc, qty, unit_price_for_dialog
                    # Update global product part
                    db_manager.update_product(linked_product_details['product_id'], {'product_name': form_data['product_name'], 'description': form_data['product_description']})
                    # Determine if unit_price_for_dialog is an override for the link
                    base_price = db_manager.get_product_by_id(linked_product_details['product_id'])['base_unit_price']
                    price_override = form_data['unit_price_for_dialog'] if form_data['unit_price_for_dialog'] != base_price else None
                    update_link_data = {'quantity': form_data['quantity'], 'unit_price_override': price_override}
                    if db_manager.update_client_project_product(client_project_product_id, update_link_data): self.load_products_for_client()
                    else: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Échec mise à jour produit lié."))
            else: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Détails produit lié introuvables."))
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur modification produit:
{0}").format(str(e)))

    def remove_linked_client_product(self): # Renamed
        selected_row = self.products_table.currentRow();
        if selected_row < 0: return
        cpp_id_item = self.products_table.item(selected_row, 0);
        if not cpp_id_item: return
        client_project_product_id = cpp_id_item.data(Qt.UserRole)
        product_name = self.products_table.item(selected_row, 1).text() if self.products_table.item(selected_row, 1) else self.tr("Inconnu")
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"), self.tr("Supprimer produit '{0}' de ce client?").format(product_name), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if db_manager.remove_product_from_client_or_project(client_project_product_id): self.load_products_for_client()
                else: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur suppression produit lié."))
            except Exception as e: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur suppression produit lié:
{0}").format(str(e)))

    def load_products_for_client(self): # Renamed
        self.products_table.setRowCount(0)
        client_uuid = self.client_info.get("client_id");
        if not client_uuid: return
        try:
            linked_products = db_manager.get_products_for_client_or_project(client_uuid, project_id=None)
            if linked_products is None: linked_products = []
            for row_idx, prod_link_data in enumerate(linked_products):
                self.products_table.insertRow(row_idx)
                id_item = QTableWidgetItem(str(prod_link_data.get('client_project_product_id'))); id_item.setData(Qt.UserRole, prod_link_data.get('client_project_product_id')); self.products_table.setItem(row_idx, 0, id_item)
                self.products_table.setItem(row_idx, 1, QTableWidgetItem(prod_link_data.get('product_name', 'N/A')))
                self.products_table.setItem(row_idx, 2, QTableWidgetItem(prod_link_data.get('product_description', '')))
                qty_item = QTableWidgetItem(str(prod_link_data.get('quantity', 0))); qty_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter); self.products_table.setItem(row_idx, 3, qty_item)
                effective_unit_price = prod_link_data.get('unit_price_override', prod_link_data.get('base_unit_price', 0.0))
                unit_price_item = QTableWidgetItem(f"€ {effective_unit_price:.2f}"); unit_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter); self.products_table.setItem(row_idx, 4, unit_price_item)
                total_price_item = QTableWidgetItem(f"€ {prod_link_data.get('total_price_calculated', 0.0):.2f}"); total_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter); self.products_table.setItem(row_idx, 5, total_price_item)
            self.products_table.resizeColumnsToContents()
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur chargement produits:
{0}").format(str(e)))

def populate_docx_template(docx_path, client_data):
    try:
        document = Document(docx_path)
        placeholders = {
            "{{CLIENT_NAME}}": client_data.get('client_name', ''), "{{PROJECT_ID}}": client_data.get('project_identifier', ''),
            "{{COMPANY_NAME}}": client_data.get('company_name', ''), "{{NEED}}": client_data.get('need', ''),
            "{{COUNTRY}}": client_data.get('country', ''), "{{CITY}}": client_data.get('city', ''),
            "{{PRICE}}": str(client_data.get('price', 0)), "{{DATE}}": datetime.now().strftime('%Y-%m-%d'),
            "{{STATUS}}": client_data.get('status', ''),
            "{{SELECTED_LANGUAGES}}": ", ".join(client_data.get('selected_languages', [])),
            "{{NOTES}}": client_data.get('notes', ''), "{{CREATION_DATE}}": client_data.get('creation_date', ''),
            "{{CATEGORY}}": client_data.get('category', ''), "{{PRIMARY_CONTACT_NAME}}": "",
        }
        for para in document.paragraphs:
            for key, value in placeholders.items():
                if key in para.text: para.text = para.text.replace(key, value)
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for key, value in placeholders.items():
                            if key in para.text: para.text = para.text.replace(key, value)
        document.save(docx_path)
    except Exception as e:
        print(f"Error populating DOCX template {docx_path}: {e}")
        raise
