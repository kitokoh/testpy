# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QDialogButtonBox, QDoubleSpinBox, QMessageBox
)
from PyQt5.QtGui import QIcon
# from PyQt5.QtCore import Qt # Qt not directly used, omitting for now

# Anticipated import, will be resolved when ProductDimensionUIDialog is moved
from .product_dimension_ui_dialog import ProductDimensionUIDialog


class EditProductLineDialog(QDialog):
    def __init__(self, product_data, app_root_dir, parent=None): # Added app_root_dir
        super().__init__(parent)
        self.product_data = product_data
        self.app_root_dir = app_root_dir # Store app_root_dir
        self.setWindowTitle(self.tr("Modifier Ligne de Produit"))
        self.setMinimumSize(450, 300) # Adjusted for new button
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout(); form_layout.setSpacing(10)
        self.name_input = QLineEdit(self.product_data.get('name', ''))
        form_layout.addRow(self.tr("Nom du Produit:"), self.name_input)
        self.description_input = QTextEdit(self.product_data.get('description', ''))
        self.description_input.setFixedHeight(80)
        form_layout.addRow(self.tr("Description:"), self.description_input)

        # Editable Weight and Dimensions for the specific client product line
        self.weight_input_edit = QDoubleSpinBox()
        self.weight_input_edit.setSuffix(" kg")
        self.weight_input_edit.setRange(0.0, 10000.0) # Adjust range as needed
        self.weight_input_edit.setDecimals(2) # Adjust decimals as needed
        retrieved_weight = self.product_data.get('weight', 0.0)
        self.weight_input_edit.setValue(float(retrieved_weight) if retrieved_weight is not None else 0.0)
        form_layout.addRow(self.tr("Poids (Ligne):"), self.weight_input_edit)

        self.dimensions_input_edit = QLineEdit(self.product_data.get('dimensions', ''))
        self.dimensions_input_edit.setPlaceholderText(self.tr("LxlxH cm"))
        form_layout.addRow(self.tr("Dimensions (Ligne):"), self.dimensions_input_edit)

        # Add View Detailed Dimensions Button (references global product)
        self.view_detailed_dimensions_button = QPushButton(self.tr("Voir Dimensions Détaillées (Global Produit)"))
        self.view_detailed_dimensions_button.setIcon(QIcon.fromTheme("view-fullscreen")) # Example icon
        self.view_detailed_dimensions_button.clicked.connect(self.on_view_detailed_dimensions)
        if not self.product_data.get('product_id'): # Disable if no product_id
            self.view_detailed_dimensions_button.setEnabled(False)
        form_layout.addRow(self.view_detailed_dimensions_button)

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

    def on_view_detailed_dimensions(self):
        product_id = self.product_data.get('product_id')
        if product_id is not None:
            # Ensure app_root_dir is passed to ProductDimensionUIDialog
            dialog = ProductDimensionUIDialog(product_id, self.app_root_dir, self, read_only=True)
            dialog.exec_()
        else:
            QMessageBox.information(self, self.tr("ID Produit Manquant"), self.tr("Aucun ID de produit global associé à cette ligne."))

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "quantity": self.quantity_input.value(),
            "unit_price": self.unit_price_input.value(),
            "weight": self.weight_input_edit.value(),
            "dimensions": self.dimensions_input_edit.text().strip(),
            "product_id": self.product_data.get('product_id'),
            "client_project_product_id": self.product_data.get('client_project_product_id')
        }
