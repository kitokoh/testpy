# -*- coding: utf-8 -*-
import os
import json
import shutil
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import io

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QSpinBox, QDialogButtonBox,
    QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QTextEdit,
    QInputDialog, QMessageBox, QFrame, QLabel, QListWidget, QListWidgetItem, QCheckBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QDoubleSpinBox,
    QGridLayout, QGroupBox
)
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QColor, QBrush
from PyQt5.QtCore import Qt, QUrl, QCoreApplication, QDate

import pandas as pd
from docx import Document
from PyPDF2 import PdfMerger
from reportlab.pdfgen import canvas

import db as db_manager
from company_management import CompanyTabWidget
from excel_editor import ExcelEditor
from html_editor import HtmlEditor
from pagedegrde import generate_cover_page_logic, APP_CONFIG as PAGEDEGRDE_APP_CONFIG
from utils import populate_docx_template, load_config as utils_load_config, save_config as utils_save_config

# APP_ROOT_DIR is now passed to CompilePdfDialog constructor where needed.
# The global import from main is removed.

class SettingsDialog(QDialog):
    def __init__(self, main_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Paramètres de l'Application")); self.setMinimumSize(500, 400)
        self.current_config_data = main_config
        self.CONFIG = main_config
        self.save_config = utils_save_config
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
            self.tr("Français (fr)"): "fr", self.tr("English (en)"): "en",
            self.tr("العربية (ar)"): "ar", self.tr("Türkçe (tr)"): "tr",
            self.tr("Português (pt)"): "pt"
        }
        self.interface_lang_combo.addItems(list(self.lang_display_to_code.keys()))
        current_lang_code = self.current_config_data.get("language", "fr")
        code_to_display_text = {code: display for display, code in self.lang_display_to_code.items()}
        current_display_text = code_to_display_text.get(current_lang_code)
        if current_display_text: self.interface_lang_combo.setCurrentText(current_display_text)
        else: self.interface_lang_combo.setCurrentText(code_to_display_text.get("fr", list(self.lang_display_to_code.keys())[0]))
        general_form_layout.addRow(self.tr("Langue Interface (redémarrage requis):"), self.interface_lang_combo)
        self.reminder_days_spinbox = QSpinBox(); self.reminder_days_spinbox.setRange(1, 365)
        self.reminder_days_spinbox.setValue(self.current_config_data.get("default_reminder_days", 30))
        general_form_layout.addRow(self.tr("Jours avant rappel client ancien:"), self.reminder_days_spinbox)
        tabs_widget.addTab(general_tab_widget, self.tr("Général"))
        email_tab_widget = QWidget(); email_form_layout = QFormLayout(email_tab_widget)
        self.smtp_server_input_field = QLineEdit(self.current_config_data.get("smtp_server", ""))
        email_form_layout.addRow(self.tr("Serveur SMTP:"), self.smtp_server_input_field)
        self.smtp_port_spinbox = QSpinBox(); self.smtp_port_spinbox.setRange(1, 65535); self.smtp_port_spinbox.setValue(self.current_config_data.get("smtp_port", 587))
        email_form_layout.addRow(self.tr("Port SMTP:"), self.smtp_port_spinbox)
        self.smtp_user_input_field = QLineEdit(self.current_config_data.get("smtp_user", ""))
        email_form_layout.addRow(self.tr("Utilisateur SMTP:"), self.smtp_user_input_field)
        self.smtp_pass_input_field = QLineEdit(self.current_config_data.get("smtp_password", "")); self.smtp_pass_input_field.setEchoMode(QLineEdit.Password)
        email_form_layout.addRow(self.tr("Mot de passe SMTP:"), self.smtp_pass_input_field)
        tabs_widget.addTab(email_tab_widget, self.tr("Email"))
        self.company_tab = CompanyTabWidget(self); tabs_widget.addTab(self.company_tab, self.tr("Company Details"))
        dialog_button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_settings_button = dialog_button_box.button(QDialogButtonBox.Ok); ok_settings_button.setText(self.tr("OK")); ok_settings_button.setObjectName("primaryButton")
        cancel_settings_button = dialog_button_box.button(QDialogButtonBox.Cancel); cancel_settings_button.setText(self.tr("Annuler"))
        dialog_button_box.accepted.connect(self.accept); dialog_button_box.rejected.connect(self.reject)
        layout.addWidget(dialog_button_box)

    def browse_directory_for_input(self, line_edit_target, dialog_title):
        dir_path = QFileDialog.getExistingDirectory(self, dialog_title, line_edit_target.text())
        if dir_path: line_edit_target.setText(dir_path)

    def get_config(self):
        selected_lang_display_text = self.interface_lang_combo.currentText()
        language_code = self.lang_display_to_code.get(selected_lang_display_text, "fr")
        return {"templates_dir": self.templates_dir_input.text(), "clients_dir": self.clients_dir_input.text(),
                "language": language_code, "default_reminder_days": self.reminder_days_spinbox.value(),
                "smtp_server": self.smtp_server_input_field.text(), "smtp_port": self.smtp_port_spinbox.value(),
                "smtp_user": self.smtp_user_input_field.text(), "smtp_password": self.smtp_pass_input_field.text()}

class TemplateDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Gestion des Modèles"))
        self.setMinimumSize(800, 500)
        self.config = config
        self.setup_ui()

    def setup_ui(self):
        main_hbox_layout = QHBoxLayout(self); left_vbox_layout = QVBoxLayout(); left_vbox_layout.setSpacing(10)
        self.template_list = QTreeWidget(); self.template_list.setColumnCount(4)
        self.template_list.setHeaderLabels([self.tr("Name"), self.tr("Type"), self.tr("Language"), self.tr("Default Status")])
        header = self.template_list.header(); header.setSectionResizeMode(0, QHeaderView.Stretch); header.setSectionResizeMode(1, QHeaderView.ResizeToContents); header.setSectionResizeMode(2, QHeaderView.ResizeToContents); header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.template_list.setAlternatingRowColors(True); font = self.template_list.font(); font.setPointSize(font.pointSize() + 1); self.template_list.setFont(font)
        left_vbox_layout.addWidget(self.template_list)
        btn_layout = QHBoxLayout(); btn_layout.setSpacing(8)
        self.add_btn = QPushButton(self.tr("Ajouter")); self.add_btn.setIcon(QIcon(":/icons/add.svg")); self.add_btn.setToolTip(self.tr("Ajouter un nouveau modèle")); self.add_btn.setObjectName("primaryButton"); self.add_btn.clicked.connect(self.add_template); btn_layout.addWidget(self.add_btn)
        self.edit_btn = QPushButton(self.tr("Modifier")); self.edit_btn.setIcon(QIcon(":/icons/edit.svg")); self.edit_btn.setToolTip(self.tr("Modifier le modèle sélectionné (ouvre le fichier externe)")); self.edit_btn.clicked.connect(self.edit_template); self.edit_btn.setEnabled(False); btn_layout.addWidget(self.edit_btn)
        self.delete_btn = QPushButton(self.tr("Supprimer")); self.delete_btn.setIcon(QIcon(":/icons/delete.svg")); self.delete_btn.setToolTip(self.tr("Supprimer le modèle sélectionné")); self.delete_btn.setObjectName("dangerButton"); self.delete_btn.clicked.connect(self.delete_template); self.delete_btn.setEnabled(False); btn_layout.addWidget(self.delete_btn)
        self.default_btn = QPushButton(self.tr("Par Défaut")); self.default_btn.setIcon(QIcon.fromTheme("emblem-default")); self.default_btn.setToolTip(self.tr("Définir le modèle sélectionné comme modèle par défaut pour sa catégorie et langue")); self.default_btn.clicked.connect(self.set_default_template); self.default_btn.setEnabled(False); btn_layout.addWidget(self.default_btn) # emblem-default not in list yet
        left_vbox_layout.addLayout(btn_layout); main_hbox_layout.addLayout(left_vbox_layout, 1)
        self.preview_area = QTextEdit(); self.preview_area.setReadOnly(True); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
        self.preview_area.setObjectName("templatePreviewArea")
        main_hbox_layout.addWidget(self.preview_area, 2); main_hbox_layout.setContentsMargins(15,15,15,15); self.load_templates(); self.template_list.currentItemChanged.connect(self.handle_tree_item_selection)

    def handle_tree_item_selection(self,current_item,previous_item):
        if current_item is not None and current_item.parent() is not None: self.show_template_preview(current_item); self.edit_btn.setEnabled(True); self.delete_btn.setEnabled(True); self.default_btn.setEnabled(True)
        else: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(False); self.default_btn.setEnabled(False)

    def show_template_preview(self, item):
        if not item: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); return
        template_id=item.data(0,Qt.UserRole);
        if template_id is None: self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu.")); return
        try:
            details=db_manager.get_template_details_for_preview(template_id)
            if details:
                base_file_name=details['base_file_name']; language_code=details['language_code']; template_file_path=os.path.join(self.config["templates_dir"],language_code,base_file_name)
                self.preview_area.clear()
                if os.path.exists(template_file_path):
                    _,file_extension=os.path.splitext(template_file_path); file_extension=file_extension.lower()
                    if file_extension==".xlsx":
                        try:
                            df=pd.read_excel(template_file_path,sheet_name=0); html_content=f"""<style>table {{ border-collapse: collapse; width: 95%; font-family: Arial, sans-serif; margin: 10px; }} th, td {{ border: 1px solid #cccccc; padding: 6px; text-align: left; }} th {{ background-color: #e0e0e0; font-weight: bold; }} td {{ text-align: right; }} tr:nth-child(even) {{ background-color: #f9f9f9; }} tr:hover {{ background-color: #e6f7ff; }}</style>{df.to_html(escape=False,index=False,border=0)}"""; self.preview_area.setHtml(html_content)
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Excel:\n{0}").format(str(e)))
                    elif file_extension==".docx":
                        try: doc=Document(template_file_path); full_text=[para.text for para in doc.paragraphs]; self.preview_area.setPlainText("\n".join(full_text))
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier Word:\n{0}").format(str(e)))
                    elif file_extension==".html":
                        try:
                            with open(template_file_path,"r",encoding="utf-8") as f: self.preview_area.setPlainText(f.read())
                        except Exception as e: self.preview_area.setPlainText(self.tr("Erreur de lecture du fichier HTML:\n{0}").format(str(e)))
                    else: self.preview_area.setPlainText(self.tr("Aperçu non disponible pour ce type de fichier."))
                else: self.preview_area.setPlainText(self.tr("Fichier modèle introuvable."))
            else: self.preview_area.setPlainText(self.tr("Détails du modèle non trouvés dans la base de données."))
        except Exception as e_general: self.preview_area.setPlainText(self.tr("Une erreur est survenue lors de la récupération des détails du modèle:\n{0}").format(str(e_general)))

    def load_templates(self):
        self.template_list.clear(); self.preview_area.clear(); self.preview_area.setPlaceholderText(self.tr("Sélectionnez un modèle pour afficher un aperçu."))
        categories=db_manager.get_all_template_categories(); categories=categories if categories else []
        for category_dict in categories:
            category_item=QTreeWidgetItem(self.template_list,[category_dict['category_name']])
            templates_in_category=db_manager.get_templates_by_category_id(category_dict['category_id']); templates_in_category=templates_in_category if templates_in_category else []
            for template_dict in templates_in_category:
                template_name=template_dict['template_name']; template_type=template_dict.get('template_type','N/A'); language=template_dict['language_code']; is_default=self.tr("Yes") if template_dict.get('is_default_for_type_lang') else self.tr("No")
                template_item=QTreeWidgetItem(category_item,[template_name,template_type,language,is_default]); template_item.setData(0,Qt.UserRole,template_dict['template_id'])
        self.template_list.expandAll(); self.edit_btn.setEnabled(False); self.delete_btn.setEnabled(False); self.default_btn.setEnabled(False)

    def add_template(self):
        file_path,_=QFileDialog.getOpenFileName(self,self.tr("Sélectionner un modèle"),self.config["templates_dir"],self.tr("Fichiers Modèles (*.xlsx *.docx *.html);;Tous les fichiers (*)"))
        if not file_path:return
        name,ok=QInputDialog.getText(self,self.tr("Nom du Modèle"),self.tr("Entrez un nom pour ce modèle:"))
        if not ok or not name.strip():return
        existing_categories=db_manager.get_all_template_categories(); existing_categories=existing_categories if existing_categories else []
        category_display_list=[cat['category_name'] for cat in existing_categories]; create_new_option=self.tr("[Create New Category...]"); category_display_list.append(create_new_option)
        selected_category_name,ok=QInputDialog.getItem(self,self.tr("Select Template Category"),self.tr("Category:"),category_display_list,0,False)
        if not ok:return
        final_category_id=None
        if selected_category_name==create_new_option:
            new_category_text,ok_new=QInputDialog.getText(self,self.tr("New Category"),self.tr("Enter name for new category:"))
            if ok_new and new_category_text.strip(): final_category_id=db_manager.add_template_category(new_category_text.strip());
            if not final_category_id:QMessageBox.warning(self,self.tr("Error"),self.tr("Could not create or find category: {0}").format(new_category_text.strip()));return
            else:return
        else:
            found_cat=next((cat for cat in existing_categories if cat['category_name']==selected_category_name),None)
            if found_cat:final_category_id=found_cat['category_id']
            else:QMessageBox.critical(self,self.tr("Error"),self.tr("Selected category not found internally."));return
        languages=["fr","en","ar","tr","pt"]; lang,ok=QInputDialog.getItem(self,self.tr("Langue du Modèle"),self.tr("Sélectionnez la langue:"),languages,0,False)
        if not ok:return
        target_dir=os.path.join(self.config["templates_dir"],lang); os.makedirs(target_dir,exist_ok=True)
        base_file_name=os.path.basename(file_path); target_path=os.path.join(target_dir,base_file_name)
        file_ext=os.path.splitext(base_file_name)[1].lower(); template_type_for_db="document_other"
        if file_ext==".xlsx":template_type_for_db="document_excel"
        elif file_ext==".docx":template_type_for_db="document_word"
        elif file_ext==".html":template_type_for_db="document_html"
        template_metadata={'template_name':name.strip(),'template_type':template_type_for_db,'language_code':lang,'base_file_name':base_file_name,'description':f"Modèle {name.strip()} en {lang} ({base_file_name})",'category_id':final_category_id,'is_default_for_type_lang':False}
        try:
            shutil.copy(file_path,target_path); new_template_id=db_manager.add_template(template_metadata)
            if new_template_id:self.load_templates();QMessageBox.information(self,self.tr("Succès"),self.tr("Modèle ajouté avec succès."))
            else:QMessageBox.critical(self,self.tr("Erreur DB"),self.tr("Erreur lors de l'enregistrement du modèle dans la base de données."))
        except Exception as e:QMessageBox.critical(self,self.tr("Erreur"),self.tr("Erreur lors de l'ajout du modèle (fichier ou DB):\n{0}").format(str(e)))

    def edit_template(self):
        current_item=self.template_list.currentItem()
        if not current_item or not current_item.parent():QMessageBox.warning(self,self.tr("Sélection Requise"),self.tr("Veuillez sélectionner un modèle à modifier."));return
        template_id=current_item.data(0,Qt.UserRole);
        if template_id is None:return
        try:
            path_info=db_manager.get_template_path_info(template_id)
            if path_info:template_file_path=os.path.join(self.config["templates_dir"],path_info['language'],path_info['file_name']); QDesktopServices.openUrl(QUrl.fromLocalFile(template_file_path))
            else:QMessageBox.warning(self,self.tr("Erreur"),self.tr("Impossible de récupérer les informations du modèle."))
        except Exception as e:QMessageBox.warning(self,self.tr("Erreur"),self.tr("Erreur lors de l'ouverture du modèle:\n{0}").format(str(e)))

    def delete_template(self):
        current_item=self.template_list.currentItem()
        if not current_item or not current_item.parent():QMessageBox.warning(self,self.tr("Sélection Requise"),self.tr("Veuillez sélectionner un modèle à supprimer."));return
        template_id=current_item.data(0,Qt.UserRole);
        if template_id is None:return
        reply=QMessageBox.question(self,self.tr("Confirmer Suppression"),self.tr("Êtes-vous sûr de vouloir supprimer ce modèle ?"),QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if reply==QMessageBox.Yes:
            try:
                file_info=db_manager.delete_template_and_get_file_info(template_id)
                if file_info:
                    file_path_to_delete=os.path.join(self.config["templates_dir"],file_info['language'],file_info['file_name'])
                    if os.path.exists(file_path_to_delete):os.remove(file_path_to_delete)
                    self.load_templates();QMessageBox.information(self,self.tr("Succès"),self.tr("Modèle supprimé avec succès."))
                else:QMessageBox.critical(self,self.tr("Erreur"),self.tr("Erreur de suppression du modèle."))
            except Exception as e:QMessageBox.critical(self,self.tr("Erreur"),self.tr("Erreur de suppression du modèle:\n{0}").format(str(e)))

    def set_default_template(self):
        current_item=self.template_list.currentItem()
        if not current_item or not current_item.parent():QMessageBox.warning(self,self.tr("Sélection Requise"),self.tr("Veuillez sélectionner un modèle à définir par défaut."));return
        template_id=current_item.data(0,Qt.UserRole);
        if template_id is None:return
        try:
            success=db_manager.set_default_template_by_id(template_id)
            if success:self.load_templates();QMessageBox.information(self,self.tr("Succès"),self.tr("Modèle défini comme modèle par défaut."))
            else:QMessageBox.critical(self,self.tr("Erreur DB"),self.tr("Erreur de mise à jour du modèle."))
        except Exception as e:QMessageBox.critical(self,self.tr("Erreur"),self.tr("Erreur lors de la définition du modèle par défaut:\n{0}").format(str(e)))

class ContactDialog(QDialog):
    def __init__(self, client_id=None, contact_data=None, parent=None):
        super().__init__(parent)
        self.client_id = client_id; self.contact_data = contact_data or {}
        self.setWindowTitle(self.tr("Modifier Contact") if self.contact_data else self.tr("Ajouter Contact"))
        self.setMinimumSize(450,380); self.setup_ui()
    def _create_icon_label_widget(self,icon_name,label_text):
        widget=QWidget();layout=QHBoxLayout(widget);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5)
        icon_label=QLabel();icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16,16));layout.addWidget(icon_label);layout.addWidget(QLabel(label_text));return widget
    def setup_ui(self):
        main_layout=QVBoxLayout(self);main_layout.setSpacing(15)
        header_label=QLabel(self.tr("Ajouter Nouveau Contact") if not self.contact_data else self.tr("Modifier Détails Contact")); header_label.setObjectName("dialogHeaderLabel"); main_layout.addWidget(header_label)
        form_layout=QFormLayout();form_layout.setSpacing(10);form_layout.setContentsMargins(10,0,10,0)
        # self.setStyleSheet("QLineEdit, QCheckBox { padding: 3px; }") # Prefer global styles
        self.name_input=QLineEdit(self.contact_data.get("name",""));form_layout.addRow(self._create_icon_label_widget("user",self.tr("Nom complet:")),self.name_input)
        self.email_input=QLineEdit(self.contact_data.get("email",""));form_layout.addRow(self._create_icon_label_widget("mail-message-new",self.tr("Email:")),self.email_input)
        self.phone_input=QLineEdit(self.contact_data.get("phone",""));form_layout.addRow(self._create_icon_label_widget("phone",self.tr("Téléphone:")),self.phone_input)
        self.position_input=QLineEdit(self.contact_data.get("position",""));form_layout.addRow(self._create_icon_label_widget("preferences-desktop-user",self.tr("Poste:")),self.position_input)
        self.primary_check=QCheckBox(self.tr("Contact principal"));self.primary_check.setChecked(bool(self.contact_data.get("is_primary",0)));self.primary_check.stateChanged.connect(self.update_primary_contact_visuals);form_layout.addRow(self._create_icon_label_widget("emblem-important",self.tr("Principal:")),self.primary_check)
        main_layout.addLayout(form_layout);main_layout.addStretch()
        button_frame=QFrame(self);button_frame.setObjectName("buttonFrame") # Style in QSS
        button_frame_layout=QHBoxLayout(button_frame);button_frame_layout.setContentsMargins(0,0,0,0)
        button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        ok_button=button_box.button(QDialogButtonBox.Ok);ok_button.setText(self.tr("OK"));ok_button.setIcon(QIcon(":/icons/dialog-ok-apply.svg"));ok_button.setObjectName("primaryButton")
        cancel_button=button_box.button(QDialogButtonBox.Cancel);cancel_button.setText(self.tr("Annuler"));cancel_button.setIcon(QIcon(":/icons/dialog-cancel.svg"))
        button_box.accepted.connect(self.accept);button_box.rejected.connect(self.reject);button_frame_layout.addWidget(button_box);main_layout.addWidget(button_frame)
        self.update_primary_contact_visuals(self.primary_check.checkState())
    def update_primary_contact_visuals(self,state):
        # Dynamic style based on state - kept inline
        # Padding will be inherited from global QLineEdit style
        if state==Qt.Checked:
            self.name_input.setStyleSheet("background-color: #E8F5E9;") # Light Green from palette
        else:
            self.name_input.setStyleSheet("") # Reset to default QSS
    def get_data(self):return{"name":self.name_input.text().strip(),"email":self.email_input.text().strip(),"phone":self.phone_input.text().strip(),"position":self.position_input.text().strip(),"is_primary":1 if self.primary_check.isChecked() else 0}

