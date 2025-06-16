# -*- coding: utf-8 -*-
import os
import shutil
import logging # Added for logging
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QMessageBox, QLabel,
    QListWidget, QListWidgetItem, QComboBox, QGroupBox, QWidget
)
from PyQt5.QtGui import QIcon, QColor # QColor was used for item background (optional)
from PyQt5.QtCore import Qt # Qt is used for e.g. Qt.UserRole

import db as db_manager
from html_editor import HtmlEditor
from utils import populate_docx_template
# clients_crud_instance is not used by CreateDocumentDialog
import icons_rc # Import for Qt resource file

class CreateDocumentDialog(QDialog):
    def __init__(self, client_info, config, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.config = config # Store config passed from main
        self.setWindowTitle(self.tr("Créer des Documents"))
        self.setMinimumSize(600, 500)
        self._initial_load_complete = False
        self.setup_ui()

    def _create_icon_label_widget(self, icon_name, label_text): # This method was in original dialogs.py, but might not be used by this specific class. Let's check.
        # Upon review, this method is NOT used by CreateDocumentDialog. I will remove it.
        pass

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        header_label = QLabel(self.tr("Sélectionner Documents à Créer"))
        header_label.setObjectName("dialogHeaderLabel")
        main_layout.addWidget(header_label)

        filters_group = QGroupBox(self.tr("Filtres"))
        filters_group_layout = QVBoxLayout(filters_group)
        filters_group_layout.setSpacing(10)

        filter_row1_layout = QHBoxLayout()
        self.language_filter_label = QLabel(self.tr("Langue:"))
        filter_row1_layout.addWidget(self.language_filter_label)
        self.language_filter_combo = QComboBox()
        self.language_filter_combo.addItems([self.tr("All"), "fr", "en", "ar", "tr", "pt"])
        self.language_filter_combo.setCurrentText(self.tr("All"))
        filter_row1_layout.addWidget(self.language_filter_combo)
        filter_row1_layout.addSpacing(20)
        self.extension_filter_label = QLabel(self.tr("Extension:"))
        filter_row1_layout.addWidget(self.extension_filter_label)
        self.extension_filter_combo = QComboBox()
        self.extension_filter_combo.addItems([self.tr("All"), "HTML", "XLSX", "DOCX"])
        self.extension_filter_combo.setCurrentText("HTML")
        filter_row1_layout.addWidget(self.extension_filter_combo)
        filter_row1_layout.addStretch()
        filters_group_layout.addLayout(filter_row1_layout)

        filter_row2_layout = QHBoxLayout()
        self.search_bar_label = QLabel(self.tr("Rechercher:"))
        filter_row2_layout.addWidget(self.search_bar_label)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(self.tr("Filtrer par nom..."))
        filter_row2_layout.addWidget(self.search_bar)
        filters_group_layout.addLayout(filter_row2_layout)
        main_layout.addWidget(filters_group)

        self.order_select_combo = None
        client_category = self.client_info.get('category', '')
        client_id_for_events = self.client_info.get('client_id')

        has_multiple_events = False
        if client_id_for_events:
            has_multiple_events = self.has_multiple_purchase_events()

        if client_category == 'Distributeur' or has_multiple_events:
            order_group = QGroupBox(self.tr("Association Commande"))
            order_group_layout = QHBoxLayout(order_group)

            self.order_select_combo = QComboBox()
            self.order_select_combo.addItem(self.tr("Document Général (pas de commande spécifique)"), "NONE")
            if client_id_for_events:
                purchase_events = db_manager.get_distinct_purchase_confirmed_at_for_client(client_id_for_events)
                if purchase_events:
                    for event_ts in purchase_events:
                        if event_ts:
                            try:
                                dt_obj = datetime.fromisoformat(event_ts.replace('Z', '+00:00'))
                                display_text = self.tr("Commande du {0}").format(dt_obj.strftime('%Y-%m-%d %H:%M'))
                                self.order_select_combo.addItem(display_text, event_ts)
                            except ValueError:
                                # logging.warning(f"Could not parse purchase event timestamp: {event_ts}") # Consider logging
                                self.order_select_combo.addItem(self.tr("Commande du {0} (brut)").format(event_ts), event_ts)
            order_group_layout.addWidget(QLabel(self.tr("Associer à la Commande:")))
            order_group_layout.addWidget(self.order_select_combo)
            order_group_layout.addStretch()
            main_layout.addWidget(order_group)

        templates_group = QGroupBox(self.tr("Modèles Disponibles"))
        templates_group_layout = QVBoxLayout(templates_group)
        self.templates_list = QListWidget()
        self.templates_list.setSelectionMode(QListWidget.MultiSelection)
        self.templates_list.setAlternatingRowColors(True)
        self.templates_list.setStyleSheet("QListWidget::item:hover { background-color: #e6f7ff; }")
        templates_group_layout.addWidget(self.templates_list)
        main_layout.addWidget(templates_group)

        self.language_filter_combo.currentTextChanged.connect(self.load_templates)
        self.extension_filter_combo.currentTextChanged.connect(self.load_templates)
        self.search_bar.textChanged.connect(self.load_templates)

        self.load_templates()
        main_layout.addStretch(1)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        create_btn = button_box.button(QDialogButtonBox.Ok)
        create_btn.setText(self.tr("Créer Documents"))
        create_btn.setIcon(QIcon(":/icons/file-plus.svg"))
        create_btn.setObjectName("primaryButton")
        cancel_btn = button_box.button(QDialogButtonBox.Cancel)
        cancel_btn.setText(self.tr("Annuler"))
        cancel_btn.setIcon(QIcon(":/icons/dialog-cancel.svg"))
        button_box.accepted.connect(self.create_documents)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def has_multiple_purchase_events(self):
        if not self.client_info or not self.client_info.get('client_id'):
            return False
        try:
            events = db_manager.get_distinct_purchase_confirmed_at_for_client(self.client_info['client_id'])
            return len(events) > 1 if events else False
        except Exception as e:
            # logging.error(f"Error checking for multiple purchase events: {e}") # Consider logging
            print(f"Error checking for multiple purchase events: {e}") # Keep print if logging not set up
            return False

    def load_templates(self):
        self.templates_list.clear()
        if not self._initial_load_complete:
            primary_language = None; client_langs = self.client_info.get('selected_languages')
            if client_langs:
                if isinstance(client_langs, list) and client_langs: primary_language = client_langs[0]
                elif isinstance(client_langs, str) and client_langs.strip(): primary_language = client_langs.split(',')[0].strip()
            if primary_language and self.language_filter_combo.currentText() == self.tr("All"):
                for i in range(self.language_filter_combo.count()):
                    if self.language_filter_combo.itemText(i) == primary_language: self.language_filter_combo.setCurrentText(primary_language); break
            self._initial_load_complete = True

        selected_lang = self.language_filter_combo.currentText(); selected_ext_display = self.extension_filter_combo.currentText(); search_text = self.search_bar.text().lower()
        ext_map = {"HTML": ".html", "XLSX": ".xlsx", "DOCX": ".docx"}; selected_ext = ext_map.get(selected_ext_display)

        try:
            all_file_templates = db_manager.get_all_file_based_templates()
            if all_file_templates is None: all_file_templates = []

            default_templates = []
            other_templates = []

            for template_dict in all_file_templates:
                if template_dict.get('is_default_for_type_lang'):
                    default_templates.append(template_dict)
                else:
                    other_templates.append(template_dict)

            processed_templates = []
            for template_list_segment in [default_templates, other_templates]:
                for template_dict in template_list_segment:
                    name = template_dict.get('template_name', 'N/A')
                    lang_code = template_dict.get('language_code', 'N/A')
                    base_file_name = template_dict.get('base_file_name', 'N/A')

                    if selected_lang != self.tr("All") and lang_code != selected_lang:
                        continue
                    file_actual_ext = os.path.splitext(base_file_name)[1].lower()
                    if selected_ext_display != self.tr("All"):
                        if not selected_ext or file_actual_ext != selected_ext:
                            continue
                    if search_text and search_text not in name.lower():
                        continue
                    processed_templates.append(template_dict)

            for template_dict in processed_templates:
                name = template_dict.get('template_name', 'N/A')
                lang = template_dict.get('language_code', 'N/A')
                base_file_name = template_dict.get('base_file_name', 'N/A')
                is_default = template_dict.get('is_default_for_type_lang', False)
                item_text = f"{name} ({lang}) - {base_file_name}"
                if is_default: item_text = f"[D] {item_text}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, template_dict)
                if is_default:
                    font = item.font(); font.setBold(True); item.setFont(font)
                    # item.setBackground(QColor("#E0F0E0")) # QColor needs import
                self.templates_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des modèles:\n{0}").format(str(e)))

    def create_documents(self):
        selected_items = self.templates_list.selectedItems()
        if not selected_items: QMessageBox.warning(self, self.tr("Aucun document sélectionné"), self.tr("Veuillez sélectionner au moins un document à créer.")); return
        created_files_count = 0

        default_company_obj = db_manager.get_default_company()
        default_company_id = default_company_obj['company_id'] if default_company_obj else None
        if default_company_id is None:
            QMessageBox.warning(self, self.tr("Avertissement"), self.tr("Aucune société par défaut n'est définie. Les détails du vendeur peuvent être manquants."))

        client_id_for_context = self.client_info.get('client_id')
        project_id_for_context_arg = self.client_info.get('project_id', self.client_info.get('project_identifier'))

        for item in selected_items:
            template_data = item.data(Qt.UserRole)
            if not isinstance(template_data, dict):
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Données de modèle invalides pour l'élément sélectionné."))
                continue

            db_template_name = template_data.get('template_name', 'N/A')
            db_template_lang = template_data.get('language_code', 'N/A')
            actual_template_filename = template_data.get('base_file_name', None)
            template_type = template_data.get('template_type', 'UNKNOWN')
            template_id_for_db = template_data.get('template_id')

            if not actual_template_filename:
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Nom de fichier manquant pour le modèle '{0}'. Impossible de créer.").format(db_template_name)); continue

            template_file_on_disk_abs = os.path.join(self.config["templates_dir"], db_template_lang, actual_template_filename)

            if os.path.exists(template_file_on_disk_abs):
                selected_order_identifier = None
                if self.order_select_combo and self.order_select_combo.isVisible():
                    selected_order_identifier_data = self.order_select_combo.currentData()
                    if selected_order_identifier_data != "NONE":
                        selected_order_identifier = selected_order_identifier_data

                client_base_folder = self.client_info.get("base_folder_path")
                if not client_base_folder:
                    logging.error(f"Client base folder not found for client_id: {client_id_for_context}")
                    QMessageBox.warning(self, self.tr("Erreur Configuration Client"), self.tr("Dossier de base du client non configuré pour {0}.").format(self.client_info.get("client_name", "ce client")))
                    continue

                safe_order_subfolder = ""
                if selected_order_identifier:
                    safe_order_subfolder = selected_order_identifier.replace(':', '_').replace(' ', '_')
                    # Path for file system
                    target_path_for_file = os.path.join(client_base_folder, safe_order_subfolder, db_template_lang, actual_template_filename)
                    # Path for DB (relative to client_base_folder)
                    file_path_relative_for_db = os.path.join(safe_order_subfolder, db_template_lang, actual_template_filename)
                else:
                    # Path for file system
                    target_path_for_file = os.path.join(client_base_folder, db_template_lang, actual_template_filename)
                    # Path for DB (relative to client_base_folder)
                    file_path_relative_for_db = os.path.join(db_template_lang, actual_template_filename)

                logging.info(f"Target path for file: {target_path_for_file}")
                os.makedirs(os.path.dirname(target_path_for_file), exist_ok=True)

                try:
                    logging.info(f"Copying template '{template_file_on_disk_abs}' to '{target_path_for_file}'")
                    shutil.copy(template_file_on_disk_abs, target_path_for_file)
                    logging.info(f"Successfully copied template to target path.")

                    additional_context = {}
                    if 'project_id' in self.client_info: additional_context['project_id'] = self.client_info['project_id']
                    # invoice_id seems to be set later contextually for packing lists, not from client_info directly here.
                    # if 'invoice_id' in self.client_info: additional_context['invoice_id'] = self.client_info['invoice_id']
                    additional_context['order_identifier'] = selected_order_identifier

                    if template_type == 'HTML_PACKING_LIST':
                        additional_context['document_type'] = 'packing_list'
                        additional_context['current_document_type_for_notes'] = 'HTML_PACKING_LIST'
                        # ... (rest of packing list logic from original) ...
                        packing_details_payload = {}
                        linked_products = db_manager.get_products_for_client_or_project(
                            client_id_for_context,
                            project_id=project_id_for_context_arg
                        )
                        linked_products = linked_products if linked_products else []
                        packing_items_data = []
                        total_net_w = 0.0; total_gross_w = 0.0; total_pkg_count = 0
                        for idx, prod_data in enumerate(linked_products):
                            net_w = float(prod_data.get('weight', 0.0) or 0.0)
                            quantity = float(prod_data.get('quantity', 1.0) or 1.0)
                            gross_w = net_w * 1.05
                            dims = prod_data.get('dimensions', 'N/A')
                            num_pkgs = 1; pkg_type = 'Carton'
                            packing_items_data.append({
                                'marks_nos': f'BOX {total_pkg_count + 1}', 'product_id': prod_data.get('product_id'),
                                'product_name_override': None, 'quantity_description': f"{quantity} {prod_data.get('unit_of_measure', 'unit(s)')}",
                                'num_packages': num_pkgs, 'package_type': pkg_type,
                                'net_weight_kg_item': net_w * quantity, 'gross_weight_kg_item': gross_w * quantity,
                                'dimensions_cm_item': dims
                            })
                            total_net_w += net_w * quantity; total_gross_w += gross_w * quantity; total_pkg_count += num_pkgs
                        if not linked_products:
                             packing_items_data.append({
                                'marks_nos': 'N/A', 'product_id': None, 'product_name_override': 'No products linked to client/project.',
                                'quantity_description': '', 'num_packages': 0, 'package_type': '',
                                'net_weight_kg_item': 0, 'gross_weight_kg_item': 0, 'dimensions_cm_item': ''
                            })
                        packing_details_payload['items'] = packing_items_data
                        packing_details_payload['total_packages'] = total_pkg_count
                        packing_details_payload['total_net_weight_kg'] = round(total_net_w, 2)
                        packing_details_payload['total_gross_weight_kg'] = round(total_gross_w, 2)
                        packing_details_payload['total_volume_cbm'] = 'N/A'
                        client_project_identifier = self.client_info.get('project_identifier', self.client_info.get('client_id', 'NOID'))
                        timestamp_str = datetime.now().strftime('%Y%m%d')
                        additional_context['packing_list_id'] = f"PL-{client_project_identifier}-{timestamp_str}"
                        additional_context['invoice_id'] = f"INVREF-{client_project_identifier}-{timestamp_str}"
                        additional_context['project_id'] = self.client_info.get('project_identifier', 'N/A')
                        additional_context['packing_details'] = packing_details_payload
                    else:
                        additional_context.update(self.client_info.copy())
                        additional_context['document_type'] = template_type
                        additional_context['order_identifier'] = selected_order_identifier
                        if template_type.startswith("HTML_"):
                             additional_context['current_document_type_for_notes'] = template_type

                    doc_db_data = {
                        'client_id': client_id_for_context,
                        'project_id': project_id_for_context_arg, # This can be None if not applicable
                        'order_identifier': selected_order_identifier, # This can be None
                        'document_name': actual_template_filename, # Name of the doc, usually same as file
                        'file_name_on_disk': actual_template_filename, # Actual file name
                        'file_path_relative': file_path_relative_for_db, # Corrected relative path
                        'document_type_generated': template_type,
                        'source_template_id': template_id_for_db,
                        'created_by_user_id': None # Placeholder for user ID, to be implemented
                    }
                    logging.info(f"Attempting to add document to DB with data: {doc_db_data}")
                    new_document_id_from_db = db_manager.add_client_document(doc_db_data)

                    if new_document_id_from_db:
                        logging.info(f"Document record added to DB with ID: {new_document_id_from_db}")
                        additional_context['document_id'] = new_document_id_from_db
                    else:
                        logging.error(f"Failed to add document record to DB for: {actual_template_filename}. Data: {doc_db_data}")
                        QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Impossible d'enregistrer l'entrée du document dans la base de données pour {0}.").format(actual_template_filename))
                        # Consider cleanup of copied file if DB entry fails: os.remove(target_path_for_file)
                        continue # Skip to next template

                    if target_path_for_file.lower().endswith(".docx"):
                        logging.info(f"Populating DOCX template: {target_path_for_file}")
                        populate_docx_template(target_path_for_file, self.client_info) # self.client_info is used as context here
                    elif target_path_for_file.lower().endswith(".html"):
                        logging.info(f"Populating HTML template: {target_path_for_file}")
                        with open(target_path_for_file, 'r', encoding='utf-8') as f: template_content = f.read()

                        document_context = db_manager.get_document_context_data(
                            client_id=client_id_for_context, company_id=default_company_id,
                            target_language_code=db_template_lang, project_id=project_id_for_context_arg,
                            additional_context=additional_context
                        )
                        if not document_context:
                             logging.warning(f"Failed to get document context for {actual_template_filename}. HTML might be incomplete.")

                        try:
                            populated_content = HtmlEditor.populate_html_content(template_content, document_context if document_context else {})
                            with open(target_path_for_file, 'w', encoding='utf-8') as f: f.write(populated_content)
                            logging.info(f"Successfully populated and saved HTML: {target_path_for_file}")
                        except Exception as e_html_pop:
                            logging.error(f"Error populating HTML content for {target_path_for_file}: {e_html_pop}", exc_info=True)
                            QMessageBox.warning(self, self.tr("Erreur HTML"), self.tr("Erreur lors de la population du contenu HTML pour {0}:\n{1}").format(actual_template_filename, str(e_html_pop)))
                            # Continue, as file is copied, DB entry made, but content might be unpopulated/default.
                    created_files_count += 1
                except (IOError, shutil.Error) as e_copy:
                    logging.error(f"Error copying template '{template_file_on_disk_abs}' to '{target_path_for_file}': {e_copy}", exc_info=True)
                    QMessageBox.warning(self, self.tr("Erreur Copie Fichier"), self.tr("Impossible de copier le fichier modèle '{0}' vers la destination:\n{1}").format(actual_template_filename, str(e_copy)))
                except Exception as e_create:
                    logging.error(f"General error creating document '{actual_template_filename}': {e_create}", exc_info=True)
                    QMessageBox.warning(self, self.tr("Erreur Création Document"), self.tr("Impossible de créer ou populer le document '{0}':\n{1}").format(actual_template_filename, str(e_create)))
            else:
                logging.warning(f"Template file not found on disk: {template_file_on_disk_abs} for template name '{db_template_name}'")
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Fichier modèle '{0}' introuvable pour '{1}'.").format(actual_template_filename, db_template_name))

        if created_files_count > 0:
            QMessageBox.information(self, self.tr("Documents créés"), self.tr("{0} documents ont été créés avec succès.").format(created_files_count))
            self.accept()
        elif not selected_items:
            # This case should be handled by the initial check, but good to have robustness
            pass
        else: # Some items were selected, but none were created
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Aucun document n'a pu être créé. Vérifiez les messages d'erreur précédents ou les logs pour plus de détails."))
