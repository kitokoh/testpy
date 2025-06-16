# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import Qt # Added for Qt.UserRole

import db as db_manager

class AssignPersonnelDialog(QDialog):
    def __init__(self, client_id, role_filter, company_id, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.role_filter = role_filter
        self.company_id = company_id

        self.setWindowTitle(self.tr("Assigner Personnel au Client"))
        self.setMinimumWidth(400)
        self.setup_ui()
        self.load_available_personnel()
        if self.personnel_combo.count() > 0:
            self._on_personnel_selected(self.personnel_combo.currentIndex())


    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.personnel_combo = QComboBox()
        form_layout.addRow(self.tr("Personnel Disponible:"), self.personnel_combo)

        self.role_in_project_edit = QLineEdit()
        self.role_in_project_edit.setPlaceholderText(self.tr("Ex: Vendeur principal, Support Technique"))
        form_layout.addRow(self.tr("Rôle pour ce Client/Projet:"), self.role_in_project_edit)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self.tr("Assigner"))
        self.button_box.button(QDialogButtonBox.Ok).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

        self.personnel_combo.currentIndexChanged.connect(self._on_personnel_selected)

    def _on_personnel_selected(self, index):
        if index < 0: # Should not happen if combo has items, but good check
            self.role_in_project_edit.clear()
            return

        general_role = self.personnel_combo.itemData(index, Qt.UserRole + 1)

        if general_role and general_role not in ['N/A', '']:
            self.role_in_project_edit.setText(general_role)
        else:
            # Optional: Use self.role_filter if it's descriptive and general_role is not useful
            # For now, just clearing if personnel's own role isn't specific enough.
            self.role_in_project_edit.clear()
            if self.role_filter: # If a filter was provided, it might be a good default
                 # This could be refined, e.g. "technical_manager" might map to "Technical Manager"
                self.role_in_project_edit.setPlaceholderText(self.tr("Rôle suggéré: {0}").format(self.role_filter))


    def load_available_personnel(self):
        self.personnel_combo.clear()
        try:
            personnel_list = db_manager.get_personnel_for_company(self.company_id, role=self.role_filter)
            if not personnel_list: # personnel_list could be None or empty list
                self.personnel_combo.addItem(self.tr("Aucun personnel disponible pour ce filtre."), None)
                self.personnel_combo.setEnabled(False)
                return

            self.personnel_combo.setEnabled(True) # Ensure it's enabled if there was data
            for p in personnel_list:
                display_text = f"{p.get('name', 'N/A')} ({p.get('role', 'N/A')})"
                personnel_id = p.get('personnel_id')
                general_role = p.get('role', 'N/A')

                # Add item and store personnel_id in UserRole
                self.personnel_combo.addItem(display_text, personnel_id)

                # Store general_role in UserRole + 1
                # Need to get the index of the item just added to set its data for UserRole + 1
                # This is a bit inefficient. A QStandardItemModel would be better for complex data.
                # For now, find the item if only one was added, or manage index.
                # Assuming addItem appends, so last item is count - 1
                item_index = self.personnel_combo.count() - 1
                if item_index >= 0: # Should always be true here
                    self.personnel_combo.setItemData(item_index, general_role, Qt.UserRole + 1)

        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de charger le personnel: {0}").format(str(e)))
            self.personnel_combo.setEnabled(False)

    def accept(self):
        selected_personnel_id = self.personnel_combo.currentData(Qt.UserRole) # Explicitly get UserRole for ID
        role_in_project_text = self.role_in_project_edit.text().strip()

        if selected_personnel_id is None: # Check if data is None (e.g. "Aucun personnel..." item)
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Veuillez sélectionner un membre du personnel."))
            self.personnel_combo.setFocus()
            return

        if not role_in_project_text:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Veuillez définir un rôle pour ce personnel pour ce client/projet."))
            self.role_in_project_edit.setFocus()
            return

        try:
            assignment_id = db_manager.assign_personnel_to_client(
                client_id=self.client_id,
                personnel_id=selected_personnel_id,
                role_in_project=role_in_project_text
            )
            if assignment_id:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Personnel assigné avec succès."))
                super().accept()
            else:
                QMessageBox.warning(self, self.tr("Échec Assignation"),
                                    self.tr("Impossible d'assigner le personnel. Vérifiez s'il est déjà assigné avec ce rôle ou consultez les logs."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur est survenue: {0}").format(str(e)))