class ProductDialog(QDialog):
    def __init__(self,client_id,product_data=None,parent=None):super().__init__(parent);self.client_id=client_id;self.setWindowTitle(self.tr("Ajouter Produits au Client"));self.setMinimumSize(900,800);self.client_info=db_manager.get_client_by_id(self.client_id);self.setup_ui();self._set_initial_language_filter();self._filter_products_by_language_and_search()
    def _set_initial_language_filter(self):
        primary_language=None
        if self.client_info:client_langs=self.client_info.get('selected_languages');
        if client_langs:primary_language=client_langs.split(',')[0].strip()
        if primary_language:
            for i in range(self.product_language_filter_combo.count()):
                if self.product_language_filter_combo.itemText(i)==primary_language:self.product_language_filter_combo.setCurrentText(primary_language);break
    def _filter_products_by_language_and_search(self):
        self.existing_products_list.clear();selected_language=self.product_language_filter_combo.currentText();language_code_for_db=None if selected_language==self.tr("All") else selected_language;search_text=self.search_existing_product_input.text().lower();name_pattern_for_db=f"%{search_text}%" if search_text else None
        try:
            products=db_manager.get_all_products_for_selection_filtered(language_code=language_code_for_db,name_pattern=name_pattern_for_db)
            if products is None:products=[]
            for product_data in products:
                product_name=product_data.get('product_name','N/A');description=product_data.get('description','');base_unit_price=product_data.get('base_unit_price',0.0)
                if base_unit_price is None:base_unit_price=0.0
                desc_snippet=(description[:30]+'...') if len(description)>30 else description;display_text=f"{product_name} (Desc: {desc_snippet}, Prix: {base_unit_price:.2f} €)"
                item=QListWidgetItem(display_text);item.setData(Qt.UserRole,product_data);self.existing_products_list.addItem(item)
        except Exception as e:print(f"Error loading existing products: {e}");QMessageBox.warning(self,self.tr("Erreur Chargement Produits"),self.tr("Impossible de charger la liste des produits existants:\n{0}").format(str(e)))
    def _populate_form_from_selected_product(self,item):
        product_data=item.data(Qt.UserRole)
        if product_data:
            self.name_input.setText(product_data.get('product_name',''));self.description_input.setPlainText(product_data.get('description',''));base_price=product_data.get('base_unit_price',0.0)
            try:self.unit_price_input.setValue(float(base_price))
            except(ValueError,TypeError):self.unit_price_input.setValue(0.0)
            self.quantity_input.setValue(1.0);self.quantity_input.setFocus();self._update_current_line_total_preview()
    def _create_icon_label_widget(self,icon_name,label_text):widget=QWidget();layout=QHBoxLayout(widget);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5);icon_label=QLabel();icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16,16));layout.addWidget(icon_label);layout.addWidget(QLabel(label_text));return widget
    def setup_ui(self):
        main_layout=QVBoxLayout(self);main_layout.setSpacing(15);header_label=QLabel(self.tr("Ajouter Lignes de Produits")); header_label.setObjectName("dialogHeaderLabel"); main_layout.addWidget(header_label)
        two_columns_layout=QHBoxLayout();search_group_box=QGroupBox(self.tr("Rechercher Produit Existant"));search_layout=QVBoxLayout(search_group_box)
        self.product_language_filter_label=QLabel(self.tr("Filtrer par langue:"));search_layout.addWidget(self.product_language_filter_label);self.product_language_filter_combo=QComboBox();self.product_language_filter_combo.addItems([self.tr("All"),"fr","en","ar","tr","pt"]);self.product_language_filter_combo.currentTextChanged.connect(self._filter_products_by_language_and_search);search_layout.addWidget(self.product_language_filter_combo)
        self.search_existing_product_input=QLineEdit();self.search_existing_product_input.setPlaceholderText(self.tr("Tapez pour rechercher..."));self.search_existing_product_input.textChanged.connect(self._filter_products_by_language_and_search);search_layout.addWidget(self.search_existing_product_input)
        self.existing_products_list=QListWidget();self.existing_products_list.setMinimumHeight(150);self.existing_products_list.itemDoubleClicked.connect(self._populate_form_from_selected_product);search_layout.addWidget(self.existing_products_list);two_columns_layout.addWidget(search_group_box,1)
        input_group_box=QGroupBox(self.tr("Détails de la Ligne de Produit Actuelle (ou Produit Sélectionné)"));form_layout=QFormLayout(input_group_box);form_layout.setSpacing(10); # self.setStyleSheet("QLineEdit, QTextEdit, QDoubleSpinBox { padding: 3px; }") # Prefer global
        self.name_input=QLineEdit();form_layout.addRow(self._create_icon_label_widget("package-x-generic",self.tr("Nom du Produit:")),self.name_input);self.description_input=QTextEdit();self.description_input.setFixedHeight(80);form_layout.addRow(self.tr("Description:"),self.description_input)
        self.quantity_input=QDoubleSpinBox();self.quantity_input.setRange(0,1000000);self.quantity_input.setValue(0.0);self.quantity_input.valueChanged.connect(self._update_current_line_total_preview);form_layout.addRow(self._create_icon_label_widget("format-list-numbered",self.tr("Quantité:")),self.quantity_input)
        self.unit_price_input=QDoubleSpinBox();self.unit_price_input.setRange(0,10000000);self.unit_price_input.setPrefix("€ ");self.unit_price_input.setValue(0.0);self.unit_price_input.valueChanged.connect(self._update_current_line_total_preview);form_layout.addRow(self._create_icon_label_widget("cash",self.tr("Prix Unitaire:")),self.unit_price_input)
        current_line_total_title_label=QLabel(self.tr("Total Ligne Actuelle:"));self.current_line_total_label=QLabel("€ 0.00");font=self.current_line_total_label.font();font.setBold(True);self.current_line_total_label.setFont(font);form_layout.addRow(current_line_total_title_label,self.current_line_total_label);two_columns_layout.addWidget(input_group_box,2);main_layout.addLayout(two_columns_layout)
        self.add_line_btn=QPushButton(self.tr("Ajouter Produit à la Liste"));self.add_line_btn.setIcon(QIcon(":/icons/list-add.svg"));self.add_line_btn.setObjectName("primaryButton");self.add_line_btn.clicked.connect(self._add_current_line_to_table);main_layout.addWidget(self.add_line_btn)
        self.products_table=QTableWidget();self.products_table.setColumnCount(5);self.products_table.setHorizontalHeaderLabels([self.tr("Nom Produit"),self.tr("Description"),self.tr("Qté"),self.tr("Prix Unitaire"),self.tr("Total Ligne")]);self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.products_table.setSelectionBehavior(QAbstractItemView.SelectRows);self.products_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);self.products_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);self.products_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeToContents);self.products_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeToContents);self.products_table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeToContents);main_layout.addWidget(self.products_table)
        self.remove_line_btn=QPushButton(self.tr("Supprimer Produit Sélectionné"));self.remove_line_btn.setIcon(QIcon(":/icons/list-remove.svg")); self.remove_line_btn.setObjectName("removeProductLineButton"); self.remove_line_btn.clicked.connect(self._remove_selected_line_from_table);main_layout.addWidget(self.remove_line_btn) # Added objectName
        self.overall_total_label=QLabel(self.tr("Total Général: € 0.00")); font=self.overall_total_label.font();font.setPointSize(font.pointSize()+3);font.setBold(True);self.overall_total_label.setFont(font); self.overall_total_label.setObjectName("overallTotalLabel"); self.overall_total_label.setAlignment(Qt.AlignRight);main_layout.addWidget(self.overall_total_label);main_layout.addStretch()
        button_frame=QFrame(self);button_frame.setObjectName("buttonFrame"); button_frame_layout=QHBoxLayout(button_frame);button_frame_layout.setContentsMargins(0,0,0,0) # Style in QSS
        button_box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);ok_button=button_box.button(QDialogButtonBox.Ok);ok_button.setText(self.tr("OK"));ok_button.setIcon(QIcon(":/icons/dialog-ok-apply.svg"));ok_button.setObjectName("primaryButton");cancel_button=button_box.button(QDialogButtonBox.Cancel);cancel_button.setText(self.tr("Annuler"));cancel_button.setIcon(QIcon(":/icons/dialog-cancel.svg"));button_box.accepted.connect(self.accept);button_box.rejected.connect(self.reject);button_frame_layout.addWidget(button_box);main_layout.addWidget(button_frame)
    def _update_current_line_total_preview(self):quantity=self.quantity_input.value();unit_price=self.unit_price_input.value();current_quantity=quantity if isinstance(quantity,(int,float)) else 0.0;current_unit_price=unit_price if isinstance(unit_price,(int,float)) else 0.0;line_total=current_quantity*current_unit_price;self.current_line_total_label.setText(f"€ {line_total:.2f}")
    def _add_current_line_to_table(self):
        name=self.name_input.text().strip();description=self.description_input.toPlainText().strip();quantity=self.quantity_input.value();unit_price=self.unit_price_input.value()
        if not name:QMessageBox.warning(self,self.tr("Champ Requis"),self.tr("Le nom du produit est requis."));self.name_input.setFocus();return
        if quantity<=0:QMessageBox.warning(self,self.tr("Quantité Invalide"),self.tr("La quantité doit être supérieure à zéro."));self.quantity_input.setFocus();return
        line_total=quantity*unit_price;row_position=self.products_table.rowCount();self.products_table.insertRow(row_position);name_item=QTableWidgetItem(name);current_lang_code=self.product_language_filter_combo.currentText()
        if current_lang_code==self.tr("All"):current_lang_code="fr"
        name_item.setData(Qt.UserRole+1,current_lang_code);self.products_table.setItem(row_position,0,name_item);self.products_table.setItem(row_position,1,QTableWidgetItem(description));qty_item=QTableWidgetItem(f"{quantity:.2f}");qty_item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter);self.products_table.setItem(row_position,2,qty_item);price_item=QTableWidgetItem(f"€ {unit_price:.2f}");price_item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter);self.products_table.setItem(row_position,3,price_item);total_item=QTableWidgetItem(f"€ {line_total:.2f}");total_item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter);self.products_table.setItem(row_position,4,total_item)
        self.name_input.clear();self.description_input.clear();self.quantity_input.setValue(0.0);self.unit_price_input.setValue(0.0);self._update_current_line_total_preview();self._update_overall_total();self.name_input.setFocus()
    def _remove_selected_line_from_table(self):
        selected_rows = self.products_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, self.tr("Aucune Sélection"), self.tr("Veuillez sélectionner une ligne à supprimer."))
            return
        for index in sorted(selected_rows, reverse=True):
            self.products_table.removeRow(index.row())
        self._update_overall_total()
    def _update_overall_total(self):
        total_sum=0.0
        for row in range(self.products_table.rowCount()):
            item=self.products_table.item(row,4)
            if item and item.text():
                try:value_str=item.text().replace("€","").replace(",",".").strip();total_sum+=float(value_str)
                except ValueError:print(f"Warning: Could not parse float from table cell: {item.text()}")
        self.overall_total_label.setText(self.tr("Total Général: € {0:.2f}").format(total_sum))
    def get_data(self):
        products_list=[]
        for row in range(self.products_table.rowCount()):
            name=self.products_table.item(row,0).text();description=self.products_table.item(row,1).text();qty_str=self.products_table.item(row,2).text().replace(",",".");quantity=float(qty_str) if qty_str else 0.0;unit_price_str=self.products_table.item(row,3).text().replace("€","").replace(",",".").strip();unit_price=float(unit_price_str) if unit_price_str else 0.0;line_total_str=self.products_table.item(row,4).text().replace("€","").replace(",",".").strip();line_total=float(line_total_str) if line_total_str else 0.0;name_item=self.products_table.item(row,0);language_code=name_item.data(Qt.UserRole+1) if name_item else "fr"
            products_list.append({"client_id":self.client_id,"name":name,"description":description,"quantity":quantity,"unit_price":unit_price,"total_price":line_total,"language_code":language_code})
        return products_list

