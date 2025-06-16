# -*- coding: utf-8 -*-
import os
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QDialogButtonBox, QMessageBox, QLabel, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView,
    QCheckBox, QFileDialog, QInputDialog
)
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtCore import QUrl, QDir

from PyPDF2 import PdfMerger
from pagedegrde import generate_cover_page_logic, APP_CONFIG as PAGEDEGRDE_APP_CONFIG
import db as db_manager
# clients_crud_instance is not used by CompilePdfDialog
import icons_rc # Import for Qt resource file

class CompilePdfDialog(QDialog):
    def __init__(self, client_info, config, app_root_dir, parent=None):
        super().__init__(parent)
        self.client_info = client_info
        self.config = config
        self.app_root_dir = app_root_dir
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
        add_btn = QPushButton(self.tr("Ajouter PDF")); add_btn.setIcon(QIcon(":/icons/plus.svg")); add_btn.clicked.connect(self.add_pdf); btn_layout.addWidget(add_btn)
        remove_btn = QPushButton(self.tr("Supprimer")); remove_btn.setIcon(QIcon(":/icons/trash.svg")); remove_btn.clicked.connect(self.remove_selected); btn_layout.addWidget(remove_btn)
        move_up_btn = QPushButton(self.tr("Monter")); move_up_btn.setIcon(QIcon.fromTheme("go-up")); move_up_btn.clicked.connect(self.move_up); btn_layout.addWidget(move_up_btn)
        move_down_btn = QPushButton(self.tr("Descendre")); move_down_btn.setIcon(QIcon.fromTheme("go-down")); move_down_btn.clicked.connect(self.move_down); btn_layout.addWidget(move_down_btn)
        layout.addLayout(btn_layout)
        options_layout = QHBoxLayout(); options_layout.addWidget(QLabel(self.tr("Nom du fichier compilé:")))
        self.output_name = QLineEdit(f"{self.tr('compilation')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"); options_layout.addWidget(self.output_name); layout.addLayout(options_layout)
        action_layout = QHBoxLayout()
        compile_btn = QPushButton(self.tr("Compiler PDF")); compile_btn.setIcon(QIcon(":/icons/download.svg")); compile_btn.setObjectName("primaryButton")
        compile_btn.clicked.connect(self.compile_pdf); action_layout.addWidget(compile_btn)
        cancel_btn = QPushButton(self.tr("Annuler")); cancel_btn.setIcon(QIcon(":/icons/dialog-cancel.svg")); cancel_btn.clicked.connect(self.reject); action_layout.addWidget(cancel_btn)
        layout.addLayout(action_layout)
        self.load_existing_pdfs()

    def load_existing_pdfs(self):
        client_dir = self.client_info["base_folder_path"]; pdf_files = []
        for root, dirs, files in os.walk(client_dir):
            for file_name in files: # Renamed 'file' to 'file_name' to avoid conflict
                if file_name.lower().endswith('.pdf'): pdf_files.append(os.path.join(root, file_name))
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
                            if '-' in part: start, end = map(int, part.split('-')); pages.extend(range(start, end + 1))
                            else: pages.append(int(part))
                        merger.append(file_path, pages=[p-1 for p in pages]) # PyPDF2 pages are 0-indexed
                except Exception as e: QMessageBox.warning(self, self.tr("Erreur"), self.tr("Erreur lors de l'ajout de {0}:\n{1}").format(os.path.basename(file_path), str(e)))
        try:
            with open(output_path, 'wb') as f: merger.write(f)
            if cover_path and os.path.exists(cover_path): os.remove(cover_path) # Clean up temp cover
            # QMessageBox.information(self, self.tr("Compilation réussie"), self.tr("Le PDF compilé a été sauvegardé dans:\n{0}").format(output_path)) # Original line
            self.offer_download_or_email(output_path); # Call this before accept
            self.accept()
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur"), self.tr("Erreur lors de la compilation du PDF:\n{0}").format(str(e)))

    def create_cover_page(self):
        config_dict = {'title': self.tr("Compilation de Documents - Projet: {0}").format(self.client_info.get('project_identifier', self.tr('N/A'))),
                       'subtitle': self.tr("Client: {0}").format(self.client_info.get('client_name', self.tr('N/A'))),
                       'author': self.client_info.get('company_name', PAGEDEGRDE_APP_CONFIG.get('default_institution', self.tr('Votre Entreprise'))),
                       'institution': "", 'department': "", 'doc_type': self.tr("Compilation de Documents"),
                       'date': datetime.now().strftime('%d/%m/%Y %H:%M'), 'version': "1.0",
                       'font_name': PAGEDEGRDE_APP_CONFIG.get('default_font', 'Helvetica'), 'font_size_title': 20, 'font_size_subtitle': 16, 'font_size_author': 10,
                       'text_color': PAGEDEGRDE_APP_CONFIG.get('default_text_color', '#000000'), 'template_style': 'Moderne', 'show_horizontal_line': True, 'line_y_position_mm': 140,
                       'logo_data': None, 'logo_width_mm': 40, 'logo_height_mm': 40, 'logo_x_mm': 25, 'logo_y_mm': 297 - 25 - 40, # A4 height based
                       'margin_top': 25, 'margin_bottom': 25, 'margin_left': 20, 'margin_right': 20,
                       'footer_text': self.tr("Document compilé le {0}").format(datetime.now().strftime('%d/%m/%Y'))}

        logo_path = os.path.join(self.app_root_dir, "logo.png")
        if os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f_logo: config_dict['logo_data'] = f_logo.read()
            except Exception as e_logo: print(self.tr("Erreur chargement logo.png: {0}").format(e_logo)) # Keep print or use logging

        try:
            pdf_bytes = generate_cover_page_logic(config_dict)
            base_temp_dir = self.client_info.get("base_folder_path", QDir.tempPath()); temp_cover_filename = f"cover_page_generated_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.pdf"
            temp_cover_path = os.path.join(base_temp_dir, temp_cover_filename)
            with open(temp_cover_path, "wb") as f: f.write(pdf_bytes)
            return temp_cover_path
        except Exception as e:
            print(self.tr("Erreur lors de la génération de la page de garde via pagedegrde: {0}").format(e)) # Keep print or use logging
            QMessageBox.warning(self, self.tr("Erreur Page de Garde"), self.tr("Impossible de générer la page de garde personnalisée: {0}").format(e)); return None

    def offer_download_or_email(self, pdf_path):
        msg_box = QMessageBox(self); msg_box.setWindowTitle(self.tr("Compilation réussie")); msg_box.setText(self.tr("Le PDF compilé a été sauvegardé dans:\n{0}").format(pdf_path))
        download_btn = msg_box.addButton(self.tr("Télécharger"), QMessageBox.ActionRole); email_btn = msg_box.addButton(self.tr("Envoyer par email"), QMessageBox.ActionRole)
        close_btn = msg_box.addButton(self.tr("Fermer"), QMessageBox.RejectRole) # Changed to RejectRole for clarity
        msg_box.exec_()
        if msg_box.clickedButton() == download_btn: QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        elif msg_box.clickedButton() == email_btn: self.send_email(pdf_path)
        # If close_btn is clicked, it does nothing extra, dialog closes.

    def send_email(self, pdf_path):
        primary_email = None; client_uuid = self.client_info.get("client_id")
        if client_uuid:
            contacts_for_client = db_manager.get_contacts_for_client(client_uuid) # Uses db_manager
            if contacts_for_client:
                for contact in contacts_for_client:
                    if contact.get('is_primary_for_client'): primary_email = contact.get('email'); break

        email, ok = QInputDialog.getText(self, self.tr("Envoyer par email"), self.tr("Adresse email du destinataire:"), text=primary_email or "")
        if not ok or not email.strip(): return

        if not self.config.get("smtp_server") or not self.config.get("smtp_user"):
            QMessageBox.warning(self, self.tr("Configuration manquante"), self.tr("Veuillez configurer les paramètres SMTP dans les paramètres de l'application.")); return

        msg = MIMEMultipart(); msg['From'] = self.config["smtp_user"]; msg['To'] = email; msg['Subject'] = self.tr("Documents compilés - {0}").format(self.client_info.get('client_name', 'N/A'))
        body = self.tr("Bonjour,\n\nVeuillez trouver ci-joint les documents compilés pour le projet {0}.\n\nCordialement,\nVotre équipe").format(self.client_info.get('project_identifier', 'N/A')); msg.attach(MIMEText(body, 'plain'))

        with open(pdf_path, 'rb') as f: part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'; msg.attach(part)

        try:
            server = smtplib.SMTP(self.config["smtp_server"], self.config.get("smtp_port", 587))
            if self.config.get("smtp_port", 587) == 587: server.starttls()
            server.login(self.config["smtp_user"], self.config["smtp_password"]); server.send_message(msg); server.quit()
            QMessageBox.information(self, self.tr("Email envoyé"), self.tr("Le document a été envoyé avec succès."))
        except Exception as e: QMessageBox.critical(self, self.tr("Erreur d'envoi"), self.tr("Erreur lors de l'envoi de l'email:\n{0}").format(str(e)))
