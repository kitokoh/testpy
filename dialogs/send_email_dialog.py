# -*- coding: utf-8 -*-
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QMessageBox, QComboBox,
    QListWidget, QAbstractItemView, QFileDialog, QLabel
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt # Included for safety and common Qt enum usage

import db as db_manager
from db.cruds.clients_crud import clients_crud_instance
from db.cruds.templates_crud import templates_crud_instance

# Anticipated imports for other dialogs
from .select_contacts_dialog import SelectContactsDialog
from .select_client_attachment_dialog import SelectClientAttachmentDialog
from .select_utility_attachment_dialog import SelectUtilityAttachmentDialog
import icons_rc # Import for Qt resource file


class SendEmailDialog(QDialog):
    def __init__(self, client_email, config, client_id=None, parent=None):
        super().__init__(parent)
        self.client_email = client_email
        self.config = config
        self.client_id = client_id
        self.client_info = None
        if self.client_id:
            try:
                self.client_info = clients_crud_instance.get_client_by_id(self.client_id)
            except Exception as e:
                print(f"Error fetching client_info in SendEmailDialog: {e}") # Or logging
        self.attachments = []
        self.active_template_type = None

        self.setWindowTitle(self.tr("Envoyer un Email"))
        self.setMinimumSize(600, 550)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        to_layout = QHBoxLayout()
        self.to_edit = QLineEdit(self.client_email)
        to_layout.addWidget(self.to_edit)

        if self.client_id:
            self.select_contacts_btn = QPushButton(self.tr("Sélectionner Contacts"))
            self.select_contacts_btn.setIcon(QIcon.fromTheme("address-book-new", QIcon(":/icons/user-plus.svg")))
            self.select_contacts_btn.clicked.connect(self.open_select_contacts_dialog)
            to_layout.addWidget(self.select_contacts_btn)
        form_layout.addRow(self.tr("À:"), to_layout)

        template_selection_layout = QHBoxLayout()
        self.language_combo = QComboBox()
        self.language_combo.setPlaceholderText(self.tr("Langue..."))
        template_selection_layout.addWidget(self.language_combo)
        self.template_combo = QComboBox()
        self.template_combo.setPlaceholderText(self.tr("Sélectionner un modèle..."))
        template_selection_layout.addWidget(self.template_combo)
        form_layout.addRow(self.tr("Modèle d'Email:"), template_selection_layout)

        self.subject_edit = QLineEdit()
        form_layout.addRow(self.tr("Sujet:"), self.subject_edit)
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText(self.tr("Saisissez votre message ici ou sélectionnez un modèle..."))
        form_layout.addRow(self.tr("Corps:"), self.body_edit)
        layout.addLayout(form_layout)

        self.email_template_types = ['EMAIL_BODY_HTML', 'EMAIL_BODY_TXT']
        self.default_company_id = None
        try:
            default_company_obj = db_manager.get_default_company()
            if default_company_obj:
                self.default_company_id = default_company_obj.get('company_id')
        except Exception as e:
            print(f"Error fetching default company ID: {e}") # Or logging

        self.language_combo.currentTextChanged.connect(self.load_email_templates)
        self.template_combo.currentIndexChanged.connect(self.on_template_selected)
        self.load_available_languages()
        if self.language_combo.count() > 0:
            self.load_email_templates(self.language_combo.currentText())

        attachment_buttons_layout = QHBoxLayout()
        self.add_attachment_btn = QPushButton(self.tr("Ajouter Pièce Jointe (Fichier)"))
        self.add_attachment_btn.setIcon(QIcon.fromTheme("document-open", QIcon(":/icons/plus.svg")))
        self.add_attachment_btn.clicked.connect(self.add_attachment_from_file_system)
        attachment_buttons_layout.addWidget(self.add_attachment_btn)

        if self.client_info:
            self.add_client_document_btn = QPushButton(self.tr("Ajouter Document Client"))
            self.add_client_document_btn.setIcon(QIcon.fromTheme("folder-open", QIcon(":/icons/folder.svg")))
            self.add_client_document_btn.clicked.connect(self.add_attachment_from_client_docs)
            attachment_buttons_layout.addWidget(self.add_client_document_btn)

        self.add_utility_document_btn = QPushButton(self.tr("Ajouter Document Utilitaire"))
        self.add_utility_document_btn.setIcon(QIcon.fromTheme("document-properties", QIcon(":/icons/document.svg")))
        self.add_utility_document_btn.clicked.connect(self.add_attachment_from_utility_docs)
        attachment_buttons_layout.addWidget(self.add_utility_document_btn)

        self.remove_attachment_btn = QPushButton(self.tr("Supprimer Pièce Jointe"))
        self.remove_attachment_btn.setIcon(QIcon.fromTheme("edit-delete", QIcon(":/icons/trash.svg")))
        self.remove_attachment_btn.clicked.connect(self.remove_attachment)
        attachment_buttons_layout.addWidget(self.remove_attachment_btn)
        layout.addLayout(attachment_buttons_layout)

        self.attachments_list_widget = QListWidget()
        self.attachments_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(QLabel(self.tr("Pièces jointes:")))
        layout.addWidget(self.attachments_list_widget)

        button_box = QDialogButtonBox()
        send_button = button_box.addButton(self.tr("Envoyer"), QDialogButtonBox.AcceptRole)
        send_button.setIcon(QIcon.fromTheme("mail-send", QIcon(":/icons/bell.svg"))) # Using bell as mail-send might not be in all themes
        send_button.setObjectName("primaryButton")
        button_box.addButton(QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.send_email_action)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_available_languages(self):
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        available_langs = set()
        try:
            for template_type in self.email_template_types:
                langs = db_manager.get_distinct_languages_for_template_type(template_type)
                if langs:
                    available_langs.update(lang_tuple[0] for lang_tuple in langs if lang_tuple and lang_tuple[0])
        except Exception as e:
            print(f"Error loading available languages for email templates: {e}")
            available_langs.update(["fr", "en"])
        sorted_langs = sorted(list(available_langs))
        self.language_combo.addItems(sorted_langs)
        preferred_lang_set = False
        if self.client_info and self.client_info.get('selected_languages'):
            client_langs_str = self.client_info['selected_languages']
            client_langs_list = [lang.strip() for lang in client_langs_str.split(',') if lang.strip()]
            if client_langs_list:
                first_client_lang = client_langs_list[0]
                if first_client_lang in sorted_langs:
                    self.language_combo.setCurrentText(first_client_lang)
                    preferred_lang_set = True
        if not preferred_lang_set and sorted_langs:
            self.language_combo.setCurrentIndex(0)
        self.language_combo.blockSignals(False)
        if self.language_combo.currentText():
             self.load_email_templates(self.language_combo.currentText())

    def load_email_templates(self, language_code):
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem(self.tr("--- Aucun Modèle ---"), None)
        if not language_code:
            self.template_combo.blockSignals(False)
            self.on_template_selected(0)
            return
        try:
            all_templates_for_lang = []
            for template_type in self.email_template_types:
                templates = templates_crud_instance.get_templates_by_type_and_language(
                    template_type=template_type, language_code=language_code
                )
                if templates: all_templates_for_lang.extend(templates)
            all_templates_for_lang.sort(key=lambda x: x.get('template_name', ''))
            for template in all_templates_for_lang:
                self.template_combo.addItem(template['template_name'], template['template_id'])
        except Exception as e:
            print(f"Error loading email templates for lang {language_code}: {e}")
            QMessageBox.warning(self, self.tr("Erreur Modèles Email"), self.tr("Impossible de charger les modèles d'email pour la langue {0}:\n{1}").format(language_code, str(e)))
        self.template_combo.blockSignals(False)
        self.on_template_selected(self.template_combo.currentIndex())

    def on_template_selected(self, index):
        template_id = self.template_combo.itemData(index)
        self.active_template_type = None
        if template_id is None:
            self.body_edit.setPlainText("")
            self.body_edit.setReadOnly(False)
            self.subject_edit.setText("")
            return
        try:
            template_details = db_manager.get_template_details_by_id(template_id)
            if not template_details:
                QMessageBox.warning(self, self.tr("Erreur Modèle"), self.tr("Détails du modèle non trouvés."))
                self.body_edit.setPlainText(""); self.body_edit.setReadOnly(False); return

            template_lang = template_details.get('language_code')
            base_file_name = template_details.get('base_file_name')
            template_type = template_details.get('template_type')
            self.active_template_type = template_type
            email_subject_template = template_details.get('email_subject_template')

            if not self.config or "templates_dir" not in self.config:
                QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("Le dossier des modèles n'est pas configuré."))
                return
            template_file_path = os.path.join(self.config["templates_dir"], template_lang, base_file_name)
            if not os.path.exists(template_file_path):
                QMessageBox.warning(self, self.tr("Erreur Fichier Modèle"), self.tr("Fichier modèle introuvable:\n{0}").format(template_file_path))
                self.body_edit.setPlainText(""); self.body_edit.setReadOnly(False); return
            with open(template_file_path, 'r', encoding='utf-8') as f: template_content = f.read()

            context_data = {}
            if self.client_info and self.client_info.get('client_id'):
                context_data = db_manager.get_document_context_data(
                    client_id=self.client_info['client_id'], company_id=self.default_company_id,
                    target_language_code=template_lang, project_id=self.client_info.get('project_id')
                )
            else:
                if self.default_company_id:
                     company_details = db_manager.get_company_by_id(self.default_company_id)
                     if company_details : context_data['seller'] = company_details

            populated_body = template_content
            for key, value in context_data.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                         placeholder = f"{{{{{key}.{sub_key}}}}}"
                         populated_body = populated_body.replace(placeholder, str(sub_value) if sub_value is not None else "")
                else:
                    placeholder = f"{{{{{key}}}}}"
                    populated_body = populated_body.replace(placeholder, str(value) if value is not None else "")

            if template_type == 'EMAIL_BODY_HTML': self.body_edit.setHtml(populated_body)
            elif template_type == 'EMAIL_BODY_TXT': self.body_edit.setPlainText(populated_body)
            else: self.body_edit.setPlainText(self.tr("Type de modèle non supporté pour l'aperçu."))
            self.body_edit.setReadOnly(True)

            if email_subject_template:
                populated_subject = email_subject_template
                for key, value in context_data.items(): # Simplified replacement, same as body
                     if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                             placeholder = f"{{{{{key}.{sub_key}}}}}"
                             populated_subject = populated_subject.replace(placeholder, str(sub_value) if sub_value is not None else "")
                     else:
                        placeholder = f"{{{{{key}}}}}"
                        populated_subject = populated_subject.replace(placeholder, str(value) if value is not None else "")
                self.subject_edit.setText(populated_subject)
            else: self.subject_edit.setText("")
        except Exception as e:
            print(f"Error applying email template (ID: {template_id}): {e}")
            QMessageBox.critical(self, self.tr("Erreur Application Modèle"), self.tr("Une erreur est survenue lors de l'application du modèle:\n{0}").format(str(e)))
            self.body_edit.setPlainText(""); self.body_edit.setReadOnly(False); self.active_template_type = None

    def open_select_contacts_dialog(self):
        if not self.client_id:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("ID Client non disponible."))
            return
        dialog = SelectContactsDialog(self.client_id, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_emails = dialog.get_selected_emails()
            if selected_emails:
                current_text = self.to_edit.text().strip()
                current_emails = [email.strip() for email in current_text.split(',') if email.strip()]
                new_emails_to_add = [email for email in selected_emails if email not in current_emails]
                if new_emails_to_add:
                    prefix = ", " if current_emails and current_text and not current_text.endswith(',') else ""
                    if not current_text: prefix = ""
                    elif current_text.endswith(','): prefix = " "
                    self.to_edit.setText(current_text + prefix + ", ".join(new_emails_to_add))

    def add_attachment_from_client_docs(self):
        if not self.client_info:
            QMessageBox.warning(self, self.tr("Erreur"), self.tr("Informations client non disponibles pour sélectionner des documents."))
            return
        dialog = SelectClientAttachmentDialog(self.client_info, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_files = dialog.get_selected_files()
            if selected_files:
                for file_path in selected_files:
                    if file_path not in self.attachments:
                        self.attachments.append(file_path)
                        self.attachments_list_widget.addItem(os.path.basename(file_path))
                    else:
                        QMessageBox.information(self, self.tr("Info"), self.tr("Le fichier '{0}' est déjà attaché.").format(os.path.basename(file_path)))

    def add_attachment_from_utility_docs(self):
        dialog = SelectUtilityAttachmentDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            selected_files = dialog.get_selected_files()
            if selected_files:
                for file_path in selected_files:
                    if file_path not in self.attachments:
                        self.attachments.append(file_path)
                        self.attachments_list_widget.addItem(os.path.basename(file_path))
                    else:
                        QMessageBox.information(self, self.tr("Info"), self.tr("Le fichier '{0}' est déjà attaché.").format(os.path.basename(file_path)))

    def add_attachment_from_file_system(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.tr("Sélectionner des fichiers à joindre"), "", self.tr("Tous les fichiers (*.*)"))
        if files:
            for file_path in files:
                if file_path not in self.attachments:
                    self.attachments.append(file_path)
                    self.attachments_list_widget.addItem(os.path.basename(file_path))

    def remove_attachment(self):
        selected_items = self.attachments_list_widget.selectedItems()
        if not selected_items: return
        for item in selected_items:
            row = self.attachments_list_widget.row(item)
            self.attachments_list_widget.takeItem(row)
            if 0 <= row < len(self.attachments): del self.attachments[row]
            else:
                try: self.attachments = [att for att in self.attachments if os.path.basename(att) != item.text()]
                except ValueError: pass

    def send_email_action(self):
        to_email = self.to_edit.text().strip()
        subject = self.subject_edit.text().strip()
        body_content = self.body_edit.toHtml() if self.active_template_type == 'EMAIL_BODY_HTML' else self.body_edit.toPlainText().strip()
        mime_subtype = 'html' if self.active_template_type == 'EMAIL_BODY_HTML' else 'plain'

        if not to_email: QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("L'adresse email du destinataire est requise.")); return
        if not subject: QMessageBox.warning(self, self.tr("Champ Requis"), self.tr("Le sujet de l'email est requis.")); return

        smtp_server = self.config.get("smtp_server")
        smtp_port = self.config.get("smtp_port", 587)
        smtp_user = self.config.get("smtp_user")
        smtp_password = self.config.get("smtp_password")

        if not smtp_server or not smtp_user:
            QMessageBox.warning(self, self.tr("Configuration SMTP Manquante"), self.tr("Veuillez configurer les détails du serveur SMTP dans les paramètres de l'application.")); return

        msg = MIMEMultipart(); msg['From'] = smtp_user; msg['To'] = to_email; msg['Subject'] = subject
        msg.attach(MIMEText(body_content, mime_subtype))

        for attachment_path in self.attachments:
            try:
                with open(attachment_path, 'rb') as f: part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'; msg.attach(part)
            except Exception as e:
                QMessageBox.warning(self, self.tr("Erreur Pièce Jointe"), self.tr("Impossible de joindre le fichier {0}:\n{1}").format(os.path.basename(attachment_path), str(e))); return
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if smtp_port == 587: server.starttls()
            server.login(smtp_user, smtp_password); server.send_message(msg); server.quit()
            QMessageBox.information(self, self.tr("Email Envoyé"), self.tr("L'email a été envoyé avec succès.")); self.accept()
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur d'Envoi Email"), self.tr("Une erreur est survenue lors de l'envoi de l'email:\n{0}").format(str(e)))