class EditProductLineDialog(QDialog):
    def __init__(self, product_data, parent=None):
        super().__init__(parent)
        self.product_data = product_data
        self.setWindowTitle(self.tr("Modifier Ligne de Produit"))
        self.setMinimumSize(450, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout(); form_layout.setSpacing(10)
        self.name_input = QLineEdit(self.product_data.get('name', ''))
        form_layout.addRow(self.tr("Nom du Produit:"), self.name_input)
        self.description_input = QTextEdit(self.product_data.get('description', ''))
        self.description_input.setFixedHeight(80)
        form_layout.addRow(self.tr("Description:"), self.description_input)
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0.01, 1000000)
        self.quantity_input.setValue(float(self.product_data.get('quantity', 1.0)))
        form_layout.addRow(self.tr("Quantité:"), self.quantity_input)
        self.unit_price_input = QDoubleSpinBox()
        self.unit_price_input.setRange(0.00, 10000000); self.unit_price_input.setPrefix("€ "); self.unit_price_input.setDecimals(2)
        self.unit_price_input.setValue(float(self.product_data.get('unit_price', 0.0)))
        form_layout.addRow(self.tr("Prix Unitaire:"), self.unit_price_input)
        layout.addLayout(form_layout); layout.addStretch()
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK")); button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        button_box.accepted.connect(self.accept); button_box.rejected.connect(self.reject)
        layout.addWidget(button_box); self.setLayout(layout)

    def get_data(self) -> dict:
        return {"name": self.name_input.text().strip(), "description": self.description_input.toPlainText().strip(),
                "quantity": self.quantity_input.value(), "unit_price": self.unit_price_input.value(),
                "product_id": self.product_data.get('product_id'), "client_project_product_id": self.product_data.get('client_project_product_id')}

