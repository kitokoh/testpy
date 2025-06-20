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
# get_template_category_by_name is not directly used anymore, get_all_template_categories is.
# from db.cruds.template_categories_crud import get_template_category_by_name
from db.cruds.template_categories_crud import get_all_template_categories # Import for fetching all categories
# get_setting is no longer used for this purpose.
# from db.cruds.application_settings_crud import get_setting
from html_editor import HtmlEditor
from utils import populate_docx_template
# clients_crud_instance is not used by CreateDocumentDialog
import icons_rc # Import for Qt resource file

class CreateDocumentDialog(QDialog):
    def __init__(self, client_info, config, parent=None, template_data=None): # Added template_data
        super().__init__(parent)
        self.client_info = client_info
        self.config = config # Store config passed from main
        self.template_data = template_data # Store template_data
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
        main_layout.setSpacing(15) # Increased main layout spacing

        header_label = QLabel(self.tr("Sélectionner Documents à Créer"))
        header_label.setObjectName("dialogHeaderLabel")
        main_layout.addWidget(header_label)

        filters_group = QGroupBox(self.tr("Filtres"))
        # Create a single QHBoxLayout for all filter controls and set it directly for the group
        combined_filter_layout = QHBoxLayout(filters_group) # Set as layout for filters_group
        combined_filter_layout.setSpacing(10)
        combined_filter_layout.setContentsMargins(10, 10, 10, 10) # Add some margins inside the group box

        # Language Filter
        self.language_filter_label = QLabel(self.tr("Langue:"))
        combined_filter_layout.addWidget(self.language_filter_label)
        self.language_filter_combo = QComboBox()
        self.language_filter_combo.addItems([self.tr("All"), "fr", "en", "ar", "tr", "pt"])
        self.language_filter_combo.setCurrentText(self.tr("All"))
        combined_filter_layout.addWidget(self.language_filter_combo)

        # Extension Filter
        combined_filter_layout.addSpacing(15)
        self.extension_filter_label = QLabel(self.tr("Extension:"))
        combined_filter_layout.addWidget(self.extension_filter_label)
        self.extension_filter_combo = QComboBox()
        self.extension_filter_combo.addItems([self.tr("All"), "HTML", "XLSX", "DOCX"])
        self.extension_filter_combo.setCurrentText("HTML")
        combined_filter_layout.addWidget(self.extension_filter_combo)

        # Search Bar
        combined_filter_layout.addSpacing(15)
        self.search_bar_label = QLabel(self.tr("Rechercher:"))
        combined_filter_layout.addWidget(self.search_bar_label)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(self.tr("Filtrer par nom..."))
        combined_filter_layout.addWidget(self.search_bar)

        from PyQt5.QtWidgets import QSizePolicy


        self.search_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        main_layout.addWidget(filters_group)

        self.order_select_combo = None
        client_category = self.client_info.get('category', '')
        client_id_for_events = self.client_info.get('client_id')

        has_multiple_events = False
        if client_id_for_events:
            has_multiple_events = self.has_multiple_purchase_events()

        if client_category == 'Distributeur' or has_multiple_events:
            order_group = QGroupBox(self.tr("Association Commande"))
            order_group_layout = QHBoxLayout(order_group) # Set as layout for order_group
            order_group_layout.setSpacing(10)
            order_group_layout.setContentsMargins(10, 10, 10, 10) # Add margins

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
        templates_group_layout = QVBoxLayout(templates_group) # Set as layout for templates_group
        templates_group_layout.setSpacing(10) # Or keep default if it looks better
        templates_group_layout.setContentsMargins(10, 10, 10, 10) # Add margins
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
        ext_map = {"HTML": ".html", "XLSX": ".xlsx", "DOCX": ".docx"}
        type_map_from_ext = {".html": "document_html", ".xlsx": "document_excel", ".docx": "document_word"} # Add other types if needed

        selected_ext_val = ext_map.get(selected_ext_display)
        template_type_filter = None
        if selected_ext_display != self.tr("All"):
            template_type_filter = type_map_from_ext.get(selected_ext_val)

        effective_lang_filter = selected_lang if selected_lang != self.tr("All") else None
        current_client_id = self.client_info.get('client_id')
        logging.info(f"Loading templates with lang_filter: {effective_lang_filter}, ext_filter (maps to type): {template_type_filter}, search: '{search_text}'")

        try:
            # Fetch client-specific and global templates based on filters
            category_ids_to_filter = []
            # Define desired purposes
            desired_purposes = ['client_document', 'utility', 'document_global'] # Expanded list
            all_categories = get_all_template_categories()

            if all_categories:
                for category in all_categories:
                    purpose = category.get('purpose')
                    if purpose == 'client_document' or purpose == 'utility':

                        category_ids_to_filter.append(category['category_id'])

            logging.info(f"Category IDs to filter by (purposes: {desired_purposes}): {category_ids_to_filter}")

            if not category_ids_to_filter:
                logging.warning("No categories found with purpose 'client_document' or 'utility'. No templates will be shown based on this criterion if category filtering is applied.")
                # If category_ids_to_filter is empty and passed to get_all_templates,
                # it should result in no templates if the IN clause becomes `IN ()`.
                # Or, if get_all_templates handles empty list by not adding the category filter,
                # then all templates (matching other criteria) would be shown.
                # The current implementation of get_all_templates with an empty list for IN clause
                # will likely result in an SQL error or no results for that clause.
                # It's better if get_all_templates doesn't add the clause if the list is empty.
                # For now, we pass the empty list. If it causes issues, get_all_templates needs adjustment
                # or we explicitly pass None if category_ids_to_filter is empty.
                # Let's assume get_all_templates handles an empty list for category_id_filter correctly
                # by not filtering on categories if the list is empty (e.g. by not adding the IN clause).
                # To be safe, if empty, we might not want to filter by category at all,
                # or ensure get_all_templates handles it. If get_all_templates expects None to not filter,
                # then: category_id_filter = category_ids_to_filter if category_ids_to_filter else None
            actual_category_id_filter = category_ids_to_filter if category_ids_to_filter else None

            templates_from_db = db_manager.get_all_templates(
                template_type_filter=template_type_filter,
                language_code_filter=effective_lang_filter,
                client_id_filter=current_client_id,
                category_id_filter=actual_category_id_filter
            )
            if templates_from_db is None: templates_from_db = []
            logging.info(f"Fetched {len(templates_from_db)} templates from DB initially after category filtering.")

            # Apply search text filter locally first
            if search_text:
                templates_from_db = [
                    t for t in templates_from_db
                    if search_text in t.get('template_name', '').lower()
                ]

            # Refine default status based on client-specificity
            # Key: (template_type, language_code)
            # Value: template_dict (prioritizing client-specific default)
            effective_defaults_map = {}
            client_specific_defaults_found = {} # Stores client-specific defaults: key=(type,lang), value=template_dict

            # First, identify all client-specific defaults from the filtered list
            for t_dict in templates_from_db:
                if t_dict.get('client_id') and t_dict.get('is_default_for_type_lang'):
                    key = (t_dict.get('template_type'), t_dict.get('language_code'))
                    # If multiple client-specific defaults for same type/lang (should ideally not happen if set_default is used)
                    # we prefer the first one encountered or based on some criteria, here just overwriting.
                    client_specific_defaults_found[key] = t_dict

            effective_defaults_map.update(client_specific_defaults_found)

            # Second, add global defaults only if no client-specific default exists for that type/lang
            for t_dict in templates_from_db:
                if not t_dict.get('client_id') and t_dict.get('is_default_for_type_lang'):
                    key = (t_dict.get('template_type'), t_dict.get('language_code'))
                    if key not in effective_defaults_map: # No client-specific default for this type/lang
                        effective_defaults_map[key] = t_dict

            processed_templates_display_list = []
            for t_dict in templates_from_db:
                display_dict = t_dict.copy()
                key = (t_dict.get('template_type'), t_dict.get('language_code'))

                # Is this template the one chosen as the "effective" default for its type/lang?
                # We compare using object identity (id()) in case of identical dicts from different sources (unlikely here but safe)
                # or more simply, if the template_id matches (assuming template_id is unique and present)
                effective_default_for_key = effective_defaults_map.get(key)
                if effective_default_for_key and effective_default_for_key.get('template_id') == t_dict.get('template_id'):
                    display_dict['is_display_default'] = True
                else:
                    display_dict['is_display_default'] = False
                processed_templates_display_list.append(display_dict)

            # Sort: display_defaults first, then by name/lang
            # Global templates (client_id is None) should generally come after client-specific ones if names are similar etc.
            # The primary sort is by the new 'is_display_default' flag.
            processed_templates_display_list.sort(key=lambda t: (
                not t['is_display_default'], # False (is_display_default=True) comes before True (is_display_default=False)
                bool(t.get('client_id')),    # Client-specific (True) before global (False) for non-defaults or secondary sort
                t.get('template_name', '').lower(),
                t.get('language_code', '').lower()
            ))

            for template_dict_display_item in processed_templates_display_list:
                name = template_dict_display_item.get('template_name', 'N/A')
                lang = template_dict_display_item.get('language_code', 'N/A')
                base_file_name = template_dict_display_item.get('base_file_name', 'N/A')
                # Use 'is_display_default' for the UI indication
                is_default_for_display = template_dict_display_item.get('is_display_default', False)

                item_text = f"{name} ({lang}) - {base_file_name}"
                if is_default_for_display:
                    item_text = f"[D] {item_text}"

                item = QListWidgetItem(item_text)
                # Store the original template_dict (or its copy if modification is an issue) in UserRole
                # Here, template_dict_display_item contains the original data + 'is_display_default'
                item.setData(Qt.UserRole, template_dict_display_item)

                if is_default_for_display:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    # item.setBackground(QColor("#E0F0E0")) # Optional: QColor needs import
                self.templates_list.addItem(item)

            if self.template_data and self.template_data.get('template_id'):
                target_template_id = self.template_data.get('template_id')
                for i in range(self.templates_list.count()):
                    item = self.templates_list.item(i)
                    item_template_data = item.data(Qt.UserRole)
                    if isinstance(item_template_data, dict) and item_template_data.get('template_id') == target_template_id:
                        logging.info(f"Pre-selecting template item based on template_id: {target_template_id} (Name: {item_template_data.get('template_name')})")
                        item.setSelected(True)
                        from PyQt5.QtWidgets import QAbstractItemView # Import for PositionAtCenter
                        self.templates_list.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                        break
        except Exception as e:
            logging.error("Error loading templates in dialog", exc_info=True)
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

            # Path construction modification: include template_type as a subdirectory
            template_type_folder = template_type if template_type and template_type.strip() else "unknown_type"

            template_file_on_disk_abs = os.path.join(self.config["templates_dir"], template_type_folder, db_template_lang, actual_template_filename)
            logging.info(f"Constructed template path for existence check: {template_file_on_disk_abs} (Type: {template_type_folder}, Lang: {db_template_lang}, File: {actual_template_filename})")

            if not os.path.exists(template_file_on_disk_abs):
                logging.warning(f"Template file not found on disk: {template_file_on_disk_abs} for template name '{db_template_name}'. Skipping this template.")
                QMessageBox.warning(self, self.tr("Fichier Modèle Introuvable"),
                                    self.tr("Le fichier pour le modèle '{0}' ({1}) de type '{2}' est introuvable à l'emplacement attendu:\n{3}\n\nCe modèle sera ignoré.").format(db_template_name, db_template_lang, template_type, template_file_on_disk_abs))
                continue
            # No need for '=== Added Existence Check ===' comments, the logic is integrated.

            # The original if os.path.exists(template_file_on_disk_abs) is now redundant due to the check above,
            # but the logic inside it should proceed if the file exists (i.e., if the `continue` above wasn't hit).
            # So, we don't need to indent the following block further, it's correctly placed.
            # if os.path.exists(template_file_on_disk_abs): # This line can be effectively removed or commented out if the above check is comprehensive.
            # For clarity, let's assume the code below this point only runs if the file exists.

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
            # The 'else' for the original 'if os.path.exists' is no longer needed here as the check is done above.
            # else:
            #     logging.warning(f"Template file not found on disk: {template_file_on_disk_abs} for template name '{db_template_name}'")
            #     QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Fichier modèle '{0}' introuvable pour '{1}'.").format(actual_template_filename, db_template_name))

        if created_files_count > 0:
            QMessageBox.information(self, self.tr("Documents créés"), self.tr("{0} documents ont été créés avec succès.").format(created_files_count))
            self.accept()
        elif not selected_items:
            # This case should be handled by the initial check, but good to have robustness
            pass
        else: # Some items were selected, but none were created
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Aucun document n'a pu être créé. Vérifiez les messages d'erreur précédents ou les logs pour plus de détails."))
