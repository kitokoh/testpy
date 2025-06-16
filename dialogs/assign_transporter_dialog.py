# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QTextEdit,
    QDoubleSpinBox, QDialogButtonBox, QMessageBox
)
# No specific QtGui or QtCore imports noted as directly used by this class methods
# other than those implicitly handled by QtWidgets.

import db as db_manager

class AssignTransporterDialog(QDialog):
    def __init__(self, client_id, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.setWindowTitle(self.tr("Assigner Transporteur au Client"))
        self.setMinimumWidth(450)
        self.setup_ui()
        self.load_available_transporters()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.transporter_combo = QComboBox()
        form_layout.addRow(self.tr("Transporteur Disponible:"), self.transporter_combo)

        self.transport_details_edit = QTextEdit()
        self.transport_details_edit.setPlaceholderText(self.tr("Ex: Route A vers B, instructions spécifiques..."))
        self.transport_details_edit.setFixedHeight(80)
        form_layout.addRow(self.tr("Détails du Transport:"), self.transport_details_edit)

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

    def load_available_transporters(self):
        self.transporter_combo.clear()
        try:
            transporters = db_manager.get_all_transporters()
            if not transporters: # transporters could be None or empty list
                self.transporter_combo.addItem(self.tr("Aucun transporteur disponible."), None)
                self.transporter_combo.setEnabled(False)
                return

            self.transporter_combo.setEnabled(True) # Ensure enabled if data is loaded
            for t in transporters:
                self.transporter_combo.addItem(t.get('name', 'N/A'), t.get('transporter_id'))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur DB"), self.tr("Impossible de charger les transporteurs: {0}").format(str(e)))
            self.transporter_combo.setEnabled(False)

    def accept(self):
        selected_transporter_id = self.transporter_combo.currentData()
        details_text = self.transport_details_edit.toPlainText().strip()
        cost_value = self.cost_estimate_spinbox.value()

        if selected_transporter_id is None:
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Veuillez sélectionner un transporteur."))
            self.transporter_combo.setFocus()
            return

        try:
            assignment_id = db_manager.assign_transporter_to_client(
                client_id=self.client_id,
                transporter_id=selected_transporter_id,
                transport_details=details_text,
                cost_estimate=cost_value
            )
            if assignment_id:
                QMessageBox.information(self, self.tr("Succès"), self.tr("Transporteur assigné avec succès."))
                super().accept()
            else:
                QMessageBox.warning(self, self.tr("Échec Assignation"),
                                    self.tr("Impossible d'assigner le transporteur. Vérifiez s'il est déjà assigné ou consultez les logs."))
        except Exception as e:
            QMessageBox.critical(self, self.tr("Erreur Inattendue"), self.tr("Une erreur est survenue: {0}").format(str(e)))