class CreateDocumentDialog(QDialog):
    def __init__(self, client_info, config, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.config = config # Store config passed from main
        self.setWindowTitle(self.tr("Créer des Documents"))
        self.setMinimumSize(600, 500)
        self._initial_load_complete = False
        self.setup_ui()

    def _create_icon_label_widget(self, icon_name, label_text):
        widget = QWidget(); layout = QHBoxLayout(widget); layout.setContentsMargins(0,0,0,0); layout.setSpacing(5)
        icon_label = QLabel(); icon_label.setPixmap(QIcon.fromTheme(icon_name).pixmap(16,16)); layout.addWidget(icon_label); layout.addWidget(QLabel(label_text))
        return widget

    def setup_ui(self):
        main_layout = QVBoxLayout(self); main_layout.setSpacing(15)
        header_label = QLabel(self.tr("Sélectionner Documents à Créer")); header_label.setObjectName("dialogHeaderLabel")
        main_layout.addWidget(header_label)
        # self.setStyleSheet("QComboBox, QListWidget, QLineEdit { padding: 3px; } QListWidget::item:hover { background-color: #e6f7ff; }") # Prefer global styles
        filters_layout = QGridLayout(); filters_layout.setSpacing(10)
        self.language_filter_label = QLabel(self.tr("Langue:")); self.language_filter_combo = QComboBox()
        self.language_filter_combo.addItems([self.tr("All"), "fr", "en", "ar", "tr", "pt"]); self.language_filter_combo.setCurrentText(self.tr("All"))
        filters_layout.addWidget(self.language_filter_label, 0, 0); filters_layout.addWidget(self.language_filter_combo, 0, 1)
        self.extension_filter_label = QLabel(self.tr("Extension:")); self.extension_filter_combo = QComboBox()
        self.extension_filter_combo.addItems([self.tr("All"), "HTML", "XLSX", "DOCX"]); self.extension_filter_combo.setCurrentText("HTML")
        filters_layout.addWidget(self.extension_filter_label, 0, 2); filters_layout.addWidget(self.extension_filter_combo, 0, 3)
        self.search_bar_label = QLabel(self.tr("Rechercher:")); self.search_bar = QLineEdit(); self.search_bar.setPlaceholderText(self.tr("Filtrer par nom..."))
        filters_layout.addWidget(self.search_bar_label, 1, 0); filters_layout.addWidget(self.search_bar, 1, 1, 1, 3)
        main_layout.addLayout(filters_layout)
        templates_list_label = self._create_icon_label_widget("document-multiple", self.tr("Modèles disponibles:")); main_layout.addWidget(templates_list_label)
        self.templates_list = QListWidget(); self.templates_list.setSelectionMode(QListWidget.MultiSelection); main_layout.addWidget(self.templates_list)
        self.language_filter_combo.currentTextChanged.connect(self.load_templates)
        self.extension_filter_combo.currentTextChanged.connect(self.load_templates)
        self.search_bar.textChanged.connect(self.load_templates)
        self.load_templates(); main_layout.addStretch()
        button_frame = QFrame(self); button_frame.setObjectName("buttonFrame") # Style in QSS
        button_frame_layout = QHBoxLayout(button_frame); button_frame_layout.setContentsMargins(0,0,0,0)
        create_btn = QPushButton(self.tr("Créer Documents")); create_btn.setIcon(QIcon(":/icons/document-new.svg")); create_btn.setObjectName("primaryButton")
        create_btn.clicked.connect(self.create_documents); button_frame_layout.addWidget(create_btn)
        cancel_btn = QPushButton(self.tr("Annuler")); cancel_btn.setIcon(QIcon(":/icons/dialog-cancel.svg"))
        cancel_btn.clicked.connect(self.reject); button_frame_layout.addWidget(cancel_btn)
        main_layout.addWidget(button_frame)

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
            all_file_templates = db_manager.get_all_file_based_templates();
            if all_file_templates is None: all_file_templates = []
            filtered_templates = []
            for template_dict in all_file_templates:
                name = template_dict.get('template_name', 'N/A'); lang_code = template_dict.get('language_code', 'N/A'); base_file_name = template_dict.get('base_file_name', 'N/A')
                if selected_lang != self.tr("All") and lang_code != selected_lang: continue
                file_actual_ext = os.path.splitext(base_file_name)[1].lower()
                if selected_ext_display != self.tr("All"):
                    if not selected_ext or file_actual_ext != selected_ext: continue
                if search_text and search_text not in name.lower(): continue
                filtered_templates.append(template_dict)
            for template_dict in filtered_templates:
                name = template_dict.get('template_name', 'N/A'); lang = template_dict.get('language_code', 'N/A'); base_file_name = template_dict.get('base_file_name', 'N/A')
                item_text = f"{name} ({lang}) - {base_file_name}"; item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, (name, lang, base_file_name)); self.templates_list.addItem(item)
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des modèles:\n{0}").format(str(e)))

    def create_documents(self):
        selected_items = self.templates_list.selectedItems()
        if not selected_items: QMessageBox.warning(self, self.tr("Aucun document sélectionné"), self.tr("Veuillez sélectionner au moins un document à créer.")); return
        created_files_count = 0
        for item in selected_items:
            db_template_name, db_template_lang, actual_template_filename = item.data(Qt.UserRole)
            target_dir_for_document = os.path.join(self.client_info["base_folder_path"], db_template_lang)
            os.makedirs(target_dir_for_document, exist_ok=True)
            if not actual_template_filename:
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Nom de fichier manquant pour le modèle '{0}'. Impossible de créer.").format(db_template_name)); continue
            template_file_found_abs = os.path.join(self.config["templates_dir"], db_template_lang, actual_template_filename)
            if os.path.exists(template_file_found_abs):
                target_path = os.path.join(target_dir_for_document, actual_template_filename)
                try:
                    shutil.copy(template_file_found_abs, target_path)
                    if target_path.lower().endswith(".docx"):
                        populate_docx_template(target_path, self.client_info) # Uses global populate_docx_template
                    elif target_path.lower().endswith(".html"):
                        with open(target_path, 'r', encoding='utf-8') as f: template_content = f.read()
                        default_company_obj = db_manager.get_default_company(); default_company_id = default_company_obj['company_id'] if default_company_obj else None
                        if default_company_id is None: QMessageBox.information(self, self.tr("Avertissement"), self.tr("Aucune société par défaut n'est définie. Les détails du vendeur peuvent être manquants dans les documents HTML."))
                        populated_content = HtmlEditor.populate_html_content(template_content, self.client_info, default_company_id) # Uses imported HtmlEditor
                        with open(target_path, 'w', encoding='utf-8') as f: f.write(populated_content)
                    created_files_count += 1
                except Exception as e_create: QMessageBox.warning(self, self.tr("Erreur Création Document"), self.tr("Impossible de créer ou populer le document '{0}':\n{1}").format(actual_template_filename, e_create))
            else: QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Fichier modèle '{0}' introuvable pour '{1}'.").format(actual_template_filename, db_template_name))
        if created_files_count > 0: QMessageBox.information(self, self.tr("Documents créés"), self.tr("{0} documents ont été créés avec succès.").format(created_files_count)); self.accept()
        elif not selected_items: pass
        else: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Aucun document n'a pu être créé. Vérifiez les erreurs précédentes."))

