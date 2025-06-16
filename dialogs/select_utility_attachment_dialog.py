# -*- coding: utf-8 -*-
import os

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QDialogButtonBox, QLabel, QMessageBox, QHeaderView, QAbstractItemView
)
from PyQt5.QtGui import QColor # QIcon not directly used
from PyQt5.QtCore import Qt

import db as db_manager

class SelectUtilityAttachmentDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.selected_files = []
        self.utility_category_name = "Document Utilitaires"

        self.setWindowTitle(self.tr("Sélectionner Documents Utilitaires"))
        self.setMinimumSize(500, 350)
        self.setup_ui()
        self.load_utility_documents()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.doc_table_widget = QTableWidget()
        self.doc_table_widget.setColumnCount(4)
        self.doc_table_widget.setHorizontalHeaderLabels([
            "",
            self.tr("Nom du Document"),
            self.tr("Langue"),
            self.tr("Nom de Fichier")
        ])
        self.doc_table_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.doc_table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.doc_table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.doc_table_widget.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.doc_table_widget.setColumnWidth(0, 30)

        layout.addWidget(QLabel(self.tr("Documents utilitaires disponibles :")))
        layout.addWidget(self.doc_table_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok); ok_button.setText(self.tr("OK")); ok_button.setObjectName("primaryButton")
        cancel_button = button_box.button(QDialogButtonBox.Cancel); cancel_button.setText(self.tr("Annuler"))

        button_box.accepted.connect(self.accept_selection)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_utility_documents(self):
        self.doc_table_widget.setRowCount(0)
        category = db_manager.get_template_category_by_name(self.utility_category_name)
        if not category:
            QMessageBox.warning(self, self.tr("Erreur Catégorie"),
                                self.tr("La catégorie '{0}' est introuvable.").format(self.utility_category_name))
            return

        templates = db_manager.get_templates_by_category_id(category['category_id'])
        if not templates:
            QMessageBox.information(self, self.tr("Aucun Document"),
                                    self.tr("Aucun document utilitaire trouvé dans la catégorie '{0}'.").format(self.utility_category_name))
            return

        templates_dir = self.config.get("templates_dir")
        if not templates_dir:
            QMessageBox.critical(self, self.tr("Erreur Configuration"), self.tr("Le dossier des modèles n'est pas configuré."))
            return

        for row_idx, template_data in enumerate(templates):
            self.doc_table_widget.insertRow(row_idx)

            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Unchecked)
            self.doc_table_widget.setItem(row_idx, 0, chk_item)

            name_item = QTableWidgetItem(template_data.get('template_name', self.tr('N/A')))
            self.doc_table_widget.setItem(row_idx, 1, name_item)

            lang_code = template_data.get('language_code', self.tr('N/A'))
            self.doc_table_widget.setItem(row_idx, 2, QTableWidgetItem(lang_code))

            base_file_name = template_data.get('base_file_name', self.tr('N/A'))
            self.doc_table_widget.setItem(row_idx, 3, QTableWidgetItem(base_file_name))

            full_path = os.path.join(templates_dir, lang_code, base_file_name)
            if not os.path.exists(full_path):
                # Fallback for "utility" subfolder structure if that's a convention
                alt_path = os.path.join(templates_dir, "utility", lang_code, base_file_name)
                if os.path.exists(alt_path):
                    full_path = alt_path
                else:
                    name_item.setForeground(QColor("red"))
                    name_item.setToolTip(self.tr("Fichier non trouvé: {0} ou {1}").format(full_path, alt_path))
                    chk_item.setFlags(chk_item.flags() & ~Qt.ItemIsEnabled)
                    full_path = None
            if full_path:
                 name_item.setData(Qt.UserRole, full_path)

    def accept_selection(self):
        self.selected_files = []
        for row in range(self.doc_table_widget.rowCount()):
            chk_item = self.doc_table_widget.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.Checked:
                name_item = self.doc_table_widget.item(row, 1) # Name item holds the path in UserRole
                if name_item:
                    file_path = name_item.data(Qt.UserRole)
                    if file_path and os.path.exists(file_path):
                        self.selected_files.append(file_path)
                    elif file_path:
                        QMessageBox.warning(self, self.tr("Fichier Manquant"), self.tr("Le fichier {0} n'a pas pu être trouvé au moment de la sélection.").format(os.path.basename(file_path)))
        self.accept()

    def get_selected_files(self):
        return self.selected_files
