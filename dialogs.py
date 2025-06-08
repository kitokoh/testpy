# -*- coding: utf-8 -*-
import os
import json
import shutil

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QSpinBox, QDialogButtonBox,
    QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QTextEdit,
    QInputDialog, QMessageBox
)
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtCore import Qt, QUrl, QCoreApplication

import pandas as pd
from docx import Document

import db as db_manager # Standardized import
from company_management import CompanyTabWidget

# Global imports from main.py (temporary workaround, ideally refactor these out of main)
# These might cause circular imports if main.py also imports from dialogs.py BEFORE these are needed.
# This implies that main.py should import dialogs.py functions/classes specifically where needed,
# and not necessarily at the very top if these globals are initialized later in main.py.
# For now, assuming CONFIG is available when dialogs are instantiated.
CONFIG_IMPORTED_FROM_MAIN = None
SAVE_CONFIG_IMPORTED_FROM_MAIN = None

def _import_main_globals():
    global CONFIG_IMPORTED_FROM_MAIN, SAVE_CONFIG_IMPORTED_FROM_MAIN
    if CONFIG_IMPORTED_FROM_MAIN is None or SAVE_CONFIG_IMPORTED_FROM_MAIN is None:
        import main as main_module
        CONFIG_IMPORTED_FROM_MAIN = main_module.CONFIG
        SAVE_CONFIG_IMPORTED_FROM_MAIN = main_module.save_config
    return CONFIG_IMPORTED_FROM_MAIN, SAVE_CONFIG_IMPORTED_FROM_MAIN


class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Paramètres de l'Application")); self.setMinimumSize(500, 400)
        self.current_config_data = current_config
        self.CONFIG, self.save_config = _import_main_globals() # Get globals
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
        self.lang_display_to_code = {
            self.tr("Français (fr)"): "fr",
            self.tr("English (en)"): "en",
            self.tr("العربية (ar)"): "ar",
            self.tr("Türkçe (tr)"): "tr",
            self.tr("Português (pt)"): "pt"
        }
        self.interface_lang_combo.addItems(list(self.lang_display_to_code.keys()))
        current_lang_code = self.current_config_data.get("language", "fr")
        code_to_display_text = {code: display for display, code in self.lang_display_to_code.items()}
        current_display_text = code_to_display_text.get(current_lang_code)
        if current_display_text:
            self.interface_lang_combo.setCurrentText(current_display_text)
        else:
            french_display_text = code_to_display_text.get("fr", list(self.lang_display_to_code.keys())[0])
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

        self.company_tab = CompanyTabWidget(self)
        tabs_widget.addTab(self.company_tab, self.tr("Company Details"))

        dialog_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_settings_button = dialog_button_box.button(QDialogButtonBox.Ok)
        ok_settings_button.setText(self.tr("OK"))
        ok_settings_button.setObjectName("primaryButton")
        cancel_settings_button = dialog_button_box.button(QDialogButtonBox.Cancel)
        cancel_settings_button.setText(self.tr("Annuler"))
        dialog_button_box.accepted.connect(self.accept); dialog_button_box.rejected.connect(self.reject)
        layout.addWidget(dialog_button_box)

    def browse_directory_for_input(self, line_edit_target, dialog_title):
        dir_path = QFileDialog.getExistingDirectory(self, dialog_title, line_edit_target.text())
        if dir_path: line_edit_target.setText(dir_path)

    def get_config(self):
        selected_lang_display_text = self.interface_lang_combo.currentText()
        language_code = self.lang_display_to_code.get(selected_lang_display_text, "fr")
        return {
            "templates_dir": self.templates_dir_input.text(), "clients_dir": self.clients_dir_input.text(),
            "language": language_code,
            "default_reminder_days": self.reminder_days_spinbox.value(),
            "smtp_server": self.smtp_server_input_field.text(), "smtp_port": self.smtp_port_spinbox.value(),
            "smtp_user": self.smtp_user_input_field.text(), "smtp_password": self.smtp_pass_input_field.text()
        }

class TemplateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Gestion des Modèles"))
        self.setMinimumSize(800, 500)
        self.CONFIG, _ = _import_main_globals() # Get CONFIG
        self.setup_ui()

    def setup_ui(self):
        main_hbox_layout = QHBoxLayout(self)

        left_vbox_layout = QVBoxLayout()
        left_vbox_layout.setSpacing(10)

        self.template_list = QTreeWidget()
        self.template_list.setColumnCount(4)
        self.template_list.setHeaderLabels([self.tr("Name"), self.tr("Type"), self.tr("Language"), self.tr("Default Status")])
        header = self.template_list.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.template_list.setAlternatingRowColors(True)
        font = self.template_list.font()
        font.setPointSize(font.pointSize() + 1)
        self.template_list.setFont(font)
        left_vbox_layout.addWidget(self.template_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.add_btn = QPushButton(self.tr("Ajouter")); self.add_btn.setIcon(QIcon.fromTheme("list-add")); self.add_btn.setToolTip(self.tr("Ajouter un nouveau modèle")); self.add_btn.setObjectName("primaryButton"); self.add_btn.clicked.connect(self.add_template); btn_layout.addWidget(self.add_btn)
        self.edit_btn = QPushButton(self.tr("Modifier")); self.edit_btn.setIcon(QIcon.fromTheme("document-edit")); self.edit_btn.setToolTip(self.tr("Modifier le modèle sélectionné (ouvre le fichier externe)")); self.edit_btn.clicked.connect(self.edit_template); self.edit_btn.setEnabled(False); btn_layout.addWidget(self.edit_btn)
        self.delete_btn = QPushButton(self.tr("Supprimer")); self.delete_btn.setIcon(QIcon.fromTheme("edit-delete")); self.delete_btn.setToolTip(self.tr("Supprimer le modèle sélectionné")); self.delete_btn.setObjectName("dangerButton"); self.delete_btn.clicked.connect(self.delete_template); self.delete_btn.setEnabled(False); btn_layout.addWidget(self.delete_btn)
        self.default_btn = QPushButton(self.tr("Par Défaut")); self.default_btn.setIcon(QIcon.fromTheme("emblem-default")); self.default_btn.setToolTip(self.tr("Définir le modèle sélectionné comme modèle par défaut pour sa catégorie et langue")); self.default_btn.clicked.connect(self.set_default_template); self.default_btn.setEnabled(False); btn_layout.addWidget(self.default_btn)
        left_vbox_layout.addLayout(btn_layout)
        main_hbox_layout.addLayout(left_vbox_layout, 1)

        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
        self.preview_area.setStyleSheet("QTextEdit { border: 1px solid #cccccc; background-color: #f9f9f9; padding: 5px; }")
        main_hbox_layout.addWidget(self.preview_area, 2)
        main_hbox_layout.setContentsMargins(15, 15, 15, 15)
        self.load_templates()
        self.template_list.currentItemChanged.connect(self.handle_tree_item_selection)

    def handle_tree_item_selection(self, current_item, previous_item):
        if current_item is not None and current_item.parent() is not None:
            self.show_template_preview(current_item)
            self.edit_btn.setEnabled(True); self.delete_btn.setEnabled(True); self.default_btn.setEnabled(True)
        else:
            self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
            self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(False); self.default_btn.setEnabled(False)

    def show_template_preview(self, item):
        if not item: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); return
        template_id = item.data(0, Qt.UserRole)
        if template_id is None: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); return
        try:
            details = db_manager.get_template_details_for_preview(template_id)
            if details:
                base_file_name = details['base_file_name']; language_code = details['language_code']
                template_file_path = os.path.join(self.CONFIG["templates_dir"], language_code, base_file_name)
                self.preview_area.clear()
                if os.path.exists(template_file_path):
                    _, file_extension = os.path.splitext(template_file_path); file_extension = file_extension.lower()
                    if file_extension == ".xlsx":
                        try:
                            df = pd.read_excel(template_file_path, sheet_name=0)
                            html_content = f"""<style>table {{ border-collapse: collapse; width: 95%; font-family: Arial, sans-serif; margin: 10px; }} th, td {{ border: 1px solid #cccccc; padding: 6px; text-align: left; }} th {{ background-color: #e0e0e0; font-weight: bold; }} td {{ text-align: right; }} tr:nth-child(even) {{ background-color: #f9f9f9; }} tr:hover {{ background-color: #e6f7ff; }}</style>{df.to_html(escape=False, index=False, border=0)}"""
                            self.preview_area.setHtml(html_content)
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Excel:\n{0}").format(str(e)))
                    elif file_extension == ".docx":
                        try:
                            doc = Document(template_file_path); full_text = [para.text for para in doc.paragraphs]
                            self.preview_area.setPlainText("\n".join(full_text))
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Word:\n{0}").format(str(e)))
                    elif file_extension == ".html":
                        try:
                            with open(template_file_path, "r", encoding="utf-8") as f: self.preview_area.setPlainText(f.read())
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier HTML:\n{0}").format(str(e)))
                    else: self.preview_area.setPlainText(self.tr("Aperçu non disponible pour ce type de fichier."))
                else: self.preview_area.setPlainText(self.tr("Fichier modèle introuvable."))
            else: self.preview_area.setPlainText(self.tr("Détails du modèle non trouvés dans la base de données."))
        except Exception as e_general: self.preview_area.setPlainText(self.tr("Une erreur est survenue lors de la récupération des détails du modèle:\n{0}").format(str(e_general)))

    def load_templates(self):
        self.template_list.clear(); self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
        categories = db_manager.get_all_template_categories(); categories = categories if categories else []
        for category_dict in categories:
            category_item = QTreeWidgetItem(self.template_list, [category_dict['category_name']])
            templates_in_category = db_manager.get_templates_by_category_id(category_dict['category_id']); templates_in_category = templates_in_category if templates_in_category else []
            for template_dict in templates_in_category:
                template_name = template_dict['template_name']; template_type = template_dict.get('template_type', 'N/A'); language = template_dict['language_code']; is_default = self.tr("Yes") if template_dict.get('is_default_for_type_lang') else self.tr("No")
                template_item = QTreeWidgetItem(category_item, [template_name, template_type, language, is_default]); template_item.setData(0, Qt.UserRole, template_dict['template_id'])
        self.template_list.expandAll()
        self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(False); self.default_btn.setEnabled(False)

    def add_template(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Sélectionner un modèle"), self.CONFIG["templates_dir"], self.tr("Fichiers Modèles (*.xlsx *.docx *.html);;Tous les fichiers (*)"))
        if not file_path: return
        name, ok = QInputDialog.getText(self, self.tr("Nom du Modèle"), self.tr("Entrez un nom pour ce modèle:"))
        if not ok or not name.strip(): return
        existing_categories = db_manager.get_all_template_categories(); existing_categories = existing_categories if existing_categories else []
        category_display_list = [cat['category_name'] for cat in existing_categories]; create_new_option = self.tr("[Create New Category...]"); category_display_list.append(create_new_option)
        selected_category_name, ok = QInputDialog.getItem(self, self.tr("Select Template Category"), self.tr("Category:"), category_display_list, 0, False)
        if not ok: return
        final_category_id = None
        if selected_category_name == create_new_option:
            new_category_text, ok_new = QInputDialog.getText(self, self.tr("New Category"), self.tr("Enter name for new category:"))
            if ok_new and new_category_text.strip():
                final_category_id = db_manager.add_template_category(new_category_text.strip())
                if not final_category_id: QMessageBox.warning(self, self.tr("Error"), self.tr("Could not create or find category: {0}").format(new_category_text.strip())); return
            else: return
        else:
            for cat in existing_categories:
                if cat['category_name'] == selected_category_name: final_category_id = cat['category_id']; break
            if final_category_id is None: QMessageBox.critical(self, self.tr("Error"), self.tr("Selected category not found internally.")); return
        languages = ["fr", "en", "ar", "tr", "pt"]; lang, ok = QInputDialog.getItem(self, self.tr("Langue du Modèle"), self.tr("Sélectionnez la langue:"), languages, 0, False)
        if not ok: return
        target_dir = os.path.join(self.CONFIG["templates_dir"], lang); os.makedirs(target_dir, exist_ok=True)
        base_file_name = os.path.basename(file_path); target_path = os.path.join(target_dir, base_file_name)
        file_ext = os.path.splitext(base_file_name)[1].lower(); template_type_for_db = "document_other"
        if file_ext == ".xlsx": template_type_for_db = "document_excel"
        elif file_ext == ".docx": template_type_for_db = "document_word"
        elif file_ext == ".html": template_type_for_db = "document_html"
        template_metadata = {'template_name': name.strip(), 'template_type': template_type_for_db, 'language_code': lang, 'base_file_name': base_file_name, 'description': f"Modèle {name.strip()} en {lang} ({base_file_name})", 'category_id': final_category_id, 'is_default_for_type_lang': False}; template_metadata.pop('category', None)
        try:
            shutil.copy(file_path, target_path)
            new_template_id = db_manager.add_template(template_metadata)
            if new_template_id: self.load_templates(); QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle ajouté avec succès."))
            else: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur lors de l'enregistrement du modèle dans la base de données."))
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout du modèle (fichier ou DB):\n{0}").format(str(e)))

    def edit_template(self):
        current_item = self.template_list.currentItem()
        if not current_item or not current_item.parent(): QMessageBox.warning(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un modèle à modifier.")); return
        template_id = current_item.data(0, Qt.UserRole);
        if template_id is None: return
        try:
            path_info = db_manager.get_template_path_info(template_id)
            if path_info:
                template_file_path = os.path.join(self.CONFIG["templates_dir"], path_info['language'], path_info['file_name'])
                QDesktopServices.openUrl(QUrl.fromLocalFile(template_file_path))
            else: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Impossible de récupérer les informations du modèle."))
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Erreur lors de l'ouverture du modèle:\n{0}").format(str(e)))

    def delete_template(self):
        current_item = self.template_list.currentItem()
        if not current_item or not current_item.parent(): QMessageBox.warning(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un modèle à supprimer.")); return
        template_id = current_item.data(0, Qt.UserRole);
        if template_id is None: return
        reply = QMessageBox.question(self, self.tr("Confirmer Suppression"), self.tr("Êtes-vous sûr de vouloir supprimer ce modèle ?"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                file_info = db_manager.delete_template_and_get_file_info(template_id)
                if file_info:
                    file_path_to_delete = os.path.join(self.CONFIG["templates_dir"], file_info['language'], file_info['file_name'])
                    if os.path.exists(file_path_to_delete): os.remove(file_path_to_delete)
                    self.load_templates(); QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle supprimé avec succès."))
                else: QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur de suppression du modèle."))
            except Exception as e: QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur de suppression du modèle:\n{0}").format(str(e)))

    def set_default_template(self):
        current_item = self.template_list.currentItem()
        if not current_item or not current_item.parent(): QMessageBox.warning(self, self.tr("Sélection Requise"), self.tr("Veuillez sélectionner un modèle à définir par défaut.")); return
        template_id = current_item.data(0, Qt.UserRole);
        if template_id is None: return
        try:
            success = db_manager.set_default_template_by_id(template_id)
            if success: self.load_templates(); QMessageBox.information(self, self.tr("Succès"), self.tr("Modèle défini comme modèle par défaut."))
            else: QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Erreur de mise à jour du modèle."))
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la définition du modèle par défaut:\n{0}").format(str(e)))

# Ensure QCoreApplication.translate can be used by defining tr for the module if needed,
# or ensure these dialogs are always parented by a QObject that has tr correctly setup.
# For simplicity, assuming parent provides tr() or QCoreApplication.translate is used directly.
# Example: self.tr = parent.tr if parent else QCoreApplication.translate