class CompilePdfDialog(QDialog):
    def __init__(self, client_info, config, app_root_dir, parent=None): # Added config and app_root_dir
        super().__init__(parent)
        self.client_info = client_info
        self.config = config # Store config
        self.app_root_dir = app_root_dir # Store app_root_dir
        self.setWindowTitle(self.tr("Compiler des PDF"))
        self.setMinimumSize(700, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.tr("Sélectionnez les PDF à compiler:")))
        self.pdf_list = QTableWidget(); self.pdf_list.setColumnCount(4)
        self.pdf_list.setHorizontalHeaderLabels([self.tr("Sélection"), self.tr("Nom du fichier"), self.tr("Chemin"), self.tr("Pages (ex: 1-3,5)")])
        self.pdf_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); self.pdf_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.pdf_list)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton(self.tr("Ajouter PDF")); add_btn.setIcon(QIcon(":/icons/list-add.svg")); add_btn.clicked.connect(self.add_pdf); btn_layout.addWidget(add_btn)
        remove_btn = QPushButton(self.tr("Supprimer")); remove_btn.setIcon(QIcon(":/icons/delete.svg")); remove_btn.clicked.connect(self.remove_selected); btn_layout.addWidget(remove_btn)
        move_up_btn = QPushButton(self.tr("Monter")); move_up_btn.setIcon(QIcon.fromTheme("go-up")); move_up_btn.clicked.connect(self.move_up); btn_layout.addWidget(move_up_btn) # go-up not in list
        move_down_btn = QPushButton(self.tr("Descendre")); move_down_btn.setIcon(QIcon.fromTheme("go-down")); move_down_btn.clicked.connect(self.move_down); btn_layout.addWidget(move_down_btn) # go-down not in list
        layout.addLayout(btn_layout)
        options_layout = QHBoxLayout(); options_layout.addWidget(QLabel(self.tr("Nom du fichier compilé:")))
        self.output_name = QLineEdit(f"{self.tr('compilation')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"); options_layout.addWidget(self.output_name); layout.addLayout(options_layout)
        action_layout = QHBoxLayout()
        compile_btn = QPushButton(self.tr("Compiler PDF")); compile_btn.setIcon(QIcon(":/icons/document-export.svg")); compile_btn.setObjectName("primaryButton")
        compile_btn.clicked.connect(self.compile_pdf); action_layout.addWidget(compile_btn)
        cancel_btn = QPushButton(self.tr("Annuler")); cancel_btn.setIcon(QIcon(":/icons/dialog-cancel.svg")); cancel_btn.clicked.connect(self.reject); action_layout.addWidget(cancel_btn)
        layout.addLayout(action_layout)
        self.load_existing_pdfs()

    def load_existing_pdfs(self):
        client_dir = self.client_info["base_folder_path"]; pdf_files = []
        for root, dirs, files in os.walk(client_dir):
            for file in files:
                if file.lower().endswith('.pdf'): pdf_files.append(os.path.join(root, file))
        self.pdf_list.setRowCount(len(pdf_files))
        for i, file_path in enumerate(pdf_files):
            chk = QCheckBox(); chk.setChecked(True); self.pdf_list.setCellWidget(i, 0, chk)
            self.pdf_list.setItem(i, 1, QTableWidgetItem(os.path.basename(file_path)))
            self.pdf_list.setItem(i, 2, QTableWidgetItem(file_path))
            pages_edit = QLineEdit("all"); pages_edit.setPlaceholderText(self.tr("all ou 1-3,5")); self.pdf_list.setCellWidget(i, 3, pages_edit)

    def add_pdf(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Sélectionner des PDF"), "", self.tr("Fichiers PDF (*.pdf)"));
        if not file_paths: return
        current_row_count = self.pdf_list.rowCount(); self.pdf_list.setRowCount(current_row_count + len(file_paths))
        for i, file_path in enumerate(file_paths):
            row = current_row_count + i; chk = QCheckBox(); chk.setChecked(True); self.pdf_list.setCellWidget(row, 0, chk)
            self.pdf_list.setItem(row, 1, QTableWidgetItem(os.path.basename(file_path))); self.pdf_list.setItem(row, 2, QTableWidgetItem(file_path))
            pages_edit = QLineEdit("all"); pages_edit.setPlaceholderText(self.tr("all ou 1-3,5")); self.pdf_list.setCellWidget(row, 3, pages_edit)

    def remove_selected(self):
        selected_rows = set(index.row() for index in self.pdf_list.selectedIndexes())
        for row in sorted(selected_rows, reverse=True): self.pdf_list.removeRow(row)

    def move_up(self):
        current_row = self.pdf_list.currentRow()
        if current_row > 0: self.swap_rows(current_row, current_row - 1); self.pdf_list.setCurrentCell(current_row - 1, 0)

    def move_down(self):
        current_row = self.pdf_list.currentRow()
        if current_row < self.pdf_list.rowCount() - 1: self.swap_rows(current_row, current_row + 1); self.pdf_list.setCurrentCell(current_row + 1, 0)

    def swap_rows(self, row1, row2):
        for col in range(self.pdf_list.columnCount()):
            item1 = self.pdf_list.takeItem(row1, col); item2 = self.pdf_list.takeItem(row2, col)
            self.pdf_list.setItem(row1, col, item2); self.pdf_list.setItem(row2, col, item1)
        widget1 = self.pdf_list.cellWidget(row1,0); widget3 = self.pdf_list.cellWidget(row1,3); widget2 = self.pdf_list.cellWidget(row2,0); widget4 = self.pdf_list.cellWidget(row2,3)
        self.pdf_list.setCellWidget(row1,0,widget2); self.pdf_list.setCellWidget(row1,3,widget4); self.pdf_list.setCellWidget(row2,0,widget1); self.pdf_list.setCellWidget(row2,3,widget3)

    def compile_pdf(self):
        merger = PdfMerger(); output_name = self.output_name.text().strip()
        if not output_name: QMessageBox.warning(self, self.tr("Nom manquant"), self.tr("Veuillez spécifier un nom de fichier pour la compilation.")); return
        if not output_name.lower().endswith('.pdf'): output_name += '.pdf'
        output_path = os.path.join(self.client_info["base_folder_path"], output_name)
        cover_path = self.create_cover_page()
        if cover_path: merger.append(cover_path)
        for row in range(self.pdf_list.rowCount()):
            chk = self.pdf_list.cellWidget(row, 0)
            if chk and chk.isChecked():
                file_path = self.pdf_list.item(row, 2).text(); pages_spec = self.pdf_list.cellWidget(row, 3).text().strip()
                try:
                    if pages_spec.lower() == "all" or not pages_spec: merger.append(file_path)
                    else:
                        pages = [];
                        for part in pages_spec.split(','):
                            if '-' in part: start, end = part.split('-'); pages.extend(range(int(start), int(end)+1))
                            else: pages.append(int(part))
                        merger.append(file_path, pages=[p-1 for p in pages])
                except Exception as e: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout de {0}:\n{1}").format(os.path.basename(file_path), str(e)))
        try:
            with open(output_path, 'wb') as f: merger.write(f)
            if cover_path and os.path.exists(cover_path): os.remove(cover_path)
            QMessageBox.information(self, self.tr("Compilation réussie"), self.tr("Le PDF compilé a été sauvegardé dans:\n{0}").format(output_path))
            self.offer_download_or_email(output_path); self.accept()
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la compilation du PDF:\n{0}").format(str(e)))

    def create_cover_page(self):
        config_dict = {'title': self.tr("Compilation de Documents - Projet: {0}").format(self.client_info.get('project_identifier', self.tr('N/A'))),
                       'subtitle': self.tr("Client: {0}").format(self.client_info.get('client_name', self.tr('N/A'))),
                       'author': self.client_info.get('company_name', PAGEDEGRDE_APP_CONFIG.get('default_institution', self.tr('Votre Entreprise'))),
                       'institution': "", 'department': "", 'doc_type': self.tr("Compilation de Documents"),
                       'date': datetime.now().strftime('%d/%m/%Y %H:%M'), 'version': "1.0",
                       'font_name': PAGEDEGRDE_APP_CONFIG.get('default_font', 'Helvetica'), 'font_size_title': 20, 'font_size_subtitle': 16, 'font_size_author': 10,
                       'text_color': PAGEDEGRDE_APP_CONFIG.get('default_text_color', '#000000'), 'template_style': 'Moderne', 'show_horizontal_line': True, 'line_y_position_mm': 140,
                       'logo_data': None, 'logo_width_mm': 40, 'logo_height_mm': 40, 'logo_x_mm': 25, 'logo_y_mm': 297 - 25 - 40,
                       'margin_top': 25, 'margin_bottom': 25, 'margin_left': 20, 'margin_right': 20,
                       'footer_text': self.tr("Document compilé le {0}").format(datetime.now().strftime('%d/%m/%Y'))}
        logo_path = os.path.join(self.app_root_dir, "logo.png") # Use self.app_root_dir
        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f_logo: config_dict['logo_data'] = f_logo.read()
            except Exception as e_logo: print(self.tr("Erreur chargement logo.png: {0}").format(e_logo))
        try:
            pdf_bytes = generate_cover_page_logic(config_dict) # Uses imported generate_cover_page_logic
            base_temp_dir = self.client_info.get("base_folder_path", QDir.tempPath()); temp_cover_filename = f"cover_page_generated_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.pdf"
            temp_cover_path = os.path.join(base_temp_dir, temp_cover_filename)
            with open(temp_cover_path, "wb") as f: f.write(pdf_bytes)
            return temp_cover_path
        except Exception as e: print(self.tr("Erreur lors de la génération de la page de garde via pagedegrde: {0}").format(e)); QMessageBox.warning(self, self.tr("Erreur Page de Garde"), self.tr("Impossible de générer la page de garde personnalisée: {0}").format(e)); return None

    def offer_download_or_email(self, pdf_path):
        msg_box = QMessageBox(self); msg_box.setWindowTitle(self.tr("Compilation réussie")); msg_box.setText(self.tr("Le PDF compilé a été sauvegardé dans:\n{0}").format(pdf_path))
        download_btn = msg_box.addButton(self.tr("Télécharger"), QMessageBox.ActionRole); email_btn = msg_box.addButton(self.tr("Envoyer par email"), QMessageBox.ActionRole)
        close_btn = msg_box.addButton(self.tr("Fermer"), QMessageBox.RejectRole)
        msg_box.exec_()
        if msg_box.clickedButton() == download_btn: QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        elif msg_box.clickedButton() == email_btn: self.send_email(pdf_path)

    def send_email(self, pdf_path):
        primary_email = None; client_uuid = self.client_info.get("client_id")
        if client_uuid:
            contacts_for_client = db_manager.get_contacts_for_client(client_uuid)
            if contacts_for_client:
                for contact in contacts_for_client:
                    if contact.get('is_primary_for_client'): primary_email = contact.get('email'); break
        email, ok = QInputDialog.getText(self, self.tr("Envoyer par email"), self.tr("Adresse email du destinataire:"), text=primary_email or "")
        if not ok or not email.strip(): return
        # Use self.config for SMTP settings
        if not self.config.get("smtp_server") or not self.config.get("smtp_user"): QMessageBox.warning(self, self.tr("Configuration manquante"), self.tr("Veuillez configurer les paramètres SMTP dans les paramètres de l'application.")); return
        msg = MIMEMultipart(); msg['From'] = self.config["smtp_user"]; msg['To'] = email; msg['Subject'] = self.tr("Documents compilés - {0}").format(self.client_info['client_name'])
        body = self.tr("Bonjour,\n\nVeuillez trouver ci-joint les documents compilés pour le projet {0}.\n\nCordialement,\nVotre équipe").format(self.client_info['project_identifier']); msg.attach(MIMEText(body, 'plain'))
        with open(pdf_path, 'rb') as f: part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'; msg.attach(part)
        try:
            server = smtplib.SMTP(self.config["smtp_server"], self.config.get("smtp_port", 587))
            if self.config.get("smtp_port", 587) == 587: server.starttls()
            server.login(self.config["smtp_user"], self.config["smtp_password"]); server.send_message(msg); server.quit()
            QMessageBox.information(self, self.tr("Email envoyé"), self.tr("Le document a été envoyé avec succès."))
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur d'envoi"), self.tr("Erreur lors de l'envoi de l'email:\n{0}").format(str(e)))

class EditClientDialog(QDialog):
    def __init__(self, client_info, config, parent=None): # Config is passed but not explicitly used in original for DB path
        super().__init__(parent)
        self.client_info = client_info
        self.config = config # Store config
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(self.tr("Modifier Client")); self.setMinimumSize(500, 430)
        layout = QFormLayout(self); layout.setSpacing(10)
        self.client_name_input = QLineEdit(self.client_info.get('client_name', '')); layout.addRow(self.tr("Nom Client:"), self.client_name_input)
        self.company_name_input = QLineEdit(self.client_info.get('company_name', '')); layout.addRow(self.tr("Nom Entreprise:"), self.company_name_input)
        self.client_need_input = QLineEdit(self.client_info.get('primary_need_description', self.client_info.get('need',''))); layout.addRow(self.tr("Besoin Client:"), self.client_need_input)
        self.project_id_input_field = QLineEdit(self.client_info.get('project_identifier', '')); layout.addRow(self.tr("ID Projet:"), self.project_id_input_field)
        self.final_price_input = QDoubleSpinBox(); self.final_price_input.setPrefix("€ "); self.final_price_input.setRange(0,10000000); self.final_price_input.setValue(float(self.client_info.get('price',0.0))); self.final_price_input.setReadOnly(True)
        price_info_label = QLabel(self.tr("Le prix final est calculé à partir des produits et n'est pas modifiable ici.")); price_info_label.setObjectName("priceInfoLabel")
        price_layout = QHBoxLayout(); price_layout.addWidget(self.final_price_input); price_layout.addWidget(price_info_label); layout.addRow(self.tr("Prix Final:"), price_layout)
        self.status_select_combo = QComboBox(); self.populate_statuses()
        current_status_id = self.client_info.get('status_id')
        if current_status_id is not None:
            index = self.status_select_combo.findData(current_status_id)
            if index >= 0: self.status_select_combo.setCurrentIndex(index)
        layout.addRow(self.tr("Statut Client:"), self.status_select_combo)
        self.category_input = QLineEdit(self.client_info.get('category', '')); layout.addRow(self.tr("Catégorie:"), self.category_input)
        self.notes_edit = QTextEdit(self.client_info.get('notes', '')); self.notes_edit.setPlaceholderText(self.tr("Ajoutez des notes sur ce client...")); self.notes_edit.setFixedHeight(80); layout.addRow(self.tr("Notes:"), self.notes_edit)
        self.country_select_combo = QComboBox(); self.country_select_combo.setEditable(True); self.country_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.country_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion); self.country_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.populate_countries()
        current_country_id = self.client_info.get('country_id')
        if current_country_id is not None:
            index = self.country_select_combo.findData(current_country_id)
            if index >= 0:
                self.country_select_combo.setCurrentIndex(index)
            else:
                current_country_name = self.client_info.get('country')
                if current_country_name:
                    index_name = self.country_select_combo.findText(current_country_name)
                    if index_name >= 0:
                        self.country_select_combo.setCurrentIndex(index_name)
        self.country_select_combo.currentTextChanged.connect(self.load_cities_for_country_edit); layout.addRow(self.tr("Pays Client:"), self.country_select_combo)
        self.city_select_combo = QComboBox(); self.city_select_combo.setEditable(True); self.city_select_combo.setInsertPolicy(QComboBox.NoInsert)
        self.city_select_combo.completer().setCompletionMode(QCompleter.PopupCompletion); self.city_select_combo.completer().setFilterMode(Qt.MatchContains)
        self.load_cities_for_country_edit(self.country_select_combo.currentText())
        current_city_id = self.client_info.get('city_id')
        if current_city_id is not None:
            index = self.city_select_combo.findData(current_city_id)
            if index >= 0:
                self.city_select_combo.setCurrentIndex(index)
            else:
                current_city_name = self.client_info.get('city')
                if current_city_name:
                    index_name = self.city_select_combo.findText(current_city_name)
                    if index_name >= 0:
                        self.city_select_combo.setCurrentIndex(index_name)
        layout.addRow(self.tr("Ville Client:"), self.city_select_combo)
        self.language_select_combo = QComboBox()
        self.lang_display_to_codes_map = {self.tr("Français uniquement (fr)"): ["fr"], self.tr("Arabe uniquement (ar)"): ["ar"], self.tr("Turc uniquement (tr)"): ["tr"], self.tr("Toutes les langues (fr, ar, tr)"): ["fr", "ar", "tr"]}
        self.language_select_combo.addItems(list(self.lang_display_to_codes_map.keys()))
        current_lang_codes = self.client_info.get('selected_languages', ['fr'])
        if not isinstance(current_lang_codes, list): current_lang_codes = [code.strip() for code in str(current_lang_codes).split(',') if code.strip()]
        selected_display_string = None
        for display_string, codes_list in self.lang_display_to_codes_map.items():
            if sorted(codes_list) == sorted(current_lang_codes): selected_display_string = display_string; break
        if selected_display_string: self.language_select_combo.setCurrentText(selected_display_string)
        else: self.language_select_combo.setCurrentText(self.tr("Français uniquement (fr)"))
        layout.addRow(self.tr("Langues:"), self.language_select_combo)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText(self.tr("OK")); button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        button_box.accepted.connect(self.accept); button_box.rejected.connect(self.reject); layout.addRow(button_box)

    def populate_statuses(self):
        self.status_select_combo.clear()
        try:
            statuses = db_manager.get_all_status_settings(status_type='Client')
            if statuses is None: statuses = []
            for status_dict in statuses: self.status_select_combo.addItem(status_dict['status_name'], status_dict.get('status_id'))
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des statuts client:\n{0}").format(str(e)))

    def populate_countries(self):
        self.country_select_combo.clear()
        try:
            countries = db_manager.get_all_countries()
            if countries is None: countries = []
            for country_dict in countries: self.country_select_combo.addItem(country_dict['country_name'], country_dict.get('country_id'))
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des pays:\n{0}").format(str(e)))

    def load_cities_for_country_edit(self, country_name_str):
        self.city_select_combo.clear();
        if not country_name_str: return
        selected_country_id = self.country_select_combo.currentData()
        if selected_country_id is None:
            country_obj_by_name = db_manager.get_country_by_name(country_name_str)
            if country_obj_by_name: selected_country_id = country_obj_by_name['country_id']
            else: return
        try:
            cities = db_manager.get_all_cities(country_id=selected_country_id)
            if cities is None: cities = []
            for city_dict in cities: self.city_select_combo.addItem(city_dict['city_name'], city_dict.get('city_id'))
        except Exception as e: QMessageBox.warning(self, self.tr("Erreur DB"), self.tr("Erreur de chargement des villes:\n{0}").format(str(e)))

    def get_data(self) -> dict:
        data = {}; data['client_name'] = self.client_name_input.text().strip(); data['company_name'] = self.company_name_input.text().strip()
        data['primary_need_description'] = self.client_need_input.text().strip(); data['project_identifier'] = self.project_id_input_field.text().strip()
        data['price'] = self.final_price_input.value(); data['status_id'] = self.status_select_combo.currentData()
        data['category'] = self.category_input.text().strip(); data['notes'] = self.notes_edit.toPlainText().strip()
        country_id = self.country_select_combo.currentData()
        if country_id is None:
            country_name = self.country_select_combo.currentText().strip()
            if country_name:
                country_obj = db_manager.get_country_by_name(country_name)
                if country_obj: country_id = country_obj['country_id']
        data['country_id'] = country_id
        city_id = self.city_select_combo.currentData()
        if city_id is None:
            city_name = self.city_select_combo.currentText().strip()
            if city_name and data.get('country_id') is not None:
                city_obj = db_manager.get_city_by_name_and_country_id(city_name, data['country_id'])
                if city_obj: city_id = city_obj['city_id']
        data['city_id'] = city_id
        selected_lang_display_text = self.language_select_combo.currentText()
        lang_codes_list = self.lang_display_to_codes_map.get(selected_lang_display_text, ["fr"])
        data['selected_languages'] = ",".join(lang_codes_list)
        return data

