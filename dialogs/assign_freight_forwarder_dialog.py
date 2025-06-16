# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QTextEdit,
    QDoubleSpinBox, QDialogButtonBox, QMessageBox
)
# No specific QtGui or QtCore imports noted as directly used by this class methods
# other than those implicitly handled by QtWidgets.

import db as db_manager

class AssignFreightForwarderDialog(QDialog):
    def __init__(self, client_id, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.setWindowTitle(self.tr("Assigner Transitaire au Client")) # Title seems to be a slight misnomer, "Assign Freight Forwarder"
        self.setMinimumWidth(450)
        self.setup_ui()
        self.load_available_forwarders()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.forwarder_combo = QComboBox()
        form_layout.addRow(self.tr("Transitaire Disponible:"), self.forwarder_combo)

        self.task_description_edit = QTextEdit()
        self.task_description_edit.setPlaceholderText(self.tr("Ex: Dédouanement pour l'expédition XYZ..."))
        self.task_description_edit.setFixedHeight(80)
        form_layout.addRow(self.tr("Description de la Tâche:"), self.task_description_edit)

        self.cost_estimate_spinbox = QDoubleSpinBox()
        self.cost_estimate_spinbox.setRange(0.0, 9999999.99)
        self.cost_estimate_spinbox.setDecimals(2)
        self.cost_estimate_spinbox.setPrefix("€ ")
        form_layout.addRow(self.tr("Coût Estimé:"), self.cost_estimate_spinbox)

        main_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText(self.tr("Assigner"))
        self.button_box.button(QDialogButtonBox.Ok).setObjectName("primaryButton")
        self.button_box.button(QDialogButtonBox.Cancel).setText(self.tr("Annuler"))
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def load_available_forwarders(self):
        self.forwarder_combo.clear()
        try:
            forwarders = db_manager.get_all_freight_forwarders()
            if not forwarders: # forwarders could be None or empty list
                self.forwarder_combo.addItem(self.tr("Aucun transitaire disponible."), None)
                self.forwarder_combo.setEnabled(False)
                return

            self.forwarder_combo.setEnabled(True) # Ensure enabled if data loaded
            for ff in forwarders:
                self.forwarder_combo.addItem(ff.get('name', 'N/A'), ff.get('forwarder_id'))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de charger les transitaires: {0}").format(str(e)))
            self.forwarder_combo.setEnabled(False)

    def accept(self):
        selected_forwarder_id = self.forwarder_combo.currentData()
        description_text = self.task_description_edit.toPlainText().strip()
        cost_value = self.cost_estimate_spinbox.value()

        if selected_forwarder_id is None:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Veuillez sélectionner un transitaire."))
            self.forwarder_combo.setFocus()
            return

        try:
            assignment_id = db_manager.assign_forwarder_to_client(
                client_id=self.client_id,
                forwarder_id=selected_forwarder_id,
                task_description=description_text,
                cost_estimate=cost_value
            )
            if assignment_id:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Transitaire assigné avec succès."))
                super().accept()
            else:
                QMessageBox.warning(self, self.tr("Échec Assignation"),
                                    self.tr("Impossible d'assigner le transitaire. Vérifiez s'il est déjà assigné ou consultez les logs."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur est survenue: {0}").format(str(e)))