# DIALOG CLASSES MOVED FROM MAIN.PY END HERE

class SendEmailDialog(QDialog):
    def __init__(self, client_email, config, parent=None):
        super().__init__(parent)
        self.client_email = client_email
        self.config = config
        self.attachments = []  # List to store paths of attachments

        self.setWindowTitle(self.tr("Envoyer un Email"))
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.to_edit = QLineEdit(self.client_email)
        form_layout.addRow(self.tr("À:"), self.to_edit)

        self.subject_edit = QLineEdit()
        form_layout.addRow(self.tr("Sujet:"), self.subject_edit)

        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText(self.tr("Saisissez votre message ici..."))
        form_layout.addRow(self.tr("Corps:"), self.body_edit)

        layout.addLayout(form_layout)

        attachment_layout = QHBoxLayout()
        self.add_attachment_btn = QPushButton(self.tr("Ajouter Pièce Jointe"))
        self.add_attachment_btn.setIcon(QIcon.fromTheme("document-open", QIcon(":/icons/plus.svg"))) # Using an existing icon
        self.add_attachment_btn.clicked.connect(self.add_attachment)
        attachment_layout.addWidget(self.add_attachment_btn)

        self.remove_attachment_btn = QPushButton(self.tr("Supprimer Pièce Jointe"))
        self.remove_attachment_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg"))) # Using an existing icon
        self.remove_attachment_btn.clicked.connect(self.remove_attachment)
        attachment_layout.addWidget(self.remove_attachment_btn)
        layout.addLayout(attachment_layout)

        self.attachments_list_widget = QListWidget()
        self.attachments_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(QLabel(self.tr("Pièces jointes:")))
        layout.addWidget(self.attachments_list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Send | QDialogButtonBox.Cancel)
        send_button = button_box.button(QDialogButtonBox.Send)
        send_button.setText(self.tr("Envoyer"))
        send_button.setIcon(QIcon.fromTheme("mail-send", QIcon(":/icons/bell.svg"))) # Using an existing icon
        send_button.setObjectName("primaryButton")
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        cancel_button.setText(self.tr("Annuler"))

        button_box.accepted.connect(self.send_email_action) # Connect to send_email_action
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def add_attachment(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.tr("Sélectionner des fichiers à joindre"), "", self.tr("Tous les fichiers (*.*)"))
        if files:
            for file_path in files:
                if file_path not in self.attachments:
                    self.attachments.append(file_path)
                    self.attachments_list_widget.addItem(os.path.basename(file_path))

    def remove_attachment(self):
        selected_items = self.attachments_list_widget.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            row = self.attachments_list_widget.row(item)
            self.attachments_list_widget.takeItem(row)
            # Remove from self.attachments by matching basename, less robust if multiple files with same name from different paths
            # A more robust way would be to store full paths in item data or find by index if list order is guaranteed.
            # For simplicity, let's find by index.
            if 0 <= row < len(self.attachments):
                del self.attachments[row]
            else: # Fallback if index is out of sync (should not happen with SingleSelection)
                try:
                    # Attempt to remove by matching basename from the list
                    file_to_remove = item.text()
                    self.attachments = [att for att in self.attachments if os.path.basename(att) != file_to_remove]
                except ValueError:
                    pass # Item not found, already removed or error

    def send_email_action(self):
        to_email = self.to_edit.text().strip()
        subject = self.subject_edit.text().strip()
        body = self.body_edit.toPlainText().strip()

        if not to_email:
            QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("L'adresse email du destinataire est requise."))
            return
        if not subject:
            QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("Le sujet de l'email est requis."))
            return

        # Use self.config for SMTP settings
        smtp_server = self.config.get("smtp_server")
        smtp_port = self.config.get("smtp_port", 587)
        smtp_user = self.config.get("smtp_user")
        smtp_password = self.config.get("smtp_password")

        if not smtp_server or not smtp_user: # Password can be empty for some configs
            QMessageBox.warning(self, self.tr("Configuration SMTP Manquante"),
                                self.tr("Veuillez configurer les détails du serveur SMTP dans les paramètres de l'application."))
            return

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        for attachment_path in self.attachments:
            try:
                with open(attachment_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur Pièce Jointe"), self.tr("Impossible de joindre le fichier {0}:\
{1}").format(os.path.basename(attachment_path), str(e)))
                return # Stop if an attachment fails

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if smtp_port == 587: # Standard port for TLS
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            QMessageBox.information(self, self.tr("Email Envoyé"), self.tr("L'email a été envoyé avec succès."))
            self.accept() # Close dialog on success
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur d'Envoi Email"), self.tr("Une erreur est survenue lors de l'envoi de l'email:\
{0}").format(str(e)))

# [end of dialogs.py]
